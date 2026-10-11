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
import EntryScreen from './components/EntryScreen'
import OrganizationPortal from './components/OrganizationPortal'
import SupportDirectory from './components/SupportDirectory'
import ShareSummary from './components/ShareSummary'
import InstallPrompt from './components/InstallPrompt'
import LanguageSelector from './components/LanguageSelector'
import FeedbackWidget from './components/FeedbackWidget'
import Auth from './components/Auth'
import { Home, MessageCircle, BarChart3, Phone, Settings as SettingsIcon, Moon } from 'lucide-react'
import './App.css'
import './components/Pilot.css'

function App() {
  const { t } = useTranslation()
  const [authChecked, setAuthChecked] = useState(false)
  const [userId, setUserId] = useState(null)
  const [sessionKey, setSessionKey] = useState(0)
  const [entry, setEntry] = useState(() => {
    const path = window.location?.pathname
    return path === '/family' ? 'family' : path === '/organization' ? 'organization' : null
  })

  const chooseEntry = value => {
    window.history.pushState({}, '', value ? `/${value}` : '/')
    setEntry(value)
  }

  useEffect(() => {
    const onPopState = () => {
      const path = window.location.pathname
      setEntry(path === '/family' ? 'family' : path === '/organization' ? 'organization' : null)
    }
    window.addEventListener('popstate', onPopState)
    return () => window.removeEventListener('popstate', onPopState)
  }, [])

  useEffect(() => {
    let active = true
    let generation = 0
    const clearAccount = () => {
      generation++
      if (!active) return
      setUserId(null)
      setSessionKey(key => key + 1)
      setAuthChecked(true)
    }
    const unsubscribe = api.onAuthChange(({ preserveTasks }) => {
      if (!preserveTasks) clearAccount()
    })
    api.setOnUnauthorized(clearAccount)

    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/sw.js').catch(error => {
        console.error('Service Worker registration failed:', error)
      })
    }

    const initialize = async () => {
      const initialGeneration = generation
      if (!api.isAuthenticated()) {
        setAuthChecked(true)
        return
      }
      const storedUserId = api.getUserId()
      if (storedUserId) {
        setUserId(storedUserId)
        setAuthChecked(true)
        return
      }
      try {
        const user = await api.getCurrentUser()
        if (!active || generation !== initialGeneration) return
        api.setUserId(user?.user_id || null)
        setUserId(user?.user_id || null)
        setAuthChecked(true)
      } catch {
        if (active && generation === initialGeneration) api.logout()
      }
    }
    initialize()
    return () => {
      active = false
      unsubscribe()
      api.setOnUnauthorized(null)
    }
  }, [])

  if (!authChecked) {
    return (
      <div className="app app-loading" style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <p>{t('auth.loggingIn', 'Loading...')}</p>
      </div>
    )
  }
  if (!entry) return <EntryScreen onChoose={chooseEntry} />
  if (!userId) return <Auth entry={entry} onBack={() => chooseEntry(null)} onSuccess={setUserId} />
  if (entry === 'organization') return <OrganizationPortal key={`${sessionKey}:${userId}:organization`}
    userId={userId} onFamily={() => chooseEntry('family')} onExit={() => chooseEntry(null)} />
  return <AuthenticatedApp key={`${sessionKey}:${userId}:family`} userId={userId} onChooseEntry={chooseEntry} />
}

// A new login mounts fresh private state, including all child components.
function AuthenticatedApp({ userId, onChooseEntry }) {
  const { t, i18n } = useTranslation()
  const [activeTab, setActiveTab] = useState('dashboard')
  const [nightMode, setNightMode] = useState(false)
  const [showWelcome, setShowWelcome] = useState(false)
  const [userContext, setUserContext] = useState(null)
  const [trackingRequest, setTrackingRequest] = useState(null)
  const [chatDraft, setChatDraft] = useState('')

  useEffect(() => {
    let active = true
    const welcomeCompleted = localStorage.getItem(`hasCompletedWelcome:${userId}`)
    setShowWelcome(!welcomeCompleted)
    if (welcomeCompleted) {
      api.getUserContext(userId).then(context => {
        if (active) setUserContext(context)
      }).catch(error => {
        if (active) console.error('Error loading context:', error)
      })
    }
    return () => { active = false }
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

  const handleWelcomeComplete = async (formData) => {
    const saved = await api.updateUserContext(userId, { ...formData, language: i18n.resolvedLanguage || 'ja' })
    localStorage.setItem(`hasCompletedWelcome:${userId}`, 'true')
    setUserContext(saved.context)
    setShowWelcome(false)
    setTrackingRequest('feeding')
    setActiveTab('tracking')
  }

  const handleContextUpdate = (newContext) => {
    setUserContext(newContext)
  }

  const navigate = (tab, detail) => {
    if (tab === 'tracking') setTrackingRequest(detail || null)
    if (tab === 'chat') setChatDraft(detail || '')
    setActiveTab(tab)
  }

  if (showWelcome) {
    return <WelcomeScreen onComplete={handleWelcomeComplete} onExit={() => onChooseEntry(null)} />
  }

  if (nightMode) {
    return <NightMode userId={userId} onExit={() => setNightMode(false)} />
  }

  const tabs = [
    { id: 'dashboard', label: t('nav.home'), icon: <Home size={20} /> },
    { id: 'chat', label: t('nav.chat'), icon: <MessageCircle size={20} /> },
    { id: 'tracking', label: t('nav.tracking'), icon: <BarChart3 size={20} /> },
    { id: 'support', label: t('pilot.supportNav'), icon: <Phone size={20} /> },
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
          <button className="entrance-switch" onClick={() => onChooseEntry(null)}>{t('pilot.switchEntrance')}</button>
          <motion.button
            className="night-mode-btn"
            onClick={() => setNightMode(true)}
            title={t('nightMode.title')}
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
            onClick={() => navigate(tab.id)}
            aria-current={activeTab === tab.id ? 'page' : undefined}
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
              <Dashboard userId={userId} userContext={userContext} onNavigate={navigate} onNightMode={() => setNightMode(true)} />
            )}
            {activeTab === 'chat' && <ChatInterface userId={userId} initialDraft={chatDraft} />}
            {activeTab === 'tracking' && <TrackingPanel userId={userId} initialEntryType={trackingRequest} />}
            {activeTab === 'checkin' && <EmotionalCheckIn userId={userId} />}
            {activeTab === 'support' && <><SupportDirectory /><ShareSummary userId={userId} /></>}
            {activeTab === 'settings' && (
              <Settings
                userId={userId}
                onContextUpdate={handleContextUpdate}
                onLogout={() => api.logout()}
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
