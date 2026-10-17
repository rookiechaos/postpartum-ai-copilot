import React, { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { japanDay } from '../utils/japanTime'
import { publicHttps, phoneHref } from '../utils/publicDirectory'
import { revealElement } from '../utils/focusView'

export default function WeeklyDirectoryReview({ profile, due, maintainerFilter, blocked, hasUnpublishedChanges, onEdit, onConfirm, onSaveDraft, onPreview, onSessionChange }) {
  const { t } = useTranslation()
  const [queue, setQueue] = useState(null)
  const [index, setIndex] = useState(0)
  const [decisions, setDecisions] = useState({})
  const [editing, setEditing] = useState(false)
  const [checked, setChecked] = useState(false)
  const [attestedSnapshot, setAttestedSnapshot] = useState('')
  const [checkedOn, setCheckedOn] = useState('')
  const [dueOn, setDueOn] = useState('')
  const [error, setError] = useState('')
  const heading = useRef(null)
  const item = queue && profile.resources.find(resource => resource.resource_key === queue[index])
  const currentSnapshot = item ? JSON.stringify(item) : ''
  const attested = checked && Boolean(item) && attestedSnapshot === currentSnapshot
  useEffect(() => { onSessionChange?.(Boolean(queue)) }, [queue, onSessionChange])
  const eligible = due.filter(({ resource }) => !maintainerFilter || (maintainerFilter === 'unassigned'
    ? !resource.maintainer?.trim() : `name:${resource.maintainer?.trim()}` === maintainerFilter))
  const start = () => {
    setQueue(eligible.map(({ resource }) => resource.resource_key)); setIndex(0); setDecisions({})
    setEditing(false); setChecked(false); setCheckedOn(japanDay()); setDueOn(''); setError('')
  }
  const next = decision => {
    if (blocked || !queue) return
    setDecisions(previous => ({ ...previous, [queue[index]]: decision })); setIndex(value => value + 1)
    setChecked(false); setEditing(false); setCheckedOn(japanDay()); setDueOn(''); setError('')
    revealElement(heading.current)
  }
  const dateValid = value => {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false
    const date = new Date(`${value}T00:00:00+09:00`)
    return Number.isFinite(date.getTime()) && japanDay(date) === value
  }
  return <section className="weekly-directory-review"><h3 id="weekly-review-heading" ref={heading} tabIndex={-1}>{t('interaction.weekly.title')}</h3>
    <p>{t('interaction.weekly.notice')}</p>
    {!queue ? <button type="button" className="pilot-button" disabled={blocked || eligible.length === 0} onClick={start}>
      {t('interaction.weekly.start', { count: eligible.length })}</button>
      : index >= queue.length ? <>
        <p role="status">{t('interaction.weekly.complete', { count: queue.length, deferred: Object.values(decisions).filter(value => value === 'later').length })}</p>
        <p>{t(hasUnpublishedChanges ? 'interaction.weekly.finishNotice' : 'ui.organization.upToDate')}</p>
        <div className="pilot-actions"><button type="button" className="pilot-button secondary" disabled={blocked} onClick={onSaveDraft}>{t('ui.organization.saveDraft')}</button>
          <button type="button" className="pilot-button" disabled={blocked} onClick={onPreview}>{t('interaction.weekly.preview')}</button>
          <button type="button" className="pilot-button secondary" disabled={blocked} onClick={() => setQueue(null)}>{t('interaction.weekly.close')}</button></div>
      </> : <>
        <p>{t('interaction.weekly.position', { number: index + 1, count: queue.length })}</p>
        {item ? <article className="support-card"><h4>{item.name || t('work.unnamedResource')}</h4>
          <p>{item.maintainer || t('polish.noMaintainer')} · {item.review_due_on || t('polish.noReviewDate')}</p>
          <p>{t('polish.supportPurpose')}: {t(`polish.purposes.${item.category || 'parenting'}`)}</p>
          <p>{t('pilot.checkedOn')}: {item.checked_on || t('pilot.notChecked')}</p>
          <dl className="weekly-contact-facts">{['description', 'area', 'audience', 'hours', 'phone', 'cost_note', 'application_steps', 'visiting_note', 'preparation', 'fallback_contact', 'pause_notice'].map(field => <div key={field}>
            <dt>{t(['application_steps', 'preparation', 'fallback_contact', 'pause_notice'].includes(field) ? `flows.directory.${field}`
              : field === 'visiting_note' ? 'localCare.support.visiting_note' : field === 'hours' ? 'pilot.hours'
              : field === 'description' ? 'pilot.resource.description' : `work.resourceFields.${field}`)}</dt>
            <dd className="preserve-lines">{item[field]?.trim() || t('pilot.notProvided')}</dd>
          </div>)}</dl>
          <p>{t('flows.directory.service_status')}: {t(`flows.directory.statuses.${item.service_status || 'active'}`)}</p>
          {publicHttps(item.url) && <a href={publicHttps(item.url)} target="_blank" rel="noreferrer">{t('interaction.weekly.source')}</a>}
          {publicHttps(item.booking_url) && <p><a href={publicHttps(item.booking_url)} target="_blank" rel="noreferrer">{t('work.booking')}</a></p>}
          {phoneHref(item.phone) && <p>{item.phone}</p>}
          <div className="pilot-actions"><button type="button" className="pilot-button secondary" disabled={blocked} onClick={() => { setEditing(true); onEdit(item.resource_key) }}>{t('interaction.weekly.edit')}</button>
            <button type="button" className="pilot-button secondary" disabled={blocked} onClick={() => next('later')}>{t('interaction.weekly.later')}</button></div>
          {editing ? <>
            <p>{t('interaction.weekly.editNotice')}</p><button type="button" className="pilot-button secondary" disabled={blocked} onClick={() => next('edited')}>{t('interaction.weekly.edited')}</button>
          </> : <fieldset disabled={blocked}><legend>{t('interaction.weekly.unchanged')}</legend>
            <label>{t('pilot.checkedOn')}<input type="date" required value={checkedOn} max={japanDay()} onChange={event => { setCheckedOn(event.target.value); setChecked(false) }} /></label>
            <label>{t('polish.review_due_on')}<input type="date" required value={dueOn} min={japanDay()} onChange={event => { setDueOn(event.target.value); setChecked(false) }} /></label>
            <label><input type="checkbox" checked={attested} onChange={event => { setChecked(event.target.checked); setAttestedSnapshot(currentSnapshot) }} />{t('interaction.weekly.attest')}</label>
            <button type="button" className="pilot-button secondary" disabled={!attested} onClick={() => {
              if (!attested) return
              if (!dateValid(checkedOn) || checkedOn > japanDay() || !dateValid(dueOn) || dueOn <= checkedOn || dueOn < japanDay()) { setError('dates'); return }
              onConfirm(item.resource_key, checkedOn, dueOn); next('unchanged')
            }}>{t('interaction.weekly.confirm')}</button>
          </fieldset>}
          {error && <p role="alert">{t('interaction.weekly.dateError')}</p>}
        </article> : <><p>{t('interaction.weekly.removed')}</p><button type="button" className="pilot-button secondary" disabled={blocked} onClick={() => next('later')}>{t('interaction.weekly.next')}</button></>}
        <button type="button" className="text-action" disabled={blocked} onClick={() => setQueue(null)}>{t('interaction.weekly.close')}</button>
      </>}
  </section>
}
