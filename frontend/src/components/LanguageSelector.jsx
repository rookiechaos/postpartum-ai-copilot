import React from 'react'
import { useTranslation } from 'react-i18next'
import { Globe } from 'lucide-react'
import './LanguageSelector.css'

function LanguageSelector() {
  const { i18n } = useTranslation()

  const languages = [
    { code: 'en', name: 'English', flag: '🇺🇸' },
    { code: 'ja', name: '日本語', flag: '🇯🇵' }
  ]

  const changeLanguage = (langCode) => {
    i18n.changeLanguage(langCode)
    localStorage.setItem('preferred-language', langCode)
  }

  return (
    <div className="language-selector">
      <Globe size={18}>
      <select
        value={i18n.language}
        onChange={(e) => changeLanguage(e.target.value)}
        className="language-select"
      >
        {languages.map((lang) => (
          <option key={lang.code} value={lang.code}>
            {lang.flag} {lang.name}
          </option>
        ))}
      </select>
    </div>
  )
}

export default LanguageSelector

