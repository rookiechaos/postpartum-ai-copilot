import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'

export default function RecordingExample() {
  const { t } = useTranslation()
  const [saved, setSaved] = useState(false)
  return <details className="pilot-panel recording-example"><summary>{t('polish.exampleTitle')}</summary>
    <p>{t('polish.exampleNotice')}</p>
    <button type="button" className="pilot-button secondary" onClick={() => setSaved(true)}>{t('polish.exampleAction')}</button>
    {saved && <p role="status">{t('polish.exampleResult')} <button type="button" onClick={() => setSaved(false)}>{t('polish.undoQuick')}</button></p>}
  </details>
}
