import React, { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../utils/api'
import { useCareSession, useCareWork } from '../utils/CareSession'
import { requestKey } from '../utils/recordOperations'
import { japanDateTime } from '../utils/japanTime'
import CareScope from './CareScope'
import { revealElement } from '../utils/focusView'

export default function RecordOrganizer({ visible, blocked, onRecordsChanged, openRequest = 0 }) {
  const { t, i18n } = useTranslation()
  const care = useCareSession()
  const [open, setOpen] = useState(false)
  const [rows, setRows] = useState([])
  const [total, setTotal] = useState(0)
  const [next, setNext] = useState(null)
  const [before, setBefore] = useState(null)
  const [kind, setKind] = useState('all')
  const [from, setFrom] = useState('')
  const [to, setTo] = useState('')
  const [selected, setSelected] = useState({})
  const [subjectId, setSubjectId] = useState('')
  const [preview, setPreview] = useState(null)
  const [pending, setPending] = useState(null)
  const [receipts, setReceipts] = useState([])
  const [loading, setLoading] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const [attempt, setAttempt] = useState(0)
  const writing = useRef(false)
  const heading = useRef(null)
  const pendingFocus = useRef(false)
  const locked = blocked || busy || Boolean(pending)
  const subject = care.subjects.find(item => item.subject_id === subjectId)
  useCareWork('organization', pending ? { version: pending.request_key, title: 'workflow.work.organizePending',
    critical: true, priority: 0, subjectId: pending.subject_id, tab: 'tracking', detail: { action: 'organize' }, action: 'workflow.work.checkSave' } : null)
  useEffect(() => { if (openRequest) { setOpen(true); pendingFocus.current = true } }, [openRequest])
  useEffect(() => { if (visible && open && pendingFocus.current && revealElement(heading.current)) pendingFocus.current = false }, [visible, open, openRequest])
  useEffect(() => {
    if (!visible || !open) return
    let active = true
    setLoading(true); setError('')
    if (!before) { setRows([]); setTotal(0); setNext(null) }
    if (from && to && from > to) { setError('dates'); setLoading(false); return }
    const query = new URLSearchParams({ kind, ...(before ? { before_id: before } : {}),
      ...(from ? { from_day: from } : {}), ...(to ? { to_day: to } : {}) })
    api.get(`/api/record-organization/unassigned?${query}`).then(data => {
      if (active) { setRows(previous => before ? [...previous, ...data.records] : data.records); setTotal(data.total); setNext(data.next_before_id) }
    }).catch(() => { if (active) setError('load') }).finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [visible, open, kind, from, to, before, attempt])
  useEffect(() => {
    if (!visible || !open) return
    let active = true
    api.get('/api/record-organization/receipts').then(data => { if (active) setReceipts(data) }).catch(() => { if (active) setError('load') })
    return () => { active = false }
  }, [visible, open, attempt])
  useEffect(() => {
    if (!pending) return
    const warn = event => { event.preventDefault(); event.returnValue = '' }
    window.addEventListener('beforeunload', warn)
    return () => window.removeEventListener('beforeunload', warn)
  }, [pending])
  const refresh = () => { setBefore(null); setAttempt(value => value + 1); onRecordsChanged?.() }
  const complete = receipt => { setResult(receipt); setPending(null); setPreview(null); setSelected({}); refresh() }
  const save = async () => {
    if (writing.current || blocked || !preview) return
    const operation = pending || preview.payload
    writing.current = true; setBusy(true); setPending(operation); setError('')
    try { complete(await api.post('/api/record-organization', operation)) }
    catch (failure) { setError(failure.status === 409 ? 'conflict' : 'unconfirmed') }
    finally { writing.current = false; setBusy(false) }
  }
  const check = async () => {
    if (writing.current || !pending) return
    writing.current = true; setBusy(true); setError('')
    try { complete(await api.get(`/api/record-organization/${pending.request_key}`)) }
    catch (failure) { setError(failure.status === 404 ? 'notFound' : 'load') }
    finally { writing.current = false; setBusy(false) }
  }
  const undo = async receipt => {
    if (writing.current || locked || !window.confirm(t('workflow.organize.undoConfirm'))) return
    writing.current = true; setBusy(true); setError('')
    try { complete(await api.post(`/api/record-organization/${receipt.request_key}/undo`, { confirmed: true })) }
    catch (failure) { setError(failure.status === 409 ? 'undoConflict' : 'unconfirmed'); refresh() }
    finally { writing.current = false; setBusy(false) }
  }
  const resetFilter = (setter, value) => { setter(value); setBefore(null); setSelected({}); setPreview(null) }
  const facts = row => [row.feeding_type && t(`tracking.${row.feeding_type}`), row.diaper_type && t(`tracking.${row.diaper_type}`),
    row.amount_ml != null && `${row.amount_ml} mL`, row.pumped_amount_ml != null && `${row.pumped_amount_ml} mL`,
    (row.duration_minutes ?? row.sleep_duration_minutes) != null && `${row.duration_minutes ?? row.sleep_duration_minutes} ${t('pilot.minutes')}`].filter(value => value !== false && value != null && value !== '').join(' · ')
  return <details className="pilot-panel record-organizer" open={open} onToggle={event => { if (event.target === event.currentTarget) setOpen(event.currentTarget.open) }}>
    <summary id="record-organizer-heading" ref={heading} tabIndex={-1}>{t('workflow.organize.title')}</summary><p>{t('workflow.organize.notice')}</p>
    {result && <p role="status">{t(result.undone ? 'workflow.organize.undone' : 'workflow.organize.saved', { count: result.count })}</p>}
    {error && <p role="alert">{t(`workflow.organize.errors.${error}`)}</p>}
    {!preview ? <>
      <fieldset disabled={locked || loading}><legend>{t('workflow.organize.choose')}</legend>
        <label>{t('workflow.organize.from')}<input type="date" value={from} onChange={event => resetFilter(setFrom, event.target.value)} /></label>
        <label>{t('workflow.organize.to')}<input type="date" value={to} onChange={event => resetFilter(setTo, event.target.value)} /></label>
        <label>{t('interaction.timeline.filter')}<select value={kind} onChange={event => resetFilter(setKind, event.target.value)}>
          {['all', 'feeding', 'diaper', 'sleep', 'pumping'].map(value => <option key={value} value={value}>{t(value === 'all' ? 'interaction.timeline.all' : `tracking.${value}`)}</option>)}
        </select></label>
        <p>{t('workflow.organize.count', { count: total, loaded: rows.length })}</p>
        <ul className="workflow-records">{rows.map(row => <li key={row.record_key}><label><input type="checkbox" checked={Boolean(selected[row.record_key])}
          disabled={!selected[row.record_key] && Object.keys(selected).length >= 50} onChange={event => {
            const checked = event.target.checked
            setSelected(previous => { const value = { ...previous }; if (checked) value[row.record_key] = row; else delete value[row.record_key]; return value })
          }} />{t(`tracking.${row.entry_type}`)} · {row.timestamp ? japanDateTime(row.timestamp, i18n.resolvedLanguage || 'ja') : t('pilot.notProvided')}
          {facts(row) ? ` · ${facts(row)}` : ''}</label></li>)}</ul>
        <label>{t('continuity.subject.recordFor')}<select value={subjectId} disabled={!care.ready} onChange={event => { setSubjectId(event.target.value); care.rememberSubject(event.target.value) }}>
          <option value="">{t('workflow.organize.chooseSubject')}</option>{care.subjects.map(item => <option key={item.subject_id} value={item.subject_id}>{item.nickname} · {item.family_name || t('continuity.subject.personal')}</option>)}
        </select></label>
        <button type="button" className="pilot-button" disabled={!subject || !Object.keys(selected).length} onClick={() => {
          const entries = Object.values(selected)
          setPreview({ entries, name: `${subject.nickname} · ${subject.family_name || t('continuity.subject.personal')}`, payload: { request_key: requestKey(), subject_id: subject.subject_id, subject_revision: subject.revision,
            records: entries.map(({ id, record_key, revision }) => ({ id, record_key, revision })), confirmed: true } })
        }}>{t('workflow.organize.preview')}</button>
      </fieldset>
      {next && <button type="button" className="pilot-button secondary" disabled={locked || loading} onClick={() => setBefore(next)}>{t('workflow.organize.more')}</button>}
      <button type="button" className="text-action" disabled={locked || loading} onClick={() => { setBefore(null); setAttempt(value => value + 1) }}>{t('pilot.retry')}</button>
    </> : <section className="support-card">
      <h3>{t('workflow.organize.previewTitle', { name: preview.name, count: preview.entries.length })}</h3>
      <CareScope subjectId={preview.payload.subject_id} /><p>{t('workflow.organize.privateNotice')}</p>
      <ul>{preview.entries.map(row => <li key={row.record_key}>{t(`tracking.${row.entry_type}`)} · {row.timestamp ? japanDateTime(row.timestamp, i18n.resolvedLanguage || 'ja') : t('pilot.notProvided')} {facts(row)}</li>)}</ul>
      <button type="button" className="pilot-button" disabled={busy || blocked} onClick={save}>{t(pending ? 'workflow.organize.retry' : 'workflow.organize.confirm')}</button>
      {pending && <button type="button" className="pilot-button secondary" disabled={busy} onClick={check}>{t('workflow.organize.check')}</button>}
      <button type="button" className="pilot-button secondary" disabled={busy} onClick={() => {
        if (pending && !window.confirm(t('polish.abandonWrite'))) return
        setPending(null); setPreview(null); refresh()
      }}>{t('tracking.cancel')}</button>
    </section>}
    {loading && <p role="status">{t('common.loading')}</p>}
    <details><summary>{t('workflow.organize.recent')}</summary>{receipts.map(row => <article key={row.request_key}>
      <p>{t('workflow.context.subject', { name: care.subjects.find(item => item.subject_id === row.subject_id)?.nickname || t('continuity.subject.unavailable') })}</p>
      <p>{japanDateTime(row.created_at, i18n.resolvedLanguage || 'ja')} · {t('workflow.organize.resultCount', { count: row.count })} {row.undone && t('workflow.organize.undoneLabel')}</p>
      {!row.undone && <button type="button" className="text-action" disabled={locked} onClick={() => undo(row)}>{t('workflow.organize.undo')}</button>}
    </article>)}</details>
  </details>
}
