import { highlight } from '../highlight'
import type { Round, Scorecard, Side, Turn } from '../types'
import { ROUNDS } from '../types'

interface Props {
  turns: Turn[]
  userSide?: Side
  scorecard?: Scorecard | null
  /** Text of a turn that is still streaming in. */
  streaming?: { side: Side; round: Round; text: string } | null
}

function quotesFor(scorecard: Scorecard | null | undefined, side: Side): string[] {
  const s = scorecard?.sides.find((x) => x.side === side)
  return s ? s.scores.flatMap((c) => c.quotes) : []
}

function Cell({ side, round, turns, userSide, scorecard, streaming }: Props & { side: Side; round: Round }) {
  const turn = turns.find((t) => t.side === side && t.round === round)
  const live = streaming && streaming.side === side && streaming.round === round ? streaming.text : null
  const who = userSide ? (side === userSide ? 'You' : 'AI') : null
  return (
    <div className={`cell cell-${side}`}>
      <div className="cell-head">
        <span className="tag">{side === 'pro' ? 'For' : 'Against'}</span>
        {who && <span className="who">{who}</span>}
      </div>
      {turn ? (
        <p>
          {highlight(turn.text, quotesFor(scorecard, side)).map((seg, i) =>
            seg.quoted ? <mark key={i}>{seg.text}</mark> : <span key={i}>{seg.text}</span>,
          )}
        </p>
      ) : live !== null ? (
        <p aria-live="polite">
          {live}
          <span className="caret" aria-hidden="true" />
        </p>
      ) : (
        <p className="empty">Not yet spoken</p>
      )}
    </div>
  )
}

export function Transcript(props: Props) {
  return (
    <div className="transcript">
      {ROUNDS.map((round) => (
        <section key={round} className="round">
          <h3>{round}</h3>
          <div className="pair">
            <Cell {...props} side="pro" round={round} />
            <Cell {...props} side="con" round={round} />
          </div>
        </section>
      ))}
    </div>
  )
}
