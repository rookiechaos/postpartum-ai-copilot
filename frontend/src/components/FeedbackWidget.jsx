import React, { useState, useEffect } from 'react'
import { MessageSquare, X, Star, ThumbsUp, ThumbsDown, Send, CheckCircle } from 'lucide-react'
import api from '../utils/api'
import errorTracker from '../utils/errorTracker'
import NPSSurvey from './NPSSurvey'
import './FeedbackWidget.css'

function FeedbackWidget({ userId }) {
  const [isOpen, setIsOpen] = useState(false)
  const [feedbackType, setFeedbackType] = useState(null) // 'quick', 'nps', 'satisfaction', 'feature'
  const [rating, setRating] = useState(0)
  const [npsScore, setNpsScore] = useState(null)
  const [comment, setComment] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [showNpsSurvey, setShowNpsSurvey] = useState(false)

  useEffect(() => {
    // Check if NPS survey should be shown (e.g., after 7 days of usage)
    const lastNpsDate = localStorage.getItem('last_nps_survey')
    const daysSinceLastNps = lastNpsDate
      ? (Date.now() - new Date(lastNpsDate).getTime()) / (1000 * 60 * 60 * 24)
      : Infinity

    // Show NPS survey if it's been more than 30 days since last survey
    if (daysSinceLastNps > 30) {
      setShowNpsSurvey(true)
    }
  }, [])

  const handleQuickFeedback = async (isPositive) => {
    try {
      await api.createFeedbackAutoClassify(
        isPositive ? 'Positive Feedback' : 'Issue Report',
        isPositive ? 'User found the app helpful' : 'User reported an issue',
        null, // Auto-classify
        'low'
      )
      setSubmitted(true)
      setTimeout(() => {
        setIsOpen(false)
        setSubmitted(false)
        setFeedbackType(null)
      }, 2000)
    } catch (error) {
      errorTracker.trackError(error, { action: 'quick_feedback' })
    }
  }

  const handleNpsSubmit = async () => {
    if (npsScore === null) return

    try {
      await api.submitNPSSurvey(npsScore, comment || null, {
        page: window.location.pathname,
        timestamp: new Date().toISOString()
      })
      localStorage.setItem('last_nps_survey', new Date().toISOString())
      setSubmitted(true)
      setShowNpsSurvey(false)
      setTimeout(() => {
        setIsOpen(false)
        setSubmitted(false)
        setFeedbackType(null)
        setNpsScore(null)
        setComment('')
      }, 2000)
    } catch (error) {
      errorTracker.trackError(error, { action: 'submit_nps' })
    }
  }

  const handleSatisfactionSubmit = async () => {
    if (rating === 0) return

    try {
      await api.post('/api/feedback', {
        category: 'other',
        title: 'Satisfaction Survey',
        message: `Rating: ${rating}/5${comment ? `\nComment: ${comment}` : ''}`,
        metadata: {
          satisfaction_rating: rating,
          survey_type: 'satisfaction'
        }
      })
      setSubmitted(true)
      setTimeout(() => {
        setIsOpen(false)
        setSubmitted(false)
        setFeedbackType(null)
        setRating(0)
        setComment('')
      }, 2000)
    } catch (error) {
      console.error('Failed to submit satisfaction:', error)
    }
  }

  const handleFeatureRequest = async () => {
    if (!comment.trim()) return

    try {
      // Extract feature name from comment (first line or first 50 chars)
      const lines = comment.trim().split('\n')
      const featureName = lines[0].substring(0, 50) || 'Feature Request'
      const description = comment.trim()

      await api.createFeatureRequest(featureName, description, 'user_request')
      setSubmitted(true)
      setTimeout(() => {
        setIsOpen(false)
        setSubmitted(false)
        setFeedbackType(null)
        setComment('')
      }, 2000)
    } catch (error) {
      errorTracker.trackError(error, { action: 'submit_feature_request' })
    }
  }

  if (isOpen && showNpsSurvey && !feedbackType) {
    return (
      <NPSSurvey
        onClose={() => {
          setIsOpen(false)
          setShowNpsSurvey(false)
        }}
        userId={userId}
        context={{
          page: window.location.pathname,
          timestamp: new Date().toISOString()
        }}
      />
    )
  }

  if (!isOpen) {
    return (
      <button
        className="feedback-button"
        onClick={() => setIsOpen(true)}
        title="Give Feedback"
      >
        <MessageSquare size={24} />
      </button>
    )
  }

  return (
    <div className="feedback-widget">
      <div className="feedback-modal">
        <button className="close-button" onClick={() => setIsOpen(false)}>
          <X size={20} />
        </button>

        {!feedbackType ? (
          <div className="feedback-options">
            <h3>How can we help?</h3>
            <div className="option-buttons">
              <button
                className="option-button"
                onClick={() => setFeedbackType('quick')}
              >
                <ThumbsUp size={24} />
                <span>Quick Feedback</span>
              </button>
              <button
                className="option-button"
                onClick={() => setFeedbackType('satisfaction')}
              >
                <Star size={24} />
                <span>Rate Your Experience</span>
              </button>
              <button
                className="option-button"
                onClick={() => setFeedbackType('feature')}
              >
                <MessageSquare size={24} />
                <span>Request a Feature</span>
              </button>
              <button
                className="option-button"
                onClick={() => {
                  setFeedbackType('nps')
                  setShowNpsSurvey(true)
                }}
              >
                <Star size={24} />
                <span>NPS Survey</span>
              </button>
            </div>
          </div>
        ) : feedbackType === 'quick' ? (
          <div className="feedback-form">
            <h3>Quick Feedback</h3>
            <p>How was your experience?</p>
            <div className="quick-feedback-buttons">
              <button
                className="quick-btn positive"
                onClick={() => handleQuickFeedback(true)}
                disabled={submitted}
              >
                <ThumbsUp size={24} />
                <span>Good</span>
              </button>
              <button
                className="quick-btn negative"
                onClick={() => handleQuickFeedback(false)}
                disabled={submitted}
              >
                <ThumbsDown size={24} />
                <span>Issue</span>
              </button>
            </div>
            {submitted && (
              <div className="success-message">
                <CheckCircle size={20} />
                <span>Thank you for your feedback!</span>
              </div>
            )}
          </div>
        ) : feedbackType === 'satisfaction' ? (
          <div className="feedback-form">
            <h3>Rate Your Experience</h3>
            <p>How satisfied are you with the app?</p>
            <div className="rating-buttons">
              {[1, 2, 3, 4, 5].map(star => (
                <button
                  key={star}
                  className={`rating-star ${rating >= star ? 'active' : ''}`}
                  onClick={() => setRating(star)}
                >
                  <Star size={32} fill={rating >= star ? '#fbbf24' : 'none'} />
                </button>
              ))}
            </div>
            <textarea
              placeholder="Tell us more (optional)..."
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              className="feedback-textarea"
              rows={4}
            />
            <button
              className="submit-button"
              onClick={handleSatisfactionSubmit}
              disabled={rating === 0 || submitted}
            >
              {submitted ? (
                <>
                  <CheckCircle size={18} />
                  Thank you!
                </>
              ) : (
                <>
                  <Send size={18} />
                  Submit
                </>
              )}
            </button>
          </div>
        ) : feedbackType === 'feature' ? (
          <div className="feedback-form">
            <h3>Request a Feature</h3>
            <p>What feature would you like to see?</p>
            <textarea
              placeholder="Describe the feature you'd like..."
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              className="feedback-textarea"
              rows={6}
              required
            />
            <button
              className="submit-button"
              onClick={handleFeatureRequest}
              disabled={!comment.trim() || submitted}
            >
              {submitted ? (
                <>
                  <CheckCircle size={18} />
                  Thank you!
                </>
              ) : (
                <>
                  <Send size={18} />
                  Submit Request
                </>
              )}
            </button>
          </div>
        ) : feedbackType === 'nps' ? (
          <NPSSurvey
            onClose={() => {
              setIsOpen(false)
              setFeedbackType(null)
            }}
            userId={userId}
            context={{
              page: window.location.pathname,
              timestamp: new Date().toISOString()
            }}
          />
        ) : null}

        {feedbackType && !submitted && (
          <button
            className="back-button"
            onClick={() => {
              setFeedbackType(null)
              setRating(0)
              setNpsScore(null)
              setComment('')
            }}
          >
            ← Back
          </button>
        )}
      </div>
    </div>
  )
}

export default FeedbackWidget
