import React, { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../utils/api'
import './ProductAnalytics.css'

const number = value => Number.isFinite(Number(value)) ? Number(value) : 0

export default function ProductAnalytics() {
  const { t } = useTranslation()
  const [dashboard, setDashboard] = useState(null)
  const [loading, setLoading] = useState(true)
  const [failed, setFailed] = useState(false)
  const [days, setDays] = useState(30)
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    let active = true
    setLoading(true); setFailed(false); setDashboard(null)
    api.getProductDashboard(days).then(data => { if (active) setDashboard(data) })
      .catch(() => { if (active) setFailed(true) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [days, attempt])
  const current = dashboard?.current || {}
  const funnel = dashboard?.conversion_funnel
  const historical = dashboard?.historical || []
  const maxDaily = Math.max(1, ...historical.map(point => number(point.dau)))
  const metrics = [['daily', number(current.dau)], ['monthly', number(current.mau)],
    ['ratio', `${number(current.dau_mau_ratio).toFixed(1)}%`], ['retention', `${number(dashboard?.retention?.day_7).toFixed(1)}%`]]
  return <section className="product-analytics">
    <div className="analytics-header"><h2>{t('analytics.title')}</h2>
      <label>{t('work.recordPeriod')}<select value={days} onChange={event => setDays(Number(event.target.value))}>
        {[7, 30, 90].map(value => <option key={value} value={value}>{t('work.rangeDays', { days: value })}</option>)}
      </select></label></div>
    {loading && <p role="status">{t('common.loading')}</p>}
    {failed && <p role="alert">{t('pilot.loadFailed')} <button className="pilot-button secondary" onClick={() => setAttempt(value => value + 1)}>{t('pilot.retry')}</button></p>}
    {dashboard && <>
      <div className="metrics-grid">{metrics.map(([key, value]) => <div className="metric-card" key={key}>
        <div className="metric-label">{t(`analytics.${key}`)}</div><div className="metric-value">{value}</div>
      </div>)}</div>
      {funnel && <section className="analytics-section"><h3>{t('analytics.funnel')}</h3>
        <dl className="privacy-facts">{[['registered', 'registered'], ['onboarding', 'completed_onboarding'], ['tracking', 'first_tracking'], ['chat', 'first_chat'], ['active', 'active_users']].map(([label, key]) =>
          <React.Fragment key={key}><dt>{t(`analytics.${label}`)}</dt><dd>{number(funnel[key])}</dd></React.Fragment>)}</dl>
      </section>}
      {dashboard.feature_usage && <section className="analytics-section"><h3>{t('analytics.features')}</h3>
        {Object.entries(dashboard.feature_usage).sort((a, b) => number(b[1]) - number(a[1])).slice(0, 10).map(([key, count]) =>
          <div className="feature-item" key={key}><span>{t(`analytics.featureNames.${key}`, { defaultValue: key })}</span><span>{number(count)}</span></div>)}
      </section>}
      {historical.length > 0 && <section className="analytics-section"><h3>{t('analytics.history')}</h3>
        <div className="historical-chart">{historical.map((point, index) => <div className="chart-bar" key={index}>
          <div className="bar-fill" style={{ height: `${Math.max(0, number(point.dau)) / maxDaily * 100}%` }} />
          <span className="bar-label">{number(point.dau)}</span><span className="bar-date">{String(point.date).slice(0, 10)}</span>
        </div>)}</div>
      </section>}
    </>}
  </section>
}
