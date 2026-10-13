import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import api from '../utils/api'
import { Save, User, Baby, Shield, HelpCircle, Eye } from 'lucide-react'
import { useToast } from './Toast'
import PrivacyCenter from './PrivacyCenter'
import FamilyHelp from './FamilyHelp'
import NotificationManager from './NotificationManager'
import AccessibilitySettings from './AccessibilitySettings'
import SecuritySettings from './SecuritySettings'
import { InstallInstructions } from './InstallPrompt'
import './Settings.css'

function Settings({ userId, onContextUpdate, onLogout, onFindHelp }) {
  const { t, i18n } = useTranslation()
  const [settings, setSettings] = useState({
    babyName: '',
    babyAge: '',
    birthType: '',
    feedingType: '',
    language: i18n.language
  })
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [loadState, setLoadState] = useState('loading')
  const [loadAttempt, setLoadAttempt] = useState(0)
  const [activeSubTab, setActiveSubTab] = useState('profile')
  const toast = useToast()

  useEffect(() => {
    let active = true
    const loadSettings = async () => {
      setLoadState('loading')
      setSaved(false)
      try {
        const context = await api.getUserContext(userId)
        if (!active) return
        setSettings({
          babyName: context.babyName || '',
          babyAge: context.babyAge || '',
          birthType: context.birthType || '',
          feedingType: context.feedingType || '',
          language: context.language || i18n.language
        })
        if (context.language && context.language !== i18n.language) {
          i18n.changeLanguage(context.language)
        }
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

  const handleSave = async () => {
    if (loadState !== 'ready' || saving) return
    setSaving(true)
    try {
      // Update language if changed.
      if (settings.language !== i18n.language) {
        i18n.changeLanguage(settings.language)
        localStorage.setItem('preferred-language', settings.language)
      }
      
      const savedContext = await api.updateUserContext(userId, {
        babyName: settings.babyName,
        babyAge: settings.babyAge,
        birthType: settings.birthType,
        feedingType: settings.feedingType,
        language: settings.language
      })
      setSaved(true)
      if (onContextUpdate) {
        onContextUpdate(savedContext.context)
      }
      toast.success(t('settings.saved'))
      setTimeout(() => setSaved(false), 3000)
    } catch (error) {
      console.error('Error saving settings:', error)
      toast.error(t('common.error'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="settings">
      <div className="settings-header">
        <h2>{t('settings.title')}</h2>
        <p>{t('settings.subtitle')}</p>
      </div>

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
      {loadState === 'error' && <div role="alert"><p>{t('pilot.loadFailed')}</p>
        <button className="pilot-button secondary" onClick={() => setLoadAttempt(value => value + 1)}>{t('pilot.retry')}</button>
      </div>}
      <fieldset className="settings-sections" disabled={loadState !== 'ready' || saving}>
        <motion.div
          className="settings-section"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <div className="section-header">
            <User size={20} />
            <h3>{t('settings.profile')}</h3>
          </div>
          <div className="section-content">
            <div className="form-group">
              <label>{t('settings.babyName')}</label>
              <input
                type="text"
                value={settings.babyName}
                onChange={(e) => setSettings({ ...settings, babyName: e.target.value })}
                placeholder={t('settings.babyNamePlaceholder')} />
            </div>
            <div className="form-group">
              <label>{t('settings.language')}</label>
              <select
                value={settings.language}
                onChange={(e) => setSettings({ ...settings, language: e.target.value })}
              >
                <option value="en">🇺🇸 English</option>
                <option value="ja">🇯🇵 日本語</option>
              </select>
            </div>
          </div>
        </motion.div>

        <motion.div
          className="settings-section"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          <div className="section-header">
            <Baby size={20} />
            <h3>{t('settings.babyInfo')}</h3>
          </div>
          <div className="section-content">
            <div className="form-group">
              <label>{t('settings.babyAge')}</label>
              <select
                value={settings.babyAge}
                onChange={(e) => setSettings({ ...settings, babyAge: e.target.value })}
              >
                <option value="">{t('common.select')}</option>
                {['0-7', '1-2', '2-4', '1-2m', '2-3m', '3+'].map(value => <option key={value} value={value}>{t(`pilot.ages.${value}`)}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label>{t('settings.birthType')}</label>
              <select
                value={settings.birthType}
                onChange={(e) => setSettings({ ...settings, birthType: e.target.value })}
              >
                <option value="">{t('common.select')}</option>
                <option value="vaginal">{t('pilot.vaginal')}</option>
                <option value="c-section">{t('pilot.csection')}</option>
              </select>
            </div>
            <div className="form-group">
              <label>{t('settings.feedingType')}</label>
              <select
                value={settings.feedingType}
                onChange={(e) => setSettings({ ...settings, feedingType: e.target.value })}
              >
                <option value="">{t('common.select')}</option>
                {['breast', 'formula', 'mixed'].map(value => <option key={value} value={value}>{t(`tracking.${value}`)}</option>)}
              </select>
            </div>
          </div>
        </motion.div>

        <motion.div
          className="settings-section"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          <div className="section-header">
            <Shield size={20} />
            <h3>{t('settings.privacy')}</h3>
          </div>
          <div className="section-content">
            <p className="safety-note">
              {t('settings.privacyNote')}
            </p>
          </div>
        </motion.div>
      </fieldset>

      <div className="settings-footer">
        <motion.button
          className="save-button"
          onClick={handleSave}
          disabled={loadState !== 'ready' || saving}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          <Save size={20} />
          {saving ? t('settings.saving') : saved ? t('settings.saved') : t('settings.save')}
        </motion.button>
        {onLogout && (
          <button type="button" className="settings-logout" onClick={onLogout}>
            {t('settings.logout')}
          </button>
        )}
      </div>
      </>
      )}

      {activeSubTab === 'export' && <PrivacyCenter userId={userId} />}
      {activeSubTab === 'help' && <><FamilyHelp onPrivacy={() => setActiveSubTab('export')} onFindHelp={onFindHelp} /><InstallInstructions /></>}
      {activeSubTab === 'accessibility' && <><AccessibilitySettings />
        <details className="pilot-panel"><summary>{t('settings.notifications')}</summary><NotificationManager userId={userId} /></details></>}
      {activeSubTab === 'profile' && <details className="pilot-panel"><summary>{t('settings.security')}</summary><SecuritySettings userId={userId} /></details>}
    </div>
  )
}

export default Settings

