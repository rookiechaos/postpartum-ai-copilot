const test = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const { harness, all, find, text, flush, root } = require('./component_harness.cjs')
const event = { preventDefault() {} }
const button = (tree, caption) => find(tree, node => node.type === 'button' && text(node) === caption)
const consent = tree => find(tree, node => node.type === './AIUseNotice').props.onChange(true)

test('public entrance routes families and organizations without granting a role', () => {
  const h = harness('frontend/src/App.jsx', { pathname: '/', api: {
    onAuthChange: () => () => {}, setOnUnauthorized() {}, isAuthenticated: () => false,
  } })
  const app = h.mount()
  app.render()
  assert.equal(app.render().type, './components/EntryScreen')
  app.render().props.onChoose('organization')
  assert.equal(h.browser.location.pathname, '/organization')
  assert.equal(app.render().type, './components/Auth')
  assert.equal(app.render().props.entry, 'organization')
  app.render().props.onBack()
  app.render().props.onChoose('family')
  assert.equal(app.render().props.entry, 'family')
  app.unmount()
})

test('organization URL mounts only the organization workspace after authentication', () => {
  const h = harness('frontend/src/App.jsx', { pathname: '/organization', api: {
    onAuthChange: () => () => {}, setOnUnauthorized() {}, isAuthenticated: () => true, getUserId: () => 'sample_staff',
  } })
  const app = h.mount()
  app.render()
  assert.equal(app.render().type, './components/OrganizationPortal')
  app.render().props.onFamily()
  assert.equal(typeof app.render().type, 'function')
  assert.equal(h.browser.location.pathname, '/family')
  app.unmount()
})

test('welcome completion is scoped to each account and opens the first record', async () => {
  const h = harness('frontend/src/App.jsx', { api: {
    onAuthChange: () => () => {}, setOnUnauthorized() {}, isAuthenticated: () => true, getUserId: () => 'new_person',
    updateUserContext: async (_id, value) => ({ context: value }),
  } })
  h.stored.set('hasCompletedWelcome', 'true') // A legacy shared-device flag must not suppress welcome.
  h.stored.set('hasCompletedWelcome:other_person', 'true')
  const app = h.mount()
  app.render()
  const account = app.render(), family = h.mount(account.props, account.type)
  family.render()
  assert.equal(family.render().type, './components/WelcomeScreen')
  await family.render().props.onComplete({ babyName: '' })
  assert.equal(h.stored.get('hasCompletedWelcome:new_person'), 'true')
  assert.equal(find(family.render(), node => node.type === './components/TrackingPanel').props.initialEntryType, 'feeding')
  family.unmount()
  app.unmount()
})

test('home actions work even with no records and do not make AI requests', async () => {
  const navigation = [], requests = []
  const h = harness('frontend/src/components/Dashboard.jsx', { api: { async getTracking(...args) { requests.push(args); return [] } } })
  const home = h.mount({ userId: 'sample_family', onNavigate: (...args) => navigation.push(args), onNightMode() {} })
  home.render()
  await flush()
  const tree = home.render()
  button(tree, h.t('tracking.diaper')).props.onClick()
  assert.deepEqual(navigation.pop(), ['tracking', 'diaper'])
  button(tree, h.t('pilot.scenes.rest')).props.onClick()
  assert.deepEqual(navigation.pop(), ['chat', h.t('pilot.questions.rest')])
  assert.equal(requests.length, 1)
  assert.doesNotMatch(text(tree), /正常|stable|100%/)
})

test('tracking opens the requested form and preserves input on failed save', async () => {
  const h = harness('frontend/src/components/TrackingPanel.jsx', { api: {
    getTracking: async () => [], addTrackingEntry: async () => { throw new Error('offline') },
  } })
  const panel = h.mount({ userId: 'sample_family', initialEntryType: 'feeding' })
  let tree = panel.render()
  const formNode = find(tree, node => typeof node.type === 'function')
  assert.equal(formNode.props.entryType, 'feeding')
  const form = h.mount(formNode.props, formNode.type)
  find(form.render(), node => node.type === 'input' && node.props.type === 'number').props.onChange({ target: { value: '15' } })
  find(form.render(), node => node.type === 'form').props.onSubmit(event)
  await flush()
  assert.equal(find(form.render(), node => node.type === 'input' && node.props.type === 'number').props.value, 15)
  assert.ok(find(panel.render(), node => typeof node.type === 'function'))
  assert.equal(h.errors.length, 1)
})

