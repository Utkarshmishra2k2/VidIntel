// Mirrors backend/app/schemas.py field-for-field.
// If you change one, change the other.

export type ResourceType = 'video' | 'playlist'
export type Role = 'user' | 'assistant'

export interface Message {
  role: Role
  content: string
}

export interface VideoMeta {
  video_id: string
  title: string | null
  channel: string | null
  duration_seconds: number | null
  thumbnail_url: string | null
  transcript_available: boolean
  chunk_count: number
  error: string | null
}

export interface ImportantMoment {
  video_id: string
  time: number
  label: string
}

export interface AnalyzeRequest {
  resource: string
}

export interface AnalyzeResponse {
  resource_id: string
  resource_type: ResourceType
  videos: VideoMeta[]
  total_chunks: number
  summary: string | null
  key_takeaways: string[]
  suggested_questions: string[]
  important_moments: ImportantMoment[]
  status: 'ready' | 'partial'
  warnings: string[]
}

export interface QueryRequest {
  resource_id: string
  question: string
  history?: Message[]
  current_time?: number
  video_id?: string
}

export interface SourceChunk {
  video_id: string
  start: number
  end: number
  snippet: string
}

export interface QueryResponse {
  answer: string
  sources: SourceChunk[]
  resource_id: string
}

// --- Frontend-only types ---

export interface ChatMessage extends Message {
  id: string
  sources?: SourceChunk[]
  pending?: boolean
  error?: string
}
