# Steelman: build plan (15 Nov 2026)

Risk tier: HIGH. Steelman saves user debates to a database, serves public share links, and spends money on AI calls for every visitor. Under the rules in `~/.claude/CLAUDE.md`, storing data makes it HIGH. If saving and share links were dropped, it would be MED.

## What it is

Steelman is a debate app.
1. You pick a topic and a side.
2. An AI argues the other side over three rounds: opening, rebuttal and closing.
3. A separate AI judge scores both sides against a rubric, quoting the lines behind each score.
4. A public "judge report card" page shows how fair the judge is, measured on labelled debates. This page is the difference from the many existing debate apps: none of the ones found publish how accurate their judge is (web search, 15 Nov).

**Why it exists:** it's the web and AI project for the portfolio's Shipped section and the résumé. It shows React + TypeScript, a Python backend, structured AI output, and evals with a real before/after number. The research behind this choice is in `research/ai-engineer-roles-2026-11-14.md`.

## Decisions already made (don't re-litigate)

- **Stack (approach B):**
  - Frontend: React + TypeScript (Vite), hosted on Vercel.
  - Backend: Python FastAPI.
  - Database: Postgres.
  - Replies stream to the screen as they're written (server-sent events).
- **Name:** Steelman.
- **AI provider:** OpenRouter. One key reaches several companies' models, so the judge and the opponent can come from different model families. VERIFIED 15 Nov from the OpenRouter `/api/v1/models` endpoint: structured JSON output is supported by many models, including:
  - Anthropic: `claude-haiku-5.5` at $0.10 / $0.50 per million tokens in / out.
  - DeepSeek: `deepseek-v4.1-flash`.
  - Google: `gemini-3.1-flash-lite`.
  The final model choice is made in step 2.
- **Build order:** the judge and its evals come before the debate screen, so the report-card number exists early.
- **No accounts in v1.** Logging in would be extra HIGH-tier work and isn't needed to show the skills.
- **Audience (decided 15 Nov):** almost nobody except people who click through from the résumé. The goal is a site that always works for them, plus a strong eval story. Traffic isn't the goal.
- **Free models only, with slow evals (decided 15 Nov):**
  - Models: OpenRouter `:free`. The opponent starts as `google/gemma-4-31b-it:free` and the judge as `nvidia/nemotron-3.5-super-vl:free`, with `baidu/ernie-5.5-flash-preview:free` as the backup judge. All are confirmed in step 2.
  - Free cap: 20 requests a minute and 50 a day for the whole account (VERIFIED, OpenRouter limits page, 15 Nov). It counts against the account, not the key.
  - So the eval runner must stop safely and resume the next day. It keeps a daily allowance (default 35 calls), leaving room for testing and live debates.
- **Showcase mode (decided 15 Nov):**
  - Three curated debates are run in advance, saved, and replayed on the home page with their scorecards, using no AI calls.
  - The report card also reads saved results.
  - If live mode can't run (cap reached, model gone), the site says so and points to the recorded debates instead of showing an error.
- **AgentRouter is not used** for the judge or the evals, because nobody can verify which model it actually serves.

## Where things live

- **New repo:** `~/Developer/Personal/steelman/`. It doesn't exist yet; step 1 creates it.
  - `backend/` holds FastAPI. The `app/` package contains the AI client, judge, debate engine and API.
  - `backend/evals/` holds the labelled datasets, the runner and the results.
  - `frontend/` holds Vite + React + TypeScript.
  - `docs/PLAN.md` is a copy of this file.
- **Local tools** (VERIFIED, 15 Nov):
  - Available: Node 26.5, npm 11.17, Python 3.14 at `/opt/homebrew/bin/python3.14`, Docker.
  - Not installed: `uv` and `psql`.
- **Git:** step 1 makes the initial commit on `main`; all later work goes on `feat/steelman`. One local commit per step, after its checkpoint passes. Never push unless asked. No AI attribution in commits.

## Steps

Each checkpoint is run by Claude and its output shown. Only the items marked "you" need you.

