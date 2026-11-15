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
