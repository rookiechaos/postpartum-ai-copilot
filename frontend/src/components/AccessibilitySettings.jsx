import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { readDisplaySettings, saveDisplaySettings } from '../utils/displaySettings'
import './AccessibilitySettings.css'

export default function AccessibilitySettings() {
  const { t } = useTranslation()
  const [settings, setSettings] = useState(readDisplaySettings)
  const [saveFailed, setSaveFailed] = useState(false)
  const change = (key, value) => {
    const next = { ...settings, [key]: value }
    setSettings(next); setSaveFailed(!saveDisplaySettings(next))
  }
  return <section className="accessibility-settings">
    <div className="accessibility-header"><h2>{t('accessibility.title')}</h2><p>{t('accessibility.description')}</p></div>
    <div className="accessibility-options">
      <div className="option-group">
        <label className="option-item"><span className="option-info"><span>
          <strong>{t('accessibility.highContrast')}</strong><p>{t('accessibility.highContrastDesc')}</p>
        </span></span><input type="checkbox" checked={settings.highContrast} onChange={event => change('highContrast', event.target.checked)} /></label>
        <label className="option-item"><span className="option-info"><span>
          <strong>{t('accessibility.fontSize')}</strong><p>{t('accessibility.fontSizeDesc')}</p>
        </span></span><select className="font-size-select" value={settings.fontSize} onChange={event => change('fontSize', event.target.value)}>
          {['small', 'medium', 'large', 'xlarge'].map(size => <option key={size} value={size}>{t(`accessibility.${size}`)}</option>)}
        </select></label>
        <label className="option-item"><span className="option-info"><span>
          <strong>{t('accessibility.reducedMotion')}</strong><p>{t('accessibility.reducedMotionDesc')}</p>
        </span></span><input type="checkbox" checked={settings.reducedMotion} onChange={event => change('reducedMotion', event.target.checked)} /></label>
      </div>
      <p>{t('accessibility.deviceOnly')}</p><p>{t('accessibility.keyboardHelp')}</p>
      {saveFailed && <p role="status">{t('accessibility.saveFailed')}</p>}
    </div>
  </section>
}
