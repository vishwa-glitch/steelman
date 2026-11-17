/** "Your debates": debates started in this browser, kept in localStorage. Storage can be missing or
 * blocked (private windows, previews), so every read and write is guarded and the site works without it. */
import type { Side } from './types'

export interface SavedDebate {
  id: string
  topic: string
  side: Side
  startedAt: string
  result?: 'won' | 'lost'
  score?: string
}

const KEY = 'steelman.debates.v1'
const MAX = 20

export function loadDebates(): SavedDebate[] {
  try {
    const raw = localStorage.getItem(KEY)
    const list = raw ? (JSON.parse(raw) as unknown) : []
    return Array.isArray(list) ? (list as SavedDebate[]).filter((d) => d && typeof d.id === 'string') : []
  } catch {
    return []
  }
}

export function saveDebate(entry: SavedDebate): void {
  try {
    const rest = loadDebates().filter((d) => d.id !== entry.id)
    const old = loadDebates().find((d) => d.id === entry.id)
    const merged = { ...old, ...entry, startedAt: old?.startedAt ?? entry.startedAt }
    localStorage.setItem(KEY, JSON.stringify([merged, ...rest].slice(0, MAX)))
  } catch {
    // storage unavailable: the debate still works, it just won't be listed
  }
}

export function forgetDebate(id: string): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(loadDebates().filter((d) => d.id !== id)))
  } catch {
    // ignore
  }
}
