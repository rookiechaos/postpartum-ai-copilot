import React, { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../utils/api'
import { japanDateTime, japanDateTimeInput, utcDate } from '../utils/japanTime'
import { earliestRecordTime } from '../utils/trackingPolicy'
import { isRecordOperation, recordOperation, requestKey } from '../utils/recordOperations'
import useAccountDraft from '../utils/useAccountDraft'
import { DraftRecoveryNotice } from './DraftRecovery'
import RecordSaveStatus from './RecordSaveStatus'
import { useCareSession, useCareWork } from '../utils/CareSession'
import { CareSubjectFields, privateSubject } from './CareSubject'
import useDuplicateReview from '../utils/useDuplicateReview'
import DuplicateReview from './DuplicateReview'

const validTimer = value => value && ['feeding', 'sleep'].includes(value.entry_type)
  && typeof value.started_at === 'string' && Number.isFinite(utcDate(value.started_at).getTime())
  && (value.ended_at === null || (typeof value.ended_at === 'string' && Number.isFinite(utcDate(value.ended_at).getTime())))
  && isRecordOperation({ entry_type: value.entry_type, timestamp: value.started_at, request_key: value.request_key })

export default function CareTimer({ userId, visible, requestedKind, requestVersion, blocked, onRecordsChanged, onLocate }) {
  const { t, i18n } = useTranslation()
  const care = useCareSession()
  const duplicates = useDuplicateReview()
  const [subjectScope, setSubjectScope] = useState(null)
  const [lastSaved, setLastSaved] = useState(null)
  const [kind, setKind] = useState('feeding')
  const [side, setSide] = useState('')
  const [timer, setTimer] = useState(null)
  const [start, setStart] = useState('')
  const [end, setEnd] = useState('')
  const [pending, setPending] = useState(null)
  const [status, setStatus] = useState('')
  const [error, setError] = useState('')
  const [returned, setReturned] = useState(false)
  const [confirmed, setConfirmed] = useState(false)
  const [clock, setClock] = useState(Date.now)
  const [expanded, setExpanded] = useState(false)
  const activeView = visible && expanded
  const writing = useRef(false)
  const uncertain = useRef(false)
  const hidden = useRef(false)
  const content = timer ? { timer, start, end, side, pending, subjectScope } : null
  const draft = useAccountDraft('timer', userId, content, value => {
    if (!validTimer(value.timer) || (value.pending && (!isRecordOperation(value.pending)
      || value.pending.request_key !== value.timer.request_key || value.pending.entry_type !== value.timer.entry_type
      || !value.timer.ended_at))) return false
    setTimer(value.timer); setKind(value.timer.entry_type)
    setStart(typeof value.start === 'string' ? value.start : japanDateTimeInput(value.timer.started_at))
    setEnd(typeof value.end === 'string' ? value.end : value.timer.ended_at ? japanDateTimeInput(value.timer.ended_at) : '')
    setSide(['left', 'right', 'both'].includes(value.side) ? value.side : '')
    setSubjectScope(value.subjectScope || privateSubject(''))
    setPending(value.pending || null); uncertain.current = Boolean(value.pending)
    setStatus(value.pending ? 'unconfirmed' : ''); setReturned(true); setConfirmed(false)
  })
  useCareWork('timer', timer ? { version: `${timer.request_key}:${timer.ended_at || 'running'}:${status}`,
    title: duplicates.review ? 'continuity.work.duplicateReview' : pending && status === 'offline' ? 'continuity.work.recordUnsent'
      : pending ? 'continuity.work.timerPending' : timer.ended_at ? 'continuity.work.timerReview' : 'continuity.work.timerRunning',
    priority: pending ? 0 : 1, tab: 'dashboard', detail: { section: 'care-timer-heading' } } : draft.candidate ? {
    version: draft.candidate.updated_at, title: 'continuity.work.timerRecovery', priority: 2,
    tab: 'dashboard', detail: { section: 'care-timer-heading' },
  } : null)
  useEffect(() => {
    if (['feeding', 'sleep'].includes(requestedKind)) {
      setExpanded(true)
      if (!timer) setKind(requestedKind)
    }
  }, [requestVersion, requestedKind])
  useEffect(() => {
    if (!timer || timer.ended_at) return
    if (!activeView) { hidden.current = true; return }
    const update = () => {
      if (document.visibilityState !== 'visible') { hidden.current = true; return }
      setClock(Date.now())
      if (hidden.current) { setReturned(true); setConfirmed(false); hidden.current = false }
    }
    update()
    const interval = setInterval(update, 1000)
    document.addEventListener('visibilitychange', update)
    return () => { clearInterval(interval); document.removeEventListener('visibilitychange', update) }
  }, [activeView, timer?.started_at, timer?.ended_at])
  useEffect(() => {
    if (!timer) return
    const warn = event => { event.preventDefault(); event.returnValue = '' }
    window.addEventListener('beforeunload', warn)
    return () => window.removeEventListener('beforeunload', warn)
  }, [timer])
  const begin = () => {
    if (timer || writing.current || blocked || draft.candidate || draft.status === 'loading') return
    const startedAt = new Date().toISOString()
    duplicates.clear()
    setTimer({ entry_type: kind, started_at: startedAt, ended_at: null, request_key: requestKey() })
    setSubjectScope(privateSubject(care.activeId)); setLastSaved(null)
    setStart(japanDateTimeInput(startedAt)); setEnd(''); setClock(Date.now()); setStatus(''); setError('')
    setReturned(false); setConfirmed(false); uncertain.current = false; hidden.current = false
  }
  const stop = () => {
    if (!timer || timer.ended_at || writing.current) return
    const endedAt = new Date().toISOString()
    setTimer(previous => ({ ...previous, ended_at: endedAt })); setEnd(japanDateTimeInput(endedAt)); setConfirmed(false)
  }
  const startedAt = timer && (start === japanDateTimeInput(timer.started_at) ? utcDate(timer.started_at) : new Date(`${start}:00+09:00`))
  const endedAt = timer?.ended_at && (end === japanDateTimeInput(timer.ended_at) ? utcDate(timer.ended_at) : new Date(`${end}:00+09:00`))
  const duration = startedAt && endedAt ? Math.floor((endedAt - startedAt) / 60000) : null
  const validTimes = timer?.ended_at && Number.isFinite(startedAt?.getTime()) && Number.isFinite(endedAt?.getTime())
    && endedAt >= startedAt && endedAt.getTime() <= Date.now() + 60000 && startedAt >= earliestRecordTime()
  const elapsed = timer ? Math.max(0, Math.floor((clock - utcDate(timer.started_at).getTime()) / 1000)) : 0
  const busy = ['saving', 'checking', 'clearing'].includes(status)
  const finish = async saved => {
    setLastSaved(saved)
    uncertain.current = false; setPending(null); setTimer(null); setConfirmed(false); setReturned(false)
    setStart(''); setEnd(''); setSide(''); setError(''); setStatus('saving'); onRecordsChanged()
    await draft.clear(); setStatus('saved')
  }
  const save = async event => {
    event.preventDefault()
    if (writing.current || blocked || !timer || !confirmed) return
    if (!pending && !validTimes) { setError('invalidTime'); return }
    const operation = pending || { ...recordOperation({ entry_type: timer.entry_type, timestamp: startedAt.toISOString(),
      end_timestamp: endedAt.toISOString(), ...(subjectScope || privateSubject('')),
      ...(timer.entry_type === 'feeding' ? { feeding_type: 'breast', duration_minutes: duration, side: side || null }
        : { sleep_duration_minutes: duration }) }), request_key: timer.request_key }
    setPending(operation)
    if (navigator.onLine === false) { setStatus(uncertain.current ? 'unconfirmed' : 'offline'); return }
    writing.current = true; setStatus('saving'); setError('')
    try {
      if (!pending && !(await duplicates.check(operation))) { setStatus('unsaved'); return }
      duplicates.clear()
      const result = await api.addTrackingEntry(operation)
      await finish({ ...operation, ...result })
    } catch (failure) {
      if (!(failure.status >= 400 && failure.status < 500)) uncertain.current = true
      setStatus(uncertain.current ? 'unconfirmed' : 'unsaved')
      if ([404, 409].includes(failure.status)) setError('conflict')
      if (failure.status === 422 && !uncertain.current) { setPending(null); setError('invalidTime') }
    } finally { writing.current = false }
  }
  const check = async () => {
    if (writing.current || !pending) return
    writing.current = true; setStatus('checking'); setError('')
    try {
      const result = await api.get(`/api/tracking/operations/${pending.request_key}`)
      const record = result.record
      const fields = [...(pending.entry_type === 'feeding' ? ['entry_type', 'feeding_type', 'duration_minutes', 'side'] : ['entry_type', 'sleep_duration_minutes']),
        ...['subject_id', 'family_shared'].filter(key => Object.prototype.hasOwnProperty.call(pending, key))]
      const sameEnd = pending.end_timestamp === undefined || (record?.end_timestamp && utcDate(record.end_timestamp).getTime() === utcDate(pending.end_timestamp).getTime())
      if (result.state === 'saved' && record.revision === 1 && sameEnd && utcDate(record.timestamp).getTime() === utcDate(pending.timestamp).getTime()
        && fields.every(key => (record[key] ?? null) === (pending[key] ?? null))) await finish(record)
      else if (result.state === 'saved' || result.state === 'deleted') { setError('conflict'); setStatus('unconfirmed'); onRecordsChanged() }
      else { setError('notFound'); setStatus(uncertain.current ? 'unconfirmed' : 'unsaved'); onRecordsChanged() }
    } catch { setError('checkFailed'); setStatus(uncertain.current ? 'unconfirmed' : 'unsaved') }
    finally { writing.current = false }
  }
  const discard = async () => {
    if (writing.current || !window.confirm(t(pending ? 'polish.abandonWrite' : 'interaction.timer.discardConfirm'))) return
    writing.current = true; setStatus('clearing')
    try {
      const cleared = await draft.clear()
      if (!cleared) { setError('draftClear'); setStatus(pending ? 'unconfirmed' : ''); return }
      duplicates.clear()
      uncertain.current = false; setTimer(null); setPending(null); setStatus(''); setConfirmed(false); setError(''); setSide('')
    } finally { writing.current = false }
  }
  return <details className="pilot-panel care-timer" id="care-timer" open={expanded} onToggle={event => {
    if (event.target === event.currentTarget) setExpanded(event.currentTarget.open)
  }}><summary id="care-timer-heading">{t('interaction.timer.title')}
    {timer ? ` · ${t(timer.ended_at ? 'interaction.timer.awaiting' : 'interaction.timer.running')}` : draft.candidate ? ` · ${t('polish.draftFound')}` : ''}</summary>
    <p>{t('interaction.timer.notice')}</p>
    <DraftRecoveryNotice draft={draft} disabled={busy} compact />
    {!timer ? <>
      <div className="pilot-actions" role="group" aria-label={t('interaction.timer.choose')}>
        {['feeding', 'sleep'].map(value => <button key={value} type="button" className="pilot-button secondary" aria-pressed={kind === value}
          disabled={busy} onClick={() => setKind(value)}>{t(value === 'feeding' ? 'interaction.timer.breast' : 'tracking.sleep')}</button>)}
      </div><button type="button" className="pilot-button" disabled={blocked || Boolean(draft.candidate) || draft.status === 'loading' || busy} onClick={begin}>{t('interaction.timer.start')}</button>
    </> : <>
      <h4>{t(timer.entry_type === 'feeding' ? 'interaction.timer.breast' : 'tracking.sleep')}</h4>
      <p>{t('interaction.timer.started', { time: japanDateTime(timer.started_at, i18n.resolvedLanguage || 'ja') })}</p>
      {!timer.ended_at && <><p className="timer-display" aria-label={t('interaction.timer.elapsed')}>{Math.floor(elapsed / 60)}:{String(elapsed % 60).padStart(2, '0')}</p>
        <button type="button" className="pilot-button" onClick={stop}>{t('interaction.timer.stop')}</button></>}
      {returned && <p role="status">{t('interaction.timer.returned')}</p>}
      {timer.ended_at && <form onSubmit={save}><fieldset disabled={busy || Boolean(pending)}>
        <legend>{t('interaction.timer.review')}</legend>
        <CareSubjectFields value={subjectScope || privateSubject('')} kind={timer.entry_type} onChange={value => { setSubjectScope(value); setConfirmed(false) }} />
        <label>{t('interaction.timer.startTime')}<input type="datetime-local" required value={start}
          min={japanDateTimeInput(earliestRecordTime())} max={japanDateTimeInput()} onChange={event => { setStart(event.target.value); setConfirmed(false) }} /></label>
        <label>{t('interaction.timer.endTime')}<input type="datetime-local" required value={end} max={japanDateTimeInput()}
          onChange={event => { setEnd(event.target.value); setConfirmed(false) }} /></label>
        {timer.entry_type === 'feeding' && <label>{t('localCare.record.feedingSide')}<select value={side} onChange={event => { setSide(event.target.value); setConfirmed(false) }}>
          <option value="">{t('pilot.notProvided')}</option>{['left', 'right', 'both'].map(value => <option key={value} value={value}>{t(`localCare.record.sides.${value}`)}</option>)}
        </select></label>}
        <p>{validTimes ? t('interaction.timer.duration', { count: duration }) : t('interaction.timer.errors.invalidTime')}</p>
        <p>{t('interaction.timer.rounding')}</p>
      </fieldset>
        {pending && <p>{t('interaction.timer.pendingPreview', { time: japanDateTime(pending.timestamp, i18n.resolvedLanguage || 'ja'),
          count: pending.duration_minutes ?? pending.sleep_duration_minutes })}</p>}
        <label><input type="checkbox" disabled={busy} checked={confirmed} onChange={event => setConfirmed(event.target.checked)} />{t('interaction.timer.confirm')}</label>
        <button type="submit" className="pilot-button" disabled={blocked || busy || Boolean(duplicates.review) || !confirmed || (!pending && !validTimes) || error === 'conflict'}>
        {t(pending ? 'localCare.record.resend' : 'interaction.timer.save')}</button></form>}
      <DuplicateReview review={duplicates.review} disabled={busy} continueDisabled={blocked || !confirmed || error === 'conflict'} onContinue={() => save({ preventDefault() {} })} onCancel={() => {
        duplicates.clear(); setPending(null); setStatus(''); setConfirmed(false)
      }} />
      {pending && <p>{t('localCare.record.retryHint')} <button type="button" className="text-action" disabled={busy} onClick={check}>{t('localCare.record.check')}</button></p>}
      <button type="button" className="pilot-button secondary" disabled={busy} onClick={discard}>{t('interaction.timer.discard')}</button>
    </>}
    {['checking', 'clearing'].includes(status) ? <p role="status">{t('common.loading')}</p> : <RecordSaveStatus status={status} />}
    {error && <p role="alert">{t(`interaction.timer.errors.${error}`)}</p>}
    {lastSaved && <button type="button" className="pilot-button secondary" onClick={() => onLocate?.(lastSaved)}>{t('continuity.period.findSaved')}</button>}
  </details>
}
