import { useCallback, useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ApiError, addTurn, getDebate, judgeDebate, streamAiTurn } from '../api'
import { ScorecardView } from '../components/ScorecardView'
import { Transcript } from '../components/Transcript'
import type { DebateView } from '../types'

const MIN = 20
const MAX = 1500
const message = (e: unknown) => (e instanceof ApiError ? e.message : 'Something went wrong. Please try again.')

export function DebatePage() {
  const { id = '' } = useParams()
  const [debate, setDebate] = useState<DebateView | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [streamText, setStreamText] = useState<string | null>(null)
  const [judging, setJudging] = useState(false)
  const [draft, setDraft] = useState('')
  const [sending, setSending] = useState(false)
  const [copied, setCopied] = useState(false)
  // One AI request at a time, even if an effect runs twice. Each request costs one of the day's AI calls.
  const busy = useRef(false)

  // Move the debate along: the AI speaks when it is its turn, and the judge runs once the debate is finished.
  // It stops at the first error and waits for "Try again", so a failing model can't loop and burn AI calls.
  const advance = useCallback(
    async (from: DebateView) => {
      if (busy.current) return
      busy.current = true
      setError(null)
      let d = from
      try {
        while (d.next?.who === 'ai' || (d.finished && !d.scorecard)) {
          if (d.next?.who === 'ai') {
            setStreamText('')
            d = await streamAiTurn(id, (piece) => setStreamText((t) => (t ?? '') + piece))
            setStreamText(null)
          } else {
            setJudging(true)
            d = await judgeDebate(id)
            setJudging(false)
          }
          setDebate(d)
        }
      } catch (e) {
        setError(message(e))
      } finally {
        setStreamText(null)
        setJudging(false)
        busy.current = false
      }
    },
    [id],
  )

  useEffect(() => {
    let cancelled = false
    getDebate(id)
      .then((d) => {
        if (cancelled) return
        setDebate(d)
        void advance(d)
      })
      .catch((e: unknown) => {
        if (!cancelled) setLoadError(message(e))
      })
    return () => {
      cancelled = true
    }
  }, [id, advance])

  async function submit(e: FormEvent) {
    e.preventDefault()
    setSending(true)
    setError(null)
    try {
      const d = await addTurn(id, draft)
      setDebate(d)
      setDraft('')
      void advance(d)
    } catch (err) {
      setError(message(err))
    } finally {
      setSending(false)
    }
  }

  if (loadError)
    return (
      <section className="panel">
        <p className="error" role="alert">
          {loadError}
        </p>
        <Link to="/">Back to the start</Link>
      </section>
    )
  if (!debate) return <p className="mute">Loading the debate…</p>

  const next = debate.next
  const shareUrl = debate.share_slug ? `${window.location.origin}/d/${debate.share_slug}` : null
  const who = next?.who
  const canRetry = who === 'ai' || (debate.finished && !debate.scorecard)

  return (
    <>
      <section className="debate-head">
        <p className="eyebrow">The motion</p>
        <h1>{debate.motion}</h1>
        <p className="mute">
          You argue {debate.user_side === 'pro' ? 'for' : 'against'}. The AI ({debate.difficulty}) argues{' '}
          {debate.user_side === 'pro' ? 'against' : 'for'}.
        </p>
      </section>

      <Transcript
        turns={debate.turns}
        userSide={debate.user_side}
        scorecard={debate.scorecard}
        streaming={streamText !== null && next ? { side: next.side, round: next.round, text: streamText } : null}
      />

      {error && (
        <div className="notice" role="alert">
          {error}{' '}
          {canRetry && (
            <button className="link" onClick={() => void advance(debate)}>
              Try again
            </button>
          )}
        </div>
      )}

      {who === 'user' && next && (
        <form className="panel turn-form" onSubmit={submit}>
          <label htmlFor="turn">Your {next.round}</label>
          <textarea
            id="turn"
            rows={6}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            maxLength={MAX}
            placeholder={
              next.round === 'opening'
                ? 'Make your case. Specific examples score higher than general claims.'
                : next.round === 'rebuttal'
                  ? "Answer the other side's points directly."
                  : 'Say why your side has won the main clashes.'
            }
          />
          <div className="turn-foot">
            <span className={draft.trim().length < MIN ? 'mute' : 'mute ok'}>
              {draft.trim().length} / {MAX} characters (minimum {MIN})
            </span>
            <button className="primary" disabled={sending || draft.trim().length < MIN}>
              {sending ? 'Sending…' : 'Submit turn'}
            </button>
          </div>
        </form>
      )}

      {judging && (
        <p className="notice" role="status">
          The judge is deliberating. This takes about 30 to 45 seconds.
        </p>
      )}

      {debate.scorecard && (
        <>
          <ScorecardView scorecard={debate.scorecard} judge={debate.judge} userSide={debate.user_side} />
          {shareUrl && (
            <section className="panel share">
              <span>Share this debate (read-only):</span>
              <code>{shareUrl}</code>
              <button
                className="link"
                onClick={() => {
                  void navigator.clipboard.writeText(shareUrl).then(() => setCopied(true))
                }}
              >
                {copied ? 'Copied' : 'Copy link'}
              </button>
            </section>
          )}
          <p>
            <Link to="/">Start another debate</Link>
          </p>
        </>
      )}
    </>
  )
}
