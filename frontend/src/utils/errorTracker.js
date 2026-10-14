/**
 * Error Tracker - Frontend error tracking and reporting
 */

import api from './api.js'

// Diagnostics may start before React removes an invitation fragment. Never
// collect the address, query, fragment, browser fingerprint or raw error text.
const diagnosticPage = () => ({ '/': 'entry', '/family': 'family', '/organization': 'organization', '/operator': 'operator' })[window.location.pathname] || 'other'
const errorTypes = ['error', 'unhandledrejection', 'react_error']
const actionTypes = ['page_view', 'open_help', 'save_record', 'login', 'logout']
const metricUnits = { LCP: 'ms', FID: 'ms', CLS: 'score' }

class ErrorTracker {
  constructor() {
    this.errors = []
    this.maxErrors = 100
    this.reportInterval = 30000 // 30 seconds
    this.lastReportTime = Date.now()
    this.initialized = false
  }

  init() {
    if (this.initialized) return
    
    // Track unhandled errors
    window.addEventListener('error', (event) => {
      this.trackError({
        type: 'error',
        lineno: event.lineno,
        colno: event.colno,
      })
    })

    // Track unhandled promise rejections
    window.addEventListener('unhandledrejection', () => this.trackError({ type: 'unhandledrejection' }))

    // Track React errors (if ErrorBoundary is used)
    this.trackReactError = () => this.trackError({ type: 'react_error' })

    this.initialized = true
  }

  trackError(errorData) {
    const error = {
      type: errorTypes.includes(errorData?.type) ? errorData.type : 'handled_error',
      page: diagnosticPage(),
      timestamp: new Date().toISOString()
    }
    for (const field of ['lineno', 'colno']) {
      if (Number.isSafeInteger(errorData?.[field]) && errorData[field] >= 0) error[field] = errorData[field]
    }

    this.errors.push(error)

    // Keep only recent errors
    if (this.errors.length > this.maxErrors) {
      this.errors.shift()
    }

    // Auto-report periodically
    const now = Date.now()
    if (now - this.lastReportTime > this.reportInterval) {
      this.reportErrors()
    }
  }

  async reportErrors() {
    if (this.errors.length === 0) return

    const errorsToReport = [...this.errors]
    this.errors = []
    this.lastReportTime = Date.now()

    try {
      // Report to backend
      await api.post('/api/monitoring/errors', {
        errors: errorsToReport
      })
    } catch (error) {
      // If reporting fails, keep errors for next attempt
      this.errors.unshift(...errorsToReport)
      console.error('Failed to report errors:', error)
    }
  }

  trackUserAction(action) {
    // Track user actions for analytics
    try {
      api.post('/api/monitoring/actions', {
        action: actionTypes.includes(action) ? action : 'ui_action',
        timestamp: new Date().toISOString(),
        page: diagnosticPage()
      }).catch(() => {
        // Silently fail - don't interrupt user flow
      })
    } catch (error) {
      // Ignore errors in tracking
    }
  }

  trackPerformance(metricName, value) {
    if (!Object.hasOwn(metricUnits, metricName) || typeof value !== 'number' || !Number.isFinite(value) || value < 0) return
    // Track performance metrics (Web Vitals)
    try {
      api.post('/api/monitoring/performance', {
        metric: metricName,
        value,
        unit: metricUnits[metricName],
        timestamp: new Date().toISOString(),
        page: diagnosticPage()
      }).catch(() => {
        // Silently fail
      })
    } catch (error) {
      // Ignore errors in tracking
    }
  }

  // Web Vitals tracking
  trackWebVitals() {
    // Track Largest Contentful Paint (LCP)
    if ('PerformanceObserver' in window) {
      try {
        const observer = new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            if (entry.entryType === 'largest-contentful-paint') {
              this.trackPerformance('LCP', entry.renderTime || entry.loadTime, 'ms')
            }
            if (entry.entryType === 'first-input') {
              this.trackPerformance('FID', entry.processingStart - entry.startTime, 'ms')
            }
            if (entry.entryType === 'layout-shift') {
              if (!entry.hadRecentInput) {
                this.trackPerformance('CLS', entry.value, 'score')
              }
            }
          }
        })

        observer.observe({ entryTypes: ['largest-contentful-paint', 'first-input', 'layout-shift'] })
      } catch (error) {
        // PerformanceObserver might not be supported
        console.warn('Web Vitals tracking not available:', error)
      }
    }
  }
}

// Export singleton instance
const errorTracker = new ErrorTracker()
export default errorTracker
