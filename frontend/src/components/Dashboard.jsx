import React, { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../utils/api'
import { japanDay, utcDate } from '../utils/japanTime'
import { recordOperation, isRecordOperation } from '../utils/recordOperations'
import RecordingExample from './RecordingExample'
import FamilyCareOverview from './FamilyCareOverview'
import RecordTime, { useRecordClock } from './RecordTime'
import RecordSaveStatus from './RecordSaveStatus'
import useConnection from '../utils/useConnection'
import useAccountDraft from '../utils/useAccountDraft'
import { DraftRecoveryNotice } from './DraftRecovery'
import RecordEditor from './RecordEditor'
import CareTimeline from './CareTimeline'
import CareTimer from './CareTimer'
import QuickActionSettings from './QuickActionSettings'
import { quickChoices, readQuickPreferences } from '../utils/quickPreferences'
import { revealElement } from '../utils/focusView'
import { useCareSession, useCareWork } from '../utils/CareSession'
import CareSubjectManager, { CareSubjectFields, CareRecordIdentity, privateSubject } from './CareSubject'
import ContinueCare from './ContinueCare'
import useDuplicateReview from '../utils/useDuplicateReview'
import DuplicateReview from './DuplicateReview'
import './Dashboard.css'

export default function Dashboard({ userId, userContext, onNavigate, onRecordsChanged, refreshKey = 0, visible = true, navigationRequest }) {
  const { t } = useTranslation()
  const care = useCareSession()
  const [quickScope, setQuickScope] = useState(privateSubject(''))
  const selectedScope = quickScope.subject_id === (care.activeId || null) ? quickScope : privateSubject(care.activeId)
  const duplicates = useDuplicateReview()
  const { online, reconnections } = useConnection()
  const now = useRecordClock(visible)
  const [entries, setEntries] = useState(null)
  const [error, setError] = useState(false)
  const [attempt, setAttempt] = useState(0)
  const [pending, setPending] = useState(null)
  const [saveStatus, setSaveStatus] = useState('')
  const [undo, setUndo] = useState(null)
  const [receipt, setReceipt] = useState(null)
  const [receiptMode, setReceiptMode] = useState(null)
  const [shortcutKeys, setShortcutKeys] = useState(() => readQuickPreferences(userId))
  const [customizing, setCustomizing] = useState(false)
  const [timerRequest, setTimerRequest] = useState({ kind: '', version: 0 })
  const [timelineRequest, setTimelineRequest] = useState(null)
  const handledNavigation = useRef(null)
  const writing = useRef(false)
  // A later offline/rejected retry cannot disprove an earlier dispatched save.
  const unconfirmedRequest = useRef(null)
  const draft = useAccountDraft('quick', userId, pending ? { pending } : null, content => {
    if (!isRecordOperation(content.pending)) return false
    unconfirmedRequest.current = content.pending.request_key
    setPending(content.pending); setSaveStatus('unconfirmed')
  })
  const refresh = () => { setAttempt(value => value + 1); onRecordsChanged?.() }
  const recordName = entry => [t(`tracking.${entry.entry_type}`),
    entry.diaper_type && t(`tracking.${entry.diaper_type}`), entry.feeding_type && t(`tracking.${entry.feeding_type}`)].filter(Boolean).join(' · ')
  const editRecord = entry => onNavigate('tracking', { action: 'edit', record: entry })
  const quickBlocked = Boolean(pending) || Boolean(draft.candidate) || draft.status === 'loading'
    || ['saving', 'undoing', 'checking'].includes(saveStatus) || Boolean(receiptMode) || !care.ready
  useCareWork('quick', pending ? { version: `${pending.request_key}:${saveStatus}`, title: duplicates.review ? 'continuity.work.duplicateReview'
    : saveStatus === 'offline' ? 'continuity.work.recordUnsent' : 'continuity.work.quickPending', priority: 0,
    tab: 'dashboard', detail: { section: 'quick-record-heading' }, critical: true, entryType: pending.entry_type,
    subjectId: pending.subject_id, time: pending.timestamp, action: 'workflow.work.checkSave' } : draft.candidate ? {
    version: draft.candidate.updated_at, title: 'continuity.work.quickRecovery', priority: 2,
    tab: 'dashboard', detail: { section: 'quick-record-heading' }, action: 'workflow.work.restore',
  } : null)
  useEffect(() => {
    if (visible && navigationRequest?.section && handledNavigation.current !== navigationRequest.key
      && revealElement(document.getElementById(navigationRequest.section))) handledNavigation.current = navigationRequest.key
  }, [visible, navigationRequest?.key])

  useEffect(() => {
    if (!visible) return
    let active = true
    setError(false)
    api.getTracking(userId, 2).then(today => {
      if (active) setEntries(today)
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
      if (!pending && !(await duplicates.check(operation))) { setSaveStatus('unsaved'); return }
      duplicates.clear()
      const result = await api.addTrackingEntry(operation)
      await draft.clear()
      unconfirmedRequest.current = null
      // The receipt carries identity/version only; keep the submitted care fields
      // so its name and edit action refer to the record that was actually saved.
      const saved = { ...operation, ...result }
      setQuickScope(privateSubject(operation.subject_id))
      setUndo(saved); setReceipt(saved); setReceiptMode(null); setPending(null); setSaveStatus('saved'); refresh()
    } catch (failure) {
      if (!(failure.status >= 400 && failure.status < 500)) unconfirmedRequest.current = operation.request_key
      setSaveStatus(unconfirmedRequest.current === operation.request_key ? 'unconfirmed' : 'unsaved')
      setAttempt(value => value + 1)
    }
    finally { writing.current = false }
  }
  const undoQuick = async () => {
    if (writing.current || !undo || pending) return
    writing.current = true; setSaveStatus('undoing')
    try { await api.deleteTrackingEntry(undo.id, undo); setUndo(null); setReceipt(null); setSaveStatus('undone'); refresh() }
    catch { setSaveStatus('undoFailed'); setAttempt(value => value + 1) }
    finally { writing.current = false }
  }

  return <div className="dashboard family-dashboard">
    <header className="dashboard-header"><div><h2>{t('friendly.home.title')}</h2>
      <p>{t('pilot.todayIntro')}</p></div></header>
    <ContinueCare visible={visible} refreshKey={refreshKey + attempt} onNavigate={onNavigate} />
    <section className="pilot-panel quick-record-panel"><h3 id="quick-record-heading" tabIndex={-1}>{t('polish.recordNow')}</h3><p>{t('friendly.home.intro')}</p>
      <fieldset disabled={Boolean(pending) || Boolean(receiptMode)}><legend>{t('continuity.subject.current')}</legend>
        <CareSubjectFields value={selectedScope} onChange={value => { care.setActiveId(value.subject_id || ''); setQuickScope(value) }} />
      </fieldset>
      <div className="record-choices">{shortcutKeys.map(key => quickChoices.find(choice => choice.key === key)).map(choice => <button type="button" key={choice.key}
        className="pilot-button" disabled={quickBlocked}
        onClick={() => {
          if (choice.timer) {
            setTimerRequest(previous => ({ kind: choice.timer, version: previous.version + 1 }))
            revealElement(document.getElementById('care-timer-heading'))
          } else saveQuick(recordOperation({ ...choice.data, ...selectedScope }))
        }}><span className="quick-record-name">{t(choice.timer ? `interaction.shortcuts.${choice.key}` : `polish.quick.${choice.key}`)}</span>
          <small>{t(choice.timer ? 'interaction.shortcuts.timerHint' : 'localCare.record.nowHint')}</small></button>)}</div>
      <button type="button" className="text-action" disabled={quickBlocked} aria-expanded={customizing} onClick={() => setCustomizing(value => !value)}>{t('interaction.shortcuts.title')}</button>
      {customizing && <QuickActionSettings userId={userId} value={shortcutKeys} onSaved={keys => { setShortcutKeys(keys); setCustomizing(false) }} onClose={() => setCustomizing(false)} />}
      {saveStatus && !(receipt && saveStatus === 'saved') && <RecordSaveStatus status={saveStatus} />}
      {receipt && !pending && ['saved', 'undoFailed'].includes(saveStatus) && <section className="quick-save-receipt" aria-label={t('friendly.home.saved')}>
        <p role="status"><strong>{t('friendly.home.saved')}</strong> · <time dateTime={utcDate(receipt.timestamp).toISOString()}>{new Intl.DateTimeFormat('ja-JP', { timeZone: 'Asia/Tokyo', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).format(utcDate(receipt.timestamp))}</time></p>
        <p>{recordName(receipt)}</p><RecordTime value={receipt.timestamp} now={now} />
        <CareRecordIdentity record={receipt} />
        <div className="pilot-actions">
          <button type="button" className="pilot-button secondary" disabled={Boolean(receiptMode)} aria-expanded={receiptMode === 'time'} onClick={() => setReceiptMode('time')}>{t('interaction.record.time')}</button>
          {['feeding', 'sleep', 'pumping'].includes(receipt.entry_type) && <button type="button" className="pilot-button secondary" disabled={Boolean(receiptMode)} aria-expanded={receiptMode === 'quantity'} onClick={() => setReceiptMode('quantity')}>{t('interaction.record.quantity')}</button>}
          {undo && <button type="button" className="pilot-button secondary" disabled={Boolean(receiptMode)} onClick={undoQuick}>{t('friendly.home.undo')}</button>}
        </div>{undo && <small>{t('friendly.home.undoHint')}</small>}
        <button type="button" className="text-action" onClick={() => setTimelineRequest({ ...receipt, focusVersion: Date.now() })}>{t('continuity.period.findSaved')}</button>
        {receiptMode && <RecordEditor key={receipt.record_key} record={receipt} mode={receiptMode} onSaved={result => {
          setReceipt(result); setUndo(null); refresh()
        }} onCancel={() => setReceiptMode(null)} />}
      </section>}
      <DraftRecoveryNotice draft={draft} disabled={['saving', 'undoing'].includes(saveStatus)} compact />
      <DuplicateReview review={duplicates.review} disabled={['saving', 'undoing'].includes(saveStatus)} onContinue={() => saveQuick(pending)} onCancel={() => {
        duplicates.clear(); setPending(null); setSaveStatus(''); draft.clear()
      }} />
      {pending && saveStatus !== 'saving' && !duplicates.review && <div className="pilot-actions"><p>{t('localCare.record.retryHint')}</p>
        <button className="pilot-button secondary" onClick={() => setAttempt(value => value + 1)}>{t('localCare.record.check')}</button>
        <button className="pilot-button secondary" onClick={() => saveQuick(pending)}>{t('localCare.record.resend')}</button>
        <button className="pilot-button secondary" onClick={() => {
          if (window.confirm(t('polish.abandonWrite'))) { unconfirmedRequest.current = null; setPending(null); draft.clear(); setSaveStatus(''); refresh() }
        }}>{t('localCare.record.stopRetry')}</button></div>}
      <button className="pilot-button secondary" onClick={() => onNavigate('tracking', 'feeding')}>{t('friendly.home.details')}</button>
      <p>{t('pilot.noPressure')}</p>
    </section>
    <CareTimeline entries={entries} userId={userId} visible={visible} refreshKey={refreshKey + attempt} error={error}
      navigationRecord={timelineRequest} onReload={() => setAttempt(value => value + 1)} onFullEdit={editRecord} onRecordsChanged={refresh} blocked={quickBlocked} />
    <section className="pilot-panel">
      <button className="pilot-button secondary" onClick={() => onNavigate('tracking')}>{t('polish.allRecords')}</button>
      {entries && <details><summary>{t('continuity.period.startedToday')}</summary><p>{t('polish.recordedCountsOnly')}</p><p>{t('continuity.period.totalsNotice')}</p>
        <p>{t('dashboard.todayFeeds')}: {entries.filter(entry => japanDay(entry.timestamp) === japanDay() && entry.entry_type === 'feeding').length} · {t('dashboard.diaperChanges')}: {entries.filter(entry => japanDay(entry.timestamp) === japanDay() && entry.entry_type === 'diaper').length}</p>
        <p>{t('pilot.totalSleep')}: {entries.reduce((total, entry) => total + (japanDay(entry.timestamp) === japanDay() && entry.entry_type === 'sleep' ? entry.sleep_duration_minutes || 0 : 0), 0)}</p>
      </details>}
    </section>
    <CareTimer userId={userId} visible={visible} requestedKind={timerRequest.kind} requestVersion={timerRequest.version}
      blocked={quickBlocked} onRecordsChanged={refresh} onLocate={record => setTimelineRequest({ ...record, focusVersion: Date.now() })} />
    <CareSubjectManager />
    <FamilyCareOverview visible={visible} refreshKey={refreshKey} onManage={() => onNavigate('family')} />
    <div className="pilot-actions family-secondary-actions">
      <button className="pilot-button secondary" onClick={() => onNavigate('chat')}>{t('friendly.chat.title')}</button>
      <button className="pilot-button secondary" onClick={() => onNavigate('support', { view: 'contacts' })}>{t('pilot.supportTitle')}</button>
    </div>
    <details className="pilot-panel"><summary>{t('polish.selfCare')}</summary>
      <button className="pilot-button secondary" onClick={() => onNavigate('checkin')}>{t('checkin.title')}</button>
    </details>
    <RecordingExample />
  </div>
}
