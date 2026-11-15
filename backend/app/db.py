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
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class UsageRow(Base):
    __tablename__ = "usage"

    day: Mapped[dt.date] = mapped_column(Date, primary_key=True)
    ai_calls: Mapped[int] = mapped_column(Integer, default=0)


def make_session_factory(database_url: str) -> sessionmaker:
    return sessionmaker(create_engine(database_url, pool_pre_ping=True), expire_on_commit=False)
