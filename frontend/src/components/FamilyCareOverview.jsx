import React, { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../utils/api'
import { japanDateTime } from '../utils/japanTime'
import useConnection from '../utils/useConnection'
import RecordTime, { useRecordClock } from './RecordTime'

const categories = ['feeding', 'diaper', 'sleep', 'pumping']
export default function FamilyCareOverview({ visible, refreshKey, onManage }) {
  const { t, i18n } = useTranslation()
  const { reconnections } = useConnection()
  const [expanded, setExpanded] = useState(false)
  const activeView = visible && expanded
  const now = useRecordClock(activeView)
  const [families, setFamilies] = useState([])
  const [selected, setSelected] = useState('')
  const [overview, setOverview] = useState(null)
  const [form, setForm] = useState({ text: '', shared: false })
  const [loading, setLoading] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [conflict, setConflict] = useState(false)
  const [attempt, setAttempt] = useState(0)
  const [saved, setSaved] = useState(false)
  const [acknowledging, setAcknowledging] = useState('')
  const [ackError, setAckError] = useState('')
  const acknowledgementBusy = useRef(false)
  const edited = useRef(false)
  const base = useRef(null)
  const saving = useRef(false)
  const label = item => item.recorder_label || t('polish.memberNumber', { number: item.recorder_number || '?' })
  const date = value => japanDateTime(value, i18n.resolvedLanguage || 'ja')
  useEffect(() => {
    if (!activeView) return
    let active = true
    api.get('/api/families/').then(groups => {
      if (!active) return
      setFamilies(groups)
      if (selected && !groups.some(group => group.family_id === selected)) {
        setSelected(''); setOverview(null); setForm({ text: '', shared: false }); edited.current = false; base.current = null
      }
    }).catch(() => { if (active) { setError('load'); setOverview(null) } })
    return () => { active = false }
  }, [activeView, refreshKey, reconnections, attempt, selected])
  useEffect(() => {
    if (!selected || !activeView) { setOverview(null); setLoading(false); return }
    let active = true
    setLoading(true)
    api.get(`/api/families/${selected}/overview`).then(result => {
      if (!active) return
      setOverview(result); setError('')
      const changed = base.current && (base.current.revision !== result.own_handover.revision ||
        base.current.membership !== result.membership_revision)
      if (edited.current && changed) { setConflict(true); setError('conflict') }
      else if (!edited.current) {
        setForm({ text: result.own_handover.text, shared: result.own_handover.shared })
        base.current = { revision: result.own_handover.revision, membership: result.membership_revision }
        setConflict(false)
      }
    }).catch(() => { if (active) { setOverview(null); setError('load') } })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [selected, activeView, refreshKey, reconnections, attempt])
  useEffect(() => {
    if (!selected || !activeView) return
    const refresh = () => setAttempt(value => value + 1)
    const timer = setInterval(refresh, 30000)
    window.addEventListener('focus', refresh)
    return () => { clearInterval(timer); window.removeEventListener('focus', refresh) }
  }, [selected, activeView])
  const reload = () => {
    if (edited.current && !window.confirm(t('flows.overview.reloadConfirm'))) return
    edited.current = false; base.current = null; setConflict(false); setAttempt(value => value + 1)
  }
  const edit = (key, value) => { edited.current = true; setSaved(false); setForm(previous => ({ ...previous, [key]: value })) }
  const save = async event => {
    event.preventDefault()
    if (saving.current || !overview || conflict || !base.current || loading) return
    saving.current = true; setBusy(true); setError(''); setSaved(false)
    try {
      await api.post(`/api/families/${selected}/handover`, { ...form, revision: base.current.revision,
        membership_revision: base.current.membership })
      edited.current = false; setSaved(true); setAttempt(value => value + 1)
    } catch (failure) { setError(failure.status === 409 ? 'conflict' : 'save'); setConflict(failure.status === 409) }
    finally { saving.current = false; setBusy(false) }
  }
  const acknowledge = async note => {
    if (acknowledgementBusy.current || busy || loading) return
    acknowledgementBusy.current = true; setAcknowledging(note.author_id); setAckError('')
    try {
      await api.post(`/api/families/${selected}/handovers/${encodeURIComponent(note.author_id)}/acknowledge`, {
        revision: note.revision, membership_revision: note.membership_revision,
      })
      setAttempt(value => value + 1)
    } catch (failure) {
      setAckError(failure.status === 409 ? 'conflict' : 'failed'); setAttempt(value => value + 1)
    } finally { acknowledgementBusy.current = false; setAcknowledging('') }
  }
  return <details className="pilot-panel family-overview" onToggle={event => {
    if (event.target === event.currentTarget) setExpanded(event.currentTarget.open)
  }}><summary>{t('friendly.home.family')}{edited.current ? ` · ${t('flows.overview.unsaved')}` : ''}</summary>
    {!selected && <p>{t('friendly.home.familyOff')}</p>}
    <p>{t('flows.overview.notice')}</p>
    <label>{t('flows.overview.choose')}<select value={selected} disabled={busy || Boolean(acknowledging)} onChange={event => {
      if (edited.current && !window.confirm(t('flows.overview.reloadConfirm'))) return
      edited.current = false; base.current = null; setSelected(event.target.value); setOverview(null)
      setForm({ text: '', shared: false }); setConflict(false); setSaved(false); setError(''); setAckError('')
    }}><option value="">{t('flows.overview.off')}</option>
      {families.map(family => <option key={family.family_id} value={family.family_id}>{family.name}</option>)}
    </select></label>
    {error && <p role="alert">{t(`flows.overview.${error}Error`)} <button className="pilot-button secondary" type="button" disabled={busy} onClick={reload}>{t('flows.overview.reload')}</button></p>}
    {loading && <p role="status">{t('common.loading')}</p>}
    {selected && <>
      {overview && <dl className="care-overview-grid">{categories.map(kind => {
        const record = overview?.latest[kind]
        return <div key={kind}><dt>{t(`tracking.${kind}`)}</dt><dd>{record ? <>
          <RecordTime value={record.timestamp} now={now} /><span>{t('polish.recordedBy', { name: label(record) })}</span>
          {record.feeding_type && <span>{t(`tracking.${record.feeding_type}`)}</span>}
          {record.diaper_type && <span>{t(`tracking.${record.diaper_type}`)}</span>}
          {['duration_minutes', 'sleep_duration_minutes'].map(key => record[key] != null && <span key={key}>{record[key]} {t('pilot.minutes')}</span>)}
          {['amount_ml', 'pumped_amount_ml'].map(key => record[key] != null && <span key={key}>{record[key]} mL</span>)}
        </> : t('flows.overview.unknown')}</dd></div>
      })}</dl>}
      {overview?.checked_at && <p>{t('flows.overview.checkedAt', { time: date(overview.checked_at) })}</p>}
      {ackError && <p role="alert">{t(`interaction.handover.${ackError}`)}</p>}
      {overview?.handovers.map(note => {
        const receipts = note.acknowledgements || []
        const confirmed = receipts.some(receipt => receipt.is_me && receipt.note_revision === note.revision)
        return <article className="support-card" key={note.author_id}>
          <h4>{t('polish.recordedBy', { name: label(note) })}</h4><p>{t('interaction.handover.version', { number: note.revision })}</p>
          <p className="preserve-lines">{note.text}</p><time>{date(note.updated_at)}</time>
          <ul className="handover-receipts">{receipts.map(receipt => <li key={receipt.recorder_number}>
            {t(receipt.note_revision === note.revision ? 'interaction.handover.receipt' : 'interaction.handover.previousReceipt', {
              name: label(receipt), time: date(receipt.acknowledged_at), number: receipt.note_revision,
            })}
          </li>)}</ul>
          {!note.is_own && <><p className="field-hint">{t('interaction.handover.notice')}</p>
            <button type="button" className="pilot-button secondary" disabled={confirmed || Boolean(acknowledging) || busy || loading}
              onClick={() => acknowledge(note)}>{t(confirmed ? 'interaction.handover.confirmed' : acknowledging === note.author_id ? 'settings.saving' : 'interaction.handover.confirm')}</button>
          </>}
        </article>
      })}
      <details className="handover-editor"><summary>{t('friendly.home.note')}{edited.current ? ` · ${t('flows.overview.unsaved')}` : ''}</summary>
      <form onSubmit={save}><fieldset disabled={busy || !overview || conflict}>
        <legend>{t('flows.overview.noteTitle')}</legend>
        <label>{t('flows.overview.note')}<textarea rows={3} maxLength={1000} value={form.text} onChange={event => edit('text', event.target.value)} /></label>
        <label><input type="checkbox" checked={form.shared} onChange={event => edit('shared', event.target.checked)} />{t('flows.overview.share')}</label>
        <p>{t('flows.overview.noteNotice')}</p>
        <button type="submit" className="pilot-button secondary" disabled={loading}>{t(busy ? 'settings.saving' : 'work.saveChanges')}</button>
        <button type="button" className="pilot-button secondary" onClick={() => {
          if (window.confirm(t('flows.overview.deleteConfirm'))) { edit('text', ''); edit('shared', false) }
        }}>{t('flows.overview.clearNote')}</button>
      </fieldset></form>
      {edited.current && <p role="status">{t('flows.overview.unsaved')}</p>}
      {saved && <p role="status">{t('pilot.saved')}</p>}
      {conflict && <button type="button" className="pilot-button secondary" disabled={busy} onClick={reload}>{t('flows.overview.reload')}</button>}
      </details>
    </>}
    <button type="button" className="pilot-button secondary" onClick={onManage}>{t('polish.familyHandoff')}</button>
  </details>
}
