import React, { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../utils/api'
import taskManager from '../utils/taskManager'
import { japanDateTime } from '../utils/japanTime'
import AIUseNotice from './AIUseNotice'
import Charts from './Charts'
import { useToast } from './Toast'
import './TrackingPanel.css'

const types = ['feeding', 'diaper', 'sleep', 'mood', 'pumping', 'recovery']

export default function TrackingPanel({ userId, initialEntryType }) {
  const { t, i18n } = useTranslation()
  const toast = useToast()
  const [entries, setEntries] = useState([])
  const [summary, setSummary] = useState(null)
  const [showAddForm, setShowAddForm] = useState(types.includes(initialEntryType))
  const [entryType, setEntryType] = useState(types.includes(initialEntryType) ? initialEntryType : 'feeding')
  const [loading, setLoading] = useState(false)
  const [showCharts, setShowCharts] = useState(false)
  const [acceptedAI, setAcceptedAI] = useState(false)
  const [summaryLoading, setSummaryLoading] = useState(false)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let active = true
    setError('')
    api.getTracking(userId, 7).then(data => { if (active) setEntries(data) })
      .catch(() => { if (active) setError(t('pilot.loadFailed')) })
    return () => { active = false }
  }, [userId, attempt])

  const addEntry = async formData => {
    setLoading(true)
    try {
      await api.addTrackingEntry({ ...formData, user_id: userId })
      setShowAddForm(false)
      setSummary(null)
      setAttempt(value => value + 1)
      toast.success(t('pilot.recordSaved'))
    } catch { toast.error(t('pilot.recordFailed')) }
    finally { setLoading(false) }
  }
  const loadSummary = async () => {
    if (!acceptedAI || summaryLoading) return
    setSummaryLoading(true)
    try {
      const result = import.meta.env.VITE_ASYNC_MODE !== 'false'
        ? await taskManager.submitTask('tracking_analysis', { user_id: userId, days: 7, language: i18n.language }, { priority: 'low', timeout: 120000 })
        : await api.getTrackingSummary(userId, 7)
      setSummary(result)
    }
    catch { toast.error(t('pilot.chatUnavailable')) }
    finally { setSummaryLoading(false) }
  }

  return <div className="tracking-panel">
    <div className="tracking-header"><h2>{t('tracking.title')}</h2>
      <button className="add-button" onClick={() => setShowAddForm(value => !value)}>{showAddForm ? t('tracking.cancel') : `+ ${t('tracking.addEntry')}`}</button></div>
    <p>{t('pilot.noPressure')}</p>
    {showAddForm && <EntryForm key={entryType} entryType={entryType} onEntryTypeChange={setEntryType}
      onSubmit={addEntry} onCancel={() => setShowAddForm(false)} loading={loading} />}
    {error && <p role="alert">{error}<button className="pilot-button secondary" onClick={() => setAttempt(value => value + 1)}>{t('pilot.retry')}</button></p>}
    <section className="entries-list"><h3>{t('tracking.recentEntries')}</h3><p>{t('pilot.japanTime')}</p>
      {!error && entries.length === 0 && <p>{t('tracking.noEntries')}</p>}
      {entries.map(entry => <article key={entry.id} className="entry-card">
        <div className="entry-header"><strong>{t(`tracking.${entry.entry_type}`)}</strong><time>{japanDateTime(entry.timestamp, i18n.language)}</time></div>
        <div className="entry-details">
          {entry.feeding_type && <span>{t(`tracking.${entry.feeding_type}`)}</span>}
          {entry.diaper_type && <span>{t(`tracking.${entry.diaper_type}`)}</span>}
          {entry.duration_minutes != null && <span>{entry.duration_minutes} {t('pilot.minutes')}</span>}
          {entry.amount_ml != null && <span>{entry.amount_ml} mL</span>}
          {entry.pumped_amount_ml != null && <span>{entry.pumped_amount_ml} mL</span>}
          {entry.sleep_duration_minutes != null && <span>{entry.sleep_duration_minutes} {t('pilot.minutes')}</span>}
          {entry.mood_level && <span>{t(`tracking.${entry.mood_level}`)}</span>}
          {entry.weight_kg != null && <span>{entry.weight_kg} kg</span>}
          {entry.breast_condition && <span>{t(`tracking.${entry.breast_condition}`)}</span>}
        </div>
        {['notes', 'mood_notes', 'recovery_notes'].map(key => entry[key] && <p key={key} className="entry-notes">{entry[key]}</p>)}
      </article>)}
    </section>
    <details className="pilot-panel"><summary>{t('pilot.optionalAnalysis')}</summary>
      <button className="pilot-button secondary" onClick={() => setShowCharts(value => !value)}>{t(showCharts ? 'tracking.hideCharts' : 'tracking.showCharts')}</button>
      {showCharts && <Charts userId={userId} refreshKey={attempt} onRecord={() => setShowAddForm(true)} />}
      <AIUseNotice accepted={acceptedAI} onChange={setAcceptedAI} />
      <button className="pilot-button secondary" disabled={!acceptedAI || summaryLoading || entries.length === 0} onClick={loadSummary}>{t(summaryLoading ? 'common.loading' : 'pilot.analyzeRecords')}</button>
      {summary && <div className="ai-summary"><p>{t('pilot.aiLabel')}</p>
        {['patterns', 'insights', 'recommendations'].map(key => summary[key]?.length > 0 && <section key={key}>
          <h3>{t(`tracking.${key}`)}</h3><ul>{summary[key].map((value, index) => <li key={index}>{value}</li>)}</ul>
        </section>)}
      </div>}
    </details>
  </div>
}

