import React, { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../utils/api'
import LanguageSelector from './LanguageSelector'
import SupportDirectory from './SupportDirectory'
import FamilyHandout from './FamilyHandout'
import { needsReview, phoneHref, publicHttps } from '../utils/publicDirectory'
import { japanDay, japanDateTime } from '../utils/japanTime'
import { requestKey } from '../utils/recordOperations'

const emptyResource = category => ({ resource_key: requestKey(), category, name: '', url: '', description: '', hours: '', area: '',
  audience: '', phone: '', booking_url: null, cost_note: '', checked_on: null, maintainer: '', review_due_on: null })
const resourceFields = ['name', 'url', 'description', 'area', 'audience', 'phone', 'booking_url', 'hours', 'cost_note', 'checked_on', 'maintainer', 'review_due_on']

export default function OrganizationPortal({ userId, onFamily, onExit, registerLeaveGuard }) {
  const { t, i18n } = useTranslation()
  const [profile, setProfile] = useState(null)
  const [savedDraft, setSavedDraft] = useState(null)
  const [published, setPublished] = useState(null)
  const [revision, setRevision] = useState(0)
  const [history, setHistory] = useState([])
  const [selected, setSelected] = useState('')
  const [status, setStatus] = useState('loading')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [reloading, setReloading] = useState(true)
  const [previewed, setPreviewed] = useState(false)
  const [attempt, setAttempt] = useState(0)
  const [directoryVersion, setDirectoryVersion] = useState(0)
  const [copied, setCopied] = useState(false)
  const formRef = useRef(null)
  const actionBusy = useRef(false)
  const reloadBusy = useRef(true)
  const editingBlocked = busy || reloading
  const familyLink = `${window.location.origin}/family`
  const dirty = Boolean(profile && JSON.stringify(profile) !== JSON.stringify(savedDraft))
  const unpublished = Boolean(profile && JSON.stringify(profile) !== JSON.stringify(published))
  const canLeave = useCallback(() => {
    if (actionBusy.current) { setError(t('work.saveInProgress')); return false }
    return !dirty || window.confirm(`${t('work.unsavedTitle')}\n${t('work.unsavedDescription')}`)
  }, [dirty, t])
  useLayoutEffect(() => registerLeaveGuard?.(canLeave), [registerLeaveGuard, canLeave])
  const applyResult = result => {
    setProfile(result.workspace.profile); setSavedDraft(result.workspace.profile); setPublished(result.profile)
    setRevision(result.workspace.revision); setHistory(result.history); setPreviewed(false)
    setSelected(previous => result.workspace.profile.resources.some(resource => resource.resource_key === previous)
      ? previous : result.workspace.profile.resources[0]?.resource_key || '')
  }
  useEffect(() => {
    let active = true
    reloadBusy.current = true; setReloading(true); setStatus('loading')
    api.get('/api/pilot/organization').then(result => {
      if (active) { applyResult(result); setStatus('ready'); setError('') }
    }).catch(err => { if (active) setStatus(err.status === 403 ? 'denied' : 'failed') })
      .finally(() => { if (active) { reloadBusy.current = false; setReloading(false) } })
    return () => { active = false }
  }, [userId, attempt])
  useEffect(() => {
    if (!dirty && !busy) return
    const warn = event => { event.preventDefault(); event.returnValue = '' }
    window.addEventListener('beforeunload', warn)
    return () => window.removeEventListener('beforeunload', warn)
  }, [dirty, busy])
  const change = updater => {
    if (actionBusy.current || reloadBusy.current) return
    setProfile(previous => typeof updater === 'function' ? updater(previous) : updater)
    setPreviewed(false); setStatus('ready'); setError('')
  }
  const perform = async (path, body, nextStatus) => {
    if (actionBusy.current || reloadBusy.current) return
    actionBusy.current = true; setBusy(true); setError('')
    try { applyResult(await api.post(path, body)); setStatus(nextStatus); setDirectoryVersion(value => value + 1) }
    catch (err) { setError(t(err.status === 409 ? 'polish.institutionConflict' : err.status === 422 ? 'polish.completePublication' : 'pilot.saveFailed')) }
    finally { actionBusy.current = false; setBusy(false) }
  }
  const addResource = category => {
    if (actionBusy.current || reloadBusy.current) return
    const resource = { ...emptyResource(category), name: t(`polish.purposes.${category}`), area: profile.municipality || '' }
    change(previous => ({ ...previous, resources: [...previous.resources, resource] })); setSelected(resource.resource_key)
  }
  const updateResource = (key, value) => change(previous => ({ ...previous,
    resources: previous.resources.map(resource => resource.resource_key === selected ? { ...resource, [key]: value } : resource) }))
  const resource = profile?.resources.find(item => item.resource_key === selected)
  const due = (profile?.resources || []).map(item => {
    const issues = ['name', 'url', 'area', 'audience', 'hours', 'maintainer'].filter(key => !item[key]?.trim())
    if (needsReview(item.checked_on)) issues.push('checked_on')
    if (!phoneHref(item.phone) && !publicHttps(item.booking_url)) issues.push('contact')
    if (!item.review_due_on || item.review_due_on <= japanDay()) issues.push('review_due_on')
    return { resource: item, issues }
  }).filter(item => item.issues.length)
  const reload = () => {
    if (actionBusy.current || reloadBusy.current) return
    if (dirty && !window.confirm(t('polish.reloadDraftConfirm'))) return
    reloadBusy.current = true; setReloading(true); setAttempt(value => value + 1)
  }
  const labelFor = key => ['maintainer', 'review_due_on'].includes(key) ? t(`polish.${key}`)
    : ['name', 'url', 'description', 'hours', 'checked_on'].includes(key) ? t(`pilot.resource.${key}`) : t(`work.resourceFields.${key}`)

  return <main className="pilot-shell organization-portal">
    <div className="pilot-topbar"><strong>{t('pilot.organizationTitle')}</strong><LanguageSelector /></div>
    <h1>{t('pilot.organizationHeading')}</h1><p>{t('pilot.organizationScope')}</p>
    <div className="pilot-actions">
      <button className="pilot-button secondary" disabled={busy} onClick={() => { if (registerLeaveGuard || canLeave()) onFamily() }}>{t('pilot.openFamily')}</button>
      <button className="pilot-button secondary" disabled={busy} onClick={() => { if (registerLeaveGuard || canLeave()) onExit() }}>{t('pilot.switchEntrance')}</button>
      <button className="pilot-button secondary" disabled={busy} onClick={() => { if (canLeave()) api.logout() }}>{t('settings.logout')}</button>
    </div>
    {status === 'loading' && <p role="status">{t('common.loading')}</p>}
    {status === 'denied' && <section className="pilot-panel"><h2>{t('pilot.accessNeeded')}</h2><p>{t('pilot.accessInstructions')}</p>
      <label>{t('pilot.accountId')}<input readOnly value={userId} /></label></section>}
    {status === 'failed' && <p role="alert">{t('pilot.loadFailed')} <button disabled={editingBlocked} onClick={reload}>{t('pilot.retry')}</button></p>}
    {profile && <>
      <section className="pilot-panel"><h2>{t('pilot.familyLink')}</h2><input aria-label={t('pilot.familyLink')} readOnly value={familyLink} />
        <button type="button" className="pilot-button secondary" onClick={async () => {
          try { await navigator.clipboard.writeText(familyLink); setCopied(true) }
          catch { setError(t('pilot.copyFailed')) }
        }}>{t(copied ? 'pilot.copied' : 'pilot.copyLink')}</button>
        <FamilyHandout familyLink={familyLink} organizationName={published?.name} />
      </section>
      <section className="pilot-panel"><h2>{t('work.reviewQueue')}</h2><p>{t('polish.maintenanceNotice')}</p>
        {due.length ? <ul>{due.map(({ resource: item, issues }) => <li key={item.resource_key}>
          <button type="button" disabled={editingBlocked} onClick={() => setSelected(item.resource_key)}>{item.name || t('work.unnamedResource')}</button>
          <span> · {item.maintainer || t('polish.noMaintainer')} · {item.review_due_on || t('polish.noReviewDate')}</span>
          <p>{issues.map(key => ['maintainer', 'review_due_on'].includes(key) ? t(`polish.${key}`)
            : ['name', 'url'].includes(key) ? t(`pilot.resource.${key}`) : t(`work.reviewIssues.${key}`)).join(' / ')}</p>
        </li>)}</ul> : <p>{t('work.noReviewDue')}</p>}
      </section>
      <form ref={formRef} className="pilot-panel pilot-form" onSubmit={event => {
        event.preventDefault()
        if (!editingBlocked && previewed) perform('/api/pilot/organization', { profile, revision }, 'saved')
      }}>
        <h2>{t('pilot.directoryEditor')}</h2><p>{t('pilot.publicFields')}</p>
        {dirty && <p role="status">{t('polish.localDraftUnsaved')}</p>}
        {!dirty && unpublished && <p role="status">{t('polish.serverDraftOnly')}</p>}
        <details><summary>{t('work.businessInfo')}</summary><fieldset disabled={editingBlocked}>
          <legend>{t('work.businessInfo')}</legend>
          {['name', 'municipality', 'contact', 'hours', 'phone', 'email'].map(key => <label key={key}>
            {t(['phone', 'email'].includes(key) ? `work.${key}` : `pilot.${key}`)}
            <input type={key === 'email' ? 'email' : key === 'phone' ? 'tel' : 'text'} value={profile[key] || ''}
              maxLength={key === 'phone' ? 40 : key === 'email' ? 255 : key === 'name' || key === 'municipality' ? 100 : 200}
              onChange={event => change({ ...profile, [key]: event.target.value })} />
          </label>)}
          {['retention_notice', 'ai_data_notice', 'account_support_notice'].map(key => <label key={key}>
            {t(key === 'retention_notice' ? 'pilot.retention' : key === 'ai_data_notice' ? 'work.aiHandling' : 'work.supportHandling')}
            <textarea value={profile[key] || ''} maxLength={key === 'ai_data_notice' ? 1500 : 1000}
              onChange={event => change({ ...profile, [key]: event.target.value })} />
          </label>)}<p>{t('work.operatorCheckNotice')}</p>
        </fieldset></details>
        <h3>{t('pilot.localResources')}</h3><p>{t('work.templateNotice')}</p>
        <div className="pilot-actions">{['postpartum', 'parenting', 'feeding'].map(category => <button key={category} type="button"
          className="pilot-button secondary" disabled={editingBlocked || profile.resources.length >= 10} onClick={() => addResource(category)}>{t(`polish.purposes.${category}`)}</button>)}</div>
        <ul className="contact-editor-list">{profile.resources.map(item => <li key={item.resource_key}>
          <button type="button" disabled={editingBlocked} aria-pressed={selected === item.resource_key} onClick={() => setSelected(item.resource_key)}>{item.name || t('work.unnamedResource')}</button>
          <span>{item.maintainer || t('polish.noMaintainer')} · {item.review_due_on || t('polish.noReviewDate')}</span>
        </li>)}</ul>
        {resource && <fieldset disabled={editingBlocked}><legend>{t('polish.editContact')}</legend>
          <label>{t('polish.supportPurpose')}<select value={resource.category || 'parenting'} onChange={event => updateResource('category', event.target.value)}>
            {['parenting', 'postpartum', 'feeding'].map(key => <option key={key} value={key}>{t(`polish.purposes.${key}`)}</option>)}
          </select></label>
          {resourceFields.map(key => <label key={key}>{labelFor(key)}
            <input type={['checked_on', 'review_due_on'].includes(key) ? 'date' : ['url', 'booking_url'].includes(key) ? 'url' : key === 'phone' ? 'tel' : 'text'}
              max={key === 'checked_on' ? japanDay() : undefined} value={resource[key] || ''}
              maxLength={['name', 'area', 'maintainer'].includes(key) ? 100 : key === 'phone' ? 40 : ['hours', 'audience'].includes(key) ? 200 : key === 'cost_note' ? 300 : 500}
              onChange={event => updateResource(key, ['checked_on', 'review_due_on', 'booking_url'].includes(key) ? event.target.value || null : event.target.value)} />
          </label>)}
          <button type="button" className="pilot-button secondary" onClick={() => {
            if (window.confirm(t('polish.removeContactConfirm'))) { change({ ...profile, resources: profile.resources.filter(item => item.resource_key !== selected) }); setSelected('') }
          }}>{t('common.delete')}</button>
        </fieldset>}
        <div className="pilot-actions">
          <button type="button" className="pilot-button secondary" disabled={editingBlocked} onClick={() => perform('/api/pilot/organization/draft', { profile, revision }, 'draftSaved')}>{t('polish.saveInstitutionDraft')}</button>
          <button type="button" className="pilot-button secondary" disabled={editingBlocked} onClick={() => {
            if (!profile.name.trim() || profile.resources.some(item => !item.name.trim() || !publicHttps(item.url)) || !formRef.current?.reportValidity()) {
              setError(t('polish.completePublication')); return
            }
            setPreviewed(true); setError('')
          }}>{t('work.previewPublication')}</button>
          <button className="pilot-button" disabled={editingBlocked || !previewed}>{t(busy ? 'settings.saving' : 'pilot.publishDirectory')}</button>
        </div>
        {previewed && <section className="publication-preview"><h3>{t('work.previewOnly')}</h3><SupportDirectory previewProfile={profile} /></section>}
        {status === 'saved' && <p role="status">{t('pilot.saved')}</p>}{status === 'draftSaved' && <p role="status">{t('polish.serverDraftOnly')}</p>}
      </form>
      <details className="pilot-panel"><summary>{t('polish.publicationHistory')}</summary><p>{t('polish.restorePublicationNotice')}</p>
        {history.length === 0 && <p>{t('polish.noPublicationHistory')}</p>}
        <ul>{history.map(item => <li key={item.id}><time>{japanDateTime(item.published_at, i18n.resolvedLanguage || 'ja')}</time> · {item.name}
          {item.fields?.length > 0 && <p>{t('polish.businessInfoChanged')}</p>}
          {['added', 'removed', 'updated'].map(key => item.changes?.[key]?.length > 0 && <p key={key}>
            {t(`polish.publicationChanges.${key}`)}: {item.changes[key].join(' / ')}
          </p>)}
          <button type="button" disabled={editingBlocked} onClick={() => {
            if (window.confirm(t('polish.restoreVersionConfirm'))) perform('/api/pilot/organization/restore', { history_id: item.id, revision }, 'draftSaved')
          }}>{t('polish.restoreAsDraft')}</button>
        </li>)}</ul>
      </details>
      {error && <p role="alert">{error} <button type="button" disabled={editingBlocked} onClick={reload}>{t('polish.reloadServerDraft')}</button></p>}
    </>}
    <SupportDirectory key={directoryVersion} />
  </main>
}
