import React, { useState, useRef, useEffect } from 'react'
import { Mic, MicOff, Volume2 } from 'lucide-react'
import api from '../utils/api'
import './VoiceInput.css'

function VoiceInput({ onTranscript, language = 'en' }) {
  const [isRecording, setIsRecording] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [error, setError] = useState(null)
  const mediaRecorderRef = useRef(null)
  const audioChunksRef = useRef([])

  useEffect(() => {
    return () => {
      // Cleanup on unmount
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop()
      }
    }
  }, [])

  const startRecording = async () => {
    try {
      setError(null)
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      })
      
      mediaRecorderRef.current = mediaRecorder
      audioChunksRef.current = []

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data)
        }
      }

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
        await processAudio(audioBlob)
        
        // Stop all tracks
        stream.getTracks().forEach(track => track.stop())
      }

      mediaRecorder.start()
      setIsRecording(true)
    } catch (err) {
      console.error('Error starting recording:', err)
      setError('Failed to access microphone. Please check permissions.')
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
    }
  }

  const processAudio = async (audioBlob) => {
    setIsProcessing(true)
    try {
      const formData = new FormData()
      formData.append('audio', audioBlob, 'recording.webm')
      formData.append('language', language)

      const response = await api.post('/api/voice/speech-to-text', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      })

      if (response.text && onTranscript) {
        onTranscript(response.text)
      }
    } catch (err) {
      console.error('Error processing audio:', err)
      setError('Failed to process audio. Please try again.')
    } finally {
      setIsProcessing(false)
    }
  }

  const handleTextToSpeech = async (text) => {
    try {
      const response = await api.post('/api/voice/text-to-speech', {
        text,
        language,
        speed: 1.0
      }, {
        responseType: 'blob'
      })

      const audioUrl = URL.createObjectURL(response)
      const audio = new Audio(audioUrl)
      audio.play()
    } catch (err) {
      console.error('Error with text-to-speech:', err)
      setError('Failed to generate speech.')
    }
  }

  return (
    <div className="voice-input">
      {error && (
        <div className="voice-error">
          {error}
        </div>
      )}
      
      <div className="voice-controls">
        {!isRecording ? (
          <button
            onClick={startRecording}
            disabled={isProcessing}
            className="voice-button record"
            title="Start recording"
          >
            <Mic size={20} />
            {isProcessing ? 'Processing...' : 'Record'}
          </button>
        ) : (
          <button
            onClick={stopRecording}
            className="voice-button stop"
            title="Stop recording"
          >
            <MicOff size={20} />
            Recording...
          </button>
        )}
      </div>
    </div>
  )
}

export default VoiceInput
