import type { JudgeMeta, Scorecard, Side } from '../types'
import { CRITERION_LABEL } from '../types'

interface Props {
  scorecard: Scorecard
  judge: JudgeMeta | null
  userSide?: Side
}

const total = (card: Scorecard, side: Side) =>
  card.sides.find((s) => s.side === side)?.scores.reduce((sum, c) => sum + c.score, 0) ?? 0

export function ScorecardView({ scorecard, judge, userSide }: Props) {
  const name = (side: Side) => (side === 'pro' ? 'For' : 'Against')
  const outcome = userSide ? (scorecard.winner === userSide ? 'You won.' : 'The AI won.') : null
  return (
    <section className="scorecard">
      <p className="eyebrow">The judge's verdict</p>
      <h2>
        {name(scorecard.winner)} wins, {total(scorecard, scorecard.winner)} to{' '}
        {total(scorecard, scorecard.winner === 'pro' ? 'con' : 'pro')}. {outcome}
      </h2>
      <p className="summary">{scorecard.summary}</p>
      <div className="pair">
        {(['pro', 'con'] as Side[]).map((side) => (
          <div key={side} className={`cell cell-${side}`}>
            <div className="cell-head">
              <span className="tag">{name(side)}</span>
              <span className="who">{total(scorecard, side)} / 40</span>
            </div>
            {scorecard.sides
              .find((s) => s.side === side)
              ?.scores.map((c) => (
                <div key={c.criterion} className="criterion">
                  <div className="criterion-head">
                    <span>{CRITERION_LABEL[c.criterion]}</span>
                    <span className="score">{c.score}</span>
                  </div>
                  <div className="bar" aria-hidden="true">
                    <div style={{ width: `${c.score * 10}%` }} />
                  </div>
                  <p className="reason">{c.reason}</p>
                  {c.quotes.map((q, i) => (
                    <blockquote key={i}>{q}</blockquote>
                  ))}
                </div>
              ))}
          </div>
        ))}
      </div>
      {judge && (
        <p className="fineprint">
          Judged by {judge.model} (judge {judge.version}). Every quote above was checked against the transcript by
          code: {judge.kept_quotes} kept, {judge.dropped_quotes} removed because they weren't in it. Highlighted
          text in the transcript is what the judge quoted. The AI's facts are not checked.
        </p>
      )}
    </section>
  )
}
