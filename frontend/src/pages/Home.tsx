import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ApiError, createDebate, getStatus } from '../api'
import { SHOWCASE } from '../showcase'
import type { Difficulty, Side } from '../types'

const PRESETS = [
  'Remote work is better for companies than office work.',
  'Smartphones should be banned in schools.',
  'A four-day work week should be the standard.',
  'Public transport should be free.',
  'Zoos should be closed.',
]

export function Home() {
  const navigate = useNavigate()
  const [motion, setMotion] = useState(PRESETS[0])
  const [side, setSide] = useState<Side>('pro')
  const [difficulty, setDifficulty] = useState<Difficulty>('sharp')
  const [live, setLive] = useState<'checking' | 'on' | 'off'>('checking')
  const [notice, setNotice] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [starting, setStarting] = useState(false)

  useEffect(() => {
    let cancelled = false
    getStatus()
      .then((s) => {
        if (cancelled) return
        setLive(s.live ? 'on' : 'off')
        setNotice(s.message)
      })
      .catch((e: unknown) => {
        if (cancelled) return
        setLive('off')
        setNotice(e instanceof ApiError ? e.message : 'Live mode is unavailable right now.')
      })
    return () => {
      cancelled = true
    }
  }, [])

  async function start(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setStarting(true)
    try {
      const d = await createDebate(motion, side, difficulty)
      navigate(`/debate/${d.id}`)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong. Please try again.')
      if (err instanceof ApiError && (err.status === 503 || err.status === 0)) setLive('off')
    } finally {
      setStarting(false)
    }
  }

  return (
    <>
      <section className="hero">
        <p className="eyebrow">AI debate practice</p>
        <h1>Argue your side. The AI argues the other. A judge you can audit scores you both.</h1>
        <p className="lede">
          Three rounds: opening, rebuttal, closing. The judge has to quote the exact lines behind every score, and
          code checks each quote is real.
        </p>
      </section>

      <section className="panel">
        <h2>Start a debate</h2>
        {live === 'off' && (
          <p className="notice" role="status">
            {notice ?? 'Live mode is resting.'} <a href="#recorded">Watch a recorded debate</a>
          </p>
        )}
        <form onSubmit={start}>
          <label htmlFor="motion">Motion</label>
          <input
            id="motion"
            value={motion}
            onChange={(e) => setMotion(e.target.value)}
            maxLength={200}
            minLength={10}
            required
          />
          <div className="chips">
            {PRESETS.map((p) => (
              <button type="button" key={p} className={p === motion ? 'chip on' : 'chip'} onClick={() => setMotion(p)}>
                {p}
              </button>
            ))}
          </div>
          <div className="choices">
            <fieldset>
              <legend>Your side</legend>
              {(['pro', 'con'] as Side[]).map((s) => (
                <label key={s} className={side === s ? 'radio on' : 'radio'}>
                  <input type="radio" name="side" checked={side === s} onChange={() => setSide(s)} />
                  {s === 'pro' ? 'For (you speak first)' : 'Against (AI speaks first)'}
                </label>
              ))}
            </fieldset>
            <fieldset>
              <legend>Opponent</legend>
              {(['friendly', 'sharp'] as Difficulty[]).map((d) => (
                <label key={d} className={difficulty === d ? 'radio on' : 'radio'}>
                  <input type="radio" name="difficulty" checked={difficulty === d} onChange={() => setDifficulty(d)} />
                  {d === 'friendly' ? 'Friendly' : 'Sharp'}
                </label>
              ))}
            </fieldset>
          </div>
          {error && (
            <p className="error" role="alert">
              {error}
            </p>
          )}
          <button className="primary" disabled={live !== 'on' || starting}>
            {starting ? 'Checking the motion…' : live === 'checking' ? 'Checking live mode…' : 'Start the debate'}
          </button>
        </form>
      </section>

      <section id="recorded" className="recorded">
        <h2>Recorded debates</h2>
        <p className="mute">Real debates played on this site, saved with their verdicts. These always work.</p>
        <ul>
          {SHOWCASE.map(({ key, blurb, debate }) => (
            <li key={key}>
              <Link to={`/recorded/${key}`}>
                <span className="motion">{debate.motion}</span>
                <span className="mute">{blurb}</span>
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </>
  )
}
