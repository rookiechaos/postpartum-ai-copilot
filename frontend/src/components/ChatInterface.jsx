import React, { useState, useRef, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../utils/api'
import taskManager from '../utils/taskManager'
import AIUseNotice from './AIUseNotice'
import SupportDirectory from './SupportDirectory'
import useAccountDraft from '../utils/useAccountDraft'
import { DraftRecoveryNotice } from './DraftRecovery'
import { revealElement } from '../utils/focusView'
import { publicHttps } from '../utils/publicDirectory'
import './ChatInterface.css'

function ChatInterface({ userId, initialDraft = '', draftVersion = 0, visible = true, onPrepareSheet }) {
  const { t, i18n } = useTranslation()
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: t('chat.initialMessage'),
      timestamp: new Date()
    }
  ])
  const [input, setInput] = useState(initialDraft)
  const [acceptedAI, setAcceptedAI] = useState(false)
  const [includeProfile, setIncludeProfile] = useState(false)
  const [failed, setFailed] = useState(false)
  const [loading, setLoading] = useState(false)
  const [taskStatus, setTaskStatus] = useState(null)
  const [followUp, setFollowUp] = useState(null)
  const [includePrevious, setIncludePrevious] = useState(false)
  const [submission, setSubmission] = useState(null)
  const [hasNewMessages, setHasNewMessages] = useState(false)
  const [preparedQuestion, setPreparedQuestion] = useState(null)
  const [composerRequest, setComposerRequest] = useState(0)
  const draft = useAccountDraft('chat', userId, input.trim() ? { input, followUp } : null, content => {
    if (typeof content.input !== 'string') return false
    setInput(content.input.slice(0, 5000))
    const previous = content.followUp
    setFollowUp(previous && typeof previous.previous_question === 'string' && typeof previous.previous_answer === 'string'
      ? { previous_question: [...previous.previous_question].slice(0, 2000).join(''), previous_answer: [...previous.previous_answer].slice(0, 4000).join('') } : null)
    setIncludePrevious(false); setIncludeProfile(false); setAcceptedAI(false)
  })
  const threadRef = useRef(null)
  const inputRef = useRef(null)
  const composerRef = useRef(null)
  const stickToLatest = useRef(true)
  const pendingComposerFocus = useRef(false)
  const questionDraftRef = useRef(null)
  const pendingQuestionFocus = useRef(false)
  useEffect(() => {
    if (visible && pendingQuestionFocus.current && preparedQuestion && revealElement(questionDraftRef.current)) pendingQuestionFocus.current = false
  }, [preparedQuestion?.index, visible])
  const profileValue = (field, value) => {
    if (typeof value !== 'string' && typeof value !== 'number') return t('pilot.notProvided')
    if (field === 'babyAge') return t(`pilot.ages.${value}`, { defaultValue: String(value) })
    if (['feedingType', 'feeding_type'].includes(field)) return t(`tracking.${value}`, { defaultValue: String(value) })
    if (['birthType', 'birth_type'].includes(field)) return value === 'vaginal' ? t('pilot.vaginal') : value === 'c-section' ? t('pilot.csection') : String(value)
    if (field === 'baby_age_days' && typeof value === 'number') return t('flows.ai.days', { count: value })
    if (field === 'sleep_hours_avg' && typeof value === 'number') return t('flows.ai.hours', { count: value })
    return String(value)
  }
  const revealComposer = () => {
    pendingComposerFocus.current = true; setComposerRequest(value => value + 1)
  }
  const scrollToLatest = () => {
    const thread = threadRef.current
    if (thread) thread.scrollTop = thread.scrollHeight
    stickToLatest.current = true; setHasNewMessages(false)
  }
  useEffect(() => {
    if (!visible) return
    if (stickToLatest.current) scrollToLatest()
    else setHasNewMessages(true)
  }, [messages, loading, visible])
  useEffect(() => {
    if (initialDraft) { setInput(initialDraft); revealComposer() }
  }, [draftVersion])
  useEffect(() => {
    if (visible && pendingComposerFocus.current) {
      pendingComposerFocus.current = false; revealElement(composerRef.current)
    }
  }, [composerRequest, visible])
  useEffect(() => {
    if (!visible || !inputRef.current) return
    const textarea = inputRef.current
    textarea.style.height = 'auto'
    textarea.style.height = `${Math.min(textarea.scrollHeight, 240)}px`
  }, [input, visible])
  useEffect(() => { setAcceptedAI(false) }, [includeProfile])

  const sendMessage = async (e) => {
    e.preventDefault()
    if (!input.trim() || loading || !acceptedAI) return

    const userMessage = {
      role: 'user',
      content: input,
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    const queryText = input
    const selectedPrevious = includePrevious ? followUp : null
    setSubmission({ query: queryText, previous: selectedPrevious, includeProfile })
    stickToLatest.current = true
    revealElement(threadRef.current)
    setInput('')
    setLoading(true)
    setFailed(false)
    setTaskStatus('pending')

    try {
      // Check if async mode is enabled (default).
      const asyncMode = import.meta.env.VITE_ASYNC_MODE !== 'false'
      
      if (asyncMode) {
        // Use task manager for async processing.
        const taskData = {
          query: queryText,
          language: i18n.resolvedLanguage || 'ja',
          include_profile: includeProfile,
          include_previous: Boolean(selectedPrevious),
          previous_exchange: selectedPrevious,
        }
        // Determine priority based on query content.
        let priority = 'medium'
        if (/\b(urgent|emergency|help|crisis|immediate)\b|緊急|救急|助けて|今すぐ|息ができない/i.test(queryText)) {
          priority = 'high'
        }
        
        try {
          const result = await taskManager.submitTask('ai_chat', taskData, {
            priority,
            timeout: 300000 // 5 minutes
          })
          if (result.error) throw new Error('AI response unavailable')
          
          const assistantMessage = {
            role: 'assistant',
            generated: !result.error,
            content: result.response || result.text || '',
            question: queryText,
            suggestions: result.suggestions || [],
            red_flags: result.red_flags || [],
            validation: result.validation || null,
            presentation: result.presentation || null,
            timestamp: new Date()
          }
          
          setMessages(prev => [...prev, assistantMessage])
          setTaskStatus('completed')
        } catch (taskError) {
          console.error('Task error:', taskError)
          throw taskError
        }
      } else {
        // Synchronous mode (fallback).
        const response = await api.post('/api/chat', {
          query: queryText,
          user_id: userId,
          language: i18n.resolvedLanguage || 'ja',
          include_profile: includeProfile,
          include_previous: Boolean(selectedPrevious),
          previous_exchange: selectedPrevious,
        })
        if (response.error) throw new Error('AI response unavailable')

        const assistantMessage = {
          role: 'assistant',
          generated: !response.error,
          content: response.response || response.text || '',
          question: queryText,
          suggestions: response.suggestions || [],
          red_flags: response.red_flags || [],
          validation: response.validation || null,
          presentation: response.presentation || null,
          timestamp: new Date()
        }

        setMessages(prev => [...prev, assistantMessage])
        setTaskStatus('completed')
      }
      setFollowUp(null); setIncludePrevious(false); setAcceptedAI(false)
      await draft.clear()
    } catch (error) {
      console.error('Chat error:', error)
      setTaskStatus('failed')
      setFailed(true)
      setInput(current => current.trim() ? current : queryText)
      const errorMessage = {
        role: 'assistant',
        content: t('pilot.chatUnavailable'),
        timestamp: new Date()
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setLoading(false)
      setTaskStatus(null)
    }
  }

  return (
    <div className="chat-interface">
      <header className="guided-chat">
        <h2>{t('pilot.askTitle')}</h2>
        <p>{t('pilot.guidedChatIntro')}</p>
        <details className="chat-scenes"><summary>{t('ui.chat.exampleQuestions')}</summary><div className="pilot-actions">
          {['crying', 'feeding', 'rest', 'appointment'].map(scene => <button key={scene} type="button"
            className="pilot-button secondary" disabled={loading} onClick={() => { setInput(t(`pilot.questions.${scene}`)); revealComposer() }}>{t(`pilot.scenes.${scene}`)}</button>)}
        </div></details>
        <p>{t('pilot.chatBoundary')}</p>
      </header>
      <details className="chat-support"><summary>{t('work.humanHelp')}</summary><SupportDirectory userId={userId} visible={visible} onPrepareSheet={onPrepareSheet} /></details>
      <div className="chat-thread-heading"><h3 id="chat-thread-heading">{t('ui.chat.conversation')}</h3>
        {hasNewMessages && <button type="button" className="pilot-button secondary" onClick={() => {
          scrollToLatest(); threadRef.current?.focus({ preventScroll: true })
        }}>{t('ui.chat.latest')}</button>}
      </div>
      <p className="chat-thread-status" role="status">{loading ? t('work.chatWaiting')
        : messages[messages.length - 1]?.generated ? t('ui.chat.answerReady') : ''}</p>
      <div className="chat-messages" ref={threadRef} role="region" aria-labelledby="chat-thread-heading" tabIndex={0}
        onScroll={() => {
          const thread = threadRef.current
          stickToLatest.current = thread.scrollHeight - thread.scrollTop - thread.clientHeight < 48
          if (stickToLatest.current) setHasNewMessages(false)
        }}>
        {messages.map((msg, idx) => (
          <article key={idx} className={`message ${msg.role}`} aria-label={t(msg.role === 'user' ? 'ui.chat.you' : 'ui.chat.assistant')}>
            {msg.generated && msg.presentation?.summary_excerpt && <section className="answer-excerpt">
              <h4>{t('flows.ai.summary')}</h4><p>{msg.presentation.summary_excerpt}</p><small>{t('flows.ai.excerptNotice')}</small>
            </section>}
            <div className="message-content">
              {msg.content}
            </div>
            {msg.suggestions && msg.suggestions.length > 0 && (
              <div className="suggestions">
                <strong>{t('chat.suggestions')}</strong>
                <ul>
                  {msg.suggestions.map((suggestion, i) => (
                    <li key={i}>
                      {suggestion}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {msg.red_flags && msg.red_flags.length > 0 && (
              <div className="red-flags">
                <strong>⚠️ {t('chat.important')}</strong>
                <ul>
                  {msg.red_flags.map((flag, i) => (
                    <li key={i}>{flag}</li>
                  ))}
                </ul>
              </div>
            )}
            {msg.generated && <><small className="ai-label">{t('pilot.aiLabel')}</small>
              {msg.presentation && <details className="answer-context"><summary>{t('flows.ai.provided')}</summary>
                <p>{t('flows.ai.providedNotice')}</p><p className="preserve-lines">{msg.presentation.provided_question}</p>
                {Object.entries(msg.presentation.provided_profile || {}).map(([field, value]) => <p key={field}>
                  {t(`flows.ai.profileFields.${field}`)}: {profileValue(field, value)}
                </p>)}
                {msg.presentation.provided_previous_exchange && <details><summary>{t('polish.previousExchange')}</summary>
                  <p>{t('polish.previousQuestion')}</p><p className="preserve-lines">{msg.presentation.provided_previous_exchange.previous_question}</p>
                  <p>{t('polish.previousAnswer')}</p><p className="preserve-lines">{msg.presentation.provided_previous_exchange.previous_answer}</p>
                </details>}
              </details>}
              {msg.presentation && <section><h4>{t('flows.ai.questions')}</h4>
                {msg.presentation.clarifying_questions?.length > 0 ? <ul>{msg.presentation.clarifying_questions.map((question, index) => <li key={index}>{question}</li>)}</ul>
                  : <p>{t('flows.ai.noQuestions')}</p>}<small>{t('flows.ai.questionsNotice')}</small>
              </section>}
              <section><h4>{t('flows.ai.sources')}</h4>
                {msg.presentation?.sources?.some(source => source.kind === 'retrieved_document' && publicHttps(source.url))
                  ? <ul>{msg.presentation.sources.filter(source => source.kind === 'retrieved_document' && publicHttps(source.url)).map((source, index) => <li key={index}>
                    <a href={publicHttps(source.url)} target="_blank" rel="noreferrer">{source.title}</a>
                  </li>)}</ul> : <p>{t('flows.ai.noSources')}</p>}
                <small>{t('flows.ai.sourcesNotice')}</small>
              </section>
              {msg.question && msg.content && <button type="button" className="pilot-button secondary" disabled={loading} onClick={() => {
                setFollowUp({ previous_question: [...msg.question].slice(0, 2000).join(''), previous_answer: [...msg.content].slice(0, 4000).join('') })
                setIncludePrevious(false); setAcceptedAI(false)
                revealComposer()
              }}>{t('polish.continueQuestion')}</button>}
              {onPrepareSheet && <button type="button" className="pilot-button secondary" onClick={() => {
                if (preparedQuestion && preparedQuestion.index !== idx && preparedQuestion.text.trim() && !window.confirm(t('flows.ai.replaceQuestion'))) return
                if (preparedQuestion?.index !== idx) {
                  pendingQuestionFocus.current = true; setPreparedQuestion({ index: idx, text: (msg.question || '').slice(0, 250) })
                }
              }}>
                {t('flows.ai.prepareQuestion')}</button>}
              {preparedQuestion?.index === idx && <section className="pilot-panel"><label>{t('flows.ai.questionDraft')}
                <textarea ref={questionDraftRef} rows={4} maxLength={250} value={preparedQuestion.text} onChange={event => setPreparedQuestion(previous => ({ ...previous, text: event.target.value }))} />
              </label><p>{t('flows.ai.questionNotice')}</p>
                <button type="button" className="pilot-button secondary" disabled={!preparedQuestion.text.trim()} onClick={() => {
                  onPrepareSheet(preparedQuestion.text); setPreparedQuestion(null)
                }}>{t('flows.ai.useQuestion')}</button>
                <button type="button" className="pilot-button secondary" onClick={() => setPreparedQuestion(null)}>{t('tracking.cancel')}</button>
              </section>}
            </>}
          </article>
        ))}
            {loading && (
          <div className="message assistant">
            <div className="message-content">
              <span className="typing-indicator">
                {taskStatus === 'pending' ? t('chat.processing') || 'Processing...' : 
                 taskStatus === 'processing' ? t('chat.thinking') || 'Thinking...' : 
                 t('chat.thinking') || 'Thinking...'}
              </span>
              {taskStatus && (
                <div className="task-status">
                  <span className={`status-badge ${taskStatus}`}>
                    {taskStatus === 'pending' ? '⏳' : 
                     taskStatus === 'processing' ? '🔄' : 
                     taskStatus === 'failed' ? '❌' : '✓'}
                  </span>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      <form className="chat-composer" onSubmit={sendMessage} aria-labelledby="chat-composer-heading">
      <h3 id="chat-composer-heading" ref={composerRef} tabIndex={-1}>{t('ui.chat.writeQuestion')}</h3>
      <DraftRecoveryNotice draft={draft} disabled={loading} compact />
      {loading && <p className="field-hint">{t('work.chatWaiting')}</p>}
      {failed && <p role="alert">{t('work.retryDraft')}</p>}
      {followUp && <section className="pilot-panel follow-up-preview"><h3>{t('polish.followUpTitle')}</h3>
        <p>{t('polish.followUpNotice')}</p><details open><summary>{t('polish.previousExchange')}</summary>
          <p>{t('polish.previousQuestion')}</p><pre>{followUp.previous_question}</pre>
          <p>{t('polish.previousAnswer')}</p><pre>{followUp.previous_answer}</pre>
        </details>
        <label><input type="checkbox" disabled={loading} checked={includePrevious} onChange={event => {
          setIncludePrevious(event.target.checked); setAcceptedAI(false)
        }} />{t('polish.confirmPrevious')}</label>
        <button type="button" className="pilot-button secondary" disabled={loading} onClick={() => { setFollowUp(null); setIncludePrevious(false); setAcceptedAI(false) }}>{t('polish.removePrevious')}</button>
      </section>}
      <label className="chat-input-label" htmlFor="chat-question">{t('polish.currentQuestion')}</label>
      <textarea id="chat-question" ref={inputRef} rows={3} maxLength={5000} value={input}
        onChange={event => setInput(event.target.value)} placeholder={t('chat.placeholder')} disabled={loading}
        aria-describedby="chat-input-hint" className="chat-input" />
      <p id="chat-input-hint" className="field-hint">{t('ui.chat.inputHint')}</p>
      <details className="submission-preview"><summary>{t(loading ? 'ui.chat.sentContent' : 'polish.actualSubmission')}</summary>
        <p>{t('polish.currentQuestion')}</p><pre>{(loading ? submission?.query : input) || t('pilot.notProvided')}</pre>
        <p>{t((loading ? submission?.previous : includePrevious && followUp) ? 'polish.previousIncluded' : 'polish.previousExcluded')}</p>
        {(loading ? submission?.previous : includePrevious && followUp) && <>
          <p>{t('polish.previousQuestion')}</p><pre>{(loading ? submission.previous : followUp).previous_question}</pre>
          <p>{t('polish.previousAnswer')}</p><pre>{(loading ? submission.previous : followUp).previous_answer}</pre>
        </>}
        <p>{t((loading ? submission?.includeProfile : includeProfile) ? 'ui.chat.profileIncluded' : 'ui.chat.profileExcluded')}</p>
      </details>
      <AIUseNotice accepted={acceptedAI} onChange={setAcceptedAI} disabled={loading}
        includeProfile={includeProfile} onProfileChange={setIncludeProfile} />
      <div className="chat-composer-actions">
        <button type="submit" disabled={loading || !input.trim() || !acceptedAI} className="send-button">
          {t(loading ? 'ui.chat.sending' : failed ? 'work.retrySend' : 'chat.send')}
        </button>
        {(input.trim() || followUp || draft.hasSavedDraft) && <button type="button" className="pilot-button secondary" disabled={loading} onClick={() => {
          if (window.confirm(t('polish.deleteChatDraftConfirm'))) { setInput(''); setFollowUp(null); setIncludePrevious(false); setAcceptedAI(false); draft.clear() }
        }}>{t('polish.deleteDraft')}</button>}
      </div>
      <p className="field-hint">{t('work.sessionDraftNotice')}</p>
      </form>
    </div>
  )
}

export default ChatInterface

