import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../utils/api'
import LanguageSelector from './LanguageSelector'
import SupportDirectory from './SupportDirectory'

const emptyResource = () => ({ name: '', url: '', description: '', hours: '', checked_on: null })

export default function OrganizationPortal({ userId, onFamily, onExit }) {
  const { t } = useTranslation()
  const [profile, setProfile] = useState(null)
  const [status, setStatus] = useState('loading')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [copied, setCopied] = useState(false)
  const [directoryVersion, setDirectoryVersion] = useState(0)
  const familyLink = `${window.location.origin}/family`

  useEffect(() => {
    let active = true
    api.get('/api/pilot/organization').then(result => {
      if (active) { setProfile(result.profile); setStatus('ready') }
    }).catch(error => {
      if (active) setStatus(error.status === 403 ? 'denied' : 'failed')
    })
    return () => { active = false }
  }, [userId])

  const save = async event => {
    event.preventDefault()
    if (busy) return
    setBusy(true)
    setError('')
    setStatus('ready')
    try {
      const result = await api.post('/api/pilot/organization', profile)
      setProfile(result.profile)
      setStatus('saved')
      setDirectoryVersion(value => value + 1)
    } catch { setError(t('pilot.saveFailed')) }
    finally { setBusy(false) }
  }
  const updateResource = (index, key, value) => setProfile(previous => ({ ...previous,
    resources: previous.resources.map((resource, i) => i === index ? { ...resource, [key]: value } : resource),
  }))

  return (
    <main className="pilot-shell organization-portal">
      <div className="pilot-topbar"><strong>{t('pilot.organizationTitle')}</strong><LanguageSelector /></div>
      <h1>{t('pilot.organizationHeading')}</h1>
      <p>{t('pilot.organizationScope')}</p>
      <div className="pilot-actions">
        <button className="pilot-button secondary" onClick={onFamily}>{t('pilot.openFamily')}</button>
        <button className="pilot-button secondary" onClick={onExit}>{t('pilot.switchEntrance')}</button>
        <button className="pilot-button secondary" onClick={() => api.logout()}>{t('settings.logout')}</button>
      </div>
      {status === 'loading' && <p role="status">{t('common.loading')}</p>}
      {status === 'denied' && <section className="pilot-panel" role="status">
        <h2>{t('pilot.accessNeeded')}</h2>
        <p>{t('pilot.accessInstructions')}</p>
        <label>{t('pilot.accountId')}<input readOnly value={userId} /></label>
      </section>}
      {status === 'failed' && <p role="alert">{t('pilot.loadFailed')}</p>}
      {profile && <>
        <section className="pilot-panel">
          <h2>{t('pilot.familyLink')}</h2>
          <p>{t('pilot.familyLinkDescription')}</p>
          <input aria-label={t('pilot.familyLink')} readOnly value={familyLink} />
          <button className="pilot-button secondary" onClick={async () => {
            try { await navigator.clipboard.writeText(familyLink); setCopied(true) }
            catch { setError(t('pilot.copyFailed')) }
          }}>{copied ? t('pilot.copied') : t('pilot.copyLink')}</button>
        </section>
        <form className="pilot-panel pilot-form" onSubmit={save}>
          <h2>{t('pilot.directoryEditor')}</h2>
          <p>{t('pilot.publicFields')}</p>
          {['name', 'municipality', 'contact', 'hours'].map(key => <label key={key}>
            {t(`pilot.${key}`)}<input disabled={busy} value={profile[key]} maxLength={key === 'name' || key === 'municipality' ? 100 : 200}
              onChange={event => setProfile({ ...profile, [key]: event.target.value })} />
          </label>)}
          <label>{t('pilot.retention')}<textarea disabled={busy} value={profile.retention_notice} maxLength={1000}
            onChange={event => setProfile({ ...profile, retention_notice: event.target.value })} /></label>
          <p>{t('pilot.retentionHelp')}</p>
          <h3>{t('pilot.localResources')}</h3>
          {profile.resources.map((resource, index) => <fieldset key={index} disabled={busy}>
            <legend>{t('pilot.resourceNumber', { number: index + 1 })}</legend>
            {['name', 'url', 'description', 'hours', 'checked_on'].map(key => <label key={key}>
              {t(`pilot.resource.${key}`)}
              <input type={key === 'checked_on' ? 'date' : key === 'url' ? 'url' : 'text'}
                required={key === 'name' || key === 'url'} value={resource[key] || ''}
                maxLength={key === 'name' ? 100 : key === 'hours' ? 200 : 500}
                onChange={event => updateResource(index, key, key === 'checked_on' ? event.target.value || null : event.target.value)} />
            </label>)}
            <button type="button" className="pilot-button secondary" onClick={() => setProfile({ ...profile,
              resources: profile.resources.filter((_, i) => i !== index),
            })}>{t('common.delete')}</button>
          </fieldset>)}
          <button type="button" className="pilot-button secondary" disabled={busy || profile.resources.length >= 10}
            onClick={() => setProfile({ ...profile, resources: [...profile.resources, emptyResource()] })}>{t('pilot.addResource')}</button>
          <p>{t('pilot.sourceReviewReminder')}</p>
          {error && <p role="alert">{error}</p>}
          {status === 'saved' && <p role="status">{t('pilot.saved')}</p>}
          <button className="pilot-button" disabled={busy}>{busy ? t('settings.saving') : t('pilot.publishDirectory')}</button>
        </form>
      </>}
      <SupportDirectory key={directoryVersion} />
    </main>
  )
}
