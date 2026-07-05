import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../utils/api'
import './Auth.css'

function Auth({ onSuccess }) {
  const { t } = useTranslation()
  const [mode, setMode] = useState('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleLogin = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await api.login(email, password)
      const user = await api.getCurrentUser()
      if (user?.user_id) {
        api.setUserId(user.user_id)
        onSuccess(user.user_id)
      } else {
        setError(t('auth.errorGeneric'))
      }
    } catch (err) {
      const msg = err?.message || ''
      setError(msg.includes('Incorrect') || msg.includes('401') ? t('auth.errorInvalidCredentials') : (msg || t('auth.errorGeneric')))
    } finally {
      setLoading(false)
    }
  }

  const handleRegister = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await api.register(email, password)
      await api.login(email, password)
      const user = await api.getCurrentUser()
      if (user?.user_id) {
        api.setUserId(user.user_id)
        onSuccess(user.user_id)
      } else {
        setError(t('auth.errorGeneric'))
      }
    } catch (err) {
      const msg = err?.message || ''
      if (msg.includes('already exists') || msg.includes('400')) {
        setError(t('auth.errorEmailExists'))
      } else {
        setError(msg || t('auth.errorGeneric'))
      }
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = mode === 'login' ? handleLogin : handleRegister

  return (
    <div className="auth-screen">
      <div className="auth-container">
        <div className="auth-header">
          <h1>🤱 {t('app.title')}</h1>
          <p className="auth-subtitle">{t('auth.subtitle')}</p>
        </div>

        <div className="auth-tabs">
          <button
            type="button"
            className={mode === 'login' ? 'active' : ''}
            onClick={() => { setMode('login'); setError('') }}
          >
            {t('auth.login')}
          </button>
          <button
            type="button"
            className={mode === 'register' ? 'active' : ''}
            onClick={() => { setMode('register'); setError('') }}
          >
            {t('auth.register')}
          </button>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          <div className="auth-field">
            <label htmlFor="auth-email">{t('auth.email')}</label>
            <input
              id="auth-email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              disabled={loading}
            />
          </div>
          <div className="auth-field">
            <label htmlFor="auth-password">{t('auth.password')}</label>
            <input
              id="auth-password"
              type="password"
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
              disabled={loading}
            />
            {mode === 'register' && (
              <p className="auth-hint">{t('auth.passwordHint')}</p>
            )}
          </div>
          {error && <p className="auth-error">{error}</p>}
          <button type="submit" className="auth-submit" disabled={loading}>
            {loading
              ? (mode === 'login' ? t('auth.loggingIn') : t('auth.registering'))
              : (mode === 'login' ? t('auth.loginSubmit') : t('auth.registerSubmit'))}
          </button>
        </form>

        <p className="auth-switch">
          {mode === 'login' ? (
            <>
              {t('auth.switchToRegister')}{' '}
              <button type="button" className="auth-link" onClick={() => { setMode('register'); setError('') }}>
                {t('auth.register')}
              </button>
            </>
          ) : (
            <>
              {t('auth.switchToLogin')}{' '}
              <button type="button" className="auth-link" onClick={() => { setMode('login'); setError('') }}>
                {t('auth.login')}
              </button>
            </>
          )}
        </p>
      </div>
    </div>
  )
}

export default Auth
