import React, { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { Eye, Type, Keyboard, Volume2 } from 'lucide-react'
import './AccessibilitySettings.css'

function AccessibilitySettings({ onClose }) {
  const { t } = useTranslation()
  const [settings, setSettings] = useState({
    highContrast: false,
    fontSize: 'medium', // small, medium, large, xlarge
    keyboardNavigation: true,
    screenReader: true,
    reducedMotion: false
  })

  useEffect(() => {
    // Load saved settings
    const saved = localStorage.getItem('accessibility_settings')
    if (saved) {
      try {
        setSettings(JSON.parse(saved))
        applySettings(JSON.parse(saved))
      } catch (e) {
        console.error('Failed to load accessibility settings:', e)
      }
    } else {
      applySettings(settings)
    }
  }, [])

  const applySettings = (newSettings) => {
    const root = document.documentElement
    
    // High contrast
    if (newSettings.highContrast) {
      root.classList.add('high-contrast')
    } else {
      root.classList.remove('high-contrast')
    }
    
    // Font size
    root.style.setProperty('--font-size-base', {
      small: '14px',
      medium: '16px',
      large: '18px',
      xlarge: '20px'
    }[newSettings.fontSize] || '16px')
    
    // Reduced motion
    if (newSettings.reducedMotion) {
      root.classList.add('reduced-motion')
    } else {
      root.classList.remove('reduced-motion')
    }
  }

  const handleChange = (key, value) => {
    const newSettings = { ...settings, [key]: value }
    setSettings(newSettings)
    localStorage.setItem('accessibility_settings', JSON.stringify(newSettings))
    applySettings(newSettings)
  }

  return (
    <div className="accessibility-settings">
      <div className="accessibility-header">
        <h2>{t('accessibility.title', 'Accessibility Settings')}</h2>
        <p>{t('accessibility.description', 'Customize the app to meet your needs')}</p>
      </div>

      <div className="accessibility-options">
        <div className="option-group">
          <div className="option-item">
            <div className="option-info">
              <Eye size={20} />
              <div>
                <h3>{t('accessibility.highContrast', 'High Contrast Mode')}</h3>
                <p>{t('accessibility.highContrastDesc', 'Increase contrast for better visibility')}</p>
              </div>
            </div>
            <label className="toggle-switch">
              <input
                type="checkbox"
                checked={settings.highContrast}
                onChange={(e) => handleChange('highContrast', e.target.checked)}
              />
              <span className="slider"></span>
            </label>
          </div>

          <div className="option-item">
            <div className="option-info">
              <Type size={20} />
              <div>
                <h3>{t('accessibility.fontSize', 'Font Size')}</h3>
                <p>{t('accessibility.fontSizeDesc', 'Adjust text size for better readability')}</p>
              </div>
            </div>
            <select
              value={settings.fontSize}
              onChange={(e) => handleChange('fontSize', e.target.value)}
              className="font-size-select"
            >
              <option value="small">{t('accessibility.small', 'Small')}</option>
              <option value="medium">{t('accessibility.medium', 'Medium')}</option>
              <option value="large">{t('accessibility.large', 'Large')}</option>
              <option value="xlarge">{t('accessibility.xlarge', 'Extra Large')}</option>
            </select>
          </div>

          <div className="option-item">
            <div className="option-info">
              <Keyboard size={20} />
              <div>
                <h3>{t('accessibility.keyboardNav', 'Keyboard Navigation')}</h3>
                <p>{t('accessibility.keyboardNavDesc', 'Navigate using keyboard shortcuts')}</p>
              </div>
            </div>
            <label className="toggle-switch">
              <input
                type="checkbox"
                checked={settings.keyboardNavigation}
                onChange={(e) => handleChange('keyboardNavigation', e.target.checked)}
              />
              <span className="slider"></span>
            </label>
          </div>

          <div className="option-item">
            <div className="option-info">
              <Volume2 size={20} />
              <div>
                <h3>{t('accessibility.screenReader', 'Screen Reader Support')}</h3>
                <p>{t('accessibility.screenReaderDesc', 'Optimize for screen readers')}</p>
              </div>
            </div>
            <label className="toggle-switch">
              <input
                type="checkbox"
                checked={settings.screenReader}
                onChange={(e) => handleChange('screenReader', e.target.checked)}
              />
              <span className="slider"></span>
            </label>
          </div>

          <div className="option-item">
            <div className="option-info">
              <Eye size={20} />
              <div>
                <h3>{t('accessibility.reducedMotion', 'Reduce Motion')}</h3>
                <p>{t('accessibility.reducedMotionDesc', 'Minimize animations and transitions')}</p>
              </div>
            </div>
            <label className="toggle-switch">
              <input
                type="checkbox"
                checked={settings.reducedMotion}
                onChange={(e) => handleChange('reducedMotion', e.target.checked)}
              />
              <span className="slider"></span>
            </label>
          </div>
        </div>

        <div className="accessibility-shortcuts">
          <h3>{t('accessibility.shortcuts', 'Keyboard Shortcuts')}</h3>
          <ul>
            <li><kbd>Tab</kbd> - Navigate between elements</li>
            <li><kbd>Enter</kbd> - Activate button/link</li>
            <li><kbd>Esc</kbd> - Close modal/dialog</li>
            <li><kbd>/</kbd> - Focus search</li>
            <li><kbd>?</kbd> - Show help</li>
          </ul>
        </div>
      </div>

      {onClose && (
        <div className="accessibility-actions">
          <button className="btn-primary" onClick={onClose}>
            {t('common.done', 'Done')}
          </button>
        </div>
      )}
    </div>
  )
}

export default AccessibilitySettings
