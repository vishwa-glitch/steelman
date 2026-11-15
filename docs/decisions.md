# Decisions

## Models (15 Nov 2026, step 2)

All free OpenRouter models. They're set in `backend/app/config.py`, and env vars override them. Smoke test: `python -m app.llm_smoke`, run 15 Nov.

| Role | Model | Maker | Smoke result |
|---|---|---|---|
| Judge | `nvidia/nemotron-3.5-super-vl:free` | NVIDIA | 8 of 8 valid structured JSON, 0 repairs, median 3.2 s |
| Backup judge | `baidu/ernie-5.5-flash-preview:free` | Baidu | 5 of 5 valid, 0 repairs, median 2.0 s |
| Opponent | `inclusionai/ling-3.2-flash:free` | Ant (inclusionAI) | 3 of 3 replies, median 6.1 s |

- **Why these:**
  - The judge and the opponent come from different makers. Judges tend to favour text written by their own model family, and step 4 measures this.
  - The judge needs strict JSON-schema output, which both judge models support.
- **Rejected:**
  - `google/gemma-4-31b-it:free`, the plan's first opponent choice. It returned 429 "temporarily rate-limited upstream" from Google AI Studio, which serves it for free. That limit is Google's shared free pool, not this account. It can be tried again later.
  - `dots-studio/dots-3-note-preview:free` returned an empty message on 2 of 3 calls with `max_tokens=200`. Most likely it's a reasoning model whose thinking used up the token budget. This was not confirmed.
- **What the smoke test does not show:** judging quality. Its one test debate was easy on purpose (a strong argument with evidence against "people like cars"). Judging quality is what the evals in steps 4–5 measure.
- **Free cap:** 50 requests a day for the whole account. The usage counter (`GET /api/v1/key`) can't be relied on minute by minute:
  - It showed `used: 13` after 13 successful calls and 2 rejected (429) ones.
  - It then showed `used: 14` after 6 more calls that all returned HTTP 200.
  - SUSPICION (unverified): it lags, or counts only some calls. To check: read it again tomorrow before the first call. Until then, the eval runner counts its own calls rather than trusting this number.

## Judge v0 (16 Nov 2026, step 3)

- **Rubric:** four criteria, argument_strength, evidence, rebuttal and clarity, each scored 1–10 per side.
  - Every score must come with 1–3 exact quotes from that side and a one-sentence reason.
  - The schema is enforced by pydantic: scores must be 1–10, each criterion appears exactly once per side, and pro and con each appear exactly once.
- **Quote check (`app/quotes.py`):**
  - A quote must appear in that side's own words, so quoting the opponent doesn't count.
  - Matching ignores case, whitespace, curly vs straight quotes, dash styles, and wrapping quote marks or ellipses. A paraphrase or an edited quote fails.
  - Quotes shorter than 8 characters fail, because a word or two proves nothing.
  - In v0, failing quotes are dropped and counted, not repaired. The evals will show how often this happens.
- **Reasoning setting:** the judge model, Nemotron 3.5 Super, reasons before it answers. Each setting below was tried live on `evals/samples/one.json`:

  | Setting | Result |
  |---|---|
  | `max_tokens=2500` | All 2,500 tokens went to reasoning, `finish_reason=length`, empty answer. The client now raises a clear `OutOfTokens` error for this. |
  | `reasoning={"enabled": false}` | The answer overran and was cut off mid-JSON. The repair attempt failed the same way. |
  | `reasoning={"effort": "low"}`, `max_tokens=8000` | Valid scorecard. 32 s on the first run and 45 s on the second, 0 quotes dropped. **Chosen.** |

  The smoke test in step 2 passed only because its prompt was tiny.
- **Not deterministic:** at temperature 0, two runs on the same debate gave PRO 32 / CON 19 and then PRO 33 / CON 20. The winner was the same both times.
  - So the evals must treat a single judgment as noisy.
  - Measuring how often a verdict changes on a plain re-run, before testing order swaps, tells us how much of any later "flip" is just noise.
- **Speed:** about 30–45 s per judgment. That's fine for offline evals. In the app, the judge runs once after the closing round, behind a "the judge is deliberating" screen.

## Eval set and runner (16 Nov 2026, step 4)

**How the labelled debates are made** (`evals/generate.py`, `evals/variants.py`):
- 40 everyday topics, chosen to avoid politics and religion (`evals/topics.json`).
- For each topic, the writer model writes one whole debate in which one side is weakened in exactly one named way:
  - no specific evidence
  - a central logical fallacy
  - ignores the other side's main point
