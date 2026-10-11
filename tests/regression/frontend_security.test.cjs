const test = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const vm = require('node:vm')

const root = path.resolve(__dirname, '../..')

function workerFixture(fetch) {
  const events = {}
  const deleted = []
  let cacheWrites = 0
  const cacheNames = ['postpartum-runtime-v2', 'postpartum-copilot-v2', 'postpartum-runtime-v3', 'postpartum-copilot-v3', 'unrelated-cache']
  const context = {
    Request, Response, URL, console,
    self: {
      addEventListener(name, callback) { events[name] = callback },
      clients: { async claim() {} },
      async skipWaiting() {}
    },
    fetch,
    caches: {
      async keys() { return cacheNames },
      async delete(name) { deleted.push(name); return true },
      async match() { return new Response('{"private":"previous-account"}') },
      async open() { return { async put() { cacheWrites++ }, async addAll() {} } }
    }
  }
  vm.createContext(context)
  vm.runInContext(fs.readFileSync(path.join(root, 'frontend/public/sw.js'), 'utf8'), context)
  return {
    events, deleted, cacheWrites: () => cacheWrites,
    fetch(request) {
      let response
      events.fetch({ request, respondWith(value) { response = value } })
      return response
    }
  }
}

function apiFixture(fetch) {
  const stored = new Map()
  const deleted = []
  const context = {
    console, AbortController, setTimeout, clearTimeout, fetch,
    localStorage: {
      getItem(key) { return stored.get(key) || null },
      setItem(key, value) { stored.set(key, value) },
      removeItem(key) { stored.delete(key) }
    },
    caches: {
      async keys() { return ['postpartum-runtime-v2', 'postpartum-runtime-v3', 'postpartum-copilot-v3', 'unrelated-cache'] },
      async delete(name) { deleted.push(name); return true }
    }
  }
  let source = fs.readFileSync(path.join(root, 'frontend/src/utils/api.js'), 'utf8')
  source = source.replace('import.meta.env.VITE_API_BASE_URL', 'undefined')
    .replace(/^export const /gm, 'const ')
    .replace('export default api', 'globalThis.reviewApi = api')
  vm.createContext(context)
  vm.runInContext(source, context)
  return { api: context.reviewApi, stored, deleted }
}

test('private API requests never write to Cache Storage', async () => {
  let options
  const worker = workerFixture(async (request, receivedOptions) => {
    options = receivedOptions
    return new Response('{"user":"current"}')
  })
  const response = await worker.fetch(new Request('http://localhost/api/export/json'))
  assert.equal((await response.json()).user, 'current')
  assert.equal(options.cache, 'no-store')
  assert.equal(worker.cacheWrites(), 0)
})

test('offline API requests cannot fall back to a previous account response', async () => {
  const worker = workerFixture(async () => { throw new Error('offline-fixture') })
  await assert.rejects(worker.fetch(new Request('http://localhost/api/export/json')), /offline-fixture/)
})

test('authorization-bearing requests outside /api also bypass caches', async () => {
  const worker = workerFixture(async () => { throw new Error('offline-fixture') })
  await assert.rejects(worker.fetch(new Request('http://localhost/private.json', {
    headers: { Authorization: 'Bearer fixture' }
  })), /offline-fixture/)
})

test('activation removes legacy application caches while preserving unrelated caches', async () => {
  const worker = workerFixture(async () => new Response('sample'))
  let done
  worker.events.activate({ waitUntil(value) { done = value } })
  await done
  assert.deepEqual(worker.deleted.sort(), ['postpartum-copilot-v2', 'postpartum-runtime-v2'])
})

test('logout clears credentials and both legacy/current private caches', async () => {
  const fixture = apiFixture(async () => new Response('{}'))
  fixture.stored.set('access_token', 'old-access')
  fixture.stored.set('refresh_token', 'old-refresh')
  fixture.stored.set('userId', 'previous-account')
  await fixture.api.logout()
  assert.equal(fixture.stored.size, 0)
  assert.deepEqual(fixture.deleted.sort(), ['postpartum-runtime-v2', 'postpartum-runtime-v3'])
})

test('a 2FA-required response does not authenticate or preserve a previous session', async () => {
  const fixture = apiFixture(async () => new Response(JSON.stringify({ requires_2fa: true, access_token: null })))
  fixture.stored.set('access_token', 'previous-access')
  fixture.stored.set('refresh_token', 'previous-refresh')
  const response = await fixture.api.login('review@example.com', 'fixture-password')
  assert.equal(response.requires_2fa, true)
  assert.equal(fixture.api.isAuthenticated(), false)
  assert.equal(fixture.stored.size, 0)
})

test('login forwards the second factor and stores only the completed session', async () => {
  let payload
  const fixture = apiFixture(async (url, options) => {
    payload = JSON.parse(options.body)
    return new Response(JSON.stringify({ access_token: 'current-access', refresh_token: 'current-refresh' }))
  })
  await fixture.api.login('review@example.com', 'fixture-password', '123456')
  assert.equal(payload.verification_token, '123456')
  assert.equal(fixture.stored.get('access_token'), 'current-access')
  assert.equal(fixture.stored.get('refresh_token'), 'current-refresh')
})

test('failed password login surfaces its error without refreshing another session', async () => {
  const calls = []
  const fixture = apiFixture(async url => {
    calls.push(url)
    return new Response(JSON.stringify({ error: { message: 'Incorrect email or password' } }), { status: 401 })
  })
  fixture.stored.set('refresh_token', 'previous-refresh')
  await assert.rejects(fixture.api.login('review@example.com', 'fixture-password'), /Incorrect email or password/)
  assert.equal(calls.length, 1)
})

test('expired /auth/me access can still refresh the verified session', async () => {
  const calls = []
  const fixture = apiFixture(async url => {
    calls.push(url)
    if (url.endsWith('/api/auth/refresh')) {
      return new Response(JSON.stringify({ access_token: 'renewed-access', refresh_token: 'renewed-refresh' }))
    }
    if (calls.length === 1) return new Response('{}', { status: 401 })
    return new Response(JSON.stringify({ user_id: 'current-account' }))
  })
  fixture.stored.set('refresh_token', 'verified-refresh')
  assert.equal((await fixture.api.getCurrentUser()).user_id, 'current-account')
  assert.equal(fixture.stored.get('access_token'), 'renewed-access')
  assert.equal(calls.length, 3)
})

test('disabling second factor clears the previous credentials and requests a new sign-in', async () => {
  let url, unauthorized = 0
  const fixture = apiFixture(async endpoint => {
    url = endpoint
    return new Response(JSON.stringify({ is_enabled: false }))
  })
  fixture.stored.set('access_token', 'old-access')
  fixture.stored.set('refresh_token', 'old-refresh')
  fixture.stored.set('userId', 'review-account')
  fixture.api.setOnUnauthorized(() => { unauthorized++ })
  const response = await fixture.api.disable2FA()
  assert.equal(response.is_enabled, false)
  assert.match(url, /\/api\/security\/2fa\/disable$/)
  assert.equal(fixture.stored.size, 0)
  assert.equal(unauthorized, 1)
})
