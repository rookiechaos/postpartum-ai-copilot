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
import './Dashboard.css'

export default function Dashboard({ userId, userContext, onNavigate, onRecordsChanged, refreshKey = 0, visible = true }) {
  const { t } = useTranslation()
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
    || ['saving', 'undoing'].includes(saveStatus) || Boolean(receiptMode)

  useEffect(() => {
    if (!visible) return
    let active = true
    setError(false)
    api.getTracking(userId, 2).then(today => {
      if (active) setEntries(today.filter(entry => japanDay(entry.timestamp) === japanDay()))
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
      // The receipt carries identity/version only; keep the submitted care fields
      // so its name and edit action refer to the record that was actually saved.
      const saved = { ...operation, ...result }
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
      <p>{userContext?.babyName ? t('dashboard.howIsBaby', { name: userContext.babyName }) : t('pilot.todayIntro')}</p></div></header>
    <section className="pilot-panel quick-record-panel"><h3>{t('polish.recordNow')}</h3><p>{t('friendly.home.intro')}</p>
      <div className="record-choices">{shortcutKeys.map(key => quickChoices.find(choice => choice.key === key)).map(choice => <button type="button" key={choice.key}
        className="pilot-button" disabled={quickBlocked}
        onClick={() => {
          if (choice.timer) {
            setTimerRequest(previous => ({ kind: choice.timer, version: previous.version + 1 }))
            revealElement(document.getElementById('care-timer-heading'))
          } else saveQuick(recordOperation(choice.data))
        }}><span className="quick-record-name">{t(choice.timer ? `interaction.shortcuts.${choice.key}` : `polish.quick.${choice.key}`)}</span>
          <small>{t(choice.timer ? 'interaction.shortcuts.timerHint' : 'localCare.record.nowHint')}</small></button>)}</div>
      <button type="button" className="text-action" disabled={quickBlocked} aria-expanded={customizing} onClick={() => setCustomizing(value => !value)}>{t('interaction.shortcuts.title')}</button>
      {customizing && <QuickActionSettings userId={userId} value={shortcutKeys} onSaved={keys => { setShortcutKeys(keys); setCustomizing(false) }} onClose={() => setCustomizing(false)} />}
      {saveStatus && !(receipt && saveStatus === 'saved') && <RecordSaveStatus status={saveStatus} />}
      {receipt && !pending && ['saved', 'undoFailed'].includes(saveStatus) && <section className="quick-save-receipt" aria-label={t('friendly.home.saved')}>
        <p role="status"><strong>{t('friendly.home.saved')}</strong> · <time dateTime={utcDate(receipt.timestamp).toISOString()}>{new Intl.DateTimeFormat('ja-JP', { timeZone: 'Asia/Tokyo', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).format(utcDate(receipt.timestamp))}</time></p>
        <p>{recordName(receipt)}</p><RecordTime value={receipt.timestamp} now={now} />
        <div className="pilot-actions">
          <button type="button" className="pilot-button secondary" disabled={Boolean(receiptMode)} aria-expanded={receiptMode === 'time'} onClick={() => setReceiptMode('time')}>{t('interaction.record.time')}</button>
          {['feeding', 'sleep', 'pumping'].includes(receipt.entry_type) && <button type="button" className="pilot-button secondary" disabled={Boolean(receiptMode)} aria-expanded={receiptMode === 'quantity'} onClick={() => setReceiptMode('quantity')}>{t('interaction.record.quantity')}</button>}
          {undo && <button type="button" className="pilot-button secondary" disabled={Boolean(receiptMode)} onClick={undoQuick}>{t('friendly.home.undo')}</button>}
        </div>{undo && <small>{t('friendly.home.undoHint')}</small>}
        {receiptMode && <RecordEditor key={receipt.record_key} record={receipt} mode={receiptMode} onSaved={result => {
          setReceipt(result); setUndo(null); refresh()
        }} onCancel={() => setReceiptMode(null)} />}
      </section>}
      <DraftRecoveryNotice draft={draft} disabled={['saving', 'undoing'].includes(saveStatus)} compact />
      {pending && saveStatus !== 'saving' && <div className="pilot-actions"><p>{t('localCare.record.retryHint')}</p>
        <button className="pilot-button secondary" onClick={() => setAttempt(value => value + 1)}>{t('localCare.record.check')}</button>
        <button className="pilot-button secondary" onClick={() => saveQuick(pending)}>{t('localCare.record.resend')}</button>
        <button className="pilot-button secondary" onClick={() => {
          if (window.confirm(t('polish.abandonWrite'))) { unconfirmedRequest.current = null; setPending(null); draft.clear(); setSaveStatus(''); refresh() }
        }}>{t('localCare.record.stopRetry')}</button></div>}
      <button className="pilot-button secondary" onClick={() => onNavigate('tracking', 'feeding')}>{t('friendly.home.details')}</button>
      <p>{t('pilot.noPressure')}</p>
    </section>
    <CareTimeline entries={entries} userId={userId} visible={visible} refreshKey={refreshKey + attempt} error={error}
      onReload={() => setAttempt(value => value + 1)} onFullEdit={editRecord} onRecordsChanged={refresh} blocked={quickBlocked} />
    <section className="pilot-panel">
      <button className="pilot-button secondary" onClick={() => onNavigate('tracking')}>{t('polish.allRecords')}</button>
      {entries && <details><summary>{t('pilot.todayRecords')}</summary><p>{t('polish.recordedCountsOnly')}</p>
        <p>{t('dashboard.todayFeeds')}: {entries.filter(entry => entry.entry_type === 'feeding').length} · {t('dashboard.diaperChanges')}: {entries.filter(entry => entry.entry_type === 'diaper').length}</p>
        <p>{t('pilot.totalSleep')}: {entries.reduce((total, entry) => total + (entry.entry_type === 'sleep' ? entry.sleep_duration_minutes || 0 : 0), 0)}</p>
      </details>}
    </section>
    <CareTimer userId={userId} visible={visible} requestedKind={timerRequest.kind} requestVersion={timerRequest.version}
      blocked={quickBlocked} onRecordsChanged={refresh} />
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
