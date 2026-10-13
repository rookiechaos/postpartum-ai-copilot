import React from 'react'
import { useTranslation } from 'react-i18next'
import AccountRequests from './AccountRequests'
import ExportData from './ExportData'
import ServicePrivacyInfo from './ServicePrivacyInfo'
import DraftRecoverySettings from './DraftRecovery'

export default function PrivacyCenter({ userId }) {
  const { t } = useTranslation()
  return <div>
    <section className="pilot-panel"><h3>{t('work.dataPrivacy')}</h3><ServicePrivacyInfo /></section>
    <DraftRecoverySettings />
    <AccountRequests />
    <details className="pilot-panel"><summary>{t('settings.export')}</summary><ExportData userId={userId} /></details>
  </div>
}
