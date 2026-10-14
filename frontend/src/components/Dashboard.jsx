import React, { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../utils/api'
import { japanDay, japanDateTime } from '../utils/japanTime'
import { recordOperation, isRecordOperation } from '../utils/recordOperations'
import RecordingExample from './RecordingExample'
import FamilyCareOverview from './FamilyCareOverview'
import useConnection from '../utils/useConnection'
import useAccountDraft from '../utils/useAccountDraft'
import { DraftRecoveryNotice } from './DraftRecovery'
import './Dashboard.css'

const quickChoices = [
  ['wet', { entry_type: 'diaper', diaper_type: 'wet' }],
  ['dirty', { entry_type: 'diaper', diaper_type: 'dirty' }],
  ['breast', { entry_type: 'feeding', feeding_type: 'breast' }],
  ['formula', { entry_type: 'feeding', feeding_type: 'formula' }],
]

export default function Dashboard({ userId, userContext, onNavigate, onRecordsChanged, refreshKey = 0, visible = true }) {
  const { t, i18n } = useTranslation()
  const { online, reconnections } = useConnection()
  const [entries, setEntries] = useState(null)
  const [recent, setRecent] = useState([])
  const [error, setError] = useState(false)
  const [attempt, setAttempt] = useState(0)
  const [pending, setPending] = useState(null)
  const [saveStatus, setSaveStatus] = useState('')
  const [undo, setUndo] = useState(null)
  const writing = useRef(false)
  // A later offline/rejected retry cannot disprove an earlier dispatched save.
  const unconfirmedRequest = useRef(null)
  const draft = useAccountDraft('quick', userId, pending ? { pending } : null, content => {
    if (!isRecordOperation(content.pending)) return false
    unconfirmedRequest.current = content.pending.request_key
    setPending(content.pending); setSaveStatus('unconfirmed')
  })
  const refresh = () => { setAttempt(value => value + 1); onRecordsChanged?.() }

  useEffect(() => {
    if (!visible) return
    let active = true
    setError(false)
    Promise.all([api.getTracking(userId, 2), api.get(`/api/tracking/${userId}/recent`)]).then(([today, latest]) => {
      if (active) { setEntries(today.filter(entry => japanDay(entry.timestamp) === japanDay())); setRecent(latest) }
    }).catch(() => { if (active) setError(true) })
    return () => { active = false }
  }, [userId, attempt, refreshKey, visible, reconnections])
  useEffect(() => {
    if (!visible) return
    const update = () => setAttempt(value => value + 1)
    const onVisibility = () => { if (document.visibilityState === 'visible') update() }
    const midnight = new Date(`${japanDay()}T00:00:00+09:00`).getTime() + 86400000
    const timer = setTimeout(update, Math.max(1000, midnight - Date.now() + 100))
    window.addEventListener('focus', update)
    document.addEventListener('visibilitychange', onVisibility)
    return () => { clearTimeout(timer); window.removeEventListener('focus', update); document.removeEventListener('visibilitychange', onVisibility) }
  }, [visible, attempt])
  useEffect(() => {
    if (!undo) return
    const timer = setTimeout(() => setUndo(null), 8000)
    return () => clearTimeout(timer)
  }, [undo])

  const saveQuick = async operation => {
    if (writing.current) return
    if (!online || navigator.onLine === false) {
      setPending(operation)
      setSaveStatus(unconfirmedRequest.current === operation.request_key ? 'unconfirmed' : 'offline')
      return
    }
    writing.current = true
    setPending(operation); setSaveStatus('saving')
    try {
      const result = await api.addTrackingEntry(operation)
      await draft.clear()
      unconfirmedRequest.current = null
      setUndo(result); setPending(null); setSaveStatus('saved'); refresh()
    } catch (failure) {
      if (!(failure.status >= 400 && failure.status < 500)) unconfirmedRequest.current = operation.request_key
      setSaveStatus(unconfirmedRequest.current === operation.request_key ? 'unconfirmed' : 'unsaved')
      setAttempt(value => value + 1)
    }
    finally { writing.current = false }
  }
  const undoQuick = async () => {
    if (writing.current || !undo || pending) return
    writing.current = true; setSaveStatus('saving')
    try { await api.deleteTrackingEntry(undo.id, undo); setUndo(null); setSaveStatus('undone'); refresh() }
    catch { setSaveStatus('undoFailed'); setAttempt(value => value + 1) }
    finally { writing.current = false }
  }

  return <div className="dashboard family-dashboard">
    <header className="dashboard-header"><div><h2>{t('pilot.familyHeading')}</h2>
      <p>{userContext?.babyName ? t('dashboard.howIsBaby', { name: userContext.babyName }) : t('pilot.todayIntro')}</p></div></header>
    <section className="pilot-panel quick-record-panel"><h3>{t('polish.recordNow')}</h3><p>{t('polish.quickNotice')}</p>
      <div className="record-choices">{quickChoices.map(([key, data]) => <button type="button" key={key}
        className="pilot-button" disabled={Boolean(pending) || Boolean(draft.candidate) || draft.status === 'loading' || saveStatus === 'saving'}
        onClick={() => saveQuick(recordOperation(data))}>{t(`polish.quick.${key}`)}</button>)}</div>
      {saveStatus && <p role="status">{t(['offline', 'unconfirmed'].includes(saveStatus) ? `flows.connection.${saveStatus}Save` : `polish.saveStatus.${saveStatus}`)}</p>}
      <DraftRecoveryNotice draft={draft} disabled={saveStatus === 'saving'} compact />
      {pending && saveStatus !== 'saving' && <div className="pilot-actions"><p>{t('polish.pendingWriteNotice')}</p>
        <button className="pilot-button secondary" onClick={() => saveQuick(pending)}>{t('polish.retrySameSave')}</button>
        <button className="pilot-button secondary" onClick={() => {
          if (window.confirm(t('polish.abandonWrite'))) { unconfirmedRequest.current = null; setPending(null); draft.clear(); setSaveStatus(''); refresh() }
        }}>{t('polish.checkBeforeNew')}</button></div>}
      {undo && <button className="pilot-button secondary" disabled={Boolean(pending) || saveStatus === 'saving'} onClick={undoQuick}>{t('polish.undoQuick')}</button>}
      <button className="pilot-button secondary" onClick={() => onNavigate('tracking', 'feeding')}>{t('polish.detailedRecord')}</button>
      <p>{t('pilot.noPressure')}</p>
    </section>
    <FamilyCareOverview visible={visible} refreshKey={refreshKey} onManage={() => onNavigate('family')} />
    <section className="pilot-panel"><h3>{t('polish.recentRecords')}</h3><p>{t('pilot.japanTime')}</p>
      {error ? <p role="status">{t('pilot.loadFailed')} <button onClick={() => setAttempt(value => value + 1)}>{t('pilot.retry')}</button></p>
        : entries === null ? <p role="status">{t('common.loading')}</p>
        : recent.length === 0 ? <p>{t('tracking.noEntries')}</p>
        : <ol className="recent-records">{recent.map(entry => <li key={entry.record_key}>
          <strong>{t(`tracking.${entry.entry_type}`)}{entry.diaper_type ? ` · ${t(`tracking.${entry.diaper_type}`)}` : ''}
            {entry.feeding_type ? ` · ${t(`tracking.${entry.feeding_type}`)}` : ''}</strong>
          <time>{japanDateTime(entry.timestamp, i18n.resolvedLanguage || 'ja')}</time><small>{t('polish.recordedByYou')}</small>
        </li>)}</ol>}
      <button className="pilot-button secondary" onClick={() => onNavigate('tracking')}>{t('polish.allRecords')}</button>
      {entries && <details><summary>{t('pilot.todayRecords')}</summary><p>{t('polish.recordedCountsOnly')}</p>
        <p>{t('dashboard.todayFeeds')}: {entries.filter(entry => entry.entry_type === 'feeding').length} · {t('dashboard.diaperChanges')}: {entries.filter(entry => entry.entry_type === 'diaper').length}</p>
        <p>{t('pilot.totalSleep')}: {entries.reduce((total, entry) => total + (entry.entry_type === 'sleep' ? entry.sleep_duration_minutes || 0 : 0), 0)}</p>
      </details>}
    </section>
    <div className="pilot-actions family-secondary-actions">
      <button className="pilot-button secondary" onClick={() => onNavigate('chat')}>{t('pilot.askTitle')}</button>
      <button className="pilot-button secondary" onClick={() => onNavigate('support', { view: 'contacts' })}>{t('pilot.supportTitle')}</button>
      <button className="pilot-button secondary" onClick={() => onNavigate('family')}>{t('polish.familyHandoff')}</button>
    </div>
    <details className="pilot-panel"><summary>{t('polish.selfCare')}</summary>
      <button className="pilot-button secondary" onClick={() => onNavigate('checkin')}>{t('checkin.title')}</button>
    </details>
    <RecordingExample />
  </div>
}
