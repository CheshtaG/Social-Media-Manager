import { useState, useRef, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import '../App.css'

const API_BASE = '/api'

function formatScriptLines(text) {
  if (!text || typeof text !== 'string') return []
  return text.split('\n')
}

function parseTable(text) {
  const lines = (text || '')
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line.length > 0)
  if (lines.length < 2) return null
  const header = lines[0]
  if (!header.includes('|')) return null
  const headerCells = header.split('|').map((c) => c.trim()).filter(Boolean)
  if (headerCells.length < 3) return null
  const rows = []
  for (let i = 1; i < lines.length; i += 1) {
    const line = lines[i]
    if (!line.includes('|')) continue
    const cells = line.split('|').map((c) => c.trim()).filter(Boolean)
    if (cells.length < 3) continue
    // Skip markdown separator row
    if (cells.every((c) => /^-+$/.test(c))) continue
    rows.push(cells)
  }
  if (rows.length === 0) return null
  return { header: headerCells, rows }
}

function ScriptDisplay({ script }) {
  const table = parseTable(script)
  if (table) {
    const { header, rows } = table
    return (
      <div className="script-display">
        <table className="script-table">
          <thead>
            <tr>
              {header.map((cell, idx) => (
                <th key={idx}>{cell}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, rIdx) => (
              <tr key={rIdx}>
                {row.map((cell, cIdx) => (
                  <td key={cIdx}>{cIdx === 0 ? <strong>{cell}</strong> : cell}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )
  }
  const lines = formatScriptLines(script)
  return (
    <div className="script-display">
      {lines.map((line, i) => {
        const trimmed = line.trim()
        const isSectionHeader = /^\[.+\]$/.test(trimmed)
        const isVoLabel = trimmed === 'VO:'
        const isEmpty = trimmed === ''
        return (
          <div
            key={i}
            className={
              isEmpty
                ? 'script-line script-line--blank'
                : isSectionHeader
                  ? 'script-line script-line--header'
                  : isVoLabel
                    ? 'script-line script-line--vo'
                    : 'script-line script-line--dialogue'
            }
          >
            {isEmpty ? '\u00A0' : line}
          </div>
        )
      })}
    </div>
  )
}

function renderAiMessage(content) {
  if (!content || typeof content !== 'string') {
    return <div className="message-content">{content}</div>
  }
  const lines = content.split('\n').map((line) => line.trim())
  const bulletLines = lines.filter((line) => line.startsWith('- '))
  if (bulletLines.length === 0) {
    return <div className="message-content">{content}</div>
  }
  const introLine = lines.find((line) => line.length > 0 && !line.startsWith('- ')) || ''
  const bullets = bulletLines.map((line) => line.replace(/^-+\s*/, ''))
  return (
    <div className="message-content">
      {introLine && <div className="recommendation-intro">{introLine}</div>}
      <ul className="recommendation-list">
        {bullets.map((item, idx) => {
          const match = item.match(/^(Duration|Tone|Target audience):\s*([^—-]+)(.*)$/i)
          if (match) {
            const label = match[1]
            const value = match[2].trim()
            const rest = (match[3] || '').trim()
            return (
              <li key={idx}>
                <span>{label}: </span>
                <strong>{value}</strong>
                {rest ? <span> {rest}</span> : null}
              </li>
            )
          }
          return <li key={idx}>{item}</li>
        })}
      </ul>
    </div>
  )
}

function getDurationOverride(text) {
  const t = (text || '').toLowerCase()
  if (/\b(1\s*min|one\s*minute|60\s*s|60\s*sec|60\s*second)\b/.test(t)) return '1 min'
  if (/\b(30\s*s|30\s*sec|30\s*second|half\s*minute)\b/.test(t)) return '30s'
  if (/\b(15\s*s|15\s*sec|15\s*second)\b/.test(t)) return '15s'
  return null
}

function getToneOverride(text) {
  const t = (text || '').toLowerCase()
  if (/\b(playful|fun|chaotic)\b/.test(t)) return 'Playful / Fun'
  if (/\b(motivational|inspiring)\b/.test(t)) return 'Motivational / Inspiring'
  if (/\b(aesthetic|soft|cozy)\b/.test(t)) return 'Aesthetic / Soft / Cozy'
  if (/\b(storytelling|cinematic)\b/.test(t)) return 'Storytelling / Cinematic'
  if (/\b(educational|informative|instructional)\b/.test(t)) return 'Educational / Informative'
  return null
}

function formatDurationLabel(value) {
  if (!value) return ''
  if (value === '1 min') return '1 minute'
  if (value === '30s') return '30 seconds'
  if (value === '15s') return '15 seconds'
  return value
}

function GeneratePage() {
  const location = useLocation()
  const state = location.state

  const [script, setScript] = useState(state?.script ?? null)
  const [messages, setMessages] = useState(state?.messages ?? [])
  const [recommendation, setRecommendation] = useState(state?.recommendation ?? null)
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [leftPanelWidth, setLeftPanelWidth] = useState(35)
  const conversationEndRef = useRef(null)
  const appRef = useRef(null)

  const MIN_PANEL = 25
  const MAX_PANEL = 75

  const handleResizeStart = (e) => {
    e.preventDefault()
    const onMouseMove = (e) => {
      const container = appRef.current
      if (!container) return
      const rect = container.getBoundingClientRect()
      const width = rect.width
      const x = e.clientX - rect.left
      let percent = (x / width) * 100
      percent = Math.min(MAX_PANEL, Math.max(MIN_PANEL, percent))
      setLeftPanelWidth(percent)
    }

    const onMouseUp = () => {
      document.removeEventListener('mousemove', onMouseMove)
      document.removeEventListener('mouseup', onMouseUp)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }

    document.addEventListener('mousemove', onMouseMove)
    document.addEventListener('mouseup', onMouseUp)
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
  }

  const scrollToBottom = () => {
    conversationEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const hasScript = script !== null && !error
  const originalPrompt = messages.find((m) => m.role === 'user')?.content ?? ''
  const waitingForConfirmation = !hasScript && messages.length > 0 && recommendation
  const showSplit = hasScript || messages.length > 0

  const handleGenerateFromRecommendation = async () => {
    if (!waitingForConfirmation) return
    const newMessages = [...messages, { role: 'user', content: 'Generate script' }]
    setMessages(newMessages)
    setInput('')
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE}/generate-script`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: originalPrompt,
          duration: recommendation.suggested_duration,
          tone: recommendation.suggested_tone,
          language: 'English',
          conversation_history: newMessages,
        }),
      })
      if (!res.ok) {
        const errBody = await res.text()
        throw new Error(errBody || `Request failed (${res.status})`)
      }
      const data = await res.json()
      if (data && typeof data.script === 'string') {
        setScript(data.script)
        setMessages((prev) => [...prev, { role: 'ai', content: "Here's your script." }])
      } else {
        throw new Error('Invalid response: missing script')
      }
    } catch (err) {
      setError(err.message || 'Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async () => {
    const text = input.trim()
    if (!text) return

    setError(null)
    const newMessages = [...messages, { role: 'user', content: text }]
    setMessages(newMessages)
    setInput('')
    setLoading(true)

    try {
      if (waitingForConfirmation) {
        // Collect user preferences and respond with a confirmation message.
        const durationOverride = getDurationOverride(text)
        const toneOverride = getToneOverride(text)
        const currentDuration = recommendation?.suggested_duration || '30s'
        const currentTone = recommendation?.suggested_tone || 'Playful / Fun'
        const nextDuration = durationOverride || currentDuration
        const nextTone = toneOverride || currentTone
        if (durationOverride || toneOverride) {
          setRecommendation({
            suggested_duration: nextDuration,
            suggested_tone: nextTone,
          })
        }
        const updates = []
        if (durationOverride && durationOverride !== currentDuration) {
          updates.push(
            `Changing the duration from ${formatDurationLabel(currentDuration)} to ${formatDurationLabel(nextDuration)}.`
          )
        }
        if (toneOverride && toneOverride !== currentTone) {
          updates.push(`Changing the tone from ${currentTone} to ${nextTone}.`)
        }
        const reply =
          updates.length > 0
            ? updates.join(' ')
            : 'Got it. I have noted your preference.'
        setMessages((prev) => [...prev, { role: 'ai', content: reply }])
        setLoading(false)
        return
      }
      if (hasScript) {
        // Optimize existing script
        const res = await fetch(`${API_BASE}/optimize-script`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            current_script: script,
            conversation_history: newMessages,
          }),
        })
        if (!res.ok) {
          const errBody = await res.text()
          throw new Error(errBody || `Request failed (${res.status})`)
        }
        const data = await res.json()
        const aiReply = data.message || 'Done.'
        setMessages((prev) => [...prev, { role: 'ai', content: aiReply }])
        if (data.script) {
          setScript(data.script)
        }
      } else {
        // First message: recommendation only, no script yet (right side stays empty)
        const res = await fetch(`${API_BASE}/recommend-script`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt: text }),
        })
        if (!res.ok) {
          const errBody = await res.text()
          throw new Error(errBody || `Request failed (${res.status})`)
        }
        const data = await res.json()
        if (data && typeof data.message === 'string') {
          setRecommendation({
            suggested_duration: data.suggested_duration || '30s',
            suggested_tone: data.suggested_tone || 'Playful',
          })
          setMessages((prev) => [...prev, { role: 'ai', content: data.message }])
        } else {
          throw new Error('Invalid response: missing recommendation')
        }
      }
    } catch (err) {
      setError(err.message || 'Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleRegenerate = async () => {
    if (!originalPrompt.trim()) return
    setError(null)
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/generate-script`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: originalPrompt.trim(),
          duration: recommendation?.suggested_duration || '30s',
          tone: recommendation?.suggested_tone || 'Playful',
          language: 'English',
          conversation_history: messages,
        }),
      })
      if (!res.ok) {
        const errBody = await res.text()
        throw new Error(errBody || `Request failed (${res.status})`)
      }
      const data = await res.json()
      if (data && typeof data.script === 'string') {
        setScript(data.script)
        setMessages((prev) => [...prev, { role: 'ai', content: "Here's a new version." }])
      } else {
        throw new Error('Invalid response: missing script')
      }
    } catch (err) {
      setError(err.message || 'Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      ref={appRef}
      className={`app ${showSplit ? 'app--split' : ''}`}
      style={showSplit ? { '--split-left': `${leftPanelWidth}%` } : undefined}
    >
      <Link to="/" className="back-link">
        ← Back
      </Link>

      <div className="generate-left">
        <div className="conversation-area">
          {!hasScript && messages.length === 0 && (
            <p className="conversation-placeholder">
              Describe your reel idea below, or <Link to="/create/reel">start from the Create Reel page</Link>.
            </p>
          )}
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`message message--${msg.role}`}
              role={msg.role === 'ai' ? 'status' : undefined}
            >
              <span className="message-label">
                {msg.role === 'user' ? 'You' : 'AI'}
              </span>
              {msg.role === 'ai' ? renderAiMessage(msg.content) : <div className="message-content">{msg.content}</div>}
              {msg.role === 'ai' && i === messages.length - 1 && waitingForConfirmation && (
                <div className="message-content generate-script-btn-wrap">
                  <button
                    type="button"
                    className="generate-script-btn"
                    onClick={handleGenerateFromRecommendation}
                    disabled={loading}
                    aria-busy={loading}
                  >
                    {loading ? 'Generating…' : 'Generate script'}
                  </button>
                </div>
              )}
            </div>
          ))}
          {loading && (
            <div className="message message--ai">
              <span className="message-label">AI</span>
              <div className="message-content message-loading">
                Generating…
              </div>
            </div>
          )}
          <div ref={conversationEndRef} />
        </div>
        {error && (
          <div className="generate-left-error" role="alert">
            {error}
          </div>
        )}
        <div className="input-area">
          <div className="input-row">
            <div className="text-box-wrapper">
              <textarea
                className="text-box"
                placeholder={
                  waitingForConfirmation
                    ? 'Add more preferences (optional)…'
                    : hasScript
                      ? 'Type a message…'
                      : "What's your reel idea?"
                }
                value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault()
                      handleSubmit()
                    }
                  }}
                  disabled={loading}
                  aria-label="Message"
                />
                {hasScript && (
                  <button
                    type="button"
                    className="regenerate-btn regenerate-btn--inline"
                    onClick={handleRegenerate}
                    disabled={loading}
                    aria-busy={loading}
                    aria-label="Regenerate"
                    title="Regenerate"
                  >
                    {loading ? '…' : <span className="regenerate-icon regenerate-icon--char" aria-hidden="true">↻</span>}
                  </button>
                )}
                <button
                  type="button"
                  className="send-btn"
                  onClick={handleSubmit}
                  disabled={loading}
                  aria-label="Send"
                  title="Send (Enter)"
                >
                  ↑
                </button>
              </div>
            </div>
        </div>
      </div>

      {showSplit && (
        <div
          className="resize-handle"
          onMouseDown={handleResizeStart}
          role="separator"
          aria-valuenow={leftPanelWidth}
          aria-valuemin={MIN_PANEL}
          aria-valuemax={MAX_PANEL}
          aria-label="Resize panels"
        />
      )}

      <div className="generate-right" aria-hidden={!showSplit}>
        {hasScript ? (
          <>
            <div className="output-heading-row">
              <h3 className="output-heading">Script</h3>
            </div>
            <div className="script-scroll">
              <ScriptDisplay script={script} />
            </div>
          </>
        ) : showSplit ? (
          <div className="script-scroll script-scroll--empty" aria-label="Script will appear here after you confirm in the chat" />
        ) : null}
      </div>
    </div>
  )
}

export default GeneratePage
