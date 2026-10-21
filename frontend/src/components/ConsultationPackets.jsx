import React, { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../utils/api'
import { requestKey } from '../utils/recordOperations'
import { japanDateTime } from '../utils/japanTime'

export default function ConsultationPackets({ visible, content, canSave, onOpen, onDeleted, onLockChange }) {
  const { t, i18n } = useTranslation()
  const [items, setItems] = useState([])
  const [next, setNext] = useState(null)
  const [active, setActive] = useState(null)
  const [pending, setPending] = useState(null)
  const [unresolved, setUnresolved] = useState(null)
  const [remote, setRemote] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)
  const [attempt, setAttempt] = useState(0)
  const writing = useRef(false)
  const newId = useRef(null)
  if (!newId.current) newId.current = requestKey()
  const contentVersion = JSON.stringify(content)
  useEffect(() => { setSaved(false) }, [contentVersion])
  useEffect(() => { onLockChange?.(busy || Boolean(pending)) }, [busy, pending, onLockChange])
  useEffect(() => {
    if (!visible) return
    let current = true
    api.get('/api/consultations').then(data => { if (current) { setItems(data.items); setNext(data.next_before_id) } }).catch(() => { if (current) setError('load') })
    return () => { current = false }
  }, [visible, attempt])
  useEffect(() => {
    if (!pending && !unresolved) return
    const warn = event => { event.preventDefault(); event.returnValue = '' }
    window.addEventListener('beforeunload', warn)
    return () => window.removeEventListener('beforeunload', warn)
  }, [pending, unresolved])
  const adopt = row => {
    setActive(row); setPending(null); setUnresolved(null); setRemote(null); setError(''); setSaved(true); setAttempt(value => value + 1)
    if (row.cleared) { onDeleted(); setActive(null); newId.current = requestKey() }
  }
  const execute = async operation => {
    if (writing.current) return
    writing.current = true; setBusy(true); setPending(operation); setUnresolved(operation); setSaved(false); setError('')
    try {
      const row = operation.mode === 'delete'
        ? await api.delete(`/api/consultations/${operation.id}?${new URLSearchParams({ revision: operation.revision })}`)
        : await api.post(`/api/consultations/${operation.id}`, operation.body)
      adopt(row)
    } catch (failure) { setError(failure.status === 409 ? 'conflict' : 'unconfirmed') }
    finally { writing.current = false; setBusy(false) }
  }
  const check = async () => {
    const operation = pending || unresolved
    if (writing.current || !operation) return
    writing.current = true; setBusy(true); setError('')
    try {
      const row = await api.get(`/api/consultations/${operation.id}`)
      if (pending && ((operation.mode === 'delete' && row.cleared) || (operation.mode === 'save' && !row.cleared && row.last_write_key === operation.body.request_key))) adopt(row)
      else { setRemote(row); setError('conflict') }
    } catch (failure) { setError(failure.status === 404 ? 'notFound' : 'load') }
    finally { writing.current = false; setBusy(false) }
  }
  const openPacket = async id => {
    if (writing.current || pending || unresolved || !window.confirm(t('workflow.packet.openConfirm'))) return
    writing.current = true; setBusy(true); setError('')
    try {
      const row = await api.get(`/api/consultations/${id}`)
      if (row.cleared) { setError('removed'); return }
      setActive(row); setSaved(false); onOpen(row)
    } catch { setError('load') }
    finally { writing.current = false; setBusy(false) }
  }
  return <section className="consultation-packets support-card"><h3>{t('workflow.packet.title')}</h3><p>{t('workflow.packet.notice')}</p><p>{t('workflow.packet.retention')}</p>
    {active && !active.cleared && <p>{t('workflow.packet.editing', { name: active.content.contact_name || t('workflow.packet.noContact'),
      time: japanDateTime(active.updated_at, i18n.resolvedLanguage || 'ja') })}</p>}
    {error && <p role="alert">{t(`workflow.packet.errors.${error}`)}</p>}
    {unresolved && !pending && <p role="status">{t('workflow.packet.sameReference')}</p>}
    {saved && <p role="status">{t('workflow.packet.saved')}</p>}
    <div className="pilot-actions"><button type="button" className="pilot-button" disabled={busy || (!pending && !canSave)} onClick={() => {
      if (pending) { execute(pending); return }
      if (!window.confirm(t('workflow.packet.saveConfirm'))) return
      execute({ mode: 'save', id: active?.consultation_id || newId.current,
        body: { ...content, revision: active?.revision || 0, request_key: requestKey(), confirmed: true } })
    }}>{t(pending ? 'workflow.packet.retry' : active ? 'workflow.packet.update' : 'workflow.packet.save')}</button>
      {(pending || unresolved) && <button type="button" className="pilot-button secondary" disabled={busy} onClick={check}>{t('workflow.packet.check')}</button>}
      <button type="button" className="pilot-button secondary" disabled={busy || (!pending && Boolean(unresolved))} onClick={() => {
        if (!window.confirm(t(pending ? 'polish.abandonWrite' : 'workflow.packet.newConfirm'))) return
        // Keep the ID when abandoning an uncertain creation. A late original
        // response must conflict with later input rather than create another packet.
        if (!pending) { newId.current = requestKey(); setActive(null) }
        setPending(null); setRemote(null); setSaved(false); setError('')
      }}>{t(pending ? 'localCare.record.stopRetry' : 'workflow.packet.new')}</button>
      {active && !pending && <button type="button" className="text-action" disabled={busy} onClick={() => {
        if (window.confirm(t('workflow.packet.deleteConfirm'))) execute({ mode: 'delete', id: active.consultation_id, revision: active.revision })
      }}>{t('workflow.packet.delete')}</button>}
    </div>
    {remote && <button type="button" className="pilot-button secondary" disabled={busy} onClick={() => {
      if (!window.confirm(t('workflow.packet.openConfirm'))) return
      adopt(remote); if (!remote.cleared) onOpen(remote)
    }}>{t('workflow.packet.openCurrent')}</button>}
    <details><summary>{t('workflow.packet.savedList')}</summary>{items.map(row => <article key={row.consultation_id}>
      <strong>{row.content.contact_name || t('workflow.packet.noContact')}</strong>
      {row.content.subject_name && <p>{row.content.subject_name}</p>}
      <p>{row.content.appointment_at ? t('workflow.packet.appointment', { time: japanDateTime(row.content.appointment_at, i18n.resolvedLanguage || 'ja') }) : t('workflow.packet.noAppointment')}</p>
      <small>{japanDateTime(row.updated_at, i18n.resolvedLanguage || 'ja')}</small>
      <button type="button" className="text-action" disabled={busy || Boolean(pending) || Boolean(unresolved)} onClick={() => openPacket(row.consultation_id)}>{t('workflow.packet.open')}</button>
    </article>)}
      {next && <button type="button" className="text-action" disabled={busy} onClick={async () => {
        if (writing.current) return
        writing.current = true; setBusy(true)
        try { const data = await api.get(`/api/consultations?${new URLSearchParams({ before_id: next })}`); setItems(previous => [...previous, ...data.items]); setNext(data.next_before_id) }
        catch { setError('load') } finally { writing.current = false; setBusy(false) }
      }}>{t('workflow.packet.more')}</button>}
      <button type="button" className="text-action" disabled={busy || Boolean(pending)} onClick={() => setAttempt(value => value + 1)}>{t('pilot.retry')}</button>
    </details>
  </section>
}
