import axios, { AxiosError } from 'axios'
import type { AnalyzeRequest, AnalyzeResponse, QueryRequest, QueryResponse } from '../types'

// Fix: previously the frontend read process.env.REACT_APP_API_URL (a CRA
// convention) while the project standardized on Vite, whose env vars are
// exposed via import.meta.env and must be prefixed VITE_. That mismatch
// meant the configured API URL was silently ignored.
const baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const http = axios.create({
  baseURL,
  timeout: 120_000, // transcript fetch + indexing + LLM generation can be slow
})

/** FastAPI returns either `{detail: string}` or `{detail: [{msg, loc, ...}]}` (pydantic validation). */
export function extractErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<{ detail?: string | { msg: string }[] }>
    const detail = axiosError.response?.data?.detail

    if (typeof detail === 'string') return detail
    if (Array.isArray(detail) && detail.length > 0) {
      return detail.map((d) => d.msg).join('; ')
    }
    if (axiosError.code === 'ECONNABORTED') {
      return 'That took too long. The video may be long, or the local model is still warming up — try again.'
    }
    if (!axiosError.response) {
      return "Can't reach the server. Make sure the backend is running."
    }
    return `Something went wrong (${axiosError.response.status}).`
  }
  return 'Something unexpected went wrong.'
}

export async function analyzeResource(resource: string): Promise<AnalyzeResponse> {
  const body: AnalyzeRequest = { resource }
  const { data } = await http.post<AnalyzeResponse>('/api/analyze', body)
  return data
}

export async function queryResource(request: QueryRequest): Promise<QueryResponse> {
  const { data } = await http.post<QueryResponse>('/api/query', request)
  return data
}
