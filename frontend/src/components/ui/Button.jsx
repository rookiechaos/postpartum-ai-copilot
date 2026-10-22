import React, { forwardRef } from 'react'

const Button = forwardRef(function Button({ variant = 'primary', type = 'button', busy = false,
  busyLabel, disabled = false, className = '', children, ...props }, ref) {
  return <button {...props} ref={ref} type={type} disabled={disabled || busy}
    aria-busy={busy || undefined} className={`ui-button ui-button--${variant} ${className}`.trim()}>
    {busy && <span className="ui-button-spinner" aria-hidden="true" />}
    {busy && busyLabel ? busyLabel : children}
  </button>
})

export default Button
