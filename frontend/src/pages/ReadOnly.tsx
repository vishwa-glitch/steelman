import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ApiError, getShared } from '../api'
import { ScorecardView } from '../components/ScorecardView'
import { Transcript } from '../components/Transcript'
import { SHOWCASE } from '../showcase'
import type { DebateView } from '../types'

function DebateRead({ debate, label }: { debate: DebateView; label: string }) {
  return (
    <>
      <section className="debate-head">
        <p className="eyebrow">{label}</p>
        <h1>{debate.motion}</h1>
        <p className="mute">
          A visitor argued {debate.user_side === 'pro' ? 'for' : 'against'}; the AI ({debate.difficulty}) argued{' '}
          {debate.user_side === 'pro' ? 'against' : 'for'}.
        </p>
      </section>
      <Transcript turns={debate.turns} scorecard={debate.scorecard} />
      {debate.scorecard && <ScorecardView scorecard={debate.scorecard} judge={debate.judge} />}
      <p>
        <Link to="/">Try a debate yourself</Link>
      </p>
    </>
  )
}

/** A recorded debate bundled with the site: no network needed. */
export function RecordedPage() {
  const { key } = useParams()
  const item = SHOWCASE.find((s) => s.key === key)
  if (!item)
    return (
      <section className="panel">
        <p>That recorded debate doesn't exist.</p>
        <Link to="/">Back to the start</Link>
      </section>
    )
  return <DebateRead debate={item.debate} label="Recorded debate" />
}

/** A debate someone shared by link. */
export function SharedPage() {
  const { slug = '' } = useParams()
  const [debate, setDebate] = useState<DebateView | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    getShared(slug)
      .then(setDebate)
      .catch((e: unknown) =>
        setError(e instanceof ApiError && e.status === 404 ? "That shared debate doesn't exist." : 'This debate could not be loaded right now.'),
      )
  }, [slug])
  if (error)
    return (
      <section className="panel">
        <p className="error" role="alert">
          {error}
        </p>
        <Link to="/">Back to the start</Link>
      </section>
    )
  if (!debate) return <p className="mute">Loading the debate…</p>
  return <DebateRead debate={debate} label="Shared debate" />
}