1. **Scaffold the repo.**
   - Create the folders and `git init`; copy this plan to `docs/PLAN.md`.
   - Backend: a venv on Python 3.14 with FastAPI, pydantic, httpx, pytest and ruff, plus a `GET /health` endpoint.
   - Frontend: Vite with React and TypeScript, plus ESLint.
   - Local Postgres runs in Docker (`docker compose`).
   - SUSPICION (unverified): every library has Python 3.14 wheels. If one doesn't, fall back to 3.13 through Homebrew.
   - *Checkpoint:* `curl localhost:8000/health` returns 200; `pytest`, `ruff check`, `npm run build` and `tsc --noEmit` all pass; the frontend page loads.

2. **AI client and model choice.**
   - `app/llm.py` calls OpenRouter with:
     - a JSON schema for structured output
     - a timeout
     - retries
     - one repair attempt when the JSON comes back invalid
   - Pick the opponent and judge models from different families, confirmed in `/models`, and record why in `docs/decisions.md`.
   - *You:* create an OpenRouter key with a credit limit and put it in `backend/.env`, which is gitignored. SUSPICION (unverified): OpenRouter supports per-key credit limits. Check this when creating the key.
   - *Checkpoint:* `python -m app.llm_smoke` returns valid JSON from both models. Unit tests with fake HTTP responses cover the timeout, retry and repair paths.

3. **Judge v0.**
   - `app/judge.py` takes a transcript and returns, for each side and each criterion:
     - a score
     - the exact lines quoted as evidence
     - a final verdict
   - The criteria are argument strength, evidence, answering the opponent's points, and clarity.
   - Plain code then checks that every quote actually appears in the transcript, and rejects any made-up quote.
   - *Checkpoint:* `python -m app.judge evals/samples/one.json` prints a scorecard. Tests cover the quote checker (a real quote passes, an edited one fails) and schema validation.

4. **Eval set and runner. This is the core step.**
   - **Generate the labelled debates:**
     - Take about 40 topics and write a strong case for each side.
     - Weaken one side on purpose: remove its evidence, add a named fallacy, or make it ignore the opponent's main point.
     - The stronger side is then known. Save everything as JSONL, recording the model and seed used.
   - **The runner measures:**
     - Accuracy: how often the judge picks the stronger side.
     - Order-swap consistency: whether the verdict stays the same when the sides swap speaking order.
     - Length bias: whether padding the weaker side with filler raises its score.
     - Self-preference: the judge's accuracy when it judges text written by its own model family, against text from another family.
   - Results are saved as `evals/results/<date>-<judge>.json` plus a Markdown summary.
   - SUSPICION (unverified): the weakened cases may be too easy to spot, which would inflate accuracy. Step 10 tests this against your hand labels.
   - Running on the free cap:
     - Each model answer is saved to disk under a key built from the prompt, model and settings, so a repeated run never pays twice for the same call.
     - The runner stops at the daily allowance, or when it gets a 429 error, and honours the `Retry-After` header. Running it again the next day continues where it stopped.
     - Expect a full run to take several days.
   - *Checkpoint:* `python -m evals.run --judge v0` prints the four numbers and writes the results file. Tests check:
     - the metric maths on a tiny fixed example
     - that the runner resumes after a simulated stop
     - that saved answers are reused instead of calling the model again

5. **Judge v1: fix what the evals found.**
   - Candidate fixes:
     - Judge both speaking orders and combine the results.
     - Score each criterion before giving the verdict.
     - Require quotes.
     - Use a different model family from the opponent.
   - Only the fixes the numbers support are kept.
   - *Checkpoint:* re-run the evals and print a v0 vs v1 table. This is the résumé number.
   - A `/walkthrough` of the diff is optional here, if you want one.

6. **Opponent and debate engine.**
   - `app/debate.py` is a round-by-round state machine: opening → rebuttal → closing. Rounds can't be skipped or repeated.
   - The opponent has difficulty levels (friendly, sharp) and must answer your points.
   - A topic filter blocks disallowed categories. It's a word list plus a model check.
   - *Checkpoint:* `python -m app.play` runs a full debate in the terminal, ending in the judge's scorecard. Tests cover the round order, blocked topics and the turn length limit.

