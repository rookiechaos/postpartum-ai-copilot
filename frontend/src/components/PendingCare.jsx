import React from 'react'
import { useTranslation } from 'react-i18next'
import { useCareSession } from '../utils/CareSession'
import './PendingCare.css'

// This is a view of registered session work, not a draft store or a retry queue.
export default function PendingCare({ activeTab, onNavigate }) {
  const { t } = useTranslation()
  const { work } = useCareSession()
  const items = Object.entries(work).map(([key, item]) => ({ key, ...item }))
    .sort((first, second) => Number(Boolean(second.critical)) - Number(Boolean(first.critical))
      || (first.priority ?? 5) - (second.priority ?? 5))

  if (!items.length) return null

  return <aside className="pending-care" aria-label={t('experience.trackedWorkTitle')}>
    <details>
      <summary>
        <span className="pending-care-title">{t('experience.trackedWorkTitle')}</span>
        <span className="pending-care-count" role="status">{t('experience.trackedWorkCount', { count: items.length })}</span>
      </summary>
      <p className="pending-care-hint">{t('experience.trackedWorkHint')}</p>
      <ul className="pending-care-list">
        {items.map(item => <li key={item.key} className={item.critical ? 'pending-care-item pending-care-item--priority' : 'pending-care-item'}>
          <div className="pending-care-copy">
            <strong>{t(item.title)}</strong>
            {activeTab === item.tab && <span className="pending-care-here">{t('experience.trackedWorkHere')}</span>}
          </div>
          <button type="button" className="pending-care-open"
            aria-label={t('experience.trackedWorkOpenItem', { title: t(item.title) })}
            onClick={() => onNavigate(item.tab, item.detail)}>{t('experience.trackedWorkOpen')}</button>
        </li>)}
      </ul>
    </details>
  </aside>
}
