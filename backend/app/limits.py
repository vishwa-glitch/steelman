"""Usage limits: a global daily cap on AI calls, and a per-visitor cap on new debates."""

import datetime as dt
import hashlib

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.db import DebateRow, UsageRow


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


def check_debate_quota(db: Session, client_hash: str, per_day: int) -> None:
    start = dt.datetime.combine(today(), dt.time.min, tzinfo=dt.UTC)
    count = db.execute(
        select(func.count())
        .select_from(DebateRow)
        .where(DebateRow.client_hash == client_hash, DebateRow.created_at >= start)
    ).scalar()
    if count >= per_day:
        raise TooManyDebates
