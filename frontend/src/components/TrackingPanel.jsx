import React, { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../utils/api'
import taskManager from '../utils/taskManager'
import { japanDateTime, japanDateTimeInput, utcDate } from '../utils/japanTime'
import { earliestRecordTime } from '../utils/trackingPolicy'
import { recordOperation, requestKey as newRequestKey, isRecordOperation } from '../utils/recordOperations'
import useAccountDraft from '../utils/useAccountDraft'
import { DraftRecoveryNotice } from './DraftRecovery'
import AIUseNotice from './AIUseNotice'
import Charts from './Charts'
import useConnection from '../utils/useConnection'
import { useToast } from './Toast'
import RecordTime, { useRecordClock } from './RecordTime'
import RecordSaveStatus from './RecordSaveStatus'
import { revealElement } from '../utils/focusView'
import './TrackingPanel.css'

const types = ['feeding', 'diaper', 'sleep', 'mood', 'pumping', 'recovery']
const recordFields = ['entry_type', 'timestamp', 'feeding_type', 'duration_minutes', 'amount_ml', 'side', 'diaper_type',
  'sleep_duration_minutes', 'sleep_quality', 'mood_level', 'mood_notes', 'pumped_amount_ml', 'weight_kg', 'breast_condition', 'recovery_notes', 'notes']
const payload = entry => Object.fromEntries(recordFields.filter(key => entry[key] !== undefined).map(key => [key, entry[key]]))

export default function TrackingPanel({ userId, initialEntryType, requestKey = 0, onRecordsChanged, visible = true }) {
  const { t, i18n } = useTranslation()
  const { online, reconnections } = useConnection()
  const now = useRecordClock(visible)
  const toast = useToast()
  const [entries, setEntries] = useState([])
  const [entriesLoading, setEntriesLoading] = useState(true)
  const [summary, setSummary] = useState(null)
  const [showAddForm, setShowAddForm] = useState(types.includes(initialEntryType))
  const [entryType, setEntryType] = useState(types.includes(initialEntryType) ? initialEntryType : 'feeding')
  const [editing, setEditing] = useState(null)
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [undoEntry, setUndoEntry] = useState(null)
  const [loading, setLoading] = useState(false)
  const [showCharts, setShowCharts] = useState(false)
  const [acceptedAI, setAcceptedAI] = useState(false)
  const [includeProfile, setIncludeProfile] = useState(false)
  const [includeParent, setIncludeParent] = useState(false)
  const [includeNotes, setIncludeNotes] = useState(false)
  const [summaryLoading, setSummaryLoading] = useState(false)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  const [recordRange, setRecordRange] = useState(7)
  const [formDraft, setFormDraft] = useState(null)
  const [restoredForm, setRestoredForm] = useState(null)
  const [formRevision, setFormRevision] = useState(0)
  const [pendingSave, setPendingSave] = useState(null)
  const [saveStatus, setSaveStatus] = useState('')
  const [openRequest, setOpenRequest] = useState(null)
  const [formFocus, setFormFocus] = useState(0)
  const consumedRequest = useRef(null)
  const formHeading = useRef(null)
  const pendingFormFocus = useRef(false)
  const writing = useRef(false)
  // Keep uncertainty attached to the original operation until success or explicit abandonment.
  const unconfirmedRequest = useRef(null)
  const recordDraft = showAddForm && (formDraft || pendingSave) ? {
    ...(formDraft || { formData: payload(pendingSave.data), when: 'specific',
      recordedAt: japanDateTimeInput(pendingSave.data.timestamp) }), entryType, editing, pendingSave,
  } : null
  const draft = useAccountDraft('record', userId, recordDraft, content => {
    if (!types.includes(content.entryType) || !content.formData || typeof content.formData !== 'object') return false
    if (content.pendingSave && !isRecordOperation(content.pendingSave.data)) return false
    if (content.editing && (!Number.isInteger(content.editing.id) || !content.editing.record_key || !Number.isInteger(content.editing.revision))) return false
    setEditing(content.editing || null); setEntryType(content.entryType); setRestoredForm(content)
    setPendingSave(content.pendingSave || null); setFormRevision(value => value + 1); setShowAddForm(true)
    unconfirmedRequest.current = content.pendingSave?.data.request_key || null
    setSaveStatus(content.pendingSave ? 'unconfirmed' : '')
  })
  const summaryVersion = useRef(0)

  useEffect(() => {
    if (!visible) return
    let active = true
    setError(''); setEntriesLoading(true)
    api.getTracking(userId, recordRange).then(data => { if (active) setEntries(data) })
      .catch(() => { if (active) setError(t('pilot.loadFailed')) })
      .finally(() => { if (active) setEntriesLoading(false) })
    return () => { active = false }
  }, [userId, attempt, recordRange, visible, reconnections])

  const openRecord = (request, confirm = true) => {
    if (pendingSave || writing.current || loading || draft.candidate || draft.status === 'loading') return
    if (confirm && formDraft && !window.confirm(t('friendly.record.replace'))) return
    // Home passes an owner-read snapshot. The immutable key/revision still guards
    // the update: an intervening edit or deletion is rejected by the API.
    setRestoredForm(null); setFormDraft(null); setEditing(request.record || null)
    setEntryType(request.record?.entry_type || request.entryType); setShowAddForm(true)
    setSaveStatus(''); setOpenRequest(null); setFormRevision(value => value + 1)
    pendingFormFocus.current = true; setFormFocus(value => value + 1)
  }
  useEffect(() => {
    if (consumedRequest.current === requestKey) return
    consumedRequest.current = requestKey
    const record = initialEntryType?.action === 'edit' ? initialEntryType.record : null
    const request = record && types.includes(record.entry_type) && Number.isInteger(record.id)
      && typeof record.record_key === 'string' && Number.isInteger(record.revision) ? { record }
      : types.includes(initialEntryType) ? { entryType: initialEntryType } : null
    if (!request) return
    // Pending writes and recovery drafts must be resolved explicitly, never
    // replaced just because navigation supplied a new target.
    if (pendingSave || writing.current || loading || formDraft || draft.candidate) setOpenRequest(request)
    else if (draft.status === 'loading') setOpenRequest({ ...request, autoOpen: true })
    else openRecord(request, false)
  }, [initialEntryType, requestKey, pendingSave, loading, formDraft, draft.candidate, draft.status])
  useEffect(() => {
    if (!visible || !openRequest?.autoOpen || draft.status === 'loading') return
    if (pendingSave || writing.current || loading || formDraft || draft.candidate) {
      setOpenRequest(previous => ({ ...previous, autoOpen: false })); return
    }
    openRecord(openRequest, false)
  }, [visible, openRequest, pendingSave, loading, formDraft, draft.candidate, draft.status])
  useEffect(() => {
    if (visible && showAddForm && pendingFormFocus.current && revealElement(formHeading.current)) pendingFormFocus.current = false
  }, [visible, showAddForm, formFocus])

  useEffect(() => {
    if (!undoEntry) return
    const timer = setTimeout(() => setUndoEntry(null), 8000)
    return () => clearTimeout(timer)
  }, [undoEntry])

  useEffect(() => { summaryVersion.current++; setSummary(null) }, [includeProfile, includeParent, includeNotes, i18n.resolvedLanguage])
  useEffect(() => () => { summaryVersion.current++ }, [])

  const refresh = () => {
    summaryVersion.current++; setSummary(null); setAttempt(value => value + 1); onRecordsChanged?.()
  }
  const saveEntry = async formData => {
    if (writing.current) return
    const operation = pendingSave || { data: recordOperation(payload(formData)),
      editing: editing ? { id: editing.id, record_key: editing.record_key, revision: editing.revision } : null }
    if (!online || navigator.onLine === false) {
      setPendingSave(operation)
      setSaveStatus(unconfirmedRequest.current === operation.data.request_key ? 'unconfirmed' : 'offline')
      return false
    }
    writing.current = true
    setPendingSave(operation); setLoading(true); setSaveStatus('saving')
    try {
      if (operation.editing) await api.updateTrackingEntry(operation.editing.id, {
        ...payload(operation.data), record_key: operation.editing.record_key, revision: operation.editing.revision,
      })
      else await api.addTrackingEntry(operation.data)
      const age = Math.floor((Date.now() - utcDate(operation.data.timestamp).getTime()) / 86400000)
      if (age >= recordRange) setRecordRange(age < 30 ? 30 : age < 90 ? 90 : 365)
      setPendingSave(null); setFormDraft(null); await draft.clear()
      unconfirmedRequest.current = null
      setRestoredForm(null); setShowAddForm(false); setEditing(null); setSaveStatus('saved'); refresh()
      toast.success(t('pilot.recordSaved'))
      return true
    } catch (err) {
      if (!(err.status >= 400 && err.status < 500)) unconfirmedRequest.current = operation.data.request_key
      const unconfirmed = unconfirmedRequest.current === operation.data.request_key
      setSaveStatus(unconfirmed ? 'unconfirmed' : 'unsaved')
      if (!unconfirmed && [400, 404, 409, 422].includes(err.status)) setPendingSave(null)
      if (err.status === 409 || err.status === 404) refresh()
      toast.error(t(unconfirmed ? 'flows.connection.unconfirmedSave'
        : err.status === 409 || err.status === 404 ? 'work.recordConflict' : 'pilot.recordFailed'))
      return false
    }
    finally { writing.current = false; setLoading(false) }
  }
  const cancelForm = () => {
    if (pendingSave && !window.confirm(t('polish.abandonWrite'))) return
    unconfirmedRequest.current = null
    setSaveStatus('')
    setPendingSave(null); setFormDraft(null); setRestoredForm(null); setShowAddForm(false); setEditing(null)
    draft.clear(); setAttempt(value => value + 1)
  }
  const removeEntry = async entry => {
    if (writing.current || loading || pendingSave) return
    writing.current = true; setLoading(true); setSaveStatus('removing')
    try {
      await api.deleteTrackingEntry(entry.id, entry)
      setUndoEntry({ ...entry, restore_request_key: newRequestKey() }); setDeleteTarget(null)
      if (editing?.record_key === entry.record_key) {
        setEditing(null); setShowAddForm(false); setFormDraft(null); setRestoredForm(null); draft.clear()
      }
      setSaveStatus('removed'); refresh()
    } catch (err) {
      if (err.status === 409 || err.status === 404) {
        setDeleteTarget(null); setSaveStatus(''); toast.error(t('work.recordConflict')); refresh()
      } else { setSaveStatus('removeFailed'); toast.error(t('work.deleteFailed')) }
    }
    finally { writing.current = false; setLoading(false) }
  }
  const restoreEntry = async () => {
    if (!undoEntry || writing.current || loading || pendingSave) return
    const restoring = undoEntry
    writing.current = true; setLoading(true); setSaveStatus('restoring')
    try {
      await api.addTrackingEntry({ ...payload(restoring), request_key: restoring.restore_request_key })
      setUndoEntry(null); setSaveStatus('restored'); refresh(); toast.success(t('work.restored'))
    } catch { setSaveStatus('restoreFailed'); toast.error(t('work.restoreFailed')) }
    finally { writing.current = false; setLoading(false) }
  }
  const loadSummary = async () => {
    if (!acceptedAI || summaryLoading) return
    setSummaryLoading(true)
    const version = ++summaryVersion.current
    const scope = { include_profile: includeProfile, include_parent: includeParent, include_notes: includeNotes,
      language: i18n.resolvedLanguage || 'ja' }
    try {
      const result = import.meta.env.VITE_ASYNC_MODE !== 'false'
        ? await taskManager.submitTask('tracking_analysis', { days: 7, ...scope }, { priority: 'low', timeout: 120000 })
        : await api.getTrackingSummary(userId, 7, scope)
      if (version === summaryVersion.current) setSummary(result)
    } catch { if (version === summaryVersion.current) toast.error(t('pilot.chatUnavailable')) }
    finally { setSummaryLoading(false) }
  }

  return <div className="tracking-panel">
    <div className="tracking-header"><h2>{t('tracking.title')}</h2>
      <button className="add-button" disabled={loading || (!showAddForm && (Boolean(draft.candidate) || draft.status === 'loading'))} onClick={() => {
        if (showAddForm) cancelForm()
        else openRecord({ entryType })
      }}>{showAddForm ? t('tracking.cancel') : `+ ${t('tracking.addEntry')}`}</button></div>
    <p>{t('pilot.noPressure')}</p>
    <DraftRecoveryNotice draft={draft} disabled={loading} />
    {openRequest && <section className="record-open-request" aria-label={t('friendly.record.incoming')}>
      <p>{t('friendly.record.incoming')}</p>
      {openRequest.record && <><strong>{t(`tracking.${openRequest.record.entry_type}`)}</strong><RecordTime value={openRequest.record.timestamp} now={now} /></>}
      {(pendingSave || draft.candidate || draft.status === 'loading') && <p>{t('friendly.record.resolveDraft')}</p>}
      <div className="pilot-actions">
        <button type="button" className="pilot-button secondary" disabled={loading || Boolean(pendingSave) || Boolean(draft.candidate) || draft.status === 'loading'}
          onClick={() => openRecord(openRequest)}>{t('friendly.record.open')}</button>
        <button type="button" className="pilot-button secondary" onClick={() => setOpenRequest(null)}>{t('friendly.record.discardOpen')}</button>
      </div>
    </section>}
    <RecordSaveStatus status={saveStatus} />
    {pendingSave && <button type="button" className="pilot-button secondary" disabled={loading} onClick={() => setAttempt(value => value + 1)}>{t('flows.connection.checkRecords')}</button>}
    {pendingSave && <p>{t('localCare.record.retryHint')} {japanDateTime(pendingSave.data.timestamp, i18n.resolvedLanguage || 'ja')}</p>}
    {showAddForm && <div ref={formHeading} tabIndex={-1} className="record-form-region" role="region" aria-label={t(editing ? 'work.editRecord' : 'tracking.addEntry')}>
      <EntryForm key={`${editing ? `edit:${editing.record_key}:${editing.revision}` : 'new'}:${formRevision}`}
      entryType={entryType} initialEntry={editing} restored={restoredForm} onDraftChange={setFormDraft} locked={Boolean(pendingSave)}
      onEntryTypeChange={setEntryType} onSubmit={saveEntry} onCancel={cancelForm} loading={loading} saving={saveStatus === 'saving'} /></div>}
    {undoEntry && <div className="pilot-panel undo-notice" role="status"><p>{t('work.lastDeleted')}</p>
      <button className="pilot-button secondary" disabled={loading || Boolean(pendingSave)} onClick={restoreEntry}>{t('work.undoDelete')}</button></div>}
    <section className="entries-list"><h3>{t('tracking.recentEntries')}</h3><p>{t('pilot.japanTime')}</p>
      <label>{t('work.recordPeriod')}<select value={recordRange} disabled={loading} onChange={event => setRecordRange(Number(event.target.value))}>
        {[7, 30, 90, 365].map(days => <option key={days} value={days}>{t('work.rangeDays', { days })}</option>)}
      </select></label>
      {error && <p role="alert">{error}<button className="pilot-button secondary" onClick={() => setAttempt(value => value + 1)}>{t('pilot.retry')}</button></p>}
      {entriesLoading && <p role="status">{t('common.loading')}</p>}
      {!error && !entriesLoading && entries.length === 0 && <p>{t('tracking.noEntries')}</p>}
      {entries.map(entry => <article key={entry.record_key} className="tracking-entry-card">
        <div className="entry-header"><strong>{t(`tracking.${entry.entry_type}`)}</strong><RecordTime value={entry.timestamp} now={now} /></div>
        <div className="entry-details">
          {entry.feeding_type && <span>{t(`tracking.${entry.feeding_type}`)}</span>}
          {entry.side && <span>{t(`localCare.record.sides.${entry.side}`, { defaultValue: entry.side })}</span>}
          {entry.diaper_type && <span>{t(`tracking.${entry.diaper_type}`)}</span>}
          {['duration_minutes', 'sleep_duration_minutes'].map(key => entry[key] != null && <span key={key}>{entry[key]} {t('pilot.minutes')}</span>)}
          {['amount_ml', 'pumped_amount_ml'].map(key => entry[key] != null && <span key={key}>{entry[key]} mL</span>)}
          {entry.mood_level && <span>{t(`tracking.${entry.mood_level}`)}</span>}
          {entry.weight_kg != null && <span>{entry.weight_kg} kg</span>}
          {entry.breast_condition && <span>{t(`tracking.${entry.breast_condition}`)}</span>}
        </div>
        {['notes', 'mood_notes', 'recovery_notes'].map(key => entry[key] && <p key={key} className="entry-notes">{entry[key]}</p>)}
        <div className="pilot-actions"><button className="pilot-button secondary" disabled={loading || Boolean(pendingSave) || Boolean(draft.candidate) || draft.status === 'loading'} onClick={() => {
          openRecord({ record: entry })
        }}>{t('work.editRecord')}</button>
          <button className="pilot-button secondary" disabled={loading || Boolean(pendingSave)} onClick={() => setDeleteTarget(entry)}>{t('common.delete')}</button></div>
        {deleteTarget?.record_key === entry.record_key && <div role="alertdialog" aria-label={t('work.deleteConfirm')}>
          <p>{t('work.deleteConfirm')}</p><button disabled={loading || Boolean(pendingSave)} onClick={() => removeEntry(deleteTarget)}>{t('work.confirmDelete')}</button>
          <button disabled={loading} onClick={() => setDeleteTarget(null)}>{t('tracking.cancel')}</button>
        </div>}
      </article>)}
    </section>
    <details className="pilot-panel"><summary>{t('pilot.optionalAnalysis')}</summary>
      <button className="pilot-button secondary" onClick={() => setShowCharts(value => !value)}>{t(showCharts ? 'tracking.hideCharts' : 'tracking.showCharts')}</button>
      {showCharts && <Charts userId={userId} refreshKey={attempt} visible={visible}
        onRecord={!loading && !pendingSave && !draft.candidate && draft.status !== 'loading' ? () => openRecord({ entryType }) : undefined} />}
      <AIUseNotice scope="records" accepted={acceptedAI} onChange={setAcceptedAI} disabled={summaryLoading}
        includeProfile={includeProfile} onProfileChange={setIncludeProfile} includeParent={includeParent} onParentChange={setIncludeParent}
        includeNotes={includeNotes} onNotesChange={setIncludeNotes} />
      <button className="pilot-button secondary" disabled={!acceptedAI || summaryLoading || entriesLoading || entries.length === 0} onClick={loadSummary}>{t(summaryLoading ? 'common.loading' : 'pilot.analyzeRecords')}</button>
      {summary && <div className="ai-summary"><p>{t('pilot.aiLabel')}</p>
        {['patterns', 'insights', 'recommendations'].map(key => summary[key]?.length > 0 && <section key={key}>
          <h3>{t(`tracking.${key}`)}</h3><ul>{summary[key].map((value, index) => <li key={index}>{value}</li>)}</ul>
        </section>)}
      </div>}
    </details>
  </div>
}

function EntryForm({ entryType, initialEntry, restored, onDraftChange, locked, onEntryTypeChange, onSubmit, onCancel, loading, saving }) {
  const { t } = useTranslation()
  const [formData, setFormData] = useState(restored?.formData || (initialEntry ? payload(initialEntry) : {}))
  const [when, setWhen] = useState(restored?.when || (initialEntry ? 'specific' : 'now'))
  const [recordedAt, setRecordedAt] = useState(restored?.recordedAt || japanDateTimeInput(initialEntry?.timestamp || new Date()))
  const [error, setError] = useState('')
  const previousType = useRef(entryType)
  useEffect(() => {
    const meaningful = when === 'specific' || Object.values(formData).some(value => value !== null && value !== undefined && value !== '')
    onDraftChange(meaningful ? { formData, when, recordedAt } : null)
  }, [formData, when, recordedAt, onDraftChange])
  useEffect(() => {
    if (previousType.current === entryType) return
    previousType.current = entryType
    // Keep the same form instance, date/time and common note, including home shortcuts.
    setFormData(previous => ({ notes: previous.notes || '' }))
    setError('')
  }, [entryType])
  const feedingMethod = formData.feeding_type
  const breastFields = [['duration_minutes', 'duration', 'number'], ['side', 'side', ['left', 'right', 'both']]]
  const milkFields = [['amount_ml', 'amount', 'number']]
  const mainFeedingFields = feedingMethod === 'breast' ? breastFields : feedingMethod === 'formula' ? milkFields
    : feedingMethod === 'mixed' ? [...breastFields, ...milkFields] : []
  const otherFeedingFields = [...breastFields, ...milkFields].filter(([key]) => !mainFeedingFields.some(([main]) => main === key))
  const hasOtherFeedingValues = otherFeedingFields.some(([key]) => formData[key] !== undefined && formData[key] !== null && formData[key] !== '')
  const fields = {
    feeding: [['feeding_type', 'feedingType', ['breast', 'formula', 'mixed']], ...mainFeedingFields],
    diaper: [['diaper_type', 'diaperType', ['wet', 'dirty', 'both']]],
    sleep: [['sleep_duration_minutes', 'duration', 'number'], ['sleep_quality', 'quality', ['peaceful', 'restless', 'interrupted']]],
    mood: [['mood_level', 'moodLevel', ['very_low', 'low', 'neutral', 'good', 'very_good']], ['mood_notes', 'notes', 'textarea']],
    pumping: [['pumped_amount_ml', 'amount', 'number']],
    recovery: [['weight_kg', 'weight', 'number'], ['breast_condition', 'breastCondition', ['normal', 'engorged', 'blocked', 'painful', 'other']], ['recovery_notes', 'recoveryNotes', 'textarea']],
  }
  const feedingLabels = { duration_minutes: feedingMethod === 'breast' ? 'feedingTime' : 'feedingDuration',
    amount_ml: feedingMethod === 'formula' ? 'milkAmount' : 'knownAmount', side: 'feedingSide' }
  const fieldLabel = (key, label) => t(entryType === 'feeding' && feedingLabels[key]
    ? `localCare.record.${feedingLabels[key]}` : `tracking.${label}`)
  const renderField = ([key, label, kind]) => Array.isArray(kind)
    ? <fieldset key={key}><legend>{fieldLabel(key, label)}</legend><div className="record-choices">
      {kind.map(value => <button key={value} type="button" className="pilot-button secondary" aria-pressed={formData[key] === value}
        onClick={() => setFormData(previous => ({ ...previous, [key]: previous[key] === value ? null : value }))}>
        {t(key === 'side' ? `localCare.record.sides.${value}` : `tracking.${value}`)}</button>)}
    </div></fieldset>
    : <label key={key}>{fieldLabel(key, label)}<input type="number" inputMode={key.endsWith('_minutes') ? 'numeric' : 'decimal'}
      min="0" step={key.endsWith('_minutes') ? '1' : '0.1'} value={formData[key] ?? ''}
      onChange={event => setFormData({ ...formData, [key]: event.target.value === '' ? null : Number(event.target.value) })} /></label>
  return <form className="entry-form" onSubmit={event => {
    event.preventDefault()
    if (loading) return
    if (locked) { onSubmit(); return }
    const date = when === 'now' ? new Date() : new Date(`${recordedAt}:00+09:00`)
    if (!Number.isFinite(date.getTime()) || date.getTime() > Date.now() + 60000) { setError(t('work.invalidTime')); return }
    if (date < earliestRecordTime()) { setError(t('work.recordTooOld')); return }
    const unchangedTime = initialEntry && when === 'specific' && recordedAt === japanDateTimeInput(initialEntry.timestamp)
    setError('')
    onSubmit({ ...formData, entry_type: entryType, timestamp: unchangedTime ? utcDate(initialEntry.timestamp).toISOString() : date.toISOString() })
  }}><fieldset disabled={loading || locked}>
    <legend>{t(initialEntry ? 'work.editRecord' : 'tracking.addEntry')}</legend>
    {initialEntry && <p>{t('work.recordTypeChangeNotice')}</p>}
    <label>{t('tracking.entryType')}<select value={entryType} onChange={event => {
      onEntryTypeChange(event.target.value)
    }}>
      {[['babyGroup', ['feeding', 'diaper', 'sleep', 'pumping']], ['selfGroup', ['mood', 'recovery']]].map(([group, options]) =>
        <optgroup key={group} label={t(`localCare.record.${group}`)}>{options.map(type => <option key={type} value={type}>{t(`tracking.${type}`)}</option>)}</optgroup>)}
    </select></label>
    <label>{t('work.recordTime')}<select value={when} onChange={event => setWhen(event.target.value)}>
      <option value="now">{t('work.now')}</option><option value="specific">{t('work.chooseTime')}</option>
    </select></label>
    {when === 'specific' && <label>{t('pilot.japanTime')}<input type="datetime-local" required value={recordedAt}
      min={japanDateTimeInput(earliestRecordTime())} max={japanDateTimeInput()} onChange={event => setRecordedAt(event.target.value)} /></label>}
    <p>{t('work.recordWindowNotice')}</p>
    {fields[entryType].filter(([, , kind]) => kind !== 'textarea').map(renderField)}
    {entryType === 'feeding' && <>
      {!mainFeedingFields.length && <p className="field-hint">{t('localCare.record.chooseFeeding')}</p>}
      {otherFeedingFields.length > 0 && <AdditionalFeedingFields key={feedingMethod || 'unspecified'} initiallyOpen={hasOtherFeedingValues}>
        {otherFeedingFields.map(renderField)}
      </AdditionalFeedingFields>}
    </>}
    <details open={Boolean(initialEntry?.notes || initialEntry?.mood_notes || initialEntry?.recovery_notes)}><summary>{t('work.optionalNotes')}</summary>
      {fields[entryType].filter(([, , kind]) => kind === 'textarea').map(([key, label]) => <label key={key}>{t(`tracking.${label}`)}
        <textarea value={formData[key] || ''} maxLength={2000} rows={3} onChange={event => setFormData({ ...formData, [key]: event.target.value })} />
      </label>)}
      <label>{t('tracking.notes')}<textarea rows={2} maxLength={2000} value={formData.notes || ''} onChange={event => setFormData({ ...formData, notes: event.target.value })} /></label>
    </details>
    {error && <p role="alert">{error}</p>}
  </fieldset><div className="form-actions"><button type="button" disabled={loading} onClick={onCancel}>{t('tracking.cancel')}</button>
      <button type="submit" disabled={loading}>{t(saving ? 'tracking.adding' : locked ? 'localCare.record.resend' : initialEntry ? 'work.saveChanges' : 'tracking.addEntryButton')}</button></div>
  </form>
}

function AdditionalFeedingFields({ initiallyOpen, children }) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(initiallyOpen)
  return <details className="additional-feeding" open={open} onToggle={event => {
    if (event.target === event.currentTarget) setOpen(event.currentTarget.open)
  }}><summary>{t('localCare.record.additionalFeeding')}</summary>
    <p className="field-hint">{t('localCare.record.additionalNotice')}</p>{children}
  </details>
}
