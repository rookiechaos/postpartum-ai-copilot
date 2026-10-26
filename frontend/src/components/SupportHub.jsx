import React, { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import SupportDirectory from './SupportDirectory'
import ShareSummary from './ShareSummary'
import { revealElement } from '../utils/focusView'
import { Button, PageHeader } from './ui'

export default function SupportHub({ userId, visible, refreshKey, navigationRequest, onPrepareSheet }) {
  const { t } = useTranslation()
  const initialView = navigationRequest?.view === 'sheet' ? 'sheet' : 'contacts'
  const [view, setView] = useState(initialView)
  const [visited, setVisited] = useState(initialView === 'sheet' ? ['contacts', 'sheet'] : ['contacts'])
  const [incoming, setIncoming] = useState(() => ({
    question: initialView === 'sheet' ? navigationRequest?.question || '' : '',
    requestKey: initialView === 'sheet' ? navigationRequest?.key || 0 : 0,
  }))
  const [navigation, setNavigation] = useState(0)
  const [incomingContact, setIncomingContact] = useState(null)
  const handledRequest = useRef(0)
  const pendingFocus = useRef(null)
  const headings = useRef({})
  useEffect(() => {
    if (!navigationRequest || navigationRequest.key === handledRequest.current) return
    handledRequest.current = navigationRequest.key
    const nextView = navigationRequest.view === 'sheet' ? 'sheet' : 'contacts'
    setVisited(previous => previous.includes(nextView) ? previous : [...previous, nextView])
    setView(nextView)
    if (nextView === 'sheet' && navigationRequest.contactKey) setIncomingContact({ key: navigationRequest.contactKey, name: navigationRequest.contactName || '', requestKey: navigationRequest.key })
    const question = nextView === 'sheet' && typeof navigationRequest.question === 'string' ? navigationRequest.question : ''
    if (question) {
      // Only a new sheet handoff may update the incoming question. Contact requests
      // preserve both the working sheet and any unapplied, edited question.
      setIncoming({ question, requestKey: navigationRequest.key })
      pendingFocus.current = null
    } else pendingFocus.current = navigationRequest.contactKey || navigationRequest.resume ? null : nextView
    setNavigation(value => value + 1)
  }, [navigationRequest])
  useEffect(() => {
    if (visible && pendingFocus.current === view) {
      if (revealElement(headings.current[view])) pendingFocus.current = null
    }
  }, [navigation, view, visible])
  const open = next => {
    setVisited(previous => previous.includes(next) ? previous : [...previous, next])
    setView(next); pendingFocus.current = next; setNavigation(value => value + 1)
  }
  return <div className="support-hub">
    <div className="view-switch" role="group" aria-label={t('ui.support.chooseView')}>
      {['contacts', 'sheet'].map(key => <Button key={key} variant="secondary"
        aria-pressed={view === key} aria-controls={visited.includes(key) ? `support-view-${key}` : undefined} onClick={() => open(key)}>{t(`ui.support.${key}`)}</Button>)}
    </div>
    {visited.map(key => <section key={key} id={`support-view-${key}`} className="support-view" hidden={view !== key}
      aria-labelledby={`support-heading-${key}`}>
      <PageHeader titleId={`support-heading-${key}`} ref={element => { headings.current[key] = element }} title={t(`ui.support.${key}`)} />
      {key === 'contacts' ? <SupportDirectory userId={userId} visible={visible && view === key} onPrepareSheet={onPrepareSheet} navigationRequest={navigationRequest}
        workDestination={{ id: 'support-directory', tab: 'support', detail: { view: 'contacts' } }} /> : <>
        <p className="view-intro">{t('ui.support.sheetIntro')}</p>
        <Button variant="secondary" onClick={() => open('contacts')}>{t('ui.support.backContacts')}</Button>
        <ShareSummary userId={userId} visible={visible && view === key} refreshKey={refreshKey} resumeRequest={navigationRequest}
          incomingContact={incomingContact} contactRequestKey={incomingContact?.requestKey || 0}
          initialQuestion={incoming.question} requestKey={incoming.requestKey} />
      </>}
    </section>)}
  </div>
}
