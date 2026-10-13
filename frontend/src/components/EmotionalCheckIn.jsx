import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../utils/api'
import { useToast } from './Toast'
import AIUseNotice from './AIUseNotice'
import SupportDirectory from './SupportDirectory'
import './EmotionalCheckIn.css'

function EmotionalCheckIn({ userId }) {
  const { t, i18n } = useTranslation()
  const toast = useToast()
  const [overwhelmed, setOverwhelmed] = useState(5)
  const [anxiety, setAnxiety] = useState(5)
  const [support, setSupport] = useState(5)
  const [notes, setNotes] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [acceptedAI, setAcceptedAI] = useState(false)
  const [includeHistory, setIncludeHistory] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!acceptedAI || loading) return
    setLoading(true)
    setResult(null)

    try {
      const data = await api.postEmotionalCheckin({
        user_id: userId,
        include_history: includeHistory,
        language: i18n.resolvedLanguage || i18n.language,
        overwhelmed_level: overwhelmed,
        anxiety_level: anxiety,
        support_level: support,
        notes: notes,
        timestamp: new Date().toISOString()
      })
      setResult(data)
    } catch (error) {
      console.error('Check-in error:', error)
      toast.error(t('pilot.chatUnavailable'))
      setResult({
        assessment: t('pilot.checkinUnavailable'),
        risk_level: 'unknown',
        analysis_available: false,
        suggestions: [],
        escalation_needed: null,
        resources: []
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="emotional-checkin">
      <div className="checkin-container">
        <h2>💚 {t('checkin.title')}</h2>
        <p className="checkin-subtitle">
          {t('checkin.subtitle')}
        </p>

        <form onSubmit={handleSubmit} className="checkin-form">
          <div className="slider-group">
            <label>
              {t('checkin.overwhelmed')} ({overwhelmed}/10)
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
              <span>{t('checkin.notAtAll')}</span>
              <span>{t('checkin.extremely')}</span>
            </div>
          </div>

          <div className="slider-group">
            <label>
              {t('checkin.anxiety')} ({anxiety}/10)
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
              <span>{t('checkin.notAtAll')}</span>
              <span>{t('checkin.extremely')}</span>
            </div>
          </div>

          <div className="slider-group">
            <label>
              {t('checkin.support')} ({support}/10)
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
              <span>{t('checkin.notAtAll')}</span>
              <span>{t('checkin.verySupported')}</span>
            </div>
          </div>

          <div className="form-group">
            <label>{t('checkin.share')}</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows="4"
              placeholder={t('checkin.sharePlaceholder')}
              className="notes-input"
            />
          </div>

          <AIUseNotice scope="checkin" accepted={acceptedAI} onChange={setAcceptedAI} disabled={loading}
            includeHistory={includeHistory} onHistoryChange={setIncludeHistory} />
          <button type="submit" disabled={loading || !acceptedAI} className="submit-button">
            {t(loading ? 'checkin.processing' : 'checkin.checkIn')}
          </button>
        </form>

        {result && (
          <div className="checkin-result">
            <p className="checkin-disclaimer">{t('checkin.disclaimerNonClinical')}</p>
            {result.analysis_available !== true && (
              <div role="status">
                <p>{t('pilot.checkinUnavailable')}</p>
                <button type="button" onClick={handleSubmit} disabled={loading}>{t('pilot.retry')}</button>
              </div>
            )}

            <div className="assessment">
              <h3>{t('checkin.assessment')}</h3>
              {result.analysis_available === true && <p>{t('pilot.aiLabel')}</p>}
              <p>{result.assessment}</p>
            </div>

            {result.suggestions && result.suggestions.length > 0 && (
              <div className="suggestions">
                <h3>{t('checkin.suggestions')}</h3>
                <ul>
                  {result.suggestions.map((suggestion, i) => (
                    <li key={i}>{suggestion}</li>
                  ))}
                </ul>
              </div>
            )}

            {result.escalation_needed && (
              <div className="escalation-warning">
                <strong>⚠️ {t('chat.important')}</strong>
                <p>{t('pilot.reachOut')}</p>
              </div>
            )}

            {result.resources && result.resources.length > 0 && (
              <div className="resources">
                <h3>{t('checkin.resources')}</h3>
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
            {t('checkin.safetyNote')}
          </p>
        </div>
        <SupportDirectory compact />
      </div>
    </div>
  )
}

export default EmotionalCheckIn
