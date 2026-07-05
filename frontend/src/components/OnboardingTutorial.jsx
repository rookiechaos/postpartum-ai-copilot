import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import { X, ChevronRight, CheckCircle, Circle, ArrowRight, ArrowLeft, MessageCircle, BarChart3, Heart, Moon, Settings, Bell, Users, CreditCard, Baby } from 'lucide-react'
import api from '../utils/api'
import errorTracker from '../utils/errorTracker'
import './OnboardingTutorial.css'

// Personalization Step Component
function PersonalizationStep({ data, onChange, t }) {
  const [formData, setFormData] = useState({
    babyAge: data.babyAge || '',
    birthType: data.birthType || '',
    feedingType: data.feedingType || '',
    babyName: data.babyName || ''
  })

  const handleChange = (field, value) => {
    const newData = { ...formData, [field]: value }
    setFormData(newData)
    onChange(newData)
  }

  return (
    <div className="onboarding-content">
      <Baby size={48} className="feature-icon" />
      <h3>{t('onboarding.personalization.title', 'Tell Us About Your Baby')}</h3>
      <p>{t('onboarding.personalization.description', 'This helps us personalize your experience and provide better recommendations.')}</p>
      
      <div className="personalization-form">
        <div className="form-group">
          <label>{t('onboarding.personalization.babyName', 'Baby\'s Name (Optional)')}</label>
          <input
            type="text"
            placeholder={t('onboarding.personalization.babyNamePlaceholder', 'e.g., Emma')}
            value={formData.babyName}
            onChange={(e) => handleChange('babyName', e.target.value)}
          />
        </div>
        
        <div className="form-group">
          <label>{t('onboarding.personalization.babyAge', 'Baby\'s Age')}</label>
          <select
            value={formData.babyAge}
            onChange={(e) => handleChange('babyAge', e.target.value)}
          >
            <option value="">{t('common.select', 'Select...')}</option>
            <option value="0-7">{t('onboarding.personalization.age0-7', '0-7 days')}</option>
            <option value="1-2">{t('onboarding.personalization.age1-2w', '1-2 weeks')}</option>
            <option value="2-4">{t('onboarding.personalization.age2-4w', '2-4 weeks')}</option>
            <option value="1-2m">{t('onboarding.personalization.age1-2m', '1-2 months')}</option>
            <option value="2-3m">{t('onboarding.personalization.age2-3m', '2-3 months')}</option>
            <option value="3+">{t('onboarding.personalization.age3+', '3+ months')}</option>
          </select>
        </div>
        
        <div className="form-group">
          <label>{t('onboarding.personalization.birthType', 'Birth Type')}</label>
          <select
            value={formData.birthType}
            onChange={(e) => handleChange('birthType', e.target.value)}
          >
            <option value="">{t('common.select', 'Select...')}</option>
            <option value="vaginal">{t('onboarding.personalization.vaginal', 'Vaginal Birth')}</option>
            <option value="c-section">{t('onboarding.personalization.csection', 'C-Section')}</option>
          </select>
        </div>
        
        <div className="form-group">
          <label>{t('onboarding.personalization.feedingType', 'Feeding Type')}</label>
          <select
            value={formData.feedingType}
            onChange={(e) => handleChange('feedingType', e.target.value)}
          >
            <option value="">{t('common.select', 'Select...')}</option>
            <option value="breast">{t('onboarding.personalization.breast', 'Breastfeeding')}</option>
            <option value="formula">{t('onboarding.personalization.formula', 'Formula')}</option>
            <option value="mixed">{t('onboarding.personalization.mixed', 'Mixed')}</option>
          </select>
        </div>
      </div>
      
      <div className="onboarding-tip">
        <strong>💡 {t('onboarding.personalization.tip', 'Tip')}:</strong> {t('onboarding.personalization.tipText', 'You can update this information later in Settings.')}
      </div>
    </div>
  )
}

