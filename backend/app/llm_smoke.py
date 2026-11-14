"""Smoke test against real free models: does each one return valid structured JSON, and how fast?

Run: python -m app.llm_smoke [--judge N] [--backup N] [--opponent N]
Each call counts against the free cap (50 requests/day), so the defaults are small.
"""

import argparse
import statistics
import sys
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.config import load_settings
from app.llm import LLMClient, LLMError, RateLimited


class MiniVerdict(BaseModel):
    model_config = ConfigDict(extra="forbid")
    winner: Literal["A", "B"]
    score_a: int
    score_b: int
    reason: str


JUDGE_PROMPT = [
    {
        "role": "system",
        "content": "You judge short debate arguments. Score each side from 1 to 10 for argument strength, "
        "pick the stronger side, and give a one-sentence reason. Reply only with JSON matching the schema.",
    },
    {
        "role": "user",
        "content": "Motion: Cities should ban cars from their centres.\n"
        "A: Car-free centres cut air pollution; after Madrid restricted cars in 2018, nitrogen dioxide "
        "levels in the centre fell sharply, and shops reported steady trade.\n"
        "B: Banning cars is bad because people like cars.",
    },
]

OPPONENT_PROMPT = [
    {
        "role": "system",
        "content": "You are a sharp debater. Argue against the user's position in under 80 words.",
    },
    {"role": "user", "content": "Homework should be banned in primary schools."},
]


def run_structured(client: LLMClient, model: str, n: int) -> dict:
    ok, repaired, failed, latencies, served, errors = 0, 0, 0, [], set(), []
    for _ in range(n):
        try:
            r = client.structured(JUDGE_PROMPT, model, MiniVerdict)
        except RateLimited as e:
            errors.append(f"rate limited (retry-after={e.retry_after})")
            break
        except LLMError as e:
            failed += 1
            errors.append(str(e)[:160])
            continue
        ok += 1
        repaired += r.repaired
        latencies.append(r.latency_s)
        served.add(r.model)
        print(
            f"  {model}: winner={r.data.winner} A={r.data.score_a} B={r.data.score_b} {r.latency_s:.1f}s",
            flush=True,
        )
    return dict(
        model=model,
        calls=ok + failed,
        valid=ok,
        repaired=repaired,
        failed=failed,
        median_s=statistics.median(latencies) if latencies else None,
        served=served,
        errors=errors,
    )


def run_chat(client: LLMClient, model: str, n: int) -> dict:
    ok, failed, latencies, served, errors = 0, 0, [], set(), []
    for _ in range(n):
        try:
            r = client.chat(OPPONENT_PROMPT, model, max_tokens=200)
        except RateLimited as e:
            errors.append(f"rate limited (retry-after={e.retry_after})")
            break
        except LLMError as e:
            failed += 1
            errors.append(str(e)[:160])
            continue
        ok += 1
        latencies.append(r.latency_s)
        served.add(r.model)
        print(f"  {model}: {len(r.text.split())} words {r.latency_s:.1f}s | {r.text[:90]!r}", flush=True)
    return dict(
        model=model,
        calls=ok + failed,
        valid=ok,
        repaired=0,
        failed=failed,
        median_s=statistics.median(latencies) if latencies else None,
        served=served,
        errors=errors,
    )


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--judge", type=int, default=8)
    p.add_argument("--backup", type=int, default=5)
    p.add_argument("--opponent", type=int, default=5)
    args = p.parse_args()
    s = load_settings()
    client = LLMClient(s)
    results = []
    if args.judge:
        results.append(("judge (structured)", run_structured(client, s.judge_model, args.judge)))
    if args.backup:
        results.append(("backup judge (structured)", run_structured(client, s.judge_backup_model, args.backup)))
    if args.opponent:
        results.append(("opponent (chat)", run_chat(client, s.opponent_model, args.opponent)))
    print("\nrole                       model                                     calls valid repaired failed median_s")
    for role, r in results:
        med = f"{r['median_s']:.1f}" if r["median_s"] is not None else "-"
        print(f"{role:26} {r['model']:41} {r['calls']:5} {r['valid']:5} {r['repaired']:8} {r['failed']:6} {med:>8}")
        if r["served"] - {r["model"]}:
            print(f"   served as: {sorted(r['served'])}")
        for e in r["errors"][:3]:
            print(f"   error: {e}")
    return 0 if all(r["valid"] > 0 for _, r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
