import React, { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../utils/api'
import { Save, User, Baby, Shield, HelpCircle, Eye } from 'lucide-react'
import { useToast } from './Toast'
import PrivacyCenter from './PrivacyCenter'
import FamilyHelp from './FamilyHelp'
import NotificationManager from './NotificationManager'
import AccessibilitySettings from './AccessibilitySettings'
import SecuritySettings from './SecuritySettings'
import LanguageSelector from './LanguageSelector'
import { InstallInstructions } from './InstallPrompt'
import { Button, ErrorMessage, FormField, PageHeader } from './ui'
import './Settings.css'

function Settings({ userId, onContextUpdate, onLogout, onFindHelp, onSwitchEntrance }) {
  const { t, i18n } = useTranslation()
  const displayLanguage = (i18n.resolvedLanguage || i18n.language || 'ja').split('-')[0]
  const [settings, setSettings] = useState({
    babyName: '',
    babyAge: '',
    birthType: '',
    feedingType: ''
  })
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [saveError, setSaveError] = useState(false)
  const [loadState, setLoadState] = useState('loading')
  const [loadAttempt, setLoadAttempt] = useState(0)
  const [activeSubTab, setActiveSubTab] = useState('profile')
  const toast = useToast()

  useEffect(() => {
    let active = true
    const loadSettings = async () => {
      setLoadState('loading')
      setSaved(false)
      setSaveError(false)
      try {
        const context = await api.getUserContext(userId)
        if (!active) return
        setSettings({
          babyName: context.babyName || '',
          babyAge: context.babyAge || '',
          birthType: context.birthType || '',
          feedingType: context.feedingType || ''
        })
        setLoadState('ready')
      } catch (error) {
        if (active) {
          console.error('Error loading settings:', error)
          setLoadState('error')
        }
      }
    }
    loadSettings()
    return () => { active = false }
  }, [userId, loadAttempt])

  useEffect(() => { setSaved(false) }, [displayLanguage])

  const handleSave = async () => {
    if (loadState !== 'ready' || saving) return
    setSaving(true)
    setSaved(false)
    setSaveError(false)
    try {
      const savedContext = await api.updateUserContext(userId, {
        babyName: settings.babyName,
        babyAge: settings.babyAge,
        birthType: settings.birthType,
        feedingType: settings.feedingType,
        // The display choice is shared with the header. Only this explicit save
        // writes it to the account; loading a profile never changes the UI language.
        language: displayLanguage
      })
      setSaved((i18n.resolvedLanguage || i18n.language || 'ja').split('-')[0] === displayLanguage)
      if (onContextUpdate) {
        onContextUpdate(savedContext.context)
      }
      toast.success(i18n.t('settings.saved'))
      setTimeout(() => setSaved(false), 3000)
    } catch (error) {
      console.error('Error saving settings:', error)
      setSaveError(true)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="settings">
      <PageHeader title={t('settings.title')} description={t('settings.subtitle')} />

      <div className="settings-tabs">
        <button
          className={activeSubTab === 'profile' ? 'active' : ''}
          onClick={() => setActiveSubTab('profile')}
        >
          <User size={18} />
          {t('settings.profile')}
        </button>
        <button
          className={activeSubTab === 'export' ? 'active' : ''}
          onClick={() => setActiveSubTab('export')}
        >
          <Shield size={18} />
          {t('work.dataPrivacy')}
        </button>
        <button
          className={activeSubTab === 'help' ? 'active' : ''}
          onClick={() => setActiveSubTab('help')}
        >
          <HelpCircle size={18} />
          {t('settings.help')}
        </button>
        <button
          className={activeSubTab === 'accessibility' ? 'active' : ''}
          onClick={() => setActiveSubTab('accessibility')}
        >
          <Eye size={18} />
          {t('accessibility.title')}
        </button>
      </div>

      {activeSubTab === 'profile' && (
      <>
      {loadState === 'loading' && <p role="status">{t('common.loading')}</p>}
      {loadState === 'error' && <ErrorMessage title={t('pilot.loadFailed')} onRetry={() => setLoadAttempt(value => value + 1)} />}
      <fieldset className="settings-sections" disabled={loadState !== 'ready' || saving}>
        <div className="settings-section">
          <div className="section-header">
            <User size={20} />
            <h3>{t('settings.profile')}</h3>
          </div>
          <div className="section-content">
            <FormField label={t('settings.babyName')} optional
              id="settings-baby-name"
              type="text"
              value={settings.babyName}
              onChange={(e) => setSettings({ ...settings, babyName: e.target.value })}
              placeholder={t('settings.babyNamePlaceholder')} />
            <div className="form-group">
              <label htmlFor="settings-language">{t('settings.language')}</label>
              <LanguageSelector id="settings-language" />
              <p className="field-hint">{t('ui.account.languageNotice')}</p>
            </div>
          </div>
        </div>

        <div className="settings-section">
          <div className="section-header">
            <Baby size={20} />
            <h3>{t('settings.babyInfo')}</h3>
          </div>
          <div className="section-content">
            <FormField as="select" label={t('settings.babyAge')} optional
              id="settings-baby-age"
              value={settings.babyAge}
              onChange={(e) => setSettings({ ...settings, babyAge: e.target.value })}
            >
              <option value="">{t('common.select')}</option>
              {['0-7', '1-2', '2-4', '1-2m', '2-3m', '3+'].map(value => <option key={value} value={value}>{t(`pilot.ages.${value}`)}</option>)}
            </FormField>
            <FormField as="select" label={t('settings.birthType')} optional
              id="settings-birth-type"
              value={settings.birthType}
              onChange={(e) => setSettings({ ...settings, birthType: e.target.value })}
            >
              <option value="">{t('common.select')}</option>
              <option value="vaginal">{t('pilot.vaginal')}</option>
              <option value="c-section">{t('pilot.csection')}</option>
            </FormField>
            <FormField as="select" label={t('settings.feedingType')} optional
              id="settings-feeding-type"
              value={settings.feedingType}
              onChange={(e) => setSettings({ ...settings, feedingType: e.target.value })}
            >
              <option value="">{t('common.select')}</option>
              {['breast', 'formula', 'mixed'].map(value => <option key={value} value={value}>{t(`tracking.${value}`)}</option>)}
            </FormField>
          </div>
        </div>

        <div className="settings-section">
          <div className="section-header">
            <Shield size={20} />
            <h3>{t('settings.privacy')}</h3>
          </div>
          <div className="section-content">
            <p className="safety-note">
              {t('settings.privacyNote')}
            </p>
          </div>
        </div>
      </fieldset>

      {saveError && <ErrorMessage title={t('pilot.saveFailed')} onRetry={handleSave} retryDisabled={saving || loadState !== 'ready'} />}
      <div className="settings-footer">
        <Button
          busy={saving} busyLabel={t('settings.saving')}
          onClick={handleSave}
          disabled={loadState !== 'ready' || saving}
        >
          <Save size={20} />
          {saving ? t('settings.saving') : saved ? t('settings.saved') : t('settings.save')}
        </Button>
      </div>
      </>
      )}

      {activeSubTab === 'export' && <PrivacyCenter userId={userId} />}
      {activeSubTab === 'help' && <><FamilyHelp onPrivacy={() => setActiveSubTab('export')} onFindHelp={onFindHelp} /><InstallInstructions /></>}
      {activeSubTab === 'accessibility' && <><AccessibilitySettings />
        <details className="pilot-panel"><summary>{t('settings.notifications')}</summary><NotificationManager userId={userId} /></details></>}
      {activeSubTab === 'profile' && <details className="pilot-panel"><summary>{t('settings.security')}</summary><SecuritySettings userId={userId} /></details>}
      <div className="pilot-panel settings-account-actions">
        <h3>{t('ui.account.actions')}</h3>
        <div className="pilot-actions">
          {onSwitchEntrance && <button type="button" className="pilot-button secondary" onClick={onSwitchEntrance}>{t('pilot.switchEntrance')}</button>}
          {onLogout && <button type="button" className="pilot-button secondary" onClick={onLogout}>{t('settings.logout')}</button>}
        </div>
      </div>
    </div>
  )
}

export default Settings

