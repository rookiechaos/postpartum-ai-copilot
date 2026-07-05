import React, { useState, useEffect } from 'react'
import api from '../utils/api'
import EmptyState from './EmptyState'
import Charts from './Charts'
import { useToast } from './Toast'
import './TrackingPanel.css'

function TrackingPanel({ userId }) {
  const toast = useToast()
  const [entries, setEntries] = useState([])
  const [summary, setSummary] = useState(null)
  const [showAddForm, setShowAddForm] = useState(false)
  const [entryType, setEntryType] = useState('feeding')
  const [loading, setLoading] = useState(false)
  const [showCharts, setShowCharts] = useState(false)

  useEffect(() => {
    loadEntries()
    loadSummary()
  }, [userId])

  const loadEntries = async () => {
    try {
      const data = await api.getTracking(userId, 7)
      setEntries(data)
    } catch (error) {
      console.error('Error loading entries:', error)
    }
  }

  const loadSummary = async () => {
    try {
      const data = await api.getTrackingSummary(userId, 7)
      setSummary(data)
    } catch (error) {
      console.error('Error loading summary:', error)
    }
  }

  const addEntry = async (formData) => {
    setLoading(true)
    try {
      await api.addTrackingEntry({ user_id: userId, ...formData })
      await loadEntries()
      await loadSummary()
      setShowAddForm(false)
      toast.success('Entry added successfully!')
    } catch (error) {
      console.error('Error adding entry:', error)
      toast.error(error?.message || 'Failed to add entry. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="tracking-panel">
      <div className="tracking-header">
        <h2>Smart Tracking</h2>
        <div className="tracking-actions">
          <button 
            onClick={() => setShowCharts(!showCharts)} 
            className="charts-button"
          >
            {showCharts ? '📊 Hide Charts' : '📈 Show Charts'}
          </button>
          <button onClick={() => setShowAddForm(!showAddForm)} className="add-button">
            + Add Entry
          </button>
        </div>
      </div>

      {showCharts && <Charts userId={userId} />}

      {showAddForm && (
        <EntryForm
          entryType={entryType}
          onEntryTypeChange={setEntryType}
          onSubmit={addEntry}
          onCancel={() => setShowAddForm(false)}
          loading={loading}
        />
      )}

      {summary && (
        <div className="ai-summary">
          <h3>AI Insights</h3>
          {summary.patterns && summary.patterns.length > 0 && (
            <div className="summary-section">
              <strong>Patterns:</strong>
              <ul>
                {summary.patterns.map((pattern, i) => (
                  <li key={i}>{pattern}</li>
                ))}
              </ul>
            </div>
          )}
          {summary.insights && summary.insights.length > 0 && (
            <div className="summary-section">
              <strong>Insights:</strong>
              <ul>
                {summary.insights.map((insight, i) => (
                  <li key={i}>{insight}</li>
                ))}
              </ul>
            </div>
          )}
          {summary.recommendations && summary.recommendations.length > 0 && (
            <div className="summary-section">
              <strong>Recommendations:</strong>
              <ul>
                {summary.recommendations.map((rec, i) => (
                  <li key={i}>{rec}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      <div className="entries-list">
        <h3>Recent Entries</h3>
        {entries.length === 0 && !showAddForm ? (
          <EmptyState
            type="tracking"
            onAction={() => setShowAddForm(true)}
          />
        ) : entries.length === 0 ? null : (
          entries.map((entry) => (
            <div key={entry.id} className="entry-card">
              <div className="entry-header">
                <span className="entry-type">{entry.entry_type}</span>
                <span className="entry-time">
                  {new Date(entry.timestamp).toLocaleString()}
                </span>
              </div>
              <div className="entry-details">
                {entry.feeding_type && <span>Type: {entry.feeding_type}</span>}
                {entry.duration_minutes && <span>Duration: {entry.duration_minutes} min</span>}
                {entry.amount_ml && <span>Amount: {entry.amount_ml} ml</span>}
                {entry.diaper_type && <span>Type: {entry.diaper_type}</span>}
                {entry.sleep_duration_minutes && (
                  <span>Sleep: {entry.sleep_duration_minutes} min</span>
                )}
                {entry.mood_level && <span>Mood: {entry.mood_level}</span>}
                {entry.weight_kg && <span>Weight: {entry.weight_kg} kg</span>}
                {entry.breast_condition && <span>Breast: {entry.breast_condition}</span>}
              </div>
              {entry.notes && <p className="entry-notes">{entry.notes}</p>}
              {entry.recovery_notes && <p className="entry-notes">Recovery: {entry.recovery_notes}</p>}
            </div>
          ))
        )}
      </div>
    </div>
  )
}

function EntryForm({ entryType, onEntryTypeChange, onSubmit, onCancel, loading }) {
  const [formData, setFormData] = useState({})

  const handleSubmit = (e) => {
    e.preventDefault()
    onSubmit({
      entry_type: entryType,
      ...formData,
      timestamp: new Date().toISOString()
    })
    setFormData({})
  }

  return (
    <form className="entry-form" onSubmit={handleSubmit}>
      <div className="form-group">
        <label>Entry Type</label>
        <select value={entryType} onChange={(e) => onEntryTypeChange(e.target.value)}>
          <option value="feeding">Feeding</option>
          <option value="diaper">Diaper</option>
          <option value="sleep">Sleep</option>
          <option value="mood">Mood</option>
          <option value="pumping">Pumping</option>
          <option value="recovery">Recovery</option>
        </select>
      </div>

      {entryType === 'feeding' && (
        <>
          <div className="form-group">
            <label>Feeding Type</label>
            <select
              value={formData.feeding_type || ''}
              onChange={(e) => setFormData({ ...formData, feeding_type: e.target.value })}
            >
              <option value="">Select...</option>
              <option value="breast">Breast</option>
              <option value="formula">Formula</option>
              <option value="mixed">Mixed</option>
            </select>
          </div>
          <div className="form-group">
            <label>Duration (minutes)</label>
            <input
              type="number"
              value={formData.duration_minutes || ''}
              onChange={(e) => setFormData({ ...formData, duration_minutes: parseInt(e.target.value) })}
            />
          </div>
          <div className="form-group">
            <label>Amount (ml)</label>
            <input
              type="number"
              value={formData.amount_ml || ''}
              onChange={(e) => setFormData({ ...formData, amount_ml: parseFloat(e.target.value) })}
            />
          </div>
        </>
      )}

      {entryType === 'diaper' && (
        <div className="form-group">
          <label>Diaper Type</label>
          <select
            value={formData.diaper_type || ''}
            onChange={(e) => setFormData({ ...formData, diaper_type: e.target.value })}
          >
            <option value="">Select...</option>
            <option value="wet">Wet</option>
            <option value="dirty">Dirty</option>
            <option value="both">Both</option>
          </select>
        </div>
      )}

      {entryType === 'sleep' && (
        <>
          <div className="form-group">
            <label>Duration (minutes)</label>
            <input
              type="number"
              value={formData.sleep_duration_minutes || ''}
              onChange={(e) => setFormData({ ...formData, sleep_duration_minutes: parseInt(e.target.value) })}
            />
          </div>
          <div className="form-group">
            <label>Quality</label>
            <select
              value={formData.sleep_quality || ''}
              onChange={(e) => setFormData({ ...formData, sleep_quality: e.target.value })}
            >
              <option value="">Select...</option>
              <option value="peaceful">Peaceful</option>
              <option value="restless">Restless</option>
              <option value="interrupted">Interrupted</option>
            </select>
          </div>
        </>
      )}

      {entryType === 'mood' && (
        <>
          <div className="form-group">
            <label>Mood Level</label>
            <select
              value={formData.mood_level || ''}
              onChange={(e) => setFormData({ ...formData, mood_level: e.target.value })}
            >
              <option value="">Select...</option>
              <option value="very_low">Very Low</option>
              <option value="low">Low</option>
              <option value="neutral">Neutral</option>
              <option value="good">Good</option>
              <option value="very_good">Very Good</option>
            </select>
          </div>
          <div className="form-group">
            <label>Notes</label>
            <textarea
              value={formData.mood_notes || ''}
              onChange={(e) => setFormData({ ...formData, mood_notes: e.target.value })}
              rows="3"
            />
          </div>
        </>
      )}

      {entryType === 'recovery' && (
        <>
          <div className="form-group">
            <label>Weight (kg)</label>
            <input
              type="number"
              step="0.1"
              value={formData.weight_kg || ''}
              onChange={(e) => setFormData({ ...formData, weight_kg: parseFloat(e.target.value) })}
              placeholder="Enter your weight"
            />
          </div>
          <div className="form-group">
            <label>Breast Condition</label>
            <select
              value={formData.breast_condition || ''}
              onChange={(e) => setFormData({ ...formData, breast_condition: e.target.value })}
            >
              <option value="">Select...</option>
              <option value="normal">Normal</option>
              <option value="engorged">Engorged</option>
              <option value="blocked">Blocked</option>
              <option value="painful">Painful</option>
              <option value="other">Other</option>
            </select>
          </div>
          <div className="form-group">
            <label>Recovery Notes</label>
            <textarea
              value={formData.recovery_notes || ''}
              onChange={(e) => setFormData({ ...formData, recovery_notes: e.target.value })}
              rows="3"
              placeholder="Pain, bleeding, discomfort, etc."
            />
          </div>
        </>
      )}

      <div className="form-group">
        <label>Notes (optional)</label>
        <textarea
          value={formData.notes || ''}
          onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
          rows="2"
        />
      </div>

      <div className="form-actions">
        <button type="button" onClick={onCancel} disabled={loading}>
          Cancel
        </button>
        <button type="submit" disabled={loading}>
          {loading ? 'Adding...' : 'Add Entry'}
        </button>
      </div>
    </form>
  )
}

export default TrackingPanel
