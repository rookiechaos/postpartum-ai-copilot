import React, { useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import SupportDirectory from './SupportDirectory'
import './WelcomeScreen.css'

export default function WelcomeScreen({ onComplete, onExit }) {
  const { t } = useTranslation()
  const [step, setStep] = useState(0)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const savingRef = useRef(false)
  const [formData, setFormData] = useState({ babyAge: '', birthType: '', feedingType: '', babyName: '' })
  const complete = async (profile = formData, task = 'record') => {
    if (savingRef.current) return
    savingRef.current = true
    setSaving(true)
    setError('')
    try { await onComplete(profile, task) }
    catch { setError(t('pilot.saveFailed', 'Unable to save your settings. Please try again.')) }
    finally { savingRef.current = false; setSaving(false) }
  }
  return <div className="welcome-screen">
    <div className="welcome-container">
      <header className="welcome-header"><h1 id="welcome-title">{t(step === 0 ? 'welcome.title' : 'welcome.step2Title')}</h1>
        <p>{t(step === 0 ? 'pilot.shortWelcome' : 'pilot.optionalProfile')}</p></header>
      <div className="welcome-body">
        {step === 0 ? <>
          <ul className="welcome-benefits"><li>{t('pilot.familyBenefit1')}</li><li>{t('pilot.familyBenefit2')}</li><li>{t('pilot.familyBenefit3')}</li></ul>
          <p>{t('pilot.entryPrivacy')}</p><p>{t('pilot.chatBoundary')}</p>
          <p>{t('friendly.welcome.profileHint')}</p>
        </> : <fieldset className="form-content welcome-profile" disabled={saving} aria-labelledby="welcome-title">
          <label>{t('welcome.babyName')}<input maxLength={50} placeholder={t('pilot.nicknamePlaceholder')}
            value={formData.babyName} onChange={event => setFormData({ ...formData, babyName: event.target.value })} /></label>
          <label>{t('welcome.babyAge')}<select value={formData.babyAge} onChange={event => setFormData({ ...formData, babyAge: event.target.value })}>
            <option value="">{t('pilot.skipProfileField')}</option>
            {['0-7', '1-2', '2-4', '1-2m', '2-3m', '3+'].map(value => <option key={value} value={value}>{t(`pilot.ages.${value}`)}</option>)}
          </select></label>
          <label>{t('welcome.birthType')}<select value={formData.birthType} onChange={event => setFormData({ ...formData, birthType: event.target.value })}>
            <option value="">{t('pilot.skipProfileField')}</option>
            <option value="vaginal">{t('pilot.vaginal')}</option><option value="c-section">{t('pilot.csection')}</option>
          </select></label>
          <label>{t('welcome.feedingType')}<select value={formData.feedingType} onChange={event => setFormData({ ...formData, feedingType: event.target.value })}>
            <option value="">{t('pilot.skipProfileField')}</option>
            {['breast', 'formula', 'mixed'].map(value => <option key={value} value={value}>{t(`tracking.${value}`)}</option>)}
          </select></label>
        </fieldset>}
      </div>
      <footer className="welcome-footer">
        {onExit && <button className="btn-link" disabled={saving} onClick={onExit}>{t('pilot.switchEntrance')}</button>}
        {error && <p role="alert">{error}</p>}
        <div className="welcome-actions">
          {step > 0 && <button className="btn-secondary" disabled={saving} onClick={() => setStep(0)}>{t('welcome.back')}</button>}
          <button className="btn-primary" disabled={saving} onClick={step === 0 ? () => complete({}) : () => complete()}>
            {saving ? t('settings.saving') : t('friendly.welcome.start')}
          </button>
          {step === 0 && <>
            <button type="button" className="btn-secondary" disabled={saving} onClick={() => complete({}, 'family')}>{t('continuity.onboarding.family')}</button>
            <button type="button" className="btn-secondary" disabled={saving} onClick={() => complete({}, 'support')}>{t('continuity.onboarding.support')}</button>
          </>}
          {step === 0 ? <button className="btn-link" disabled={saving} onClick={() => setStep(1)}>{t('friendly.welcome.profile')}</button>
            : <button className="btn-link" disabled={saving} onClick={() => complete({})}>{t('friendly.welcome.withoutProfile')}</button>}
        </div>
      </footer>
      <SupportDirectory compact />
    </div>
  </div>
}
