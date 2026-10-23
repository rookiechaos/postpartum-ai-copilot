import React, { useState, useEffect, useRef, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import api from './utils/api'
import { CareSessionProvider, useCareSession } from './utils/CareSession'
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
import { FamilyInviteReview } from './components/FamilyInviteLinks'
import ConnectionNotice from './components/ConnectionNotice'
import SupportHub from './components/SupportHub'
import InstallPrompt from './components/InstallPrompt'
import LanguageSelector from './components/LanguageSelector'
import OperatorPortal from './components/OperatorPortal'
import Auth from './components/Auth'
import ProductBrand from './components/ProductBrand'
import ErrorBoundary from './components/ErrorBoundary'
import PendingCare from './components/PendingCare'
import { NotificationDelivery } from './components/NotificationManager'
import { Home, MessageCircle, BarChart3, Phone, Settings as SettingsIcon, Moon } from 'lucide-react'
import './App.css'
import './components/Pilot.css'
import './components/ProductFlows.css'
import './styles/ui.css'
import './styles/interactions.css'

function App() {
  const { t } = useTranslation()
  const [authChecked, setAuthChecked] = useState(false)
  const [userId, setUserId] = useState(null)
  const [sessionKey, setSessionKey] = useState(0)
  const hadAuthenticatedAccount = useRef(api.isAuthenticated())
  const inviteAccount = useRef(api.isAuthenticated() ? api.getUserId() : null)
  const [pendingInvite, setPendingInvite] = useState(() => {
    const token = new URLSearchParams(window.location.hash.slice(1)).get('invite')
    return /^[A-Za-z0-9_-]{43}$/.test(token || '') ? token : null
  })
  const clearInvite = useCallback(() => { inviteAccount.current = null; setPendingInvite(null) }, [])
  const completeSignIn = useCallback(id => {
    // An expired session may resume the invite; another account starts fresh.
    if (inviteAccount.current && inviteAccount.current !== id) clearInvite()
    else inviteAccount.current = id
    setUserId(id)
  }, [clearInvite])
  useEffect(() => {
    const capture = () => {
      const fragment = new URLSearchParams(window.location.hash.slice(1))
      const token = fragment.get('invite')
      if (!/^[A-Za-z0-9_-]{43}$/.test(token || '')) return
      inviteAccount.current = api.isAuthenticated() ? api.getUserId() : null
      setPendingInvite(token); fragment.delete('invite')
      const rest = fragment.toString()
      window.history.replaceState(window.history.state, '', window.location.pathname + window.location.search + (rest ? `#${rest}` : ''))
    }
    capture(); window.addEventListener('hashchange', capture)
    return () => window.removeEventListener('hashchange', capture)
  }, [])
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
    const unsubscribe = api.onAuthChange(({ preserveTasks, token, reason }) => {
      if (!preserveTasks) {
        // Expiry preserves only the invite intent; private screens/tasks still reset.
        if (reason !== 'expired' && (hadAuthenticatedAccount.current || reason === 'logout' || reason === 'storage')) clearInvite()
        clearAccount()
      }
      hadAuthenticatedAccount.current = Boolean(token)
    })
    api.setOnUnauthorized(clearAccount)

    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/sw.js').catch(() => {
        console.error('Service Worker registration failed')
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
        completeSignIn(storedUserId)
        setAuthChecked(true)
        return
      }
      try {
        const user = await api.getCurrentUser()
        if (!active || generation !== initialGeneration) return
        api.setUserId(user?.user_id || null)
        completeSignIn(user?.user_id || null)
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
  }, [clearInvite, completeSignIn, clearLeaveGuard])

  if (!authChecked) {
    return (
      <div className="app app-loading" style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <p role="status">{t('auth.loggingIn', 'Loading...')}</p>
      </div>
    )
  }
  if (!entry) return <ErrorBoundary key="entry"><EntryScreen onChoose={chooseEntry} /></ErrorBoundary>
  if (!userId) return <ErrorBoundary key={`auth:${entry}`} onHome={() => chooseEntry(null)}>
    <Auth entry={entry} onBack={() => chooseEntry(null)} onSuccess={completeSignIn} /></ErrorBoundary>
  if (entry === 'operator') return <ErrorBoundary key={`${sessionKey}:${userId}:operator`} onHome={() => chooseEntry(null)}>
    <OperatorPortal registerLeaveGuard={registerLeaveGuard} onExit={() => chooseEntry(null)} onOrganization={() => chooseEntry('organization')} /></ErrorBoundary>
  if (entry === 'organization') return <ErrorBoundary key={`${sessionKey}:${userId}:organization`} onHome={() => chooseEntry(null)}>
    <OrganizationPortal userId={userId} registerLeaveGuard={registerLeaveGuard} onFamily={() => chooseEntry('family')} onExit={() => chooseEntry(null)} /></ErrorBoundary>
  return <CareSessionProvider key={`${sessionKey}:${userId}:family`} userId={userId}>
    <AuthenticatedApp userId={userId} onChooseEntry={chooseEntry} registerLeaveGuard={registerLeaveGuard}
      pendingInvite={pendingInvite} onInvitationHandled={clearInvite} />
  </CareSessionProvider>
}

