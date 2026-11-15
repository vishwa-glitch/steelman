# Review 2: the frontend (phase 3, steps 8 and 9)

Commits: `38270b2` (debate flow, showcase mode) and the one after it (judge report card). Reasons are in `docs/decisions.md`, in the last two sections. Screenshots are in `docs/screenshots/`.

## What exists now

| Page | Path | What to look at |
|---|---|---|
| Home | `/` | Start form, the "live mode" notice, recorded debates |
| Live debate | `/debate/:id` | Two columns per round, the AI's reply streaming in, then the verdict |
| Shared debate | `/d/:slug` | Read-only |
| Recorded debate | `/recorded/museums` | Works with the backend off |
| Judge report card | `/judge` | Reads the real eval summary; says the run is in progress |

## To try it yourself (no AI calls spent)

```
cd ~/Developer/Personal/steelman && docker compose up -d
cd backend && FAKE_LLM=1 .venv/bin/uvicorn app.main:app --port 8000
# in a second terminal
cd ~/Developer/Personal/steelman/frontend && npm run dev
```
Open http://localhost:5173. With `FAKE_LLM=1` the opponent and the judge are canned. Leave it off to use the real models, which spends the daily allowance.

## Checks run

- Frontend: lint, type-check, 8 unit tests, production build.
- Browser, with a fake model: 14 of 14 checks at desktop and phone width (full debate, highlighting, verdict, share page read-only, reload keeps state, no sideways scroll, no console errors).
- Browser, backend stopped: 5 of 5 (resting notice, start disabled, recorded debate plays, clear message on a share link).
- Report card: renders in light, dark and phone width.

## Not done or not checked

- **Only one recorded debate exists.** The plan says three. Two more need recording with real models.
- **No full debate has been played in the browser with the real models.** The real models were used through the API with `curl` (review 1), and the browser flow was tested with the fake model. The two halves are each tested, but not together.
- **The report card shows one debate's worth of data.** It will fill in as the evals run; `npm run sync-evals` updates it.
- **Wording:** the judge's summary says PRO and CON; the screen says For and Against.
- Dark mode was screenshotted only for the report card. Screen readers were not tested.

## Questions for you

Role: you're a hiring engineer at a 20-person startup, and you've clicked through from a résumé with two minutes to spare.

1. Open `docs/screenshots/home-desktop.png`. In five seconds, what does this site do? Is anything on the page unclear?
2. Open `recorded.png`. Does the highlighted text make it obvious what the judge based its scores on?
3. Open `judge-desktop.png`. Would this page make you trust the judge more, or does it read as filler? What would you want to see first?
4. On `scorecard-phone.png`, is anything too long or too cramped?
5. Is "Steelman" explained anywhere it needs to be? Would you know what the word means?
6. What's the first thing you'd click, and what would make you close the tab?

Tell me what you'd change. Design is the part where your taste should override mine.
