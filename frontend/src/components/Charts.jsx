import React, { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import api from '../utils/api'
import { useToast } from './Toast'
import { Calendar, TrendingUp } from 'lucide-react'
import EmptyState from './EmptyState'
import './Charts.css'

function Charts({ userId }) {
  const toast = useToast()
  const [chartData, setChartData] = useState([])
  const [loading, setLoading] = useState(true)
  const [timeRange, setTimeRange] = useState(7) // days

  useEffect(() => {
    loadChartData()
  }, [userId, timeRange])

  const loadChartData = async () => {
    setLoading(true)
    try {
      const entries = await api.getTracking(userId, timeRange)
      // Process data for charts
      const processed = processDataForCharts(entries)
      setChartData(processed)
    } catch (error) {
      console.error('Error loading chart data:', error)
      toast.error(error?.message || 'Failed to load chart data')
    } finally {
      setLoading(false)
    }
  }

  const processDataForCharts = (entries) => {
    // Enhanced data processing for better visualization
    const now = new Date()
    const last7Days = Array.from({ length: 7 }, (_, i) => {
      const date = new Date(now)
      date.setDate(date.getDate() - (6 - i))
      return date.toISOString().split('T')[0]
    })
    
    // Group entries by date
    const groupedByDate = {}
    last7Days.forEach(date => {
      groupedByDate[date] = {
        date,
        feeding: 0,
        diaper: 0,
        sleep: 0,
        mood: null,
        sleepDuration: 0,
        sleepCount: 0
      }
    })
    
    entries.forEach(entry => {
      const entryDate = new Date(entry.timestamp).toISOString().split('T')[0]
      if (groupedByDate[entryDate]) {
        if (entry.entry_type === 'feeding') {
          groupedByDate[entryDate].feeding++
        } else if (entry.entry_type === 'diaper') {
          groupedByDate[entryDate].diaper++
        } else if (entry.entry_type === 'sleep') {
          groupedByDate[entryDate].sleep++
          groupedByDate[entryDate].sleepDuration += entry.sleep_duration_minutes || 0
          groupedByDate[entryDate].sleepCount++
        } else if (entry.entry_type === 'mood') {
          // Convert mood level to number for chart
          const moodMap = { 'very_low': 1, 'low': 2, 'neutral': 3, 'good': 4, 'very_good': 5 }
          groupedByDate[entryDate].mood = moodMap[entry.mood_level] || 3
        }
      }
    })
    
    // Calculate average sleep duration
    Object.values(groupedByDate).forEach(day => {
      if (day.sleepCount > 0) {
        day.sleepDuration = Math.round(day.sleepDuration / day.sleepCount)
      }
    })
    
    return Object.values(groupedByDate)
      .sort((a, b) => new Date(a.date) - new Date(b.date))
      .map(day => ({
        date: new Date(day.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
        feeds: day.feeding,
        diapers: day.diaper,
        sleepMinutes: day.sleepDuration,
        mood: day.mood || 3
      }))
  }


  if (loading) {
    return (
      <div className="charts-loading">
        <div className="spinner"></div>
        <p>Loading charts...</p>
      </div>
    )
  }

  if (chartData.length === 0 || chartData.every(day => day.feeds === 0 && day.diapers === 0 && day.sleepMinutes === 0)) {
    return (
      <EmptyState
        type="charts"
        onAction={() => {
          // Navigate to tracking tab
          const event = new CustomEvent('navigate', { detail: { tab: 'tracking' } })
          window.dispatchEvent(event)
        }}
      />
    )
  }

  return (
    <div className="charts-container">
      <div className="charts-header">
        <h2>📊 Trends & Analytics</h2>
        <div className="time-range-selector">
          <Calendar size={18} />
          <select 
            value={timeRange} 
            onChange={(e) => setTimeRange(Number(e.target.value))}
            className="time-select"
          >
            <option value={3}>Last 3 days</option>
            <option value={7}>Last 7 days</option>
            <option value={14}>Last 2 weeks</option>
            <option value={30}>Last month</option>
          </select>
        </div>
      </div>

      <div className="charts-grid">
        <div className="chart-card">
          <h3>Feeding Frequency</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="feeds" fill="#667eea" name="Feeds per day" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-card">
          <h3>Diaper Changes</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="diapers" fill="#48bb78" name="Diaper changes" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-card">
          <h3>Sleep Duration</h3>
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
                name="Sleep (minutes)"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-card">
          <h3>Mood Trend</h3>
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
                name="Mood (1-5)"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}

export default Charts
