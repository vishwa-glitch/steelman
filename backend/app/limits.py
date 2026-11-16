"""Usage limits: a global daily cap on AI calls, and a per-visitor cap on new debates."""

import datetime as dt
import hashlib

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.db import UsageRow


class LiveModeResting(Exception):
    """Today's AI-call limit is reached. The API answers 503 and the site shows recorded debates."""


class TooManyDebates(Exception):
    """This visitor has started their daily maximum of debates. The API answers 429."""


def today() -> dt.date:
    return dt.datetime.now(dt.UTC).date()


def hash_client(ip: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}:{ip}".encode()).hexdigest()


def spend_ai_call(db: Session, limit: int, n: int = 1) -> None:
    """Count n AI calls against today's limit, or raise. One atomic statement, so two requests arriving
    together cannot both take the last call. Commits at once: the count must survive a later failure."""
    row = db.execute(
        text(
            "INSERT INTO usage (day, ai_calls) VALUES (:day, :n) "
            "ON CONFLICT (day) DO UPDATE SET ai_calls = usage.ai_calls + :n "
            "WHERE usage.ai_calls + :n <= :limit RETURNING ai_calls"
        ),
        {"day": today(), "n": n, "limit": limit},
    ).first()
    if row is None or n > limit:
        db.rollback()
        raise LiveModeResting
    db.commit()


def ai_calls_today(db: Session) -> int:
    return db.execute(select(UsageRow.ai_calls).where(UsageRow.day == today())).scalar() or 0


def record_extra_calls(db: Session, n: int) -> None:
    """Count calls that already happened (retries, a repair). Never refuses: the requests were sent."""
    if n <= 0:
        return
    db.execute(
        text(
            "INSERT INTO usage (day, ai_calls) VALUES (:day, :n) "
            "ON CONFLICT (day) DO UPDATE SET ai_calls = usage.ai_calls + :n"
        ),
        {"day": today(), "n": n},
    )
    db.commit()


def claim_visitor_start(db: Session, client_hash: str, per_day: int) -> None:
    """Count one attempt to start a debate, or raise. Atomic, so parallel requests can't all slip under the
    limit, and it counts attempts that reach the model, not only debates created."""
    row = db.execute(
        text(
            "INSERT INTO visitor_usage (day, client_hash, starts) VALUES (:day, :h, 1) "
            "ON CONFLICT (day, client_hash) DO UPDATE SET starts = visitor_usage.starts + 1 "
            "WHERE visitor_usage.starts + 1 <= :limit RETURNING starts"
        ),
        {"day": today(), "h": client_hash, "limit": per_day},
    ).first()
    if row is None or per_day < 1:
        db.rollback()
        raise TooManyDebates
    db.commit()


def refund_visitor_start(db: Session, client_hash: str) -> None:
    """Give the attempt back when it failed for a reason that wasn't the visitor's doing (model busy or down)."""
    db.execute(
        text("UPDATE visitor_usage SET starts = GREATEST(starts - 1, 0) WHERE day = :day AND client_hash = :h"),
        {"day": today(), "h": client_hash},
    )
    db.commit()
