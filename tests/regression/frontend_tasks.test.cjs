const test = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const vm = require('node:vm')

const root = path.resolve(__dirname, '../..')
const flush = () => new Promise(setImmediate)
const deferred = () => {
  let resolve, reject
  const promise = new Promise((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}
const json = (data, status = 200) => new Response(JSON.stringify(data), { status })

// Load the actual API, socket and task modules together with deterministic time.
function fixture({ authenticated = true, fetch: fetchOverride } = {}) {
  const stored = new Map(authenticated ? [['access_token', 'access-a'], ['refresh_token', 'refresh-a']] : [])
  const timers = new Map(), intervals = new Map(), instances = [], calls = []
  let now = 0, nextId = 0
  class ClockDate extends Date { static now() { return now } }
  class Socket {
    static OPEN = 1
    constructor(url) { this.url = url; this.readyState = 0; this.sent = []; instances.push(this) }
    open() { this.readyState = 1; this.onopen?.() }
    send(data) { this.sent.push(JSON.parse(data)) }
    close() { this.readyState = 3; this.onclose?.() }
    receive(task) { this.onmessage?.({ data: JSON.stringify({ type: 'task_update', data: task }) }) }
  }
  let handler = fetchOverride || (async (url) => {
    if (url.endsWith('/api/auth/login')) return json({ access_token: 'access-b', refresh_token: 'refresh-b' })
    if (url.endsWith('/api/auth/refresh')) return json({ access_token: 'access-renewed', refresh_token: 'refresh-renewed' })
    if (url.endsWith('/api/tasks')) return json({ task_id: 'task-a', status: 'pending' })
    return json({ task_id: 'task-a', status: 'processing' })
  })
  const context = {
    console: { log() {}, warn() {}, error() {} }, AbortController, URLSearchParams,
    Date: ClockDate, WebSocket: Socket,
    localStorage: {
      getItem: key => stored.get(key) || null,
      setItem: (key, value) => stored.set(key, value),
      removeItem: key => stored.delete(key)
    },
    fetch: (url, options) => { calls.push({ url, options }); return handler(url, options) },
    setTimeout: (callback, delay) => { const id = ++nextId; timers.set(id, { callback, due: now + delay }); return id },
    clearTimeout: id => timers.delete(id),
    setInterval: (callback, delay) => { const id = ++nextId; intervals.set(id, { callback, delay }); return id },
    clearInterval: id => intervals.delete(id),
  }
  vm.createContext(context)
  for (const [file, name] of [['api.js', 'api'], ['websocketManager.js', 'websocketManager'], ['taskManager.js', 'taskManager']]) {
    const source = fs.readFileSync(path.join(root, 'frontend/src/utils', file), 'utf8')
      .replace(/^import .*$/gm, '')
      .replace('import.meta.env.VITE_API_BASE_URL', 'undefined')
      .replace(/^export const /gm, 'const ')
      .replace(`export default ${name}`, `globalThis.review_${name} = ${name}`)
    vm.runInContext(source, context, { filename: file })
  }
  return {
    api: context.review_api, tasks: context.review_taskManager, sockets: context.review_websocketManager,
    stored, timers, intervals, instances, calls,
    setFetch(value) { handler = value },
    async advance(ms) {
      const target = now + ms
      let count = 0
      while (true) {
        const entries = [...timers].filter(([, timer]) => timer.due <= target).sort((a, b) => a[1].due - b[1].due)
        if (!entries.length) break
        if (++count > 1000) throw new Error('Unbounded timer loop')
        const [id, timer] = entries[0]
        timers.delete(id)
        now = timer.due
        timer.callback()
        await flush()
      }
      now = target
      await flush()
    }
  }
}

function outcome(promise) {
  return promise.then(value => ({ value }), error => ({ error }))
}

test('a connected socket without worker notifications still completes through polling', async () => {
  const f = fixture()
  f.instances[0].open()
  let polls = 0
  f.api.getTask = async () => (++polls === 1 ? { status: 'pending' } : { status: 'completed', result: 'done' })
  const result = f.tasks.submitTask('ai_chat', {})
  await flush()
  assert.equal(polls, 1)
  await f.advance(2000)
  assert.equal(await result, 'done')
  assert.equal(f.tasks.activeTasks.size, 0)
  assert.equal(f.timers.size, 0)
})

test('socket loss does not interrupt polling of existing tasks', async () => {
  const f = fixture()
  f.instances[0].open()
  let polls = 0
  f.api.getTask = async () => (++polls === 1 ? { status: 'processing' } : { status: 'completed', result: 'done' })
  const result = f.tasks.submitTask('ai_chat', {})
  await flush()
  f.instances[0].close()
  await f.advance(1000)
  assert.equal(await result, 'done')
  assert.equal(polls, 2)
  await f.api.logout()
  assert.equal(f.timers.size, 0)
})

test('wall-clock deadline rejects a task even when a status request never settles', async () => {
  const f = fixture()
  let signal
  f.api.getTask = (id, options) => { signal = options.signal; return new Promise(() => {}) }
  const result = outcome(f.tasks.submitTask('ai_chat', {}, { timeout: 2500 }))
  await flush()
  await f.advance(2500)
  assert.match((await result).error.message, /timeout/)
  assert.equal(signal.aborted, true)
  assert.equal(f.tasks.activeTasks.size, 0)
  assert.equal(f.timers.size, 0)
})

test('submission itself has a deadline and sends seconds to the backend', async () => {
  const f = fixture()
  let timeout, signal
  f.api.createTask = (type, data, priority, seconds, options) => {
    timeout = seconds; signal = options.signal
    return new Promise(() => {})
  }
  const result = outcome(f.tasks.submitTask('ai_chat', {}, { timeout: 300000 }))
  await f.advance(300000)
  assert.equal(timeout, 300)
  assert.equal(signal.aborted, true)
  assert.match((await result).error.message, /timeout/)
  assert.equal(f.tasks.pendingSubmissions.size, 0)
  assert.equal(f.timers.size, 0)
})

test('network failures count toward the retry budget and stop exactly at maxAttempts', async () => {
  const f = fixture()
  let calls = 0
  f.api.getTask = async () => { calls++; throw new Error('offline') }
  const result = outcome(f.tasks.submitTask('ai_chat', {}, { maxAttempts: 3 }))
  await flush()
  await f.advance(10000)
  assert.match((await result).error.message, /timeout/)
  assert.equal(calls, 3)
  assert.equal(f.tasks.activeTasks.size, 0)
  assert.equal(f.timers.size, 0)
})

test('authorization and missing-task errors are terminal, including the actual API status', async () => {
  for (const status of [401, 403, 404]) {
    const f = fixture()
    let polls = 0
    f.setFetch(async url => {
      if (url.endsWith('/api/tasks')) return json({ task_id: 'task-a', status: 'pending' })
      if (url.endsWith('/api/auth/refresh')) return json({}, 401)
      polls++
      return json({ detail: 'Unavailable' }, status)
    })
    const result = outcome(f.tasks.submitTask('ai_chat', {}))
    await flush()
    assert.ok((await result).error)
    await f.advance(10000)
    assert.equal(polls, 1)
    assert.equal(f.tasks.activeTasks.size, 0)
    assert.equal(f.timers.size, 0)
  }
})

test('WebSocket completion cancels polling and ignores a late HTTP completion', async () => {
  const f = fixture()
  f.instances[0].open()
  const status = deferred()
  let signal
  f.api.getTask = (id, options) => { signal = options.signal; return status.promise }
  const result = f.tasks.submitTask('ai_chat', {})
  await flush()
  f.instances[0].receive({ task_id: 'task-a', status: 'completed', result: 'socket-result' })
  assert.equal(await result, 'socket-result')
  status.resolve({ status: 'completed', result: 'late-result' })
  await flush()
  assert.equal(f.tasks.getCachedResult('task-a'), 'socket-result')
  assert.equal(signal.aborted, true)
  assert.equal(f.timers.size, 0)
  assert.equal(f.sockets.subscribedTasks.size, 0)
})

test('logout clears old results, aborts waiting tasks and prevents old socket reconnects', async () => {
  const f = fixture()
  const oldSocket = f.instances[0]
  oldSocket.open()
  const oldMessage = oldSocket.onmessage
  const oldClose = oldSocket.onclose
  const status = deferred()
  f.api.getTask = () => status.promise
  const result = outcome(f.tasks.submitTask('ai_chat', {}))
  await flush()
  f.tasks.taskCache.set('old-cache', 'private-a')
  await f.api.logout()
  assert.match((await result).error.message, /session changed/)
  assert.equal(f.tasks.taskCache.size, 0)
  assert.equal(f.tasks.activeTasks.size, 0)
  assert.equal(f.sockets.ws, null)
  assert.equal(f.intervals.size, 0)
  oldMessage({ data: JSON.stringify({ type: 'task_update', data: { task_id: 'task-a', status: 'completed', result: 'private-a' } }) })
  oldClose()
  status.resolve({ status: 'completed', result: 'private-a' })
  await f.advance(10000)
  assert.equal(f.tasks.taskCache.size, 0)
  assert.equal(f.instances.length, 1)
  assert.equal(f.timers.size, 0)
})

test('login from a signed-out session connects and receives task updates', async () => {
  const f = fixture({ authenticated: false })
  assert.equal(f.instances.length, 0)
  await f.api.login('review@example.com', 'fixture-password')
  assert.match(f.instances[0].url, /token=access-b/)
  f.instances[0].open()
  f.api.getTask = () => new Promise(() => {})
  const result = f.tasks.submitTask('ai_chat', {})
  await flush()
  f.instances[0].receive({ task_id: 'task-a', status: 'completed', result: 'account-b' })
  assert.equal(await result, 'account-b')
})

test('account switch rejects a late creation response without registering or caching it', async () => {
  const f = fixture()
  const creation = deferred()
  f.api.createTask = () => creation.promise
  const result = outcome(f.tasks.submitTask('ai_chat', {}))
  await f.api.login('review@example.com', 'fixture-password')
  assert.match((await result).error.message, /session changed/)
  creation.resolve({ task_id: 'old-a', status: 'completed', result: 'private-a' })
  await flush()
  assert.equal(f.tasks.activeTasks.size, 0)
  assert.equal(f.tasks.taskCache.size, 0)
  assert.match(f.instances.at(-1).url, /token=access-b/)
})

test('an old account cannot overwrite a new task using a stale HTTP response or socket frame', async () => {
  const f = fixture()
  const socketA = f.instances[0]
  socketA.open()
  const oldMessage = socketA.onmessage
  const oldStatus = deferred()
  f.api.getTask = () => oldStatus.promise
  const oldResult = outcome(f.tasks.submitTask('ai_chat', {}))
  await flush()
  await f.api.login('review@example.com', 'fixture-password')
  assert.ok((await oldResult).error)
  const socketB = f.instances.at(-1)
  socketB.open()
  f.api.getTask = () => new Promise(() => {})
  // Reuse an ID deliberately to exercise object identity as well as generation.
  const newResult = f.tasks.submitTask('ai_chat', {})
  await flush()
  oldStatus.resolve({ status: 'completed', result: 'private-a' })
  oldMessage({ data: JSON.stringify({ type: 'task_update', data: { task_id: 'task-a', status: 'completed', result: 'private-a' } }) })
  await flush()
  assert.equal(f.tasks.taskCache.size, 0)
  assert.equal(f.tasks.activeTasks.size, 1)
  socketB.receive({ task_id: 'task-a', status: 'completed', result: 'current-b' })
  assert.equal(await newResult, 'current-b')
})

test('same-account refresh reconnects with the renewed token and preserves pending tasks', async () => {
  const f = fixture()
  f.instances[0].open()
  f.api.getTask = () => new Promise(() => {})
  const result = f.tasks.submitTask('ai_chat', {})
  await flush()
  let meCalls = 0
  f.setFetch(async url => {
    if (url.endsWith('/api/auth/refresh')) return json({ access_token: 'access-renewed', refresh_token: 'refresh-renewed' })
    return ++meCalls === 1 ? json({}, 401) : json({ user_id: 'account-a' })
  })
  const generation = f.tasks.sessionGeneration
  assert.equal((await f.api.getCurrentUser()).user_id, 'account-a')
  assert.equal(f.tasks.sessionGeneration, generation)
  assert.equal(f.tasks.activeTasks.size, 1)
  const renewed = f.instances.at(-1)
  assert.match(renewed.url, /token=access-renewed/)
  renewed.open()
  assert.ok(renewed.sent.some(message => message.type === 'subscribe_task' && message.task_id === 'task-a'))
  renewed.receive({ task_id: 'task-a', status: 'completed', result: 'current-a' })
  assert.equal(await result, 'current-a')
  assert.equal(f.intervals.size, 1)
})

test('late refresh from a logged-out account cannot resurrect credentials or log out its successor', async () => {
  const refresh = deferred()
  const f = fixture({ fetch: async url => {
    if (url.endsWith('/api/auth/refresh')) return refresh.promise
    if (url.endsWith('/api/auth/login')) return json({ access_token: 'access-b', refresh_token: 'refresh-b' })
    return json({}, 401)
  } })
  const oldRequest = outcome(f.api.getCurrentUser())
  await flush()
  await f.api.login('review@example.com', 'fixture-password')
  refresh.resolve(json({ access_token: 'late-access-a', refresh_token: 'late-refresh-a' }))
  assert.match((await oldRequest).error.message, /session changed/)
  assert.equal(f.stored.get('access_token'), 'access-b')
  assert.equal(f.stored.get('refresh_token'), 'refresh-b')
  assert.match(f.sockets.ws.url, /token=access-b/)
})

test('manual disconnect cancels a scheduled automatic reconnect', async () => {
  const f = fixture()
  f.instances[0].open()
  f.instances[0].close()
  assert.equal(f.timers.size, 1)
  f.sockets.disconnect()
  await f.advance(10000)
  assert.equal(f.instances.length, 1)
  assert.equal(f.timers.size, 0)
})

test('task cancellation rejects waiting callers and clears timers', async () => {
  const f = fixture()
  f.api.getTask = () => new Promise(() => {})
  f.api.cancelTask = async () => ({ status: 'cancelled' })
  const result = outcome(f.tasks.submitTask('ai_chat', {}))
  await flush()
  await f.tasks.cancelTask('task-a')
  assert.match((await result).error.message, /cancelled/)
  assert.equal(f.tasks.activeTasks.size, 0)
  assert.equal(f.timers.size, 0)
})
