export type Side = 'pro' | 'con'
export type Round = 'opening' | 'rebuttal' | 'closing'
export type Difficulty = 'friendly' | 'sharp'
export type Criterion = 'argument_strength' | 'evidence' | 'rebuttal' | 'clarity'

export interface Turn {
  side: Side
  round: Round
  text: string
}

export interface CriterionScore {
  criterion: Criterion
  score: number
  quotes: string[]
  reason: string
}

export interface Scorecard {
  sides: { side: Side; scores: CriterionScore[] }[]
  winner: Side
  summary: string
}

export interface JudgeMeta {
  version: string
  model: string
  dropped_quotes: number
  kept_quotes: number
}

export interface DebateView {
  id?: string
  motion: string
  user_side: Side
  difficulty: Difficulty
  turns: Turn[]
  finished: boolean
  next: { side: Side; round: Round; who: 'user' | 'ai' } | null
  scorecard: Scorecard | null
  judge: JudgeMeta | null
  share_slug: string | null
}

export const ROUNDS: Round[] = ['opening', 'rebuttal', 'closing']
export const CRITERION_LABEL: Record<Criterion, string> = {
  argument_strength: 'Argument strength',
  evidence: 'Evidence',
  rebuttal: 'Rebuttal',
  clarity: 'Clarity',
}
