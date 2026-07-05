import React, { useState, useEffect, useCallback } from 'react'
import { Bell, BellOff, Clock, X } from 'lucide-react'
import { useToast } from './Toast'
import api from '../utils/api'
import websocketManager from '../utils/websocketManager'
import './NotificationManager.css'

function NotificationManager({ userId }) {
  const [enabled, setEnabled] = useState(false)
  const [permission, setPermission] = useState('default')
  const [notifications, setNotifications] = useState([])
  const [loading, setLoading] = useState(false)
  const toast = useToast()

  useEffect(() => {
    checkPermission()
    loadNotifications()
    setupWebSocket()
    
    return () => {
      websocketManager.off('notification', handleWebSocketNotification)
    }
  }, [userId])

  const setupWebSocket = () => {
    const token = localStorage.getItem('access_token')
    if (token) {
      websocketManager.connect(token)
      websocketManager.on('notification', handleWebSocketNotification)
    }
  }

  const handleWebSocketNotification = useCallback((notificationData) => {
    // Show browser notification
    if (permission === 'granted') {
      showNotification(notificationData.title, {
        body: notificationData.message,
        icon: '/icon-192x192.png',
        tag: `notification-${notificationData.notification_id}`,
        data: notificationData.action_url
      })
    }
    
    // Reload notifications
    loadNotifications()
  }, [permission])

  const checkPermission = () => {
    if ('Notification' in window) {
      setPermission(Notification.permission)
      setEnabled(Notification.permission === 'granted')
    }
  }

  const requestPermission = async () => {
    if (!('Notification' in window)) {
      toast.warning('Your browser does not support notifications')
      return
    }

    try {
      const permission = await Notification.requestPermission()
      setPermission(permission)
      setEnabled(permission === 'granted')
      
      if (permission === 'granted') {
        toast.success('Notifications enabled!')
        // Show a test notification
        showNotification('Notifications Enabled', {
          body: 'You will now receive reminders for feeding, check-ins, and more.',
          icon: '/icon-192x192.png'
        })
      } else {
        toast.warning('Notification permission denied')
      }
    } catch (error) {
      console.error('Error requesting notification permission:', error)
      toast.error('Failed to enable notifications')
    }
  }

  const showNotification = useCallback((title, options = {}) => {
    if (!enabled || permission !== 'granted') return

    const notification = new Notification(title, {
      icon: '/icon-192x192.png',
      badge: '/icon-192x192.png',
      tag: 'postpartum-copilot',
      requireInteraction: false,
      ...options
    })

    notification.onclick = () => {
      window.focus()
      notification.close()
    }

    return notification
  }, [enabled, permission])

  const loadNotifications = async () => {
    if (!userId) return
    
    setLoading(true)
    try {
      const data = await api.get('/api/notifications?include_sent=false&limit=100')
      setNotifications(data || [])
    } catch (error) {
      console.error('Failed to load notifications:', error)
      toast.error('Failed to load notifications')
    } finally {
      setLoading(false)
    }
  }

  const createSmartFeedingReminder = async () => {
    try {
      await api.post('/api/notifications/smart/feeding', { based_on_history: true })
      toast.success('Smart feeding reminder created!')
      loadNotifications()
    } catch (error) {
      console.error('Failed to create feeding reminder:', error)
      toast.error('Failed to create reminder')
    }
  }

  const createMoodCheckinReminder = async () => {
    try {
      await api.post('/api/notifications/smart/mood-check', { time_of_day: 'evening' })
      toast.success('Mood check-in reminder created!')
      loadNotifications()
    } catch (error) {
      console.error('Failed to create mood check-in reminder:', error)
      toast.error('Failed to create reminder')
    }
  }

  const disableNotification = async (notificationId) => {
    try {
      await api.delete(`/api/notifications/${notificationId}`)
      toast.success('Reminder disabled')
      loadNotifications()
    } catch (error) {
      console.error('Failed to disable notification:', error)
      toast.error('Failed to disable reminder')
    }
  }

  // Format scheduled time for display
  const formatScheduledTime = (isoString) => {
    const date = new Date(isoString)
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
  }

  const getReminderBody = (type) => {
    const bodies = {
      feeding: 'Time for a feeding! 💙',
      checkin: 'How are you feeling today? 💚',
      diaper: 'Check diaper status 👶',
      sleep: 'Time to track sleep 😴'
    }
    return bodies[type] || 'Reminder'
  }

  return (
    <div className="notification-manager">
      <div className="notification-header">
        <h3>🔔 Notifications & Reminders</h3>
        <p>Get reminders for feeding, check-ins, and more</p>
      </div>

      <div className="notification-permission">
        <div className="permission-status">
          <div className="permission-info">
            <Bell size={24} className={enabled ? 'enabled' : 'disabled'} />
            <div>
              <strong>Notification Status</strong>
              <p>{permission === 'granted' ? 'Enabled' : permission === 'denied' ? 'Denied' : 'Not Set'}</p>
            </div>
          </div>
          {permission !== 'granted' && (
            <button onClick={requestPermission} className="enable-button">
              {permission === 'denied' ? 'Change in Browser Settings' : 'Enable Notifications'}
            </button>
          )}
        </div>
      </div>

      {enabled && (
        <div className="reminders-section">
          <div className="reminders-header">
            <h4>Scheduled Reminders</h4>
            <div className="reminder-actions">
              <button onClick={createSmartFeedingReminder} className="add-reminder-btn" disabled={loading}>
                + Smart Feeding Reminder
              </button>
              <button onClick={createMoodCheckinReminder} className="add-reminder-btn" disabled={loading}>
                + Mood Check-in
              </button>
            </div>
          </div>

          <div className="reminders-list">
            {loading ? (
              <p className="no-reminders">Loading...</p>
            ) : notifications.length === 0 ? (
              <p className="no-reminders">No reminders set. Create one to get started!</p>
            ) : (
              notifications
                .filter(n => n.is_enabled && !n.is_sent)
                .map(notification => (
                  <div key={notification.id} className="reminder-item">
                    <div className="reminder-content">
                      <div className="reminder-toggle">
                        <Clock size={18} />
                        <span>{formatScheduledTime(notification.scheduled_time)}</span>
                      </div>
                      <div className="reminder-details">
                        <strong>{notification.title}</strong>
                        <p>{notification.message}</p>
                        <span className="reminder-type">{notification.notification_type}</span>
                        {notification.is_recurring && (
                          <span className="recurring-badge">Recurring: {notification.recurrence_pattern}</span>
                        )}
                      </div>
                    </div>
                    <button
                      onClick={() => disableNotification(notification.id)}
                      className="delete-reminder"
                      aria-label="Disable reminder"
                    >
                      <X size={18} />
                    </button>
                  </div>
                ))
            )}
          </div>
        </div>
      )}

      {!enabled && (
        <div className="notification-info">
          <p>Enable notifications to receive helpful reminders for:</p>
          <ul>
            <li>Feeding schedules</li>
            <li>Daily check-ins</li>
            <li>Diaper changes</li>
            <li>Sleep tracking</li>
          </ul>
        </div>
      )}
    </div>
  )
}

export default NotificationManager
