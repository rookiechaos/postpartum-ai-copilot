import React, { useEffect, useId, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { ChevronRight, Clock, Droplets, Heart, Milk, Moon } from 'lucide-react'
import api from '../utils/api'
import { japanDay, utcDate } from '../utils/japanTime'
import RecordTime, { useRecordClock } from './RecordTime'
import RecordSheet from './RecordSheet'
import useConnection from '../utils/useConnection'
import { inCarePeriod } from '../utils/carePeriods'
import { CareRecordIdentity } from './CareSubject'
import { useCareSession } from '../utils/CareSession'
import CareScope from './CareScope'
import { japanDateTime } from '../utils/japanTime'
import { Button, EmptyState, ErrorMessage, FormField, PageHeader } from './ui'

const recordIcons = { feeding: Milk, diaper: Droplets, sleep: Moon, pumping: Milk, mood: Heart, recovery: Heart }
function RecordKindIcon({ kind }) {
  const Icon = recordIcons[kind] || Clock
  return <span className="timeline-record-symbol" aria-hidden="true"><Icon size={18} strokeWidth={1.8} /></span>
}

export default function CareTimeline({ entries, userId, visible, refreshKey, error, onReload, onFullEdit, onRecordsChanged, blocked, navigationRecord,
  compact = false, subjectId = '' }) {
  const { t, i18n } = useTranslation()
  const { subjects, rememberSubject } = useCareSession()
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
  const [period, setPeriod] = useState('last24')
  const [subjectFilter, setSubjectFilter] = useState(compact ? subjectId || '' : '')
  const [showAll, setShowAll] = useState(false)
  const [controlsOpen, setControlsOpen] = useState(false)
  const listId = useId()
  const previousSubject = useRef(subjectId)
  const handledRecord = useRef(null)
  useEffect(() => {
    if (!compact || previousSubject.current === subjectId) return
    previousSubject.current = subjectId
    // Changing the home baby explicitly returns to this account's own records.
    setSubjectFilter(subjectId || ''); setScope(''); setFamilyData(null); setDetail(null)
  }, [compact, subjectId])
  useEffect(() => { setShowAll(false) }, [period, scope, filter, subjectFilter])
  useEffect(() => {
    if (!visible || !navigationRecord || handledRecord.current === navigationRecord) return
    handledRecord.current = navigationRecord
    setScope(''); setSubjectFilter('')
    const recordedDay = japanDay(navigationRecord.timestamp)
    setPeriod(recordedDay === japanDay() ? 'today' : recordedDay === japanDay(new Date(Date.now() - 86400000)) ? 'yesterday' : 'last24')
    setDetail(navigationRecord)
  }, [visible, navigationRecord])
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
    api.get(`/api/families/${scope}/timeline?${new URLSearchParams({ period })}`).then(result => {
      if (!active) return
      setFamilyData(result)
      setDetail(previous => previous ? result.records.find(entry => entry.record_key === previous.record_key) || null : null)
    }).catch(() => { if (active) { setFamilyError(true); setFamilyData(null); setDetail(null) } })
    return () => { active = false }
  }, [scope, visible, refreshKey, reconnections, attempt, day, period])
  useEffect(() => {
    if (!visible || !scope) return
    const refresh = () => setAttempt(value => value + 1)
    const timer = setInterval(refresh, 30000)
    window.addEventListener('focus', refresh)
    return () => { clearInterval(timer); window.removeEventListener('focus', refresh) }
  }, [visible, scope])
  const rows = (scope ? familyData?.family_id === scope && familyData.period === period && familyData.day === day ? familyData.records : null : entries)
  const shown = rows?.filter(entry => inCarePeriod(entry, period, Date.now()) && (filter === 'all' || entry.entry_type === filter)
    && (!subjectFilter || (subjectFilter === 'unassigned' ? !entry.subject_id && !['mood', 'recovery'].includes(entry.entry_type) : entry.subject_id === subjectFilter)))
    .sort((a, b) => utcDate(b.timestamp) - utcDate(a.timestamp))
  const name = entry => [t(`tracking.${entry.entry_type}`), entry.diaper_type && t(`tracking.${entry.diaper_type}`),
    entry.feeding_type && t(`tracking.${entry.feeding_type}`)].filter(Boolean).join(' · ')
  const language = i18n.resolvedLanguage || 'ja'
  const periodLabel = period === 'last24'
    ? `${japanDateTime(new Date(now - 86400000), language)} 〜 ${japanDateTime(new Date(now), language)}`
    : japanDay(new Date(period === 'yesterday' ? now - 86400000 : now))
  const displayed = compact && !showAll ? shown?.slice(0, 3) : shown
  const Options = compact ? 'details' : 'div'
  return <section className={`pilot-panel care-timeline${compact ? ' care-timeline--compact' : ''}`}>
    <PageHeader headingLevel={3} title={t(compact ? 'foundation.home.recent' : 'continuity.period.title')} />
    <CareScope mode="view" subjectId={subjectFilter === 'unassigned' ? '' : subjectFilter || '*'}
      familyName={scope ? families.find(family => family.family_id === scope)?.name || t('interaction.timeline.familyNotice') : ''}
      onUseLast={!scope ? id => { rememberSubject(id); setSubjectFilter(id) } : undefined} />
    <p className="field-hint">{t('pilot.japanTime')} · {periodLabel}</p>
    <Options className="ui-disclosure timeline-options" {...(compact ? { open: controlsOpen, onToggle: event => {
      if (event.target === event.currentTarget) setControlsOpen(event.currentTarget.open)
    } } : {})}>
    {compact && <summary>{t('foundation.home.filters')}</summary>}
    <div className="pilot-actions" role="group" aria-label={t('continuity.period.choose')}>
      {['last24', 'today', 'yesterday'].map(value => <Button key={value} variant="secondary"
        aria-pressed={period === value} onClick={() => { setPeriod(value); setFamilyData(null) }}>{t(`continuity.period.${value}`)}</Button>)}
    </div><p>{t('continuity.period.notice')}</p>
    <FormField as="select" label={t('interaction.timeline.scope')} value={scope} disabled={Boolean(detail)} onChange={event => {
      setScope(event.target.value); setSubjectFilter(''); setFamilyData(null); setFamilyError(false); setDetail(null)
    }}>
      <option value="">{t('interaction.timeline.mine')}</option>
      {families.map(family => <option value={family.family_id} key={family.family_id}>{t('interaction.timeline.family', { name: family.name })}</option>)}
    </FormField>
    {!scope && <FormField as="select" label={t('continuity.subject.filter')} value={subjectFilter} onChange={event => {
      setSubjectFilter(event.target.value); if (event.target.value && event.target.value !== 'unassigned') rememberSubject(event.target.value)
    }}>
      <option value="">{t('continuity.subject.all')}</option><option value="unassigned">{t('continuity.subject.unknown')}</option>
      {subjects.map(item => <option key={item.subject_id} value={item.subject_id}>{item.nickname} · {item.family_name || t('continuity.subject.personal')}</option>)}
    </FormField>}
    <p className="field-hint">{t(scope ? 'interaction.timeline.familyNotice' : 'interaction.timeline.ownNotice')}</p>
    <div className="timeline-filters pilot-actions" role="group" aria-label={t('interaction.timeline.filter')}>
      {['all', 'feeding', 'diaper', 'sleep'].map(kind => <Button key={kind} variant="secondary"
        aria-pressed={filter === kind} onClick={() => setFilter(kind)}>{t(kind === 'all' ? 'interaction.timeline.all' : `tracking.${kind}`)}</Button>)}
    </div>
    </Options>
    {compact && filter !== 'all' && <p className="timeline-active-filter">{t('interaction.timeline.filter')}: {t(`tracking.${filter}`)}</p>}
    {(scope ? familyError : error) ? <ErrorMessage title={t('pilot.loadFailed')}
      onRetry={() => { if (scope) setAttempt(value => value + 1); else onReload() }} />
      : !shown ? <p role="status">{t('common.loading')}</p>
      : shown.length === 0 ? <EmptyState compact icon={false} suggestions={[]} headingLevel={4}
        title={t('continuity.period.empty')} description={compact ? t('foundation.home.filterNotice') : ''} />
      : <ol className="day-timeline" id={listId}>{displayed.map(entry => <li key={entry.record_key}>
        <button type="button" className="timeline-record" disabled={blocked} onClick={() => setDetail(entry)}>
          <strong className="timeline-record-title">{compact && <RecordKindIcon kind={entry.entry_type} />}{name(entry)}</strong><RecordTime value={entry.timestamp} now={now} />
          <CareRecordIdentity record={entry} />
          {!compact && entry.end_timestamp && <span>{t('continuity.period.ended', { time: japanDateTime(entry.end_timestamp, i18n.resolvedLanguage || 'ja') })}</span>}
          <small>{!scope ? t('polish.recordedByYou') : t('polish.recordedBy', { name: entry.recorder_label || t('polish.memberNumber', { number: entry.recorder_number || '?' }) })}</small>
          {scope && entry.is_own && <small>{t('polish.recordedByYou')}</small>}
          {['amount_ml', 'duration_minutes', 'sleep_duration_minutes', 'pumped_amount_ml'].map(key => entry[key] != null && <span className="timeline-record-value" key={key}>
            {entry[key]} {key.endsWith('_ml') ? 'mL' : t('pilot.minutes')}</span>)}
          <span className="text-action">{t('interaction.timeline.details')}{compact && <ChevronRight size={14} aria-hidden="true" />}</span>
        </button>
      </li>)}</ol>}
    {compact && !(scope ? familyError : error) && shown?.length > 3 && <Button variant="secondary" aria-expanded={showAll} aria-controls={listId}
      onClick={() => setShowAll(value => !value)}>{t(showAll ? 'foundation.home.showLess' : 'foundation.home.showMore', { count: shown.length })}</Button>}
    {detail && <RecordSheet key={detail.record_key} record={detail} own={!scope} visible={visible} onClose={() => setDetail(null)}
      onFullEdit={onFullEdit} onSaved={result => { setDetail(result); onRecordsChanged() }} />}
  </section>
}
