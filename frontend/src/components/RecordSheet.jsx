import React, { useEffect, useId, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { buildCareSummary } from '../utils/careSummary'
import RecordTime from './RecordTime'
import RecordEditor from './RecordEditor'

export default function RecordSheet({ record, own, visible, onClose, onSaved, onFullEdit }) {
  const { t, i18n } = useTranslation()
  const dialog = useRef(null)
  const editor = useRef(null)
  const heading = useId()
  const [editing, setEditing] = useState(false)
  useEffect(() => {
    const element = dialog.current
    const previousOverflow = document.body.style.overflow
    if (visible && !element.open) element.showModal()
    if (visible) document.body.style.overflow = 'hidden'
    if (!visible && element.open) element.close()
    return () => { if (element.open) element.close(); if (visible) document.body.style.overflow = previousOverflow }
  }, [visible])
  const close = () => { if (!editing || editor.current?.canClose()) onClose() }
  return <dialog ref={dialog} className="record-sheet pilot-panel" aria-labelledby={heading}
    onCancel={event => { event.preventDefault(); close() }} onClick={event => { if (event.target === event.currentTarget) close() }}>
    <div className="record-sheet-content"><header><h3 id={heading}>{t('interaction.timeline.details')}</h3>
      <button type="button" className="pilot-button secondary" onClick={close}>{t('interaction.close')}</button></header>
      <p>{t(own ? 'polish.recordedByYou' : 'polish.recordedBy', { name: record.recorder_label || t('polish.memberNumber', { number: record.recorder_number || '?' }) })}</p>
      <RecordTime value={record.timestamp} />
      <p className="preserve-lines">{buildCareSummary([record], { includeParent: own, includeNotes: own,
        language: i18n.resolvedLanguage || 'ja', t })}</p>
      {editing ? <RecordEditor ref={editor} record={record} onSaved={onSaved} onCancel={() => setEditing(false)} />
        : own ? <div className="pilot-actions">
          <button type="button" className="pilot-button" onClick={() => setEditing(true)}>{t('work.editRecord')}</button>
          <button type="button" className="pilot-button secondary" onClick={() => { onClose(); onFullEdit(record) }}>{t('interaction.record.fullEdit')}</button>
        </div> : <p>{t('interaction.timeline.readOnly')}</p>}
    </div>
  </dialog>
}
