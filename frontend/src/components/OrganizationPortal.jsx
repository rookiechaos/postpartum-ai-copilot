import React, { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../utils/api'
import LanguageSelector from './LanguageSelector'
import SupportDirectory from './SupportDirectory'
import FamilyHandout from './FamilyHandout'
import ConnectionNotice from './ConnectionNotice'
import { needsReview, phoneHref, publicHttps } from '../utils/publicDirectory'
import { japanDay, japanDateTime } from '../utils/japanTime'
import { requestKey } from '../utils/recordOperations'
import { revealElement } from '../utils/focusView'
import { businessLimits, resourceLimits, directoryFieldId, normalizeDirectory, validateDirectory, directoryServerIssues, publicationChanges } from '../utils/directoryValidation'

const emptyResource = category => ({ resource_key: requestKey(), category, name: '', url: '', description: '', hours: '', area: '',
  audience: '', phone: '', booking_url: null, cost_note: '', checked_on: null, maintainer: '', review_due_on: null,
  service_status: 'active', pause_notice: '', application_steps: '', visiting_note: '', preparation: '', fallback_contact: '' })
const resourceGroups = {
  basic: ['name', 'url', 'area', 'phone', 'hours'],
  details: ['description', 'audience', 'booking_url', 'cost_note', 'application_steps', 'visiting_note', 'preparation', 'fallback_contact', 'pause_notice'],
  review: ['maintainer', 'checked_on', 'review_due_on'],
}

export default function OrganizationPortal({ userId, onFamily, onExit, registerLeaveGuard }) {
  const { t, i18n } = useTranslation()
  const [profile, setProfile] = useState(null)
  const [savedDraft, setSavedDraft] = useState(null)
  const [published, setPublished] = useState(null)
  const [revision, setRevision] = useState(0)
  const [history, setHistory] = useState([])
  const [selected, setSelected] = useState('')
  const [editorTask, setEditorTask] = useState('all')
  const [maintainerFilter, setMaintainerFilter] = useState('')
  const [status, setStatus] = useState('loading')
  const [error, setError] = useState('')
  const [issues, setIssues] = useState([])
  const [busy, setBusy] = useState(false)
  const [reloading, setReloading] = useState(true)
  const [previewed, setPreviewed] = useState(false)
  const [publicationComplete, setPublicationComplete] = useState(false)
  const [attempt, setAttempt] = useState(0)
  const [copied, setCopied] = useState(false)
  const [focusRequest, setFocusRequest] = useState(0)
  const pendingFocus = useRef(null)
  const actionBusy = useRef(false)
  const reloadBusy = useRef(true)
  const editingBlocked = busy || reloading
  const familyLink = `${window.location.origin}/family`
  const dirty = Boolean(profile && JSON.stringify(profile) !== JSON.stringify(savedDraft))
  const changes = profile ? publicationChanges(published, profile) : []
  const unpublished = changes.length > 0
  const canLeave = useCallback(() => {
    if (actionBusy.current) { setError(t('work.saveInProgress')); return false }
    return !dirty || window.confirm(`${t('work.unsavedTitle')}\n${t('work.unsavedDescription')}`)
  }, [dirty, t])
  useLayoutEffect(() => registerLeaveGuard?.(canLeave), [registerLeaveGuard, canLeave])
  const focusField = (id, resourceKey = '', origin = null, task = 'all') => {
    if (resourceKey) {
      setSelected(resourceKey)
      setEditorTask(task)
      const target = profile?.resources.find(item => item.resource_key === resourceKey)
      if (maintainerFilter && (maintainerFilter === 'unassigned' ? Boolean(target?.maintainer?.trim())
        : `name:${target?.maintainer?.trim()}` !== maintainerFilter)) setMaintainerFilter('')
    }
    pendingFocus.current = { id, origin }; setFocusRequest(value => value + 1)
  }
  const focusIssue = issue => focusField(issue.field === 'resources' ? 'directory-contacts'
    : directoryFieldId(issue.scope, issue.field, issue.resourceKey), issue.resourceKey)
  useEffect(() => {
    if (editingBlocked || !pendingFocus.current) return
    const request = pendingFocus.current
    // Check after the result has rendered: never steal focus from another control
    // the user chose while an explicit publication request was pending.
    if (request.origin && document.activeElement !== request.origin && document.activeElement !== document.body) {
      pendingFocus.current = null; return
    }
    const element = document.getElementById(request.id)
    if (element && revealElement(element)) pendingFocus.current = null
  }, [focusRequest, selected, editorTask, editingBlocked, previewed])
  const applyResult = result => {
    setProfile(result.workspace.profile); setSavedDraft(result.workspace.profile); setPublished(result.profile)
    setRevision(result.workspace.revision); setHistory(result.history); setPreviewed(false); setIssues([])
    setPublicationComplete(false)
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
    setPreviewed(false); setPublicationComplete(false); setStatus('ready'); setError('')
  }
  const perform = async (path, body, nextStatus) => {
    if (actionBusy.current || reloadBusy.current) return
    const origin = document.activeElement
    actionBusy.current = true; setBusy(true); setError(''); setIssues([])
    try {
      applyResult(await api.post(path, body)); setStatus(nextStatus)
      if (nextStatus === 'saved') {
        setPublicationComplete(true)
        // A disabled/disappearing submit button can release focus to the body.
        focusField('directory-publication-result', '', origin)
      }
    }
    catch (err) {
      setPreviewed(false)
      setError(t(err.status === 409 ? 'polish.institutionConflict' : err.status === 422 ? 'polish.completePublication'
        : err.resultUnconfirmed ? 'flows.connection.unconfirmedAction' : 'pilot.saveFailed'))
      const fieldIssues = err.status === 422 && body.profile ? directoryServerIssues(err.validation, body.profile) : []
      setIssues(fieldIssues)
      if (fieldIssues.length) focusIssue(fieldIssues[0])
      else focusField('directory-errors')
    } finally { actionBusy.current = false; setBusy(false) }
  }
  const validate = publication => {
    if (actionBusy.current || reloadBusy.current) return null
    const next = normalizeDirectory(profile)
    const found = validateDirectory(next, { publication })
    setIssues(found); setError('')
    if (found.length) { setPreviewed(false); focusIssue(found[0]); return null }
    // Normalized phone numbers and links are also the values shown in the preview.
    setProfile(next)
    return next
  }
  const addResource = category => {
    if (actionBusy.current || reloadBusy.current || profile.resources.length >= 10) return
    const resource = { ...emptyResource(category), name: t(`polish.purposes.${category}`), area: profile.municipality || '' }
    change(previous => ({ ...previous, resources: [...previous.resources, resource] }))
    focusField(directoryFieldId('resource', 'name', resource.resource_key), resource.resource_key)
  }
  const clearFieldIssue = (scope, field, resourceKey = '') => setIssues(previous => previous.filter(issue =>
    !(issue.scope === scope && issue.field === field && issue.resourceKey === resourceKey)))
  const updateBusiness = (key, value) => {
    if (actionBusy.current || reloadBusy.current) return
    change(previous => ({ ...previous, [key]: value })); clearFieldIssue('business', key)
  }
  const updateResource = (key, value) => {
    if (actionBusy.current || reloadBusy.current) return
    change(previous => ({ ...previous, resources: previous.resources.map(resource =>
      resource.resource_key === selected ? { ...resource, [key]: value } : resource) }))
    clearFieldIssue('resource', key, selected)
  }
  const resource = profile?.resources.find(item => item.resource_key === selected)
  const visibleResources = (profile?.resources || []).filter(item => !maintainerFilter ||
    (maintainerFilter === 'unassigned' ? !item.maintainer?.trim() : `name:${item.maintainer?.trim()}` === maintainerFilter))
  const maintainers = [...new Set((profile?.resources || []).map(item => item.maintainer?.trim()).filter(Boolean))]
  const changedContacts = new Set(changes.map(item => item.resourceKey).filter(Boolean))
  const due = (profile?.resources || []).map(item => {
    const issues = ['name', 'url', 'area', 'audience', 'hours', 'maintainer'].filter(key => !item[key]?.trim())
    if (needsReview(item.checked_on)) issues.push('checked_on')
    if (!phoneHref(item.phone) && !publicHttps(item.booking_url)) issues.push('contact')
    if (!item.review_due_on || item.review_due_on <= japanDay()) issues.push('review_due_on')
    return { resource: item, issues }
  }).filter(item => item.issues.length)
  const dueContacts = new Set(due.map(item => item.resource.resource_key))
  const reload = () => {
    if (actionBusy.current || reloadBusy.current) return
    if (dirty && !window.confirm(t('polish.reloadDraftConfirm'))) return
    pendingFocus.current = null
    reloadBusy.current = true; setReloading(true); setAttempt(value => value + 1)
  }
  const labelFor = key => key === 'visiting_note' ? t('localCare.support.visiting_note')
    : ['service_status', 'pause_notice', 'application_steps', 'preparation', 'fallback_contact'].includes(key) ? t(`flows.directory.${key}`)
    : key === 'category' ? t('polish.supportPurpose')
    : ['maintainer', 'review_due_on'].includes(key) ? t(`polish.${key}`)
    : ['name', 'url', 'description', 'hours', 'checked_on'].includes(key) ? t(`pilot.resource.${key}`) : t(`work.resourceFields.${key}`)
  const businessLabel = key => key === 'resources' ? t('pilot.localResources')
    : key === 'retention_notice' ? t('pilot.retention') : key === 'ai_data_notice' ? t('work.aiHandling')
    : key === 'account_support_notice' ? t('work.supportHandling') : t(['phone', 'email'].includes(key) ? `work.${key}` : `pilot.${key}`)
  const fieldIssue = (scope, field, resourceKey = '') => issues.find(issue => issue.scope === scope && issue.field === field && issue.resourceKey === resourceKey)
  const messageFor = issue => t(`ui.organization.errors.${issue.messageKey}`, issue.values || {})
  const inputAttributes = (scope, field, resourceKey = '') => {
    const id = directoryFieldId(scope, field, resourceKey)
    const descriptions = [fieldIssue(scope, field, resourceKey) && `${id}-error`,
      scope === 'resource' && ['audience', 'cost_note', 'application_steps', 'visiting_note'].includes(field) && `${id}-hint`].filter(Boolean)
    return { id, 'aria-invalid': fieldIssue(scope, field, resourceKey) ? true : undefined,
      'aria-describedby': descriptions.join(' ') || undefined }
  }
  const inlineError = (scope, field, resourceKey = '') => {
    const issue = fieldIssue(scope, field, resourceKey)
    return issue && <span className="field-error" id={`${directoryFieldId(scope, field, resourceKey)}-error`}>{messageFor(issue)}</span>
  }
  const renderResourceField = key => <label key={key} htmlFor={directoryFieldId('resource', key, resource.resource_key)}>
    {labelFor(key)}<span className="field-badge">{t(['name', 'url'].includes(key) ? 'ui.organization.requiredForPublish' : 'ui.organization.optional')}</span>
    {['description', 'cost_note', 'pause_notice', 'application_steps', 'visiting_note', 'preparation', 'fallback_contact'].includes(key) ? <textarea {...inputAttributes('resource', key, resource.resource_key)} rows={3}
      maxLength={resourceLimits[key]} value={resource[key] || ''} onChange={event => updateResource(key, event.target.value)} />
      : <input {...inputAttributes('resource', key, resource.resource_key)}
        type={['checked_on', 'review_due_on'].includes(key) ? 'date' : ['url', 'booking_url'].includes(key) ? 'url' : key === 'phone' ? 'tel' : 'text'}
        max={key === 'checked_on' ? japanDay() : undefined} value={resource[key] || ''} maxLength={resourceLimits[key]}
        onChange={event => updateResource(key, ['checked_on', 'review_due_on', 'booking_url'].includes(key) ? event.target.value || null : event.target.value)} />}
    {inlineError('resource', key, resource.resource_key)}
    {['audience', 'cost_note', 'application_steps', 'visiting_note'].includes(key) && <span className="field-hint" id={`${directoryFieldId('resource', key, resource.resource_key)}-hint`}>
      {t(`localCare.organization.fieldHints.${key}`)}</span>}
  </label>
  const renderServiceStatus = () => <label htmlFor={directoryFieldId('resource', 'service_status', resource.resource_key)}>
    {t('flows.directory.service_status')}<select {...inputAttributes('resource', 'service_status', resource.resource_key)}
      value={resource.service_status || 'active'} onChange={event => updateResource('service_status', event.target.value)}>
      {['active', 'paused'].map(value => <option key={value} value={value}>{t(`flows.directory.statuses.${value}`)}</option>)}
    </select>{inlineError('resource', 'service_status', resource.resource_key)}
  </label>

  return <main className="pilot-shell organization-portal">
    <div className="pilot-topbar"><strong>{t('pilot.organizationTitle')}</strong><LanguageSelector /></div>
    <h1>{t('pilot.organizationHeading')}</h1><p>{t('pilot.organizationScope')}</p>
    <ConnectionNotice />
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
      <section className="pilot-panel review-queue"><h2>{t('friendly.organization.tasks')}</h2>
        <div className="maintenance-summary">
          <span>{t('friendly.organization.reviewCount', { count: due.length })}</span>
          <span>{t('friendly.organization.changedCount', { count: changedContacts.size })}</span>
          <span>{t('friendly.organization.pausedCount', { count: profile.resources.filter(item => item.service_status === 'paused').length })}</span>
        </div><p>{t('polish.maintenanceNotice')}</p>
        <details><summary>{t('friendly.organization.reviewTasks')}</summary>
        {due.length ? <ul>{due.map(({ resource: item, issues }) => <li key={item.resource_key}>
          <button type="button" disabled={editingBlocked} onClick={() => focusField(directoryFieldId('resource', issues[0] === 'contact' ? 'phone' : issues[0], item.resource_key), item.resource_key)}>{item.name || t('work.unnamedResource')}</button>
          <span> · {item.maintainer || t('polish.noMaintainer')} · {item.review_due_on || t('polish.noReviewDate')}</span>
          <p>{issues.map(key => ['maintainer', 'review_due_on'].includes(key) ? t(`polish.${key}`)
            : ['name', 'url'].includes(key) ? t(`pilot.resource.${key}`) : t(`work.reviewIssues.${key}`)).join(' / ')}</p>
        </li>)}</ul> : <p>{t('work.noReviewDue')}</p>}
        </details>
      </section>
      <form className="pilot-panel pilot-form directory-editor" noValidate onSubmit={event => {
        event.preventDefault()
        if (editingBlocked || !previewed) return
        const next = validate(true)
        if (next) perform('/api/pilot/organization', { profile: next, revision }, 'saved')
      }}>
        <h2>{t('pilot.directoryEditor')}</h2><p>{t('pilot.publicFields')}</p>
        {publicationComplete && <section id="directory-publication-result" className="publication-result" tabIndex={-1}
          role="region" aria-labelledby="directory-publication-result-title">
          <h3 id="directory-publication-result-title">{t('ui.organization.publicationComplete')}</h3>
          <p>{t('ui.organization.publicationCompleteNotice')}</p>
          <button type="button" className="pilot-button secondary" disabled={editingBlocked}
            onClick={() => focusField('directory-published-heading')}>{t('ui.organization.currentPublished')}</button>
        </section>}
        <div className="directory-action-bar" aria-label={t('ui.organization.actions')}>
          <div className="pilot-actions">
            <button type="button" className="pilot-button secondary" disabled={editingBlocked} onClick={() => {
              const next = validate(false)
              if (next) perform('/api/pilot/organization/draft', { profile: next, revision }, 'draftSaved')
            }}>{t('ui.organization.saveDraft')}</button>
            <button type="button" className="pilot-button secondary" disabled={editingBlocked} onClick={() => {
              const next = validate(true)
              if (next) { setPreviewed(true); focusField('directory-preview-heading') }
            }}>{t('ui.organization.preview')}</button>
            <button type="submit" className="pilot-button" disabled={editingBlocked || !previewed}>{t(busy ? 'settings.saving' : 'ui.organization.publish')}</button>
          </div>
        </div>
        <p role="status">{t(reloading ? 'common.loading' : busy ? 'settings.saving' : dirty ? 'polish.localDraftUnsaved'
          : unpublished ? 'polish.serverDraftOnly' : status === 'saved' ? 'pilot.saved' : 'ui.organization.upToDate')}</p>
        {!previewed && <p className="field-hint">{t('ui.organization.previewFirst')}</p>}
        {(error || issues.length > 0) && <section className="validation-summary" id="directory-errors" tabIndex={-1} role="alert">
          <h3>{t('ui.organization.checkFields')}</h3>
          {error && <p>{error}</p>}
          {issues.length > 0 && <ul>{issues.map((issue, index) => <li key={`${issue.resourceKey}:${issue.field}:${index}`}>
            <button type="button" disabled={editingBlocked} onClick={() => focusIssue(issue)}>
              {issue.scope === 'resource' ? `${profile.resources.find(item => item.resource_key === issue.resourceKey)?.name || t('work.unnamedResource')} · ${labelFor(issue.field)}` : businessLabel(issue.field)}: {messageFor(issue)}
            </button>
          </li>)}</ul>}
          {error && <button type="button" className="pilot-button secondary" disabled={editingBlocked} onClick={reload}>{t('polish.reloadServerDraft')}</button>}
        </section>}
        <details className="editor-group"><summary>{t('work.businessInfo')}</summary><fieldset disabled={editingBlocked}>
          <legend>{t('work.businessInfo')}</legend>
          {['name', 'municipality', 'contact', 'hours', 'phone', 'email'].map(key => <label key={key} htmlFor={directoryFieldId('business', key)}>
            {businessLabel(key)}<span className="field-badge">{t(key === 'name' ? 'ui.organization.requiredForPublish' : 'ui.organization.optional')}</span>
            <input {...inputAttributes('business', key)} type={key === 'email' ? 'email' : key === 'phone' ? 'tel' : 'text'} value={profile[key] || ''}
              maxLength={businessLimits[key]} onChange={event => updateBusiness(key, event.target.value)} />
            {inlineError('business', key)}
          </label>)}
          {['retention_notice', 'ai_data_notice', 'account_support_notice'].map(key => <label key={key} htmlFor={directoryFieldId('business', key)}>
            {businessLabel(key)}<textarea {...inputAttributes('business', key)} value={profile[key] || ''} rows={3}
              maxLength={businessLimits[key]} onChange={event => updateBusiness(key, event.target.value)} />
            {inlineError('business', key)}
          </label>)}<p>{t('work.operatorCheckNotice')}</p>
        </fieldset></details>
        <h3 id="directory-contacts" tabIndex={-1}>{t('pilot.localResources')}</h3><p>{t('work.templateNotice')}</p>
        <p className="field-hint">{t('ui.organization.normalizationNotice')}</p>
        <div className="pilot-actions">{['postpartum', 'parenting', 'feeding'].map(category => <button key={category} type="button"
          className="pilot-button secondary" disabled={editingBlocked || profile.resources.length >= 10} onClick={() => addResource(category)}>{t(`polish.purposes.${category}`)}</button>)}</div>
        <label>{t('flows.directory.filterMaintainer')}<select value={maintainerFilter} disabled={editingBlocked} onChange={event => setMaintainerFilter(event.target.value)}>
          <option value="">{t('flows.directory.allMaintainers')}</option><option value="unassigned">{t('polish.noMaintainer')}</option>
          {maintainers.map(name => <option key={name} value={`name:${name}`}>{name}</option>)}
        </select></label>
        {visibleResources.length === 0 && <p>{t('flows.directory.noMatches')}</p>}
        <ul className="contact-editor-list">{visibleResources.map(item => <li key={item.resource_key}>
          <div className="contact-list-info">
          <button type="button" disabled={editingBlocked} aria-pressed={selected === item.resource_key} onClick={() => focusField('directory-contact-heading', item.resource_key)}>{item.name || t('work.unnamedResource')}</button>
          <span>{item.maintainer || t('polish.noMaintainer')} · {item.review_due_on || t('polish.noReviewDate')}</span>
          <div className="contact-task-badges">
            {dueContacts.has(item.resource_key) && <span>{t('friendly.organization.needsReview')}</span>}
            {changedContacts.has(item.resource_key) && <span>{t('friendly.organization.unpublished')}</span>}
            {item.service_status === 'paused' && <span>{t('friendly.organization.draftPaused')}</span>}
            {published?.resources?.some(contact => contact.resource_key === item.resource_key && contact.service_status === 'paused')
              && <span>{t('friendly.organization.publishedPaused')}</span>}
          </div>
          {issues.some(issue => issue.resourceKey === item.resource_key) && <span className="field-error">{t('ui.organization.needsCorrection')}</span>}
          </div><div className="contact-task-actions">
            <button type="button" className="pilot-button secondary" disabled={editingBlocked}
              aria-label={`${item.name || t('work.unnamedResource')}: ${t('friendly.organization.phone')}`}
              onClick={() => focusField(directoryFieldId('resource', 'phone', item.resource_key), item.resource_key, null, 'phone')}>{t('friendly.organization.phone')}</button>
            <button type="button" className="pilot-button secondary" disabled={editingBlocked}
              aria-label={`${item.name || t('work.unnamedResource')}: ${t('friendly.organization.status')}`}
              onClick={() => focusField(directoryFieldId('resource', 'service_status', item.resource_key), item.resource_key, null, 'status')}>{t('friendly.organization.status')}</button>
          </div>
        </li>)}</ul>
        {resource && <section key={resource.resource_key} className="contact-editor" aria-labelledby="directory-contact-heading">
          <h3 id="directory-contact-heading" tabIndex={-1}>{t('polish.editContact')}: {resource.name || t('work.unnamedResource')}</h3>
          <div className="editor-task-choices" role="group" aria-label={t('polish.editContact')}>
            {['all', 'phone', 'status'].map(task => <button type="button" className="pilot-button secondary" key={task}
              disabled={editingBlocked} aria-pressed={editorTask === task}
              onClick={() => focusField(task === 'all' ? 'directory-contact-heading' : directoryFieldId('resource', task === 'phone' ? 'phone' : 'service_status', resource.resource_key), resource.resource_key, null, task)}>{t(`friendly.organization.${task}`)}</button>)}
          </div><p className="field-hint">{t('friendly.organization.taskNotice')}</p>
          {editorTask === 'phone' && <fieldset disabled={editingBlocked}><legend>{t('friendly.organization.contactTask')}</legend>{renderResourceField('phone')}</fieldset>}
          {editorTask === 'status' && <fieldset disabled={editingBlocked}><legend>{t('friendly.organization.statusTask')}</legend>
            {renderServiceStatus()}{['pause_notice', 'fallback_contact'].map(renderResourceField)}
          </fieldset>}
          {editorTask === 'all' && <>
          <fieldset disabled={editingBlocked}><legend>{t('ui.organization.groups.basic')}</legend>
            <label htmlFor={directoryFieldId('resource', 'category', resource.resource_key)}>{t('polish.supportPurpose')}
              <select {...inputAttributes('resource', 'category', resource.resource_key)} value={resource.category || 'parenting'} onChange={event => updateResource('category', event.target.value)}>
                {['parenting', 'postpartum', 'feeding'].map(key => <option key={key} value={key}>{t(`polish.purposes.${key}`)}</option>)}
              </select>{inlineError('resource', 'category', resource.resource_key)}
            </label>
            {resourceGroups.basic.map(renderResourceField)}
            {renderServiceStatus()}
          </fieldset>
          {['details', 'review'].map(group => <details className="editor-group" key={group}><summary>{t(`ui.organization.groups.${group}`)}</summary>
            <fieldset disabled={editingBlocked}><legend>{t(`ui.organization.groups.${group}`)}</legend>{resourceGroups[group].map(renderResourceField)}</fieldset>
          </details>)}
          <button type="button" className="pilot-button secondary" disabled={editingBlocked} onClick={() => {
            if (actionBusy.current || reloadBusy.current || !window.confirm(t('polish.removeContactConfirm'))) return
            change(previous => ({ ...previous, resources: previous.resources.filter(item => item.resource_key !== selected) }))
            setIssues(previous => previous.filter(issue => issue.resourceKey !== selected)); setSelected(''); focusField('directory-contacts')
          }}>{t('common.delete')}</button>
          </>}
        </section>}
        {previewed && <section className="publication-preview"><h3 id="directory-preview-heading" tabIndex={-1}>{t('work.previewOnly')}</h3>
          <p>{t('ui.organization.previewNotice')}</p>
          <section className="publication-changes"><h4>{t('flows.directory.changes')}</h4>
            {changes.length === 0 ? <p>{t('flows.directory.noChanges')}</p> : <ul>{changes.map((item, index) => <li key={index}>
              <strong>{item.name || t('work.businessInfo')} · {t(`polish.publicationChanges.${item.kind}`)}{item.field ? ` · ${item.scope === 'business' ? businessLabel(item.field) : labelFor(item.field)}` : ''}</strong>
              {item.field && <div><del>{item.before || t('pilot.notProvided')}</del><span aria-hidden="true"> → </span><ins>{item.after || t('pilot.notProvided')}</ins></div>}
            </li>)}</ul>}
          </section><SupportDirectory previewProfile={profile} />
          <button type="submit" className="pilot-button" disabled={editingBlocked}>{t('ui.organization.publish')}</button>
        </section>}
      </form>
      <details className="pilot-panel publication-history"><summary>{t('polish.publicationHistory')}</summary><p>{t('polish.restorePublicationNotice')}</p>
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
      <details className="pilot-panel"><summary>{t('pilot.familyLink')}</summary>
        <input aria-label={t('pilot.familyLink')} readOnly value={familyLink} />
        <button type="button" className="pilot-button secondary" onClick={async () => {
          try { await navigator.clipboard.writeText(familyLink); setCopied(true) }
          catch { setError(t('pilot.copyFailed')); focusField('directory-errors') }
        }}>{t(copied ? 'pilot.copied' : 'pilot.copyLink')}</button>
        <FamilyHandout familyLink={familyLink} organizationName={published?.name} />
      </details>
      <details className="pilot-panel"><summary id="directory-published-heading">{t('ui.organization.currentPublished')}</summary><SupportDirectory previewProfile={published} /></details>
    </>}
  </main>
}
