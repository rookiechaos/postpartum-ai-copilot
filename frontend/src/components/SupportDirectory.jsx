import React, { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../utils/api'
import { needsReview, phoneHref, publicHttps } from '../utils/publicDirectory'
import { revealElement } from '../utils/focusView'
import SupportProgress, { useSupportJourneys } from './SupportProgress'

// National sources remain available when the API or model is unavailable.
export default function SupportDirectory({ compact = false, previewProfile, visible = true, onPrepareSheet, userId }) {
  const { t } = useTranslation()
  const [profile, setProfile] = useState(null)
  const [unavailable, setUnavailable] = useState(false)
  const [directoryAttempt, setDirectoryAttempt] = useState(0)
  const [purpose, setPurpose] = useState('all')
  const [script, setScript] = useState('')
  const [scriptError, setScriptError] = useState('')
  const [scriptTarget, setScriptTarget] = useState('')
  const [scriptRequest, setScriptRequest] = useState(0)
  const scriptHeading = useRef(null)
  const pendingScriptFocus = useRef(false)
  const progress = useSupportJourneys(userId, visible && !compact && !previewProfile)
  const progressEnabled = Boolean(userId && !compact && !previewProfile)
  const progressFor = (key, name, archived = false) => <SupportProgress key={key} contactKey={key} contactName={name}
    row={progress.rows.find(row => row.contact_key === key)} progress={progress} archived={archived} />
  useEffect(() => {
    if (visible && pendingScriptFocus.current && scriptTarget) {
      pendingScriptFocus.current = false; revealElement(scriptHeading.current)
    }
  }, [scriptRequest, scriptTarget, visible])
  useEffect(() => {
    if (previewProfile || !visible) return
    let active = true
    setUnavailable(false)
    api.get('/api/pilot').then(result => {
      if (active) setProfile(result.profile)
    }).catch(() => { if (active) setUnavailable(true) })
    return () => { active = false }
  }, [previewProfile, visible, directoryAttempt])
  const shownProfile = previewProfile || profile
  const retainedContacts = new Map(progress.rows.filter(row => !row.cleared).map(row => [row.contact_key, row]))
  Object.entries(progress.editors).forEach(([key, editor]) => {
    if (editor.edited || editor.busy) retainedContacts.set(key, { contact_key: key, contact_name: editor.contact_name })
  })
  const archived = [...retainedContacts.values()].filter(row => row.contact_key === 'organization'
    ? !shownProfile?.name : !shownProfile?.resources?.some(resource => resource.resource_key === row.contact_key))
  const hasArchivedDrafts = archived.some(row => progress.editors[row.contact_key]?.edited)
  const prepareCall = name => {
    if (script && name !== scriptTarget && !window.confirm(t('polish.replaceCallScript'))) return
    if (!script || name !== scriptTarget) setScript(t('polish.callScriptTemplate', { name }))
    setScriptTarget(name); setScriptError(''); pendingScriptFocus.current = true; setScriptRequest(value => value + 1)
  }
  const childAdvice = <article className="support-card">
    <h3>{t('pilot.childAdvice')}</h3><p>{t('pilot.childAdviceDescription')}</p>
    <a href="tel:%238000" className="pilot-button secondary">#8000</a>
    <a href="https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/newpage_55223.html" target="_blank" rel="noreferrer">{t('pilot.checkHours')}</a>
  </article>

  return (
    <section className={`support-directory ${compact ? 'compact' : ''}`} aria-label={t('pilot.supportTitle')}>
      <h2>{t('pilot.supportTitle')}</h2>
      <p>{t('pilot.supportIntro')}</p>
      <div className={compact ? 'support-cards' : 'support-urgent-bar'} aria-label={t('friendly.support.urgent')}>
        <article className="support-card urgent">
          <h3>{t('pilot.emergencyTitle')}</h3>
          <p>{t('pilot.emergencyDescription')}</p>
          <a href="tel:119" className="pilot-button">{t('pilot.call119')}</a>
        </article>
        {compact && childAdvice}
      </div>
      {!compact && <>
        <details className="national-support"><summary>{t('friendly.support.national')}</summary><div className="support-cards">
          {childAdvice}
          <article className="support-card"><h3>{t('pilot.ambulanceAdvice')}</h3><p>{t('pilot.ambulanceAdviceDescription')}</p>
            <a href="https://www.fdma.go.jp/mission/enrichment/appropriate/appropriate007.html" target="_blank" rel="noreferrer">{t('pilot.checkCoverage')}</a>
          </article>
          <article className="support-card"><h3>{t('work.communitySupport')}</h3><p>{t('work.communitySupportDescription')}</p>
            <a href="https://www.cfa.go.jp/policies/kosodateshien/sodankikan" target="_blank" rel="noreferrer">{t('work.communitySupportLink')}</a>
          </article>
        </div></details>
        <h3>{t('pilot.localSupport')}</h3>
        <fieldset className="support-purpose"><legend>{t('friendly.support.purpose')}</legend><div className="purpose-choices">
          {['all', 'parenting', 'postpartum', 'feeding'].map(key => <button type="button" key={key} className="pilot-button secondary"
            aria-pressed={purpose === key} onClick={() => setPurpose(key)}>{t(`localCare.support.needs.${key}`)}</button>)}
        </div></fieldset>
        <p className="field-hint">{t(purpose === 'all' ? 'localCare.support.purposeNotice' : 'localCare.support.matchedCategory',
          { category: t(`polish.purposes.${purpose}`) })}</p>
        {unavailable && <p role="status">{t(shownProfile ? 'flows.directory.stale' : 'pilot.directoryUnavailable')}
          <button type="button" className="text-action" onClick={() => setDirectoryAttempt(value => value + 1)}>{t('friendly.support.reloadDirectory')}</button></p>}
        {!previewProfile && !unavailable && !profile && <p role="status">{t('common.loading')}</p>}
        {shownProfile && !shownProfile.name && <p>{t('pilot.noLocalSupport')}</p>}
        {shownProfile?.name && <article className="support-card local-support-card">
          <h3>{shownProfile.name}</h3>
          <p>{shownProfile.municipality}</p>
          <p>{t('pilot.hours')}: {shownProfile.hours || t('pilot.notProvided')}</p>
          {phoneHref(shownProfile.phone) && <a className="pilot-button" href={phoneHref(shownProfile.phone)}>{t('work.callContact')} · {shownProfile.phone}</a>}
          {shownProfile.email && <a href={`mailto:${encodeURIComponent(shownProfile.email)}`}>{t('work.emailContact')}</a>}
          <button type="button" className="text-action" onClick={() => prepareCall(shownProfile.name)}>{t('polish.prepareCall')}</button>
          <details className="service-details"><summary>{t('friendly.support.operatorDetails')}</summary>
          <p>{t('pilot.contact')}: {shownProfile.contact || t('pilot.notProvided')}</p>
          <p>{t('pilot.noMonitoring')}</p>
          <p>{t('pilot.retention')}: {shownProfile.retention_notice || t('pilot.retentionUnknown')}</p>
          {shownProfile.account_support_notice && <p>{shownProfile.account_support_notice}</p>}
          </details>
          {progressEnabled && progressFor('organization', shownProfile.name)}
        </article>}
        {shownProfile?.resources?.map((resource, index) => <article key={resource.resource_key || index} className="support-card local-support-card"
          hidden={purpose !== 'all' && (resource.category || 'parenting') !== purpose}>
          <h4>{publicHttps(resource.url) ? <a href={publicHttps(resource.url)} target="_blank" rel="noreferrer">{resource.name}</a> : resource.name}</h4>
          <p>{t('work.serviceArea')}: {resource.area || t('pilot.checkSource')}</p>
          <p>{t('pilot.hours')}: {resource.hours || t('pilot.checkSource')}</p>
          {resource.service_status === 'paused' && <p className="service-paused" role="note">{t('flows.directory.paused')}{resource.pause_notice ? `: ${resource.pause_notice}` : ''}</p>}
          {resource.service_status === 'paused' && resource.fallback_contact && <p className="preserve-lines"><strong>{t('flows.directory.fallback_contact')}: </strong>{resource.fallback_contact}</p>}
          <div className="service-actions">
            {phoneHref(resource.phone) && <a className="pilot-button" href={phoneHref(resource.phone)}>{t('work.callContact')} · {resource.phone}</a>}
            {resource.service_status !== 'paused' && publicHttps(resource.booking_url) && <a className={`pilot-button${phoneHref(resource.phone) ? ' secondary' : ''}`} href={publicHttps(resource.booking_url)} target="_blank" rel="noreferrer">{t('work.booking')}</a>}
            <button type="button" className="text-action" onClick={() => prepareCall(resource.name)}>{t('polish.prepareCall')}</button>
          </div>
          <small>{t('pilot.checkedOn')}: {resource.checked_on || t('pilot.notChecked')}</small>
          {needsReview(resource.checked_on) && <p className="review-due">{t('work.confirmDetails')}</p>}
          <details className="service-details"><summary>{t('localCare.support.conditions')}</summary>
            <p>{resource.description}</p>
            <p>{t('work.resourceFields.audience')}: {resource.audience?.trim() || t('localCare.support.unconfirmed')}</p>
            <p>{t('work.resourceFields.cost_note')}: {resource.cost_note?.trim() || t('localCare.support.unconfirmed')}</p>
            <section><h4>{t('flows.directory.application_steps')}</h4><p className="preserve-lines">{resource.application_steps?.trim() || t('localCare.support.unconfirmed')}</p></section>
            <section><h4>{t('localCare.support.visiting_note')}</h4><p className="preserve-lines">{resource.visiting_note?.trim() || t('localCare.support.unconfirmed')}</p></section>
            {['preparation', 'fallback_contact'].filter(field => field !== 'fallback_contact' || resource.service_status !== 'paused').map(field => resource[field] && <section key={field}>
              <h4>{t(`flows.directory.${field}`)}</h4><p className="preserve-lines">{resource[field]}</p>
            </section>)}
          </details>
          {progressEnabled && resource.resource_key && progressFor(resource.resource_key, resource.name)}
        </article>)}
        {progressEnabled && progress.error && <p role="alert">{t('flows.journey.loadError')} <button type="button" className="text-action" onClick={progress.reload}>{t('friendly.support.reloadAllProgress')}</button></p>}
        {progressEnabled && shownProfile && archived.length > 0 && <details>
          <summary>{t('flows.journey.archived')}{hasArchivedDrafts ? ` · ${t('flows.journey.unsaved')}` : ''}</summary><p>{t('flows.journey.archivedNotice')}</p>
          {hasArchivedDrafts && <p>{t('flows.journey.archivedDraftNotice')}</p>}
          {archived.map(row => <article key={row.contact_key}>
            <h4>{row.contact_name}</h4>{progressFor(row.contact_key, row.contact_name, true)}
          </article>)}
        </details>}
        {shownProfile && purpose !== 'all' && !shownProfile.resources?.some(resource => (resource.category || 'parenting') === purpose)
          && <p>{t('polish.noPurposeContacts')}</p>}
        {scriptTarget && <section className="pilot-panel call-script"><h3 ref={scriptHeading} tabIndex={-1}>{t('polish.callScriptTitle', { name: scriptTarget })}</h3>
          <p>{t('polish.callScriptNotice')}</p><textarea aria-label={t('polish.callScript')} rows={7} maxLength={1000}
            value={script} onChange={event => setScript(event.target.value)} />
          <button type="button" className="pilot-button secondary" onClick={async () => {
            try { await navigator.clipboard.writeText(script); setScriptError(t('pilot.copied')) }
            catch { setScriptError(t('pilot.copyFailed')) }
          }}>{t('polish.copyScript')}</button>
          {onPrepareSheet && <button type="button" className="pilot-button secondary" disabled={!script.trim()} onClick={() => onPrepareSheet(script)}>{t('polish.prepareSheetFromCall')}</button>}
          {scriptError && <p role="status">{scriptError}</p>}
        </section>}
        <p className="pilot-note">{t('pilot.directoryNote')}</p>
      </>}
    </section>
  )
}
