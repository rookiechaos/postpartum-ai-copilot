import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import LanguageDetector from 'i18next-browser-languagedetector'

import enTranslations from './locales/en.json'
import jaTranslations from './locales/ja.json'
import polishEnglish from './locales/polish.en.json'
import polishJapanese from './locales/polish.ja.json'
import uiEnglish from './locales/ui.en.json'
import uiJapanese from './locales/ui.ja.json'
import flowsEnglish from './locales/flows.en.json'
import flowsJapanese from './locales/flows.ja.json'

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      en: {
        translation: { ...enTranslations, polish: polishEnglish, ui: uiEnglish, flows: flowsEnglish }
      },
      ja: {
        translation: { ...jaTranslations, polish: polishJapanese, ui: uiJapanese, flows: flowsJapanese }
      }
    },
    fallbackLng: 'ja',
    supportedLngs: ['ja', 'en'],
    load: 'languageOnly',
    defaultNS: 'translation',
    interpolation: {
      escapeValue: false
    },
    detection: {
      order: ['localStorage', 'navigator'],
      caches: ['localStorage']
    }
  })

const updatePageLanguage = () => {
  if (typeof document !== 'undefined') document.documentElement.lang = i18n.resolvedLanguage || 'ja'
}
i18n.on('languageChanged', updatePageLanguage)
i18n.on('initialized', updatePageLanguage)

export default i18n
