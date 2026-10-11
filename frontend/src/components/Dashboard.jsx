import React, { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { Baby, MessageCircle, Phone, Heart, Moon } from 'lucide-react'
import api from '../utils/api'
import { japanDay } from '../utils/japanTime'
import './Dashboard.css'

export default function Dashboard({ userId, userContext, onNavigate, onNightMode }) {
  const { t } = useTranslation()
  const [entries, setEntries] = useState(null)
  const [error, setError] = useState(false)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let active = true
    setError(false)
    api.getTracking(userId, 2).then(data => {
      if (active) setEntries(data.filter(entry => japanDay(entry.timestamp) === japanDay()))
    }).catch(() => { if (active) setError(true) })
    return () => { active = false }
  }, [userId, attempt])

  const actions = [
    { icon: <Baby />, title: t('pilot.recordTitle'), description: t('pilot.recordDescription'), action: () => onNavigate('tracking', 'feeding') },
    { icon: <MessageCircle />, title: t('pilot.askTitle'), description: t('pilot.askDescription'), action: () => onNavigate('chat') },
    { icon: <Phone />, title: t('pilot.supportTitle'), description: t('pilot.findHelpDescription'), action: () => onNavigate('support') },
  ]
  return <div className="dashboard family-dashboard">
    <header className="dashboard-header">
      <div><h2>{t('pilot.familyHeading')}</h2><p>{userContext?.babyName ? t('dashboard.howIsBaby', { name: userContext.babyName }) : t('pilot.todayIntro')}</p></div>
    </header>
    <div className="family-primary-actions">
      {actions.map(action => <button key={action.title} className="family-action" onClick={action.action}>
        {action.icon}<strong>{action.title}</strong><span>{action.description}</span>
      </button>)}
    </div>
    <section className="pilot-panel">
      <h3>{t('pilot.quickRecord')}</h3>
      <div className="pilot-actions">
        {['feeding', 'diaper', 'sleep', 'pumping'].map(type => <button key={type} className="pilot-button secondary"
          onClick={() => onNavigate('tracking', type)}>{t(`tracking.${type}`)}</button>)}
      </div>
      <p>{t('pilot.noPressure')}</p>
    </section>
    <section className="pilot-panel">
      <h3>{t('pilot.todayRecords')}</h3>
      <p>{t('pilot.japanTime')}</p>
      {error ? <div role="status"><p>{t('pilot.loadFailed')}</p><button className="pilot-button secondary" onClick={() => setAttempt(value => value + 1)}>{t('pilot.retry')}</button></div>
        : entries === null ? <p>{t('common.loading')}</p>
        : entries.length === 0 ? <p>{t('tracking.noEntries')}</p>
        : <div className="stats-grid">
          <div className="stat-card"><strong>{entries.filter(entry => entry.entry_type === 'feeding').length}</strong><span>{t('dashboard.todayFeeds')}</span></div>
          <div className="stat-card"><strong>{entries.filter(entry => entry.entry_type === 'diaper').length}</strong><span>{t('dashboard.diaperChanges')}</span></div>
          <div className="stat-card"><strong>{entries.reduce((sum, entry) => sum + (entry.entry_type === 'sleep' ? entry.sleep_duration_minutes || 0 : 0), 0)}</strong><span>{t('pilot.totalSleep')}</span></div>
        </div>}
    </section>
    <section className="pilot-panel">
      <h3>{t('pilot.startWithSituation')}</h3>
      <div className="pilot-actions">
        {['crying', 'feeding', 'rest', 'appointment'].map(scene => <button key={scene} className="pilot-button secondary"
          onClick={() => onNavigate('chat', t(`pilot.questions.${scene}`))}>{t(`pilot.scenes.${scene}`)}</button>)}
      </div>
    </section>
    <div className="pilot-actions">
      <button className="pilot-button secondary" onClick={() => onNavigate('checkin')}><Heart size={18} />{t('checkin.title')}</button>
      <button className="pilot-button secondary" onClick={onNightMode}><Moon size={18} />{t('nightMode.title')}</button>
    </div>
  </div>
}