function OnboardingTutorial({ onComplete, skipOnboarding, userId }) {
  const { t } = useTranslation()
  const [currentStep, setCurrentStep] = useState(0)
  const [completedSteps, setCompletedSteps] = useState(new Set())
  const [completedStepIds, setCompletedStepIds] = useState([])
  const [highlightedElement, setHighlightedElement] = useState(null)
  const [personalizationData, setPersonalizationData] = useState({})
  const [loading, setLoading] = useState(false)

  const steps = [
    {
      id: 'welcome',
      title: t('onboarding.welcome.title', 'Welcome to Postpartum AI Copilot'),
      description: t('onboarding.welcome.description', 'Your AI companion for the postpartum journey'),
      content: (
        <div className="onboarding-content">
          <div className="welcome-icon">🌟</div>
          <h3>{t('onboarding.welcome.mission', 'Our Mission')}</h3>
          <p>{t('onboarding.welcome.missionText', 'We provide empathetic, evidence-based support to help new mothers navigate the postpartum period with confidence and peace of mind.')}</p>
          <ul>
            <li>🤖 {t('onboarding.welcome.feature1', 'AI-powered chat assistant')}</li>
            <li>📊 {t('onboarding.welcome.feature2', 'Smart tracking and analytics')}</li>
            <li>🌙 {t('onboarding.welcome.feature3', 'Crisis support mode')}</li>
            <li>💚 {t('onboarding.welcome.feature4', 'Emotional wellbeing check-ins')}</li>
            <li>👨‍👩‍👧 {t('onboarding.welcome.feature5', 'Family sharing')}</li>
            <li>🔔 {t('onboarding.welcome.feature6', 'Smart notifications')}</li>
          </ul>
        </div>
      ),
      highlight: null
    },
    {
      id: 'personalization',
      title: t('onboarding.personalization.title', 'Personalize Your Experience'),
      description: t('onboarding.personalization.description', 'Help us customize the app for you'),
      content: (
        <PersonalizationStep
          data={personalizationData}
          onChange={handlePersonalizationChange}
          t={t}
        />
      ),
      highlight: null
    },
    {
      id: 'chat',
      title: t('onboarding.chat.title', 'AI Chat Assistant'),
      description: t('onboarding.chat.description', 'Get instant answers to your questions'),
      content: (
        <div className="onboarding-content">
          <MessageCircle size={48} className="feature-icon" />
          <h3>{t('onboarding.chat.howToUse', 'How to Use')}</h3>
          <ol>
            <li>{t('onboarding.chat.step1', 'Click the Chat tab in the navigation')}</li>
            <li>{t('onboarding.chat.step2', 'Type your question about postpartum care, baby care, or your wellbeing')}</li>
            <li>{t('onboarding.chat.step3', 'Get personalized, evidence-based responses')}</li>
            <li>{t('onboarding.chat.step4', 'AI will flag any red flags and recommend consulting healthcare providers when needed')}</li>
          </ol>
          <div className="onboarding-tip">
            <strong>💡 {t('onboarding.chat.tip', 'Tip')}:</strong> {t('onboarding.chat.tipText', 'The AI learns from your tracking data to provide more personalized advice.')}
          </div>
        </div>
      ),
      highlight: 'chat-tab'
    },
    {
      id: 'tracking',
      title: t('onboarding.tracking.title', 'Smart Tracking'),
      description: t('onboarding.tracking.description', 'Track feeding, sleep, diapers, and more'),
      content: (
        <div className="onboarding-content">
          <BarChart3 size={48} className="feature-icon" />
          <h3>{t('onboarding.tracking.whatToTrack', 'What You Can Track')}</h3>
          <ul>
            <li><strong>{t('onboarding.tracking.feeding', 'Feeding')}:</strong> {t('onboarding.tracking.feedingDesc', 'Type, duration, amount')}</li>
            <li><strong>{t('onboarding.tracking.diaper', 'Diapers')}:</strong> {t('onboarding.tracking.diaperDesc', 'Wet, dirty, or both')}</li>
            <li><strong>{t('onboarding.tracking.sleep', 'Sleep')}:</strong> {t('onboarding.tracking.sleepDesc', 'Duration and quality')}</li>
            <li><strong>{t('onboarding.tracking.mood', 'Mood')}:</strong> {t('onboarding.tracking.moodDesc', 'Your emotional state')}</li>
          </ul>
          <p>{t('onboarding.tracking.aiAnalysis', 'The AI analyzes your data to identify patterns and provide insights about what\'s normal for your baby\'s age.')}</p>
        </div>
      ),
      highlight: 'tracking-tab'
    },
    {
      id: 'night-mode',
      title: t('onboarding.nightMode.title', 'Crisis Support Mode'),
      description: t('onboarding.nightMode.description', 'One-tap urgent help'),
      content: (
        <div className="onboarding-content">
          <Moon size={48} className="feature-icon" />
          <h3>{t('onboarding.nightMode.whenToUse', 'When to Use Night Mode')}</h3>
          <ul>
            <li>{t('onboarding.nightMode.useCase1', 'You\'re overwhelmed and need immediate guidance')}</li>
            <li>{t('onboarding.nightMode.useCase2', 'Baby won\'t stop crying and you need quick help')}</li>
            <li>{t('onboarding.nightMode.useCase3', 'You need concise, actionable advice fast')}</li>
          </ul>
          <div className="onboarding-tip">
            <strong>⚠️ {t('onboarding.nightMode.emergency', 'Emergency')}:</strong> {t('onboarding.nightMode.emergencyText', 'For medical emergencies, always call emergency services immediately.')}
          </div>
        </div>
      ),
      highlight: 'night-mode-button'
    },
    {
      id: 'checkin',
      title: t('onboarding.checkin.title', 'Emotional Check-ins'),
      description: t('onboarding.checkin.description', 'Monitor your mental wellbeing'),
      content: (
        <div className="onboarding-content">
          <Heart size={48} className="feature-icon" />
          <h3>{t('onboarding.checkin.whyImportant', 'Why Regular Check-ins Matter')}</h3>
          <ul>
            <li>{t('onboarding.checkin.benefit1', 'Early detection of postpartum depression or anxiety')}</li>
            <li>{t('onboarding.checkin.benefit2', 'Personalized support and resources')}</li>
            <li>{t('onboarding.checkin.benefit3', 'Automatic escalation for high-risk situations')}</li>
          </ul>
          <p className="onboarding-note">
            💚 {t('onboarding.checkin.note', 'Your mental health matters. It\'s okay to ask for help.')}
          </p>
        </div>
      ),
      highlight: 'checkin-tab'
    },
    {
      id: 'notifications',
      title: t('onboarding.notifications.title', 'Smart Notifications'),
      description: t('onboarding.notifications.description', 'Never miss important reminders'),
      content: (
        <div className="onboarding-content">
          <Bell size={48} className="feature-icon" />
          <h3>{t('onboarding.notifications.features', 'Notification Features')}</h3>
          <ul>
            <li>{t('onboarding.notifications.feeding', 'Feeding reminders based on your patterns')}</li>
            <li>{t('onboarding.notifications.mood', 'Mood check-in reminders')}</li>
            <li>{t('onboarding.notifications.custom', 'Custom reminders for appointments or tasks')}</li>
          </ul>
          <p>{t('onboarding.notifications.smart', 'Notifications are smart - they learn from your usage patterns and adjust timing accordingly.')}</p>
        </div>
      ),
      highlight: 'settings-tab'
    },
    {
      id: 'family',
      title: t('onboarding.family.title', 'Family Sharing'),
      description: t('onboarding.family.description', 'Share data with family members'),
      content: (
        <div className="onboarding-content">
          <Users size={48} className="feature-icon" />
          <h3>{t('onboarding.family.howItWorks', 'How It Works')}</h3>
          <ol>
            <li>{t('onboarding.family.step1', 'Create a family group')}</li>
            <li>{t('onboarding.family.step2', 'Invite family members (partner, grandparents, etc.)')}</li>
            <li>{t('onboarding.family.step3', 'Share tracking data securely')}</li>
            <li>{t('onboarding.family.step4', 'Set role-based permissions')}</li>
          </ol>
          <p>{t('onboarding.family.privacy', 'All data sharing is secure and you control who can see what.')}</p>
        </div>
      ),
      highlight: null
    },
    {
      id: 'complete',
      title: t('onboarding.complete.title', 'You\'re All Set!'),
      description: t('onboarding.complete.description', 'Ready to start your journey'),
      content: (
        <div className="onboarding-content">
          <div className="complete-icon">🎉</div>
          <h3>{t('onboarding.complete.nextSteps', 'Next Steps')}</h3>
          <div className="next-steps">
            <div className="step-card">
              <CheckCircle size={24} />
              <div>
                <h4>{t('onboarding.complete.step1Title', '1. Start Tracking')}</h4>
                <p>{t('onboarding.complete.step1Desc', 'Begin tracking your baby\'s activities')}</p>
              </div>
            </div>
            <div className="step-card">
              <CheckCircle size={24} />
              <div>
                <h4>{t('onboarding.complete.step2Title', '2. Try the Chat')}</h4>
                <p>{t('onboarding.complete.step2Desc', 'Ask your first question to the AI assistant')}</p>
              </div>
            </div>
            <div className="step-card">
              <CheckCircle size={24} />
              <div>
                <h4>{t('onboarding.complete.step3Title', '3. Set Up Notifications')}</h4>
                <p>{t('onboarding.complete.step3Desc', 'Enable reminders in Settings')}</p>
              </div>
            </div>
          </div>
        </div>
      ),
      highlight: null
    }
  ]

  // Load existing progress on mount
  useEffect(() => {
    const loadProgress = async () => {
      if (!userId) return
      
      try {
        const response = await api.getOnboardingProgress()
        if (response.progress) {
          const progress = response.progress
          setCurrentStep(progress.current_step || 0)
          setCompletedStepIds(progress.completed_steps || [])
          if (progress.personalization_data) {
            setPersonalizationData(progress.personalization_data)
          }
          
          // If already completed and skipOnboarding is true, skip
          if (progress.is_completed && skipOnboarding) {
            onComplete()
            return
          }
        }
      } catch (error) {
        errorTracker.trackError(error, { action: 'load_onboarding_progress' })
        // Continue with default state if API fails
      }
    }
    
    loadProgress()
  }, [userId, onComplete, skipOnboarding])

  useEffect(() => {
    // Highlight elements when step changes
    if (steps[currentStep].highlight) {
      setHighlightedElement(steps[currentStep].highlight)
      // Scroll to element if it exists
      const element = document.querySelector(`[data-onboarding="${steps[currentStep].highlight}"]`)
      if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'center' })
      }
    } else {
      setHighlightedElement(null)
    }
  }, [currentStep])

  const handleNext = async () => {
    const newCompleted = new Set(completedSteps)
    newCompleted.add(currentStep)
    setCompletedSteps(newCompleted)
    
    const currentStepId = steps[currentStep].id
    const newCompletedStepIds = [...completedStepIds]
    if (!newCompletedStepIds.includes(currentStepId)) {
      newCompletedStepIds.push(currentStepId)
      setCompletedStepIds(newCompletedStepIds)
    }

    // Save progress to backend
    if (userId) {
      try {
        setLoading(true)
        await api.updateOnboardingProgress({
          current_step: currentStep + 1,
          completed_steps: newCompletedStepIds,
          personalization_data: personalizationData,
          is_completed: false,
          is_skipped: false
        })
        
        // Mark step as completed
        await api.markStepCompleted(currentStepId)
      } catch (error) {
        errorTracker.trackError(error, { action: 'save_onboarding_progress', step: currentStepId })
        // Continue even if API fails
      } finally {
        setLoading(false)
      }
    }

    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1)
    } else {
      handleComplete()
    }
  }

  const handlePrevious = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1)
    }
  }

  const handleComplete = async () => {
    // Save personalization data if we have it
    if (userId && Object.keys(personalizationData).length > 0) {
      try {
        await api.savePersonalizationData(personalizationData)
      } catch (error) {
        errorTracker.trackError(error, { action: 'save_personalization_data' })
      }
    }
    
    // Mark onboarding as completed
    if (userId) {
      try {
        await api.updateOnboardingProgress({
          current_step: steps.length - 1,
          completed_steps: [...completedStepIds, steps[currentStep].id],
          personalization_data: personalizationData,
          is_completed: true,
          is_skipped: false
        })
      } catch (error) {
        errorTracker.trackError(error, { action: 'complete_onboarding' })
      }
    }
    
    localStorage.setItem('onboarding_completed', 'true')
    localStorage.setItem('onboarding_completed_at', new Date().toISOString())
    onComplete()
  }

  const handleSkip = async () => {
    // Mark onboarding as skipped
    if (userId) {
      try {
        await api.updateOnboardingProgress({
          current_step: currentStep,
          completed_steps: completedStepIds,
          personalization_data: personalizationData,
          is_completed: false,
          is_skipped: true
        })
      } catch (error) {
        errorTracker.trackError(error, { action: 'skip_onboarding' })
      }
    }
    
    localStorage.setItem('onboarding_completed', 'true')
    localStorage.setItem('onboarding_skipped', 'true')
    onComplete()
  }
  
  const handlePersonalizationChange = async (data) => {
    setPersonalizationData(data)
    
    // Save personalization data as user types (debounced)
    if (userId && Object.keys(data).length > 0) {
      try {
        await api.savePersonalizationData(data)
      } catch (error) {
        errorTracker.trackError(error, { action: 'save_personalization_data_realtime' })
      }
    }
  }

  const progress = ((currentStep + 1) / steps.length) * 100

  return (
    <div className="onboarding-tutorial">
      <div className="onboarding-overlay" />
      <motion.div
        className="onboarding-modal"
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.9 }}
      >
        <div className="onboarding-header">
          <div className="onboarding-progress">
            <div className="progress-bar">
              <motion.div
                className="progress-fill"
                initial={{ width: 0 }}
                animate={{ width: `${progress}%` }}
                transition={{ duration: 0.3 }}
              />
            </div>
            <span className="progress-text">
              {currentStep + 1} / {steps.length}
            </span>
          </div>
          <button className="skip-button" onClick={handleSkip}>
            <X size={20} />
            {t('onboarding.skip', 'Skip')}
          </button>
        </div>

        <div className="onboarding-body">
          <AnimatePresence mode="wait">
            <motion.div
              key={currentStep}
              className="onboarding-step"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.3 }}
            >
              <h2>{steps[currentStep].title}</h2>
              <p className="step-description">{steps[currentStep].description}</p>
              <div className="step-content">
                {steps[currentStep].content}
              </div>
            </motion.div>
          </AnimatePresence>
        </div>

        <div className="onboarding-footer">
          <div className="step-indicators">
            {steps.map((_, index) => (
              <button
                key={index}
                className={`step-indicator ${index === currentStep ? 'active' : ''} ${completedSteps.has(index) ? 'completed' : ''}`}
                onClick={() => setCurrentStep(index)}
              >
                {completedSteps.has(index) ? (
                  <CheckCircle size={16} />
                ) : (
                  <Circle size={16} />
                )}
              </button>
            ))}
          </div>

          <div className="onboarding-actions">
            {currentStep > 0 && (
              <button className="btn-secondary" onClick={handlePrevious}>
                <ArrowLeft size={18} />
                {t('onboarding.previous', 'Previous')}
              </button>
            )}
            <button className="btn-primary" onClick={handleNext}>
              {currentStep === steps.length - 1 ? (
                <>
                  {t('onboarding.getStarted', 'Get Started')}
                  <CheckCircle size={18} />
                </>
              ) : (
                <>
                  {t('onboarding.next', 'Next')}
                  <ArrowRight size={18} />
                </>
              )}
            </button>
          </div>
        </div>
      </motion.div>

      {/* Highlight overlay for elements */}
      {highlightedElement && (
        <div
          className="onboarding-highlight"
          data-target={highlightedElement}
        />
      )}
    </div>
  )
}

export default OnboardingTutorial
