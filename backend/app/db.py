"""Database: two tables. `debates` holds each debate; `usage` counts AI calls per day.

No personal data is stored. The visitor's IP address is kept only as a salted hash, to enforce the
per-visitor daily limit.
"""

import datetime as dt
import uuid

from sqlalchemy import JSON, Date, DateTime, Integer, String, create_engine, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


class Base(DeclarativeBase):
    pass


class DebateRow(Base):
    __tablename__ = "debates"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    motion: Mapped[str] = mapped_column(String(200))
    user_side: Mapped[str] = mapped_column(String(3))
    difficulty: Mapped[str] = mapped_column(String(10))
    turns: Mapped[list] = mapped_column(JSON, default=list)
    scorecard: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    judge_meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    client_hash: Mapped[str] = mapped_column(String(64), index=True)
    # Claims: set while an AI turn or a judgment is in flight, so a second request can't start (and pay for)
    # the same work. A claim older than its timeout is treated as abandoned.
    ai_turn_started_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    judge_started_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class UsageRow(Base):
    __tablename__ = "usage"

    day: Mapped[dt.date] = mapped_column(Date, primary_key=True)
    ai_calls: Mapped[int] = mapped_column(Integer, default=0)


class VisitorUsageRow(Base):
    """How many debates a visitor (salted IP hash) has tried to start today."""

    __tablename__ = "visitor_usage"

    day: Mapped[dt.date] = mapped_column(Date, primary_key=True)
    client_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    starts: Mapped[int] = mapped_column(Integer, default=0)


def make_session_factory(database_url: str) -> sessionmaker:
    # prepare_threshold=None: psycopg would otherwise turn repeated queries into server-side prepared
    # statements, which can break behind a transaction-mode connection pooler such as Neon's.
    connect_args = {"prepare_threshold": None} if database_url.startswith("postgresql+psycopg") else {}
    engine = create_engine(database_url, pool_pre_ping=True, connect_args=connect_args)
    return sessionmaker(engine, expire_on_commit=False)
