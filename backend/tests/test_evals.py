"""Eval machinery tests: metric maths, variants, caching, the daily allowance and resuming. No network."""

import json

from pydantic import BaseModel, ConfigDict

from app.llm import LLMError, RateLimited, StructuredResult
from app.transcript import Transcript, Turn
from evals.cached_llm import Budget, BudgetExhausted, CachedFailure, CachedLLM
from evals.generate import plan_items
from evals.metrics import consistency, length_bias, quotes, self_preference, summarise
from evals.run import run
from evals.variants import EvalDebate, check_shape, length_ratio, swap_order

WORDS = " ".join(["word"] * 20)


def transcript(pro_extra="", con_extra=""):
    turns = []
    for rnd in ("opening", "rebuttal", "closing"):
        turns.append(Turn(side="pro", round=rnd, text=f"pro {rnd} {WORDS} {pro_extra}"))
        turns.append(Turn(side="con", round=rnd, text=f"con {rnd} {WORDS} {con_extra}"))
    return Transcript(motion="m", turns=turns)


def rec(id, condition, winner, label="pro", strong=30, weak=20, ok=True, kept=3, dropped=0):
    return {
        "id": id,
        "condition": condition,
        "ok": ok,
        "winner": winner,
        "label": label,
        "correct": ok and winner == label,
        "strong_total": strong,
        "weak_total": weak,
        "kept_quotes": kept,
        "dropped_quotes": dropped,
    }


# ---------- metrics ----------


def test_consistency_counts_only_pairs_valid_in_both():
    records = [
        rec("a", "original", "pro"),
        rec("a", "swapped", "con"),
        rec("b", "original", "pro"),
        rec("b", "swapped", "pro"),
        rec("c", "original", "pro"),
        rec("c", "swapped", None, ok=False),
    ]
    assert consistency(records, "original", "swapped") == {"pairs": 2, "same": 1, "flips": 1, "rate": 0.5}


def test_length_bias_gain_and_flips():
    records = [
        rec("a", "original", "pro", weak=20),
        rec("a", "padded_weak", "con", weak=31),
        rec("b", "original", "pro", weak=20),
        rec("b", "padded_weak", "pro", weak=21),
    ]
    assert length_bias(records) == {"pairs": 2, "mean_weak_gain": 6.0, "flips_to_weak": 1}


def test_self_preference_margins():
    records = [
        rec("a", "original", "pro", strong=30, weak=20),
        rec("a", "selfpref_strong", "pro", strong=34, weak=20),
        rec("a", "selfpref_weak", "pro", strong=30, weak=26),
    ]
    sp = self_preference(records)
    assert (
        sp["margin_original"],
        sp["margin_strong_reworded_by_judge_family"],
        sp["margin_weak_reworded_by_judge_family"],
    ) == (10, 14, 4)


def test_quotes_and_summary_progress():
    records = [rec("a", "original", "pro", kept=3, dropped=1), rec("b", "original", "con", kept=4, dropped=0)]
    assert quotes(records) == {"kept": 7, "dropped": 1, "drop_rate": 0.125}
    s = summarise(records, {"original": 3, "swapped": 3})
    assert s["progress"] == {"original": "2/3", "swapped": "0/3"}
    assert s["accuracy"]["original"] == {"n": 2, "correct": 1, "rate": 0.5}


# ---------- variants ----------


def test_swap_order_puts_con_first_and_keeps_words():
    t = transcript()
    s = swap_order(t)
    assert [(x.side, x.round) for x in s.turns][:2] == [("con", "opening"), ("pro", "opening")]
    assert sorted(x.text for x in s.turns) == sorted(x.text for x in t.turns)


def test_check_shape_accepts_good_and_flags_wrong_order():
    t = transcript()
    assert check_shape(t) == []
    assert check_shape(swap_order(t))  # CON-first is not what the writer was asked for


def test_length_ratio():
    t = transcript(con_extra=" ".join(["x"] * 23))  # con 22+23 words a turn vs pro 22
    assert round(length_ratio(t, "con"), 2) == round(45 / 22, 2)


def test_plan_items_is_deterministic():
    assert plan_items(["a", "b", "c", "d"]) == plan_items(["a", "b", "c", "d"])
    assert {i["weakness"] for i in plan_items(["a", "b", "c"])} == {"no_evidence", "fallacy", "ignores_rebuttal"}


# ---------- cache and allowance ----------


class Small(BaseModel):
    model_config = ConfigDict(extra="forbid")
    v: int


class FakeClient:
    def __init__(self, behaviour=None):
        self.calls = 0
        self.behaviour = behaviour or (lambda n: f'{{"v": {n}}}')

    def structured(self, messages, model, schema, **kw):
        self.calls += 1
        if schema.__name__ == "ThreeTurns":  # rewrite steps (padding, rewording) get a valid rewrite
            out = json.dumps({r: f"rewrite {self.calls} {r} {WORDS}" for r in ("opening", "rebuttal", "closing")})
            return StructuredResult(
                data=schema.model_validate_json(out),
                raw_text=out,
                model=model,
                latency_s=0.0,
                attempts=1,
                repaired=False,
            )
        out = self.behaviour(self.calls)
        if isinstance(out, Exception):
            raise out
        return StructuredResult(
            data=schema.model_validate_json(out), raw_text=out, model=model, latency_s=0.0, attempts=1, repaired=False
        )


