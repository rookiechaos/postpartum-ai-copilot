import React, { useState, useEffect, useRef } from 'react'
import { motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import api from './utils/api'
import useEntranceNavigation from './utils/useEntranceNavigation'
import { applyDisplaySettings, readDisplaySettings } from './utils/displaySettings'
import { revealElement } from './utils/focusView'
import ChatInterface from './components/ChatInterface'
import TrackingPanel from './components/TrackingPanel'
import NightMode from './components/NightMode'
import EmotionalCheckIn from './components/EmotionalCheckIn'
import Dashboard from './components/Dashboard'
import Settings from './components/Settings'
import WelcomeScreen from './components/WelcomeScreen'
import EntryScreen from './components/EntryScreen'
import OrganizationPortal from './components/OrganizationPortal'
import FamilySharing from './components/FamilySharing'
import SupportHub from './components/SupportHub'
import InstallPrompt from './components/InstallPrompt'
import LanguageSelector from './components/LanguageSelector'
import OperatorPortal from './components/OperatorPortal'
import Auth from './components/Auth'
import { Home, MessageCircle, BarChart3, Phone, Settings as SettingsIcon, Moon } from 'lucide-react'
import './App.css'
import './components/Pilot.css'
import './components/ProductFlows.css'
import './styles/ui.css'

function App() {
  const { t } = useTranslation()
  const [authChecked, setAuthChecked] = useState(false)
  const [userId, setUserId] = useState(null)
  const [sessionKey, setSessionKey] = useState(0)
  const { entry, navigate: chooseEntry, registerLeaveGuard, clearLeaveGuard } = useEntranceNavigation()
  useEffect(() => { applyDisplaySettings(readDisplaySettings()) }, [])
  useEffect(() => {
    let active = true
    let generation = 0
    const clearAccount = () => {
      generation++
      if (!active) return
      clearLeaveGuard()
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
  if (entry === 'operator') return <OperatorPortal key={`${sessionKey}:${userId}:operator`} onExit={() => chooseEntry(null)} />
  if (entry === 'organization') return <OrganizationPortal key={`${sessionKey}:${userId}:organization`}
    userId={userId} registerLeaveGuard={registerLeaveGuard} onFamily={() => chooseEntry('family')} onExit={() => chooseEntry(null)} />
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
  const [chatRequestKey, setChatRequestKey] = useState(0)
  const [trackingRequestKey, setTrackingRequestKey] = useState(0)
  const [visitedTabs, setVisitedTabs] = useState(['dashboard'])
  const [recordVersion, setRecordVersion] = useState(0)
  const [supportRequest, setSupportRequest] = useState({ key: 0, view: 'contacts', question: '' })
  const [navigationKey, setNavigationKey] = useState(0)
  const panelRefs = useRef({})
  const pendingPanelFocus = useRef(false)

  useEffect(() => {
    if (!showWelcome && !nightMode && pendingPanelFocus.current) {
      pendingPanelFocus.current = false
      revealElement(panelRefs.current[activeTab])
    }
  }, [navigationKey, activeTab, showWelcome, nightMode])

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
        navigate('settings')
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

  const handleWelcomeComplete = async (formData = {}) => {
    const suppliedFields = Object.fromEntries(Object.entries(formData).filter(([, value]) => value !== ''))
    const saved = await api.updateUserContext(userId, { ...suppliedFields, language: i18n.resolvedLanguage || 'ja' })
    localStorage.setItem(`hasCompletedWelcome:${userId}`, 'true')
    setUserContext(saved.context)
    setShowWelcome(false)
    navigate('dashboard')
  }

  const handleContextUpdate = (newContext) => {
    setUserContext(newContext)
  }

  const navigate = (tab, detail) => {
    if (tab === 'tracking' && detail) { setTrackingRequest(detail); setTrackingRequestKey(value => value + 1) }
    if (tab === 'chat' && detail) { setChatDraft(detail); setChatRequestKey(value => value + 1) }
    const supportDestination = tab === 'support' && ['contacts', 'sheet'].includes(detail?.view) ? detail : null
    if (supportDestination) setSupportRequest(previous => ({ key: previous.key + 1, view: supportDestination.view,
      question: supportDestination.view === 'sheet' && typeof supportDestination.question === 'string' ? supportDestination.question : '' }))
    // A requested support view or incoming question owns its more specific focus target.
    pendingPanelFocus.current = !supportDestination && !(detail && tab === 'chat')
    setNavigationKey(value => value + 1)
    setVisitedTabs(previous => previous.includes(tab) ? previous : [...previous, tab])
    setActiveTab(tab)
  }

  if (showWelcome) {
    return <WelcomeScreen onComplete={handleWelcomeComplete} onExit={() => onChooseEntry(null)} />
  }

  const tabs = [
    { id: 'dashboard', label: t('nav.home'), icon: <Home size={20} /> },
    { id: 'chat', label: t('nav.chat'), icon: <MessageCircle size={20} /> },
    { id: 'tracking', label: t('nav.tracking'), icon: <BarChart3 size={20} /> },
    { id: 'support', label: t('pilot.supportNav'), icon: <Phone size={20} /> },
    { id: 'settings', label: t('nav.settings'), icon: <SettingsIcon size={20} /> }
  ]

  return (
    <><div className="app family-app" hidden={nightMode}>
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
            title={t('nightMode.title')}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            <Moon size={18} />
            {t('nightMode.title')}
          </motion.button>
        </div>
      </header>

      <nav className="tab-nav" aria-label={t('ui.nav.label')}>
        {tabs.map((tab) => (
          <button
            key={tab.id}
            id={`family-tab-${tab.id}`}
            className={activeTab === tab.id ? 'active' : ''}
            onClick={() => navigate(tab.id)}
            aria-label={tab.label}
            aria-current={activeTab === tab.id ? 'page' : undefined}
          >
            {tab.icon}
            <span className="nav-label-full" aria-hidden="true">{tab.label}</span>
            <span className="nav-label-short" aria-hidden="true">{t(`ui.nav.${tab.id}`)}</span>
          </button>
        ))}
      </nav>

      <main className="app-main">
        {visitedTabs.map(tab => <section key={tab} className="family-tab-panel" hidden={activeTab !== tab} tabIndex={-1}
          ref={element => { panelRefs.current[tab] = element }}
          aria-labelledby={tabs.some(item => item.id === tab) ? `family-tab-${tab}` : undefined}
          aria-label={tab === 'checkin' ? t('checkin.title') : tab === 'family' ? t('polish.familyHandoff') : undefined}>
            {tab === 'dashboard' && (
              <Dashboard userId={userId} userContext={userContext} refreshKey={recordVersion} visible={activeTab === 'dashboard' && !nightMode}
                onNavigate={navigate} onRecordsChanged={() => setRecordVersion(value => value + 1)} />
            )}
            {tab === 'chat' && <ChatInterface userId={userId} initialDraft={chatDraft} draftVersion={chatRequestKey} visible={activeTab === 'chat' && !nightMode}
              onPrepareSheet={script => navigate('support', { view: 'sheet', question: script })} />}
            {tab === 'tracking' && <TrackingPanel userId={userId} initialEntryType={trackingRequest} requestKey={trackingRequestKey}
              visible={activeTab === 'tracking' && !nightMode}
              onRecordsChanged={() => setRecordVersion(value => value + 1)} />}
            {tab === 'checkin' && <EmotionalCheckIn userId={userId} />}
            {tab === 'support' && <SupportHub userId={userId} visible={activeTab === 'support' && !nightMode}
              refreshKey={recordVersion} navigationRequest={supportRequest}
              onPrepareSheet={script => navigate('support', { view: 'sheet', question: script })} />}
            {tab === 'family' && <FamilySharing userId={userId} refreshKey={recordVersion} visible={activeTab === 'family' && !nightMode} />}
            {tab === 'settings' && (
              <Settings
                userId={userId}
                onContextUpdate={handleContextUpdate}
                onLogout={() => api.logout()}
                onSwitchEntrance={() => onChooseEntry(null)}
                onFindHelp={() => navigate('support', { view: 'contacts' })}
              />
            )}
          </section>)}
        <div className="family-tab-panel" hidden={activeTab !== 'dashboard'}><InstallPrompt ready={recordVersion > 0} /></div>
      </main>
    </div>{nightMode && <NightMode userId={userId} onExit={() => setNightMode(false)} />}</>
  )
}

export default App
