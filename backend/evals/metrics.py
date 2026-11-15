"""Turn per-judgment records into the eval numbers. Pure functions, so the maths is unit-tested.

A record: {id, condition, ok, winner, label, correct, strong_total, weak_total, kept_quotes, dropped_quotes}.
"""

from statistics import mean


def _by(records, condition):
    return {r["id"]: r for r in records if r["condition"] == condition}


def _ok(records, condition):
    return {i: r for i, r in _by(records, condition).items() if r["ok"]}


def _rate(k, n):
    return round(k / n, 3) if n else None


def accuracy(records, condition):
    ok = _ok(records, condition)
    return {
        "n": len(ok),
        "correct": sum(r["correct"] for r in ok.values()),
        "rate": _rate(sum(r["correct"] for r in ok.values()), len(ok)),
    }


def valid_rate(records, condition):
    allr = _by(records, condition)
    return {
        "n": len(allr),
        "valid": sum(r["ok"] for r in allr.values()),
        "rate": _rate(sum(r["ok"] for r in allr.values()), len(allr)),
    }


def consistency(records, a, b):
    """Of debates judged validly under both conditions, how often is the winner the same?"""
    ra, rb = _ok(records, a), _ok(records, b)
    pairs = [i for i in ra if i in rb]
    same = sum(ra[i]["winner"] == rb[i]["winner"] for i in pairs)
    return {"pairs": len(pairs), "same": same, "flips": len(pairs) - same, "rate": _rate(same, len(pairs))}


def length_bias(records):
    """Does making the weaker side longer (with nothing new) raise its score or flip the verdict to it?"""
    ro, rp = _ok(records, "original"), _ok(records, "padded_weak")
    pairs = [i for i in ro if i in rp]
    gains = [rp[i]["weak_total"] - ro[i]["weak_total"] for i in pairs]
    flips = sum(ro[i]["correct"] and not rp[i]["correct"] for i in pairs)
    return {"pairs": len(pairs), "mean_weak_gain": round(mean(gains), 2) if gains else None, "flips_to_weak": flips}


def self_preference(records):
    """Margin = strong side's total minus weak side's, on debates valid in all three conditions.
    If the judge favours its own family's wording, the margin rises when the strong side is reworded by that
    family and falls when the weak side is."""
    ro, rs, rw = _ok(records, "original"), _ok(records, "selfpref_strong"), _ok(records, "selfpref_weak")
    ids = [i for i in ro if i in rs and i in rw]

    def margin(r):
        return round(mean(x["strong_total"] - x["weak_total"] for x in r), 2) if ids else None

    return {
        "n": len(ids),
        "margin_original": margin([ro[i] for i in ids]),
        "margin_strong_reworded_by_judge_family": margin([rs[i] for i in ids]),
        "margin_weak_reworded_by_judge_family": margin([rw[i] for i in ids]),
        "accuracy_weak_reworded": _rate(sum(rw[i]["correct"] for i in ids), len(ids)),
    }


def quotes(records):
    ok = [r for r in records if r["ok"]]
    kept, dropped = sum(r["kept_quotes"] for r in ok), sum(r["dropped_quotes"] for r in ok)
    return {"kept": kept, "dropped": dropped, "drop_rate": _rate(dropped, kept + dropped)}


def summarise(records, planned: dict[str, int]) -> dict:
    conds = list(planned)
    return {
        "progress": {c: f"{len(_by(records, c))}/{planned[c]}" for c in conds},
        "valid_output": {c: valid_rate(records, c) for c in conds},
        "accuracy": {c: accuracy(records, c) for c in conds},
        "order_swap_consistency": consistency(records, "original", "swapped"),
        "rerun_consistency": consistency(records, "original", "rerun"),
        "length_bias": length_bias(records),
        "self_preference": self_preference(records),
        "quotes": quotes(records),
    }
