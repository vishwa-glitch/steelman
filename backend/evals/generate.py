"""Build the labelled eval debates: python -m evals.generate [--limit N] [--allowance N]

Writes evals/data/debates.jsonl. Safe to re-run: finished debates come from the cache and cost nothing,
and it stops cleanly when today's allowance is used.
"""

import argparse
import json
import random
import sys
from pathlib import Path

from app.config import load_settings
from app.llm import LLMClient, LLMError, RateLimited, TransientError
from app.transcript import Transcript
from evals.cached_llm import DEFAULT_ALLOWANCE, NOT_FINISHED_HINT, Budget, BudgetExhausted, CachedLLM
from evals.variants import WEAKNESSES, EvalDebate, check_shape, length_ratio, writer_messages

HERE = Path(__file__).parent
CACHE = HERE / "cache"
DATA = HERE / "data"
WRITER_SETTINGS = dict(temperature=0.8, max_tokens=4000, reasoning={"enabled": False})


def plan_items(topics: list[str], seed: int = 42) -> list[dict]:
    """Which side is weakened and how, decided up front with a fixed seed so re-runs ask the same questions."""
    rng = random.Random(seed)
    kinds = list(WEAKNESSES)
    return [
        {"id": f"d{i:02d}", "motion": m, "weak_side": rng.choice(["pro", "con"]), "weakness": kinds[i % len(kinds)]}
        for i, m in enumerate(topics)
    ]


def generate(cached: CachedLLM, writer_model: str, items: list[dict]) -> tuple[list[EvalDebate], list[dict], bool]:
    """Returns (debates, rejected, finished)."""
    debates, rejected, finished = [], [], True
    for it in items:
        try:
            r = cached.structured(
                writer_messages(it["motion"], it["weak_side"], it["weakness"]),
                writer_model,
                Transcript,
                **WRITER_SETTINGS,
            )
        except (BudgetExhausted, RateLimited, TransientError) as e:
            if finished:
                print(f"stopping new calls: {str(e)[:200]}")
                finished = False
                cached.cache_only = True  # still collect every debate already written
            continue
        except LLMError as e:
            rejected.append({**it, "problems": [str(e)[:200]]})
            continue
        t = Transcript(motion=it["motion"], turns=r.data.turns)  # type: ignore[attr-defined]
        problems = check_shape(t)
        if problems:
            rejected.append({**it, "problems": problems})
            continue
        debates.append(EvalDebate(writer_model=writer_model, transcript=t, **it))
    return debates, rejected, finished


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--allowance", type=int, default=DEFAULT_ALLOWANCE)
    p.add_argument("--retry-failed", action="store_true")
    p.add_argument("--writer", default=None, help="model that writes the debates (default: the opponent model)")
    args = p.parse_args()
    s = load_settings()
    writer = args.writer or s.opponent_model
    budget = Budget(CACHE / "_budget.json", args.allowance)
    cached = CachedLLM(LLMClient(s), CACHE, budget, retry_failed=args.retry_failed)
    items = plan_items(json.loads((HERE / "topics.json").read_text()))[: args.limit]
    debates, rejected, finished = generate(cached, writer, items)
    DATA.mkdir(exist_ok=True)
    # Merge with what is already on disk: a run that stops early, or uses --limit, must never drop debates.
    path = DATA / "debates.jsonl"
    merged = {}
    if path.exists():
        for line in path.read_text().splitlines():
            if line.strip():
                old = EvalDebate.model_validate_json(line)
                merged[old.id] = old
    for d in debates:
        merged[d.id] = d
    debates = [merged[k] for k in sorted(merged)]
    path.write_text("".join(d.model_dump_json() + "\n" for d in debates))
    (DATA / "rejected.json").write_text(json.dumps(rejected, indent=1))
    ratios = [length_ratio(d.transcript, d.weak_side) for d in debates]
    print(
        f"debates: {len(debates)} of {len(items)} | rejected: {len(rejected)} | new calls: {cached.calls}, "
        f"cache hits: {cached.hits} | today's allowance left: {budget.remaining()}"
    )
    if ratios:
        print(
            f"weak/strong length ratio: min {min(ratios):.2f}, max {max(ratios):.2f}, "
            f"mean {sum(ratios) / len(ratios):.2f}"
        )
    for r in rejected:
        print(f"  rejected {r['id']}: {r['problems'][0][:150]}")
    if not finished:
        print(NOT_FINISHED_HINT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
