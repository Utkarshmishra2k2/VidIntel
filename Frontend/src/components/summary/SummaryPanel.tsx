import type { ImportantMoment, VideoMeta } from '../../types'
import { formatTime } from '../../utils/time'
import './summary.css'

interface Props {
  summary: string | null
  keyTakeaways: string[]
  suggestedQuestions: string[]
  importantMoments: ImportantMoment[]
  videos: VideoMeta[]
  onAskQuestion: (question: string) => void
  onJumpToMoment: (videoId: string, time: number) => void
}

export function SummaryPanel({
  summary,
  keyTakeaways,
  suggestedQuestions,
  importantMoments,
  videos,
  onAskQuestion,
  onJumpToMoment,
}: Props) {
  const isPlaylist = videos.length > 1
  const titleFor = (videoId: string) => videos.find((v) => v.video_id === videoId)?.title || videoId

  if (!summary && keyTakeaways.length === 0 && suggestedQuestions.length === 0 && importantMoments.length === 0) {
    return null
  }

  return (
    <div className="summary-panel">
      {summary && (
        <div>
          <h3>Summary</h3>
          <p className="summary-text">{summary}</p>
        </div>
      )}

      {keyTakeaways.length > 0 && (
        <div>
          <h3>Key takeaways</h3>
          <ul className="takeaways">
            {keyTakeaways.map((t, i) => (
              <li key={i}>{t}</li>
            ))}
          </ul>
        </div>
      )}

      {importantMoments.length > 0 && (
        <div>
          <h3>Important moments</h3>
          <div className="chip-list">
            {importantMoments.map((m, i) => (
              <button
                key={i}
                type="button"
                className="chip"
                onClick={() => onJumpToMoment(m.video_id, m.time)}
                title={isPlaylist ? titleFor(m.video_id) : undefined}
              >
                <span className="chip-time">{formatTime(m.time)}</span> {m.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {suggestedQuestions.length > 0 && (
        <div>
          <h3>Ask something like…</h3>
          <div className="chip-list">
            {suggestedQuestions.map((q, i) => (
              <button key={i} type="button" className="chip" onClick={() => onAskQuestion(q)}>
                {q}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
