import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../utils/api'
import { needsReview, phoneHref, publicHttps } from '../utils/publicDirectory'

// National sources remain available when the API or model is unavailable.
export default function SupportDirectory({ compact = false, previewProfile, visible = true, onPrepareSheet }) {
  const { t } = useTranslation()
  const [profile, setProfile] = useState(null)
  const [unavailable, setUnavailable] = useState(false)
  const [purpose, setPurpose] = useState('all')
  const [script, setScript] = useState('')
  const [scriptError, setScriptError] = useState('')
  const [scriptTarget, setScriptTarget] = useState('')
  useEffect(() => {
    if (previewProfile || !visible) return
    let active = true
    setProfile(null); setUnavailable(false)
    api.get('/api/pilot').then(result => {
      if (active) setProfile(result.profile)
    }).catch(() => { if (active) setUnavailable(true) })
    return () => { active = false }
  }, [previewProfile, visible])
  const shownProfile = previewProfile || profile
  const prepareCall = name => {
    if (script && name !== scriptTarget && !window.confirm(t('polish.replaceCallScript'))) return
    if (!script || name !== scriptTarget) setScript(t('polish.callScriptTemplate', { name }))
    setScriptTarget(name); setScriptError('')
  }

  return (
    <section className={`support-directory ${compact ? 'compact' : ''}`} aria-label={t('pilot.supportTitle')}>
      <h2>{t('pilot.supportTitle')}</h2>
      <p>{t('pilot.supportIntro')}</p>
      <div className="support-cards">
        <article className="support-card urgent">
          <h3>{t('pilot.emergencyTitle')}</h3>
          <p>{t('pilot.emergencyDescription')}</p>
          <a href="tel:119" className="pilot-button">{t('pilot.call119')}</a>
        </article>
        <article className="support-card">
          <h3>{t('pilot.childAdvice')}</h3>
          <p>{t('pilot.childAdviceDescription')}</p>
          <a href="tel:%238000" className="pilot-button secondary">#8000</a>
          <a href="https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/newpage_55223.html" target="_blank" rel="noreferrer">{t('pilot.checkHours')}</a>
        </article>
        {!compact && <article className="support-card">
          <h3>{t('pilot.ambulanceAdvice')}</h3>
          <p>{t('pilot.ambulanceAdviceDescription')}</p>
          <a href="https://www.fdma.go.jp/mission/enrichment/appropriate/appropriate007.html" target="_blank" rel="noreferrer">{t('pilot.checkCoverage')}</a>
        </article>}
        {!compact && <article className="support-card">
          <h3>{t('work.communitySupport')}</h3><p>{t('work.communitySupportDescription')}</p>
          <a href="https://www.cfa.go.jp/policies/kosodateshien/sodankikan" target="_blank" rel="noreferrer">{t('work.communitySupportLink')}</a>
        </article>}
      </div>
      {!compact && <>
        <h3>{t('pilot.localSupport')}</h3>
        <label>{t('polish.supportPurpose')}<select value={purpose} onChange={event => setPurpose(event.target.value)}>
          {['all', 'parenting', 'postpartum', 'feeding'].map(key => <option key={key} value={key}>{t(`polish.purposes.${key}`)}</option>)}
        </select></label>
        {unavailable && <p role="status">{t('pilot.directoryUnavailable')}</p>}
        {!previewProfile && !unavailable && !profile && <p role="status">{t('common.loading')}</p>}
        {shownProfile && !shownProfile.name && <p>{t('pilot.noLocalSupport')}</p>}
        {shownProfile?.name && <article className="support-card">
          <h3>{shownProfile.name}</h3>
          <p>{shownProfile.municipality}</p>
          <p>{t('pilot.contact')}: {shownProfile.contact || t('pilot.notProvided')}</p>
          <p>{t('pilot.hours')}: {shownProfile.hours || t('pilot.notProvided')}</p>
          {phoneHref(shownProfile.phone) && <a className="pilot-button secondary" href={phoneHref(shownProfile.phone)}>{t('work.callContact')}</a>}
          {shownProfile.email && <a href={`mailto:${encodeURIComponent(shownProfile.email)}`}>{t('work.emailContact')}</a>}
          <button type="button" className="pilot-button secondary" onClick={() => prepareCall(shownProfile.name)}>{t('polish.prepareCall')}</button>
          <p>{t('pilot.noMonitoring')}</p>
          <p>{t('pilot.retention')}: {shownProfile.retention_notice || t('pilot.retentionUnknown')}</p>
          {shownProfile.account_support_notice && <p>{shownProfile.account_support_notice}</p>}
        </article>}
        {shownProfile?.resources?.filter(resource => purpose === 'all' || (resource.category || 'parenting') === purpose).map((resource, index) => <article key={resource.resource_key || index} className="support-card">
          {publicHttps(resource.url) ? <a href={publicHttps(resource.url)} target="_blank" rel="noreferrer">{resource.name}</a> : <h4>{resource.name}</h4>}
          <p>{resource.description}</p>
          <p>{t('work.serviceArea')}: {resource.area || t('pilot.checkSource')}</p>
          <p>{t('work.serviceAudience')}: {resource.audience || t('pilot.checkSource')}</p>
          <p>{t('pilot.hours')}: {resource.hours || t('pilot.checkSource')}</p>
          <p>{t('work.costNote')}: {resource.cost_note || t('pilot.checkSource')}</p>
          {phoneHref(resource.phone) && <a className="pilot-button secondary" href={phoneHref(resource.phone)}>{t('work.callContact')}</a>}
          {publicHttps(resource.booking_url) && <a className="pilot-button secondary" href={publicHttps(resource.booking_url)} target="_blank" rel="noreferrer">{t('work.booking')}</a>}
          <button type="button" className="pilot-button secondary" onClick={() => prepareCall(resource.name)}>{t('polish.prepareCall')}</button>
          <small>{t('pilot.checkedOn')}: {resource.checked_on || t('pilot.notChecked')}</small>
          {needsReview(resource.checked_on) && <p className="review-due">{t('work.confirmDetails')}</p>}
        </article>)}
        {shownProfile && purpose !== 'all' && !shownProfile.resources?.some(resource => (resource.category || 'parenting') === purpose)
          && <p>{t('polish.noPurposeContacts')}</p>}
        {script && <section className="pilot-panel call-script"><h3>{t('polish.callScriptTitle', { name: scriptTarget })}</h3>
          <p>{t('polish.callScriptNotice')}</p><textarea aria-label={t('polish.callScript')} rows={7} maxLength={1000}
            value={script} onChange={event => setScript(event.target.value)} />
          <button type="button" className="pilot-button secondary" onClick={async () => {
            try { await navigator.clipboard.writeText(script); setScriptError(t('pilot.copied')) }
            catch { setScriptError(t('pilot.copyFailed')) }
          }}>{t('polish.copyScript')}</button>
          {onPrepareSheet && <button type="button" className="pilot-button secondary" onClick={() => onPrepareSheet(script)}>{t('polish.prepareSheetFromCall')}</button>}
          {scriptError && <p role="status">{scriptError}</p>}
        </section>}
        <p className="pilot-note">{t('pilot.directoryNote')}</p>
      </>}
    </section>
  )
}
