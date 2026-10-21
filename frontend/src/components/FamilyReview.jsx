import React, { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../utils/api'
import { japanDateTime } from '../utils/japanTime'
import { CareRecordIdentity } from './CareSubject'
import useConnection from '../utils/useConnection'

export default function FamilyReview({ familyId, visible, refreshKey }) {
  const { t, i18n } = useTranslation()
  const { reconnections } = useConnection()
  const [snapshot, setSnapshot] = useState(null)
  const [checked, setChecked] = useState(false)
  const [loading, setLoading] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  const [expanded, setExpanded] = useState(false)
  const writing = useRef(false)
  const currentVersion = useRef('')
  useEffect(() => {
    if (!visible) return
    let active = true
    setLoading(true); setError('')
    api.get(`/api/families/${familyId}/review`).then(data => {
      if (active) {
        const version = `${data.revision}:${data.digest}`
        if (version !== currentVersion.current) setChecked(false)
        currentVersion.current = version; setSnapshot(data)
      }
    }).catch(() => { if (active) { setError('load'); setSnapshot(null) } }).finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [familyId, visible, attempt, reconnections, refreshKey])
  useEffect(() => {
    if (!visible) return
    const refresh = () => { if (!writing.current) setAttempt(value => value + 1) }
    const timer = setInterval(refresh, 30000)
    window.addEventListener('focus', refresh)
    return () => { clearInterval(timer); window.removeEventListener('focus', refresh) }
  }, [visible])
  const confirm = async () => {
    if (writing.current || !snapshot || !checked || loading) return
    writing.current = true; setBusy(true); setError('')
    try {
      await api.post(`/api/families/${familyId}/review`, { revision: snapshot.revision, digest: snapshot.digest,
        membership_revision: snapshot.membership_revision, confirmed: true })
      setChecked(false); setAttempt(value => value + 1)
    } catch (failure) { setError(failure.status === 409 ? 'conflict' : 'save'); setChecked(false) }
    finally { writing.current = false; setBusy(false) }
  }
  return <section className="family-review support-card"><h4>{t('workflow.handoff.title')}</h4><p>{t('workflow.handoff.notice')}</p>
    {error && <p role="alert">{t(`workflow.handoff.errors.${error}`)}</p>}
    <button type="button" className="text-action" disabled={loading || busy} onClick={() => setAttempt(value => value + 1)}>{t('pilot.retry')}</button>
    {loading && <p role="status">{t('common.loading')}</p>}
    {snapshot && <>
      <p>{snapshot.first_review ? t('workflow.handoff.first') : t('workflow.handoff.since', { time: japanDateTime(snapshot.confirmed_at, i18n.resolvedLanguage || 'ja') })}</p>
      {!snapshot.records.length && !snapshot.notes.length && !snapshot.withdrawn_count && <p>{t('workflow.handoff.none')}</p>}
      <ul className="workflow-records">{(expanded ? snapshot.records : snapshot.records.slice(0, 10)).map(record => <li key={record.record_key}>
        <strong>{t(`workflow.handoff.changes.${record.change}`)} · {t(`tracking.${record.entry_type}`)}</strong>
        <CareRecordIdentity record={record} /><span>{japanDateTime(record.timestamp, i18n.resolvedLanguage || 'ja')} · {record.recorder_label || t('workflow.handoff.familyMember')}</span>
        {record.amount_ml != null && <span>{record.amount_ml} mL</span>}
        {(record.duration_minutes ?? record.sleep_duration_minutes) != null && <span>{record.duration_minutes ?? record.sleep_duration_minutes} {t('pilot.minutes')}</span>}
      </li>)}</ul>
      {snapshot.records.length > 10 && <button type="button" className="text-action" aria-expanded={expanded} onClick={() => setExpanded(value => !value)}>{t(expanded ? 'continuity.work.less' : 'workflow.handoff.showAll', { count: snapshot.records.length })}</button>}
      {snapshot.notes.map(note => <p key={note.author_id}>{t('workflow.handoff.note', { name: note.recorder_label || t('polish.memberNumber', { number: note.recorder_number }), revision: note.revision })}</p>)}
      {snapshot.withdrawn_count > 0 && <p>{t('workflow.handoff.withdrawn', { count: snapshot.withdrawn_count })}</p>}
      <label><input type="checkbox" disabled={loading || busy || error === 'conflict'} checked={checked} onChange={event => setChecked(event.target.checked)} />{t('workflow.handoff.attest')}</label>
      <button type="button" className="pilot-button secondary" disabled={loading || !checked || busy || error === 'conflict'} onClick={confirm}>{t('workflow.handoff.confirm')}</button>
    </>}
  </section>
}
