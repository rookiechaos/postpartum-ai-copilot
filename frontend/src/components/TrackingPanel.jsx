import React, { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../utils/api'
import taskManager from '../utils/taskManager'
import { japanDateTime, japanDateTimeInput, utcDate } from '../utils/japanTime'
import { earliestRecordTime } from '../utils/trackingPolicy'
import { recordFields, recordOperation, recordPayload as payload, requestKey as newRequestKey, isRecordOperation } from '../utils/recordOperations'
import useAccountDraft from '../utils/useAccountDraft'
import { DraftRecoveryNotice } from './DraftRecovery'
import AIUseNotice from './AIUseNotice'
import Charts from './Charts'
import CareScope from './CareScope'
import RecordOrganizer from './RecordOrganizer'
import useConnection from '../utils/useConnection'
import { useToast } from './Toast'
import RecordTime, { useRecordClock } from './RecordTime'
import RecordSaveStatus from './RecordSaveStatus'
import { revealElement } from '../utils/focusView'
import { useCareSession, useCareWork } from '../utils/CareSession'
import { CareSubjectFields, CareRecordIdentity, privateSubject, babyKinds } from './CareSubject'
import useDuplicateReview from '../utils/useDuplicateReview'
import DuplicateReview from './DuplicateReview'
import { Button, ConfirmDialog, EmptyState, ErrorMessage, FormField, PageHeader } from './ui'
import './TrackingPanel.css'

const types = ['feeding', 'diaper', 'sleep', 'mood', 'pumping', 'recovery']
const restoredContentMatches = (record, data) => recordFields.every(key => ['timestamp', 'end_timestamp'].includes(key)
  ? (record[key] == null && data[key] == null) || utcDate(record[key]).getTime() === utcDate(data[key]).getTime()
  : (record[key] ?? null) === (data[key] ?? null))

export default function TrackingPanel({ userId, initialEntryType, requestKey = 0, onRecordsChanged, visible = true }) {
  const { t, i18n } = useTranslation()
  const care = useCareSession()
  const [analysisSubject, setAnalysisSubject] = useState('')
  const analysisReady = care.ready && (!analysisSubject || care.subjects.some(item => item.subject_id === analysisSubject))
  const { online, reconnections } = useConnection()
  const now = useRecordClock(visible)
  const toast = useToast()
  const duplicates = useDuplicateReview()
  const [entries, setEntries] = useState([])
  const [entriesLoading, setEntriesLoading] = useState(true)
  const [summary, setSummary] = useState(null)
  const [showAddForm, setShowAddForm] = useState(types.includes(initialEntryType))
  const [entryType, setEntryType] = useState(types.includes(initialEntryType) ? initialEntryType : 'feeding')
  const [editing, setEditing] = useState(null)
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [pendingDelete, setPendingDelete] = useState(null)
  const [deleteObservation, setDeleteObservation] = useState('')
  const [deleteError, setDeleteError] = useState('')
  const [undoEntry, setUndoEntry] = useState(null)
  const [pendingRestore, setPendingRestore] = useState(null)
  const [restoreObservation, setRestoreObservation] = useState('')
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
  const deleteHeading = useRef(null)
  const restoreHeading = useRef(null)
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
  useCareWork('record', pendingSave ? { version: `${pendingSave.data.request_key}:${saveStatus}`, title: duplicates.review ? 'continuity.work.duplicateReview'
    : saveStatus === 'offline' ? 'continuity.work.recordUnsent' : 'continuity.work.recordPending', priority: 0,
    tab: 'tracking', detail: { action: 'resume' }, critical: true, entryType: pendingSave.data.entry_type,
    subjectId: pendingSave.data.subject_id, time: pendingSave.data.timestamp, action: 'workflow.work.checkSave' } : draft.candidate || formDraft ? {
    version: draft.candidate?.updated_at || String(formRevision), title: 'continuity.work.recordRecovery', priority: 3,
    tab: 'tracking', detail: { action: 'resume' }, action: 'workflow.work.continueRecord',
  } : null)
  useCareWork('record-delete', pendingDelete ? {
    version: `${pendingDelete.record_key}:${saveStatus}:${deleteObservation}`,
    title: 'reviewFixes.deletion.pending', priority: 0, critical: true,
    tab: 'tracking', detail: { action: 'resume' }, entryType: pendingDelete.entry_type,
    subjectId: pendingDelete.subject_id, time: pendingDelete.timestamp, action: 'reviewFixes.deletion.check',
  } : null)
  useCareWork('record-restore', pendingRestore ? {
    version: `${pendingRestore.data.request_key}:${saveStatus}:${restoreObservation}`,
    title: ['changed', 'deleted'].includes(restoreObservation) ? 'reviewFixes.restoration.review' : 'reviewFixes.restoration.pending',
    priority: 0, critical: true, tab: 'tracking', detail: { action: 'resume' },
    entryType: pendingRestore.entry.entry_type, subjectId: pendingRestore.entry.subject_id,
    time: pendingRestore.entry.timestamp, action: 'reviewFixes.restoration.check',
  } : null)

  useEffect(() => {
    if (!pendingDelete && !pendingRestore) return
    const warn = event => { event.preventDefault(); event.returnValue = '' }
    window.addEventListener('beforeunload', warn)
    return () => window.removeEventListener('beforeunload', warn)
  }, [pendingDelete, pendingRestore])

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
    if (pendingSave || pendingDelete || pendingRestore || writing.current || loading || draft.candidate || draft.status === 'loading') return
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
    if (initialEntryType?.action === 'resume') { pendingFormFocus.current = true; setFormFocus(value => value + 1); return }
    const record = initialEntryType?.action === 'edit' ? initialEntryType.record : null
    const request = record && types.includes(record.entry_type) && Number.isInteger(record.id)
      && typeof record.record_key === 'string' && Number.isInteger(record.revision) ? { record }
      : types.includes(initialEntryType) ? { entryType: initialEntryType } : null
    if (!request) return
    // Pending writes and recovery drafts must be resolved explicitly, never
    // replaced just because navigation supplied a new target.
    if (pendingSave || pendingDelete || pendingRestore || writing.current || loading || formDraft || draft.candidate) setOpenRequest(request)
    else if (draft.status === 'loading') setOpenRequest({ ...request, autoOpen: true })
    else openRecord(request, false)
  }, [initialEntryType, requestKey, pendingSave, pendingDelete, pendingRestore, loading, formDraft, draft.candidate, draft.status])
  useEffect(() => {
    if (!visible || !openRequest?.autoOpen || draft.status === 'loading') return
    if (pendingSave || pendingDelete || pendingRestore || writing.current || loading || formDraft || draft.candidate) {
      setOpenRequest(previous => ({ ...previous, autoOpen: false })); return
    }
    openRecord(openRequest, false)
  }, [visible, openRequest, pendingSave, pendingDelete, pendingRestore, loading, formDraft, draft.candidate, draft.status])
  useEffect(() => {
    if (visible && pendingDelete && pendingFormFocus.current && revealElement(deleteHeading.current)) pendingFormFocus.current = false
    else if (visible && pendingRestore && pendingFormFocus.current && revealElement(restoreHeading.current)) pendingFormFocus.current = false
    else if (visible && showAddForm && pendingFormFocus.current && revealElement(formHeading.current)) pendingFormFocus.current = false
    else if (visible && pendingFormFocus.current && initialEntryType?.action === 'resume' && revealElement(document.getElementById('tracking-resume-heading'))) pendingFormFocus.current = false
  }, [visible, showAddForm, pendingDelete, pendingRestore, formFocus])

  useEffect(() => {
    if (!undoEntry) return
    const timer = setTimeout(() => setUndoEntry(null), 8000)
    return () => clearTimeout(timer)
  }, [undoEntry])

  useEffect(() => { summaryVersion.current++; setSummary(null) }, [includeProfile, includeParent, includeNotes, i18n.resolvedLanguage])
  useEffect(() => { summaryVersion.current++; setSummary(null); setAcceptedAI(false) }, [analysisSubject, analysisReady])
  useEffect(() => () => { summaryVersion.current++ }, [])

  const refresh = () => {
    summaryVersion.current++; setSummary(null); setAttempt(value => value + 1); onRecordsChanged?.()
  }
  const saveEntry = async formData => {
    if (writing.current || pendingDelete || pendingRestore) return false
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
      if (!pendingSave && !operation.editing && !(await duplicates.check(operation.data))) { setSaveStatus('unsaved'); return false }
      duplicates.clear()
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
    if (writing.current || loading || pendingDelete || pendingRestore) return
    if (pendingSave && !duplicates.review && !window.confirm(t('polish.abandonWrite'))) return
    duplicates.clear()
    unconfirmedRequest.current = null
    setSaveStatus('')
    setPendingSave(null); setFormDraft(null); setRestoredForm(null); setShowAddForm(false); setEditing(null)
    draft.clear(); setAttempt(value => value + 1)
  }
  const finishRemoval = entry => {
    setPendingDelete(null); setDeleteObservation(''); setDeleteError(''); setDeleteTarget(null)
    setUndoEntry({ ...entry, restore_request_key: newRequestKey() })
    if (editing?.record_key === entry.record_key) {
      setEditing(null); setShowAddForm(false); setFormDraft(null); setRestoredForm(null); draft.clear()
    }
    setSaveStatus('removed'); refresh()
  }
  const deletionState = async entry => {
    try {
      const current = await api.getTrackingEntry(entry)
      return current.revision === entry.revision ? 'present' : 'changed'
    } catch (failure) {
      if (failure.status === 404) return 'missing'
      throw failure
    }
  }
  const resolveDeletion = (state, entry) => {
    if (state === 'missing') { finishRemoval(entry); return true }
    if (state === 'changed') {
      // The original revision can no longer delete the updated record.
      setPendingDelete(null); setDeleteObservation(''); setDeleteTarget(null); setSaveStatus('')
      toast.error(t('work.recordConflict')); refresh(); return true
    }
    return false
  }
  const checkDeletion = async () => {
    if (!pendingDelete || writing.current || loading) return
    const entry = pendingDelete
    writing.current = true; setLoading(true); setSaveStatus('removeChecking'); setDeleteObservation('')
    try {
      const state = await deletionState(entry)
      if (!resolveDeletion(state, entry)) {
        // A read cannot prove an earlier timed-out request has finished.
        setDeleteObservation('present'); setSaveStatus('removeFailed'); refresh()
      }
    } catch { setDeleteObservation('checkFailed'); setSaveStatus('removeFailed') }
    finally { writing.current = false; setLoading(false) }
  }
  const removeEntry = async entry => {
    if (!entry || writing.current || loading || pendingSave || pendingRestore
      || (pendingDelete && pendingDelete.record_key !== entry.record_key)) return false
    if (!online || navigator.onLine === false) { setDeleteError('offline'); return false }
    const retrying = Boolean(pendingDelete)
    const snapshot = pendingDelete || { ...entry }
    writing.current = true; setLoading(true); setDeleteError(''); setSaveStatus('removing')
    try {
      // A retry first reads the original identity, so a committed deletion is
      // reconciled with Undo instead of reporting a misleading 404 conflict.
      if (retrying && resolveDeletion(await deletionState(snapshot), snapshot)) return true
      setPendingDelete(snapshot); setDeleteObservation('')
      await api.deleteTrackingEntry(snapshot.id, snapshot)
      finishRemoval(snapshot)
      return true
    } catch (err) {
      if (err.status === 404 && retrying) { finishRemoval(snapshot); return true }
      if (err.status === 409 || err.status === 404) {
        setPendingDelete(null); setDeleteTarget(null); setSaveStatus(''); toast.error(t('work.recordConflict')); refresh()
        return true
      }
      if (retrying || err.resultUnconfirmed || !err.status || err.status >= 500) {
        setPendingDelete(snapshot); setDeleteTarget(null); setDeleteObservation(''); setSaveStatus('removeFailed')
        toast.error(t('work.deleteFailed')); return true
      }
      setPendingDelete(null); setSaveStatus(''); setDeleteError('rejected'); return false
    }
    finally { writing.current = false; setLoading(false) }
  }
  const resolveRestoration = (result, operation) => {
    if (result.state === 'saved' && result.record) {
      // Creation receipts can outlive later edits. Only the current owner-read
      // record can confirm that the original contents are still restored.
      if (result.record.revision === 1 && restoredContentMatches(result.record, operation.data)) {
        const age = Math.floor((Date.now() - utcDate(operation.data.timestamp).getTime()) / 86400000)
        if (age >= recordRange) setRecordRange(age < 30 ? 30 : age < 90 ? 90 : 365)
        setPendingRestore(null); setRestoreObservation(''); setSaveStatus('restored')
        refresh(); toast.success(t('work.restored'))
      } else {
        setRestoreObservation('changed'); setSaveStatus('restoreChanged'); refresh()
      }
      return true
    }
    if (result.state === 'deleted') {
      // Never generate a new key or recreate a restored record that was deleted.
      setRestoreObservation('deleted'); setSaveStatus('restoreDeleted'); refresh(); return true
    }
    if (result.state !== 'not_found') throw new Error('Restore result unavailable')
    setRestoreObservation('notFound'); setSaveStatus(operation.attempted ? 'restoreFailed' : 'restoreUnsent')
    return false
  }
  const checkRestoration = async () => {
    if (!pendingRestore || writing.current || loading) return
    const operation = pendingRestore
    writing.current = true; setLoading(true); setSaveStatus('restoreChecking')
    try { resolveRestoration(await api.get(`/api/tracking/operations/${operation.data.request_key}`), operation) }
    catch { setRestoreObservation('checkFailed'); setSaveStatus(operation.attempted ? 'restoreFailed' : 'restoreUnsent') }
    finally { writing.current = false; setLoading(false) }
  }
  const restoreEntry = async () => {
    if ((!undoEntry && !pendingRestore) || writing.current || loading || pendingSave || pendingDelete
      || ['changed', 'deleted'].includes(restoreObservation)) return
    const operation = pendingRestore || { entry: { ...undoEntry },
      data: { ...payload(undoEntry), request_key: undoEntry.restore_request_key }, attempted: false }
    // Undo's eight-second offer expires independently. Once accepted, this frozen
    // operation survives until confirmation or the user's explicit abandonment.
    setPendingRestore(operation); setUndoEntry(null); setRestoreObservation('')
    if (!online || navigator.onLine === false) {
      setRestoreObservation('offline'); setSaveStatus(operation.attempted ? 'restoreFailed' : 'restoreUnsent'); return
    }
    writing.current = true; setLoading(true); setSaveStatus('restoring')
    let checking = operation.attempted
    try {
      if (operation.attempted && resolveRestoration(await api.get(`/api/tracking/operations/${operation.data.request_key}`), operation)) return
      const attempted = { ...operation, attempted: true }
      setPendingRestore(attempted); setRestoreObservation(''); setSaveStatus('restoring'); checking = false
      await api.addTrackingEntry(operation.data)
      checking = true; setSaveStatus('restoreChecking')
      resolveRestoration(await api.get(`/api/tracking/operations/${operation.data.request_key}`), attempted)
    } catch (failure) {
      setRestoreObservation(checking ? 'checkFailed' : failure.status === 409 ? 'conflict'
        : failure.status >= 400 && failure.status < 500 ? 'rejected' : '')
      setSaveStatus('restoreFailed'); toast.error(t('reviewFixes.restoration.unconfirmed'))
    } finally { writing.current = false; setLoading(false) }
  }
  const loadSummary = async () => {
    if (!acceptedAI || summaryLoading || !analysisReady) return
    setSummaryLoading(true)
    const version = ++summaryVersion.current
    const scope = { include_profile: includeProfile, include_parent: includeParent, include_notes: includeNotes,
      ...(analysisSubject ? { subject_id: analysisSubject, unassigned: false } : { unassigned: true }),
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
    <PageHeader titleId="tracking-resume-heading" title={t('tracking.title')} description={t('pilot.noPressure')}
      actions={<Button variant={showAddForm ? 'secondary' : 'primary'} disabled={loading || Boolean(pendingDelete) || Boolean(pendingRestore) || (!showAddForm && (Boolean(draft.candidate) || draft.status === 'loading'))} onClick={() => {
        if (showAddForm) cancelForm()
        else openRecord({ entryType })
      }}>{showAddForm ? t('tracking.cancel') : `+ ${t('tracking.addEntry')}`}</Button>} />
    <DraftRecoveryNotice draft={draft} disabled={loading || Boolean(pendingDelete) || Boolean(pendingRestore)} />
    {openRequest && <section className="record-open-request" aria-label={t('friendly.record.incoming')}>
      <p>{t('friendly.record.incoming')}</p>
      {openRequest.record && <><strong>{t(`tracking.${openRequest.record.entry_type}`)}</strong><RecordTime value={openRequest.record.timestamp} now={now} /></>}
      {(pendingSave || pendingDelete || pendingRestore || draft.candidate || draft.status === 'loading') && <p>{t(pendingRestore ? 'reviewFixes.restoration.pending'
        : pendingDelete ? 'reviewFixes.deletion.pending' : 'friendly.record.resolveDraft')}</p>}
      <div className="pilot-actions">
        <button type="button" className="pilot-button secondary" disabled={loading || Boolean(pendingSave) || Boolean(pendingDelete) || Boolean(pendingRestore) || Boolean(draft.candidate) || draft.status === 'loading'}
          onClick={() => openRecord(openRequest)}>{t('friendly.record.open')}</button>
        <button type="button" className="pilot-button secondary" onClick={() => setOpenRequest(null)}>{t('friendly.record.discardOpen')}</button>
      </div>
    </section>}
    <RecordSaveStatus status={saveStatus} />
    {pendingDelete && <section className="pilot-panel" aria-labelledby="tracking-delete-pending">
      <h3 id="tracking-delete-pending" ref={deleteHeading} tabIndex={-1}>{t('reviewFixes.deletion.pending')}</h3>
      <strong>{t(`tracking.${pendingDelete.entry_type}`)}</strong><CareRecordIdentity record={pendingDelete} />
      <RecordTime value={pendingDelete.timestamp} now={now} /><p>{t('reviewFixes.deletion.notice')}</p>
      {deleteObservation && <p role="status">{t(`reviewFixes.deletion.${deleteObservation}`)}</p>}
      <div className="pilot-actions">
        <Button variant="secondary" disabled={loading} onClick={checkDeletion}>{t('reviewFixes.deletion.check')}</Button>
        <Button variant="secondary" disabled={loading} onClick={() => { setDeleteError(''); setDeleteTarget(pendingDelete) }}>{t('reviewFixes.deletion.retry')}</Button>
        <Button variant="quiet" disabled={loading} onClick={() => {
          if (!window.confirm(t('reviewFixes.deletion.abandonConfirm'))) return
          setPendingDelete(null); setDeleteObservation(''); setDeleteTarget(null); setSaveStatus(''); refresh()
        }}>{t('reviewFixes.deletion.abandon')}</Button>
      </div>
    </section>}
    {pendingRestore && <section className="pilot-panel" aria-labelledby="tracking-restore-pending">
      <h3 id="tracking-restore-pending" ref={restoreHeading} tabIndex={-1}>{t('reviewFixes.restoration.review')}</h3>
      <strong>{t(`tracking.${pendingRestore.entry.entry_type}`)}</strong><CareRecordIdentity record={pendingRestore.entry} />
      <RecordTime value={pendingRestore.entry.timestamp} now={now} /><p>{t('reviewFixes.restoration.notice')}</p>
      {restoreObservation && <p role="status">{t(`reviewFixes.restoration.${restoreObservation}`)}</p>}
      <div className="pilot-actions">
        <Button variant="secondary" disabled={loading} onClick={checkRestoration}>{t('reviewFixes.restoration.check')}</Button>
        <Button variant="secondary" disabled={loading || ['changed', 'deleted'].includes(restoreObservation)} onClick={restoreEntry}>{t('reviewFixes.restoration.retry')}</Button>
        <Button variant="quiet" disabled={loading} onClick={() => {
          if (!window.confirm(t('reviewFixes.restoration.abandonConfirm'))) return
          setPendingRestore(null); setRestoreObservation(''); setSaveStatus(''); refresh()
        }}>{t('reviewFixes.restoration.abandon')}</Button>
      </div>
    </section>}
    <DuplicateReview review={duplicates.review} disabled={loading} onContinue={() => saveEntry()} onCancel={() => {
      duplicates.clear(); setPendingSave(null); setSaveStatus(''); draft.clear()
    }} />
    {pendingSave && <button type="button" className="pilot-button secondary" disabled={loading} onClick={() => setAttempt(value => value + 1)}>{t('flows.connection.checkRecords')}</button>}
    {pendingSave && <p>{t('localCare.record.retryHint')} {japanDateTime(pendingSave.data.timestamp, i18n.resolvedLanguage || 'ja')}</p>}
    {showAddForm && <div ref={formHeading} tabIndex={-1} className="record-form-region" role="region" aria-label={t(editing ? 'work.editRecord' : 'tracking.addEntry')}>
      <EntryForm key={`${editing ? `edit:${editing.record_key}:${editing.revision}` : 'new'}:${formRevision}`}
      entryType={entryType} initialEntry={editing} restored={restoredForm} onDraftChange={setFormDraft} locked={Boolean(pendingSave)}
      onEntryTypeChange={setEntryType} onSubmit={saveEntry} onCancel={cancelForm} loading={loading || Boolean(pendingDelete) || Boolean(pendingRestore) || Boolean(duplicates.review)} saving={saveStatus === 'saving'} /></div>}
    {undoEntry && <div className="pilot-panel undo-notice" role="status"><p>{t('work.lastDeleted')}</p>
      <button className="pilot-button secondary" disabled={loading || Boolean(pendingSave) || Boolean(pendingDelete) || Boolean(pendingRestore)} onClick={restoreEntry}>{t('work.undoDelete')}</button></div>}
    <section className="entries-list"><h3>{t('tracking.recentEntries')}</h3><p>{t('pilot.japanTime')}</p>
      <FormField as="select" label={t('work.recordPeriod')} value={recordRange} disabled={loading} onChange={event => setRecordRange(Number(event.target.value))}>
        {[7, 30, 90, 365].map(days => <option key={days} value={days}>{t('work.rangeDays', { days })}</option>)}
      </FormField>
      {error && <ErrorMessage title={error} onRetry={() => setAttempt(value => value + 1)} />}
      {entriesLoading && <p role="status">{t('common.loading')}</p>}
      {!error && !entriesLoading && entries.length === 0 && <EmptyState compact icon={false} suggestions={[]}
        title={t('tracking.noEntries')} description="" />}
      {entries.map(entry => <article key={entry.record_key} className="tracking-entry-card">
        <div className="entry-header"><strong>{t(`tracking.${entry.entry_type}`)}</strong><RecordTime value={entry.timestamp} now={now} /></div>
        <div className="entry-details">
          <CareRecordIdentity record={entry} />
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
        <div className="pilot-actions"><button className="pilot-button secondary" disabled={loading || Boolean(pendingSave) || Boolean(pendingDelete) || Boolean(pendingRestore) || Boolean(draft.candidate) || draft.status === 'loading'} onClick={() => {
          openRecord({ record: entry })
        }}>{t('work.editRecord')}</button>
          <Button variant="secondary" disabled={loading || Boolean(pendingSave) || Boolean(pendingDelete) || Boolean(pendingRestore)} onClick={() => {
            setDeleteError(''); setDeleteTarget(entry)
          }}>{t('common.delete')}</Button></div>
      </article>)}
    </section>
    <ConfirmDialog open={visible && Boolean(deleteTarget)} danger title={t('work.deleteConfirm')}
      description={deleteTarget ? <><strong>{t(`tracking.${deleteTarget.entry_type}`)}</strong>
        <CareRecordIdentity record={deleteTarget} /><RecordTime value={deleteTarget.timestamp} now={now} /></> : undefined}
      confirmLabel={t('work.confirmDelete')} busy={loading || Boolean(pendingSave) || Boolean(pendingRestore)}
      error={deleteError ? t(`reviewFixes.deletion.${deleteError}`) : undefined}
      onConfirm={() => removeEntry(deleteTarget)} onClose={() => setDeleteTarget(null)} />
    <RecordOrganizer visible={visible} blocked={loading || Boolean(pendingSave) || Boolean(pendingDelete) || Boolean(pendingRestore)} onRecordsChanged={refresh}
      openRequest={initialEntryType?.action === 'organize' ? requestKey : 0} />
    <details className="pilot-panel"><summary>{t('pilot.optionalAnalysis')}</summary>
      <CareScope subjectId={analysisSubject} mode="analysis" disabled={summaryLoading} onUseLast={id => {
        setAnalysisSubject(id); setAcceptedAI(false); setSummary(null); summaryVersion.current++
      }} />
      <label>{t('reviewFixes.analysisSubject')}<select value={analysisSubject} disabled={summaryLoading || !care.ready}
        onChange={event => { care.rememberSubject(event.target.value); setAnalysisSubject(event.target.value); setAcceptedAI(false); setSummary(null); summaryVersion.current++ }}>
        <option value="">{t('reviewFixes.unassigned')}</option>
        {analysisSubject && !care.subjects.some(item => item.subject_id === analysisSubject) && <option value={analysisSubject}>{t('reviewFixes.unavailable')}</option>}
        {care.subjects.map(item => <option key={item.subject_id} value={item.subject_id}>{item.nickname}{item.family_name ? ` · ${item.family_name}` : ''}</option>)}
      </select></label>
      <p>{t('reviewFixes.analysisScope')}</p>
      {!analysisReady && <p role="status">{t('reviewFixes.analysisUnavailable')} <button type="button" className="text-action" onClick={care.reload}>{t('pilot.retry')}</button></p>}
      <button className="pilot-button secondary" onClick={() => setShowCharts(value => !value)}>{t(showCharts ? 'tracking.hideCharts' : 'tracking.showCharts')}</button>
      {showCharts && analysisReady && <Charts key={analysisSubject || 'unassigned'} userId={userId} subjectId={analysisSubject} refreshKey={attempt} visible={visible}
        onRecord={!loading && !pendingSave && !pendingDelete && !pendingRestore && !draft.candidate && draft.status !== 'loading' ? () => openRecord({ entryType }) : undefined} />}
      <AIUseNotice scope="records" accepted={acceptedAI} onChange={setAcceptedAI} disabled={summaryLoading || !analysisReady}
        profileLabel={t('reviewFixes.analysisProfile')}
        includeProfile={includeProfile} onProfileChange={setIncludeProfile} includeParent={includeParent} onParentChange={setIncludeParent}
        includeNotes={includeNotes} onNotesChange={setIncludeNotes} />
      <p>{t('reviewFixes.analysisProfileNotice')}</p>
      <button className="pilot-button secondary" disabled={!acceptedAI || !analysisReady || summaryLoading || entriesLoading || !entries.some(entry =>
        (babyKinds.includes(entry.entry_type) && (entry.subject_id || '') === analysisSubject) || (includeParent && ['mood', 'recovery'].includes(entry.entry_type)))} onClick={loadSummary}>{t(summaryLoading ? 'common.loading' : 'pilot.analyzeRecords')}</button>
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
  const care = useCareSession()
  const [formData, setFormData] = useState(restored?.formData || (initialEntry ? payload(initialEntry) : privateSubject(babyKinds.includes(entryType) ? care.activeId : '')))
  const [hasEnd, setHasEnd] = useState(Boolean((restored?.formData || initialEntry)?.end_timestamp))
  const [when, setWhen] = useState(restored?.when || (initialEntry ? 'specific' : 'now'))
  const [recordedAt, setRecordedAt] = useState(restored?.recordedAt || japanDateTimeInput(initialEntry?.timestamp || new Date()))
  const [error, setError] = useState('')
  const previousType = useRef(entryType)
  useEffect(() => {
    const meaningful = when === 'specific' || Object.entries(formData).some(([key, value]) =>
      !['subject_id', 'family_shared', 'sharing_revision'].includes(key) && value !== null && value !== undefined && value !== '')
    onDraftChange(meaningful ? { formData, when, recordedAt } : null)
  }, [formData, when, recordedAt, onDraftChange])
  useEffect(() => {
    if (previousType.current === entryType) return
    previousType.current = entryType
    // Keep the same form instance, date/time and common note, including home shortcuts.
    setFormData(previous => ({ ...privateSubject(babyKinds.includes(entryType) ? previous.subject_id : ''), end_timestamp: null, notes: previous.notes || '' }))
    setHasEnd(false)
    setError('')
  }, [entryType])
  const feedingMethod = formData.feeding_type
  const displayStart = initialEntry && when === 'specific' && recordedAt === japanDateTimeInput(initialEntry.timestamp)
    ? utcDate(initialEntry.timestamp) : when === 'now' ? new Date() : new Date(`${recordedAt}:00+09:00`)
  const displayEnd = formData.end_timestamp ? utcDate(formData.end_timestamp) : null
  const displayMinutes = displayEnd && Number.isFinite(displayEnd.getTime()) && Number.isFinite(displayStart.getTime()) && displayEnd >= displayStart
    ? Math.floor((displayEnd - displayStart) / 60000) : ''
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
      disabled={hasEnd && key.endsWith('_minutes')} min="0" step={key.endsWith('_minutes') ? '1' : '0.1'} value={hasEnd && key.endsWith('_minutes') ? displayMinutes : formData[key] ?? ''}
      onChange={event => setFormData({ ...formData, [key]: event.target.value === '' ? null : Number(event.target.value) })} /></label>
  return <form className="entry-form" onSubmit={event => {
    event.preventDefault()
    if (loading) return
    if (locked) { onSubmit(); return }
    const date = when === 'now' ? new Date() : new Date(`${recordedAt}:00+09:00`)
    if (!Number.isFinite(date.getTime()) || date.getTime() > Date.now() + 60000) { setError(t('work.invalidTime')); return }
    if (date < earliestRecordTime()) { setError(t('work.recordTooOld')); return }
    const unchangedTime = initialEntry && when === 'specific' && recordedAt === japanDateTimeInput(initialEntry.timestamp)
    const timestamp = unchangedTime ? utcDate(initialEntry.timestamp).toISOString() : date.toISOString()
    const interval = { end_timestamp: hasEnd ? formData.end_timestamp : null }
    if (hasEnd) {
      const ended = utcDate(formData.end_timestamp)
      if (!formData.end_timestamp || !Number.isFinite(ended.getTime()) || ended < utcDate(timestamp) || ended.getTime() > Date.now() + 60000) { setError(t('work.invalidTime')); return }
      interval[entryType === 'feeding' ? 'duration_minutes' : 'sleep_duration_minutes'] = Math.floor((ended - utcDate(timestamp)) / 60000)
    }
    setError('')
    onSubmit({ ...formData, ...interval, entry_type: entryType, timestamp })
  }}><fieldset disabled={loading || locked}>
    <legend>{t(initialEntry ? 'work.editRecord' : 'tracking.addEntry')}</legend>
    {initialEntry && <p>{t('work.recordTypeChangeNotice')}</p>}
    <label>{t('tracking.entryType')}<select value={entryType} onChange={event => {
      onEntryTypeChange(event.target.value)
    }}>
      {[['babyGroup', ['feeding', 'diaper', 'sleep', 'pumping']], ['selfGroup', ['mood', 'recovery']]].map(([group, options]) =>
        <optgroup key={group} label={t(`localCare.record.${group}`)}>{options.map(type => <option key={type} value={type}>{t(`tracking.${type}`)}</option>)}</optgroup>)}
    </select></label>
    <CareSubjectFields value={formData} kind={entryType} onChange={scope => setFormData(previous => ({ ...previous, ...scope }))} />
    <label>{t('work.recordTime')}<select value={when} onChange={event => setWhen(event.target.value)}>
      <option value="now">{t('work.now')}</option><option value="specific">{t('work.chooseTime')}</option>
    </select></label>
    {when === 'specific' && <label>{t('pilot.japanTime')}<input type="datetime-local" required value={recordedAt}
      min={japanDateTimeInput(earliestRecordTime())} max={japanDateTimeInput()} onChange={event => setRecordedAt(event.target.value)} /></label>}
    <p>{t('work.recordWindowNotice')}</p>
    {['feeding', 'sleep'].includes(entryType) && <>
      <label><input type="checkbox" checked={hasEnd} onChange={event => { setHasEnd(event.target.checked); setFormData(previous => ({ ...previous, end_timestamp: null })) }} />{t('continuity.period.keepEnd')}</label>
      {hasEnd && <label>{t('interaction.timer.endTime')}<input type="datetime-local" required max={japanDateTimeInput()}
        value={formData.end_timestamp ? japanDateTimeInput(formData.end_timestamp) : ''} onChange={event => {
          const value = event.target.value
          const date = new Date(`${value}:00+09:00`)
          setFormData(previous => ({ ...previous, end_timestamp: value && Number.isFinite(date.getTime()) ? date.toISOString() : null }))
        }} /></label>}
      {hasEnd && <p>{t('continuity.period.deriveDuration')}</p>}
    </>}
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