test('situation questions are drafts and direct submission cannot bypass AI acknowledgement', async () => {
  let sends = 0
  const h = harness('frontend/src/components/ChatInterface.jsx', { api: { async post() {
    sends++
    return { response: '次の相談を整理しましょう。', suggestions: ['相談先を確認'], validation: { summary: { all_safe: true, average_confidence: 1 } } }
  } } })
  const chat = h.mount({ userId: 'sample_family' })
  button(chat.render(), h.t('pilot.scenes.rest')).props.onClick()
  let tree = chat.render()
  assert.equal(find(tree, node => node.type === 'input').props.value, h.t('pilot.questions.rest'))
  await find(tree, node => node.type === 'form').props.onSubmit(event)
  assert.equal(sends, 0)
  consent(tree)
  await find(chat.render(), node => node.type === 'form').props.onSubmit(event)
  tree = chat.render()
  assert.equal(sends, 1)
  assert.match(text(tree), /AIが生成/)
  assert.doesNotMatch(text(tree), /検証済み|信頼度|100%/)
})

test('emotional reflection never renders a clinical risk or certainty badge', async () => {
  const h = harness('frontend/src/components/EmotionalCheckIn.jsx', { api: { postEmotionalCheckin: async () => ({
    analysis_available: true, risk_level: 'low', assessment: '少し休むことについて整理しましょう。', suggestions: [],
  }) } })
  const checkin = h.mount({ userId: 'sample_family' })
  consent(checkin.render())
  await find(checkin.render(), node => node.type === 'form').props.onSubmit(event)
  const tree = checkin.render()
  assert.match(text(tree), /AIが生成/)
  assert.doesNotMatch(text(tree), /Risk Level|LOW|低リスク/)
})

test('connection errors and static greetings are not labeled as generated AI answers', async () => {
  const h = harness('frontend/src/components/ChatInterface.jsx', { api: { post: async () => { throw new Error('offline') } } })
  const chat = h.mount({ userId: 'sample_family', initialDraft: '相談したいです' })
  assert.equal(find(chat.render(), node => node.props.className === 'ai-label'), undefined)
  consent(chat.render())
  await find(chat.render(), node => node.type === 'form').props.onSubmit(event)
  assert.match(text(chat.render()), /回答を取得できません/)
  assert.equal(find(chat.render(), node => node.props.className === 'ai-label'), undefined)
})

test('charts preserve missing mood data and honor the selected number of Japan calendar days', async () => {
  const h = harness('frontend/src/components/Charts.jsx', { api: { getTracking: async () => [
    { entry_type: 'mood', mood_level: 'low', timestamp: new Date().toISOString() },
  ] } })
  const charts = h.mount({ userId: 'sample_family' })
  charts.render()
  await flush()
  const data = find(charts.render(), node => node.type === 'chart.LineChart').props.data
  assert.equal(data.length, 7)
  assert.equal(data.filter(day => day.mood === null).length, 6)
  assert.equal(data.filter(day => day.mood === 2).length, 1)
  find(charts.render(), node => node.type === 'select').props.onChange({ target: { value: '3' } })
  charts.render()
  await flush()
  assert.equal(find(charts.render(), node => node.type === 'chart.LineChart').props.data.length, 3)
})

test('national contacts stay visible when the directory API is down', async () => {
  const h = harness('frontend/src/components/SupportDirectory.jsx', { api: { get: async () => { throw new Error('offline') } } })
  const directory = h.mount()
  directory.render()
  await flush()
  const tree = directory.render()
  assert.ok(find(tree, node => node.props.href === 'tel:119'))
  assert.ok(find(tree, node => node.props.href === 'tel:%238000'))
  assert.match(text(tree), /実施地域|対象年齢/)
  assert.match(text(tree), /読み込めません/)
  assert.doesNotMatch(text(tree), /911|988/)
})

