import React, { useState, useRef, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../utils/api'
import taskManager from '../utils/taskManager'
import AIUseNotice from './AIUseNotice'
import SupportDirectory from './SupportDirectory'
import useAccountDraft from '../utils/useAccountDraft'
import { DraftRecoveryNotice } from './DraftRecovery'
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
  const draft = useAccountDraft('chat', userId, input.trim() ? { input, followUp } : null, content => {
    if (typeof content.input !== 'string') return false
    setInput(content.input.slice(0, 5000))
    const previous = content.followUp
    setFollowUp(previous && typeof previous.previous_question === 'string' && typeof previous.previous_answer === 'string'
      ? { previous_question: [...previous.previous_question].slice(0, 2000).join(''), previous_answer: [...previous.previous_answer].slice(0, 4000).join('') } : null)
    setIncludePrevious(false); setIncludeProfile(false); setAcceptedAI(false)
  })
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])
  useEffect(() => { if (initialDraft) setInput(initialDraft) }, [draftVersion])
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
      <div className="guided-chat">
        <h2>{t('pilot.askTitle')}</h2>
        <p>{t('pilot.guidedChatIntro')}</p>
        <div className="pilot-actions">
          {['crying', 'feeding', 'rest', 'appointment'].map(scene => <button key={scene} type="button"
            className="pilot-button secondary" disabled={loading} onClick={() => setInput(t(`pilot.questions.${scene}`))}>{t(`pilot.scenes.${scene}`)}</button>)}
        </div>
        <p>{t('pilot.chatBoundary')}</p>
      </div>
      <details className="chat-support"><summary>{t('work.humanHelp')}</summary><SupportDirectory visible={visible} onPrepareSheet={onPrepareSheet} /></details>
      <p className="session-note">{t('work.sessionDraftNotice')}</p>
      <DraftRecoveryNotice draft={draft} disabled={loading} />
      {(input.trim() || followUp || draft.hasSavedDraft) && <button type="button" className="pilot-button secondary" disabled={loading} onClick={() => {
        if (window.confirm(t('polish.deleteChatDraftConfirm'))) { setInput(''); setFollowUp(null); setIncludePrevious(false); setAcceptedAI(false); draft.clear() }
      }}>{t('polish.deleteDraft')}</button>}
      <div className="chat-messages">
        {messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.role}`}>
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
              {msg.question && msg.content && <button type="button" className="pilot-button secondary" disabled={loading} onClick={() => {
                setFollowUp({ previous_question: [...msg.question].slice(0, 2000).join(''), previous_answer: [...msg.content].slice(0, 4000).join('') })
                setIncludePrevious(false); setAcceptedAI(false)
              }}>{t('polish.continueQuestion')}</button>}
            </>}
          </div>
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
        <div ref={messagesEndRef} />
      </div>

      {loading && <p role="status">{t('work.chatWaiting')}</p>}
      {failed && <div role="alert"><p>{t('work.retryDraft')}</p>
        <button className="pilot-button secondary" disabled={!acceptedAI || loading || !input.trim()} onClick={sendMessage}>{t('work.retrySend')}</button>
      </div>}
      {followUp && <section className="pilot-panel follow-up-preview"><h3>{t('polish.followUpTitle')}</h3>
        <p>{t('polish.followUpNotice')}</p><details open><summary>{t('polish.previousExchange')}</summary>
          <p>{t('polish.previousQuestion')}</p><pre>{followUp.previous_question}</pre>
          <p>{t('polish.previousAnswer')}</p><pre>{followUp.previous_answer}</pre>
        </details>
        <label><input type="checkbox" disabled={loading} checked={includePrevious} onChange={event => {
          setIncludePrevious(event.target.checked); setAcceptedAI(false)
        }} />{t('polish.confirmPrevious')}</label>
        <button type="button" disabled={loading} onClick={() => { setFollowUp(null); setIncludePrevious(false); setAcceptedAI(false) }}>{t('polish.removePrevious')}</button>
      </section>}
      <details className="pilot-panel"><summary>{t('polish.actualSubmission')}</summary><p>{t('polish.currentQuestion')}</p><pre>{input || t('pilot.notProvided')}</pre>
        <p>{t(includePrevious && followUp ? 'polish.previousIncluded' : 'polish.previousExcluded')}</p>
      </details>
      <AIUseNotice accepted={acceptedAI} onChange={setAcceptedAI} disabled={loading}
        includeProfile={includeProfile} onProfileChange={setIncludeProfile} />
      <form className="chat-input-form" onSubmit={sendMessage}>
        <input
          type="text"
          maxLength={5000}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={t('chat.placeholder')}
          disabled={loading}
          className="chat-input" />
        <button type="submit" disabled={loading || !input.trim() || !acceptedAI} className="send-button">
          {t('chat.send')}
        </button>
      </form>
    </div>
  )
}

export default ChatInterface

