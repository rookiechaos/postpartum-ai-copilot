// Execute actual transpiled JSX with controlled React hooks and element trees.
// Supply REVIEW_TYPESCRIPT_PATH if TypeScript is not available as a module.
// This exercises component handlers/lifecycles without installing a browser.
const test = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const vm = require('node:vm')
const ts = require(process.env.REVIEW_TYPESCRIPT_PATH || 'typescript')
const root = path.resolve(__dirname, '../..')
const flush = () => new Promise(setImmediate)
const deferred = () => {
  let resolve, reject
  const promise = new Promise((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}

function harness(file, api = {}) {
  let current
  const errors = [], stored = new Map(), stubs = new Map()
  const hooks = {
    useState(initial) {
      const owner = current, index = owner.index++
      if (!owner.slots[index]) owner.slots[index] = { value: typeof initial === 'function' ? initial() : initial }
      const slot = owner.slots[index]
      return [slot.value, value => {
        if (!owner.mounted) owner.lateUpdates++
        slot.value = typeof value === 'function' ? value(slot.value) : value
      }]
    },
    useEffect(effect, deps) {
      const owner = current, index = owner.index++, previous = owner.slots[index]
      if (!previous || !deps || deps.some((value, i) => !Object.is(value, previous.deps[i]))) {
        owner.effects.push(() => {
          previous?.cleanup?.()
          owner.slots[index] = { deps, cleanup: effect() }
        })
      }
    },
  }
  const React = { createElement: (type, props, ...children) => ({ type, props: props || {}, children: children.flat(Infinity) }) }
  function requireFixture(name) {
    if (name === 'react') return { __esModule: true, default: React, ...hooks }
    if (name === 'react-i18next') return { useTranslation: () => ({ t: (key, fallback) => fallback || key, i18n: { language: 'en', resolvedLanguage: 'en' } }) }
    if (name.endsWith('/api')) return { __esModule: true, default: api }
    if (name.endsWith('/Toast')) return { useToast: () => ({ error: message => errors.push(message) }) }
    if (name === 'framer-motion') return { motion: new Proxy({}, { get: (_, key) => `motion.${key}` }), AnimatePresence: 'AnimatePresence' }
    if (name === 'lucide-react') return new Proxy({}, { get: (_, key) => `icon.${key}` })
    if (!stubs.has(name)) stubs.set(name, { __esModule: true, default: name })
    return stubs.get(name)
  }
  const source = fs.readFileSync(path.join(root, file), 'utf8')
  const parsed = ts.createSourceFile(file, source, ts.ScriptTarget.Latest, true, ts.ScriptKind.JSX)
  assert.equal(parsed.parseDiagnostics.length, 0, 'JSX must parse')
  const compiled = ts.transpileModule(source, { compilerOptions: {
    target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.React, esModuleInterop: true,
  } }).outputText
  const context = {
    exports: {}, require: requireFixture,
    console: { log() {}, error() {} }, Date,
    navigator: {}, window: { location: { pathname: '/family' }, history: { pushState() {} }, addEventListener() {}, removeEventListener() {} },
    localStorage: {
      getItem: key => stored.get(key) || null,
      setItem: (key, value) => stored.set(key, value),
    },
  }
  vm.runInNewContext(compiled, context, { filename: file })
  return {
    errors, stored,
    mount(component = context.exports.default, props = {}) {
      const owner = { slots: [], index: 0, effects: [], mounted: true, lateUpdates: 0 }
      return {
        render() {
          current = owner
          owner.index = 0
          const tree = component(props)
          current = null
          owner.effects.splice(0).forEach(effect => effect())
          return tree
        },
        unmount() { owner.mounted = false; owner.slots.forEach(slot => slot?.cleanup?.()) },
        get lateUpdates() { return owner.lateUpdates },
      }
    },
  }
}

function all(tree) {
  if (tree == null || typeof tree === 'boolean') return []
  if (Array.isArray(tree)) return tree.flatMap(all)
  return [tree, ...all(tree.children)]
}
const find = (tree, predicate) => all(tree).find(value => value && typeof value === 'object' && predicate(value))
const text = tree => all(tree).filter(value => typeof value === 'string' || typeof value === 'number').join(' ')
const submit = tree => find(tree, node => node.type === 'form').props.onSubmit({ preventDefault() {} })

test('check-in network errors show an unavailable assessment and retry without a missing toast', async () => {
  let calls = 0
  const h = harness('frontend/src/components/EmotionalCheckIn.jsx', { async postEmotionalCheckin() {
    if (++calls === 1) throw new Error('service unavailable')
    return { analysis_available: true, risk_level: 'high', assessment: 'Contact your care team.', escalation_needed: true }
  } })
  const component = h.mount(undefined, { userId: 'review_a' })
  find(component.render(), node => node.type === './AIUseNotice').props.onChange(true)
  await submit(component.render())
  const failed = component.render()
  assert.equal(h.errors.length, 1)
  assert.match(text(failed), /pilot.checkinUnavailable/)
  assert.doesNotMatch(text(failed), /Risk Level:\s+LOW/)
  const retry = find(failed, node => node.type === 'button' && text(node) === 'pilot.retry')
  assert.equal(retry.props.disabled, false)
  await retry.props.onClick({ preventDefault() {} })
  assert.match(text(component.render()), /Contact your care team/)
  assert.doesNotMatch(text(component.render()), /Risk Level:/)
})

test('provider failures returned as JSON never render a low-risk badge', async () => {
  const h = harness('frontend/src/components/EmotionalCheckIn.jsx', { async postEmotionalCheckin() {
    return { analysis_available: false, risk_level: 'unknown', escalation_needed: null, assessment: 'Please try again.' }
  } })
  const component = h.mount(undefined, { userId: 'review_a' })
  find(component.render(), node => node.type === './AIUseNotice').props.onChange(true)
  await submit(component.render())
  assert.match(text(component.render()), /pilot.checkinUnavailable/)
  assert.doesNotMatch(text(component.render()), /Risk Level:/)
})

function appHarness({ initialUser = 'review_a', bootstrap } = {}) {
  const listeners = new Set(), contexts = new Map()
  let unauthorized, logouts = 0
  const api = {
    onAuthChange(callback) { listeners.add(callback); return () => listeners.delete(callback) },
    setOnUnauthorized(callback) { unauthorized = callback },
    isAuthenticated: () => true,
    getUserId: () => initialUser,
    getCurrentUser: () => bootstrap.promise,
    setUserId() {},
    logout() { logouts++; listeners.forEach(callback => callback({ preserveTasks: false })) },
    getUserContext(user) {
      if (!contexts.has(user)) contexts.set(user, deferred())
      return contexts.get(user).promise
    },
    updateUserContext: async () => { throw new Error('save failed') },
  }
  const h = harness('frontend/src/App.jsx', api)
  h.stored.set('hasCompletedWelcome:review_a', 'true')
  h.stored.set('hasCompletedWelcome:review_b', 'true')
  return { ...h, contexts, api, listeners, get logouts() { return logouts },
    emit(change = { preserveTasks: false }) { listeners.forEach(callback => callback(change)) },
    unauthorized() { unauthorized() },
  }
}

test('account changes remount private page state and discard the previous context request', async () => {
  const h = appHarness(), app = h.mount()
  app.render() // Initialize account A.
  const accountA = app.render()
  const privateA = h.mount(accountA.type, accountA.props)
  privateA.render()
  h.emit()
  const signedOut = app.render()
  assert.equal(signedOut.type, './components/Auth')
  privateA.unmount() // React removes the old subtree on sign-out.
  signedOut.props.onSuccess('review_b')
  const accountB = app.render()
  assert.notEqual(accountB.props.key, accountA.props.key)
  const privateB = h.mount(accountB.type, accountB.props)
  privateB.render()
  h.contexts.get('review_a').resolve({ babyName: 'private-a' })
  await flush()
  assert.equal(privateA.lateUpdates, 0)
  let dashboard = find(privateB.render(), node => node.type === './components/Dashboard')
  assert.equal(dashboard.props.userContext, null)
  h.contexts.get('review_b').resolve({ babyName: 'private-b' })
  await flush()
  dashboard = find(privateB.render(), node => node.type === './components/Dashboard')
  assert.equal(dashboard.props.userContext.babyName, 'private-b')
  app.unmount()
  privateB.unmount()
})

test('same-account token refresh preserves the mounted private account', () => {
  const h = appHarness(), app = h.mount()
  app.render()
  const before = app.render()
  h.emit({ preserveTasks: true })
  const after = app.render()
  assert.equal(after.props.key, before.props.key)
  assert.equal(after.props.userId, 'review_a')
  app.unmount()
})

for (const failed of [false, true]) {
  test(`late authentication bootstrap ${failed ? 'failure' : 'success'} cannot replace the new login`, async () => {
    const bootstrap = deferred()
    const h = appHarness({ initialUser: null, bootstrap }), app = h.mount()
    app.render()
    h.emit()
    app.render().props.onSuccess('review_b')
    if (failed) bootstrap.reject(new Error('old login failed'))
    else bootstrap.resolve({ user_id: 'review_a' })
    await flush()
    assert.equal(app.render().props.userId, 'review_b')
    assert.equal(h.logouts, 0)
    app.unmount()
  })
}

test('welcome completion waits for persistence before recording completion', async () => {
  const h = appHarness(), app = h.mount()
  h.stored.delete('hasCompletedWelcome:review_a')
  app.render()
  const account = app.render(), privateApp = h.mount(account.type, account.props)
  privateApp.render()
  const welcome = privateApp.render()
  assert.equal(welcome.type, './components/WelcomeScreen')
  await assert.rejects(welcome.props.onComplete({ babyName: 'sample' }), /save failed/)
  assert.equal(h.stored.has('hasCompletedWelcome:review_a'), false)
  assert.equal(privateApp.render().type, './components/WelcomeScreen')
  privateApp.unmount()
  app.unmount()
})

test('welcome save errors stay on screen and allow another attempt', async () => {
  const h = harness('frontend/src/components/WelcomeScreen.jsx')
  const component = h.mount(undefined, { onComplete: async () => { throw new Error('save failed') } })
  const next = find(component.render(), node => node.type === 'button' && text(node) === 'welcome.next')
  next.props.onClick()
  const skip = find(component.render(), node => node.type === 'button' && text(node) === 'welcome.skip')
  skip.props.onClick()
  await flush()
  const failed = component.render()
  assert.match(text(find(failed, node => node.props.role === 'alert')), /Unable to save/)
  assert.equal(find(failed, node => node.type === 'button' && text(node) === 'welcome.skip').props.disabled, false)
})
