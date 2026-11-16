"""Run the judge over the labelled debates and their variants: python -m evals.run --judge v0

Conditions run in priority order (most important first), so a partial day still yields the key numbers:
  original, swapped (all debates); rerun, padded_weak, selfpref_strong, selfpref_weak (first --subset debates).
Safe to re-run: cached answers cost nothing; it stops when today's allowance is used and continues next time.
Writes evals/results/<judge>.json (every judgment + summary) and evals/results/<judge>.md.
"""

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

from app import judge as judge_v0
from app.config import load_settings
from app.llm import LLMClient, LLMError, RateLimited, TransientError
from evals.cached_llm import DEFAULT_ALLOWANCE, NOT_FINISHED_HINT, Budget, BudgetExhausted, CachedLLM
from evals.metrics import summarise
from evals.variants import (
    EvalDebate,
    ThreeTurns,
    padding_messages,
    paraphrase_messages,
    replace_side,
    swap_order,
)

HERE = Path(__file__).parent
JUDGES = {"v0": judge_v0.judge}
PLANNED_DEBATES = len(json.loads((HERE / "topics.json").read_text()))
FULL = ("original", "swapped")
SUBSET = ("rerun", "padded_weak", "selfpref_strong", "selfpref_weak")
REWRITE_SETTINGS = dict(temperature=0.3, max_tokens=4000, reasoning={"effort": "low"})


def build(d: EvalDebate, condition: str, cached: CachedLLM, writer_model: str, judge_model: str):
    """The transcript to judge for this condition (may call a model, through the cache)."""
    t = d.transcript
    strong = d.label
    if condition in ("original", "rerun"):
        return t
    if condition == "swapped":
        return swap_order(t)
    if condition == "padded_weak":
        r = cached.structured(padding_messages(t, d.weak_side), d.writer_model, ThreeTurns, **REWRITE_SETTINGS)
        return replace_side(t, d.weak_side, r.data)  # type: ignore[arg-type]
    if condition in ("selfpref_strong", "selfpref_weak"):
        side = strong if condition == "selfpref_strong" else d.weak_side
        r = cached.structured(paraphrase_messages(t, side), judge_model, ThreeTurns, **REWRITE_SETTINGS)
        return replace_side(t, side, r.data)  # type: ignore[arg-type]
    raise ValueError(condition)


def record(d: EvalDebate, condition: str, res=None, error: str | None = None) -> dict:
    base = {"id": d.id, "condition": condition, "label": d.label, "weakness": d.weakness}
    if res is None:
        return {
            **base,
            "ok": False,
            "error": error,
            "winner": None,
            "correct": False,
            "strong_total": None,
            "weak_total": None,
            "kept_quotes": 0,
            "dropped_quotes": 0,
        }
    card = res.scorecard
    return {
        **base,
        "ok": True,
        "error": None,
        "winner": card.winner,
        "correct": card.winner == d.label,
        "strong_total": card.total(d.label),
        "weak_total": card.total(d.weak_side),
        "kept_quotes": res.kept_quotes,
        "dropped_quotes": len(res.dropped_quotes),
        "model": res.model,
        "latency_s": round(res.latency_s, 1),
    }


class RewriteFailed(Exception):
    """Building a variant (padding, rewording) failed. That says nothing about the judge, so it is recorded
    separately and left out of the judge's valid-output and accuracy numbers."""


def run(debates, judge_fn, cached, writer_model, judge_model, subset_n) -> tuple[list[dict], dict, str | None]:
    plan = [(c, debates) for c in FULL] + [(c, debates[:subset_n]) for c in SUBSET]
    planned = {c: len(ds) for c, ds in plan}
    records, stopped = [], None
    for condition, ds in plan:
        for d in ds:
            client = cached.with_tag("rerun-1") if condition == "rerun" else cached
            try:
                try:
                    t = build(d, condition, cached, writer_model, judge_model)
                except LLMError as e:
                    raise RewriteFailed(f"{type(e).__name__}: {str(e)[:200]}") from e
                records.append(record(d, condition, res=judge_fn(t, client, judge_model)))
            except (BudgetExhausted, RateLimited, TransientError) as e:
                if stopped is None:
                    stopped = f"{type(e).__name__}: {str(e)[:300]}"
                    cached.cache_only = True  # report everything already cached, spend nothing more
            except RewriteFailed as e:
                records.append({**record(d, condition, error=str(e)), "stage": "rewrite"})
            except LLMError as e:
                records.append(record(d, condition, error=f"{type(e).__name__}: {str(e)[:200]}"))
        print(f"  {condition}: done", flush=True)
    return records, planned, stopped


