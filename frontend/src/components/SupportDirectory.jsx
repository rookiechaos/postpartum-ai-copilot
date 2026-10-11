import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../utils/api'

// National sources remain available when the API or model is unavailable.
export default function SupportDirectory({ compact = false }) {
  const { t } = useTranslation()
  const [profile, setProfile] = useState(null)
  const [unavailable, setUnavailable] = useState(false)
  useEffect(() => {
    let active = true
    api.get('/api/pilot').then(result => {
      if (active) setProfile(result.profile)
    }).catch(() => { if (active) setUnavailable(true) })
    return () => { active = false }
  }, [])

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
      </div>
      {!compact && <>
        <h3>{t('pilot.localSupport')}</h3>
        {unavailable && <p role="status">{t('pilot.directoryUnavailable')}</p>}
        {!unavailable && !profile && <p role="status">{t('common.loading')}</p>}
        {profile && !profile.name && <p>{t('pilot.noLocalSupport')}</p>}
        {profile?.name && <article className="support-card">
          <h3>{profile.name}</h3>
          <p>{profile.municipality}</p>
          <p>{t('pilot.contact')}: {profile.contact || t('pilot.notProvided')}</p>
          <p>{t('pilot.hours')}: {profile.hours || t('pilot.notProvided')}</p>
          <p>{t('pilot.noMonitoring')}</p>
          <p>{t('pilot.retention')}: {profile.retention_notice || t('pilot.retentionUnknown')}</p>
        </article>}
        {profile?.resources?.map((resource, index) => <article key={index} className="support-card">
          <a href={resource.url} target="_blank" rel="noreferrer">{resource.name}</a>
          <p>{resource.description}</p>
          <p>{t('pilot.hours')}: {resource.hours || t('pilot.checkSource')}</p>
          <small>{t('pilot.checkedOn')}: {resource.checked_on || t('pilot.notChecked')}</small>
        </article>)}
        <p className="pilot-note">{t('pilot.directoryNote')}</p>
      </>}
    </section>
  )
}
