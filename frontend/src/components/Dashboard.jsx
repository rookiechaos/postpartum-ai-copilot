import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import api from '../utils/api'
import { useToast } from './Toast'
import { Baby, Moon, Heart, TrendingUp, Clock, Droplet } from 'lucide-react'
import Skeleton from './Skeleton'
import EmptyState from './EmptyState'
import './Dashboard.css'

function Dashboard({ userId, userContext }) {
  const { t } = useTranslation()
  const toast = useToast()
  const [stats, setStats] = useState({
    todayFeeds: 0,
    todayDiapers: 0,
    avgSleep: 0,
    moodTrend: 'stable'
  })
  const [loading, setLoading] = useState(true)
  const [dailySummary, setDailySummary] = useState(null)
  const [weeklySummary, setWeeklySummary] = useState(null)
  const [summaryLoading, setSummaryLoading] = useState(false)

  useEffect(() => {
    loadStats()
    loadSummaries()
  }, [userId])
  
  const loadSummaries = async () => {
    setSummaryLoading(true)
    try {
      const [dailyRes, weeklyRes] = await Promise.all([
        api.getDailySummary(userId).catch(() => null),
        api.getWeeklySummary(userId).catch(() => null)
      ])
      if (dailyRes) setDailySummary(dailyRes)
      if (weeklyRes) setWeeklySummary(weeklyRes)
    } catch (error) {
      console.error('Error loading summaries:', error)
    } finally {
      setSummaryLoading(false)
    }
  }

  const loadStats = async () => {
    try {
      const entries = await api.getTracking(userId, 1)
      
      const feeds = entries.filter(e => e.entry_type === 'feeding').length
      const diapers = entries.filter(e => e.entry_type === 'diaper').length
      const sleepEntries = entries.filter(e => e.entry_type === 'sleep')
      const avgSleep = sleepEntries.length > 0
        ? Math.round(sleepEntries.reduce((sum, e) => sum + (e.sleep_duration_minutes || 0), 0) / sleepEntries.length)
        : 0

      setStats({
        todayFeeds: feeds,
        todayDiapers: diapers,
        avgSleep: avgSleep,
        moodTrend: 'stable'
      })
    } catch (error) {
      console.error('Error loading stats:', error)
      toast.error(error?.message || 'Failed to load stats')
    } finally {
      setLoading(false)
    }
  }

  const statCards = [
    {
      icon: <Baby size={24} />,
      label: t('dashboard.todayFeeds'),
      value: stats.todayFeeds,
      color: "#667eea"
    },
    {
      icon: <Droplet size={24} />,
      label: t('dashboard.diaperChanges'),
      value: stats.todayDiapers,
      color: "#48bb78"
    },
    {
      icon: <Clock size={24} />,
      label: t('dashboard.avgSleep'),
      value: stats.avgSleep,
      color: "#ed8936"
    },
    {
      icon: <TrendingUp size={24} />,
      label: t('dashboard.moodTrend'),
      value: stats.moodTrend,
      color: "#f56565"
    }
  ]

  const quickActions = [
    { icon: <Baby />, label: t('dashboard.logFeeding'), action: "feeding", onClick: () => {} },
    { icon: <Droplet />, label: t('dashboard.diaperChange'), action: "diaper", onClick: () => {} },
    { icon: <Clock />, label: t('dashboard.sleep'), action: "sleep", onClick: () => {} },
    { icon: <Heart />, label: t('dashboard.mood'), action: "mood", onClick: () => {} }
  ]

  if (loading) {
    return (
      <div className="dashboard">
        <div className="stats-grid">
          <Skeleton.Stat />
          <Skeleton.Stat />
          <Skeleton.Stat />
          <Skeleton.Stat />
        </div>
      </div>
    )
  }

  // Check if there's no data
  const hasNoData = stats.todayFeeds === 0 && stats.todayDiapers === 0 && stats.avgSleep === 0

  if (hasNoData) {
    return (
      <div className="dashboard">
        <div className="dashboard-header">
          <div>
            <h2>{t('dashboard.welcome')}</h2>
            {userContext?.babyName && (
              <p className="baby-name">{t('dashboard.howIsBaby', { name: userContext.babyName })}</p>
            )}
          </div>
        </div>
        <EmptyState
          type="dashboard"
          onAction={() => {
            // Navigate to tracking tab
            const event = new CustomEvent('navigate', { detail: { tab: 'tracking' } })
            window.dispatchEvent(event)
          }}
        />
      </div>
    )
  }

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <div>
          <h2>{t('dashboard.welcome')}</h2>
          {userContext?.babyName && (
            <p className="baby-name">{t('dashboard.howIsBaby', { name: userContext.babyName })}</p>
          )}
        </div>
        <motion.button
          className="night-mode-button"
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          <Moon size={20} />
          {t('nightMode.title')}
        </motion.button>
      </div>

      <div className="stats-grid">
        {statCards.map((card, index) => (
          <motion.div
            key={index}
            className="stat-card"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
          >
            <div className="stat-icon" style={{ color: card.color }}>
              {card.icon}
            </div>
            <div className="stat-content">
              <div className="stat-value">{card.value}</div>
              <div className="stat-label">{card.label}</div>
            </div>
          </motion.div>
        ))}
      </div>

      <div className="quick-actions-section">
        <h3>{t('dashboard.quickActions')}</h3>
        <div className="quick-actions-grid">
          {quickActions.map((action, index) => (
            <motion.button
              key={index}
              className="quick-action-card"
              onClick={action.onClick}
              whileHover={{ scale: 1.05, y: -5 }}
              whileTap={{ scale: 0.95 }}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 + index * 0.1 }}
            >
              <div className="quick-action-icon">{action.icon}</div>
              <div className="quick-action-label">{action.label}</div>
            </motion.button>
          ))}
        </div>
      </div>

      <div className="insights-section">
        <h3>{t('dashboard.insights')}</h3>
        <div className="insight-card">
          <p>💡 {t('dashboard.insightText')}</p>
          <p className="insight-subtext">{t('dashboard.insightSubtext')}</p>
        </div>
      </div>

      {(dailySummary || weeklySummary) && (
        <div className="summary-section">
          <h3>AI Summaries</h3>
          <div className="summary-grid">
            {dailySummary && (
              <motion.div
                className="summary-card"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.6 }}
              >
                <h4>📅 Daily Summary</h4>
                <p className="summary-date">{new Date(dailySummary.date).toLocaleDateString()}</p>
                <p className="summary-text">{dailySummary.summary}</p>
                <p className="summary-meta">{dailySummary.entries_count} entries tracked</p>
              </motion.div>
            )}
            {weeklySummary && (
              <motion.div
                className="summary-card"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.7 }}
              >
                <h4>📊 Weekly Summary</h4>
                <p className="summary-date">Week of {new Date(weeklySummary.week_start).toLocaleDateString()}</p>
                <p className="summary-text">{weeklySummary.summary}</p>
                <p className="summary-meta">{weeklySummary.entries_count} entries tracked</p>
              </motion.div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default Dashboard
