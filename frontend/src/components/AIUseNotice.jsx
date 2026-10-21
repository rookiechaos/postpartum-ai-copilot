import React, { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../utils/api'
import { AIProviders } from './ServicePrivacyInfo'

export default function AIUseNotice({ accepted, onChange = () => {}, scope = 'message', disabled = false, consentAction = false,
  includeProfile = false, onProfileChange, includeParent = false, onParentChange,
  includeNotes = false, onNotesChange, includeHistory = false, onHistoryChange, profileLabel, children }) {
  const { t } = useTranslation()
  const [provider, setProvider] = useState(null)
  useEffect(() => {
    let active = true
    api.get('/api/pilot').then(data => { if (active) setProvider(data) }).catch(() => {})
    return () => { active = false }
  }, [])
  return (
    <div className="ai-use-notice">
      <p>{t(`work.aiScope.${scope}`)}</p>
      <AIProviders directory={provider} summaryOnly />
      <details className="ai-processing-details"><summary>{t('ui.chat.processingDetails')}</summary>
        <AIProviders directory={provider} />
        <p>{t('work.operator')}: {provider?.profile?.name || t('pilot.notProvided')}</p>
        <p>{provider?.profile?.ai_data_notice || t('work.askOperator')}</p>
      </details>
      <fieldset disabled={disabled}>
        <legend>{t('work.aiAttachments')}</legend>
        {onProfileChange && <label><input type="checkbox" checked={includeProfile} onChange={event => { onProfileChange(event.target.checked); onChange(false) }} />{profileLabel || t('work.attachProfile')}</label>}
        {onParentChange && <label><input type="checkbox" checked={includeParent} onChange={event => { onParentChange(event.target.checked); onChange(false) }} />{t('pilot.includeParent')}</label>}
        {onNotesChange && <label><input type="checkbox" checked={includeNotes} onChange={event => { onNotesChange(event.target.checked); onChange(false) }} />{t('pilot.includeNotes')}</label>}
        {onHistoryChange && <label><input type="checkbox" checked={includeHistory} onChange={event => { onHistoryChange(event.target.checked); onChange(false) }} />{t('work.attachHistory')}</label>}
        {children}
      {!consentAction && <label>
        <input type="checkbox" checked={accepted} onChange={event => onChange(event.target.checked)} />
        {t('pilot.aiConsent')}
      </label>}
      </fieldset>
    </div>
  )
}
