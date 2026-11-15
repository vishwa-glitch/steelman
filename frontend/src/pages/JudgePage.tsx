import type { EvalReport } from '../data/evals'
import { REPORTS } from '../data/evals'

const CONDITIONS: Record<string, string> = {
  original: 'As written',
  swapped: 'Speaking order swapped',
  rerun: 'Judged a second time',
  padded_weak: 'Weaker side padded to twice the length',
  selfpref_strong: "Stronger side reworded by the judge's model family",
  selfpref_weak: "Weaker side reworded by the judge's model family",
}
const MIN_N = 10 // below this, a percentage would overstate what the data shows

function Tile({ label, k, n, note }: { label: string; k: number; n: number; note: string }) {
  return (
    <div className="tile">
      <p className="tile-label">{label}</p>
      <p className="tile-value">
        {n === 0 ? 'No data yet' : n >= MIN_N ? `${Math.round((100 * k) / n)}%` : `${k} of ${n}`}
      </p>
      <p className="tile-note">
        {n >= MIN_N ? `${k} of ${n}. ` : ''}
        {note}
      </p>
    </div>
  )
}

function Report({ report }: { report: EvalReport }) {
  const { meta, summary: s } = report
  const judged = s.accuracy.original?.n ?? 0
  const quotes = s.quotes.kept + s.quotes.dropped
  const sp = s.self_preference
  return (
    <section className="report">
      <h2>Judge {meta.judge}</h2>
      <p className="mute">
        Judge model {meta.judge_model}. Test debates written by {meta.writer_model}. Updated{' '}
        {meta.updated.slice(0, 10)}.
      </p>
      {(!meta.complete || judged < MIN_N) && (
        <p className="notice" role="status">
          This run is still in progress: {judged} of 40 planned debates have been judged. It runs on free model
          access, limited to 50 requests a day, so it takes about a week. Nothing below is a result yet.
        </p>
      )}
      <div className="tiles">
        <Tile label="Picks the stronger side" k={s.accuracy.original?.correct ?? 0} n={judged} note="On debates where one side was weakened on purpose." />
        <Tile label="Same verdict when the order is swapped" k={s.order_swap_consistency.same} n={s.order_swap_consistency.pairs} note="Same words, the other side speaks first." />
        <Tile label="Same verdict when asked twice" k={s.rerun_consistency.same} n={s.rerun_consistency.pairs} note="No change at all. This is the noise floor for the tile before it." />
        <Tile label="Quotes that were real" k={s.quotes.kept} n={quotes} note="Checked by code against the transcript." />
      </div>

      <h3>By test condition</h3>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th scope="col">Condition</th>
              <th scope="col">Judged</th>
              <th scope="col">Valid scorecard</th>
              <th scope="col">Picked the stronger side</th>
            </tr>
          </thead>
          <tbody>
            {Object.keys(s.progress).map((c) => {
              const acc = s.accuracy[c]
              const valid = s.valid_output[c]
              return (
                <tr key={c}>
                  <th scope="row">{CONDITIONS[c] ?? c}</th>
                  <td>{s.progress[c].replace('/', ' of ')}</td>
                  <td>{valid.n ? `${valid.valid} of ${valid.n}` : 'None yet'}</td>
                  <td>
                    {acc.n ? (
                      <span className="meter" title={`${acc.correct} of ${acc.n}`}>
                        <span className="meter-track" aria-hidden="true">
                          <span style={{ width: `${(100 * acc.correct) / acc.n}%` }} />
                        </span>
                        {acc.correct} of {acc.n}
                      </span>
                    ) : (
                      'None yet'
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <h3>Bias checks</h3>
      <ul className="plain">
        <li>
          <strong>Length.</strong>{' '}
          {s.length_bias.pairs
            ? `When the weaker side was padded, its score changed by ${s.length_bias.mean_weak_gain} points on average, and ${s.length_bias.flips_to_weak} of ${s.length_bias.pairs} verdicts flipped to it.`
            : 'No padded debates have been judged validly yet.'}
        </li>
        <li>
          <strong>Its own model family's writing.</strong>{' '}
          {sp.n
            ? `Across ${sp.n} debate${sp.n === 1 ? '' : 's'}, the stronger side led by ${sp.margin_original} points as written, ${sp.margin_strong_reworded_by_judge_family} when the stronger side was reworded by the judge's model family, and ${sp.margin_weak_reworded_by_judge_family} when the weaker side was. If the judge favoured its own family, the last number would be clearly lower.`
            : 'No reworded debates have been judged yet.'}
        </li>
      </ul>
    </section>
  )
}

export function JudgePage() {
  return (
    <>
      <section className="hero">
        <p className="eyebrow">Judge report card</p>
        <h1>How fair is the judge? Measured, not assumed.</h1>
        <p className="lede">
          AI judges are known to favour the first speaker, the longer answer and their own model's writing. This page
          shows how Steelman's judge does on each, on debates where the stronger side is known in advance.
        </p>
      </section>

      {REPORTS.map((r) => (
        <Report key={r.meta.judge} report={r} />
      ))}

      <section className="report">
        <h2>How the test works</h2>
        <ol className="plain">
          <li>An AI writes 40 debates on everyday motions. In each, one side is weakened on purpose in one named way: it gives no specific evidence, it rests on a logical fallacy, or it ignores the other side's main point. Both sides are kept about the same length.</li>
          <li>The judge scores each debate. Picking the side that was not weakened counts as correct.</li>
          <li>Each debate is judged again with the speaking order swapped. A fair judge gives the same verdict.</li>
          <li>Some debates are judged a second time unchanged, to measure how much the verdict moves by chance.</li>
          <li>Some are judged with the weaker side padded to twice the length, and some with one side reworded by the judge's own model family.</li>
        </ol>
        <h3>What this does not show</h3>
        <ul className="plain">
          <li>The test debates are written by an AI, so "stronger" means better argued, not true. The writer invents plausible evidence.</li>
          <li>Weakened arguments may be easier to spot than real ones. A second check, against debates labelled by a person, is planned.</li>
          <li>Forty debates is a small sample. Differences of a few debates are within noise.</li>
        </ul>
      </section>
    </>
  )
}
