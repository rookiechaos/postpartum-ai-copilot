import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import './WelcomeScreen.css'

function WelcomeScreen({ onComplete }) {
  const { t } = useTranslation()
  const [step, setStep] = useState(0)
  const [formData, setFormData] = useState({
    babyAge: '',
    birthType: '',
    feedingType: '',
    babyName: ''
  })

  const steps = [
    {
      title: t('welcome.title'),
      subtitle: t('welcome.subtitle'),
      content: (
        <div className="welcome-content">
          <p>{t('welcome.description')}</p>
          <ul>
            <li>🤖 {t('welcome.feature1')}</li>
            <li>📊 {t('welcome.feature2')}</li>
            <li>🌙 {t('welcome.feature3')}</li>
            <li>💚 {t('welcome.feature4')}</li>
          </ul>
        </div>
      )
    },
    {
      title: t('welcome.step2Title'),
      subtitle: t('welcome.step2Subtitle'),
      content: (
        <div className="form-content">
          <div className="form-group">
            <label>{t('welcome.babyName')}</label>
            <input
              type="text"
              placeholder="e.g., Emma"
              value={formData.babyName}
              onChange={(e) => setFormData({ ...formData, babyName: e.target.value })}
            />
          </div>
          <div className="form-group">
            <label>{t('welcome.babyAge')}</label>
            <select
              value={formData.babyAge}
              onChange={(e) => setFormData({ ...formData, babyAge: e.target.value })}
            >
              <option value="">{t('common.select')}</option>
              <option value="0-7">0-7 days</option>
              <option value="1-2">1-2 weeks</option>
              <option value="2-4">2-4 weeks</option>
              <option value="1-2m">1-2 months</option>
              <option value="2-3m">2-3 months</option>
              <option value="3+">3+ months</option>
            </select>
          </div>
          <div className="form-group">
            <label>{t('welcome.birthType')}</label>
            <select
              value={formData.birthType}
              onChange={(e) => setFormData({ ...formData, birthType: e.target.value })}
            >
              <option value="">{t('common.select')}</option>
              <option value="vaginal">Vaginal Birth</option>
              <option value="c-section">C-Section</option>
            </select>
          </div>
          <div className="form-group">
            <label>{t('welcome.feedingType')}</label>
            <select
              value={formData.feedingType}
              onChange={(e) => setFormData({ ...formData, feedingType: e.target.value })}
            >
              <option value="">{t('common.select')}</option>
              <option value="breast">Breastfeeding</option>
              <option value="formula">Formula</option>
              <option value="mixed">Mixed</option>
            </select>
          </div>
        </div>
      )
    },
    {
      title: t('welcome.step3Title'),
      subtitle: t('welcome.step3Subtitle'),
      content: (
        <div className="welcome-content">
          <p>We're ready to support you. Remember:</p>
          <ul>
            <li>{t('welcome.step3Note1')}</li>
            <li>{t('welcome.step3Note2')}</li>
            <li>{t('welcome.step3Note3')}</li>
            <li>{t('welcome.step3Note4')}</li>
          </ul>
        </div>
      )
    }
  ]

  const handleNext = () => {
    if (step < steps.length - 1) {
      setStep(step + 1)
    } else {
      onComplete(formData)
    }
  }

  const handleSkip = () => {
    onComplete(formData)
  }

  return (
    <motion.div
      className="welcome-screen"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
    >
      <div className="welcome-container">
        <div className="welcome-header">
          <h1>{steps[step].title}</h1>
          <p className="subtitle">{steps[step].subtitle}</p>
        </div>

        <motion.div
          key={step}
          className="welcome-body"
          initial={{ x: 20, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: -20, opacity: 0 }}
          transition={{ duration: 0.3 }}
        >
          {steps[step].content}
        </motion.div>

        <div className="welcome-footer">
          <div className="progress-dots">
            {steps.map((_, index) => (
              <div
                key={index}
                className={`dot ${index === step ? 'active' : ''} ${index < step ? 'completed' : ''}`}
              />
            ))}
          </div>

          <div className="welcome-actions">
            {step > 0 && (
              <button
                className="btn-secondary"
                onClick={() => setStep(step - 1)}
              >
                {t('welcome.back')}
              </button>
            )}
            {step < steps.length - 1 ? (
              <button
                className="btn-primary"
                onClick={handleNext}
                disabled={step === 1 && !formData.babyAge}
              >
                {t('welcome.next')}
              </button>
            ) : (
              <button
                className="btn-primary"
                onClick={handleNext}
              >
                {t('welcome.getStarted')}
              </button>
            )}
            {step > 0 && (
              <button
                className="btn-link"
                onClick={handleSkip}
              >
                {t('welcome.skip')}
              </button>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  )
}

export default WelcomeScreen
