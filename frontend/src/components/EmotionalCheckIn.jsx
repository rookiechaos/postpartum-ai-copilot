import React, { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../utils/api'
import AIUseNotice from './AIUseNotice'
import SupportDirectory from './SupportDirectory'
import { useCareWork } from '../utils/CareSession'
import { revealElement } from '../utils/focusView'
import { japanDateTime } from '../utils/japanTime'
import { Button, FormField, StatusMessage } from './ui'
import './EmotionalCheckIn.css'

const measures = [
  { key: 'overwhelmed_level', label: 'checkin.overwhelmed', upper: 'checkin.extremely' },
  { key: 'anxiety_level', label: 'checkin.anxiety', upper: 'checkin.extremely' },
  { key: 'support_level', label: 'checkin.support', upper: 'checkin.verySupported' },
]
const unanswered = { overwhelmed_level: null, anxiety_level: null, support_level: null }

function CheckinSnapshot({ payload }) {
  const { t } = useTranslation()
  return <dl className="checkin-snapshot">
    {measures.map(measure => <div key={measure.key}><dt>{t(measure.label)}</dt>
      <dd>{payload[measure.key] == null ? t('checkinFlow.unanswered') : `${payload[measure.key]} / 10`}</dd>
    </div>)}
    <div className="checkin-snapshot-text"><dt>{t('checkin.share')}</dt><dd className="checkin-snapshot-notes" tabIndex={payload.notes ? 0 : undefined}>{payload.notes || t('checkinFlow.noNotes')}</dd></div>
    <div><dt>{t('checkinFlow.history')}</dt><dd>{t(payload.include_history ? 'checkinFlow.historyIncluded' : 'checkinFlow.historyExcluded')}</dd></div>
    <div><dt>{t('checkinFlow.language')}</dt><dd>{payload.language === 'en' ? 'English' : '日本語'}</dd></div>
  </dl>
}

function EmotionalCheckIn({ userId, visible = true, navigationRequest }) {
  const { t, i18n } = useTranslation()
  const language = (i18n.resolvedLanguage || i18n.language || 'ja').split('-')[0] === 'en' ? 'en' : 'ja'
  const [levels, setLevels] = useState(unanswered)
  const [notes, setNotes] = useState('')
  const [includeHistory, setIncludeHistory] = useState(false)
  const [acceptedSignature, setAcceptedSignature] = useState(null)
  const [result, setResult] = useState(null)
  const [failure, setFailure] = useState(null)
  const [submission, setSubmission] = useState(null)
  const [loading, setLoading] = useState(false)
  const [unreadResult, setUnreadResult] = useState(false)
  const [focusForm, setFocusForm] = useState(0)
  const [workVersion, setWorkVersion] = useState(0)
  const writing = useRef(false)
  const generation = useRef(0)
  const sequence = useRef(0)
  const formHeading = useRef(null)
  const resultHeading = useRef(null)
  const handledNavigation = useRef(0)
  const handledFormFocus = useRef(0)
  const payload = { ...levels, notes, include_history: includeHistory, language }
  // This signature is local to this account's mounted editor. The shared work
  // list receives only counters and translated labels, never these answers.
  const signature = JSON.stringify(payload)
  const complete = measures.every(measure => Number.isInteger(levels[measure.key]) && levels[measure.key] >= 1 && levels[measure.key] <= 10)
  const acceptedAI = acceptedSignature === signature
  const hasInput = measures.some(measure => levels[measure.key] != null) || Boolean(notes) || includeHistory
  const hasUnsentInput = hasInput && (signature !== result?.signature || Boolean(failure))
  const workTitle = loading ? 'checkinFlow.waitingWork' : failure ? 'checkinFlow.failedWork'
    : hasUnsentInput ? 'checkinFlow.draftWork' : null

  useCareWork('checkin-draft', workTitle ? {
    version: `${workTitle}:${workVersion}:${sequence.current}`, title: workTitle, priority: loading ? 0 : failure ? 1 : 2,
    attention: Boolean(failure),
    critical: loading, protectLeave: true, tab: 'checkin', detail: { action: 'resume', target: 'form' },
    action: 'experience.trackedWorkOpen',
  } : null)
  useCareWork('checkin-result', unreadResult && result ? {
    version: result.sequence, title: 'checkinFlow.resultWork', priority: 1, attention: true, protectLeave: true,
    tab: 'checkin', detail: { action: 'resume', target: 'result' }, action: 'checkinFlow.reviewResult',
  } : null)

  useEffect(() => {
    generation.current += 1
    return () => { generation.current += 1 }
  }, [userId])
  useEffect(() => { setAcceptedSignature(null) }, [language])
  useEffect(() => { setWorkVersion(value => value + 1) }, [signature])
  useEffect(() => {
    if (!visible || !navigationRequest?.key || handledNavigation.current === navigationRequest.key) return
    const target = navigationRequest.target === 'result' && result ? resultHeading.current : formHeading.current
    if (revealElement(target)) {
      handledNavigation.current = navigationRequest.key
      if (navigationRequest.target === 'result' && result) setUnreadResult(false)
    }
  }, [visible, navigationRequest?.key, navigationRequest?.target, result?.sequence])
  useEffect(() => {
    if (visible && focusForm && focusForm !== handledFormFocus.current && revealElement(formHeading.current)) handledFormFocus.current = focusForm
  }, [visible, focusForm])

  const changeLevel = (key, value) => {
    if (writing.current) return
    setAcceptedSignature(null)
    setLevels(previous => ({ ...previous, [key]: value === '' ? null : Number(value) }))
  }
  const reviewResult = () => {
    if (visible && revealElement(resultHeading.current)) setUnreadResult(false)
  }
  const prepareRetry = () => {
    if (!failure || writing.current) return
    const previous = failure.payload
    if (signature !== JSON.stringify({ ...previous, language }) && !window.confirm(t('checkinFlow.replaceRetryConfirm'))) return
    setLevels(Object.fromEntries(measures.map(measure => [measure.key, previous[measure.key]])))
    setNotes(previous.notes); setIncludeHistory(previous.include_history)
    // The current display language stays in force and appears in the preview.
    // Reopening a failed request never grants consent or sends it again.
    setAcceptedSignature(null); setFocusForm(value => value + 1)
  }
  const submit = async () => {
    // Enter and generic form submission cannot call the AI. Only the explicit
    // button below can send the exact reviewed payload under fresh consent.
    if (writing.current || !complete || !acceptedAI) return
    if (unreadResult && result && !window.confirm(t('checkinFlow.replaceUnread'))) return
    writing.current = true
    const currentGeneration = generation.current
    const submitted = { payload: { ...payload }, signature, at: new Date().toISOString(), sequence: ++sequence.current }
    setSubmission(submitted); setAcceptedSignature(null); setFailure(null); setLoading(true)
    try {
      const data = await api.postEmotionalCheckin(submitted.payload)
      if (generation.current !== currentGeneration) return
      if (data?.analysis_available !== true || typeof data.assessment !== 'string' || !data.assessment.trim()) {
        setFailure({ ...submitted, kind: 'unavailable' })
        return
      }
      setResult({ ...submitted, data: { ...data,
        suggestions: Array.isArray(data.suggestions) ? data.suggestions.filter(value => typeof value === 'string') : [],
        resources: Array.isArray(data.resources) ? data.resources.filter(value => typeof value === 'string') : [],
      } }); setUnreadResult(true)
    } catch (error) {
      if (generation.current === currentGeneration) setFailure({ ...submitted, kind: error.resultUnconfirmed ? 'unconfirmed' : 'failed' })
    } finally {
      if (generation.current === currentGeneration) {
        writing.current = false; setLoading(false); setAcceptedSignature(null)
      }
    }
  }

  return <div className="emotional-checkin">
    <div className="checkin-container">
      <h2>{t('checkin.title')}</h2>
      <p className="checkin-subtitle">{t('checkin.subtitle')}</p>
      <form onSubmit={event => event.preventDefault()} className="checkin-form" aria-labelledby="checkin-form-heading">
        <h3 id="checkin-form-heading" ref={formHeading} tabIndex={-1}>{t('checkinFlow.formTitle')}</h3>
        <p id="checkin-selection-hint" className="field-hint">{t('checkinFlow.selectionHint')}</p>
        <fieldset className="checkin-fields" disabled={loading} aria-describedby="checkin-selection-hint">
          <legend>{t('checkinFlow.measuresTitle')}</legend>
          {measures.map(measure => <FormField as="select" key={measure.key} id={`checkin-${measure.key}`}
            label={t(measure.label)} required hint={t('checkinFlow.scaleHint', { low: t('checkin.notAtAll'), high: t(measure.upper) })}
            value={levels[measure.key] ?? ''} onChange={event => changeLevel(measure.key, event.target.value)}>
            <option value="">{t('checkinFlow.unanswered')}</option>
            {Array.from({ length: 10 }, (_, index) => index + 1).map(value => <option key={value} value={value}>{value} / 10</option>)}
          </FormField>)}
          <FormField as="textarea" id="checkin-notes" label={t('checkin.share')} rows={4} maxLength={5000}
            hint={t('checkinFlow.notesHint')} value={notes} placeholder={t('checkin.sharePlaceholder')}
            onChange={event => { if (!writing.current) { setNotes(event.target.value); setAcceptedSignature(null) } }} />
        </fieldset>
        <section className="checkin-send-preview" aria-labelledby="checkin-preview-heading">
          <h3 id="checkin-preview-heading">{t('checkinFlow.previewTitle')}</h3>
          <CheckinSnapshot payload={payload} />
          <p className="field-hint">{t('checkinFlow.previewHint')}</p>
        </section>
        <AIUseNotice scope="checkin" accepted={acceptedAI} onChange={checked => { if (!writing.current) setAcceptedSignature(checked ? signature : null) }} disabled={loading}
          includeHistory={includeHistory} onHistoryChange={checked => { if (!writing.current) { setIncludeHistory(checked); setAcceptedSignature(null) } }} />
        {!complete && <p className="field-hint">{t('checkinFlow.requiredHint')}</p>}
        {loading && <StatusMessage title={t('checkinFlow.waiting')}><p>{t('checkinFlow.waitingHint')}</p>
          {submission && <details><summary>{t('checkinFlow.submittedContent')}</summary><CheckinSnapshot payload={submission.payload} /></details>}
        </StatusMessage>}
        <p id="checkin-send-hint" className="field-hint">{t('checkinFlow.sendHint')}</p>
        <div className="checkin-form-actions">
          <Button type="button" busy={loading} busyLabel={t('checkin.processing')} disabled={!complete || !acceptedAI} onClick={submit}
            aria-describedby="checkin-send-hint">{t('checkinFlow.send')}</Button>
          {hasInput && <Button type="button" variant="secondary" disabled={loading} onClick={() => {
            if (writing.current) return
            if (!window.confirm(t('checkinFlow.clearConfirm'))) return
            setLevels(unanswered); setNotes(''); setIncludeHistory(false); setAcceptedSignature(null); setFailure(null)
            setFocusForm(value => value + 1)
          }}>{t('checkinFlow.clearDraft')}</Button>}
        </div>
        <p className="field-hint">{t('checkinFlow.sessionHint')}</p>
      </form>

      {failure && <StatusMessage tone="error" title={t(`checkinFlow.${failure.kind}`)}
        actions={<Button type="button" variant="secondary" disabled={loading} onClick={prepareRetry}>{t('checkinFlow.prepareRetry')}</Button>}>
        <p>{t('checkinFlow.failureHint')}</p>
        {failure.kind === 'unconfirmed' && <p>{t('checkinFlow.unconfirmedHint')}</p>}
        <p>{t('checkinFlow.requestedAt', { time: japanDateTime(failure.at, language) })}</p>
        <details><summary>{t('checkinFlow.submittedContent')}</summary><CheckinSnapshot payload={failure.payload} /></details>
      </StatusMessage>}

      {result && <section className="checkin-result" aria-labelledby="checkin-result-heading">
        <div className="checkin-result-heading"><h3 id="checkin-result-heading" ref={resultHeading} tabIndex={-1}>{t('checkin.assessment')}</h3>
          {unreadResult && <Button type="button" variant="secondary" onClick={reviewResult}>{t('checkinFlow.reviewResult')}</Button>}
        </div>
        <p className="checkin-disclaimer">{t('checkin.disclaimerNonClinical')}</p>
        <p>{t('checkinFlow.requestedAt', { time: japanDateTime(result.at, language) })}</p>
        {(loading || failure) && <p>{t('checkinFlow.previousResult')}</p>}
        {signature !== result.signature && <p>{t('checkinFlow.differentInput')}</p>}
        <details><summary>{t('checkinFlow.resultContent')}</summary><CheckinSnapshot payload={result.payload} /></details>
        {result.data.escalation_needed === true && <div className="escalation-warning">
          <strong>{t('chat.important')}</strong><p>{t('pilot.reachOut')}</p>
        </div>}
        <div className="assessment"><p>{t('pilot.aiLabel')}</p><p>{result.data.assessment}</p></div>
        {Array.isArray(result.data.suggestions) && result.data.suggestions.length > 0 && <div className="suggestions">
          <h4>{t('checkin.suggestions')}</h4><ul>{result.data.suggestions.map((suggestion, index) => <li key={index}>{suggestion}</li>)}</ul>
        </div>}
        {Array.isArray(result.data.resources) && result.data.resources.length > 0 && <div className="resources">
          <h4>{t('checkin.resources')}</h4><ul>{result.data.resources.map((resource, index) => <li key={index}>{resource}</li>)}</ul>
        </div>}
      </section>}
      <div className="safety-note"><p>{t('checkin.safetyNote')}</p></div>
      <SupportDirectory compact visible={visible} />
    </div>
  </div>
}

export default EmotionalCheckIn
