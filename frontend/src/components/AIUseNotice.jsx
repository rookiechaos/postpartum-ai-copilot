import React from 'react'
import { useTranslation } from 'react-i18next'

export default function AIUseNotice({ accepted, onChange }) {
  const { t } = useTranslation()
  return (
    <div className="ai-use-notice">
      <p>{t('pilot.aiNotice')}</p>
      <label>
        <input type="checkbox" checked={accepted} onChange={event => onChange(event.target.checked)} />
        {t('pilot.aiConsent')}
      </label>
    </div>
  )
}
