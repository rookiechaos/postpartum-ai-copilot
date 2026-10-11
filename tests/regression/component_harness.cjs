// Executes repository JSX with controlled hooks, API calls and browser state.
const fs = require('node:fs')
const path = require('node:path')
const vm = require('node:vm')
const assert = require('node:assert/strict')
const ts = require(process.env.REVIEW_TYPESCRIPT_PATH || 'typescript')
const root = path.resolve(__dirname, '../..')
const flush = () => new Promise(setImmediate)

function harness(file, { api = {}, pathname = '/family', language = 'ja', env = {}, taskManager = {} } = {}) {
  let current
  const stored = new Map(), modules = new Map(), errors = [], events = new Map()
  const translations = JSON.parse(fs.readFileSync(path.join(root, `frontend/src/i18n/locales/${language}.json`), 'utf8'))
  const t = (key, options) => {
    let value = key.split('.').reduce((item, part) => item?.[part], translations)
    if (typeof value !== 'string') value = typeof options === 'string' ? options : key
    return value.replace(/\{\{(\w+)\}\}/g, (_, name) => options?.[name] ?? '')
  }
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
        owner.effects.push(() => { previous?.cleanup?.(); owner.slots[index] = { deps, cleanup: effect() } })
      }
    },
    useRef(initial) {
      const owner = current, index = owner.index++
      if (!owner.slots[index]) owner.slots[index] = { current: initial }
      return owner.slots[index]
    },
  }
  const React = { createElement: (type, props, ...children) => ({ type, props: props || {}, children: children.flat(Infinity) }) }
  const browser = {
    location: { pathname, origin: 'https://example.com' },
    history: { pushState(_state, _title, target) { browser.location.pathname = target } },
    addEventListener(name, fn) { events.set(name, fn) }, removeEventListener(name) { events.delete(name) },
  }
  function load(relative) {
    const absolute = path.resolve(root, relative)
    if (modules.has(absolute)) return modules.get(absolute)
    const source = fs.readFileSync(absolute, 'utf8').replaceAll('import.meta.env', '__env')
    const parsed = ts.createSourceFile(relative, source, ts.ScriptTarget.Latest, true, relative.endsWith('.jsx') ? ts.ScriptKind.JSX : ts.ScriptKind.JS)
    assert.equal(parsed.parseDiagnostics.length, 0, `${relative} must parse`)
    const compiled = ts.transpileModule(source, { compilerOptions: {
      target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.React, esModuleInterop: true,
    } }).outputText
    function fixture(name) {
      if (name === 'react') return { __esModule: true, default: React, ...hooks }
      if (name === 'react-i18next') return { useTranslation: () => ({ t, i18n: { language, resolvedLanguage: language } }) }
      if (name.endsWith('/api')) return { __esModule: true, default: api }
      if (name.endsWith('/taskManager')) return { __esModule: true, default: taskManager }
      if (name.endsWith('/Toast')) return { useToast: () => ({ error: value => errors.push(value), success() {} }) }
      if (name.endsWith('/japanTime') || name.endsWith('/careSummary')) return load(path.relative(root, path.resolve(path.dirname(absolute), `${name}.js`)))
      if (name === 'framer-motion') return { motion: new Proxy({}, { get: (_, key) => `motion.${key}` }), AnimatePresence: 'AnimatePresence' }
      if (name === 'lucide-react') return new Proxy({}, { get: (_, key) => `icon.${key}` })
      if (name === 'recharts') return new Proxy({}, { get: (_, key) => `chart.${key}` })
      return { __esModule: true, default: name }
    }
    const sandbox = {
      exports: {}, require: fixture, __env: { VITE_ASYNC_MODE: 'false', ...env },
      console: { log() {}, error() {} }, Date, Intl, URL, Blob, window: browser, navigator: {},
      localStorage: { getItem: key => stored.get(key) || null, setItem: (key, value) => stored.set(key, value), removeItem: key => stored.delete(key) },
    }
    vm.runInNewContext(compiled, sandbox, { filename: relative })
    modules.set(absolute, sandbox.exports)
    return sandbox.exports
  }
  const component = load(file).default
  return { stored, browser, errors, t, load, events,
    mount(props = {}, target = component) {
      const owner = { slots: [], index: 0, effects: [], mounted: true, lateUpdates: 0 }
      return {
        render() { current = owner; owner.index = 0; const tree = target(props); current = null; owner.effects.splice(0).forEach(effect => effect()); return tree },
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
const find = (tree, predicate) => all(tree).find(node => node && typeof node === 'object' && predicate(node))
const text = tree => all(tree).filter(value => typeof value === 'string' || typeof value === 'number').join(' ')
module.exports = { harness, all, find, text, flush, root }
