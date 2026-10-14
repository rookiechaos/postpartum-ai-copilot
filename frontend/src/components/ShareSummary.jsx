import React, { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../utils/api'
import { buildConsultationSheet } from '../utils/careSummary'
import { japanDay } from '../utils/japanTime'
import { printView } from '../utils/printView'
import useAccountDraft from '../utils/useAccountDraft'
import { DraftRecoveryNotice } from './DraftRecovery'
import { revealElement } from '../utils/focusView'

export default function ShareSummary({ userId, visible = true, refreshKey = 0, initialQuestion = '', requestKey = 0 }) {
  const { t, i18n } = useTranslation()
  const [days, setDays] = useState(7)
  const [questions, setQuestions] = useState(['', '', ''])
  const [includeParent, setIncludeParent] = useState(false)
  const [includeNotes, setIncludeNotes] = useState(false)
  const [includeDetails, setIncludeDetails] = useState(false)
  const [draft, setDraft] = useState(null)
  const [candidate, setCandidate] = useState(null)
  const [savedDrafts, setSavedDrafts] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [incomingQuestion, setIncomingQuestion] = useState('')
  const [incomingActive, setIncomingActive] = useState(false)
  const [questionSlot, setQuestionSlot] = useState(0)
  const [focusTarget, setFocusTarget] = useState(null)
  const [today, setToday] = useState(() => japanDay())
  const generation = useRef(0)
  const incomingHeading = useRef(null)
  const sheetHeading = useRef(null)
  const questionInputs = useRef([])
  const sourceKey = JSON.stringify([days, includeParent, includeNotes, includeDetails, questions, refreshKey, i18n.resolvedLanguage, today])
  const preview = draft?.text || ''
  const stale = Boolean(draft && draft.sourceKey !== sourceKey)
  const currentCandidate = candidate?.sourceKey === sourceKey ? candidate : null
  const canExport = Boolean(preview && !stale && !loading && !currentCandidate)
  const recovery = useAccountDraft('sheet', userId, draft || questions.some(question => question.trim())
    ? { draft, days, questions, includeParent, includeNotes, includeDetails } : null, content => {
    if (!Array.isArray(content.questions)) return false
    setDraft(content.draft && typeof content.draft.text === 'string'
      ? { ...content.draft, text: content.draft.text.slice(0, 8000), sourceKey: 'restored-needs-review' } : null)
    if ([3, 7, 14, 30].includes(content.days)) setDays(content.days)
    if (Array.isArray(content.questions)) setQuestions([0, 1, 2].map(index => String(content.questions[index] || '').slice(0, 250)))
    setIncludeParent(content.includeParent === true); setIncludeDetails(content.includeDetails === true)
    setIncludeNotes(content.includeDetails === true && content.includeNotes === true); setCandidate(null)
  })
  useEffect(() => {
    if (initialQuestion) {
      setIncomingQuestion(initialQuestion.slice(0, 250)); setIncomingActive(true); setFocusTarget({ kind: 'incoming' })
    }
  }, [requestKey, initialQuestion])
  useEffect(() => {
    if (!visible || !focusTarget || (focusTarget.kind === 'incoming' && !incomingActive)) return
    const element = focusTarget.kind === 'incoming' ? incomingHeading.current
      : focusTarget.kind === 'question' ? questionInputs.current[focusTarget.index] : sheetHeading.current
    if (revealElement(element)) setFocusTarget(null)
  }, [visible, focusTarget, incomingActive, loading])
  useEffect(() => {
    const updateDay = () => setToday(japanDay())
    const midnight = new Date(`${japanDay()}T00:00:00+09:00`).getTime() + 86400000
    const timer = setTimeout(updateDay, Math.max(1000, midnight - Date.now() + 100))
    window.addEventListener('focus', updateDay)
    document.addEventListener('visibilitychange', updateDay)
    return () => { clearTimeout(timer); window.removeEventListener('focus', updateDay); document.removeEventListener('visibilitychange', updateDay) }
  }, [today])
  useEffect(() => {
    generation.current++
    // Invalidate pending work, never erase the user's edited consultation text.
    setError(''); setLoading(false)
  }, [sourceKey])
  useEffect(() => () => { generation.current++ }, [])
  const prepare = async () => {
    if (loading) return
    const version = ++generation.current
    setLoading(true); setError('')
    try {
      // Include the whole first Japan calendar day before filtering the printable period.
      const entries = await api.getTracking(userId, days + 1)
      if (generation.current !== version) return
      const sheet = buildConsultationSheet(entries, { days, questions, includeParent, includeNotes, includeDetails,
        language: i18n.resolvedLanguage || 'ja', t })
      if (!sheet) { setError(t('work.noSheetContent')); return }
      const next = { text: sheet, generated: sheet, sourceKey }
      if (draft && draft.text !== draft.generated) setCandidate(next)
      else { setDraft(next); setCandidate(null) }
    } catch { if (generation.current === version) setError(t('pilot.loadFailed')) }
    finally { if (generation.current === version) setLoading(false) }
  }
  const download = () => {
    if (!canExport) return
    const url = URL.createObjectURL(new Blob([preview], { type: 'text/plain;charset=utf-8' }))
    const link = document.createElement('a')
    link.href = url; link.download = `care-summary-${japanDay()}.txt`; link.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  }
  return <section className="pilot-panel share-summary" aria-labelledby="consultation-sheet-heading">
    <h2 id="consultation-sheet-heading" tabIndex={-1} ref={sheetHeading}>{t('pilot.summaryTitle')}</h2><p>{t('work.sheetDescription')}</p>
    <DraftRecoveryNotice draft={recovery} disabled={loading} />
    {incomingActive && <section className="pilot-panel"><h3 tabIndex={-1} ref={incomingHeading}>{t('polish.addCallQuestion')}</h3>
      <textarea aria-label={t('polish.currentQuestion')} rows={4} maxLength={250} value={incomingQuestion} onChange={event => setIncomingQuestion(event.target.value)} />
      <label>{t('polish.questionSlot')}<select value={questionSlot} onChange={event => setQuestionSlot(Number(event.target.value))}>
        {[0, 1, 2].map(index => <option key={index} value={index}>{t('work.questionNumber', { number: index + 1 })}</option>)}
      </select></label><p>{t('polish.replaceQuestionNotice')}</p>
      <button type="button" className="pilot-button secondary" disabled={loading || !incomingQuestion.trim()} onClick={() => {
        if (loading || !incomingQuestion.trim()) return
        setQuestions(previous => previous.map((question, index) => index === questionSlot ? incomingQuestion : question)); setIncomingQuestion(''); setIncomingActive(false)
        setFocusTarget({ kind: 'question', index: questionSlot })
      }}>{t('polish.useCallQuestion')}</button>
      <button type="button" className="pilot-button secondary" onClick={() => {
        setIncomingQuestion(''); setIncomingActive(false); setFocusTarget({ kind: 'sheet' })
      }}>
        {t('ui.support.dismissIncoming')}
      </button>
    </section>}
    <fieldset disabled={loading}>
      <legend>{t('work.sheetOptions')}</legend>
      <label>{t('work.sheetPeriod')}<select value={days} onChange={event => setDays(Number(event.target.value))}>
        {[3, 7, 14, 30].map(value => <option key={value} value={value}>{t('work.rangeDays', { days: value })}</option>)}
      </select></label>
      {questions.map((question, index) => <label key={index} htmlFor={`consultation-question-${index + 1}`}>{t('work.questionNumber', { number: index + 1 })}
        <textarea id={`consultation-question-${index + 1}`} ref={element => { questionInputs.current[index] = element }}
          rows={2} maxLength={250} value={question} placeholder={t('work.questionPlaceholder')}
          onChange={event => setQuestions(previous => previous.map((value, i) => i === index ? event.target.value : value))} />
      </label>)}
      <label className="checkbox-label"><input type="checkbox" checked={includeParent} onChange={event => setIncludeParent(event.target.checked)} />{t('pilot.includeParent')}</label>
      <label className="checkbox-label"><input type="checkbox" checked={includeDetails} onChange={event => {
        setIncludeDetails(event.target.checked); if (!event.target.checked) setIncludeNotes(false)
      }} />{t('work.includeDetails')}</label>
      <label className="checkbox-label"><input type="checkbox" disabled={!includeDetails} checked={includeNotes}
        onChange={event => setIncludeNotes(event.target.checked)} />{t('pilot.includeNotes')}</label>
    </fieldset>
    {(draft || questions.some(question => question.trim()) || recovery.hasSavedDraft) && <button type="button" className="pilot-button secondary" disabled={loading} onClick={() => {
      if (window.confirm(t('polish.deleteSheetConfirm'))) {
        setDraft(null); setQuestions(['', '', '']); setIncomingQuestion(''); setIncomingActive(false); setCandidate(null); setSavedDrafts([]); recovery.clear()
        setFocusTarget({ kind: 'sheet' })
      }
    }}>{t('polish.deleteDraft')}</button>}
    <button className="pilot-button secondary" disabled={loading} onClick={prepare}>{t(loading ? 'common.loading' : 'pilot.prepareSummary')}</button>
    {error && <p role="status">{error}</p>}
    {draft && <>
      {stale && <p role="status">{t('work.sheetStale')}</p>}
      <label className="consultation-draft-only">{t('pilot.summaryPreview')}<textarea rows={16} maxLength={8000} disabled={loading} value={preview}
        onChange={event => setDraft(previous => ({ ...previous, text: event.target.value }))} /></label>
      {currentCandidate && <section className="pilot-panel consultation-draft-only">
        <h3>{t('work.sheetUpdatedVersion')}</h3><p>{t('work.sheetReplacementNotice')}</p>
        <textarea aria-label={t('work.sheetUpdatedVersion')} rows={12} readOnly value={currentCandidate.text} />
        <button className="pilot-button secondary" disabled={loading} onClick={() => {
          if (draft.text !== draft.generated) setSavedDrafts(previous => [...previous, draft.text])
          setDraft(currentCandidate); setCandidate(null)
        }}>{t('work.useUpdatedSheet')}</button>
        <button className="pilot-button secondary" disabled={loading} onClick={() => setCandidate(null)}>{t('work.keepSheetDraft')}</button>
      </section>}
      <p>{t('pilot.summarySharingNote')}</p><p>{t('work.printNote')}</p>
      <div className="pilot-actions"><button className="pilot-button" disabled={!canExport} onClick={() => {
        if (!canExport) return
        try { printView('care-summary-print') } catch { setError(t('work.printFailed')) }
      }}>{t('work.printPdf')}</button>
        <button className="pilot-button secondary" disabled={!canExport} onClick={download}>{t('pilot.downloadSummary')}</button></div>
      <article id="care-summary-print" className="print-sheet"><pre>{canExport ? preview : ''}</pre></article>
    </>}
    {savedDrafts.length > 0 && <details className="consultation-draft-only"><summary>{t('work.previousSheetEdits')}</summary><p>{t('work.previousSheetNotice')}</p>
      {savedDrafts.map((text, index) => <label key={index}>{t('work.previousSheetNumber', { number: index + 1 })}
        <textarea rows={10} readOnly value={text} />
      </label>)}
    </details>}
  </section>
}
