import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'
import useConnection from '../utils/useConnection'
import { Button, StatusMessage } from './ui'

export default function ConnectionNotice({ onCheck }) {
  const { t } = useTranslation()
  const { online, reconnections } = useConnection()
  const [dismissed, setDismissed] = useState(0)
  if (online && reconnections <= dismissed) return null
  return <StatusMessage tone={online ? 'info' : 'warning'} className="connection-notice" aria-label={t('flows.connection.title')}
    title={t(online ? 'flows.connection.restored' : 'flows.connection.offline')}>
    <p>{t('flows.connection.noOfflineStorage')}</p>
    {online && <div className="pilot-actions">
      {onCheck && <Button variant="secondary" onClick={onCheck}>{t('flows.connection.checkRecords')}</Button>}
      <Button variant="secondary" onClick={() => setDismissed(reconnections)}>{t('flows.connection.dismiss')}</Button>
    </div>}
  </StatusMessage>
}
