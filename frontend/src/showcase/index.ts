import type { DebateView } from '../types'
import museums from './museums.json'

/** Recorded debates, saved as static files so they play with no backend and no AI calls. */
export const SHOWCASE: { key: string; blurb: string; debate: DebateView }[] = [
  {
    key: 'museums',
    blurb: 'A visitor argues against free entry; the friendly AI argues for it.',
    debate: museums as DebateView,
  },
]
