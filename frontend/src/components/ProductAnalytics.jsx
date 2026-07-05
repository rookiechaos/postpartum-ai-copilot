import React, { useState, useEffect } from 'react'
import { BarChart3, Users, TrendingUp, Activity, ArrowUp, ArrowDown } from 'lucide-react'
import api from '../utils/api'
import './ProductAnalytics.css'

function ProductAnalytics({ userId }) {
  const [dashboard, setDashboard] = useState(null)
  const [loading, setLoading] = useState(true)
  const [days, setDays] = useState(30)

  useEffect(() => {
    loadDashboard()
  }, [days])

  const loadDashboard = async () => {
    setLoading(true)
    try {
      const data = await api.getProductDashboard(days)
      setDashboard(data)
    } catch (error) {
      console.error('Failed to load dashboard:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="product-analytics">
        <div className="loading">Loading analytics...</div>
      </div>
    )
  }

  if (!dashboard) {
    return (
      <div className="product-analytics">
        <div className="error">Failed to load analytics</div>
      </div>
    )
  }

  const { current, conversion_funnel, feature_usage, retention, historical } = dashboard

  return (
    <div className="product-analytics">
      <div className="analytics-header">
        <h2>📊 Product Analytics Dashboard</h2>
        <select value={days} onChange={(e) => setDays(Number(e.target.value))} className="days-select">
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
        </select>
      </div>

      <div className="metrics-grid">
        <div className="metric-card">
          <div className="metric-header">
            <Users size={24} />
            <span>DAU</span>
          </div>
          <div className="metric-value">{current.dau}</div>
          <div className="metric-label">Daily Active Users</div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <Users size={24} />
            <span>MAU</span>
          </div>
          <div className="metric-value">{current.mau}</div>
          <div className="metric-label">Monthly Active Users</div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <TrendingUp size={24} />
            <span>DAU/MAU</span>
          </div>
          <div className="metric-value">{current.dau_mau_ratio.toFixed(1)}%</div>
          <div className="metric-label">Engagement Ratio</div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <Activity size={24} />
            <span>Retention</span>
          </div>
          <div className="metric-value">{(retention.day_7 || 0).toFixed(1)}%</div>
          <div className="metric-label">7-Day Retention</div>
        </div>
      </div>

      {conversion_funnel && (
        <div className="analytics-section">
          <h3>Conversion Funnel</h3>
          <div className="funnel">
            <div className="funnel-step">
              <div className="funnel-bar" style={{ width: '100%' }}>
                <span>Registered: {conversion_funnel.registered}</span>
              </div>
            </div>
            <div className="funnel-step">
              <div className="funnel-bar" style={{ width: `${(conversion_funnel.onboarding_rate || 0)}%` }}>
                <span>Onboarding: {conversion_funnel.completed_onboarding || 0} ({(conversion_funnel.onboarding_rate || 0).toFixed(1)}%)</span>
              </div>
            </div>
            <div className="funnel-step">
              <div className="funnel-bar" style={{ width: `${(conversion_funnel.tracking_rate || 0)}%` }}>
                <span>First Tracking: {conversion_funnel.first_tracking || 0} ({(conversion_funnel.tracking_rate || 0).toFixed(1)}%)</span>
              </div>
            </div>
            <div className="funnel-step">
              <div className="funnel-bar" style={{ width: `${(conversion_funnel.chat_rate || 0)}%` }}>
                <span>First Chat: {conversion_funnel.first_chat || 0} ({(conversion_funnel.chat_rate || 0).toFixed(1)}%)</span>
              </div>
            </div>
            <div className="funnel-step">
              <div className="funnel-bar" style={{ width: `${(conversion_funnel.activation_rate || 0)}%` }}>
                <span>Active Users: {conversion_funnel.active_users || 0} ({(conversion_funnel.activation_rate || 0).toFixed(1)}%)</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {feature_usage && Object.keys(feature_usage).length > 0 && (
        <div className="analytics-section">
          <h3>Feature Usage</h3>
          <div className="feature-usage-list">
            {Object.entries(feature_usage)
              .sort((a, b) => b[1] - a[1])
              .slice(0, 10)
              .map(([feature, count]) => (
                <div key={feature} className="feature-item">
                  <span className="feature-name">{feature}</span>
                  <span className="feature-count">{count}</span>
                </div>
              ))}
          </div>
        </div>
      )}

      {historical && historical.length > 0 && (
        <div className="analytics-section">
          <h3>Historical Trends</h3>
          <div className="historical-chart">
            {historical.map((point, index) => (
              <div key={index} className="chart-bar">
                <div className="bar-fill" style={{ height: `${(point.dau / Math.max(...historical.map(h => h.dau))) * 100}%` }} />
                <span className="bar-label">{point.dau}</span>
                <span className="bar-date">{new Date(point.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default ProductAnalytics
