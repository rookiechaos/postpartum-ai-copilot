import React from 'react'
import { AlertTriangle, Home, RefreshCw } from 'lucide-react'
import i18n from '../i18n/config'
import english from '../i18n/locales/recovery.en.json'
import japanese from '../i18n/locales/recovery.ja.json'
import errorTracker from '../utils/errorTracker'
import './ErrorBoundary.css'

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, confirmReload: false, languageVersion: 0 }
    this.headingRef = React.createRef()
  }

  static getDerivedStateFromError() {
    return { hasError: true, confirmReload: false }
  }

  componentDidMount() {
    i18n.on('languageChanged', this.updateLanguage)
    i18n.on('initialized', this.updateLanguage)
  }

  componentWillUnmount() {
    i18n.off('languageChanged', this.updateLanguage)
    i18n.off('initialized', this.updateLanguage)
  }

  componentDidCatch() {
    // Diagnostics accept a fixed event type, never the error, stack, or props.
    // A reporting failure must not prevent the recovery controls from working.
    try {
      errorTracker.trackReactError?.()
    } catch {
      // Recovery remains available even when diagnostics are unavailable.
    }
    // A crashed input can leave keyboard focus on the document body. Restore a
    // useful position only for a visible fallback, never for a retained tab.
    const heading = this.headingRef.current
    const active = document.activeElement
    if ((!active || active === document.body || active === document.documentElement || !active.isConnected)
      && heading?.isConnected && !heading.closest('[hidden], [inert], [aria-hidden="true"]')
      && heading.getClientRects().length && window.getComputedStyle(heading).visibility !== 'hidden') {
      heading.focus({ preventScroll: true })
    }
  }

  updateLanguage = () => {
    this.setState((state) => ({ languageVersion: state.languageVersion + 1 }))
  }

  text = (key) => {
    // This boundary also surrounds providers, so the fallback cannot depend on
    // React translation context, care-session state, or toast notifications.
    const fallback = (i18n.resolvedLanguage || i18n.language || 'ja').startsWith('en') ? english : japanese
    try {
      return i18n.t(`recovery.${key}`, { defaultValue: fallback[key] })
    } catch {
      return fallback[key]
    }
  }

  handleReset = () => {
    // Rendering children again remounts this subtree. It never repeats a save
    // or an AI request on the user's behalf, and does not reload other pages.
    this.setState({ hasError: false, confirmReload: false })
  }

  render() {
    if (this.state.hasError) {
      const { compact = false, label, onHome, allowReload = false } = this.props
      const title = this.text(compact ? 'pageTitle' : 'appTitle')
      return (
        <section className={`error-boundary${compact ? ' error-boundary--compact' : ''}`} aria-label={title}>
          <div className="error-boundary__content">
            <AlertTriangle size={28} className="error-boundary__icon" aria-hidden="true" />
            {label && <p className="error-boundary__label">{label}</p>}
            <div role="alert">
              <h2 ref={this.headingRef} tabIndex={-1}>{title}</h2>
              <p>{this.text(compact ? 'pageDescription' : 'appDescription')}</p>
              <p className="error-boundary__notice">{this.text(compact ? 'pageDraftWarning' : 'appDraftWarning')}</p>
              <p>{this.text('checkSavedWork')}</p>
            </div>
            <div className="error-boundary__actions">
              <button type="button" onClick={this.handleReset} className="error-boundary__button error-boundary__button--primary">
                <RefreshCw size={18} aria-hidden="true" />
                {this.text(compact ? 'retryPage' : 'retryApp')}
              </button>
              {typeof onHome === 'function' && (
                <button type="button" onClick={onHome} className="error-boundary__button">
                  <Home size={18} aria-hidden="true" />
                  {this.text('home')}
                </button>
              )}
            </div>
            {allowReload && !this.state.confirmReload && (
              <button type="button" onClick={() => this.setState({ confirmReload: true })} className="error-boundary__reload-link">
                {this.text('reloadOption')}
              </button>
            )}
            {allowReload && this.state.confirmReload && (
              <div className="error-boundary__reload-confirmation">
                <p role="alert">{this.text('reloadWarning')}</p>
                <div className="error-boundary__actions">
                  <button type="button" onClick={() => this.setState({ confirmReload: false })} className="error-boundary__button">
                    {this.text('cancelReload')}
                  </button>
                  <button type="button" onClick={() => window.location.reload()} className="error-boundary__button">
                    {this.text('confirmReload')}
                  </button>
                </div>
              </div>
            )}
          </div>
        </section>
      )
    }

    return this.props.children
  }
}

export default ErrorBoundary