7. **API, database and cost protection.**
   - Endpoints:
     - `POST /debates`
     - `POST /debates/{id}/turns`, which streams the opponent's reply
     - `POST /debates/{id}/judge`
     - `GET /share/{slug}`
   - Storage is Postgres through SQLAlchemy, with Alembic for migrations.
   - Only debate text is stored, no personal data. Share slugs are long and random.
   - Usage limits:
     - a light per-IP limit on debates per day
     - a global daily limit on AI calls that stays under the free cap; when it's reached, the API returns 503 with a "live mode is resting" message
     - a maximum length per turn
   - A `GET /status` endpoint says whether live mode can run.
   - *Checkpoint:* pytest API tests against a test database cover create → turns → judge → share, a guessed slug returning 404, the limit returning 429, and the daily limit returning 503. `curl -N` shows the reply streaming.

8. **Frontend: the debate flow.**
   - Screens:
     - Home: pick a topic and a side.
     - Debate: two columns, with the AI's reply appearing live.
     - Scorecard: the quoted lines highlighted.
     - Share page.
   - The look matches the portfolio: Fraunces headlines, IBM Plex body text, light and dark modes. It also works at phone width.
   - Showcase mode: the home page replays three saved debates with their scorecards, and needs no AI calls. When `/status` says live mode is off, the site shows a "Live mode is resting, watch a recorded debate" notice instead of an error.
   - *Checkpoint:*
     - `npm run build` and `tsc` pass.
     - A full debate works against the local backend.
     - With the backend stopped, the showcase debates still play, and the live button shows the resting message.
     - Headless-Chrome screenshots at desktop and phone width are shown to you.

9. **Frontend: the judge report card page.**
   - It shows the v0 → v1 numbers with 2–3 charts, read from the eval results JSON.
   - It also has a plain explanation of how the judge is tested, and links to the eval code.
   - *Checkpoint:* the page builds and its numbers match the latest results file exactly. A small test compares them. Screenshots are shown.

10. **Hand-labelled check.**
    - *You:* play 10–15 real debates and record who you think won.
    - The runner adds this as a second set, and the report card shows the judge's agreement with you next to the synthetic accuracy.
    - *Checkpoint:* `python -m evals.run --set human` prints the agreement figure; the report card shows both numbers.

11. **Deploy.**
    - The frontend goes on Vercel.
    - The backend host is chosen at this step. SUSPICION (unverified): free tiers on Render, Railway or Fly may put the app to sleep. To check: their current terms.
    - The database is hosted Postgres, Neon or Supabase. SUSPICION (unverified): their free tiers are enough. To check: their current limits.
    - CORS is limited to the frontend's domain; secrets go in the hosts' environment settings.
    - *Checkpoint:* the production `/health` returns 200; a full real debate works in production; the per-IP limit returns 429 in production; the share link opens in a private window.

12. **README and write-up.**
    - The README covers the problem, the judge-bias numbers, a short architecture diagram, how to run it, and how to run the evals.
    - It also has the résumé line, with the real numbers filled in.
    - *Checkpoint:* the README renders on GitHub and every link works.

13. **HIGH-tier verification.**
    - A fresh-session review of the whole diff.
    - `/evidence` on every claim: the judge numbers, the cost limits and the share-link privacy.
    - A full `/breaklist`.
    - Core-logic tests confirmed present and passing: the quote checker, the round state machine, the rate and spend limits, and the eval metric maths.

## Follow-up in another repo (after Steelman is live)

- **Portfolio** (`~/Developer/Personal/portfolio`, branch `feat/steelman`), risk tier LOW (copy only):
  - Add Steelman to `shipped` in `src/data/site.ts` (currently line 59).
  - *Checkpoint:* `npm test`, `npx astro check` and `npm run build` pass; screenshots are shown.
- **Résumé:** add the project line to `resume/resume.yaml` and re-render the PDF following `resume/NOTES.md`. This folder is not a git repo.

## Open items for you

- Create an OpenRouter key (step 2). In OpenRouter's privacy settings, turn off providers that may train on your data for free models, then confirm in step 2 which models still work.
- Play and label 10–15 debates (step 10).
- Decide how much time per week this gets. That sets the target date.
