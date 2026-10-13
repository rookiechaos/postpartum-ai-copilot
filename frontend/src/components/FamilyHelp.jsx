import React from 'react'
import { useTranslation } from 'react-i18next'

export default function FamilyHelp({ onPrivacy, onFindHelp }) {
  const { t } = useTranslation()
  return <section className="pilot-panel family-help">
    <h3>{t('work.helpTitle')}</h3><p>{t('work.helpIntro')}</p>
    {['record', 'retry', 'session', 'ai', 'share'].map(key => <details key={key}>
      <summary>{t(`work.help.${key}.question`)}</summary><p>{t(`work.help.${key}.answer`)}</p>
    </details>)}
    <div className="pilot-actions">
      <button className="pilot-button secondary" onClick={onPrivacy}>{t('work.dataPrivacy')}</button>
      {onFindHelp && <button className="pilot-button secondary" onClick={onFindHelp}>{t('work.humanHelp')}</button>}
    </div>
    <p>{t('pilot.noMonitoring')}</p>
  </section>
}
