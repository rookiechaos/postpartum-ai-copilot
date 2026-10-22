import React from 'react'
import { useTranslation } from 'react-i18next'
import Button from './Button'

export default function StatusMessage({ tone = 'info', title, children, actions, className = '', role, ...props }) {
  return <div {...props} className={`ui-status ui-status--${tone} ${className}`.trim()}
    role={role || (tone === 'error' ? 'alert' : 'status')}>
    {title && <p className="ui-status-title">{title}</p>}
    {children && <div className="ui-status-content">{children}</div>}
    {actions && <div className="ui-status-actions">{actions}</div>}
  </div>
}

export function ErrorMessage({ title, children, onRetry, retryLabel, retryDisabled = false, ...props }) {
  const { t } = useTranslation()
  return <StatusMessage {...props} tone="error" title={title}
    actions={onRetry ? <Button variant="secondary" disabled={retryDisabled} onClick={onRetry}>{retryLabel || t('pilot.retry')}</Button> : undefined}>
    {children}
  </StatusMessage>
}
