/**
 * Error Tracker - Frontend error tracking and reporting
 */

import api from './api.js'

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
        message: event.message,
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno,
        stack: event.error?.stack,
        timestamp: new Date().toISOString()
      })
    })

    // Track unhandled promise rejections
    window.addEventListener('unhandledrejection', (event) => {
      this.trackError({
        type: 'unhandledrejection',
        message: event.reason?.message || String(event.reason),
        stack: event.reason?.stack,
        timestamp: new Date().toISOString()
      })
    })

    // Track React errors (if ErrorBoundary is used)
    this.trackReactError = (error, errorInfo) => {
      this.trackError({
        type: 'react_error',
        message: error.message,
        stack: error.stack,
        componentStack: errorInfo?.componentStack,
        timestamp: new Date().toISOString()
      })
    }

    this.initialized = true
  }

  trackError(errorData) {
    const error = {
      ...errorData,
      url: window.location.href,
      userAgent: navigator.userAgent,
      timestamp: errorData.timestamp || new Date().toISOString()
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

  trackUserAction(action, details = {}) {
    // Track user actions for analytics
    try {
      api.post('/api/monitoring/actions', {
        action,
        details,
        timestamp: new Date().toISOString(),
        url: window.location.href
      }).catch(() => {
        // Silently fail - don't interrupt user flow
      })
    } catch (error) {
      // Ignore errors in tracking
    }
  }

  trackPerformance(metricName, value, unit = 'ms') {
    // Track performance metrics (Web Vitals)
    try {
      api.post('/api/monitoring/performance', {
        metric: metricName,
        value,
        unit,
        timestamp: new Date().toISOString(),
        url: window.location.href
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
