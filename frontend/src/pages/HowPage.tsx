import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { REPO_URL } from '../components/Layout'
import { REPORTS } from '../data/evals'

/** How Steelman works: the debate flow, the two AIs, how the judge is kept honest, and the stack. */
export function HowPage() {
  useEffect(() => {
    window.scrollTo(0, 0)
  }, [])
  const v0 = REPORTS[REPORTS.length - 1]
  const s = v0.summary
  const judged = s.accuracy.original?.n ?? 0

  return (
    <>
      <section className="hero">
        <p className="eyebrow">How it works</p>
        <h1>
          Two AIs, three rounds, and <em>a judge that has to show its working.</em>
        </h1>
        <p className="lede">
          One AI argues against you. A second AI, from a different company, judges you both. Here's what happens at
          each step, and how the judge is checked.
        </p>
      </section>

      <section className="how-block" aria-labelledby="flow-title">
        <h2 id="flow-title">A debate, step by step</h2>
        <ol className="flow">
          <li>
            <span className="step-n">01</span>
            <div>
              <h3>You pick a topic and a side</h3>
              <p>
                Write your own topic or pick one of 60. A quick check turns away topics that aren't debatable or that
                target people. Choose a friendly or a sharp opponent.
              </p>
            </div>
          </li>
          <li>
            <span className="step-n">02</span>
            <div>
              <h3>Three rounds: opening, rebuttal, closing</h3>
              <p>
                You type or speak each turn. The AI opponent replies to your actual points, streamed word by word as
                it writes. Turn order is enforced, so nobody speaks twice or out of turn.
              </p>
            </div>
          </li>
          <li>
            <span className="step-n">03</span>
            <div>
              <h3>A separate AI judges both sides</h3>
              <p>
                It scores argument strength, evidence, rebuttal and clarity from 1 to 10, quoting the exact lines
                behind each score, and picks a winner.
              </p>
            </div>
          </li>
          <li>
            <span className="step-n">04</span>
            <div>
              <h3>You see why, and can share it</h3>
              <p>
                Quoted lines are highlighted in the debate. Every debate gets a read-only share link and is listed
                under "Your debates" in your browser.
              </p>
            </div>
          </li>
        </ol>
      </section>

      <section className="how-block" aria-labelledby="ais-title">
        <h2 id="ais-title">The two AIs</h2>
        <div className="duo">
          <div className="duo-card pro">
            <p className="tag">Opponent</p>
            <h3>Argues against you</h3>
            <p>Ling 3.2 Flash (Ant). If it's busy, a backup model, ERNIE 5.5 Flash (Baidu), takes over.</p>
          </div>
          <div className="duo-card con">
            <p className="tag">Judge</p>
            <h3>Scores you both</h3>
            <p>
              Nemotron 3.5 Super (NVIDIA). A different company from the opponent, because AI judges tend to favour
              writing from their own model family.
            </p>
          </div>
        </div>
      </section>

      <section className="how-block" aria-labelledby="honest-title">
        <h2 id="honest-title">How the judge is kept honest</h2>
        <div className="checks">
          <div className="check">
            <h3>Quotes are checked by code</h3>
            <p>
              Every quote must appear, word for word, inside that side's own turn. Anything the judge makes up is
              removed before you see the scorecard.
            </p>
          </div>
          <div className="check">
            <h3>The judge is tested for bias</h3>
            <p>
              On debates where the stronger side is known in advance, the judge is re-run with the speaking order
              swapped, with the weaker side padded to twice the length, and with one side reworded by its own model
              family.
            </p>
          </div>
          <div className="check">
            <h3>Results are published</h3>
            <p>
              {judged > 0
                ? `So far ${s.accuracy.original.correct} of ${judged} test debates judged correctly, and ${s.order_swap_consistency.same} of ${s.order_swap_consistency.pairs} kept the same verdict with the order swapped. The run is still in progress.`
                : 'The test run is in progress.'}{' '}
              <Link to="/judge">See the judge report card →</Link>
            </p>
          </div>
        </div>
      </section>

      <section className="how-block" aria-labelledby="stack-title">
        <h2 id="stack-title">Built with</h2>
        <div className="stack">
          <div>
            <p className="tag">Frontend</p>
            <p>React, TypeScript, Vite</p>
          </div>
          <div>
            <p className="tag">Backend</p>
            <p>Python, FastAPI, SQLAlchemy</p>
          </div>
          <div>
            <p className="tag">Data</p>
            <p>Postgres (Neon)</p>
          </div>
          <div>
            <p className="tag">AI</p>
            <p>OpenRouter, structured JSON output, streaming</p>
          </div>
          <div>
            <p className="tag">Hosting</p>
            <p>Vercel</p>
          </div>
          <div>
            <p className="tag">Tests</p>
            <p>pytest, Vitest, Playwright</p>
          </div>
        </div>
        <p className="stack-foot">
          <a href={REPO_URL} target="_blank" rel="noreferrer" className="btn ghost">
            Read the code on GitHub
          </a>
        </p>
      </section>

      <section className="how-block" aria-labelledby="limits-title">
        <h2 id="limits-title">What it doesn't do</h2>
        <ul className="plain">
          <li>It doesn't fact-check. The judge scores how well a case is argued, not whether it's true.</li>
          <li>It runs on free AI models, so live debates are limited each day. Recorded debates always work.</li>
          <li>It stores debate text only. Your IP address is kept only as a one-way hash, for the daily limit.</li>
        </ul>
        <Link to="/" className="btn primary">
          Start a debate
        </Link>
      </section>
    </>
  )
}
