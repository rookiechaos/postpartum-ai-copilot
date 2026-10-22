import React, { forwardRef, useId } from 'react'
import { useTranslation } from 'react-i18next'

// One labelled input/select/textarea. Checkbox groups keep their own fieldset/legend.
const FormField = forwardRef(function FormField({ as: Control = 'input', id, label, hint, error,
  required = false, optional = false, className = '', children, 'aria-describedby': describedBy,
  'aria-invalid': invalid, ...props }, ref) {
  const generatedId = useId()
  const controlId = id || generatedId
  const { t } = useTranslation()
  const description = [describedBy, hint && `${controlId}-hint`, error && `${controlId}-error`].filter(Boolean).join(' ')
  return <div className={`ui-field ${className}`.trim()}>
    <label className="ui-field-label" htmlFor={controlId}>{label}
      {(required || optional) && <span className="ui-field-badge">{t(`foundation.field.${required ? 'required' : 'optional'}`)}</span>}
    </label>
    {hint && <p id={`${controlId}-hint`} className="ui-field-hint">{hint}</p>}
    <Control {...props} ref={ref} id={controlId} className="ui-field-control" required={required}
      aria-describedby={description || undefined} aria-invalid={error ? true : invalid}>{children}</Control>
    {error && <p id={`${controlId}-error`} className="ui-field-error" role="alert">{error}</p>}
  </div>
})

export default FormField
