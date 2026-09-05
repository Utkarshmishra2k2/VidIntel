import { useEffect, useRef, useState, type FormEvent } from 'react'
import { extractErrorMessage, queryResource } from '../../api/client'
import { useLocalStorage } from '../../hooks/useLocalStorage'
import type { ChatMessage, Message, VideoMeta } from '../../types'
import { formatTime } from '../../utils/time'
import { MessageBubble } from './MessageBubble'
import './chat.css'

interface Props {
  resourceId: string
  resourceType: 'video' | 'playlist'
  videos: VideoMeta[]
  activeVideoId: string
  prefillQuestion: { text: string; nonce: number } | null
  momentToAsk: { time: number; nonce: number } | null
  onJumpToSource: (videoId: string, time: number) => void
}

const HISTORY_TURNS = 6 // how many past messages to send back for follow-up context

export function ChatPanel({
  resourceId,
  resourceType,
  videos,
  activeVideoId,
  prefillQuestion,
  momentToAsk,
  onJumpToSource,
}: Props) {
  const [messages, setMessages] = useLocalStorage<ChatMessage[]>(`vidintel:chat:${resourceId}`, [])
  const [input, setInput] = useState('')
  const [scope, setScope] = useState<'all' | 'current'>('all')
  const [activeMoment, setActiveMoment] = useState<number | null>(null)
  const [sending, setSending] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  const isPlaylist = resourceType === 'playlist' && videos.length > 1

  useEffect(() => {
    if (prefillQuestion) setInput(prefillQuestion.text)
  }, [prefillQuestion])

  useEffect(() => {
    if (momentToAsk) setActiveMoment(momentToAsk.time)
  }, [momentToAsk])

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages])

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    const question = input.trim()
    if (!question || sending) return

    const userMsg: ChatMessage = { id: crypto.randomUUID(), role: 'user', content: question }
    const pendingMsg: ChatMessage = { id: crypto.randomUUID(), role: 'assistant', content: '', pending: true }

    const history: Message[] = messages
      .filter((m) => !m.pending && !m.error)
      .slice(-HISTORY_TURNS)
      .map((m) => ({ role: m.role, content: m.content }))

    setMessages([...messages, userMsg, pendingMsg])
    setInput('')
    setSending(true)
    const askedWithMoment = activeMoment
    setActiveMoment(null)

    try {
      const response = await queryResource({
        resource_id: resourceId,
        question,
        history,
        current_time: askedWithMoment ?? undefined,
        video_id: isPlaylist && scope === 'current' ? activeVideoId : undefined,
      })

      setMessages((prev) =>
        prev.map((m) =>
          m.id === pendingMsg.id
            ? { ...m, content: response.answer, sources: response.sources, pending: false }
            : m,
        ),
      )
    } catch (err) {
      const message = extractErrorMessage(err)
      setMessages((prev) =>
        prev.map((m) => (m.id === pendingMsg.id ? { ...m, pending: false, error: message } : m)),
      )
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="chat-panel">
      {isPlaylist && (
        <div className="chat-scope-row">
          Search:
          <select value={scope} onChange={(e) => setScope(e.target.value as 'all' | 'current')}>
            <option value="all">All videos in this playlist</option>
            <option value="current">This video only</option>
          </select>
        </div>
      )}

      <div className="chat-messages" ref={scrollRef}>
        {messages.length === 0 && (
          <div className="chat-empty-state">
            Ask anything about the content — answers are grounded in the transcript, with
            clickable timestamps so you can jump straight to the moment.
          </div>
        )}
        {messages.map((m) => (
          <MessageBubble key={m.id} message={m} videos={videos} onJumpToSource={onJumpToSource} />
        ))}
      </div>

      <div className="chat-input-row">
        {activeMoment !== null && (
          <div className="moment-pill">
            📍 Asking about {formatTime(activeMoment)}
            <button type="button" onClick={() => setActiveMoment(null)} aria-label="Remove moment context">
              ×
            </button>
          </div>
        )}
        <form className="chat-input-form" onSubmit={handleSubmit}>
          <textarea
            placeholder="Ask a question about the video…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                handleSubmit(e)
              }
            }}
            disabled={sending}
          />
          <button type="submit" className="btn btn-primary" disabled={sending || !input.trim()}>
            {sending ? 'Asking…' : 'Ask'}
          </button>
        </form>
      </div>
    </div>
  )
}
