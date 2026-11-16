"""Wraps LLMClient for evals: every answer is cached on disk, and calls are counted against a daily allowance.

Why: free models allow 50 requests a day per account. A full eval run takes several days, so the runner must
stop cleanly when today's allowance is used and pick up where it left off tomorrow, never paying twice for
the same call. Failures are cached too (so a broken item doesn't eat the budget every day) unless asked to retry.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from app.llm import LLMError, RateLimited, StructuredResult, TransientError, _parse

DEFAULT_ALLOWANCE = 35  # leaves room under the 50/day free cap for manual testing


NOT_FINISHED_HINT = (
    "Not finished. If today's allowance is used up, run again tomorrow. If a model was rate-limited upstream "
    "(its provider's shared free pool is busy), run again in a few minutes. Finished work is cached either way."
)


class BudgetExhausted(Exception):
    """Today's allowance is used up. Run again tomorrow; cached work is kept."""


class CachedFailure(LLMError):
    """This exact call failed before; the failure was cached."""


class Budget:
    """Counts requests per UTC day in a small JSON file."""

    def __init__(self, path: Path, allowance: int, today=None):
        self.path, self.allowance = path, allowance
        self._today = today or (lambda: dt.datetime.now(dt.UTC).date().isoformat())

    def _load(self) -> dict:
        if self.path.exists():
            d = json.loads(self.path.read_text())
            if d.get("date") == self._today():
                return d
        return {"date": self._today(), "used": 0}

    def used(self) -> int:
        return self._load()["used"]

    def remaining(self) -> int:
        return max(0, self.allowance - self.used())

    def require_one(self) -> None:
        if self.remaining() < 1:
            raise BudgetExhausted(f"used {self.used()} of today's allowance of {self.allowance}")

    def spend(self, n: int) -> None:
        d = self._load()
        d["used"] += n
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(d))


class CachedLLM:
    def __init__(self, client, cache_dir: Path, budget: Budget, tag: str = "", retry_failed: bool = False):
        self.client, self.cache_dir, self.budget = client, cache_dir, budget
        self.tag, self.retry_failed = tag, retry_failed
        # After a stop (allowance used, or rate limited) the runners keep going in cache-only mode, so every
        # finished piece of work is still reported instead of the report ending at the first gap.
        self.cache_only = False
        self.hits = 0
        self.calls = 0

    def with_tag(self, tag: str) -> CachedLLM:
        """Same cache and budget, different key: used to ask the same question again (re-run noise test)."""
        other = CachedLLM(self.client, self.cache_dir, self.budget, tag=tag, retry_failed=self.retry_failed)
        other.cache_only = self.cache_only
        return other

    def _path(self, payload: dict[str, Any]) -> Path:
        key = hashlib.sha256(json.dumps({**payload, "tag": self.tag}, sort_keys=True).encode()).hexdigest()
        return self.cache_dir / f"{key[:2]}/{key}.json"

    def structured(self, messages, model, schema: type[BaseModel], **kw) -> StructuredResult:
        payload = {
            "kind": "structured",
            "model": model,
            "messages": messages,
            "schema": schema.model_json_schema(),
            **kw,
        }
        path = self._path(payload)
        if path.exists():
            d = json.loads(path.read_text())
            if d["ok"]:
                self.hits += 1
                return StructuredResult(
                    data=_parse(d["raw_text"], schema),
                    raw_text=d["raw_text"],
                    model=d["model"],
                    latency_s=d["latency_s"],
                    attempts=0,
                    repaired=d["repaired"],
                )
            if not self.retry_failed:
                self.hits += 1
                raise CachedFailure(d["error"])
        if self.cache_only:
            raise BudgetExhausted("cache-only mode: not cached yet")
        self.budget.require_one()
        self.calls += 1
        before = getattr(self.client, "requests_sent", None)

        def sent(default: int) -> int:
            # The real client counts every HTTP request (retries, repairs). Fakes in tests don't, so fall back.
            after = getattr(self.client, "requests_sent", None)
            return after - before if before is not None and after is not None else default

        try:
            r = self.client.structured(messages, model, schema, **kw)
        except RateLimited:
            self.budget.spend(sent(1))
            raise  # not cached: try again another time
        except TransientError:
            self.budget.spend(sent(2))
            raise  # a network or provider failure says nothing about the model: not cached
        except LLMError as e:
            self.budget.spend(sent(2))
            self._write(path, {"ok": False, "error": f"{type(e).__name__}: {e}"})
            raise
        self.budget.spend(sent(max(1, r.attempts)))
        self._write(
            path,
            {"ok": True, "raw_text": r.raw_text, "model": r.model, "latency_s": r.latency_s, "repaired": r.repaired},
        )
        return r

    @staticmethod
    def _write(path: Path, data: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data))
