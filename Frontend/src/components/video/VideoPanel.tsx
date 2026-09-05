import { useEffect, useRef, useState } from 'react'
import type { VideoMeta } from '../../types'
import { formatDuration, formatTime } from '../../utils/time'
import { VideoPlayer, type VideoPlayerHandle } from './VideoPlayer'
import './video.css'

export interface SeekRequest {
  videoId: string
  time: number
  nonce: number
}

interface Props {
  videos: VideoMeta[]
  activeVideoId: string
  onSelectVideo: (videoId: string) => void
  seekRequest: SeekRequest | null
  onPlaybackTimeChange: (seconds: number) => void
  onAskAboutMoment: (seconds: number) => void
}

export function VideoPanel({
  videos,
  activeVideoId,
  onSelectVideo,
  seekRequest,
  onPlaybackTimeChange,
  onAskAboutMoment,
}: Props) {
  const playerRef = useRef<VideoPlayerHandle>(null)
  const [currentTime, setCurrentTime] = useState(0)
  const activeVideo = videos.find((v) => v.video_id === activeVideoId) ?? videos[0]

  useEffect(() => {
    if (!seekRequest) return
    if (seekRequest.videoId !== activeVideoId) {
      onSelectVideo(seekRequest.videoId)
      return
    }
    playerRef.current?.seekTo(seekRequest.time)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [seekRequest])

  useEffect(() => {
    const interval = setInterval(() => {
      const t = playerRef.current?.getCurrentTime() ?? 0
      setCurrentTime(t)
      onPlaybackTimeChange(t)
    }, 1000)
    return () => clearInterval(interval)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeVideoId])

  if (!activeVideo) return null

  return (
    <div className="video-panel">
      <VideoPlayer ref={playerRef} videoId={activeVideo.video_id} />

      <div className="video-meta-row">
        <div>
          <h2>{activeVideo.title || 'Untitled video'}</h2>
          <p className="channel">{activeVideo.channel || 'Unknown channel'}</p>
        </div>
        {activeVideo.duration_seconds != null && (
          <span className="duration">{formatDuration(activeVideo.duration_seconds)}</span>
        )}
      </div>

      <button
        type="button"
        className="chip ask-moment-btn"
        onClick={() => onAskAboutMoment(currentTime)}
        title="Ask a question about what's happening right now in the video"
      >
        📍 Ask about this moment <span className="chip-time">{formatTime(currentTime)}</span>
      </button>

      {videos.length > 1 && (
        <div className="playlist-list">
          {videos.map((v) => (
            <button
              key={v.video_id}
              type="button"
              className={`playlist-item ${v.video_id === activeVideoId ? 'active' : ''} ${
                v.transcript_available ? '' : 'failed'
              }`}
              onClick={() => onSelectVideo(v.video_id)}
            >
              {v.thumbnail_url && <img src={v.thumbnail_url} alt="" />}
              <div>
                <div className="title">{v.title || v.video_id}</div>
                <div className="status">
                  {v.transcript_available ? `${v.chunk_count} indexed segments` : 'No transcript available'}
                </div>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
