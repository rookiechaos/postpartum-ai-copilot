import React, { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { japanDay, japanDateTime } from '../utils/japanTime'
import { publicHttps } from '../utils/publicDirectory'
import { revealElement } from '../utils/focusView'

export default function WeeklyDirectoryReview({ profile, due, reviewTasks = [], savedContactKeys = [], maintainerFilter, blocked,
  hasUnpublishedChanges, onEdit, onSaveReview, onSaveDraft, onPreview, onSessionChange, onDraftChange }) {
  const { t, i18n } = useTranslation()
  const [queue, setQueue] = useState(null)
  const [index, setIndex] = useState(0)
  const [editing, setEditing] = useState(false)
  const [attestedSnapshot, setAttestedSnapshot] = useState('')
  const [checkedOn, setCheckedOn] = useState(japanDay())
  const [forms, setForms] = useState({})
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const saving = useRef(false)
  const heading = useRef(null)
  const pendingFocus = useRef(false)
  const locked = blocked || busy
  const item = queue && profile.resources.find(resource => resource.resource_key === queue[index])
  const task = reviewTasks.find(row => row.contact_key === item?.resource_key)
  const snapshot = item ? JSON.stringify(item) : ''
  const attested = Boolean(item && snapshot === attestedSnapshot)
  const form = item ? forms[item.resource_key] || { reason: task?.reason || '', assignee: task?.assignee || item.maintainer || '',
    next_review_on: task?.next_review_on || (item.review_due_on > japanDay() ? item.review_due_on : ''), baseRevision: task?.revision || 0 } : {}
  const conflict = Boolean(item && forms[item.resource_key] && form.baseRevision !== (task?.revision || 0))
  const formsDirty = Object.entries(forms).some(([key, value]) => {
    const saved = reviewTasks.find(row => row.contact_key === key)
    const resource = profile.resources.find(row => row.resource_key === key)
    return value.baseRevision !== (saved?.revision || 0) || value.reason !== (saved?.reason || '') || value.assignee !== (saved?.assignee || resource?.maintainer || '')
      || value.next_review_on !== (saved?.next_review_on || (resource?.review_due_on > japanDay() ? resource.review_due_on : ''))
  })
  useEffect(() => { onDraftChange?.(formsDirty || editing || Boolean(attestedSnapshot)) }, [formsDirty, editing, attestedSnapshot, onDraftChange])
  useEffect(() => { onSessionChange?.(Boolean(queue)) }, [queue, onSessionChange])
  useEffect(() => { if (!locked && pendingFocus.current && revealElement(heading.current)) pendingFocus.current = false }, [index, queue, locked])
  const dueKeys = new Set(due.map(row => row.resource.resource_key))
  const eligible = profile.resources.filter(resource => {
    if (maintainerFilter && (maintainerFilter === 'unassigned' ? Boolean(resource.maintainer?.trim()) : `name:${resource.maintainer?.trim()}` !== maintainerFilter)) return false
    const saved = reviewTasks.find(row => row.contact_key === resource.resource_key)
    if (saved && !saved.stale && saved.decision !== 'pending' && saved.next_review_on > japanDay()) return false
    return dueKeys.has(resource.resource_key) || saved?.stale || saved?.decision === 'pending' || (saved?.next_review_on && saved.next_review_on <= japanDay())
  })
  const start = keys => {
    setQueue(keys); setIndex(0); setEditing(false); setAttestedSnapshot(''); setCheckedOn(japanDay()); setError(''); pendingFocus.current = true
  }
  const editForm = (field, value) => {
    setForms(previous => ({ ...previous, [item.resource_key]: { ...form, [field]: value } }))
    setAttestedSnapshot(''); setError('')
  }
  const captureRevision = () => {
    if (!item) return
    setForms(previous => previous[item.resource_key] ? previous : { ...previous, [item.resource_key]: { ...form } })
  }
  const reloadItem = () => {
    if (locked || !item || !window.confirm(t('reviewFixes.confirmReloadReview'))) return
    setForms(previous => { const next = { ...previous }; delete next[item.resource_key]; return next })
    setEditing(false); setAttestedSnapshot(''); setCheckedOn(japanDay()); setError('')
  }
  const validDate = value => {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(value || '')) return false
    const date = new Date(`${value}T00:00:00+09:00`)
    return Number.isFinite(date.getTime()) && japanDay(date) === value
  }
  const process = async decision => {
    if (saving.current || locked || !item || conflict) return
    if (!validDate(form.next_review_on) || form.next_review_on <= japanDay()) { setError('dates'); return }
    if (decision === 'deferred' && !form.reason.trim()) { setError('reason'); return }
    if (decision === 'checked' && (!attested || !validDate(checkedOn) || checkedOn > japanDay())) { setError('dates'); return }
    const draft = decision === 'deferred' ? null : { ...profile, resources: profile.resources.map(resource =>
      resource.resource_key === item.resource_key && decision === 'checked' ? { ...resource, checked_on: checkedOn, review_due_on: form.next_review_on } : resource) }
    saving.current = true; setBusy(true); setError('')
    try {
      const saved = await onSaveReview({ contact_key: item.resource_key, revision: form.baseRevision,
        decision, reason: form.reason, assignee: form.assignee, next_review_on: form.next_review_on,
        profile: draft, confirmed: decision !== 'deferred' })
      if (!saved) { setError('save'); return }
      setForms(previous => { const next = { ...previous }; delete next[item.resource_key]; return next })
      setIndex(value => value + 1); setEditing(false); setAttestedSnapshot(''); setCheckedOn(japanDay()); pendingFocus.current = true
    } finally { saving.current = false; setBusy(false) }
  }
  return <section className="weekly-directory-review"><h3 id="weekly-review-heading" ref={heading} tabIndex={-1}>{t('interaction.weekly.title')}</h3>
    <p>{t('continuity.review.notice')}</p>
    {formsDirty && <p role="status">{t('continuity.review.unsaved')}</p>}
    {!queue ? <button type="button" className="pilot-button" disabled={locked || !eligible.length} onClick={() => start(eligible.map(resource => resource.resource_key))}>{t('interaction.weekly.start', { count: eligible.length })}</button>
      : index >= queue.length ? <>
        <p role="status">{t('continuity.review.finished')}</p><p>{t(hasUnpublishedChanges ? 'interaction.weekly.finishNotice' : 'ui.organization.upToDate')}</p>
        <div className="pilot-actions"><button type="button" className="pilot-button secondary" disabled={locked} onClick={onSaveDraft}>{t('ui.organization.saveDraft')}</button>
          <button type="button" className="pilot-button" disabled={locked} onClick={onPreview}>{t('interaction.weekly.preview')}</button>
          <button type="button" className="pilot-button secondary" disabled={locked} onClick={() => setQueue(null)}>{t('interaction.weekly.close')}</button></div>
      </> : <>
        <p>{t('interaction.weekly.position', { number: index + 1, count: queue.length })}</p>
        {item ? <article className="support-card"><h4>{item.name || t('work.unnamedResource')}</h4>
          <p>{item.maintainer || t('polish.noMaintainer')} · {item.review_due_on || t('polish.noReviewDate')}</p>
          <p>{t('polish.supportPurpose')}: {t(`polish.purposes.${item.category || 'parenting'}`)}</p>
          <dl className="weekly-contact-facts">{['description', 'area', 'audience', 'hours', 'phone', 'cost_note', 'application_steps', 'visiting_note', 'preparation', 'fallback_contact', 'pause_notice'].map(field => <div key={field}>
            <dt>{t(['application_steps', 'preparation', 'fallback_contact', 'pause_notice'].includes(field) ? `flows.directory.${field}`
              : field === 'visiting_note' ? 'localCare.support.visiting_note' : ['description', 'hours'].includes(field) ? `pilot.resource.${field}` : `work.resourceFields.${field}`)}</dt>
            <dd className="preserve-lines">{item[field]?.trim() || t('pilot.notProvided')}</dd>
          </div>)}</dl>
          <p>{t('flows.directory.service_status')}: {t(`flows.directory.statuses.${item.service_status || 'active'}`)}</p>
          {publicHttps(item.url) && <a href={publicHttps(item.url)} target="_blank" rel="noreferrer">{t('interaction.weekly.source')}</a>}
          {publicHttps(item.booking_url) && <p><a href={publicHttps(item.booking_url)} target="_blank" rel="noreferrer">{t('work.booking')}</a></p>}
          {conflict && <div role="alert"><p>{t('reviewFixes.reviewConflict')}</p>
            <h5>{t('reviewFixes.latestReview')}</h5>
            <p>{task?.assignee || t('polish.noMaintainer')} · {task?.next_review_on || t('polish.noReviewDate')}</p>
            <p className="preserve-lines">{task?.reason || t('pilot.notProvided')}</p>
            <button type="button" className="pilot-button secondary" disabled={locked} onClick={reloadItem}>{t('reviewFixes.reloadReview')}</button>
          </div>}
          <fieldset disabled={locked || conflict}><legend>{t('continuity.review.internal')}</legend>
            <p>{t('continuity.review.internalNotice')}</p>
            <label>{t('continuity.review.assignee')}<input maxLength={100} value={form.assignee} onChange={event => editForm('assignee', event.target.value)} /></label>
            <label>{t('continuity.review.reason')}<textarea rows={3} maxLength={500} value={form.reason} onChange={event => editForm('reason', event.target.value)} /></label>
            <label>{t('continuity.review.next')}<input type="date" required min={japanDay()} value={form.next_review_on} onChange={event => editForm('next_review_on', event.target.value)} /></label>
          </fieldset>
          <div className="pilot-actions"><button type="button" className="pilot-button secondary" disabled={locked || conflict} onClick={() => { captureRevision(); setEditing(true); onEdit(item.resource_key) }}>{t('interaction.weekly.edit')}</button>
            <button type="button" className="pilot-button secondary" disabled={locked || conflict || !savedContactKeys.includes(item.resource_key)} onClick={() => process('deferred')}>{t('continuity.review.defer')}</button></div>
          {!savedContactKeys.includes(item.resource_key) && <p>{t('continuity.review.saveNewFirst')}</p>}
          {editing ? <><p>{t('continuity.review.saveAllDraft')}</p><button type="button" className="pilot-button secondary" disabled={locked || conflict} onClick={() => process('edited')}>{t('continuity.review.saveEdited')}</button></>
            : <fieldset disabled={locked || conflict}><legend>{t('interaction.weekly.unchanged')}</legend>
              <label>{t('pilot.checkedOn')}<input type="date" required value={checkedOn} max={japanDay()} onChange={event => { captureRevision(); setCheckedOn(event.target.value); setAttestedSnapshot('') }} /></label>
              <p>{t('continuity.review.confirmDates')}</p>
              <label><input type="checkbox" checked={attested} onChange={event => { captureRevision(); setAttestedSnapshot(event.target.checked ? snapshot : '') }} />{t('interaction.weekly.attest')}</label>
              <button type="button" className="pilot-button secondary" disabled={!attested} onClick={() => process('checked')}>{t('continuity.review.saveChecked')}</button>
            </fieldset>}
          {error && <p role="alert">{t(`continuity.review.errors.${error}`)}</p>}
        </article> : <p>{t('interaction.weekly.removed')}</p>}
        <button type="button" className="text-action" disabled={locked} onClick={() => setQueue(null)}>{t('interaction.weekly.close')}</button>
      </>}
    <details><summary>{t('continuity.review.savedTasks')}</summary><ul>{reviewTasks.map(saved => {
      const resource = profile.resources.find(contact => contact.resource_key === saved.contact_key)
      return <li key={saved.contact_key}><strong>{resource?.name || t('interaction.weekly.removed')}</strong>
        <p>{t(`continuity.review.decisions.${saved.decision}`)} · {saved.assignee || t('polish.noMaintainer')} · {saved.next_review_on || t('polish.noReviewDate')}</p>
        <p className="preserve-lines">{saved.reason}</p><small>{japanDateTime(saved.updated_at, i18n.resolvedLanguage || 'ja')}</small>
        {saved.stale && <p>{t('continuity.review.stale')}</p>}
        <button type="button" className="text-action" disabled={locked || !resource} onClick={() => start([saved.contact_key])}>{t('continuity.review.reopen')}</button>
      </li>
    })}</ul></details>
  </section>
}
