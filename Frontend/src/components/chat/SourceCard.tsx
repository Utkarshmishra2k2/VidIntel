import type { SourceChunk } from '../../types'
import { formatTime } from '../../utils/time'
import './chat.css'

interface Props {
  source: SourceChunk
  videoTitle?: string
  showVideoLabel: boolean
  onJump: (videoId: string, time: number) => void
}

export function SourceCard({ source, videoTitle, showVideoLabel, onJump }: Props) {
  return (
    <button
      type="button"
      className="source-card"
      onClick={() => onJump(source.video_id, source.start)}
    >
      <div>
        {showVideoLabel && <span className="source-video-label">{videoTitle || source.video_id}</span>}
        <span className="source-time">{formatTime(source.start)}</span>{' '}
        <span>{source.snippet}</span>
      </div>
    </button>
  )
}
