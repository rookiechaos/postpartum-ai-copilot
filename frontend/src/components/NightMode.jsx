import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../utils/api'
import AIUseNotice from './AIUseNotice'
import SupportDirectory from './SupportDirectory'
import './NightMode.css'

function NightMode({ userId, onExit }) {
  const [acceptedAI, setAcceptedAI] = useState(false)
  const { t, i18n } = useTranslation()
  const [query, setQuery] = useState('')
  const [response, setResponse] = useState(null)
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('help') // 'help', 'relaxation', 'breathing', 'safety'
  const [relaxationGuide, setRelaxationGuide] = useState(null)
  const [breathingExercise, setBreathingExercise] = useState(null)
  const [safetyTips, setSafetyTips] = useState(null)

  const quickActions = [
    t('nightMode.babyCrying'),
    t('nightMode.babyWontSleep'),
    t('nightMode.isThisNormal'),
    t('nightMode.feedingConcerns'),
    t('nightMode.overwhelmed')
  ]

  const handleQuickAction = (action) => {
    setQuery(action)
  }

  const handleCrisis = async (crisisQuery = null) => {
    const queryToSend = crisisQuery || query
    if (!queryToSend.trim() || !acceptedAI || loading) return

    setLoading(true)
    setResponse(null)

    try {
      const result = await api.postCrisis({
        user_id: userId,
        query: queryToSend,
        urgency: 'high',
        language: i18n.language
      })

      setResponse(result.error ? { response: t('pilot.nightUnavailable'), actions: [], red_flags: [] } : { ...result, generated: true })
      setQuery('')
    } catch (error) {
      console.error('Crisis mode error:', error)
      setResponse({
        response: t('pilot.nightUnavailable'),
        actions: [],
        red_flags: []
      })
    } finally {
      setLoading(false)
    }
  }

  const loadRelaxationGuide = async () => {
    if (!acceptedAI || loading) return
    setLoading(true)
    try {
      const result = await api.getNightModeRelaxation(i18n.language)
      setRelaxationGuide(result?.guide ?? result)
      setActiveTab('relaxation')
    } catch (error) {
      console.error('Error loading relaxation guide:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadBreathingExercise = async () => {
    if (!acceptedAI || loading) return
    setLoading(true)
    try {
      const result = await api.getNightModeBreathing(i18n.language)
      setBreathingExercise(result?.exercise ?? result)
      setActiveTab('breathing')
    } catch (error) {
      console.error('Error loading breathing exercise:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadSafetyTips = async () => {
    setLoading(true)
    try {
      const result = await api.getNightModeSafetyTips(i18n.language)
      setSafetyTips(result)
      setActiveTab('safety')
    } catch (error) {
      console.error('Error loading safety tips:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="night-mode">
      <div className="night-mode-container">
        <button className="exit-button" onClick={onExit}>
          ✕ {t('nightMode.exit')}
        </button>

        <div className="night-mode-header">
          <h1>🌙 {t('nightMode.title')}</h1>
          <p>{t('nightMode.subtitle')}</p>
        </div>

        <SupportDirectory compact />
        <AIUseNotice accepted={acceptedAI} onChange={setAcceptedAI} />

        <div className="night-mode-tabs">
          <button
            className={activeTab === 'help' ? 'active' : ''}
            onClick={() => setActiveTab('help')}
          >
            💬 {t('pilot.nightHelp')}
          </button>
          <button
            className={activeTab === 'relaxation' ? 'active' : ''}
            onClick={loadRelaxationGuide}
            disabled={!acceptedAI || loading}
          >
            🧘 {t('pilot.relaxation')}
          </button>
          <button
            className={activeTab === 'breathing' ? 'active' : ''}
            onClick={loadBreathingExercise}
            disabled={!acceptedAI || loading}
          >
            🌬️ {t('pilot.breathing')}
          </button>
          <button
            className={activeTab === 'safety' ? 'active' : ''}
            onClick={loadSafetyTips}
          >
            ⚠️ {t('pilot.safety')}
          </button>
        </div>

        {activeTab === 'relaxation' && relaxationGuide && (
          <div className="relaxation-guide">
            <h3>{relaxationGuide.title}</h3>
            <p className="duration">{t('tracking.duration')}: {relaxationGuide.duration}</p>
            <ol className="relaxation-steps">
              {relaxationGuide.steps.map((step, i) => (
                <li key={i}>{step}</li>
              ))}
            </ol>
          </div>
        )}

        {activeTab === 'breathing' && breathingExercise && (
          <div className="breathing-exercise">
            <h3>{breathingExercise.name}</h3>
            <p className="description">{breathingExercise.description}</p>
            <p className="benefits">{breathingExercise.benefits}</p>
            <ol className="breathing-steps">
              {breathingExercise.steps.map((step, i) => (
                <li key={i}>{step}</li>
              ))}
            </ol>
          </div>
        )}

        {activeTab === 'safety' && safetyTips && (
          <div className="safety-tips">
            <h3>{t('pilot.safety')}</h3>
            <p className="emergency-message">{safetyTips.emergency_message}</p>
            <ul className="safety-tips-list">
              {safetyTips.tips.map((tip, i) => (
                <li key={i}>{tip}</li>
              ))}
            </ul>
          </div>
        )}

        {activeTab === 'help' && (
          <>
        <div className="quick-actions">
          <p>{t('nightMode.quickHelp')}</p>
          <div className="quick-buttons">
            {quickActions.map((action, idx) => (
              <button
                key={idx}
                onClick={() => handleQuickAction(action)}
                className="quick-action-btn"
                disabled={loading}
              >
                {action}
              </button>
            ))}
          </div>
        </div>

        <div className="crisis-input">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleCrisis()}
            placeholder={t('nightMode.placeholder')}
            disabled={loading}
            className="crisis-input-field"
          />
          <button
            onClick={() => handleCrisis()}
            disabled={loading || !query.trim() || !acceptedAI}
            className="crisis-submit-btn"
          >
            {loading ? t('nightMode.gettingHelp') : t('nightMode.getHelp')}
          </button>
        </div>

        {loading && (
          <div className="crisis-loading">
            <div className="spinner"></div>
            <p>{t('nightMode.gettingHelp')}</p>
          </div>
        )}

        {response && (
          <div className="crisis-response">
            <div className="response-text">
              {response.response}
              {response.generated && <p>{t('pilot.aiLabel')}</p>}
            </div>

            {response.actions && response.actions.length > 0 && (
              <div className="response-actions">
                <strong>{t('nightMode.tryThis')}</strong>
                <ul>
                  {response.actions.map((action, i) => (
                    <li key={i}>{action}</li>
                  ))}
                </ul>
              </div>
            )}

            {response.red_flags && response.red_flags.length > 0 && (
              <div className="response-red-flags">
                <strong>⚠️ {t('chat.important')}</strong>
                <ul>
                  {response.red_flags.map((flag, i) => (
                    <li key={i}>{flag}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        <div className="emergency-info">
          <p><strong>{t('nightMode.emergency')}</strong> {t('nightMode.emergencyText')}</p>
        </div>
          </>
        )}
      </div>
    </div>
  )
}

export default NightMode
