import React from 'react'
import { useTranslation } from 'react-i18next'
import RecordTime from './RecordTime'

export default function DuplicateReview({ review, onContinue, onCancel, disabled, continueDisabled = false }) {
  const { t } = useTranslation()
  if (!review) return null
  return <section className="pilot-panel duplicate-review" role="region" aria-label={t('continuity.duplicate.title')}>
    <h4>{t('continuity.duplicate.title')}</h4><p>{t(review.failed ? 'continuity.duplicate.unavailable' : 'continuity.duplicate.notice')}</p>
    <ul>{review.matches.map(record => <li key={record.record_key}>
      <strong>{t(`tracking.${record.entry_type}`)}</strong> · {record.recorder_label || t('continuity.duplicate.familyMember')}
      <RecordTime value={record.timestamp} />
      {['amount_ml', 'duration_minutes', 'sleep_duration_minutes'].map(key => record[key] != null && <span key={key}>{record[key]} {key === 'amount_ml' ? 'mL' : t('pilot.minutes')} </span>)}
    </li>)}</ul>
    <div className="pilot-actions"><button type="button" className="pilot-button" disabled={disabled || continueDisabled} onClick={onContinue}>{t('continuity.duplicate.continue')}</button>
      <button type="button" className="pilot-button secondary" disabled={disabled} onClick={onCancel}>{t('continuity.duplicate.cancel')}</button></div>
  </section>
}
