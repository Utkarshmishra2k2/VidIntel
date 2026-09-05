export {}

export interface YTPlayerInstance {
  seekTo: (seconds: number, allowSeekAhead: boolean) => void
  playVideo: () => void
  getCurrentTime: () => number
  destroy: () => void
}

interface YTPlayerOptions {
  videoId: string
  playerVars?: Record<string, number | string>
  events?: {
    onReady?: () => void
    onError?: () => void
  }
}

declare global {
  interface Window {
    YT?: {
      Player: new (el: HTMLElement, options: YTPlayerOptions) => YTPlayerInstance
    }
    onYouTubeIframeAPIReady?: () => void
  }
}
