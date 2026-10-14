import React from 'react'
import { useTranslation } from 'react-i18next'
import { Globe } from 'lucide-react'
import './LanguageSelector.css'

function LanguageSelector({ id } = {}) {
  const { t, i18n } = useTranslation()

  const languages = [
    { code: 'ja', name: '日本語' },
    { code: 'en', name: 'English' }
  ]

  const changeLanguage = (langCode) => {
    // i18next's configured language detector caches the display choice locally.
    i18n.changeLanguage(langCode)
  }

  return (
    <div className="language-selector">
      <Globe size={18} />
      <select
        id={id}
        value={(i18n.resolvedLanguage || i18n.language).split('-')[0]}
        aria-label={t('settings.language')}
        onChange={(e) => changeLanguage(e.target.value)}
        className="language-select"
      >
        {languages.map((lang) => (
          <option key={lang.code} value={lang.code}>
            {lang.name}
          </option>
        ))}
      </select>
    </div>
  )
}

export default LanguageSelector

