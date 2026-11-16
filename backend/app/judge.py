"""The judge (v0): scores both sides against a rubric, with quoted evidence, then gives a verdict.

v0 is deliberately simple. The evals (step 4) measure where it goes wrong; v1 (step 5) fixes what they find.
Plain code then checks every quote: one that isn't really in that side's text is dropped and counted.

Run: python -m app.judge path/to/transcript.json
"""

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

from app.config import load_settings
from app.llm import LLMClient
from app.quotes import is_real_quote
from app.transcript import Side, Transcript

JUDGE_VERSION = "v0"
# The judge model reasons before answering. With max_tokens=2500 it spent every token reasoning and returned
# nothing; with reasoning off its answer overran and was cut off. Low effort + room to answer works (15-16 Nov).
JUDGE_REASONING = {"effort": "low"}
JUDGE_MAX_TOKENS = 8000
CRITERIA = ("argument_strength", "evidence", "rebuttal", "clarity")


class CriterionScore(BaseModel):
    model_config = ConfigDict(extra="forbid")
    criterion: Literal["argument_strength", "evidence", "rebuttal", "clarity"]
    score: int
    quotes: list[str]
    reason: str

    @field_validator("score")
    @classmethod
    def in_range(cls, v: int) -> int:
        if not 1 <= v <= 10:
            raise ValueError("score must be 1 to 10")
        return v


class SideScores(BaseModel):
    model_config = ConfigDict(extra="forbid")
    side: Literal["pro", "con"]
    scores: list[CriterionScore]

    @field_validator("scores")
    @classmethod
    def all_criteria_once(cls, v: list[CriterionScore]) -> list[CriterionScore]:
        if sorted(s.criterion for s in v) != sorted(CRITERIA):
            raise ValueError(f"need exactly one score for each of {CRITERIA}")
        return v


class Scorecard(BaseModel):
    """What the model must return."""

    model_config = ConfigDict(extra="forbid")
    sides: list[SideScores]
    winner: Literal["pro", "con"]
    summary: str

    @field_validator("sides")
    @classmethod
    def both_sides_once(cls, v: list[SideScores]) -> list[SideScores]:
        if sorted(s.side for s in v) != ["con", "pro"]:
            raise ValueError("need exactly one entry for pro and one for con")
        return v

    def side(self, side: Side) -> SideScores:
        return next(s for s in self.sides if s.side == side)

    def total(self, side: Side) -> int:
        return sum(c.score for c in self.side(side).scores)


SYSTEM_PROMPT = """You are an impartial debate judge.

Score each side (PRO and CON) from 1 to 10 on each criterion:
- argument_strength: are the arguments logical and relevant to the motion?
- evidence: are claims backed by specific facts, examples or data?
- rebuttal: does the side directly answer the other side's points?
- clarity: is it clear and well organised?

For every score, give 1 to 3 short quotes copied exactly, word for word, from that side's own words, and a
one-sentence reason. Then pick the winner and write a two-sentence summary.
Judge only what is written. Reply only with JSON matching the schema."""


@dataclass
class JudgeResult:
    scorecard: Scorecard
    model: str
    judge_version: str
    latency_s: float
    attempts: int
    repaired: bool
    dropped_quotes: list[dict] = field(default_factory=list)  # quotes not found in that side's text
    kept_quotes: int = 0


def check_quotes(card: Scorecard, transcript: Transcript) -> tuple[int, list[dict]]:
    """Remove quotes that don't appear in that side's own text. Returns (kept count, dropped list)."""
    kept, dropped = 0, []
    for side_scores in card.sides:
        turns = transcript.texts_of(side_scores.side)  # a quote must sit inside one turn, not span two
        for c in side_scores.scores:
            real = [q for q in c.quotes if any(is_real_quote(q, t) for t in turns)]
            for q in c.quotes:
                if q not in real:
                    dropped.append({"side": side_scores.side, "criterion": c.criterion, "quote": q})
            kept += len(real)
            c.quotes = real
    return kept, dropped


def judge(transcript: Transcript, client: LLMClient, model: str) -> JudgeResult:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": transcript.render()},
    ]
    r = client.structured(
        messages, model, Scorecard, temperature=0.0, max_tokens=JUDGE_MAX_TOKENS, reasoning=JUDGE_REASONING
    )
    card: Scorecard = r.data  # type: ignore[assignment]
    kept, dropped = check_quotes(card, transcript)
    return JudgeResult(
        scorecard=card,
        model=r.model,
        judge_version=JUDGE_VERSION,
        latency_s=r.latency_s,
        attempts=r.attempts,
        repaired=r.repaired,
        dropped_quotes=dropped,
        kept_quotes=kept,
    )


def format_scorecard(res: JudgeResult) -> str:
    card = res.scorecard
    out = [f"Judge {res.judge_version} ({res.model}), {res.latency_s:.1f}s, attempts={res.attempts}"]
    for side in ("pro", "con"):
        out.append(f"\n{side.upper()}  total {card.total(side)}/40")
        for c in card.side(side).scores:
            out.append(f"  {c.criterion:18} {c.score:2}  {c.reason}")
            for q in c.quotes:
                out.append(f"      “{q}”")
    out.append(f"\nWinner: {card.winner.upper()}. {card.summary}")
    out.append(f"Quotes kept: {res.kept_quotes}, dropped as not found: {len(res.dropped_quotes)}")
    for d in res.dropped_quotes:
        out.append(f"  dropped ({d['side']}, {d['criterion']}): {d['quote']!r}")
    return "\n".join(out)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python -m app.judge path/to/transcript.json")
        return 2
    transcript = Transcript.model_validate(json.loads(Path(sys.argv[1]).read_text()))
    s = load_settings()
    print(format_scorecard(judge(transcript, LLMClient(s), s.judge_model)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
