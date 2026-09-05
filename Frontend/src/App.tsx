import { useState } from 'react'
import { analyzeResource, extractErrorMessage } from './api/client'
import { ChatPanel } from './components/chat/ChatPanel'
import './components/layout/layout.css'
import { ResourceInput } from './components/resource/ResourceInput'
import { ResourceStatusBanner } from './components/resource/ResourceStatusBanner'
import { SummaryPanel } from './components/summary/SummaryPanel'
import { VideoPanel, type SeekRequest } from './components/video/VideoPanel'
import { useLocalStorage } from './hooks/useLocalStorage'
import type { AnalyzeResponse } from './types'

type Status = 'idle' | 'loading' | 'ready' | 'partial' | 'error'

export default function App() {
  const [resource, setResource] = useLocalStorage<AnalyzeResponse | null>('vidintel:resource', null)
  const [status, setStatus] = useState<Status>(resource ? (resource.status === 'partial' ? 'partial' : 'ready') : 'idle')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [activeVideoId, setActiveVideoId] = useState<string>(resource?.videos[0]?.video_id ?? '')

  const [seekRequest, setSeekRequest] = useState<SeekRequest | null>(null)
  const [prefillQuestion, setPrefillQuestion] = useState<{ text: string; nonce: number } | null>(null)
  const [momentToAsk, setMomentToAsk] = useState<{ time: number; nonce: number } | null>(null)

  async function handleAnalyze(input: string) {
    setStatus('loading')
    setErrorMessage(null)
    try {
      const result = await analyzeResource(input)
      setResource(result)
      setActiveVideoId(result.videos[0]?.video_id ?? '')
      setStatus(result.status === 'partial' ? 'partial' : 'ready')
    } catch (err) {
      setStatus('error')
      setErrorMessage(extractErrorMessage(err))
    }
  }

  function handleJumpToSource(videoId: string, time: number) {
    setSeekRequest({ videoId, time, nonce: Date.now() })
  }

  function handleAskAboutMoment(seconds: number) {
    setMomentToAsk({ time: seconds, nonce: Date.now() })
  }

  function handleAskSuggested(question: string) {
    setPrefillQuestion({ text: question, nonce: Date.now() })
  }

  const showWorkspace = resource && (status === 'ready' || status === 'partial')

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="brand">
          VidIntel<span className="dot">.</span>
        </div>
        <div className="header-input">
          <ResourceInput onAnalyze={handleAnalyze} loading={status === 'loading'} />
        </div>
      </header>

      {(status === 'loading' || status === 'error' || status === 'partial') && (
        <div style={{ padding: '10px 20px 0' }}>
          <ResourceStatusBanner status={status} errorMessage={errorMessage} warnings={resource?.warnings} />
        </div>
      )}

      <div className="app-body">
        {showWorkspace && resource ? (
          <>
            <aside className="app-rail">
              <VideoPanel
                videos={resource.videos}
                activeVideoId={activeVideoId}
                onSelectVideo={setActiveVideoId}
                seekRequest={seekRequest}
                onPlaybackTimeChange={() => {}}
                onAskAboutMoment={handleAskAboutMoment}
              />
              <SummaryPanel
                summary={resource.summary}
                keyTakeaways={resource.key_takeaways}
                suggestedQuestions={resource.suggested_questions}
                importantMoments={resource.important_moments}
                videos={resource.videos}
                onAskQuestion={handleAskSuggested}
                onJumpToMoment={handleJumpToSource}
              />
            </aside>
            <main className="app-main">
              <ChatPanel
                key={resource.resource_id}
                resourceId={resource.resource_id}
                resourceType={resource.resource_type}
                videos={resource.videos}
                activeVideoId={activeVideoId}
                prefillQuestion={prefillQuestion}
                momentToAsk={momentToAsk}
                onJumpToSource={handleJumpToSource}
              />
            </main>
          </>
        ) : (
          <div className="app-empty-state">
            <h1>Ask any YouTube video a question</h1>
            <p>
              Paste a video or playlist URL above. VidIntel reads the transcript, builds a
              summary, and lets you ask questions with answers grounded in what's actually
              said — with clickable timestamps that jump straight to the moment.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
