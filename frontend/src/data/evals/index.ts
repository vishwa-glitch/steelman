import v0 from './v0.json'

interface Count {
  n: number
  correct: number
  rate: number | null
}
interface Pairs {
  pairs: number
  same: number
  flips: number
  rate: number | null
}
export interface EvalReport {
  meta: {
    judge: string
    judge_model: string
    writer_model: string
    debates: number
    subset: number
    complete: boolean
    updated: string
  }
  summary: {
    progress: Record<string, string>
    valid_output: Record<string, { n: number; valid: number; rate: number | null }>
    accuracy: Record<string, Count>
    order_swap_consistency: Pairs
    rerun_consistency: Pairs
    length_bias: { pairs: number; mean_weak_gain: number | null; flips_to_weak: number }
    self_preference: {
      n: number
      margin_original: number | null
      margin_strong_reworded_by_judge_family: number | null
      margin_weak_reworded_by_judge_family: number | null
    }
    quotes: { kept: number; dropped: number; drop_rate: number | null }
  }
}

/** One entry per judge version, oldest first. Add v1 here when its results exist. */
export const REPORTS: EvalReport[] = [v0 as EvalReport]
