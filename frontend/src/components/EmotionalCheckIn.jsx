import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../utils/api'
import './EmotionalCheckIn.css'

function EmotionalCheckIn({ userId }) {
  const { t } = useTranslation()
  const [overwhelmed, setOverwhelmed] = useState(5)
  const [anxiety, setAnxiety] = useState(5)
  const [support, setSupport] = useState(5)
  const [notes, setNotes] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setResult(null)

    try {
      const data = await api.postEmotionalCheckin({
        user_id: userId,
        overwhelmed_level: overwhelmed,
        anxiety_level: anxiety,
        support_level: support,
        notes: notes,
        timestamp: new Date().toISOString()
      })
      setResult(data)
    } catch (error) {
      console.error('Check-in error:', error)
      toast.error(error?.message || 'Check-in failed. Please try again.')
      setResult({
        assessment: "Thank you for checking in. Remember, it's okay to ask for help.",
        risk_level: "low",
        suggestions: ["Consider reaching out to a support person", "Contact your healthcare provider if concerns persist"],
        escalation_needed: false,
        resources: ["Postpartum Support International", "National Suicide Prevention Lifeline"]
      })
    } finally {
      setLoading(false)
    }
  }

  const getRiskColor = (riskLevel) => {
    switch (riskLevel) {
      case 'high': return '#ff4444'
      case 'medium': return '#ffaa00'
      case 'low': return '#44aa44'
      default: return '#999'
    }
  }

  return (
    <div className="emotional-checkin">
      <div className="checkin-container">
        <h2>💚 Emotional Check-in</h2>
        <p className="checkin-subtitle">
          How are you feeling today? This is a safe space to check in with yourself.
        </p>

        <form onSubmit={handleSubmit} className="checkin-form">
          <div className="slider-group">
            <label>
              How overwhelmed do you feel? ({overwhelmed}/10)
            </label>
            <input
              type="range"
              min="1"
              max="10"
              value={overwhelmed}
              onChange={(e) => setOverwhelmed(parseInt(e.target.value))}
              className="slider"
            />
            <div className="slider-labels">
              <span>Not at all</span>
              <span>Extremely</span>
            </div>
          </div>

          <div className="slider-group">
            <label>
              How anxious do you feel? ({anxiety}/10)
            </label>
            <input
              type="range"
              min="1"
              max="10"
              value={anxiety}
              onChange={(e) => setAnxiety(parseInt(e.target.value))}
              className="slider"
            />
            <div className="slider-labels">
              <span>Not at all</span>
              <span>Extremely</span>
            </div>
          </div>

          <div className="slider-group">
            <label>
              How supported do you feel? ({support}/10)
            </label>
            <input
              type="range"
              min="1"
              max="10"
              value={support}
              onChange={(e) => setSupport(parseInt(e.target.value))}
              className="slider"
            />
            <div className="slider-labels">
              <span>Not at all</span>
              <span>Very supported</span>
            </div>
          </div>

          <div className="form-group">
            <label>Anything else you'd like to share? (optional)</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows="4"
              placeholder="Share what's on your mind..."
              className="notes-input"
            />
          </div>

          <button type="submit" disabled={loading} className="submit-button">
            {loading ? 'Processing...' : 'Check In'}
          </button>
        </form>

        {result && (
          <div className="checkin-result">
            <p className="checkin-disclaimer">{t('checkin.disclaimerNonClinical')}</p>
            <div 
              className="risk-badge"
              style={{ backgroundColor: getRiskColor(result.risk_level) }}
            >
              Risk Level: {result.risk_level.toUpperCase()}
            </div>

            <div className="assessment">
              <h3>Assessment</h3>
              <p>{result.assessment}</p>
            </div>

            {result.suggestions && result.suggestions.length > 0 && (
              <div className="suggestions">
                <h3>Suggestions</h3>
                <ul>
                  {result.suggestions.map((suggestion, i) => (
                    <li key={i}>{suggestion}</li>
                  ))}
                </ul>
              </div>
            )}

            {result.escalation_needed && (
              <div className="escalation-warning">
                <strong>⚠️ Important:</strong>
                <p>Based on your responses, we recommend reaching out to a healthcare professional or mental health provider. You don't have to go through this alone.</p>
              </div>
            )}

            {result.resources && result.resources.length > 0 && (
              <div className="resources">
                <h3>Resources</h3>
                <ul>
                  {result.resources.map((resource, i) => (
                    <li key={i}>{resource}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        <div className="safety-note">
          <p>
            <strong>Remember:</strong> This is not a substitute for professional mental health care. 
            If you're experiencing thoughts of self-harm or harm to your baby, please contact emergency services immediately.
          </p>
        </div>
      </div>
    </div>
  )
}

export default EmotionalCheckIn