test('mood charts use the latest daily record regardless of API ordering and timestamp offset', async () => {
  for (const newestFirst of [true, false]) {
    const h = harness('frontend/src/components/Charts.jsx', { api: { getTracking: async () => {
      const { japanDay } = h.load('frontend/src/utils/japanTime.js')
      const day = japanDay()
      const newer = { entry_type: 'mood', mood_level: 'low',
        timestamp: new Date(`${day}T10:00:00+09:00`).toISOString().replace(/Z$/, '') }
      const older = { entry_type: 'mood', mood_level: 'good', timestamp: `${day}T07:00:00+09:00` }
      return newestFirst ? [newer, older] : [older, newer]
    } } })
    const charts = h.mount({ userId: 'sample_family' })
    charts.render()
    await flush()
    const data = find(charts.render(), node => node.type === 'chart.LineChart').props.data
    assert.equal(data.at(-1).mood, 2)
  }
})

test('a latest mood record without a value remains missing instead of showing an older mood', async () => {
  const h = harness('frontend/src/components/Charts.jsx', { api: { getTracking: async () => {
    const { japanDay } = h.load('frontend/src/utils/japanTime.js')
    const day = japanDay()
    return [
      { entry_type: 'mood', mood_level: null, timestamp: `${day}T10:00:00+09:00` },
      { entry_type: 'mood', mood_level: 'good', timestamp: `${day}T07:00:00+09:00` },
      { entry_type: 'feeding', timestamp: `${day}T06:00:00+09:00` },
    ]
  } } })
  const charts = h.mount({ userId: 'sample_family' })
  charts.render()
  await flush()
  const data = find(charts.render(), node => node.type === 'chart.LineChart').props.data
  assert.equal(data.at(-1).mood, null)
})

test('sleep charts show daily recorded totals rather than averages per entry', async () => {
  const h = harness('frontend/src/components/Charts.jsx', { api: { getTracking: async () => {
    const { japanDay } = h.load('frontend/src/utils/japanTime.js')
    const day = japanDay()
    return [
      { entry_type: 'sleep', sleep_duration_minutes: 90, timestamp: `${day}T10:00:00+09:00` },
      { entry_type: 'sleep', sleep_duration_minutes: 30, timestamp: `${day}T07:00:00+09:00` },
    ]
  } } })
  const charts = h.mount({ userId: 'sample_family' })
  charts.render()
  await flush()
  const data = find(charts.render(), node => node.type === 'chart.LineChart').props.data
  assert.equal(data.at(-1).sleepMinutes, 120)
  assert.equal(data.at(-2).sleepMinutes, 0)
})

test('ordinary accounts see an access request instead of the organization editor', async () => {
  const h = harness('frontend/src/components/OrganizationPortal.jsx', { api: { get: async () => { throw { status: 403 } } } })
  const portal = h.mount({ userId: 'sample_family' })
  portal.render()
  await flush()
  const tree = portal.render()
  assert.equal(find(tree, node => node.type === 'form'), undefined)
  assert.equal(find(tree, node => node.type === 'input').props.value, 'sample_family')
  assert.match(text(tree), /編集権限が必要/)
})

test('authorized organization editor saves actual public profile and refreshes its preview', async () => {
  const profile = { name: '支援拠点', municipality: '', contact: '', hours: '', retention_notice: '', resources: [] }
  const saved = []
  const h = harness('frontend/src/components/OrganizationPortal.jsx', { api: {
    get: async () => ({ profile }), post: async (url, value) => { saved.push([url, value]); return { profile: value } },
  } })
  const portal = h.mount({ userId: 'sample_staff' })
  portal.render()
  await flush()
  await find(portal.render(), node => node.type === 'form').props.onSubmit(event)
  const tree = portal.render()
  assert.equal(saved[0][0], '/api/pilot/organization')
  assert.equal(saved[0][1].name, '支援拠点')
  assert.match(text(tree), /保存しました/)
  assert.equal(find(tree, node => node.type === './SupportDirectory').props.key, 1)
})

