import React, { useCallback, useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../utils/api'
import { japanDateTime, japanDateTimeInput } from '../utils/japanTime'
import useConnection from '../utils/useConnection'
import { journeysChanged } from '../utils/CareSession'

const editorFromRow = (row, name = '') => ({
  form: { state: row?.cleared ? 'preparing' : row?.state || 'preparing',
    contact_response: row?.cleared ? '' : row?.contact_response || '', next_steps: row?.cleared ? '' : row?.next_steps || '',
    time: row?.next_contact_at && !row.cleared ? japanDateTimeInput(row.next_contact_at) : '' },
  revision: row?.revision || 0, contact_name: name || row?.contact_name || '',
  edited: false, busy: false, message: '', conflict: false,
})

export function useSupportJourneys(userId, visible) {
  const [rows, setRows] = useState([])
  // Account-session memory owns editors, including contacts removed from the directory.
  const [editors, setEditors] = useState({})
  const [ready, setReady] = useState(false)
  const [error, setError] = useState(false)
  const { reconnections } = useConnection()
  const generation = useRef(0)
  const writes = useRef(new Set())
  const reload = useCallback(async () => {
    if (writes.current.size) return
    const version = ++generation.current
    setError(false)
    try {
      const result = await api.get('/api/support-journeys')
      if (version === generation.current) {
        setRows(result); setReady(true)
        setEditors(previous => Object.fromEntries(Object.entries(previous).map(([key, editor]) => {
          const row = result.find(item => item.contact_key === key)
          if (editor.edited) return [key, editor.revision !== (row?.revision || 0)
            ? { ...editor, conflict: true, message: 'conflict' } : editor]
          return [key, { ...editorFromRow(row, editor.contact_name), message: editor.message === 'saved' ? 'saved' : '' }]
        })))
      }
    } catch { if (version === generation.current) setError(true) }
  }, [userId])
  useEffect(() => {
    if (!userId || !visible) return
    reload()
    const refresh = () => reload()
    window.addEventListener('focus', refresh)
    return () => { generation.current++; window.removeEventListener('focus', refresh) }
  }, [userId, visible, reconnections, reload])
  const updateEditor = (key, updater, name = '') => setEditors(previous => ({ ...previous,
    [key]: updater(previous[key] || editorFromRow(rows.find(row => row.contact_key === key), name)),
  }))
  const edit = (key, field, value, name) => {
    if (writes.current.has(key)) return
    updateEditor(key, editor => editor.conflict ? editor : ({ ...editor, edited: true, message: 'unsaved',
      contact_name: name || editor.contact_name, form: { ...editor.form, [field]: value } }), name)
  }
  const save = async (key, body, name) => {
    if (writes.current.has(key)) return
    writes.current.add(key); generation.current++
    updateEditor(key, editor => ({ ...editor, busy: true, message: 'saving', contact_name: name || editor.contact_name }), name)
    try {
      const result = await api.post(`/api/support-journeys/${encodeURIComponent(key)}`, body)
      setRows(previous => {
        const existing = previous.find(row => row.contact_key === key)
        return existing && existing.revision > result.revision ? previous : [...previous.filter(row => row.contact_key !== key), result]
      })
      updateEditor(key, editor => ({ ...editorFromRow(result, editor.contact_name), message: 'saved' }))
      window.dispatchEvent(new Event(journeysChanged))
    } catch (failure) {
      updateEditor(key, editor => ({ ...editor, edited: true, busy: false,
        message: failure.status === 409 ? 'conflict' : 'failed', conflict: failure.status === 409 }))
    } finally { writes.current.delete(key); generation.current++ }
  }
  const discard = key => {
    if (writes.current.has(key)) return
    setEditors(previous => { const next = { ...previous }; delete next[key]; return next })
  }
  const reloadContact = key => {
    if (writes.current.size) return
    updateEditor(key, editor => ({ ...editor, edited: false, message: '' }))
    reload()
  }
  return { rows, editors, ready, error, reload, save, edit, discard, reloadContact,
    saving: Object.values(editors).some(editor => editor.busy),
    setMessage: (key, message, name) => updateEditor(key, editor => ({ ...editor, message }), name) }
}

export default function SupportProgress({ contactKey, contactName, row, progress, archived = false, expanded = false }) {
  const { t, i18n } = useTranslation()
  const editor = progress.editors[contactKey] || editorFromRow(row, contactName)
  const { form, revision, busy, message, conflict, edited } = editor
  const canSave = !archived || Boolean(row)
  const edit = (field, value) => progress.edit(contactKey, field, value, contactName)
  const save = (event, cleared = false) => {
    event?.preventDefault()
    if (busy || !progress.ready || conflict || !canSave) return
    const time = form.time ? new Date(`${form.time}:00+09:00`) : null
    if (time && !Number.isFinite(time.getTime())) { progress.setMessage(contactKey, 'invalidTime', contactName); return }
    progress.save(contactKey, { state: form.state, contact_response: form.contact_response, next_steps: form.next_steps,
      next_contact_at: time?.toISOString() || null, revision, cleared }, contactName)
  }
  const Container = expanded ? 'section' : 'details'
  const Title = expanded ? 'h4' : 'summary'
  return <Container className="support-progress"><Title>{row && !row.cleared
    ? t('friendly.support.ownProgress', { state: t(['completed', 'paused'].includes(row.state) ? `continuity.journey.states.${row.state}` : `flows.journey.states.${row.state}`) }) : t('flows.journey.title')}
    {edited ? ` · ${t('flows.journey.unsaved')}` : ''}</Title>
    {row && !row.cleared && <p>{t('friendly.support.ownProgressHint')}</p>}
    <p>{t('flows.journey.notice')}</p>
    {archived && !row && <p role="status">{t('flows.journey.archivedDraftNotice')}</p>}
    {row?.updated_at && !row.cleared && <p>{t('flows.journey.updated', { time: japanDateTime(row.updated_at, i18n.resolvedLanguage || 'ja') })}</p>}
    <form onSubmit={save}><fieldset disabled={busy || !progress.ready || conflict}>
      <legend>{t('flows.journey.edit')}</legend>
      <label>{t('flows.journey.state')}<select value={form.state} onChange={event => {
        const state = event.target.value; edit('state', state)
        if (['completed', 'paused'].includes(state)) edit('time', '')
      }}>
        {['preparing', 'waiting', 'booked', 'completed', 'paused'].map(state => <option key={state} value={state}>{t(['completed', 'paused'].includes(state) ? `continuity.journey.states.${state}` : `flows.journey.states.${state}`)}</option>)}
      </select></label>
      <label>{t('continuity.journey.response')}<textarea rows={3} maxLength={1500} value={form.contact_response} onChange={event => edit('contact_response', event.target.value)} /></label>
      <label>{t('continuity.journey.nextSteps')}<textarea rows={3} maxLength={1500} value={form.next_steps} onChange={event => edit('next_steps', event.target.value)} /></label>
      <p>{t('continuity.journey.notice')}</p>
      <label>{t('flows.journey.nextContact')}<input type="datetime-local" disabled={['completed', 'paused'].includes(form.state)} value={form.time} onChange={event => edit('time', event.target.value)} /></label>
      <p>{t('flows.journey.timeNotice')}</p>
      <div className="pilot-actions"><button className="pilot-button secondary" type="submit" disabled={!canSave}>{t('work.saveChanges')}</button>
        {row && !row.cleared && <button className="pilot-button secondary" type="button" onClick={() => save(null, true)}>{t('flows.journey.clear')}</button>}</div>
    </fieldset></form>
    {archived && edited && <button type="button" className="pilot-button secondary" disabled={busy} onClick={() => {
      if (window.confirm(t('flows.journey.discardConfirm'))) progress.discard(contactKey)
    }}>{t('flows.journey.discardDraft')}</button>}
    {message && <p role={['failed', 'conflict', 'invalidTime'].includes(message) ? 'alert' : 'status'}>{t(`flows.journey.${message}`)}</p>}
    {(progress.error || conflict || message === 'failed') && <button type="button" className="pilot-button secondary" disabled={progress.saving} onClick={() => {
      if (edited && !window.confirm(t('flows.journey.reloadConfirm'))) return
      progress.reloadContact(contactKey)
    }}>{t('friendly.support.reloadProgress')}</button>}
  </Container>
}
