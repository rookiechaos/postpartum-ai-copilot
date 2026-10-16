import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../utils/api'
import { phoneHref } from '../utils/publicDirectory'

// Only the published public directory supplies identity/contact information.
export default function OperatorInfo() {
  const { t } = useTranslation()
  const [profile, setProfile] = useState(null)
  const [status, setStatus] = useState('loading')
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    let active = true
    setStatus('loading'); setProfile(null)
    api.get('/api/pilot').then(result => {
      if (active) { setProfile(result.profile); setStatus('ready') }
    }).catch(() => { if (active) setStatus('failed') })
    return () => { active = false }
  }, [attempt])
  return <section className="operator-info" aria-label={t('localCare.operator.title')}>
    {status === 'loading' && <p role="status">{t('common.loading')}</p>}
    {status === 'failed' && <p role="status">{t('localCare.operator.loadError')}
      <button type="button" className="text-action" onClick={() => setAttempt(value => value + 1)}>{t('localCare.operator.reload')}</button></p>}
    {status === 'ready' && <>
      <p><strong>{t('localCare.operator.name')}</strong><span>{profile?.name || t('localCare.operator.unknown')}</span></p>
      <details><summary>{t('localCare.operator.details')}</summary>
        <dl><dt>{t('localCare.operator.contact')}</dt><dd>{profile?.contact || (!phoneHref(profile?.phone) && !profile?.email ? t('localCare.operator.notListed') : '')}
          {phoneHref(profile?.phone) && <a href={phoneHref(profile.phone)}>{profile.phone}</a>}
          {profile?.email && <a href={`mailto:${encodeURIComponent(profile.email)}`}>{profile.email}</a>}
        </dd><dt>{t('localCare.operator.hours')}</dt><dd>{profile?.hours || t('localCare.operator.notListed')}</dd></dl>
        <p>{t('localCare.operator.notice')}</p>
      </details>
    </>}
  </section>
}
