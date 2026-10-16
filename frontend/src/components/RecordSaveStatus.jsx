import React from 'react'
import { useTranslation } from 'react-i18next'

const states = new Set(['saving', 'saved', 'offline', 'unconfirmed', 'unsaved', 'removing', 'removed',
  'removeFailed', 'restoring', 'restored', 'restoreFailed', 'undoing', 'undone', 'undoFailed'])
const detailedStates = new Set(['offline', 'unconfirmed', 'unsaved', 'removeFailed', 'restoreFailed', 'undoFailed'])

export default function RecordSaveStatus({ status }) {
  const { t } = useTranslation()
  if (!states.has(status)) return null
  const detail = detailedStates.has(status) ? t(`localCare.record.statusDetails.${status}`) : ''
  return <div className="record-save-status" role="status">
    <p><strong>{t(`localCare.record.statuses.${status}`)}</strong></p>
    {detail && <p>{detail}</p>}
  </div>
}
