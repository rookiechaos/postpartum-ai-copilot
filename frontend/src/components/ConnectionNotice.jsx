import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'
import useConnection from '../utils/useConnection'

export default function ConnectionNotice({ onCheck }) {
  const { t } = useTranslation()
  const { online, reconnections } = useConnection()
  const [dismissed, setDismissed] = useState(0)
  if (online && reconnections <= dismissed) return null
  return <section className="pilot-panel connection-notice" aria-label={t('flows.connection.title')}>
    <p role="status">{t(online ? 'flows.connection.restored' : 'flows.connection.offline')}</p>
    <p>{t('flows.connection.noOfflineStorage')}</p>
    {online && <div className="pilot-actions">
      {onCheck && <button type="button" className="pilot-button secondary" onClick={onCheck}>{t('flows.connection.checkRecords')}</button>}
      <button type="button" className="pilot-button secondary" onClick={() => setDismissed(reconnections)}>{t('flows.connection.dismiss')}</button>
    </div>}
  </section>
}
