import React, { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../utils/api'
import websocketManager from '../utils/websocketManager'
import { japanDateTime } from '../utils/japanTime'
import './NotificationManager.css'

export default function NotificationManager({ userId }) {
  const { t, i18n } = useTranslation()
  const [permission, setPermission] = useState(() => 'Notification' in window ? Notification.permission : 'unsupported')
  const [notifications, setNotifications] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const load = useCallback(async () => {
    setLoading(true); setError('')
    try { setNotifications(await api.get('/api/notifications/?include_sent=false&limit=100')) }
    catch { setError(t('pilot.loadFailed')) }
    finally { setLoading(false) }
  }, [userId, t])
  useEffect(() => { load() }, [load])
  useEffect(() => {
    const visible = new Set()
    const receive = data => {
      load()
      if (permission !== 'granted') return
      try {
        // Keep care details off the lock screen; the user can open the authenticated app.
        const notification = new Notification(t('notifications.genericTitle'), {
          body: t('notifications.genericBody'), icon: '/icon-192x192.png',
          tag: `notification-${data.notification_id}`,
        })
        visible.add(notification)
        notification.onclose = () => visible.delete(notification)
        notification.onclick = () => { window.focus(); notification.close() }
      } catch { setError(t('notifications.failed')) }
    }
    const token = localStorage.getItem('access_token')
    if (token) websocketManager.connect(token)
    websocketManager.on('notification', receive)
    return () => { websocketManager.off('notification', receive); visible.forEach(item => item.close()) }
  }, [permission, load, t])
  const requestPermission = async () => {
    setError('')
    try { setPermission(await Notification.requestPermission()) }
    catch { setError(t('notifications.permissionFailed')) }
  }
  const disable = async id => {
    if (loading) return
    setLoading(true)
    try { await api.delete(`/api/notifications/${encodeURIComponent(id)}`); await load() }
    catch { setError(t('notifications.failed')) }
    finally { setLoading(false) }
  }
  const pending = notifications.filter(item => item.is_enabled && !item.is_sent)
  return <section className="notification-manager">
    <div className="notification-header"><h3>{t('notifications.title')}</h3><p>{t('notifications.description')}</p></div>
    <p>{t('notifications.status')}: {t(`notifications.${permission}`)}</p>
    {permission === 'default' && <button className="pilot-button secondary" onClick={requestPermission}>{t('notifications.enable')}</button>}
    {permission === 'denied' && <p>{t('notifications.browserSettings')}</p>}
    <p>{t('notifications.privacy')}</p>
    {error && <p role="alert">{error} <button disabled={loading} onClick={load}>{t('pilot.retry')}</button></p>}
    <h4>{t('notifications.scheduled')}</h4>
    {loading ? <p role="status">{t('common.loading')}</p> : pending.length === 0 ? <p>{t('notifications.empty')}</p> : pending.map(item =>
      <article className="reminder-item" key={item.id}><div>
        <strong>{t(`notifications.types.${item.notification_type === 'mood_check' ? 'checkin' : item.notification_type}`, { defaultValue: t('notifications.genericTitle') })}</strong>
        <p>{japanDateTime(item.scheduled_time, i18n.language)}</p>
        {item.is_recurring && <span>{t('notifications.recurring')}</span>}
      </div><button disabled={loading} className="pilot-button secondary" onClick={() => disable(item.id)}>{t('notifications.disable')}</button></article>)}
  </section>
}
