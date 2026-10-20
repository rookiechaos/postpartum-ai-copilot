import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../utils/api'
import { useCareSession, journeysChanged } from '../utils/CareSession'
import { japanDateTime } from '../utils/japanTime'
import useConnection from '../utils/useConnection'

export default function ContinueCare({ visible, refreshKey, onNavigate }) {
  const { t, i18n } = useTranslation()
  const { work } = useCareSession()
  const { reconnections } = useConnection()
  const [journeys, setJourneys] = useState([])
  const [recordDraft, setRecordDraft] = useState(null)
  const [dismissed, setDismissed] = useState({})
  const [expanded, setExpanded] = useState(false)
  const [attempt, setAttempt] = useState(0)
  const [error, setError] = useState(false)
  useEffect(() => {
    if (!visible) return
    let active = true
    Promise.all([api.get('/api/support-journeys'), api.get('/api/drafts/record')]).then(([progress, draft]) => {
      if (active) { setJourneys(progress); setRecordDraft(draft.draft); setError(false) }
    }).catch(() => { if (active) setError(true) })
    return () => { active = false }
  }, [visible, refreshKey, reconnections, attempt])
  useEffect(() => {
    const refresh = () => setAttempt(value => value + 1)
    window.addEventListener(journeysChanged, refresh); window.addEventListener('focus', refresh)
    return () => { window.removeEventListener(journeysChanged, refresh); window.removeEventListener('focus', refresh) }
  }, [])
  const items = Object.entries(work).map(([key, item]) => ({ key, ...item }))
  if (!work.record && recordDraft) items.push({ key: 'record-recovery', version: recordDraft.updated_at,
    title: 'continuity.work.recordRecovery', priority: 3, tab: 'tracking', detail: { action: 'resume' } })
  journeys.filter(row => !row.cleared && !['completed', 'paused'].includes(row.state)).forEach(row => {
    items.push({ key: `journey:${row.contact_key}`, version: String(row.revision),
      title: row.next_contact_at ? 'continuity.work.contactPlan' : row.state === 'waiting' ? 'continuity.work.waiting'
        : row.state === 'booked' ? 'continuity.work.contactBooked' : 'continuity.work.contactDraft',
      time: row.next_contact_at, priority: 4, tab: 'support', detail: { view: 'contacts', contactKey: row.contact_key } })
  })
  const shown = items.filter(item => dismissed[item.key] !== item.version).sort((a, b) => a.priority - b.priority)
  if (!shown.length && !error) return null
  return <section className="pilot-panel continue-care"><h3>{t('continuity.work.title')}</h3><p>{t('continuity.work.notice')}</p>
    {(expanded ? shown : shown.slice(0, 2)).map(item => <article key={item.key}>
      <strong>{t(item.title)}</strong>{item.time && <p>{japanDateTime(item.time, i18n.resolvedLanguage || 'ja')} · {t('pilot.japanTime')}</p>}
      <div className="pilot-actions"><button type="button" className="pilot-button secondary" onClick={() => onNavigate(item.tab, item.detail)}>{t('continuity.work.open')}</button>
        <button type="button" className="text-action" onClick={() => setDismissed(previous => ({ ...previous, [item.key]: item.version }))}>{t('continuity.work.hide')}</button></div>
    </article>)}
    {shown.length > 2 && <button type="button" className="text-action" aria-expanded={expanded} onClick={() => setExpanded(value => !value)}>{t(expanded ? 'continuity.work.less' : 'continuity.work.more', { count: shown.length - 2 })}</button>}
    {error && <p role="status">{t('continuity.work.loadError')} <button type="button" className="text-action" onClick={() => setAttempt(value => value + 1)}>{t('pilot.retry')}</button></p>}
  </section>
}
