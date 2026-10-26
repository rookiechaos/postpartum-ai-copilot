import React, { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../utils/api'
import { useCareWork } from '../utils/CareSession'
import { revealElement } from '../utils/focusView'
import { Save, User, Baby, Shield, HelpCircle, Eye } from 'lucide-react'
import { useToast } from './Toast'
import PrivacyCenter from './PrivacyCenter'
import FamilyHelp from './FamilyHelp'
import NotificationManager from './NotificationManager'
import AccessibilitySettings from './AccessibilitySettings'
import SecuritySettings from './SecuritySettings'
import LanguageSelector from './LanguageSelector'
import { InstallInstructions } from './InstallPrompt'
import { Button, ErrorMessage, FormField, PageHeader, StatusMessage } from './ui'
import './Settings.css'
import './SettingsFlow.css'

const profileFields = ['babyName', 'babyAge', 'birthType', 'feedingType']
const profileValues = context => Object.fromEntries(profileFields.map(key => [key,
  typeof context?.[key] === 'string' ? context[key] : '']))
const languageValue = (context, fallback) => typeof context?.language === 'string'
  && ['ja', 'en'].includes(context.language.split('-')[0]) ? context.language.split('-')[0] : fallback
const sameProfile = (left, right) => Boolean(left && right) && Object.keys(left).every(key => left[key] === right[key])

function Settings({ userId, onContextUpdate, onLogout, onFindHelp, onSwitchEntrance, navigationRequest, visible = true }) {
  const { t, i18n } = useTranslation()
  const displayLanguage = (i18n.resolvedLanguage || i18n.language || 'ja').split('-')[0]
  const [settings, setSettings] = useState({
    babyName: '',
    babyAge: '',
    birthType: '',
    feedingType: ''
  })
  const [saveState, setSaveState] = useState('idle')
  const [baseline, setBaseline] = useState(null)
  const [pendingSave, setPendingSave] = useState(null)
  const [checkedContext, setCheckedContext] = useState(null)
  const [loadState, setLoadState] = useState('loading')
  const [loadAttempt, setLoadAttempt] = useState(0)
  const [activeSubTab, setActiveSubTab] = useState('profile')
  const handledNavigation = useRef(0)
  const helpButton = useRef(null)
  const profileButton = useRef(null)
  const operationLock = useRef(false)
  const generation = useRef(0)
  const displayLanguageRef = useRef(displayLanguage)
  displayLanguageRef.current = displayLanguage
  const toast = useToast()
  const saving = saveState === 'saving'
  const checking = saveState === 'checking'
  const dirty = loadState === 'ready' && !sameProfile(baseline, { ...settings, language: displayLanguage })
  const workTitle = saving ? 'settingsFlow.workSaving' : pendingSave ? 'settingsFlow.workPending'
    : dirty ? 'settingsFlow.workDraft' : null
  useCareWork('settings-profile', workTitle ? {
    version: `${workTitle}:${saveState}`, title: workTitle, critical: saving || Boolean(pendingSave),
    protectLeave: true, priority: saving || pendingSave ? 0 : 2,
    tab: 'settings', detail: { view: 'profile' }, action: 'experience.trackedWorkOpen'
  } : null)

  useEffect(() => {
    if (!visible || !navigationRequest?.key || handledNavigation.current === navigationRequest.key
      || !['help', 'profile'].includes(navigationRequest.view)) return
    setActiveSubTab(navigationRequest.view)
    if (revealElement(navigationRequest.view === 'help' ? helpButton.current : profileButton.current)) handledNavigation.current = navigationRequest.key
  }, [navigationRequest?.key, navigationRequest?.view, visible])

  useEffect(() => {
    const currentGeneration = ++generation.current
    const isCurrent = () => generation.current === currentGeneration
    const loadSettings = async () => {
      setLoadState('loading')
      setSaveState('idle')
      setBaseline(null)
      setPendingSave(null)
      setCheckedContext(null)
      operationLock.current = false
      try {
        const context = await api.getUserContext(userId)
        if (!isCurrent()) return
        const loaded = profileValues(context)
        setSettings(loaded)
        setBaseline({ ...loaded, language: languageValue(context, displayLanguageRef.current) })
        setLoadState('ready')
      } catch {
        if (isCurrent()) {
          setLoadState('error')
        }
      }
    }
    loadSettings()
    return () => { generation.current += 1 }
  }, [userId, loadAttempt])

  const handleSave = async () => {
    if (loadState !== 'ready' || operationLock.current || pendingSave || !dirty) return
    operationLock.current = true
    const currentGeneration = generation.current
    // Capture exactly what this explicit save sends. A language change in the
    // header while this is pending remains an unsaved change afterwards.
    const submitted = { ...settings, language: displayLanguage }
    setSaveState('saving')
    try {
      const savedContext = await api.updateUserContext(userId, submitted)
      if (generation.current !== currentGeneration) return
      setBaseline(submitted)
      setSaveState('saved')
      if (onContextUpdate) onContextUpdate(savedContext?.context || submitted)
      toast.success(i18n.t('settings.saved'))
    } catch (error) {
      if (generation.current !== currentGeneration) return
      if (error.resultUnconfirmed) {
        setPendingSave(submitted)
        setSaveState('unconfirmed')
      } else setSaveState('failed')
    } finally {
      if (generation.current === currentGeneration) operationLock.current = false
    }
  }

  const checkSaveResult = async () => {
    if (!pendingSave || operationLock.current) return
    operationLock.current = true
    const currentGeneration = generation.current
    setSaveState('checking')
    setCheckedContext(null)
    try {
      const context = await api.getUserContext(userId)
      if (generation.current !== currentGeneration) return
      if (!context || typeof context !== 'object' || Array.isArray(context)) throw new Error('Profile unavailable')
      const actual = { ...profileValues(context), language: languageValue(context, '') }
      if (sameProfile(actual, pendingSave)) {
        setBaseline(pendingSave)
        setPendingSave(null)
        setSaveState('saved')
        if (onContextUpdate) onContextUpdate(context)
      } else {
        // A different read does not prove the earlier write cannot still finish.
        // Keep its uncertainty visible until the user makes a decision.
        setCheckedContext(context)
        setSaveState('different')
      }
    } catch {
      if (generation.current === currentGeneration) setSaveState('checkFailed')
    } finally {
      if (generation.current === currentGeneration) operationLock.current = false
    }
  }

  const continueEditing = () => {
    if (!checkedContext || operationLock.current || !window.confirm(t('settingsFlow.continueConfirm'))) return
    setBaseline({ ...profileValues(checkedContext), language: languageValue(checkedContext, displayLanguage) })
    if (onContextUpdate) onContextUpdate(checkedContext)
    setPendingSave(null)
    setCheckedContext(null)
    setSaveState('idle')
  }

  const discardChanges = () => {
    if (!baseline || operationLock.current || pendingSave || !dirty || !window.confirm(t('settingsFlow.discardConfirm'))) return
    setSettings(profileValues(baseline))
    i18n.changeLanguage(baseline.language)
    setSaveState('idle')
  }

  const profileValueLabel = (key, value) => {
    if (!value) return t('pilot.notProvided')
    if (key === 'language') return value === 'ja' ? '日本語' : 'English'
    if (key === 'babyAge') return t(`pilot.ages.${value}`, { defaultValue: value })
    if (key === 'birthType') return value === 'vaginal' ? t('pilot.vaginal')
      : value === 'c-section' ? t('pilot.csection') : value
    if (key === 'feedingType') return t(`tracking.${value}`, { defaultValue: value })
    return value
  }

  return (
    <div className="settings">
      <PageHeader title={t('settings.title')} description={t('settings.subtitle')} />

      <div className="settings-tabs">
        <button
          type="button" ref={profileButton} aria-pressed={activeSubTab === 'profile'}
          className={activeSubTab === 'profile' ? 'active' : ''}
          onClick={() => setActiveSubTab('profile')}
        >
          <User size={18} />
          {t('settings.profile')}
        </button>
        <button
          type="button" aria-pressed={activeSubTab === 'export'}
          className={activeSubTab === 'export' ? 'active' : ''}
          onClick={() => setActiveSubTab('export')}
        >
          <Shield size={18} />
          {t('work.dataPrivacy')}
        </button>
        <button
          type="button" ref={helpButton} aria-pressed={activeSubTab === 'help'}
          className={activeSubTab === 'help' ? 'active' : ''}
          onClick={() => setActiveSubTab('help')}
        >
          <HelpCircle size={18} />
          {t('settings.help')}
        </button>
        <button
          type="button" aria-pressed={activeSubTab === 'accessibility'}
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
      {loadState === 'ready' && !pendingSave && (saveState !== 'failed' || !dirty) && (
        <StatusMessage tone={saveState === 'saved' && !dirty ? 'success' : 'info'}
          title={t(saving ? 'settingsFlow.saving' : dirty ? 'settingsFlow.unsaved'
          : saveState === 'saved' ? 'settingsFlow.saved' : 'settingsFlow.unchanged')}>
          <p>{t('settingsFlow.scopeHint')}</p>
        </StatusMessage>
      )}
      {pendingSave && (
        <StatusMessage tone={saveState === 'checkFailed' ? 'error' : 'info'}
          title={t(checking ? 'settingsFlow.checking' : saveState === 'different' ? 'settingsFlow.different'
            : saveState === 'checkFailed' ? 'settingsFlow.checkFailed' : 'settingsFlow.unconfirmed')}
          actions={<>
            <Button variant="secondary" busy={checking} busyLabel={t('settingsFlow.checking')}
              onClick={checkSaveResult}>{t('settingsFlow.checkResult')}</Button>
            {saveState === 'different' && checkedContext && <Button variant="secondary"
              onClick={continueEditing}>{t('settingsFlow.continueEditing')}</Button>}
          </>}>
          <p>{t('settingsFlow.pendingHint')}</p>
          {checkedContext && saveState === 'different' && <details className="settings-save-comparison">
            <summary>{t('settingsFlow.comparison')}</summary>
            <div className="settings-save-comparison-scroll" role="region" tabIndex={0} aria-label={t('settingsFlow.comparison')}>
              <table>
                <thead><tr><th scope="col">{t('settingsFlow.field')}</th><th scope="col">{t('settingsFlow.submitted')}</th><th scope="col">{t('settingsFlow.onAccount')}</th></tr></thead>
                <tbody>{[...profileFields, 'language'].map(key => <tr key={key}>
                  <th scope="row">{t(`settings.${key}`)}</th>
                  <td>{profileValueLabel(key, pendingSave[key])}</td>
                  <td>{profileValueLabel(key, key === 'language' ? languageValue(checkedContext, '') : profileValues(checkedContext)[key])}</td>
                </tr>)}</tbody>
              </table>
            </div>
          </details>}
        </StatusMessage>
      )}
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

      {saveState === 'failed' && dirty && <ErrorMessage title={t('settingsFlow.failed')} onRetry={handleSave}
        retryDisabled={saving || loadState !== 'ready' || !dirty}><p>{t('settingsFlow.failedHint')}</p></ErrorMessage>}
      <div className="settings-footer">
        <Button
          busy={saving} busyLabel={t('settings.saving')}
          onClick={handleSave}
          disabled={loadState !== 'ready' || saving || Boolean(pendingSave) || !dirty}
        >
          <Save size={20} />
          {saving ? t('settings.saving') : t('settings.save')}
        </Button>
        <Button variant="secondary" onClick={discardChanges}
          disabled={loadState !== 'ready' || saving || Boolean(pendingSave) || !dirty}>{t('settingsFlow.discard')}</Button>
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