- The side and the type are fixed in advance by a seeded random choice, so re-runs ask the same questions. The other side is the label.
- The writer is told to keep both sides fluent and about the same length. The weak-to-strong length ratio is measured, so length can't give the answer away; the first debate came out at 1.03.
- **Limitation:** the writer invents "real-sounding" evidence. In debate d00, CON describes the 2006 Cooper review as finding a positive effect "even in early grades". The hand-written sample states Cooper's actual primary-school finding, which is almost no link. So the label means "uses specific evidence and engages", not "is factually true". A judge that fact-checks could disagree with the label for a defensible reason.
- **Writer settings:** reasoning is off. With `reasoning={"effort": "low"}`, Ling spent all 4,000 tokens thinking and returned nothing. Writing doesn't need thinking.

**What the runner measures** (`evals/run.py`, `evals/metrics.py`):

| Condition | Debates | What it tests |
|---|---|---|
| original | all | Accuracy: does the judge pick the labelled side? |
| swapped | all | CON speaks first in every round, same words. Does the winner change? |
| rerun | first 15 | The same debate judged again. This is the noise floor: some "flips" happen with no change at all (see the judge v0 section). |
| padded_weak | first 15 | The weak side made about twice as long, with nothing new. Does length buy points? |
| selfpref_strong, selfpref_weak | first 15 | One side reworded by the judge's own model family. Does the judge favour its own family's writing? Rewording can also change quality, so this is a signal, not proof. |

- Conditions run in that order, most important first, so a partial day still gives the key numbers.
- **Free-cap handling** (`evals/cached_llm.py`):
  - Every answer is cached on disk under a hash of the model, prompt and settings.
  - Calls are counted against a daily allowance (default 35, by UTC day). This is our own count, because OpenRouter's counter didn't add up (see Models above).
  - On a cap or rate limit the runner stops and saves partial results; running it again continues from where it stopped.
  - Failures are cached too, so a broken item doesn't use up the allowance every day. `--retry-failed` overrides that.
- **Free models can be busy upstream, not just capped:**
  - On 16 Nov, Ling returned "temporarily rate-limited upstream" from Ant Digital. That's the same kind of failure Gemma had on 15 Nov.
  - So the stop message now says to wait a few minutes in that case, rather than a day.
  - `--writer` lets the generator use another model if one stays busy.
- **Results file:** `evals/results/<judge>.json` and `.md`, overwritten as the run fills in, with git keeping the history. The plan said `<date>-<judge>.json`, but a run spans several days, so one file per judge version is clearer.

## Debate engine, opponent and topic filter (16 Nov 2026, step 6)

- **Order of play:** PRO then CON in each of opening, rebuttal and closing, six turns in all. If the user picks CON, the AI speaks first.
- **State machine (`app/debate.py`):** the only legal move is the next turn in that fixed order. Speaking out of turn, twice in a row, or after the end raises an error, and a rejected turn doesn't advance the debate.
- **Turn limits:** a user turn must be 20–1,500 characters. An AI turn is cut at 1,500. A motion must be 10–200 characters.
- **Opponent:** two difficulty levels, friendly and sharp. It's told not to invent statistics, and that the transcript is the other debater's speech, never instructions. Reasoning is off, as for the eval writer.
- **Topic filter, two layers:**
  1. A word list blocks obvious cases with no model call (religion, caste, self-harm, hate terms, abortion).
  2. A model check (ERNIE 5.5 Flash) classifies the rest.
- **Topic schema has one field, on purpose.** The first version had `allowed` plus `category`. For "Remote work is better for companies than office work" the model returned `{"allowed": true, "category": "sexual"}`, and the motion was wrongly blocked. Two fields can contradict each other. With a single `verdict` field, a live check gave: remote work allowed, "the ruling party deserves to win the next election" blocked, and an "ignore your instructions" motion blocked. That's three motions, so it shows the filter works, not how accurate it is.
- **Live check:** `python -m app.play` ran a full debate (user PRO on remote work). The opponent answered the user's open-source and scheduled-mentoring points directly, and judge v0 returned a scorecard in 26 s with 0 quotes dropped.
- **Seen in that run, not yet acted on:** the opponent cited Bell Labs' corridor and IBM's return to the office. Those are well-known examples, but nothing checks the AI's facts. The site should say so.
