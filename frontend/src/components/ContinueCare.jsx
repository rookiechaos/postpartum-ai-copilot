import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../utils/api'
import { useCareSession, journeysChanged } from '../utils/CareSession'
import { japanDateTime } from '../utils/japanTime'
import useConnection from '../utils/useConnection'
import { CareRecordIdentity } from './CareSubject'

export default function ContinueCare({ visible, refreshKey, onNavigate }) {
  const { t, i18n } = useTranslation()
  const { work, subjects } = useCareSession()
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
    Promise.allSettled([api.get('/api/support-journeys'), api.get('/api/drafts/record')]).then(([progress, draft]) => {
      if (!active) return
      if (progress.status === 'fulfilled') setJourneys(progress.value)
      if (draft.status === 'fulfilled') setRecordDraft(draft.value.draft)
      setError(progress.status === 'rejected' || draft.status === 'rejected')
    })
    return () => { active = false }
  }, [visible, refreshKey, reconnections, attempt])
  useEffect(() => {
    const refresh = () => setAttempt(value => value + 1)
    window.addEventListener(journeysChanged, refresh); window.addEventListener('focus', refresh)
    return () => { window.removeEventListener(journeysChanged, refresh); window.removeEventListener('focus', refresh) }
  }, [])
  const items = Object.entries(work).map(([key, item]) => ({ key, ...item }))
  if (!work.record && recordDraft) items.push({ key: 'record-recovery', version: recordDraft.updated_at,
    title: 'continuity.work.recordRecovery', priority: 3, tab: 'tracking', detail: { action: 'resume' }, action: 'workflow.work.restore' })
  journeys.filter(row => !row.cleared && !['completed', 'paused'].includes(row.state)).forEach(row => {
    items.push({ key: `journey:${row.contact_key}`, version: String(row.revision),
      title: row.next_contact_at ? 'continuity.work.contactPlan' : row.state === 'waiting' ? 'continuity.work.waiting'
        : row.state === 'booked' ? 'continuity.work.contactBooked' : 'continuity.work.contactDraft',
      time: row.next_contact_at, contactName: row.contact_name, action: row.state === 'booked' ? 'workflow.work.prepareContact' : 'workflow.work.contactNext',
      priority: 4, tab: 'support', detail: { view: 'contacts', contactKey: row.contact_key } })
  })
  const shown = items.filter(item => item.critical || dismissed[item.key] !== item.version).sort((a, b) => a.priority - b.priority ||
    (a.time && b.time ? new Date(a.time).getTime() - new Date(b.time).getTime() : 0))
  const critical = shown.filter(item => item.critical)
  const initial = [...critical, ...shown.filter(item => !item.critical).slice(0, Math.max(0, 2 - critical.length))]
  const moreCount = shown.length - initial.length
  if (!shown.length && !error) return null
  return <section className="pilot-panel continue-care"><h3>{t('continuity.work.title')}</h3><p>{t('continuity.work.notice')}</p>
    {(expanded ? shown : initial).map(item => <article key={item.key}>
      <strong>{t(item.title)}</strong>
      {item.entryType && <p>{t(`tracking.${item.entryType}`)} · <CareRecordIdentity record={{ entry_type: item.entryType, subject_id: item.subjectId }} /></p>}
      {!item.entryType && item.subjectId && <p>{t('workflow.context.subject', { name: subjects.find(subject => subject.subject_id === item.subjectId)?.nickname || t('continuity.subject.unavailable') })}</p>}
      {item.contactName && <p>{item.contactName}</p>}
      {item.time && <p>{japanDateTime(item.time, i18n.resolvedLanguage || 'ja')} · {t('pilot.japanTime')}</p>}
      <div className="pilot-actions"><button type="button" className="pilot-button secondary" onClick={() => onNavigate(item.tab, item.detail)}>{t(item.action || 'continuity.work.open')}</button>
        {!item.critical && <button type="button" className="text-action" onClick={() => setDismissed(previous => ({ ...previous, [item.key]: item.version }))}>{t('continuity.work.hide')}</button>}</div>
    </article>)}
    {moreCount > 0 && <button type="button" className="text-action" aria-expanded={expanded} onClick={() => setExpanded(value => !value)}>{t(expanded ? 'continuity.work.less' : 'continuity.work.more', { count: moreCount })}</button>}
    {error && <p role="status">{t('continuity.work.loadError')} <button type="button" className="text-action" onClick={() => setAttempt(value => value + 1)}>{t('pilot.retry')}</button></p>}
  </section>
}
