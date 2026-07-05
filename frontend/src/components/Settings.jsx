import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import api from '../utils/api'
import { Save, User, Baby, Bell, Shield, HelpCircle, Download, Globe, BarChart3, Eye, Lock } from 'lucide-react'
import { useToast } from './Toast'
import ExportData from './ExportData'
import Help from './Help'
import HelpCenter from './HelpCenter'
import ProductAnalytics from './ProductAnalytics'
import NotificationManager from './NotificationManager'
import AccessibilitySettings from './AccessibilitySettings'
import SecuritySettings from './SecuritySettings'
import './Settings.css'

function Settings({ userId, onContextUpdate, onLogout }) {
  const { t, i18n } = useTranslation()
  const [settings, setSettings] = useState({
    babyName: '',
    babyAge: '',
    birthType: '',
    feedingType: '',
    notifications: true,
    darkMode: false,
    language: i18n.language
  })
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [activeSubTab, setActiveSubTab] = useState('profile')
  const toast = useToast()

  useEffect(() => {
    loadSettings()
  }, [userId])

  const loadSettings = async () => {
    try {
      const context = await api.getUserContext(userId)
      setSettings({
        babyName: context.babyName || '',
        babyAge: context.babyAge || '',
        birthType: context.birthType || '',
        feedingType: context.feedingType || '',
        notifications: context.notifications !== false,
        darkMode: context.darkMode || false,
        language: context.language || i18n.language
      })Set language if available
      if (context.language && context.language !== i18n.language) {
        i18n.changeLanguage(context.language)
      }
    } catch (error) {
      console.error('Error loading settings:', error)
    }
  }

  const handleSave = async () => {
    setSaving(true)
    try {Update language if changed
      if (settings.language !== i18n.language) {
        i18n.changeLanguage(settings.language)
        localStorage.setItem('preferred-language', settings.language)
      }
      
      await api.updateUserContext(userId, {
        babyName: settings.babyName,
        babyAge: settings.babyAge,
        birthType: settings.birthType,
        feedingType: settings.feedingType,
        notifications: settings.notifications,
        darkMode: settings.darkMode,
        language: settings.language
      })
      setSaved(true)
      if (onContextUpdate) {
        onContextUpdate(settings)
      }
      toast.success(t('settings.saved'))
      setTimeout(() => setSaved(false), 3000)
    } catch (error) {
      console.error('Error saving settings:', error)
      toast.error(error?.message || t('common.error'))
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
          <User size={18}>
          {t('settings.profile')}
        </button>
        <button
          className={activeSubTab === 'export' ? 'active' : ''}
          onClick={() => setActiveSubTab('export')}
        >
          <Download size={18}>
          {t('settings.export')}
        </button>
        <button
          className={activeSubTab === 'notifications' ? 'active' : ''}
          onClick={() => setActiveSubTab('notifications')}
        >
          <Bell size={18}>
          {t('settings.notifications')}
        </button>
        <button
          className={activeSubTab === 'help' ? 'active' : ''}
          onClick={() => setActiveSubTab('help')}
        >
          <HelpCircle size={18}>
          {t('settings.help')}
        </button>
        <button
          className={activeSubTab === 'analytics' ? 'active' : ''}
          onClick={() => setActiveSubTab('analytics')}
        >
          <BarChart3 size={18}>
          Analytics
        </button>
        <button
          className={activeSubTab === 'accessibility' ? 'active' : ''}
          onClick={() => setActiveSubTab('accessibility')}
        >
          <Eye size={18}>
          {t('settings.accessibility', 'Accessibility')}
        </button>
        <button
          className={activeSubTab === 'security' ? 'active' : ''}
          onClick={() => setActiveSubTab('security')}
        >
          <Lock size={18}>
          {t('settings.security', 'Security')}
        </button>
      </div>

      {activeSubTab === 'profile' && (
      <>
      <div className="settings-sections">
        <motion.div
          className="settings-section"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <div className="section-header">
            <User size={20}>
            <h3>{t('settings.profile')}</h3>
          </div>
          <div className="section-content">
            <div className="form-group">
              <label>{t('settings.babyName')}</label>
              <input
                type="text"
                value={settings.babyName}
                onChange={(e) => setSettings({ ...settings, babyName: e.target.value })}
                placeholder={t('settings.babyNamePlaceholder')}>
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
            <Baby size={20}>
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
                <option value="0-7">0-7 days</option>
                <option value="1-2">1-2 weeks</option>
                <option value="2-4">2-4 weeks</option>
                <option value="1-2m">1-2 months</option>
                <option value="2-3m">2-3 months</option>
                <option value="3+">3+ months</option>
              </select>
            </div>
            <div className="form-group">
              <label>{t('settings.birthType')}</label>
              <select
                value={settings.birthType}
                onChange={(e) => setSettings({ ...settings, birthType: e.target.value })}
              >
                <option value="">{t('common.select')}</option>
                <option value="vaginal">Vaginal Birth</option>
                <option value="c-section">C-Section</option>
              </select>
            </div>
            <div className="form-group">
              <label>{t('settings.feedingType')}</label>
              <select
                value={settings.feedingType}
                onChange={(e) => setSettings({ ...settings, feedingType: e.target.value })}
              >
                <option value="">{t('common.select')}</option>
                <option value="breast">Breastfeeding</option>
                <option value="formula">Formula</option>
                <option value="mixed">Mixed</option>
              </select>
            </div>
          </div>
        </motion.div>

        <motion.div
          className="settings-section"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <div className="section-header">
            <Bell size={20}>
            <h3>{t('settings.preferences')}</h3>
          </div>
          <div className="section-content">
            <div className="toggle-group">
              <label>
                <input
                  type="checkbox"
                  checked={settings.notifications}
                  onChange={(e) => setSettings({ ...settings, notifications: e.target.checked })}>
                <span>{t('settings.enableNotifications')}</span>
              </label>
            </div>
            <div className="toggle-group">
              <label>
                <input
                  type="checkbox"
                  checked={settings.darkMode}
                  onChange={(e) => setSettings({ ...settings, darkMode: e.target.checked })}>
                <span>{t('settings.darkMode')}</span>
              </label>
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
            <Shield size={20}>
            <h3>{t('settings.privacy')}</h3>
          </div>
          <div className="section-content">
            <p className="safety-note">
              {t('settings.privacyNote')}
            </p>
          </div>
        </motion.div>
      </div>

      <div className="settings-footer">
        <motion.button
          className="save-button"
          onClick={handleSave}
          disabled={saving}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          <Save size={20}>
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

      {activeSubTab === 'export' && <ExportData userId={userId}>}
      {activeSubTab === 'notifications' && <NotificationManager userId={userId}>}
      {activeSubTab === 'help' && <HelpCenter>}
      {activeSubTab === 'analytics' && <ProductAnalytics userId={userId}>}
      {activeSubTab === 'accessibility' && <AccessibilitySettings>}
      {activeSubTab === 'security' && <SecuritySettings userId={userId}>}
    </div>
  )
}

export default Settings

