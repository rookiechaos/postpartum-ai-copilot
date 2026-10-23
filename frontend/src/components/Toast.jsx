import React, { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { CheckCircle, XCircle, AlertCircle, Info, X } from 'lucide-react'
import api from '../utils/api'
import './Toast.css'

const ToastContext = createContext()

export const useToast = () => {
  const context = useContext(ToastContext)
  if (!context) {
    throw new Error('useToast must be used within ToastProvider')
  }
  return context
}

export const ToastProvider = ({ children }) => {
  const [toasts, setToasts] = useState([])
  const [sessionGeneration, setSessionGeneration] = useState(0)
  const generation = useRef(0)
  const mounted = useRef(true)
  const nextId = useRef(0)
  const timers = useRef(new Map())

  const removeToast = useCallback((id) => {
    clearTimeout(timers.current.get(id))
    timers.current.delete(id)
    setToasts(prev => prev.filter(t => t.id !== id))
  }, [])

  useEffect(() => {
    mounted.current = true
    const unsubscribe = api.onAuthChange(({ preserveTasks }) => {
      if (preserveTasks) return
      // The provider outlives private screens. Clear messages on every new login,
      // logout and account switch; a token refresh keeps the same session.
      generation.current += 1
      setSessionGeneration(generation.current)
      timers.current.forEach(timer => clearTimeout(timer))
      timers.current.clear()
      setToasts([])
    })
    return () => {
      mounted.current = false
      unsubscribe()
      timers.current.forEach(timer => clearTimeout(timer))
      timers.current.clear()
    }
  }, [])

  const showToast = useCallback((message, type = 'info', duration) => {
    // Async callbacks held by an old screen must not notify the next account.
    if (!mounted.current || sessionGeneration !== generation.current) return null
    const id = ++nextId.current
    const toast = { id, message, type }
    // Errors remain available until dismissed; informational receipts may expire.
    const lifetime = duration ?? (type === 'error' || type === 'warning' ? 0 : 5000)
    
    setToasts(prev => [...prev, toast])
    
    if (lifetime > 0) {
      timers.current.set(id, setTimeout(() => removeToast(id), lifetime))
    }
    
    return id
  }, [removeToast, sessionGeneration])

  const success = useCallback((message, duration) => {
    return showToast(message, 'success', duration)
  }, [showToast])

  const error = useCallback((message, duration) => {
    return showToast(message, 'error', duration)
  }, [showToast])

  const warning = useCallback((message, duration) => {
    return showToast(message, 'warning', duration)
  }, [showToast])

  const info = useCallback((message, duration) => {
    return showToast(message, 'info', duration)
  }, [showToast])

  return (
    <ToastContext.Provider value={{ showToast, success, error, warning, info, removeToast }}>
      {children}
      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </ToastContext.Provider>
  )
}

const ToastContainer = ({ toasts, onRemove }) => {
  return (
    <>
      {/* Keep live regions mounted before messages arrive. Visible cards are not
          also live, so each notification is announced only once. */}
      <div className="toast-announcements" role="status" aria-atomic="false" aria-relevant="additions text">
        {toasts.filter(toast => toast.type !== 'error').map(toast => <div key={toast.id}>{toast.message}</div>)}
      </div>
      <div className="toast-announcements" role="alert" aria-atomic="false" aria-relevant="additions text">
        {toasts.filter(toast => toast.type === 'error').map(toast => <div key={toast.id}>{toast.message}</div>)}
      </div>
      <div className="toast-container">
        {toasts.map(toast => (
          <Toast key={toast.id} toast={toast} onRemove={onRemove} />
        ))}
      </div>
    </>
  )
}

const Toast = ({ toast, onRemove }) => {
  const { t } = useTranslation()
  const icons = {
    success: <CheckCircle size={20} />,
    error: <XCircle size={20} />,
    warning: <AlertCircle size={20} />,
    info: <Info size={20} />
  }

  const colors = {
    success: '#48bb78',
    error: '#f56565',
    warning: '#ed8936',
    info: '#667eea'
  }

  return (
    <div
      className="toast"
      style={{ borderLeftColor: colors[toast.type] }}
    >
      <div className="toast-icon" style={{ color: colors[toast.type] }} aria-hidden="true">
        {icons[toast.type]}
      </div>
      <div className="toast-message">{toast.message}</div>
      <button
        type="button"
        className="toast-close"
        onClick={() => onRemove(toast.id)}
        aria-label={t('common.close')}
      >
        <X size={16} aria-hidden="true" />
      </button>
    </div>
  )
}
