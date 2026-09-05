import { forwardRef, useEffect, useImperativeHandle, useRef } from 'react'
import type { YTPlayerInstance } from '../../types/youtube'
import './video.css'

export interface VideoPlayerHandle {
  seekTo: (seconds: number) => void
  getCurrentTime: () => number
}

interface Props {
  videoId: string
}

let apiLoadPromise: Promise<void> | null = null

function loadYouTubeApi(): Promise<void> {
  if (window.YT?.Player) return Promise.resolve()
  if (apiLoadPromise) return apiLoadPromise

  apiLoadPromise = new Promise((resolve) => {
    const previous = window.onYouTubeIframeAPIReady
    window.onYouTubeIframeAPIReady = () => {
      previous?.()
      resolve()
    }
    const tag = document.createElement('script')
    tag.src = 'https://www.youtube.com/iframe_api'
    document.head.appendChild(tag)
  })
  return apiLoadPromise
}

export const VideoPlayer = forwardRef<VideoPlayerHandle, Props>(function VideoPlayer(
  { videoId },
  ref,
) {
  const containerRef = useRef<HTMLDivElement>(null)
  const playerRef = useRef<YTPlayerInstance | null>(null)

  useEffect(() => {
    let cancelled = false

    loadYouTubeApi().then(() => {
      if (cancelled || !containerRef.current || !window.YT) return
      playerRef.current = new window.YT.Player(containerRef.current, {
        videoId,
        playerVars: { rel: 0, modestbranding: 1 },
      })
    })

    return () => {
      cancelled = true
      playerRef.current?.destroy()
      playerRef.current = null
    }
  }, [videoId])

  useImperativeHandle(ref, () => ({
    seekTo: (seconds: number) => {
      playerRef.current?.seekTo(seconds, true)
      playerRef.current?.playVideo()
    },
    getCurrentTime: () => playerRef.current?.getCurrentTime() ?? 0,
  }))

  return (
    <div className="video-player">
      <div ref={containerRef} />
    </div>
  )
})