def status_line(meta: dict) -> str:
    if meta["complete"]:
        return "Complete."
    why = meta["stopped"] or "more debates still to generate"
    return f"Incomplete: {meta['debates']} of {meta['planned_debates']} debates written; {why}"


def to_markdown(judge_name: str, meta: dict, s: dict) -> str:
    acc = s["accuracy"]
    lines = [
        f"# Judge {judge_name}: eval results",
        "",
        f"Judge model `{meta['judge_model']}`, debates written by `{meta['writer_model']}`. "
        f"Updated {meta['updated']}. {status_line(meta)}",
        "",
        "| Condition | Progress | Valid output | Accuracy |",
        "|---|---|---|---|",
    ]
    for c, prog in s["progress"].items():
        v, a = s["valid_output"][c], acc[c]
        lines.append(f"| {c} | {prog} | {v['valid']}/{v['n']} | {a['correct']}/{a['n']} ({a['rate']}) |")
    o, r, lb, sp, q = (
        s["order_swap_consistency"],
        s["rerun_consistency"],
        s["length_bias"],
        s["self_preference"],
        s["quotes"],
    )
    lines += [
        "",
        f"- Order swap: same winner in {o['same']}/{o['pairs']} ({o['rate']}), {o['flips']} flips",
        f"- Plain re-run: same winner in {r['same']}/{r['pairs']} ({r['rate']}), {r['flips']} flips "
        "(the noise floor for the order-swap number)",
        f"- Length bias: weak side gains {lb['mean_weak_gain']} points on average when padded; "
        f"{lb['flips_to_weak']}/{lb['pairs']} verdicts flipped to it",
        f"- Self-preference (n={sp['n']}): strong-minus-weak margin {sp['margin_original']} originally, "
        f"{sp['margin_strong_reworded_by_judge_family']} when the strong side is reworded by the judge's "
        f"family, {sp['margin_weak_reworded_by_judge_family']} when the weak side is",
        f"- Quotes: {q['dropped']} of {q['kept'] + q['dropped']} dropped as not found ({q['drop_rate']})",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--judge", default="v0", choices=sorted(JUDGES))
    p.add_argument("--subset", type=int, default=15)
    p.add_argument("--allowance", type=int, default=DEFAULT_ALLOWANCE)
    p.add_argument("--retry-failed", action="store_true")
    args = p.parse_args()
    s = load_settings()
    debates = [EvalDebate.model_validate_json(x) for x in (HERE / "data/debates.jsonl").read_text().splitlines() if x]
    budget = Budget(HERE / "cache/_budget.json", args.allowance)
    cached = CachedLLM(LLMClient(s), HERE / "cache", budget, retry_failed=args.retry_failed)
    records, planned, stopped = run(debates, JUDGES[args.judge], cached, s.opponent_model, s.judge_model, args.subset)
    summary = summarise(records, planned)
    meta = {
        "judge": args.judge,
        "judge_model": s.judge_model,
        "writer_model": ", ".join(sorted({d.writer_model for d in debates})),
        "debates": len(debates),
        "subset": args.subset,
        "planned_debates": PLANNED_DEBATES,
        "complete": stopped is None and len(debates) == PLANNED_DEBATES,
        "stopped": stopped,
        "updated": dt.datetime.now(dt.UTC).isoformat(timespec="minutes"),
    }
    out = HERE / "results"
    out.mkdir(exist_ok=True)
    (out / f"{args.judge}.json").write_text(
        json.dumps({"meta": meta, "summary": summary, "records": records}, indent=1)
    )
    (out / f"{args.judge}.md").write_text(to_markdown(args.judge, meta, summary))
    print(to_markdown(args.judge, meta, summary))
    print(f"new calls: {cached.calls}, cache hits: {cached.hits}, today's allowance left: {budget.remaining()}")
    if stopped:
        print(NOT_FINISHED_HINT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
