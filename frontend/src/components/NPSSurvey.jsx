import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { X, Star, MessageSquare } from 'lucide-react'
import api from '../utils/api'
import errorTracker from '../utils/errorTracker'
import './NPSSurvey.css'

function NPSSurvey({ onClose, userId, context = null }) {
  const { t } = useTranslation()
  const [score, setScore] = useState(null)
  const [comment, setComment] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async () => {
    if (score === null) return

    setLoading(true)
    try {
      await api.submitNPSSurvey(score, comment || null, context)
      setSubmitted(true)
      
      // Store last survey date
      localStorage.setItem('last_nps_survey', new Date().toISOString())
      
      setTimeout(() => {
        onClose()
      }, 2000)
    } catch (error) {
      errorTracker.trackError(error, { action: 'submit_nps_survey' })
    } finally {
      setLoading(false)
    }
  }

  if (submitted) {
    return (
      <div className="nps-survey-modal">
        <div className="nps-survey-content">
          <div className="nps-success">
            <Star size={48} className="success-icon" />
            <h3>{t('nps.thankYou', 'Thank You!')}</h3>
            <p>{t('nps.feedbackReceived', 'Your feedback has been received. We appreciate your input!')}</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="nps-survey-modal">
      <div className="nps-survey-content">
        <button className="nps-close-button" onClick={onClose}>
          <X size={20} />
        </button>

        <div className="nps-header">
          <h2>{t('nps.title', 'How likely are you to recommend us?')}</h2>
          <p>{t('nps.description', 'Your feedback helps us improve')}</p>
        </div>

        <div className="nps-score-selector">
          <div className="nps-scale">
            <span className="nps-label">{t('nps.notLikely', 'Not Likely')}</span>
            <div className="nps-buttons">
              {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((value) => (
                <button
                  key={value}
                  className={`nps-button ${score === value ? 'selected' : ''}`}
                  onClick={() => setScore(value)}
                >
                  {value}
                </button>
              ))}
            </div>
            <span className="nps-label">{t('nps.veryLikely', 'Very Likely')}</span>
          </div>
        </div>

        {score !== null && (
          <div className="nps-followup">
            <div className="nps-category">
              {score >= 9 && (
                <p className="nps-category-text promoter">
                  {t('nps.promoter', '🎉 Promoter - Thank you for your support!')}
                </p>
              )}
              {score >= 7 && score <= 8 && (
                <p className="nps-category-text passive">
                  {t('nps.passive', '👍 Passive - We\'d love to improve. What can we do better?')}
                </p>
              )}
              {score <= 6 && (
                <p className="nps-category-text detractor">
                  {t('nps.detractor', '💬 Detractor - We\'re sorry to hear that. Please tell us more.')}
                </p>
              )}
            </div>

            <div className="nps-comment-section">
              <label>
                <MessageSquare size={18} />
                {t('nps.commentLabel', 'Tell us more (optional)')}
              </label>
              <textarea
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder={t('nps.commentPlaceholder', 'Share your thoughts...')}
                rows={4}
                maxLength={1000}
              />
              <span className="nps-char-count">{comment.length}/1000</span>
            </div>
          </div>
        )}

        <div className="nps-actions">
          <button
            className="nps-submit-button btn-primary"
            onClick={handleSubmit}
            disabled={score === null || loading}
          >
            {loading ? t('nps.submitting', 'Submitting...') : t('nps.submit', 'Submit')}
          </button>
          <button className="nps-skip-button" onClick={onClose}>
            {t('nps.skip', 'Skip')}
          </button>
        </div>
      </div>
    </div>
  )
}

export default NPSSurvey
