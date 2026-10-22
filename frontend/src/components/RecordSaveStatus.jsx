import React from 'react'
import { useTranslation } from 'react-i18next'
import { StatusMessage } from './ui'

const states = new Set(['saving', 'saved', 'offline', 'unconfirmed', 'unsaved', 'removing', 'removed',
  'removeFailed', 'restoring', 'restored', 'restoreFailed', 'undoing', 'undone', 'undoFailed'])
const detailedStates = new Set(['offline', 'unconfirmed', 'unsaved', 'removeFailed', 'restoreFailed', 'undoFailed'])

export default function RecordSaveStatus({ status }) {
  const { t } = useTranslation()
  if (!states.has(status)) return null
  const detail = detailedStates.has(status) ? t(`localCare.record.statusDetails.${status}`) : ''
  const tone = ['saved', 'removed', 'restored', 'undone'].includes(status) ? 'success'
    : ['offline', 'unconfirmed', 'unsaved'].includes(status) ? 'warning' : status.endsWith('Failed') ? 'error' : 'info'
  return <StatusMessage tone={tone} title={t(`localCare.record.statuses.${status}`)}>
    {detail && <p>{detail}</p>}
  </StatusMessage>
}