def make_cached(tmp_path, allowance=10, behaviour=None, today="2026-11-16"):
    fake = FakeClient(behaviour)
    budget = Budget(tmp_path / "_budget.json", allowance, today=lambda: today)
    return CachedLLM(fake, tmp_path, budget), fake, budget


MSG = [{"role": "user", "content": "q"}]


def test_cache_hit_does_not_call_or_spend(tmp_path):
    c, fake, budget = make_cached(tmp_path)
    assert c.structured(MSG, "m", Small).data.v == 1
    assert c.structured(MSG, "m", Small).data.v == 1  # same answer, from disk
    assert fake.calls == 1 and budget.used() == 1


def test_tag_gives_a_fresh_answer_for_reruns(tmp_path):
    c, fake, _ = make_cached(tmp_path)
    c.structured(MSG, "m", Small)
    assert c.with_tag("rerun-1").structured(MSG, "m", Small).data.v == 2 and fake.calls == 2


def test_allowance_stops_before_calling(tmp_path):
    c, fake, _ = make_cached(tmp_path, allowance=1)
    c.structured(MSG, "m", Small)
    try:
        c.structured([{"role": "user", "content": "other"}], "m", Small)
        raise AssertionError("expected BudgetExhausted")
    except BudgetExhausted:
        pass
    assert fake.calls == 1


def test_allowance_resets_on_a_new_day(tmp_path):
    c, _, _ = make_cached(tmp_path, allowance=1)
    c.structured(MSG, "m", Small)
    c2, fake2, budget2 = make_cached(tmp_path, allowance=1, today="2026-11-17")
    c2.structured([{"role": "user", "content": "other"}], "m", Small)
    assert fake2.calls == 1 and budget2.used() == 1


def test_failures_are_cached_unless_retry_requested(tmp_path):
    c, fake, _ = make_cached(tmp_path, behaviour=lambda n: LLMError("bad json") if n == 1 else '{"v": 9}')
    for _ in range(2):
        try:
            c.structured(MSG, "m", Small)
        except LLMError as e:
            last = e
    assert isinstance(last, CachedFailure) and fake.calls == 1
    c.retry_failed = True
    assert c.structured(MSG, "m", Small).data.v == 9 and fake.calls == 2


def test_rate_limit_is_not_cached(tmp_path):
    c, fake, _ = make_cached(tmp_path, behaviour=lambda n: RateLimited("429", None) if n == 1 else '{"v": 5}')
    try:
        c.structured(MSG, "m", Small)
    except RateLimited:
        pass
    assert c.structured(MSG, "m", Small).data.v == 5 and fake.calls == 2


# ---------- the runner stops and resumes ----------


class FakeJudgeResult:
    def __init__(self, winner):
        from app.judge import CRITERIA, Scorecard

        def side(name, s):
            return {
                "side": name,
                "scores": [{"criterion": c, "score": s, "quotes": [], "reason": "r"} for c in CRITERIA],
            }

        self.scorecard = Scorecard.model_validate(
            {"sides": [side("pro", 8), side("con", 5)], "winner": winner, "summary": "s"}
        )
        self.kept_quotes, self.dropped_quotes, self.model, self.latency_s = 2, [], "j", 0.1


def fake_judge(t, client, model):
    """Spends one cached call per distinct transcript, like the real judge does."""
    client.structured([{"role": "user", "content": t.render()}], model, Small)
    return FakeJudgeResult("pro")


def debates(n):
    return [
        EvalDebate(
            id=f"d{i}",
            motion=f"m{i}",
            weak_side="con",
            weakness="fallacy",
            writer_model="w",
            transcript=transcript(pro_extra=str(i)),
        )
        for i in range(n)
    ]


def test_runner_stops_at_allowance_and_resumes_without_repeating(tmp_path):
    ds = debates(3)
    c, fake, budget = make_cached(tmp_path, allowance=4)
    records, planned, stopped = run(ds, fake_judge, c, "w", "j", subset_n=1)
    assert stopped and "BudgetExhausted" in stopped and len(records) == 4 and fake.calls == 4
    # next day: a fresh allowance; the first 4 judgments come from the cache
    c2, fake2, _ = make_cached(tmp_path, allowance=50, today="2026-11-17")
    records2, planned2, stopped2 = run(ds, fake_judge, c2, "w", "j", subset_n=1)
    assert stopped2 is None
    assert planned2 == {
        "original": 3,
        "swapped": 3,
        "rerun": 1,
        "padded_weak": 1,
        "selfpref_strong": 1,
        "selfpref_weak": 1,
    }
    assert len(records2) == 10
    # padded/selfpref need one rewrite call each, plus one judge call; the 4 cached judgments cost nothing
    assert fake2.calls == (6 - 4) + 1 + 3 * 2
    assert all(r["correct"] for r in records2 if r["ok"])
