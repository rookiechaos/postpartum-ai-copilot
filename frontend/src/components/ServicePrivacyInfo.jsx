import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../utils/api'

export function AIProviders({ directory, summaryOnly = false }) {
  const { t } = useTranslation()
  const names = { openai: 'OpenAI', claude: 'Claude', gemini: 'Gemini' }
  return <>
    <p>{t('work.answerProvider')}: {names[directory?.ai_provider] || directory?.ai_provider || t('pilot.notProvided')}</p>
    {!summaryOnly && directory?.ai_services?.length > 0 && <div><p>{t('work.processingProviders')}</p><ul>
      {directory.ai_services.map(service => <li key={service.purpose}>{t(`work.servicePurposes.${service.purpose}`)}: {service.provider}</li>)}
    </ul></div>}
  </>
}

export default function ServicePrivacyInfo() {
  const { t } = useTranslation()
  const [directory, setDirectory] = useState(null)
  const [failed, setFailed] = useState(false)
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    let active = true
    setFailed(false)
    api.get('/api/pilot').then(data => { if (active) setDirectory(data) })
      .catch(() => { if (active) setFailed(true) })
    return () => { active = false }
  }, [attempt])
  return <section className="service-privacy-info">
    <p>{t('work.dataLocation')}</p>
    {failed && <p role="alert">{t('pilot.loadFailed')} <button onClick={() => setAttempt(value => value + 1)}>{t('pilot.retry')}</button></p>}
    <dl className="privacy-facts">
      <dt>{t('work.operator')}</dt><dd>{directory?.profile?.name || t('pilot.notProvided')}</dd>
      <dt>{t('pilot.contact')}</dt><dd>{directory?.profile?.contact || directory?.profile?.email || t('pilot.notProvided')}</dd>
      <dt>{t('pilot.retention')}</dt><dd>{directory?.profile?.retention_notice || t('pilot.retentionUnknown')}</dd>
      <dt>{t('work.aiHandling')}</dt><dd>{directory?.profile?.ai_data_notice || t('work.askOperator')}</dd>
      <dt>{t('work.supportHandling')}</dt><dd>{directory?.profile?.account_support_notice || t('work.askOperator')}</dd>
    </dl>
    <AIProviders directory={directory} />
  </section>
}
