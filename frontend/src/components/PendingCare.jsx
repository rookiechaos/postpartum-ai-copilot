import React, { useId, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useCareSession } from '../utils/CareSession'
import './PendingCare.css'

// This is a view of registered session work, not a draft store or a retry queue.
export default function PendingCare({ activeTab, onNavigate }) {
  const { t } = useTranslation()
  const { work } = useCareSession()
  const [page, setPage] = useState('all')
  const filterId = useId()
  const items = Object.entries(work).map(([key, item]) => ({ key, ...item }))
    .sort((first, second) => Number(Boolean(second.critical)) - Number(Boolean(first.critical))
      || (first.priority ?? 5) - (second.priority ?? 5))
  const attention = items.filter(item => item.critical || item.attention)
  const pages = ['dashboard', 'tracking', 'chat', 'support', 'settings', 'family', 'checkin', 'night']
  const filtered = page === 'all' ? items : items.filter(item => item.tab === page)

  if (!items.length) return null

  return <aside className="pending-care" aria-label={t('experience.trackedWorkTitle')}>
    {attention.length > 0 && <div className="pending-care-attention">
      <div><p className="pending-care-attention-count" role="status">{t('taskFlow.attentionCount', { count: attention.length })}</p>
        <p>{t(attention[0].title)}</p></div>
      <button type="button" className="pending-care-open"
        aria-label={t('experience.trackedWorkOpenItem', { title: t(attention[0].title) })}
        onClick={() => onNavigate(attention[0].tab, attention[0].detail)}>{t('experience.trackedWorkOpen')}</button>
    </div>}
    <details>
      <summary>
        <span className="pending-care-title">{t('experience.trackedWorkTitle')}</span>
        <span className="pending-care-count" role="status">{t('experience.trackedWorkCount', { count: items.length })}</span>
      </summary>
      <p className="pending-care-hint">{t('experience.trackedWorkHint')}</p>
      <div className="pending-care-filter">
        <label htmlFor={filterId}>{t('taskFlow.filter')}</label>
        <select id={filterId} value={page} onChange={event => setPage(event.target.value)}>
          <option value="all">{t('taskFlow.all', { count: items.length })}</option>
          {pages.map(tab => <option key={tab} value={tab}>{t('taskFlow.pageCount', {
            page: t(`taskFlow.pages.${tab}`), count: items.filter(item => item.tab === tab).length,
          })}</option>)}
        </select>
        <p role="status">{t('taskFlow.shown', { count: filtered.length, total: items.length })}</p>
      </div>
      <ul className="pending-care-list">
        {filtered.map(item => <li key={item.key} className={item.critical ? 'pending-care-item pending-care-item--priority' : 'pending-care-item'}>
          <div className="pending-care-copy">
            <strong>{t(item.title)}</strong>
            <span className="pending-care-here">{t(`taskFlow.pages.${item.tab}`, { defaultValue: t('experience.trackedWorkTitle') })}
              {activeTab === item.tab ? ` · ${t('experience.trackedWorkHere')}` : ''}</span>
          </div>
          <button type="button" className="pending-care-open"
            aria-label={t('experience.trackedWorkOpenItem', { title: t(item.title) })}
            onClick={() => onNavigate(item.tab, item.detail)}>{t('experience.trackedWorkOpen')}</button>
        </li>)}
      </ul>
      {filtered.length === 0 && <div className="pending-care-empty"><p>{t('taskFlow.empty')}</p>
        <button type="button" className="text-action" onClick={() => setPage('all')}>{t('taskFlow.clear')}</button></div>}
    </details>
  </aside>
}