test('summary uses an allowlist and separate opt-ins for parent records and notes', () => {
  const h = harness('frontend/src/components/ShareSummary.jsx')
  const { buildCareSummary } = h.load('frontend/src/utils/careSummary.js')
  const base = { timestamp: '2026-10-10T15:30:00Z', user_id: 'private-identity', email: 'private-email-marker' }
  const entries = [
    { ...base, entry_type: 'feeding', amount_ml: 90, weight_kg: 55, notes: 'private-care-note', mood_notes: 'private-mood-note' },
    { ...base, entry_type: 'mood', mood_level: 'low', mood_notes: 'private-mood-note' },
    { ...base, entry_type: 'recovery', weight_kg: 55, recovery_notes: 'private-recovery-note' },
    { ...base, entry_type: 'unknown', notes: 'private-unknown' },
  ]
  const basic = buildCareSummary(entries, { t: h.t })
  assert.match(basic, /90 mL/)
  assert.doesNotMatch(basic, /private-|55 kg|自分の気分/)
  const notesOnly = buildCareSummary(entries, { t: h.t, includeNotes: true })
  assert.match(notesOnly, /private-care-note/)
  assert.doesNotMatch(notesOnly, /private-mood-note|private-recovery-note|55 kg/)
  const parentsOnly = buildCareSummary(entries, { t: h.t, includeParent: true })
  assert.match(parentsOnly, /55 kg/)
  assert.doesNotMatch(parentsOnly, /private-/)
  const both = buildCareSummary(entries, { t: h.t, includeParent: true, includeNotes: true })
  assert.match(both, /private-mood-note|private-recovery-note/)
  assert.doesNotMatch(both, /private-identity|private-email-marker|private-unknown/)
})

test('clearing optional organization resource text preserves empty strings and permits publishing', async () => {
  const profile = { name: '支援拠点', municipality: '', contact: '', hours: '', retention_notice: '', resources: [
    { name: '資料', url: 'https://example.com', description: '説明', hours: '受付時間', checked_on: '2026-01-01' },
  ] }
  let saved
  const h = harness('frontend/src/components/OrganizationPortal.jsx', { api: {
    get: async () => ({ profile }), post: async (_url, value) => { saved = value; return { profile: value } },
  } })
  const portal = h.mount({ userId: 'sample_staff' })
  portal.render()
  await flush()
  for (const index of [2, 3, 4]) {
    const resource = find(portal.render(), node => node.type === 'fieldset')
    all(resource).filter(node => node?.type === 'input')[index].props.onChange({ target: { value: '' } })
  }
  await find(portal.render(), node => node.type === 'form').props.onSubmit(event)
  assert.equal(saved.resources[0].description, '')
  assert.equal(saved.resources[0].hours, '')
  assert.equal(saved.resources[0].checked_on, null)
  assert.equal(saved.resources[0].name, '資料')
  assert.equal(saved.resources[0].url, 'https://example.com')
  assert.match(text(portal.render()), /保存しました/)
})

test('changing summary choices invalidates the previous preview', async () => {
  const h = harness('frontend/src/components/ShareSummary.jsx', { api: { getTracking: async () => [
    { timestamp: '2026-10-10T15:30:00Z', entry_type: 'feeding', amount_ml: 90 },
  ] } })
  const summary = h.mount({ userId: 'sample_family' })
  await button(summary.render(), h.t('pilot.prepareSummary')).props.onClick()
  assert.ok(find(summary.render(), node => node.type === 'textarea'))
  find(summary.render(), node => node.type === 'input').props.onChange({ target: { checked: true } })
  assert.equal(find(summary.render(), node => node.type === 'textarea'), undefined)
})

test('Japan dates handle midnight and UTC timestamps lacking an explicit suffix', () => {
  const h = harness('frontend/src/components/Dashboard.jsx')
  const { japanDay, japanDateTime } = h.load('frontend/src/utils/japanTime.js')
  assert.equal(japanDay('2026-10-10T14:59:59Z'), '2026-10-10')
  assert.equal(japanDay('2026-10-10T15:00:00Z'), '2026-10-11')
  assert.equal(japanDay('2026-10-10T15:00:00'), '2026-10-11')
  assert.match(japanDateTime('2026-10-10T15:30:00Z', 'ja'), /0:30/)
})

test('Japanese and English translation keys cover the same active product flows', () => {
  const leaves = (value, prefix = '') => Object.entries(value).flatMap(([key, child]) => {
    const full = prefix ? `${prefix}.${key}` : key
    return typeof child === 'object' ? leaves(child, full) : [full]
  })
  const read = language => JSON.parse(fs.readFileSync(path.join(root, `frontend/src/i18n/locales/${language}.json`), 'utf8'))
  assert.deepEqual(leaves(read('ja')).sort(), leaves(read('en')).sort())
})