// A new login mounts fresh private state, including all child components.
function AuthenticatedApp({ userId, onChooseEntry, registerLeaveGuard, pendingInvite, onInvitationHandled }) {
  const { t, i18n } = useTranslation()
  const { work } = useCareSession()
  const [activeTab, setActiveTab] = useState('dashboard')
  const [nightMode, setNightMode] = useState(false)
  const [showWelcome, setShowWelcome] = useState(false)
  const [userContext, setUserContext] = useState(null)
  const [trackingRequest, setTrackingRequest] = useState(null)
  const [chatDraft, setChatDraft] = useState('')
  const [chatRequestKey, setChatRequestKey] = useState(0)
  const [chatNavigation, setChatNavigation] = useState({ key: 0 })
  const [settingsNavigation, setSettingsNavigation] = useState({ key: 0 })
  const [trackingRequestKey, setTrackingRequestKey] = useState(0)
  const [visitedTabs, setVisitedTabs] = useState(['dashboard'])
  const [recordVersion, setRecordVersion] = useState(0)
  const [supportRequest, setSupportRequest] = useState({ key: 0, view: 'contacts', question: '' })
  const [navigationKey, setNavigationKey] = useState(0)
  const [familyRequest, setFamilyRequest] = useState({ id: '', key: 0 })
  const [dashboardRequest, setDashboardRequest] = useState({ key: 0 })
  const [firstTask, setFirstTask] = useState('')
  const familyVisible = !nightMode && !pendingInvite
  const panelRefs = useRef({})
  const pendingPanelFocus = useRef(false)
  const hasOpenWork = Object.values(work).some(item => item.critical || item.protectLeave)
  const confirmLeave = useCallback(() => !hasOpenWork || window.confirm(t('experience.leavePrompt')), [hasOpenWork, t])

  useEffect(() => registerLeaveGuard(confirmLeave), [registerLeaveGuard, confirmLeave])
  useEffect(() => {
    if (!hasOpenWork) return
    const warn = event => { event.preventDefault(); event.returnValue = '' }
    window.addEventListener('beforeunload', warn)
    return () => window.removeEventListener('beforeunload', warn)
  }, [hasOpenWork])

  useEffect(() => {
    if (!showWelcome && familyVisible && pendingPanelFocus.current) {
      pendingPanelFocus.current = false
      revealElement(panelRefs.current[activeTab])
    }
  }, [navigationKey, activeTab, showWelcome, familyVisible])

  useEffect(() => {
    let active = true
    const welcomeCompleted = localStorage.getItem(`hasCompletedWelcome:${userId}`)
    setShowWelcome(!welcomeCompleted)
    if (welcomeCompleted) {
      api.getUserContext(userId).then(context => {
        if (active) setUserContext(context)
      }).catch(() => {
        if (active) console.error('Error loading context')
      })
    }
    return () => { active = false }
  }, [userId])

  const handleWelcomeComplete = async (formData = {}, task = 'record') => {
    const suppliedFields = Object.fromEntries(Object.entries(formData).filter(([, value]) => value !== ''))
    const saved = await api.updateUserContext(userId, { ...suppliedFields, language: i18n.resolvedLanguage || 'ja' })
    localStorage.setItem(`hasCompletedWelcome:${userId}`, 'true')
    setUserContext(saved.context)
    setShowWelcome(false)
    setFirstTask(task)
    navigate(familyRequest.id || task === 'family' ? 'family' : task === 'support' ? 'support' : 'dashboard',
      task === 'support' ? { view: 'contacts' } : task === 'record' ? { section: 'quick-record-heading' } : undefined)
  }

  const handleContextUpdate = (newContext) => {
    setUserContext(newContext)
  }

  const navigate = useCallback((tab, detail) => {
    if (tab === 'dashboard' && detail) setDashboardRequest(previous => ({ ...detail, key: previous.key + 1 }))
    if (tab === 'tracking' && detail) { setTrackingRequest(detail); setTrackingRequestKey(value => value + 1) }
    const chatResume = tab === 'chat' && detail?.action === 'resume'
    const chatQuestion = tab === 'chat' && typeof detail === 'string' && detail.length > 0
    const settingsHelp = tab === 'settings' && detail?.view === 'help'
    if (chatQuestion) { setChatDraft(detail); setChatRequestKey(value => value + 1) }
    if (chatResume) setChatNavigation(previous => ({ key: previous.key + 1, action: 'resume' }))
    if (settingsHelp) setSettingsNavigation(previous => ({ key: previous.key + 1, view: 'help' }))
    const supportDestination = tab === 'support' && ['contacts', 'sheet'].includes(detail?.view) ? detail : null
    if (supportDestination) setSupportRequest(previous => ({ key: previous.key + 1, view: supportDestination.view,
      contactKey: supportDestination.contactKey || '',
      contactName: supportDestination.contactName || '',
      question: supportDestination.view === 'sheet' && typeof supportDestination.question === 'string' ? supportDestination.question : '' }))
    // A requested support view or incoming question owns its more specific focus target.
    pendingPanelFocus.current = !supportDestination && !chatResume && !chatQuestion && !settingsHelp
      && !(detail && ['tracking', 'dashboard'].includes(tab))
    setNavigationKey(value => value + 1)
    setVisitedTabs(previous => previous.includes(tab) ? previous : [...previous, tab])
    setActiveTab(tab)
  }, [])

  useEffect(() => {
    const handleKeyDown = event => {
      if (!familyVisible || showWelcome || event.defaultPrevented || event.isComposing || event.ctrlKey || event.metaKey || event.altKey) return
      if (event.target?.closest?.('input, textarea, select, [contenteditable]:not([contenteditable="false"])')) return
      if (Array.from(document.querySelectorAll('dialog[open], [role="dialog"], [aria-modal="true"]'))
        .some(element => !element.closest('[hidden]') && element.getClientRects().length)) return
      if (event.key === '/') {
        // Retained tabs and closed details must never receive shortcut focus.
        const search = Array.from(panelRefs.current[activeTab]?.querySelectorAll('input[type="search"]') || [])
          .find(element => !element.disabled && !element.closest('[hidden], [inert]') && element.getClientRects().length
            && window.getComputedStyle(element).visibility !== 'hidden')
        if (search) { event.preventDefault(); search.focus() }
      } else if (event.key === '?') {
        event.preventDefault(); navigate('settings', { view: 'help' })
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [activeTab, familyVisible, showWelcome, navigate])

  const handleInvitation = familyId => {
    onInvitationHandled()
    if (familyId) {
      setFamilyRequest(previous => ({ id: familyId, key: previous.key + 1 }))
      setRecordVersion(value => value + 1); setNightMode(false); navigate('family')
    }
  }
  if (pendingInvite && showWelcome) return <ErrorBoundary compact onHome={onInvitationHandled}><FamilyInviteReview token={pendingInvite} onHandled={handleInvitation} /></ErrorBoundary>
  if (showWelcome) {
    return <ErrorBoundary key="welcome" onHome={() => onChooseEntry(null)}><WelcomeScreen onComplete={handleWelcomeComplete} onExit={() => onChooseEntry(null)} /></ErrorBoundary>
  }

  const tabs = [
    { id: 'dashboard', label: t('nav.home'), icon: <Home size={20} /> },
    { id: 'tracking', label: t('nav.tracking'), icon: <BarChart3 size={20} /> },
    { id: 'chat', label: t('friendly.chat.title'), icon: <MessageCircle size={20} /> },
    { id: 'support', label: t('pilot.supportNav'), icon: <Phone size={20} /> },
    { id: 'settings', label: t('nav.settings'), icon: <SettingsIcon size={20} /> }
  ]

  return (
    <><NotificationDelivery userId={userId} />{pendingInvite && <ErrorBoundary compact onHome={onInvitationHandled}><FamilyInviteReview token={pendingInvite} onHandled={handleInvitation} /></ErrorBoundary>}
    <div className="app family-app" hidden={!familyVisible}>
      <a className="family-skip-link" href="#family-main" onClick={event => {
        event.preventDefault(); revealElement(panelRefs.current[activeTab])
      }}>{t('experience.skip')}</a>
      <header className="app-header">
        <div className="header-content">
          <ProductBrand as="h1" />
          <p className="tagline">{t('app.tagline')}</p>
        </div>
        <div className="header-actions">
          <LanguageSelector />
          <button
            className="night-mode-btn"
            onClick={() => setNightMode(true)}
            title={t('nightMode.title')}
          >
            <Moon size={18} aria-hidden="true" />
            {t('nightMode.title')}
          </button>
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
            <span className="nav-icon" aria-hidden="true">{tab.icon}</span>
            <span className="nav-label-full" aria-hidden="true">{tab.label}</span>
            <span className="nav-label-short" aria-hidden="true">{t(`ui.nav.${tab.id}`)}</span>
          </button>
        ))}
      </nav>

      <main className="app-main" id="family-main" tabIndex={-1}>
        <ConnectionNotice onCheck={() => navigate('tracking')} />
        <ErrorBoundary compact><PendingCare activeTab={activeTab} onNavigate={navigate} /></ErrorBoundary>
        {['family', 'checkin'].includes(activeTab) && <nav className="family-subpage-nav" aria-label={t('ui.nav.label')}>
          <button type="button" className="text-action" onClick={() => navigate('dashboard')}>{t('experience.backHome')}</button>
          <span aria-current="page">{t(activeTab === 'family' ? 'polish.familyHandoff' : 'checkin.title')}</span>
        </nav>}
        {firstTask && <section className="pilot-panel first-task-guide"><h3>{t(`continuity.onboarding.tasks.${firstTask}.title`)}</h3>
          <p>{t(`continuity.onboarding.tasks.${firstTask}.hint`)}</p>
          <button type="button" className="text-action" onClick={() => setFirstTask('')}>{t('continuity.onboarding.dismiss')}</button>
        </section>}
        {visitedTabs.map(tab => <section key={tab} className="family-tab-panel" hidden={activeTab !== tab} tabIndex={-1}
          ref={element => { panelRefs.current[tab] = element }}
          aria-labelledby={tabs.some(item => item.id === tab) ? `family-tab-${tab}` : undefined}
          aria-label={tab === 'checkin' ? t('checkin.title') : tab === 'family' ? t('polish.familyHandoff') : undefined}>
            <ErrorBoundary compact label={tabs.find(item => item.id === tab)?.label || t(tab === 'family' ? 'polish.familyHandoff' : 'checkin.title')}
              onHome={tab !== 'dashboard' ? () => navigate('dashboard') : undefined}>
            {tab === 'dashboard' && (
              <Dashboard userId={userId} userContext={userContext} refreshKey={recordVersion} visible={activeTab === 'dashboard' && familyVisible}
                navigationRequest={dashboardRequest}
                onNavigate={navigate} onRecordsChanged={() => setRecordVersion(value => value + 1)} />
            )}
            {tab === 'chat' && <ChatInterface userId={userId} initialDraft={chatDraft} draftVersion={chatRequestKey} navigationRequest={chatNavigation} visible={activeTab === 'chat' && familyVisible}
              onPrepareSheet={(script, contact) => navigate('support', { view: 'sheet', question: script, contactKey: contact?.key, contactName: contact?.name })} />}
            {tab === 'tracking' && <TrackingPanel userId={userId} initialEntryType={trackingRequest} requestKey={trackingRequestKey}
              visible={activeTab === 'tracking' && familyVisible}
              onRecordsChanged={() => setRecordVersion(value => value + 1)} />}
            {tab === 'checkin' && <EmotionalCheckIn userId={userId} />}
            {tab === 'support' && <SupportHub userId={userId} visible={activeTab === 'support' && familyVisible}
              refreshKey={recordVersion} navigationRequest={supportRequest}
              onPrepareSheet={(script, contact) => navigate('support', { view: 'sheet', question: script, contactKey: contact?.key, contactName: contact?.name })} />}
            {tab === 'family' && <FamilySharing userId={userId} refreshKey={recordVersion} visible={activeTab === 'family' && familyVisible}
              initialFamilyId={familyRequest.id} familyRequestKey={familyRequest.key} />}
            {tab === 'settings' && (
              <Settings
                userId={userId}
                navigationRequest={settingsNavigation} visible={activeTab === 'settings' && familyVisible}
                onContextUpdate={handleContextUpdate}
                onLogout={() => { if (confirmLeave()) api.logout() }}
                onSwitchEntrance={() => onChooseEntry(null)}
                onFindHelp={() => navigate('support', { view: 'contacts' })}
              />
            )}
            </ErrorBoundary>
          </section>)}
        <div className="family-tab-panel" hidden={activeTab !== 'dashboard'}><InstallPrompt ready={recordVersion > 0} /></div>
      </main>
    </div>{nightMode && <div hidden={Boolean(pendingInvite)}><ErrorBoundary compact label={t('nightMode.title')} onHome={() => setNightMode(false)}>
      <NightMode userId={userId} onExit={() => setNightMode(false)} /></ErrorBoundary></div>}</>
  )
}

export default App
