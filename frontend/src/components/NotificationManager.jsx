import React, { useState, useEffect, useCallback, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../utils/api'
import useConnection from '../utils/useConnection'
import { japanDateTime } from '../utils/japanTime'
import './NotificationManager.css'

const permissionEvent = 'postpartum-notification-permission'
const deliveryEvent = 'postpartum-notification-delivery'

function useNotificationPermission() {
  const read = () => 'Notification' in window ? Notification.permission : 'unsupported'
  const [permission, setPermission] = useState(read)
  useEffect(() => {
    const update = () => setPermission(read())
    window.addEventListener('focus', update)
    window.addEventListener(permissionEvent, update)
    return () => { window.removeEventListener('focus', update); window.removeEventListener(permissionEvent, update) }
  }, [])
  return permission
}

// Mounted for the family login session, independently of the settings page.
// The account-bound database queue works across API/worker processes. Neither a
// worker send nor a GET marks delivery; the browser acknowledges acceptance.
export function NotificationDelivery({ userId }) {
  const { t } = useTranslation()
  const permission = useNotificationPermission()
  const { online, reconnections } = useConnection()
  const shown = useRef(new Set())
  const [failed, setFailed] = useState(false)
  useEffect(() => {
    if (!userId || permission !== 'granted' || !online) return
    let active = true
    let inFlight = false
    const notices = new Set()
    const workerTags = new Map()
    const controller = new AbortController()
    const closeWorkerNotice = async (registration, tag) => {
      try { (await registration.getNotifications({ tag })).forEach(item => item.close()) } catch {}
    }
    const show = async id => {
      const tag = `postpartum-reminder-${id}`
      const options = { body: t('notifications.genericBody'), icon: '/icon.svg', tag, data: { url: '/family' } }
      let registration = null
      if ('serviceWorker' in navigator) registration = await navigator.serviceWorker.getRegistration().catch(() => null)
      if (!active) return false
      if (registration?.active && typeof registration.showNotification === 'function') {
        if (!workerTags.has(registration)) workerTags.set(registration, new Set())
        workerTags.get(registration).add(tag)
        await registration.showNotification(t('notifications.genericTitle'), options)
        if (!active) { await closeWorkerNotice(registration, tag); return false }
      } else {
        const notice = new Notification(t('notifications.genericTitle'), options)
        notices.add(notice)
        notice.onclose = () => notices.delete(notice)
        notice.onclick = () => { window.focus(); notice.close() }
      }
      return true
    }
    const poll = async () => {
      if (!active || inFlight || document.visibilityState !== 'visible') return
      inFlight = true
      let acknowledged = false
      try {
        const due = await api.get('/api/notifications/due', { signal: controller.signal })
        if (!active) return
        for (const reminder of due) {
          if (!active) return
          if (!shown.current.has(reminder.id)) {
            if (!await show(reminder.id)) return
            shown.current.add(reminder.id)
          }
          const receipt = await api.post(`/api/notifications/${reminder.id}/acknowledge`, {}, { signal: controller.signal })
          if (!active) return
          if (!receipt?.acknowledged) throw new Error('Reminder acknowledgment unavailable')
          acknowledged = true
        }
        setFailed(false)
      } catch { if (active) setFailed(true) }
      finally {
        inFlight = false
        if (active && acknowledged) window.dispatchEvent(new Event(deliveryEvent))
      }
    }
    poll()
    const timer = setInterval(poll, 30000)
    window.addEventListener('focus', poll)
    document.addEventListener('visibilitychange', poll)
    return () => {
      active = false; controller.abort(); clearInterval(timer)
      window.removeEventListener('focus', poll); document.removeEventListener('visibilitychange', poll)
      notices.forEach(item => item.close())
      workerTags.forEach((tags, registration) => tags.forEach(tag => closeWorkerNotice(registration, tag)))
    }
  }, [userId, permission, online, reconnections, t])
  return failed && permission === 'granted' ? <p role="status" className="notification-delivery-status">{t('notifications.deliveryFailed')}</p> : null
}

export default function NotificationManager({ userId }) {
  const { t, i18n } = useTranslation()
  const permission = useNotificationPermission()
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
    window.addEventListener(deliveryEvent, load)
    return () => window.removeEventListener(deliveryEvent, load)
  }, [load])
  const requestPermission = async () => {
    setError('')
    try { await Notification.requestPermission(); window.dispatchEvent(new Event(permissionEvent)) }
    catch { setError(t('notifications.permissionFailed')) }
  }
  const disable = async id => {
    if (loading) return
    setLoading(true)
    try { await api.delete(`/api/notifications/${encodeURIComponent(id)}`); await load() }
    catch (failure) { await load(); setError(t(failure.status === 409 ? 'notifications.changed' : 'notifications.failed')) }
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
