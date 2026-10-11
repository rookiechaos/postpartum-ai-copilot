import React, { useState, useRef, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../utils/api'
import taskManager from '../utils/taskManager'
import AIUseNotice from './AIUseNotice'
import SupportDirectory from './SupportDirectory'
import './ChatInterface.css'

function ChatInterface({ userId, initialDraft = '' }) {
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
  const [loading, setLoading] = useState(false)
  const [taskStatus, setTaskStatus] = useState(null)
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

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
    setInput('')
    setLoading(true)
    setTaskStatus('pending')

    try {
      // Check if async mode is enabled (default).
      const asyncMode = import.meta.env.VITE_ASYNC_MODE !== 'false'
      
      if (asyncMode) {
        // Use task manager for async processing.
        const taskData = {
          query: queryText,
          language: i18n.language,
          user_id: userId
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
          
          const assistantMessage = {
            role: 'assistant',
            generated: !result.error,
            content: result.response || result.text || '',
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
          language: i18n.language
        })

        const assistantMessage = {
          role: 'assistant',
          generated: !response.error,
          content: response.response || response.text || '',
          suggestions: response.suggestions || [],
          red_flags: response.red_flags || [],
          validation: response.validation || null,
          timestamp: new Date()
        }

        setMessages(prev => [...prev, assistantMessage])
        setTaskStatus('completed')
      }
    } catch (error) {
      console.error('Chat error:', error)
      setTaskStatus('failed')
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
      <details className="chat-support"><summary>{t('pilot.supportTitle')}</summary><SupportDirectory compact /></details>
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
            {msg.generated && <small className="ai-label">{t('pilot.aiLabel')}</small>}
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

      <AIUseNotice accepted={acceptedAI} onChange={setAcceptedAI} />
      <form className="chat-input-form" onSubmit={sendMessage}>
        <input
          type="text"
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

