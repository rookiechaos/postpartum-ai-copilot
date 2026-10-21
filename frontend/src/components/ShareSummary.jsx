import React, { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../utils/api'
import { buildConsultationSheet } from '../utils/careSummary'
import { japanDay, japanDateTime, japanDateTimeInput } from '../utils/japanTime'
import { printView } from '../utils/printView'
import useAccountDraft from '../utils/useAccountDraft'
import { DraftRecoveryNotice } from './DraftRecovery'
import { revealElement } from '../utils/focusView'
import { useCareSession } from '../utils/CareSession'
import CareScope from './CareScope'
import ConsultationPackets from './ConsultationPackets'

export default function ShareSummary({ userId, visible = true, refreshKey = 0, initialQuestion = '', requestKey = 0, incomingContact, contactRequestKey = 0 }) {
  const { t, i18n } = useTranslation()
  const { subjects, rememberSubject } = useCareSession()
  const [subjectId, setSubjectId] = useState('')
  const selectedSubject = subjects.find(item => item.subject_id === subjectId)
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
  const [contacts, setContacts] = useState([])
  const [contactKey, setContactKey] = useState('')
  const [contactNameSnapshot, setContactNameSnapshot] = useState('')
  const [appointment, setAppointment] = useState('')
  const [pendingContact, setPendingContact] = useState(null)
  const [packetLocked, setPacketLocked] = useState(false)
  const [frozenOptions, setFrozenOptions] = useState('')
  const contactName = contactNameSnapshot || contacts.find(item => item.key === contactKey)?.name || ''
  const optionsKey = JSON.stringify([subjectId, days, includeParent, includeNotes, includeDetails, questions, contactKey, appointment])
  const generation = useRef(0)
  const incomingHeading = useRef(null)
  const sheetHeading = useRef(null)
  const questionInputs = useRef([])
  const sourceKey = JSON.stringify([subjectId, selectedSubject?.revision || 0, days, includeParent, includeNotes, includeDetails, questions, refreshKey, i18n.resolvedLanguage, today, contactKey, contactName, appointment])
  const preview = draft?.text || ''
  const stale = Boolean(draft && draft.sourceKey !== sourceKey)
  const currentCandidate = candidate?.sourceKey === sourceKey ? candidate : null
  const canExport = Boolean(preview && !stale && !loading && !currentCandidate)
  const recovery = useAccountDraft('sheet', userId, draft || questions.some(question => question.trim())
    ? { draft, days, questions, includeParent, includeNotes, includeDetails, subjectId, contactKey, appointment } : null, content => {
    if (!Array.isArray(content.questions)) return false
    setDraft(content.draft && typeof content.draft.text === 'string'
      ? { ...content.draft, text: content.draft.text.slice(0, 8000), sourceKey: 'restored-needs-review' } : null)
    if ([3, 7, 14, 30].includes(content.days)) setDays(content.days)
    setSubjectId(typeof content.subjectId === 'string' ? content.subjectId : '')
    if (Array.isArray(content.questions)) setQuestions([0, 1, 2].map(index => String(content.questions[index] || '').slice(0, 250)))
    setIncludeParent(content.includeParent === true); setIncludeDetails(content.includeDetails === true)
    setIncludeNotes(content.includeDetails === true && content.includeNotes === true); setCandidate(null)
    setContactKey(typeof content.contactKey === 'string' ? content.contactKey : '')
    setAppointment(typeof content.appointment === 'string' ? content.appointment : ''); setContactNameSnapshot(''); setFrozenOptions('')
  })
  useEffect(() => {
    if (!visible) return
    let active = true
    Promise.allSettled([api.get('/api/pilot'), api.get('/api/support-journeys')]).then(([directory, journeys]) => {
      if (!active) return
      const options = new Map()
      if (journeys.status === 'fulfilled') journeys.value.filter(row => !row.cleared).forEach(row => options.set(row.contact_key, row.contact_name))
      if (directory.status === 'fulfilled') {
        const profile = directory.value.profile
        if (profile?.name) options.set('organization', profile.name)
        profile?.resources?.forEach(row => options.set(row.resource_key, row.name))
      }
      setContacts([...options].map(([key, name]) => ({ key, name })))
    })
    return () => { active = false }
  }, [visible])
  useEffect(() => { if (incomingContact?.key) setPendingContact(incomingContact) }, [contactRequestKey, incomingContact])
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
    if (loading || packetLocked) return
    const version = ++generation.current
    setLoading(true); setError('')
    try {
      // Include the whole first Japan calendar day before filtering the printable period.
      const entries = await api.getTracking(userId, days + 1)
      if (generation.current !== version) return
      const selected = entries.filter(entry => ['mood', 'recovery'].includes(entry.entry_type) || (entry.subject_id || '') === subjectId)
      const sheet = buildConsultationSheet(selected, { days, questions, includeParent, includeNotes, includeDetails,
        subjectLabel: t('continuity.subject.recordLabel', { name: selectedSubject?.nickname || t(subjectId ? 'continuity.subject.unavailable' : 'continuity.subject.unassignedLabel') }),
        language: i18n.resolvedLanguage || 'ja', t })
      if (!sheet) { setError(t('work.noSheetContent')); return }
      const header = [contactName && t('workflow.packet.contactLine', { name: contactName }),
        appointment && t('workflow.packet.appointment', { time: japanDateTime(new Date(`${appointment}:00+09:00`), i18n.resolvedLanguage || 'ja') })].filter(Boolean).join('\n')
      const text = header ? `${header}\n\n${sheet}` : sheet
      if (text.length > 8000) { setError(t('workflow.packet.errors.tooLong')); return }
      const next = { text, generated: text, sourceKey }
      setFrozenOptions('')
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
    <CareScope subjectId={subjectId} mode="sheet" disabled={loading || packetLocked} onUseLast={id => { rememberSubject(id); setSubjectId(id) }} />
    <label>{t('continuity.subject.sheetFor')}<select value={subjectId} disabled={loading || packetLocked} onChange={event => { rememberSubject(event.target.value); setSubjectId(event.target.value) }}>
      <option value="">{t('continuity.subject.unknown')}</option>
      {subjectId && !subjects.some(item => item.subject_id === subjectId) && <option value={subjectId}>{t('continuity.subject.unavailable')}</option>}
      {subjects.map(item => <option key={item.subject_id} value={item.subject_id}>{item.nickname} · {item.family_name || t('continuity.subject.personal')}</option>)}
    </select></label><p>{t('continuity.subject.sheetNotice')}</p>
    <h2 id="consultation-sheet-heading" tabIndex={-1} ref={sheetHeading}>{t('pilot.summaryTitle')}</h2><p>{t('work.sheetDescription')}</p>
    <DraftRecoveryNotice draft={recovery} disabled={loading || packetLocked} />
    {pendingContact && <section className="support-card"><p>{t('workflow.packet.incoming', { name: pendingContact.name })}</p>
      <button type="button" className="pilot-button secondary" disabled={loading || packetLocked} onClick={() => {
        setContactKey(pendingContact.key); setContactNameSnapshot(pendingContact.name); setPendingContact(null)
      }}>{t('workflow.packet.useContact')}</button>
      <button type="button" className="text-action" disabled={packetLocked} onClick={() => setPendingContact(null)}>{t('tracking.cancel')}</button>
    </section>}
    {incomingActive && <section className="pilot-panel"><h3 tabIndex={-1} ref={incomingHeading}>{t('polish.addCallQuestion')}</h3>
      <textarea aria-label={t('polish.currentQuestion')} rows={4} maxLength={250} disabled={loading || packetLocked} value={incomingQuestion} onChange={event => setIncomingQuestion(event.target.value)} />
      <label>{t('polish.questionSlot')}<select value={questionSlot} disabled={loading || packetLocked} onChange={event => setQuestionSlot(Number(event.target.value))}>
        {[0, 1, 2].map(index => <option key={index} value={index}>{t('work.questionNumber', { number: index + 1 })}</option>)}
      </select></label><p>{t('polish.replaceQuestionNotice')}</p>
      <button type="button" className="pilot-button secondary" disabled={loading || packetLocked || !incomingQuestion.trim()} onClick={() => {
        if (loading || packetLocked || !incomingQuestion.trim()) return
        setQuestions(previous => previous.map((question, index) => index === questionSlot ? incomingQuestion : question)); setIncomingQuestion(''); setIncomingActive(false)
        setFocusTarget({ kind: 'question', index: questionSlot })
      }}>{t('polish.useCallQuestion')}</button>
      <button type="button" className="pilot-button secondary" disabled={packetLocked} onClick={() => {
        setIncomingQuestion(''); setIncomingActive(false); setFocusTarget({ kind: 'sheet' })
      }}>
        {t('ui.support.dismissIncoming')}
      </button>
    </section>}
    <fieldset disabled={loading || packetLocked}>
      <legend>{t('work.sheetOptions')}</legend>
      <label>{t('workflow.packet.contact')}<select value={contactKey} onChange={event => { setContactKey(event.target.value); setContactNameSnapshot('') }}>
        <option value="">{t('workflow.packet.noContact')}</option>
        {contactKey && !contacts.some(item => item.key === contactKey) && <option value={contactKey}>{contactName || t('workflow.packet.unavailableContact')}</option>}
        {contacts.map(item => <option key={item.key} value={item.key}>{item.name}</option>)}
      </select></label>
      <label>{t('workflow.packet.appointmentLabel')}<input type="datetime-local" value={appointment} onChange={event => setAppointment(event.target.value)} /></label>
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
    {(draft || questions.some(question => question.trim()) || recovery.hasSavedDraft) && <button type="button" className="pilot-button secondary" disabled={loading || packetLocked} onClick={() => {
      if (window.confirm(t('polish.deleteSheetConfirm'))) {
        setDraft(null); setQuestions(['', '', '']); setIncomingQuestion(''); setIncomingActive(false); setCandidate(null); setSavedDrafts([]); recovery.clear()
        setFocusTarget({ kind: 'sheet' })
      }
    }}>{t('polish.deleteDraft')}</button>}
    <button className="pilot-button secondary" disabled={loading || packetLocked} onClick={prepare}>{t(loading ? 'common.loading' : 'pilot.prepareSummary')}</button>
    {error && <p role="status">{error}</p>}
    {draft && <>
      {stale && <p role="status">{t('work.sheetStale')}</p>}
      {stale && frozenOptions === optionsKey && <button type="button" className="pilot-button secondary" disabled={loading || packetLocked} onClick={() => {
        if (window.confirm(t('workflow.packet.keepConfirm'))) setDraft(previous => ({ ...previous, sourceKey }))
      }}>{t('workflow.packet.keepSaved')}</button>}
      <label className="consultation-draft-only">{t('pilot.summaryPreview')}<textarea rows={16} maxLength={8000} disabled={loading || packetLocked} value={preview}
        onChange={event => setDraft(previous => ({ ...previous, text: event.target.value }))} /></label>
      {currentCandidate && <section className="pilot-panel consultation-draft-only">
        <h3>{t('work.sheetUpdatedVersion')}</h3><p>{t('work.sheetReplacementNotice')}</p>
        <textarea aria-label={t('work.sheetUpdatedVersion')} rows={12} readOnly value={currentCandidate.text} />
        <button className="pilot-button secondary" disabled={loading || packetLocked} onClick={() => {
          if (draft.text !== draft.generated) setSavedDrafts(previous => [...previous, draft.text])
          setDraft(currentCandidate); setCandidate(null)
        }}>{t('work.useUpdatedSheet')}</button>
        <button className="pilot-button secondary" disabled={loading || packetLocked} onClick={() => setCandidate(null)}>{t('work.keepSheetDraft')}</button>
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
    <ConsultationPackets visible={visible} onLockChange={setPacketLocked} canSave={canExport && !packetLocked}
      content={{ contact_key: contactKey || null, subject_id: subjectId || null, days, questions,
        include_parent: includeParent, include_notes: includeNotes, include_details: includeDetails, text: preview,
        appointment_at: appointment && Number.isFinite(new Date(`${appointment}:00+09:00`).getTime()) ? new Date(`${appointment}:00+09:00`).toISOString() : null }}
      onOpen={row => {
        const value = row.content
        const id = value.subject_id || '', key = value.contact_key || '', name = value.contact_name || ''
        const time = value.appointment_at ? japanDateTimeInput(value.appointment_at) : ''
        setSubjectId(id); setDays(value.days); setQuestions(value.questions); setIncludeParent(value.include_parent)
        setIncludeNotes(value.include_notes); setIncludeDetails(value.include_details); setContactKey(key); setContactNameSnapshot(name); setAppointment(time)
        setCandidate(null); setSavedDrafts([])
        setDraft({ text: value.text, generated: value.text, sourceKey: JSON.stringify([id, subjects.find(item => item.subject_id === id)?.revision || 0,
          value.days, value.include_parent, value.include_notes, value.include_details, value.questions, refreshKey, i18n.resolvedLanguage, today, key, name, time]) })
        setFrozenOptions(JSON.stringify([id, value.days, value.include_parent, value.include_notes, value.include_details, value.questions, key, time])); setFocusTarget({ kind: 'sheet' })
      }} onDeleted={() => {
        setDraft(null); setQuestions(['', '', '']); setCandidate(null); setSavedDrafts([]); setFrozenOptions('')
        setContactKey(''); setContactNameSnapshot(''); setAppointment(''); recovery.clear()
      }} />
  </section>
}
