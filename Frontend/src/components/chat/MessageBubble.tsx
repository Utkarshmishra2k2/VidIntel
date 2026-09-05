import { useState } from 'react'
import type { ChatMessage, VideoMeta } from '../../types'
import { SourceCard } from './SourceCard'
import './chat.css'

interface Props {
  message: ChatMessage
  videos: VideoMeta[]
  onJumpToSource: (videoId: string, time: number) => void
}

export function MessageBubble({ message, videos, onJumpToSource }: Props) {
  const [copied, setCopied] = useState(false)
  const isPlaylist = videos.length > 1
  const titleFor = (videoId: string) => videos.find((v) => v.video_id === videoId)?.title

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(message.content)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      // clipboard API unavailable — silently do nothing rather than error out
    }
  }

  return (
    <div className={`message-row ${message.role}`}>
      <div className={`message-bubble ${message.error ? 'error' : ''}`}>
        {message.pending ? 'Thinking…' : message.error || message.content}
      </div>

      {message.role === 'assistant' && !message.pending && !message.error && (
        <div className="message-actions">
          <button type="button" className="btn-ghost" onClick={handleCopy}>
            {copied ? 'Copied ✓' : 'Copy answer'}
          </button>
        </div>
      )}

      {message.sources && message.sources.length > 0 && (
        <div className="sources-block">
          <span className="sources-label">Sources</span>
          {message.sources.map((s, i) => (
            <SourceCard
              key={i}
              source={s}
              videoTitle={titleFor(s.video_id) ?? undefined}
              showVideoLabel={isPlaylist}
              onJump={onJumpToSource}
            />
          ))}
        </div>
      )}
    </div>
  )
}
