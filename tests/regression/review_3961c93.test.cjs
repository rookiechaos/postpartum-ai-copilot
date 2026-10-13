// Session, profile preservation and chart regressions for the 3961c93 review.
const test = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const vm = require('node:vm')
const { harness, all, find, text, flush, root } = require('./component_harness.cjs')
const deferred = () => {
  let resolve, reject
  const promise = new Promise((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}
const json = (value, status = 200) => new Response(JSON.stringify(value), { status })
const outcome = promise => promise.then(value => ({ value }), error => ({ error }))
const button = (tree, caption) => find(tree, node => node.type === 'button' && text(node) === caption)

// Browser storage is shared, while modules and queued storage events belong to each tab.
function browserTabs() {
  const stored = new Map([['access_token', 'fixture-access-a'], ['refresh_token', 'fixture-refresh-a'], ['userId', 'sample_a']])
  const tabs = [], pendingEvents = []
  function tab(fetch) {
    const events = new Map()
    const localStorage = {
      getItem: key => stored.get(key) || null,
      setItem(key, value) { const oldValue = this.getItem(key); stored.set(key, String(value)); emit(key, oldValue, String(value)) },
      removeItem(key) { const oldValue = this.getItem(key); stored.delete(key); emit(key, oldValue, null) },
      clear() { stored.clear(); emit(null, null, null) },
    }
    function emit(key, oldValue, newValue) {
      for (const other of tabs) if (other.events !== events) {
        pendingEvents.push(() => other.events.get('storage')?.({ key, oldValue, newValue, storageArea: other.localStorage }))
      }
    }
    const context = {
      console: { error() {} }, AbortController, setTimeout, clearTimeout, fetch, localStorage,
      window: { addEventListener: (name, callback) => events.set(name, callback) },
      caches: { async keys() { return [] } },
    }
    const source = fs.readFileSync(path.join(root, 'frontend/src/utils/api.js'), 'utf8')
      .replace('import.meta.env.VITE_API_BASE_URL', 'undefined')
      .replace(/^export const /gm, 'const ')
      .replace('export default api', 'globalThis.reviewApi = api')
    vm.createContext(context)
    vm.runInContext(source, context)
    const result = { api: context.reviewApi, events, localStorage }
    tabs.push(result)
    return result
  }
  return { stored, tab, flushStorage() { pendingEvents.splice(0).forEach(callback => callback()) } }
}

function mountedApp(api) {
  const h = harness('frontend/src/App.jsx', { api })
  const app = h.mount()
  app.render()
  assert.equal(app.render().props.userId, 'sample_a')
  return app
}

test('logout in another tab removes the mounted private account', async () => {
  const browser = browserTabs(), a = browser.tab(async () => json({})), b = browser.tab(async () => json({}))
  const app = mountedApp(a.api)
  await b.api.logout()
  browser.flushStorage()
  assert.equal(app.render().type, './components/Auth')
  app.unmount()
})

test('cross-tab account switch rejects private bodies before storage events are delivered', async () => {
  for (const method of ['get', 'post', 'delete']) {
    const browser = browserTabs(), body = deferred()
    const a = browser.tab(async () => ({ ok: true, status: 200, json: () => body.promise }))
    const b = browser.tab(async () => json({ access_token: 'fixture-access-b', refresh_token: 'fixture-refresh-b' }))
    const app = mountedApp(a.api)
    const result = outcome(method === 'post' ? a.api.post('/api/private', {}) : a.api[method]('/api/private'))
    await flush()
    await b.api.login('review@example.com', 'fixture-password')
    b.api.setUserId('sample_b')
    body.resolve({ privateOwner: 'sample_a' })
    assert.match((await result).error?.message || '', /session changed/)
    assert.equal(app.render().type, './components/Auth')
    assert.equal(browser.stored.get('access_token'), 'fixture-access-b')
    browser.flushStorage()
    app.unmount()
  }
})

test('same-account token refresh in another tab preserves private state and pending requests', async () => {
  for (const marker of [null, 'fixture-login-a']) {
    const browser = browserTabs(), body = deferred(), changes = []
    if (marker) browser.stored.set('auth_session_id', marker)
    const a = browser.tab(async () => ({ ok: true, status: 200, json: () => body.promise }))
    let calls = 0
    const b = browser.tab(async url => {
      if (url.endsWith('/api/auth/refresh')) return json({ access_token: 'fixture-access-renewed', refresh_token: 'fixture-refresh-renewed' })
      return ++calls === 1 ? json({}, 401) : json({ user_id: 'sample_a' })
    })
    const app = mountedApp(a.api), before = app.render()
    a.api.onAuthChange(change => changes.push(change))
    const pending = a.api.get('/api/private')
    await flush()
    await b.api.getCurrentUser()
    browser.flushStorage()
    body.resolve({ privateOwner: 'sample_a' })
    assert.equal((await pending).privateOwner, 'sample_a')
    assert.equal(app.render().props.key, before.props.key)
    assert.ok(changes.length > 0)
    assert.ok(changes.every(change => change.preserveTasks === true))
    app.unmount()
  }
})

test('clearing browser storage clears other tabs and rejects a late response', async () => {
  const browser = browserTabs(), response = deferred()
  const a = browser.tab(() => response.promise), b = browser.tab(async () => json({}))
  const app = mountedApp(a.api), pending = outcome(a.api.get('/api/private'))
  b.localStorage.clear()
  browser.flushStorage()
  response.resolve(json({ privateOwner: 'sample_a' }))
  assert.equal(app.render().type, './components/Auth')
  assert.match((await pending).error?.message || '', /session changed/)
  app.unmount()
})

test('a late cross-tab refresh cannot replace or log out the new account', async () => {
  const browser = browserTabs(), refresh = deferred()
  const a = browser.tab(url => url.endsWith('/api/auth/refresh') ? refresh.promise : Promise.resolve(json({}, 401)))
  const b = browser.tab(async () => json({ access_token: 'fixture-access-b', refresh_token: 'fixture-refresh-b' }))
  const pending = outcome(a.api.get('/api/private'))
  await flush()
  await b.api.login('review@example.com', 'fixture-password')
  b.api.setUserId('sample_b')
  refresh.resolve(json({ access_token: 'fixture-access-old-renewed', refresh_token: 'fixture-refresh-old-renewed' }))
  assert.match((await pending).error?.message || '', /session changed/)
  assert.equal(browser.stored.get('access_token'), 'fixture-access-b')
  assert.equal(browser.stored.get('userId'), 'sample_b')
})

test('an old tab cannot submit stale form data with the new account token before storage events', async () => {
  const browser = browserTabs()
  let sends = 0
  const a = browser.tab(async () => { sends++; return json({}) })
  const b = browser.tab(async () => json({ access_token: 'fixture-access-b', refresh_token: 'fixture-refresh-b' }))
  await b.api.login('review@example.com', 'fixture-password')
  b.api.setUserId('sample_b')
  await assert.rejects(a.api.post('/api/private', { notes: 'previous account draft' }), /session changed/)
  assert.equal(sends, 0)
})

test('stale authentication metadata cannot overwrite the current cross-tab account', async () => {
  const browser = browserTabs(), a = browser.tab(async () => json({}))
  const b = browser.tab(async () => json({ access_token: 'fixture-access-b', refresh_token: 'fixture-refresh-b' }))
  await b.api.login('review@example.com', 'fixture-password')
  b.api.setUserId('sample_b')
  assert.throws(() => a.api.setUserId('sample_a'), /session changed/)
  assert.equal(browser.stored.get('userId'), 'sample_b')
})

function welcomeFixture() {
  const calls = [], existing = { babyName: 'saved nickname', babyAge: '2-3m', feedingType: 'mixed', notifications: true, language: 'ja' }
  const h = harness('frontend/src/App.jsx', { api: {
    onAuthChange: () => () => {}, setOnUnauthorized() {}, isAuthenticated: () => true, getUserId: () => 'sample_a',
    async updateUserContext(_id, context) { calls.push(context); return { context: { ...existing, ...context } } },
  } })
  h.stored.set('hasCompletedWelcome:sample_b', 'true')
  const app = h.mount()
  app.render()
  const account = app.render(), family = h.mount(account.props, account.type)
  family.render()
  assert.equal(family.render().type, './components/WelcomeScreen')
  const welcome = h.mount(family.render().props, h.load('frontend/src/components/WelcomeScreen.jsx').default)
  return { h, app, family, welcome, calls }
}

test('skipping welcome on a new device does not submit blank profile fields or draft edits', async () => {
  const { h, app, family, welcome, calls } = welcomeFixture()
  button(welcome.render(), h.t('welcome.next')).props.onClick()
  find(welcome.render(), node => node.type === 'input').props.onChange({ target: { value: 'unfinished nickname' } })
  await button(welcome.render(), h.t('welcome.skip')).props.onClick()
  assert.deepEqual(JSON.parse(JSON.stringify(calls)), [{ language: 'ja' }])
  assert.equal(h.stored.get('hasCompletedWelcome:sample_a'), 'true')
  assert.equal(find(family.render(), node => node.type === './components/TrackingPanel').props.initialEntryType, 'feeding')
  welcome.unmount(); family.unmount(); app.unmount()
})

test('welcome completion submits only the optional fields the user supplied', async () => {
  const { h, app, family, calls } = welcomeFixture()
  await family.render().props.onComplete({ babyName: 'new nickname', babyAge: '', birthType: '', feedingType: '' })
  assert.deepEqual(JSON.parse(JSON.stringify(calls)), [{ babyName: 'new nickname', language: 'ja' }])
  assert.equal(h.stored.get('hasCompletedWelcome:sample_a'), 'true')
  family.unmount(); app.unmount()
})

test('settings cannot edit or save until loading succeeds, then explicit clearing is allowed', async () => {
  const load = deferred(), writes = [], updates = []
  const h = harness('frontend/src/components/Settings.jsx', { globals: { setTimeout() {} }, api: {
    getUserContext: () => load.promise,
    async updateUserContext(_id, context) { writes.push(context); return { context: { preferences: { tone: 'warm' }, ...context } } },
  } })
  const settings = h.mount({ userId: 'sample_a', onContextUpdate: context => updates.push(context) })
  let tree = settings.render()
  const save = find(tree, node => node.props.className === 'save-button')
  assert.equal(save.props.disabled, true)
  assert.equal(find(tree, node => node.type === 'fieldset').props.disabled, true)
  await save.props.onClick()
  assert.equal(writes.length, 0)
  load.resolve({ babyName: 'saved nickname', babyAge: '2-3m', notifications: true, language: 'ja' })
  await flush()
  tree = settings.render()
  assert.equal(find(tree, node => node.props.className === 'save-button').props.disabled, false)
  const nickname = find(tree, node => node.type === 'input' && node.props.type === 'text')
  assert.equal(nickname.props.value, 'saved nickname')
  nickname.props.onChange({ target: { value: '' } })
  await find(settings.render(), node => node.props.className === 'save-button').props.onClick()
  assert.equal(writes[0].babyName, '')
  assert.equal(writes[0].babyAge, '2-3m')
  assert.equal(writes[0].notifications, true)
  assert.equal(updates[0].preferences.tone, 'warm')
  assert.equal(h.errors.length, 0)
  settings.unmount()
})

test('failed settings loading blocks saving and exposes a working retry', async () => {
  let reads = 0, writes = 0
  const h = harness('frontend/src/components/Settings.jsx', { api: {
    async getUserContext() { if (++reads === 1) throw new Error('offline'); return { babyName: 'retained', language: 'ja' } },
    async updateUserContext() { writes++; return {} },
  } })
  const settings = h.mount({ userId: 'sample_a' })
  settings.render()
  await flush()
  let tree = settings.render()
  assert.match(text(find(tree, node => node.props.role === 'alert')), /読み込めません/)
  const save = find(tree, node => node.props.className === 'save-button')
  assert.equal(save.props.disabled, true)
  await save.props.onClick()
  assert.equal(writes, 0)
  button(tree, h.t('pilot.retry')).props.onClick()
  settings.render()
  await flush()
  tree = settings.render()
  assert.equal(reads, 2)
  assert.equal(find(tree, node => node.props.role === 'alert'), undefined)
  assert.equal(find(tree, node => node.props.className === 'save-button').props.disabled, false)
  assert.equal(find(tree, node => node.type === 'input' && node.props.type === 'text').props.value, 'retained')
  settings.unmount()
})

test('late settings loading cannot update an unmounted account', async () => {
  const load = deferred()
  const h = harness('frontend/src/components/Settings.jsx', { api: { getUserContext: () => load.promise } })
  const settings = h.mount({ userId: 'sample_a' })
  settings.render(); settings.unmount()
  load.resolve({ babyName: 'private previous account', language: 'ja' })
  await flush()
  assert.equal(settings.lateUpdates, 0)
})

test('saving the first record refreshes an already open chart without remounting it', async () => {
  const records = []
  const h = harness('frontend/src/components/TrackingPanel.jsx', { api: {
    getTracking: async () => records.slice(),
    async addTrackingEntry(entry) { records.push({ ...entry, id: 1, timestamp: new Date().toISOString() }); return { id: 1 } },
  } })
  const panel = h.mount({ userId: 'sample_a', initialEntryType: 'feeding' })
  panel.render(); await flush()
  button(panel.render(), h.t('tracking.showCharts')).props.onClick()
  let chartProps = find(panel.render(), node => node.type === './Charts').props
  const Charts = h.load('frontend/src/components/Charts.jsx').default
  const charts = h.mount({}, () => Charts(chartProps))
  charts.render(); await flush()
  assert.equal(charts.render().type, './EmptyState')
  const form = find(panel.render(), node => typeof node.type === 'function' && node.props.onSubmit)
  await form.props.onSubmit({ entry_type: 'feeding', feeding_type: 'formula', amount_ml: 60 })
  panel.render(); await flush()
  const tree = panel.render()
  assert.equal(all(tree).filter(node => node?.type === 'article').length, 1)
  chartProps = find(tree, node => node.type === './Charts').props
  charts.render(); await flush()
  assert.equal(find(charts.render(), node => node.type === 'chart.BarChart').props.data.at(-1).feeds, 1)
  charts.unmount(); panel.unmount()
})

test('refreshing chart data keeps the selected range and ignores older responses', async () => {
  const requests = []
  const h = harness('frontend/src/components/Charts.jsx', { api: { getTracking(_id, days) {
    const request = { ...deferred(), days }; requests.push(request); return request.promise
  } } })
  const props = { userId: 'sample_a', refreshKey: 0 }, charts = h.mount(props)
  const record = { entry_type: 'feeding', timestamp: new Date().toISOString() }
  charts.render()
  requests[0].resolve([record]); await flush()
  find(charts.render(), node => node.type === 'select').props.onChange({ target: { value: '14' } })
  charts.render()
  props.refreshKey++
  charts.render()
  assert.deepEqual(requests.map(request => request.days), [7, 14, 14])
  requests[2].resolve([record, record]); await flush()
  requests[1].resolve([]); await flush()
  const tree = charts.render()
  assert.equal(find(tree, node => node.type === 'select').props.value, 14)
  const data = find(tree, node => node.type === 'chart.BarChart').props.data
  assert.equal(data.length, 14)
  assert.equal(data.at(-1).feeds, 2)
  charts.unmount()
})
