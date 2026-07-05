import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import api from './utils/api'
import ChatInterface from './components/ChatInterface'
import TrackingPanel from './components/TrackingPanel'
import NightMode from './components/NightMode'
import EmotionalCheckIn from './components/EmotionalCheckIn'
import Dashboard from './components/Dashboard'
import Settings from './components/Settings'
import WelcomeScreen from './components/WelcomeScreen'
import OnboardingTutorial from './components/OnboardingTutorial'
import InstallPrompt from './components/InstallPrompt'
import LanguageSelector from './components/LanguageSelector'
import FeedbackWidget from './components/FeedbackWidget'
import Auth from './components/Auth'
import { Home, MessageCircle, BarChart3, Heart, Settings as SettingsIcon, Moon } from 'lucide-react'
import './App.css'

function App() {
  const { t } = useTranslation()
  const [activeTab, setActiveTab] = useState('dashboard')
  const [nightMode, setNightMode] = useState(false)
  const [showWelcome, setShowWelcome] = useState(false)
  const [showOnboarding, setShowOnboarding] = useState(false)
  const [userContext, setUserContext] = useState(null)
  const [authChecked, setAuthChecked] = useState(false)
  const [userId, setUserId] = useState(null)

  useEffect(() => {
    api.setOnUnauthorized(() => {
      setUserId(null)
      setAuthChecked(true)
    })
  }, [])

  useEffect(() => {
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/sw.js')
        .then((registration) => {
          console.log('Service Worker registered:', registration)
        })
        .catch((error) => {
          console.log('Service Worker registration failed:', error)
        })
    }
    if (!api.isAuthenticated()) {
      setUserId(null)
      setAuthChecked(true)
      return
    }
    const storedUserId = api.getUserId()
    if (storedUserId) {
      setUserId(storedUserId)
      setAuthChecked(true)
      return
    }
    api.getCurrentUser()
      .then((user) => {
        if (user?.user_id) {
          api.setUserId(user.user_id)
          setUserId(user.user_id)
        } else {
          setUserId(null)
        }
        setAuthChecked(true)
      })
      .catch(() => {
        api.logout()
        setUserId(null)
        setAuthChecked(true)
      })
  }, [])

  useEffect(() => {
    if (!userId) return
    const hasCompletedWelcome = localStorage.getItem('hasCompletedWelcome')
    const hasCompletedOnboarding = localStorage.getItem('onboarding_completed')
    if (!hasCompletedWelcome) {
      setShowWelcome(true)
    } else if (!hasCompletedOnboarding) {
      setShowOnboarding(true)
      loadUserContext()
    } else {
      loadUserContext()
    }
  }, [userId])

  useEffect(() => {
    const handleKeyDown = (e) => {
      // Skip if user is typing in input/textarea
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
        return
      }

      // Keyboard shortcuts
      if (e.key === '/' && !e.ctrlKey && !e.metaKey) {
        e.preventDefault()
        // Focus search if available
        const searchInput = document.querySelector('input[type="search"], input[placeholder*="Search"]')
        if (searchInput) {
          searchInput.focus()
        }
      } else if (e.key === '?' && !e.ctrlKey && !e.metaKey) {
        e.preventDefault()
        // Open help
        setActiveTab('settings')
        // Trigger help tab if available
        const helpButton = document.querySelector('[data-tab="help"]')
        if (helpButton) {
          helpButton.click()
        }
      } else if (e.key === 'Escape') {
        // Close modals
        const modals = document.querySelectorAll('.modal, .overlay')
        modals.forEach(modal => {
          if (modal.style.display !== 'none') {
            modal.style.display = 'none'
          }
        })
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  const loadUserContext = async () => {
    if (!userId) return
    try {
      const context = await api.getUserContext(userId)
      setUserContext(context)
    } catch (error) {
      console.error('Error loading context:', error)
    }
  }

  const handleWelcomeComplete = (formData) => {
    localStorage.setItem('hasCompletedWelcome', 'true')
    setUserContext(formData)
    setShowWelcome(false)
    api.updateUserContext(userId, formData).catch(console.error)
  }

  const handleContextUpdate = (newContext) => {
    setUserContext(newContext)
  }

  if (!authChecked) {
    return (
      <div className="app app-loading" style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <p>{t('auth.loggingIn', 'Loading...')}</p>
      </div>
    )
  }

  if (authChecked && !userId) {
    return <Auth onSuccess={(uid) => setUserId(uid)} />
  }

  if (showWelcome) {
    return <WelcomeScreen onComplete={handleWelcomeComplete} />
  }

  if (showOnboarding) {
    return <OnboardingTutorial onComplete={() => setShowOnboarding(false)} skipOnboarding={false} userId={userId} />
  }

  if (nightMode) {
    return <NightMode userId={userId} onExit={() => setNightMode(false)} />
  }

  const tabs = [
    { id: 'dashboard', label: t('nav.home'), icon: <Home size={20} /> },
    { id: 'chat', label: t('nav.chat'), icon: <MessageCircle size={20} /> },
    { id: 'tracking', label: t('nav.tracking'), icon: <BarChart3 size={20} /> },
    { id: 'checkin', label: t('nav.checkin'), icon: <Heart size={20} /> },
    { id: 'settings', label: t('nav.settings'), icon: <SettingsIcon size={20} /> }
  ]

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-content">
          <h1>🤱 {t('app.title')}</h1>
          <p className="tagline">{t('app.tagline')}</p>
        </div>
        <div className="header-actions">
          <LanguageSelector />
          <motion.button
            className="night-mode-btn"
            onClick={() => setNightMode(true)}
            title="Crisis Mode"
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            <Moon size={18} />
            {t('nightMode.title')}
          </motion.button>
        </div>
      </header>

      <nav className="tab-nav">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            className={activeTab === tab.id ? 'active' : ''}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.icon}
            <span>{tab.label}</span>
          </button>
        ))}
      </nav>

      <main className="app-main">
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.3 }}
          >
            {activeTab === 'dashboard' && (
              <Dashboard userId={userId} userContext={userContext} />
            )}
            {activeTab === 'chat' && <ChatInterface userId={userId} />}
            {activeTab === 'tracking' && <TrackingPanel userId={userId} />}
            {activeTab === 'checkin' && <EmotionalCheckIn userId={userId} />}
            {activeTab === 'settings' && (
              <Settings
                userId={userId}
                onContextUpdate={handleContextUpdate}
                onLogout={() => {
                  api.logout()
                  setUserId(null)
                }}
              />
            )}
          </motion.div>
        </AnimatePresence>
      </main>
      <InstallPrompt />
    </div>
  )
}

export default App
