import { createSseParser } from './sse'
import type { DebateView, Difficulty, Side } from './types'

const BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000'

/** An error with a message that is safe to show the user. `status` is 0 when the server can't be reached. */
export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

const OFFLINE = 'Live mode is unavailable right now. You can still watch the recorded debates.'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(BASE + path, { ...init, headers: { 'Content-Type': 'application/json' } })
  } catch {
    throw new ApiError(0, OFFLINE)
  }
  if (!res.ok) throw new ApiError(res.status, await errorMessage(res))
  return (await res.json()) as T
}

async function errorMessage(res: Response): Promise<string> {
  try {
    const body = (await res.json()) as { detail?: unknown }
    if (typeof body.detail === 'string') return body.detail
  } catch {
    // fall through
  }
  return res.status === 422 ? 'That input was not accepted.' : 'Something went wrong. Please try again.'
}

export const getStatus = () => request<{ live: boolean; message: string | null }>('/status')
export const getDebate = (id: string) => request<DebateView>(`/debates/${id}`)
export const getShared = (slug: string) => request<DebateView>(`/share/${slug}`)
export const judgeDebate = (id: string) => request<DebateView>(`/debates/${id}/judge`, { method: 'POST' })
export const createDebate = (motion: string, side: Side, difficulty: Difficulty) =>
  request<DebateView>('/debates', { method: 'POST', body: JSON.stringify({ motion, side, difficulty }) })
export const addTurn = (id: string, text: string) =>
  request<DebateView>(`/debates/${id}/turns`, { method: 'POST', body: JSON.stringify({ text }) })

interface AiEvent {
  delta?: string
  done?: boolean
  error?: string
  debate?: DebateView
}

/** Stream the AI's turn. Calls onDelta for each piece of text; resolves with the saved debate. */
export async function streamAiTurn(id: string, onDelta: (text: string) => void): Promise<DebateView> {
  let res: Response
  try {
    res = await fetch(`${BASE}/debates/${id}/ai-turn`, { method: 'POST' })
  } catch {
    throw new ApiError(0, OFFLINE)
  }
  if (!res.ok || !res.body) throw new ApiError(res.status, await errorMessage(res))
  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  const parse = createSseParser()
  let saved: DebateView | undefined
  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    for (const ev of parse(decoder.decode(value, { stream: true })) as AiEvent[]) {
      if (ev.delta) onDelta(ev.delta)
      if (ev.error) {
        if (ev.debate) return ev.debate // the turn was already taken elsewhere: show the saved state
        throw new ApiError(502, ev.error)
      }
      if (ev.done && ev.debate) saved = ev.debate
    }
  }
  if (!saved) throw new ApiError(502, "The AI's reply was cut off. Please try again.")
  return saved
}
