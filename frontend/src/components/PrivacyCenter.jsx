import React, { useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import AccountRequests from './AccountRequests'
import ExportData from './ExportData'
import ServicePrivacyInfo from './ServicePrivacyInfo'
import DraftRecoverySettings from './DraftRecovery'
import api from '../utils/api'

export default function PrivacyCenter({ userId }) {
  const { t } = useTranslation()
  const [cleanup, setCleanup] = useState('')
  const clearing = useRef(false)
  return <div>
    <section className="pilot-panel"><h3>{t('work.dataPrivacy')}</h3><ServicePrivacyInfo /></section>
    <DraftRecoverySettings />
    <details className="pilot-panel"><summary>{t('flows.connection.legacyStorage')}</summary>
      <p>{t('flows.connection.legacyNotice')}</p>
      <button type="button" className="pilot-button secondary" disabled={cleanup === 'clearing'} onClick={async () => {
        if (clearing.current || !window.confirm(t('flows.connection.legacyClearConfirm'))) return
        clearing.current = true; setCleanup('clearing')
        try { setCleanup(await api.clearLegacyOfflineStorage() ? 'cleared' : 'blocked') }
        finally { clearing.current = false }
      }}>{t('flows.connection.legacyClear')}</button>
      {cleanup && <p role="status">{t(`flows.connection.${cleanup}`)}</p>}
    </details>
    <AccountRequests />
    <details className="pilot-panel"><summary>{t('settings.export')}</summary><ExportData userId={userId} /></details>
  </div>
}
