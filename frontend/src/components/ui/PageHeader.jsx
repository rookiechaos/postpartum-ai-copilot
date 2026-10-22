import React, { forwardRef } from 'react'

const PageHeader = forwardRef(function PageHeader({ title, description, actions, headingLevel = 2,
  titleId, className = '', children, ...props }, ref) {
  const Heading = `h${headingLevel}`
  return <header {...props} className={`ui-page-header ${className}`.trim()}>
    <div className="ui-page-header-copy">
      <Heading id={titleId} ref={ref} tabIndex={titleId ? -1 : undefined}>{title}</Heading>
      {description && <p>{description}</p>}
      {children}
    </div>
    {actions && <div className="ui-page-header-actions">{actions}</div>}
  </header>
})

export default PageHeader
