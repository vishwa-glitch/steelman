import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ApiError, createDebate, getStatus } from '../api'
import topicBank from '../data/topics.json'
import { forgetDebate, loadDebates, saveDebate } from '../history'
import type { SavedDebate } from '../history'
import { SHOWCASE } from '../showcase'
import type { Difficulty, Side } from '../types'

const BANK = topicBank as Record<string, string[]>
const CATEGORIES = ['All', ...Object.keys(BANK)]
const ALL_TOPICS = Object.values(BANK).flat()
const PER_PAGE = 6

function pick<T>(list: T[], not?: T): T {
  const pool = list.length > 1 ? list.filter((x) => x !== not) : list
  return pool[Math.floor(Math.random() * pool.length)]
}

export function Home() {
  const navigate = useNavigate()
  const [topic, setTopic] = useState('')
  const [category, setCategory] = useState('All')
  const [shuffle, setShuffle] = useState(0)
  const [side, setSide] = useState<Side>('pro')
  const [difficulty, setDifficulty] = useState<Difficulty>('sharp')
  const [live, setLive] = useState<'checking' | 'on' | 'off'>('checking')
  const [notice, setNotice] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [starting, setStarting] = useState(false)
  const [mine, setMine] = useState<SavedDebate[]>(() => loadDebates())

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

  const suggestions = useMemo(() => {
    const list = category === 'All' ? ALL_TOPICS : BANK[category]
    const start = (shuffle * PER_PAGE) % list.length
    return [...list.slice(start), ...list.slice(0, start)].slice(0, PER_PAGE)
  }, [category, shuffle])

  async function start(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setStarting(true)
    try {
      const d = await createDebate(topic, side, difficulty)
      if (d.id) saveDebate({ id: d.id, topic: d.motion, side, startedAt: new Date().toISOString() })
      navigate(`/debate/${d.id}`)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong. Please try again.')
      if (err instanceof ApiError && (err.status === 503 || err.status === 0)) setLive('off')
    } finally {
      setStarting(false)
    }
  }

  const tooShort = topic.trim().length < 10

  return (
    <>
      <section className="hero">
        <p className="eyebrow">AI debate practice</p>
        <h1>
          Argue your side. The AI argues the other. <em>A judge you can audit</em> scores you both.
        </h1>
        <p className="lede">
          Three rounds: opening, rebuttal, closing. Then a separate AI judge scores both sides and quotes the exact lines
          behind every score, so you can check its reasoning.
        </p>
      </section>

      <section className="panel start" aria-labelledby="start-title">
        <h2 id="start-title">Start a debate</h2>
        {live === 'off' && (
          <p className="notice" role="status">
            {notice ?? 'Live mode is resting.'} <a href="#recorded">Watch a recorded debate</a>
          </p>
        )}
        <form onSubmit={start}>
          <label htmlFor="topic">Debate topic</label>
          <div className="topic-row">
            <input
              id="topic"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="Write your own topic, e.g. “Homework should be optional.”"
              maxLength={200}
              autoComplete="off"
            />
            <button
              type="button"
              className="btn ghost"
              onClick={() => setTopic((t) => pick(category === 'All' ? ALL_TOPICS : BANK[category], t))}
            >
              Surprise me
            </button>
          </div>
          <p className="hint">Write any statement people could argue for or against, or pick one below.</p>

          <div className="cats" role="tablist" aria-label="Topic categories">
            {CATEGORIES.map((c) => (
              <button
                type="button"
                role="tab"
                aria-selected={c === category}
                key={c}
                className={c === category ? 'cat on' : 'cat'}
                onClick={() => {
                  setCategory(c)
                  setShuffle(0)
                }}
              >
                {c}
              </button>
            ))}
          </div>
          <div className="chips">
            {suggestions.map((t) => (
              <button type="button" key={t} className={t === topic ? 'chip on' : 'chip'} onClick={() => setTopic(t)}>
                {t}
              </button>
            ))}
            <button type="button" className="chip more" onClick={() => setShuffle((s) => s + 1)}>
              More ideas ↻
            </button>
          </div>

          <div className="choices">
            <fieldset>
              <legend>Your side</legend>
              <div className="seg">
                {(['pro', 'con'] as Side[]).map((s) => (
                  <label key={s} className={side === s ? 'on' : ''}>
                    <input type="radio" name="side" checked={side === s} onChange={() => setSide(s)} />
                    {s === 'pro' ? 'For · you open' : 'Against · AI opens'}
                  </label>
                ))}
              </div>
            </fieldset>
            <fieldset>
              <legend>Opponent</legend>
              <div className="seg">
                {(['friendly', 'sharp'] as Difficulty[]).map((d) => (
                  <label key={d} className={difficulty === d ? 'on' : ''}>
                    <input type="radio" name="difficulty" checked={difficulty === d} onChange={() => setDifficulty(d)} />
                    {d === 'friendly' ? 'Friendly' : 'Sharp'}
                  </label>
                ))}
              </div>
            </fieldset>
          </div>
          {error && (
            <p className="error" role="alert">
              {error}
            </p>
          )}
          <button className="btn primary" disabled={live !== 'on' || starting || tooShort}>
            {starting
              ? 'Checking the topic…'
              : live === 'checking'
                ? 'Checking live mode…'
                : tooShort
                  ? 'Write or pick a topic to start'
                  : 'Start the debate'}
          </button>
        </form>
      </section>

      {mine.length > 0 && (
        <section className="mine" aria-labelledby="mine-title">
          <h2 id="mine-title">Your debates</h2>
          <p className="mute small">Saved in this browser only.</p>
          <ul className="cards">
            {mine.map((d) => (
              <li key={d.id} className="card">
                <Link to={`/debate/${d.id}`} className="card-link">
                  <span className="card-motion">{d.topic}</span>
                  <span className="card-meta">
                    You argued {d.side === 'pro' ? 'for' : 'against'} ·{' '}
                    {d.result ? `you ${d.result} ${d.score ?? ''}` : 'unfinished'} ·{' '}
                    {new Date(d.startedAt).toLocaleDateString()}
                  </span>
                </Link>
                <button
                  className="forget"
                  aria-label={`Remove “${d.topic}” from this list`}
                  onClick={() => {
                    forgetDebate(d.id)
                    setMine(loadDebates())
                  }}
                >
                  ×
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="how" aria-labelledby="how-title">
        <p className="eyebrow">How it works</p>
        <h2 id="how-title">Three steps, two AIs, every score explained.</h2>
        <ol className="steps">
          <li>
            <span className="step-n">01</span>
            <h3>You argue</h3>
            <p>Pick a topic and a side. Type your turn, or speak it.</p>
          </li>
          <li>
            <span className="step-n">02</span>
            <h3>The AI argues back</h3>
            <p>An AI opponent answers your actual points, word by word as it writes.</p>
          </li>
          <li>
            <span className="step-n">03</span>
            <h3>A judge scores you both</h3>
            <p>A second AI scores four criteria and quotes the lines behind every score.</p>
          </li>
        </ol>
        <Link to="/how" className="btn ghost">
          See how it works in detail →
        </Link>
      </section>

      <section id="recorded" className="recorded" aria-labelledby="rec-title">
        <h2 id="rec-title">Recorded debates</h2>
        <p className="mute small">Real debates played on this site, saved with their verdicts. These always work.</p>
        <ul className="cards">
          {SHOWCASE.map(({ key, blurb, debate }) => (
            <li key={key} className="card">
              <Link to={`/recorded/${key}`} className="card-link">
                <span className="card-motion">{debate.motion}</span>
                <span className="card-meta">{blurb}</span>
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </>
  )
}
