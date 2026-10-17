import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../utils/api'
import { japanDay, utcDate } from '../utils/japanTime'
import RecordTime, { useRecordClock } from './RecordTime'
import RecordSheet from './RecordSheet'
import useConnection from '../utils/useConnection'

export default function CareTimeline({ entries, userId, visible, refreshKey, error, onReload, onFullEdit, onRecordsChanged, blocked }) {
  const { t } = useTranslation()
  const { reconnections } = useConnection()
  const now = useRecordClock(visible)
  const day = japanDay()
  const [scope, setScope] = useState('')
  const [families, setFamilies] = useState([])
  const [familyData, setFamilyData] = useState(null)
  const [familyError, setFamilyError] = useState(false)
  const [attempt, setAttempt] = useState(0)
  const [filter, setFilter] = useState('all')
  const [detail, setDetail] = useState(null)
  useEffect(() => {
    if (!visible) return
    let active = true
    api.get('/api/families/').then(result => {
      if (!active) return
      setFamilies(result)
      if (scope && !result.some(family => family.family_id === scope)) { setScope(''); setFamilyData(null); setDetail(null) }
    }).catch(() => { if (active) { setFamilies([]); if (scope) { setFamilyError(true); setFamilyData(null); setDetail(null) } } })
    return () => { active = false }
  }, [userId, visible, refreshKey, reconnections, attempt, scope])
  useEffect(() => {
    if (!scope) return
    if (!visible) { setFamilyData(null); setDetail(null); return }
    let active = true
    setFamilyError(false)
    api.get(`/api/families/${scope}/timeline`).then(result => {
      if (!active) return
      setFamilyData(result)
      setDetail(previous => previous ? result.records.find(entry => entry.record_key === previous.record_key) || null : null)
    }).catch(() => { if (active) { setFamilyError(true); setFamilyData(null); setDetail(null) } })
    return () => { active = false }
  }, [scope, visible, refreshKey, reconnections, attempt, day])
  useEffect(() => {
    if (!visible || !scope) return
    const refresh = () => setAttempt(value => value + 1)
    const timer = setInterval(refresh, 30000)
    window.addEventListener('focus', refresh)
    return () => { clearInterval(timer); window.removeEventListener('focus', refresh) }
  }, [visible, scope])
  const rows = (scope ? familyData?.family_id === scope && familyData.day === day ? familyData.records : null : entries)
  const shown = rows?.filter(entry => japanDay(entry.timestamp) === day && (filter === 'all' || entry.entry_type === filter))
    .sort((a, b) => utcDate(b.timestamp) - utcDate(a.timestamp))
  const name = entry => [t(`tracking.${entry.entry_type}`), entry.diaper_type && t(`tracking.${entry.diaper_type}`),
    entry.feeding_type && t(`tracking.${entry.feeding_type}`)].filter(Boolean).join(' · ')
  return <section className="pilot-panel care-timeline"><h3>{t('interaction.timeline.title')}</h3>
    <p>{t('pilot.japanTime')} · {day}</p>
    <label>{t('interaction.timeline.scope')}<select value={scope} disabled={Boolean(detail)} onChange={event => {
      setScope(event.target.value); setFamilyData(null); setFamilyError(false); setDetail(null)
    }}>
      <option value="">{t('interaction.timeline.mine')}</option>
      {families.map(family => <option value={family.family_id} key={family.family_id}>{t('interaction.timeline.family', { name: family.name })}</option>)}
    </select></label>
    <p className="field-hint">{t(scope ? 'interaction.timeline.familyNotice' : 'interaction.timeline.ownNotice')}</p>
    <div className="timeline-filters pilot-actions" role="group" aria-label={t('interaction.timeline.filter')}>
      {['all', 'feeding', 'diaper', 'sleep'].map(kind => <button type="button" key={kind} className="pilot-button secondary"
        aria-pressed={filter === kind} onClick={() => setFilter(kind)}>{t(kind === 'all' ? 'interaction.timeline.all' : `tracking.${kind}`)}</button>)}
    </div>
    {(scope ? familyError : error) ? <p role="alert">{t('pilot.loadFailed')} <button type="button" className="text-action"
      onClick={() => { if (scope) setAttempt(value => value + 1); else onReload() }}>{t('pilot.retry')}</button></p>
      : !shown ? <p role="status">{t('common.loading')}</p>
      : shown.length === 0 ? <p>{t('interaction.timeline.empty')}</p>
      : <ol className="day-timeline">{shown.map(entry => <li key={entry.record_key}>
        <button type="button" className="timeline-record" disabled={blocked} onClick={() => setDetail(entry)}>
          <strong>{name(entry)}</strong><RecordTime value={entry.timestamp} now={now} />
          <small>{!scope ? t('polish.recordedByYou') : t('polish.recordedBy', { name: entry.recorder_label || t('polish.memberNumber', { number: entry.recorder_number || '?' }) })}</small>
          {scope && entry.is_own && <small>{t('polish.recordedByYou')}</small>}
          {['amount_ml', 'duration_minutes', 'sleep_duration_minutes', 'pumped_amount_ml'].map(key => entry[key] != null && <span key={key}>
            {entry[key]} {key.endsWith('_ml') ? 'mL' : t('pilot.minutes')}</span>)}
          <span className="text-action">{t('interaction.timeline.details')}</span>
        </button>
      </li>)}</ol>}
    {detail && <RecordSheet key={detail.record_key} record={detail} own={!scope} visible={visible} onClose={() => setDetail(null)}
      onFullEdit={onFullEdit} onSaved={result => { setDetail(result); onRecordsChanged() }} />}
  </section>
}
