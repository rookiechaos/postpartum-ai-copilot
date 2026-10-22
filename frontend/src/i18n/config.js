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
import friendlyEnglish from './locales/friendly.en.json'
import friendlyJapanese from './locales/friendly.ja.json'
import localCareEnglish from './locales/localCare.en.json'
import localCareJapanese from './locales/localCare.ja.json'
import interactionEnglish from './locales/interaction.en.json'
import interactionJapanese from './locales/interaction.ja.json'
import continuityEnglish from './locales/continuity.en.json'
import continuityJapanese from './locales/continuity.ja.json'
import reviewFixesEnglish from './locales/reviewFixes.en.json'
import reviewFixesJapanese from './locales/reviewFixes.ja.json'
import workflowEnglish from './locales/workflow.en.json'
import workflowJapanese from './locales/workflow.ja.json'
import foundationEnglish from './locales/foundation.en.json'
import foundationJapanese from './locales/foundation.ja.json'

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      en: {
        translation: { ...enTranslations, polish: polishEnglish, ui: uiEnglish, flows: flowsEnglish, friendly: friendlyEnglish, localCare: localCareEnglish, interaction: interactionEnglish, continuity: continuityEnglish, reviewFixes: reviewFixesEnglish, workflow: workflowEnglish, foundation: foundationEnglish }
      },
      ja: {
        translation: { ...jaTranslations, polish: polishJapanese, ui: uiJapanese, flows: flowsJapanese, friendly: friendlyJapanese, localCare: localCareJapanese, interaction: interactionJapanese, continuity: continuityJapanese, reviewFixes: reviewFixesJapanese, workflow: workflowJapanese, foundation: foundationJapanese }
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
  if (typeof document !== 'undefined') {
    document.documentElement.lang = i18n.resolvedLanguage || 'ja'
    if (i18n.isInitialized) document.title = i18n.t('app.title')
  }
}
i18n.on('languageChanged', updatePageLanguage)
i18n.on('initialized', updatePageLanguage)
if (i18n.isInitialized) updatePageLanguage()

export default i18n
