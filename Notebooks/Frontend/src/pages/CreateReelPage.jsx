import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import './CreateReelPage.css'

const API_BASE = '/api'

function CreateReelPage() {
  const navigate = useNavigate()
  const [reelAbout, setReelAbout] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleGenerateScript = async () => {
    const promptText = reelAbout.trim()
    if (!promptText) return

    setError(null)
    setLoading(true)

    try {
      const res = await fetch(`${API_BASE}/recommend-script`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: promptText }),
      })
      if (!res.ok) {
        const errBody = await res.text()
        throw new Error(errBody || `Request failed (${res.status})`)
      }
      const data = await res.json()
      if (data && typeof data.message === 'string') {
        navigate('/generate', {
          state: {
            messages: [
              { role: 'user', content: promptText },
              { role: 'ai', content: data.message },
            ],
            recommendation: {
              suggested_duration: data.suggested_duration || '30s',
              suggested_tone: data.suggested_tone || 'Playful',
            },
          },
        })
      } else {
        throw new Error('Invalid response: missing recommendation')
      }
    } catch (err) {
      setError(err.message || 'Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="create-reel-page">
      <Link to="/" className="create-reel-back">
        ← Back
      </Link>

      <div className="create-reel-content">
        <h1 className="create-reel-heading">What's your reel about?</h1>

        <div className="create-reel-input-wrapper">
          <textarea
            className="create-reel-prompt-box"
            placeholder="Describe your reel idea..."
            value={reelAbout}
            onChange={(e) => setReelAbout(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                handleGenerateScript()
              }
            }}
            disabled={loading}
            aria-label="Describe your reel idea"
          />
          <button
            type="button"
            className="create-reel-attach-btn"
            title="Attachment"
            aria-label="Attachment"
          >
            <span className="create-reel-attach-icon">+</span>
          </button>
          <button
            type="button"
            className={`create-reel-send-btn ${loading ? 'create-reel-send-btn--loading' : ''}`}
            onClick={handleGenerateScript}
            disabled={loading}
            aria-label={loading ? 'Generating…' : 'Generate'}
            title={loading ? 'Generating…' : 'Generate (Enter)'}
          >
            {loading ? (
              <span className="create-reel-send-spinner" aria-hidden />
            ) : (
              <span className="create-reel-send-icon">↑</span>
            )}
          </button>
        </div>

        {error && (
          <div className="create-reel-error" role="alert">
            {error}
          </div>
        )}
      </div>
    </div>
  )
}

export default CreateReelPage
