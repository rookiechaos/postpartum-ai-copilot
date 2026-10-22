import React, { useEffect, useId, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { useTranslation } from 'react-i18next'
import Button from './Button'
import { ErrorMessage } from './StatusMessage'

export default function ConfirmDialog({ open, title, description, confirmLabel, cancelLabel,
  onConfirm, onClose, danger = false, busy = false, error }) {
  const { t } = useTranslation()
  const titleId = useId()
  const descriptionId = useId()
  const dialog = useRef(null)
  const cancel = useRef(null)
  const confirming = useRef(false)
  const [working, setWorking] = useState(false)
  const [failed, setFailed] = useState(false)
  const blocked = busy || working
  useEffect(() => {
    if (!open) return
    const element = dialog.current
    const previous = document.activeElement
    setFailed(false)
    if (!element.open) element.showModal()
    cancel.current?.focus()
    return () => {
      if (element.open) element.close()
      if (previous?.isConnected && !previous.closest('[hidden]')) previous.focus?.({ preventScroll: true })
    }
  }, [open])
  const close = () => { if (!blocked && !confirming.current) onClose() }
  const confirm = async () => {
    if (blocked || confirming.current) return
    confirming.current = true; setWorking(true); setFailed(false)
    try {
      // Returning false leaves the dialog open when the caller needs a correction.
      if (await onConfirm() !== false) onClose()
    } catch { setFailed(true) }
    finally { confirming.current = false; setWorking(false) }
  }
  return createPortal(<dialog ref={dialog} className="ui-confirm-dialog" aria-labelledby={titleId}
    aria-describedby={description ? descriptionId : undefined} aria-busy={blocked || undefined}
    onCancel={event => { event.preventDefault(); close() }}
    onClick={event => { if (event.target === event.currentTarget) close() }}>
    <h2 id={titleId}>{title}</h2>
    {description && <p id={descriptionId} className="ui-dialog-description">{description}</p>}
    {(failed || error) && <ErrorMessage title={error || t('foundation.common.actionError')} />}
    <div className="ui-dialog-actions">
      <Button ref={cancel} variant="secondary" disabled={blocked} onClick={close}>{cancelLabel || t('tracking.cancel')}</Button>
      <Button variant={danger ? 'danger' : 'primary'} busy={blocked} busyLabel={t('common.loading')} onClick={confirm}>
        {confirmLabel || t('foundation.common.confirm')}
      </Button>
    </div>
  </dialog>, document.body)
}
