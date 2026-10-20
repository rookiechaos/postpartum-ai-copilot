import React, { forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../utils/api'
import { japanDateTimeInput, utcDate } from '../utils/japanTime'
import { earliestRecordTime } from '../utils/trackingPolicy'
import { recordFields, recordPayload } from '../utils/recordOperations'
import RecordSaveStatus from './RecordSaveStatus'
import { CareSubjectFields, privateSubject } from './CareSubject'

const measurements = {
  feeding: [['duration_minutes', 'duration'], ['amount_ml', 'amount']],
  sleep: [['sleep_duration_minutes', 'duration']], pumping: [['pumped_amount_ml', 'amount']],
}
const sameRecord = (stored, operation) => recordFields.every(key => ['timestamp', 'end_timestamp'].includes(key)
  ? (stored[key] == null && operation[key] == null) || utcDate(stored[key]).getTime() === utcDate(operation[key]).getTime()
  : (stored[key] ?? null) === (operation[key] ?? null))

// The ref lets the containing sheet ask before dismissing unsaved work.
const RecordEditor = forwardRef(function RecordEditor({ record, mode = 'time', onSaved, onCancel }, ref) {
  const { t } = useTranslation()
  const [base, setBase] = useState(null)
  const [values, setValues] = useState({})
  const [time, setTime] = useState('')
  const [endTime, setEndTime] = useState(null)
  const [status, setStatus] = useState('loading')
  const [error, setError] = useState('')
  const [pending, setPending] = useState(null)
  const [attempt, setAttempt] = useState(0)
  const writing = useRef(false)
  const uncertain = useRef(false)
  const dirty = Boolean(base && (time !== japanDateTimeInput(base.timestamp)
    || endTime !== (base.end_timestamp ? japanDateTimeInput(base.end_timestamp) : null)
    || Object.keys(values).some(key => values[key] !== (base[key] ?? null))))
  const canClose = () => !writing.current && (!(dirty || pending)
    || window.confirm(t(pending ? 'polish.abandonWrite' : 'interaction.record.discard')))
  useImperativeHandle(ref, () => ({ canClose }))
  useEffect(() => {
    let active = true
    setStatus('loading'); setError('')
    api.getTrackingEntry(record).then(result => {
      if (!active) return
      setBase(result); setTime(japanDateTimeInput(result.timestamp))
      setEndTime(result.end_timestamp ? japanDateTimeInput(result.end_timestamp) : null)
      setValues({ ...privateSubject(result.subject_id), family_shared: result.family_shared, sharing_revision: result.sharing_revision,
        ...Object.fromEntries((measurements[result.entry_type] || []).map(([key]) => [key, result[key] ?? null])) })
      setStatus('')
    }).catch(failure => { if (active) { setStatus(''); setError(failure.status === 404 ? 'missing' : 'load') } })
    return () => { active = false }
  }, [record.id, record.record_key, attempt])
  useEffect(() => {
    if (!dirty && !pending) return
    const warn = event => { event.preventDefault(); event.returnValue = '' }
    window.addEventListener('beforeunload', warn)
    return () => window.removeEventListener('beforeunload', warn)
  }, [dirty, pending])
  const accept = result => {
    uncertain.current = false; setPending(null); setBase(result); setStatus('saved'); setError('')
    setTime(japanDateTimeInput(result.timestamp))
    setEndTime(result.end_timestamp ? japanDateTimeInput(result.end_timestamp) : null)
    setValues({ ...privateSubject(result.subject_id), family_shared: result.family_shared, sharing_revision: result.sharing_revision,
      ...Object.fromEntries((measurements[result.entry_type] || []).map(([key]) => [key, result[key] ?? null])) })
    onSaved(result)
  }
  const check = async () => {
    if (writing.current || !pending) return
    writing.current = true; setStatus('loading'); setError('')
    try {
      const current = await api.getTrackingEntry(record)
      if (sameRecord(current, pending)) accept(current)
      else if (current.revision !== pending.revision) { setStatus('unconfirmed'); setError('conflict') }
      else { setStatus(uncertain.current ? 'unconfirmed' : 'unsaved'); setError('notApplied') }
    } catch (failure) { setStatus('unconfirmed'); setError(failure.status === 404 ? 'missing' : 'load') }
    finally { writing.current = false }
  }
  const save = async event => {
    event.preventDefault()
    if (writing.current || !base || error === 'conflict' || error === 'missing') return
    const date = time === japanDateTimeInput(base.timestamp) ? utcDate(base.timestamp) : new Date(`${time}:00+09:00`)
    if (!Number.isFinite(date.getTime()) || date.getTime() > Date.now() + 60000 || date < earliestRecordTime()) {
      setError('invalidTime'); return
    }
    const ended = endTime === null ? null : base.end_timestamp && endTime === japanDateTimeInput(base.end_timestamp)
      ? utcDate(base.end_timestamp) : new Date(`${endTime}:00+09:00`)
    if (!pending && ended && (!Number.isFinite(ended.getTime()) || ended < date || ended.getTime() > Date.now() + 60000)) { setError('invalidTime'); return }
    const operation = pending || { ...recordPayload(base), ...values, timestamp: date.toISOString(),
      end_timestamp: ended?.toISOString() || null,
      record_key: base.record_key, revision: base.revision }
    if (!pending && operation.end_timestamp) {
      operation[base.entry_type === 'feeding' ? 'duration_minutes' : 'sleep_duration_minutes'] = Math.floor((utcDate(operation.end_timestamp) - date) / 60000)
    }
    setPending(operation)
    if (navigator.onLine === false) { setStatus(uncertain.current ? 'unconfirmed' : 'offline'); return }
    writing.current = true; setStatus('saving'); setError('')
    try { accept(await api.updateTrackingEntry(base.id, operation)) }
    catch (failure) {
      if (!(failure.status >= 400 && failure.status < 500)) uncertain.current = true
      setStatus(uncertain.current ? 'unconfirmed' : 'unsaved')
      if ([404, 409].includes(failure.status)) setError(failure.status === 404 ? 'missing' : 'conflict')
      else if (failure.status === 422) { setError('invalid'); if (!uncertain.current) setPending(null) }
    } finally { writing.current = false }
  }
  const busy = ['saving', 'loading'].includes(status)
  const displayedStatus = !dirty && !pending && status === 'unsaved' ? '' : status
  const displayStart = base && time === japanDateTimeInput(base.timestamp) ? utcDate(base.timestamp) : new Date(`${time}:00+09:00`)
  const displayEnd = endTime === null ? null : base?.end_timestamp && endTime === japanDateTimeInput(base.end_timestamp)
    ? utcDate(base.end_timestamp) : new Date(`${endTime}:00+09:00`)
  const displayMinutes = displayEnd && Number.isFinite(displayEnd.getTime()) && Number.isFinite(displayStart.getTime()) && displayEnd >= displayStart
    ? Math.floor((displayEnd - displayStart) / 60000) : ''
  return <form className="record-compact-editor" onSubmit={save}>
    <p>{t('interaction.record.editNotice')}</p>
    <fieldset disabled={busy || Boolean(pending) || !base || error === 'missing' || error === 'conflict'}>
      <legend>{t(`interaction.record.${mode === 'quantity' ? 'quantity' : 'time'}`)}</legend>
      {base && <CareSubjectFields value={values} kind={base.entry_type} onChange={scope => {
        setValues(previous => ({ ...previous, ...scope })); setStatus('unsaved'); setError('')
      }} />}
      <label>{t('work.recordTime')}<input type="datetime-local" required value={time}
        min={japanDateTimeInput(earliestRecordTime())} max={japanDateTimeInput()} onChange={event => {
          setTime(event.target.value); setStatus('unsaved'); setError('')
        }} /></label>
      {['feeding', 'sleep'].includes(base?.entry_type) && <>
        <label><input type="checkbox" checked={endTime !== null} onChange={event => { setEndTime(event.target.checked ? '' : null); setStatus('unsaved'); setError('') }} />{t('continuity.period.keepEnd')}</label>
        {endTime !== null && <label>{t('interaction.timer.endTime')}<input type="datetime-local" required value={endTime} max={japanDateTimeInput()}
          onChange={event => { setEndTime(event.target.value); setStatus('unsaved'); setError('') }} /></label>}
        {endTime !== null && <p>{t('continuity.period.deriveDuration')}</p>}
      </>}
      {(measurements[base?.entry_type] || []).map(([key, label]) => <label key={key}>{t(`tracking.${label}`)} {key.endsWith('_ml') ? '(mL)' : `(${t('pilot.minutes')})`}
        <input type="number" inputMode={key.endsWith('_minutes') ? 'numeric' : 'decimal'} min="0" step={key.endsWith('_minutes') ? '1' : '0.1'}
          disabled={endTime !== null && key.endsWith('_minutes')}
          value={endTime !== null && key.endsWith('_minutes') ? displayMinutes : values[key] ?? ''} onChange={event => {
            const value = event.target.value === '' ? null : Number(event.target.value)
            setValues(previous => ({ ...previous, [key]: value })); setStatus('unsaved'); setError('')
          }} />
      </label>)}
    </fieldset>
    {status === 'loading' ? <p role="status">{t('common.loading')}</p> : <RecordSaveStatus status={displayedStatus} />}
    {error && <p role="alert">{t(`interaction.record.errors.${error}`)}</p>}
    <div className="pilot-actions">
      <button type="submit" className="pilot-button" disabled={busy || !base || ['missing', 'conflict'].includes(error) || (!dirty && !pending)}>
        {t(pending ? 'localCare.record.resend' : 'work.saveChanges')}</button>
      {pending && <button type="button" className="pilot-button secondary" disabled={busy} onClick={check}>{t('localCare.record.check')}</button>}
      {!pending && !base && error === 'load' && <button type="button" className="pilot-button secondary" disabled={busy} onClick={() => setAttempt(value => value + 1)}>{t('pilot.retry')}</button>}
      {error === 'conflict' && <button type="button" className="pilot-button secondary" disabled={busy} onClick={() => {
        if (!window.confirm(t('interaction.record.reload'))) return
        uncertain.current = false; setPending(null); setAttempt(value => value + 1)
      }}>{t('flows.overview.reload')}</button>}
      <button type="button" className="pilot-button secondary" disabled={busy} onClick={() => { if (canClose()) onCancel() }}>{t(status === 'saved' && !dirty ? 'interaction.close' : 'tracking.cancel')}</button>
    </div>
  </form>
})
export default RecordEditor
