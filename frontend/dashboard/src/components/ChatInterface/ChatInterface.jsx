// ChatInterface.jsx — Conversational chatbot UI with voice support

import { useState, useRef, useEffect } from 'react'
import { motion } from 'framer-motion'
import { sendChat } from '../../services/apiClient'

const PLACEHOLDER_MESSAGES = [
  "What's the weather in Mumbai right now?",
  "Is there any cyclone warning for Chennai?",
  "What crops should I sow in Delhi this month?",
  "कोलकाता में बारिश कब होगी?",
]

export default function ChatInterface({ userLocation }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: "👋 Hello! I'm WeatherGPT. Ask me about weather, disasters, or crop advisories for any Indian city.",
    }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [recording, setRecording] = useState(false)
  const [placeholder, setPlaceholder] = useState(PLACEHOLDER_MESSAGES[0])
  const bottomRef = useRef(null)
  const inputRef = useRef(null)

  // Cycle placeholder
  useEffect(() => {
    let i = 0
    const interval = setInterval(() => {
      i = (i + 1) % PLACEHOLDER_MESSAGES.length
      setPlaceholder(PLACEHOLDER_MESSAGES[i])
    }, 3500)
    return () => clearInterval(interval)
  }, [])

  // Scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = async (text) => {
    if (!text.trim() || loading) return
    const userMsg = { role: 'user', content: text }
    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const response = await sendChat(
        text,
        'en',
        userLocation?.lat,
        userLocation?.lon
      )
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: response.reply || 'No response received.' }
      ])
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: '⚠️ Unable to connect to WeatherGPT server. Please check your connection.' }
      ])
    } finally {
      setLoading(false)
    }
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage(input)
    }
  }

  const handleVoice = () => {
    if (!('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) {
      alert('Speech recognition not supported in this browser.')
      return
    }
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    const recognition = new SpeechRecognition()
    recognition.continuous = false
    recognition.interimResults = false
    recognition.lang = 'en-IN'

    setRecording(true)
    recognition.start()

    recognition.onresult = (e) => {
      const transcript = e.results[0][0].transcript
      setInput(transcript)
      setRecording(false)
    }
    recognition.onerror = () => setRecording(false)
    recognition.onend = () => setRecording(false)
  }

  return (
    <motion.div
      className="chat-panel glass"
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.3 }}
    >
      {/* Messages */}
      <div className="chat-messages">
        {messages.map((msg, i) => (
          <div key={i} className={`chat-msg ${msg.role}`}>
            <div className="chat-avatar">
              {msg.role === 'user' ? 'U' : 'W'}
            </div>
            <div className="chat-bubble">{msg.content}</div>
          </div>
        ))}
        {loading && (
          <div className="chat-msg assistant">
            <div className="chat-avatar">W</div>
            <div className="chat-bubble" style={{ color: 'var(--text-muted)' }}>
              <div className="spinner" style={{ display: 'inline-block', width: 14, height: 14 }} />
              {' '}Fetching live data...
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="chat-input-row">
        <button
          className={`chat-voice-btn ${recording ? 'recording' : ''}`}
          onClick={handleVoice}
          title="Voice input"
          id="voice-input-btn"
        >
          🎤
        </button>
        <input
          ref={inputRef}
          className="chat-input"
          placeholder={placeholder}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKey}
          id="chat-text-input"
        />
        <button
          className="chat-send-btn"
          onClick={() => sendMessage(input)}
          disabled={loading}
          id="chat-send-btn"
        >
          ➤
        </button>
      </div>
    </motion.div>
  )
}
