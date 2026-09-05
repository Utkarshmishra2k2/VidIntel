import { useState, type FormEvent } from 'react'
import './resource.css'

interface Props {
  onAnalyze: (resource: string) => void
  loading: boolean
}

export function ResourceInput({ onAnalyze, loading }: Props) {
  const [value, setValue] = useState('')
  const [fieldError, setFieldError] = useState<string | null>(null)

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    const trimmed = value.trim()
    if (!trimmed) {
      setFieldError('Paste a YouTube video or playlist URL to get started.')
      return
    }
    setFieldError(null)
    onAnalyze(trimmed)
  }

  return (
    <div className="resource-input">
      <form onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder="Paste a YouTube video or playlist URL…"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          disabled={loading}
          aria-label="YouTube video or playlist URL"
        />
        <button type="submit" className="btn btn-primary" disabled={loading}>
          {loading ? 'Analyzing…' : 'Analyze'}
        </button>
      </form>
      {fieldError && <span className="field-error">{fieldError}</span>}
      <span className="hint">
        Works with video URLs, playlist URLs, youtu.be links, or a raw video/playlist ID.
      </span>
    </div>
  )
}