function EntryForm({ entryType, onEntryTypeChange, onSubmit, onCancel, loading }) {
  const { t } = useTranslation()
  const [formData, setFormData] = useState({})
  const fields = {
    feeding: [['feeding_type', 'feedingType', ['breast', 'formula', 'mixed']], ['duration_minutes', 'duration', 'number'], ['amount_ml', 'amount', 'number']],
    diaper: [['diaper_type', 'diaperType', ['wet', 'dirty', 'both']]],
    sleep: [['sleep_duration_minutes', 'duration', 'number'], ['sleep_quality', 'quality', ['peaceful', 'restless', 'interrupted']]],
    mood: [['mood_level', 'moodLevel', ['very_low', 'low', 'neutral', 'good', 'very_good']], ['mood_notes', 'notes', 'textarea']],
    pumping: [['pumped_amount_ml', 'amount', 'number']],
    recovery: [['weight_kg', 'weight', 'number'], ['breast_condition', 'breastCondition', ['normal', 'engorged', 'blocked', 'painful', 'other']], ['recovery_notes', 'recoveryNotes', 'textarea']],
  }
  return <form className="entry-form" onSubmit={event => {
    event.preventDefault()
    if (!loading) onSubmit({ ...formData, entry_type: entryType, timestamp: new Date().toISOString() })
  }}><fieldset disabled={loading}>
    <label>{t('tracking.entryType')}<select value={entryType} onChange={event => onEntryTypeChange(event.target.value)}>
      {types.map(type => <option key={type} value={type}>{t(`tracking.${type}`)}</option>)}
    </select></label>
    {fields[entryType].map(([key, label, kind]) => <label key={key}>{t(`tracking.${label}`)}
      {Array.isArray(kind) ? <select value={formData[key] || ''} onChange={event => setFormData({ ...formData, [key]: event.target.value || null })}>
        <option value="">{t('common.select')}</option>{kind.map(value => <option key={value} value={value}>{t(`tracking.${value}`)}</option>)}
      </select> : kind === 'textarea' ? <textarea value={formData[key] || ''} maxLength={2000} rows={3}
        onChange={event => setFormData({ ...formData, [key]: event.target.value })} />
        : <input type="number" min="0" step={key.endsWith('_minutes') ? '1' : '0.1'} value={formData[key] ?? ''}
          onChange={event => setFormData({ ...formData, [key]: event.target.value === '' ? null : Number(event.target.value) })} />}
    </label>)}
    <label>{t('tracking.notes')}<textarea rows={2} maxLength={2000} value={formData.notes || ''} onChange={event => setFormData({ ...formData, notes: event.target.value })} /></label>
    <div className="form-actions"><button type="button" onClick={onCancel}>{t('tracking.cancel')}</button>
      <button type="submit">{t(loading ? 'tracking.adding' : 'tracking.addEntryButton')}</button></div>
  </fieldset></form>
}
