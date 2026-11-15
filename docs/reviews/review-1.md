# Review 1: foundations, the judge, the eval machinery, and the debate API

Covers steps 1–4, 6 and 7 (phases 0 and 2, and phase 1 as far as it can go before the eval data exists).
Commits: `git log --oneline main..feat/steelman`, plus `2c21e82` on `main`. Every decision and its reason is in `docs/decisions.md`.

## What exists now

| Part | Where | State |
|---|---|---|
| OpenRouter client | `backend/app/llm.py` | Done. Structured output with one repair, retries, streaming |
| Judge v0 | `backend/app/judge.py`, `quotes.py` | Done. Scores four criteria per side and drops quotes that aren't in the text |
| Eval machinery | `backend/evals/` | Done and tested. Data: 8 of 40 debates written; 1 debate judged in all conditions |
| Debate engine and topic filter | `backend/app/debate.py` | Done |
| API, database, limits | `backend/app/api.py`, `db.py`, `limits.py` | Done. One full real debate played through it |
| Frontend | `frontend/` | Template only (phase 3) |

Tests: 69 pass. The model calls are faked; the API tests use a real Postgres test database.

## What isn't done

- **Step 4's numbers and step 5 (judge v1).** The full eval needs about 225 calls at 35 a day, so about a week. Each day, from `backend/`:
  ```
  .venv/bin/python -m evals.generate
  .venv/bin/python -m evals.run --judge v0
  ```
- Nothing in the eval results means anything yet. One debate was judged, which proves only that the pipeline runs.

## Things that went differently from the plan

1. **Opponent model:** Ling 3.2 Flash, not Gemma, which was rate-limited upstream.
2. **The judge model reasons before answering.** It needs `reasoning effort=low` and 8,000 tokens, and takes 26–45 s per judgment.
3. **Two endpoints for a turn, not one:** saving the user's turn and streaming the AI's reply are separate calls.
4. **Results file** is one per judge version, not one per date.
5. **Linter:** oxlint on the frontend, as shipped by Vite's template.

## Open risks

- **Ling's upstream rate limit** interrupted four runs in one day. It's the main reliability risk for live mode. The API handles it (503, state kept, retry works), and showcase mode will cover visitors. A backup opponent model would reduce it further.
- **Judge v0 failed on a long debate:** with the weak side padded, the scorecard was invalid even after repair. A fix belongs in judge v1.
- **Eval labels mean "argues better", not "is true".** The writer invents evidence (see `docs/decisions.md`, eval section).
- **Not deterministic:** the same debate scored 32–19 and then 33–20. The evals measure this as the re-run noise floor.
- **`TRUST_PROXY` must be set correctly at deploy,** or the per-visitor limit is wrong.

## Questions for you

Role: you're interviewing the person who built this, and you have ten minutes.

1. Open `backend/app/judge.py`. Why does the judge have to quote the debaters, and what stops it making quotes up?
2. Why is the judge a different company's model from the opponent?
3. In `backend/evals/variants.py`, what are the three ways a side is weakened? Can you think of a weak argument that none of them covers?
4. The eval set is written by an AI. What's the biggest reason not to trust the accuracy number it produces, and what does step 10 do about it?
5. In `backend/app/api.py`, why are the debate id and the share slug two different values?
6. What happens if a visitor opens the same debate in two tabs and clicks "AI's turn" in both?
7. The daily limit counts a call before it's made. What does that cost, and why is it the safer choice?

Answer in your own words. Where an answer is wrong or thin, that's the part to read again or ask about.
