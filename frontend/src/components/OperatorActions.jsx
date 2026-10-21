import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../utils/api'
import { japanDateTime } from '../utils/japanTime'

export default function OperatorActions({ refreshKey, blocked, onRequests, onOrganization }) {
  const { t, i18n } = useTranslation()
  const [data, setData] = useState(null)
  const [error, setError] = useState(false)
  const [loading, setLoading] = useState(false)
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    let active = true
    setLoading(true); setError(false)
    api.get('/api/monitoring/actions').then(result => { if (active) setData(result) })
      .catch(() => { if (active) { setError(true); setData(null) } }).finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [refreshKey, attempt])
  return <section className="pilot-panel operator-actions"><h2>{t('workflow.operator.title')}</h2><p>{t('workflow.operator.notice')}</p>
    <button type="button" className="text-action" disabled={loading} onClick={() => setAttempt(value => value + 1)}>{t('workflow.operator.refresh')}</button>
    {error && <p role="alert">{t('pilot.loadFailed')}</p>}
    {loading && <p role="status">{t('common.loading')}</p>}
    {data && <>
      <p>{t('workflow.operator.checked', { time: japanDateTime(data.checked_at, i18n.resolvedLanguage || 'ja') })}</p>
      <div className="workflow-action-grid">
        <article className="support-card"><h3>{t('workflow.operator.requests')}</h3>
          {['received', 'verifying', 'overdue'].map(key => <p key={key}>
            <button type="button" className="text-action" disabled={blocked} onClick={() => onRequests(key)}>{t(`workflow.operator.${key}`, { count: data.requests[key] })}</button>
          </p>)}<p>{t('workflow.operator.requestAction')}</p>
        </article>
        <article className="support-card"><h3>{t('workflow.operator.ai')}</h3>
          <p>{t('workflow.operator.waiting', { count: data.ai.waiting })}</p><p>{t('workflow.operator.waitingLong', { count: data.ai.waiting_long })}</p>
          <p>{t('workflow.operator.failed', { count: data.ai.failed_last_day })}</p>
          {data.ai.oldest_at && <p>{t('workflow.operator.oldest', { time: japanDateTime(data.ai.oldest_at, i18n.resolvedLanguage || 'ja') })}</p>}
          <p>{t('workflow.operator.aiAction')}</p>
        </article>
        <article className="support-card"><h3>{t('workflow.operator.directory', { count: data.directory.due_count })}</h3>
          <ul>{data.directory.contacts.map(item => <li key={item.contact_key}><strong>{item.name || t('work.unnamedResource')}</strong>
            <p>{item.assignee || t('polish.noMaintainer')} · {item.due_on || t('polish.noReviewDate')}</p>
          </li>)}</ul>
          {onOrganization && <button type="button" className="pilot-button secondary" disabled={blocked} onClick={onOrganization}>{t('workflow.operator.openDirectory')}</button>}
        </article>
      </div>
    </>}
  </section>
}
