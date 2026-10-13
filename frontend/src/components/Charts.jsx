import React, { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import api from '../utils/api'
import { japanDay, utcDate } from '../utils/japanTime'
import { useToast } from './Toast'
import { Calendar } from 'lucide-react'
import EmptyState from './EmptyState'
import './Charts.css'

function Charts({ userId, onRecord, refreshKey = 0, visible = true }) {
  const { t, i18n } = useTranslation()
  const toast = useToast()
  const [chartData, setChartData] = useState([])
  const [loading, setLoading] = useState(true)
  const [timeRange, setTimeRange] = useState(7) // days

  useEffect(() => {
    if (!visible) return
    let active = true
    const loadChartData = async () => {
      setLoading(true)
      try {
        const entries = await api.getTracking(userId, timeRange)
        if (active) setChartData(processDataForCharts(entries))
      } catch (error) {
        if (active) {
          console.error('Error loading chart data:', error)
          toast.error(t('pilot.loadFailed'))
        }
      } finally {
        if (active) setLoading(false)
      }
    }
    loadChartData()
    return () => { active = false }
  }, [userId, timeRange, refreshKey, visible])

  const processDataForCharts = (entries) => {
    // Enhanced data processing for better visualization
    const now = new Date()
    const last7Days = Array.from({ length: timeRange }, (_, i) => {
      return japanDay(new Date(now.getTime() - (timeRange - 1 - i) * 86400000))
    })
    
    // Group entries by date
    const groupedByDate = {}
    last7Days.forEach(date => {
      groupedByDate[date] = {
        date,
        feeding: 0,
        diaper: 0,
        mood: null,
        moodTimestamp: null,
        sleepDuration: 0,
      }
    })
    
    entries.forEach(entry => {
      const entryDate = japanDay(entry.timestamp)
      if (groupedByDate[entryDate]) {
        if (entry.entry_type === 'feeding') {
          groupedByDate[entryDate].feeding++
        } else if (entry.entry_type === 'diaper') {
          groupedByDate[entryDate].diaper++
        } else if (entry.entry_type === 'sleep') {
          groupedByDate[entryDate].sleepDuration += entry.sleep_duration_minutes || 0
        } else if (entry.entry_type === 'mood') {
          // Select by timestamp rather than relying on the API's record order.
          const moodMap = { 'very_low': 1, 'low': 2, 'neutral': 3, 'good': 4, 'very_good': 5 }
          const timestamp = utcDate(entry.timestamp).getTime()
          const day = groupedByDate[entryDate]
          if (day.moodTimestamp === null || timestamp > day.moodTimestamp) {
            day.mood = moodMap[entry.mood_level] ?? null
            day.moodTimestamp = timestamp
          }
        }
      }
    })
    
    return Object.values(groupedByDate)
      .sort((a, b) => new Date(a.date) - new Date(b.date))
      .map(day => ({
        date: new Date(`${day.date}T00:00:00+09:00`).toLocaleDateString(i18n.language, { timeZone: 'Asia/Tokyo', month: 'short', day: 'numeric' }),
        feeds: day.feeding,
        diapers: day.diaper,
        sleepMinutes: day.sleepDuration,
        mood: day.mood
      }))
  }


  if (loading) {
    return (
      <div className="charts-loading">
        <div className="spinner"></div>
        <p>{t('charts.loading')}</p>
      </div>
    )
  }

  if (chartData.length === 0 || chartData.every(day => day.feeds === 0 && day.diapers === 0 && day.sleepMinutes === 0 && day.mood === null)) {
    return (
      <EmptyState
        type="charts"
        onAction={onRecord}
      />
    )
  }

  return (
    <div className="charts-container">
      <div className="charts-header">
        <h2>📊 {t('charts.title')}</h2>
        <div className="time-range-selector">
          <Calendar size={18} />
          <select 
            value={timeRange} 
            onChange={(e) => setTimeRange(Number(e.target.value))}
            className="time-select"
          >
            <option value={3}>{t('charts.last3Days')}</option>
            <option value={7}>{t('charts.last7Days')}</option>
            <option value={14}>{t('charts.last2Weeks')}</option>
            <option value={30}>{t('charts.lastMonth')}</option>
          </select>
        </div>
      </div>

      <div className="charts-grid">
        <div className="chart-card">
          <h3>{t('charts.feedingFrequency')}</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="feeds" fill="#256354" name={t('charts.feedsPerDay')} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-card">
          <h3>{t('charts.diaperChanges')}</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="diapers" fill="#48bb78" name={t('charts.diaperChanges')} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-card">
          <h3>{t('charts.sleepDuration')}</h3>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line 
                type="monotone" 
                dataKey="sleepMinutes" 
                stroke="#ed8936" 
                strokeWidth={2}
                name={t('charts.sleepMinutes')}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-card">
          <h3>{t('charts.moodTrend')}</h3>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis domain={[1, 5]} />
              <Tooltip />
              <Legend />
              <Line 
                type="monotone" 
                dataKey="mood" 
                stroke="#f56565" 
                strokeWidth={2}
                name={t('charts.moodTrend')}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}

export default Charts
