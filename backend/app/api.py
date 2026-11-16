"""HTTP API.

POST /debates                 start a debate (topic check, per-visitor limit)
GET  /debates/{id}            the debate's current state
POST /debates/{id}/turns      add the user's turn
POST /debates/{id}/ai-turn    the AI's turn, streamed as server-sent events
POST /debates/{id}/judge      judge a finished debate (runs once; repeats return the saved scorecard)
GET  /share/{slug}            read-only view of a judged debate
GET  /status                  can live mode run right now?

The debate id is a random UUID known only to the browser that started the debate; it is what lets that
browser continue it. The share slug is a separate random value and gives read-only access.
"""

import json
import os
import secrets
import uuid
from collections.abc import Iterator
from functools import lru_cache
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings, load_settings
from app.db import DebateRow, make_session_factory
from app.debate import (
    MAX_MOTION_CHARS,
    MAX_TURN_CHARS,
    Debate,
    DebateError,
    TurnOrderError,
    check_topic,
    opponent_messages,
    validate_motion_text,
)
from app.judge import judge
from app.limits import (
    LiveModeResting,
    TooManyDebates,
    ai_calls_today,
    claim_visitor_start,
    hash_client,
    record_extra_calls,
    refund_visitor_start,
    spend_ai_call,
)
from app.llm import LLMClient, LLMError, RateLimited, TransientError
from app.transcript import Turn

router = APIRouter()
RESTING = "Live mode is resting for today. You can still watch the recorded debates."
BUSY = "The AI model is busy right now. Please try again in a minute."


@lru_cache
def get_settings() -> Settings:
    return load_settings()


@lru_cache
def _factory_for(database_url: str) -> sessionmaker:
    return make_session_factory(database_url)


def get_session_factory(settings: Settings = Depends(get_settings)) -> sessionmaker:
    return _factory_for(settings.database_url)


def get_db(factory: sessionmaker = Depends(get_session_factory)) -> Iterator[Session]:
    with factory() as session:
        yield session


@lru_cache
def get_llm() -> LLMClient:
    if os.environ.get("FAKE_LLM") == "1":  # local development and browser tests only
        from app.fake_llm import FakeLLM

        return FakeLLM()  # type: ignore[return-value]
    return LLMClient(get_settings())


class NewDebate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    motion: str = Field(max_length=MAX_MOTION_CHARS * 2)
    side: Literal["pro", "con"]
    difficulty: Literal["friendly", "sharp"] = "sharp"


class NewTurn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(max_length=MAX_TURN_CHARS * 2)


def to_debate(row: DebateRow) -> Debate:
    return Debate(
        motion=row.motion,
        user_side=row.user_side,  # type: ignore[arg-type]
        difficulty=row.difficulty,  # type: ignore[arg-type]
        turns=[Turn.model_validate(t) for t in row.turns],
    )


def view(row: DebateRow, include_id: bool = True) -> dict:
    d = to_debate(row)
    nxt = d.next_turn()
    out = {
        "motion": d.motion,
        "user_side": d.user_side,
        "difficulty": d.difficulty,
        "turns": [t.model_dump() for t in d.turns],
        "finished": d.finished,
        "next": None if nxt is None else {"side": nxt[0], "round": nxt[1], "who": d.whose_turn()},
        "scorecard": row.scorecard,
        "judge": row.judge_meta,
        "share_slug": row.slug if row.scorecard else None,
    }
    if include_id:
        out["id"] = str(row.id)
    return out


def load(db: Session, debate_id: uuid.UUID, lock: bool = False) -> DebateRow:
    q = select(DebateRow).where(DebateRow.id == debate_id)
    if lock:
        # populate_existing: re-read the row's values even if this session already holds the object.
        # Without it a locked re-read returns the stale copy, and a check like "is there a scorecard yet?"
        # sees the old answer.
        q = q.with_for_update().execution_options(populate_existing=True)
    row = db.execute(q).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "Debate not found.")
    return row


def client_ip(request: Request, settings: Settings) -> str:
    if settings.trust_proxy:
        # Our proxy appends the address it saw to whatever the client sent, so only the LAST entry is
        # trustworthy; earlier entries can be typed by anyone.
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


def spend(db: Session, settings: Settings, n: int = 1) -> None:
    try:
        spend_ai_call(db, settings.daily_ai_call_limit, n)
    except LiveModeResting:
        raise HTTPException(503, RESTING) from None


def sent(llm) -> int:
    return getattr(llm, "requests_sent", 0)


def settle(db: Session, llm, before: int) -> None:
    """One call was counted up front. If the client sent more (a retry, a repair), count the rest too."""
    record_extra_calls(db, sent(llm) - before - 1)


AI_TURN_CLAIM_S = 120
JUDGE_CLAIM_S = 180


def claim(db: Session, debate_id: uuid.UUID, column: str, seconds: int, condition: str, **params) -> bool:
    """Atomically mark work on this debate as started. False if someone else has a live claim, or the
    debate is no longer in the state the caller saw. `column` and `condition` are fixed strings from this
    file, never user input."""
    row = db.execute(
        text(
            f"UPDATE debates SET {column} = now() WHERE id = :id AND {condition} "
            f"AND ({column} IS NULL OR {column} < now() - make_interval(secs => :secs)) RETURNING id"
        ),
        {"id": debate_id, "secs": seconds, **params},
    ).first()
    db.commit()
    return row is not None


def release(db: Session, debate_id: uuid.UUID, column: str) -> None:
    db.execute(text(f"UPDATE debates SET {column} = NULL WHERE id = :id"), {"id": debate_id})
    db.commit()


@router.get("/status")
def status(db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> dict:
    used = ai_calls_today(db)
    # A full debate needs about 5 calls; don't invite someone to start one that can't finish.
    live = settings.daily_ai_call_limit - used >= 5
    return {"live": live, "message": None if live else RESTING}


@router.post("/debates", status_code=201)
def create_debate(
    body: NewDebate,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    llm: LLMClient = Depends(get_llm),
) -> dict:
    client_hash = hash_client(client_ip(request, settings), settings.ip_hash_salt)
    try:
        validate_motion_text(body.motion)  # free checks first: a motion blocked here costs nothing
    except DebateError as e:
        raise HTTPException(422, str(e)) from None
    try:
        claim_visitor_start(db, client_hash, settings.debates_per_ip_per_day)
    except TooManyDebates:
        raise HTTPException(429, "You've reached today's limit of new debates. Come back tomorrow.") from None
    try:
        spend(db, settings)
    except HTTPException:
        refund_visitor_start(db, client_hash)
        raise
    before = sent(llm)
    try:
        motion = check_topic(body.motion, llm, settings.judge_backup_model)
    except DebateError as e:  # the model rejected the motion: this attempt counts against the visitor
        raise HTTPException(422, str(e)) from None
    except RateLimited:
        refund_visitor_start(db, client_hash)
        raise HTTPException(503, BUSY) from None
    except LLMError:
        refund_visitor_start(db, client_hash)
        raise HTTPException(502, "The topic check failed. Please try again.") from None
    finally:
        settle(db, llm, before)
    row = DebateRow(
        slug=secrets.token_urlsafe(16),
        motion=motion,
        user_side=body.side,
        difficulty=body.difficulty,
        turns=[],
        client_hash=client_hash,
    )
    db.add(row)
    db.commit()
    return view(row)


@router.get("/debates/{debate_id}")
def get_debate(debate_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    return view(load(db, debate_id))


@router.post("/debates/{debate_id}/turns")
def add_turn(debate_id: uuid.UUID, body: NewTurn, db: Session = Depends(get_db)) -> dict:
    row = load(db, debate_id, lock=True)
    d = to_debate(row)
    try:
        d.add_user_turn(body.text)
    except TurnOrderError as e:
        raise HTTPException(409, str(e)) from None
    except DebateError as e:
        raise HTTPException(422, str(e)) from None
    row.turns = [t.model_dump() for t in d.turns]
    db.commit()
    return view(row)


def start_opponent(d: Debate, llm, settings: Settings, db: Session):
    """Start streaming the AI's turn. If the opponent's free model is busy or down before it has said
    anything, try the backup model once (counted as one more AI call). Returns (stream, first piece)."""
    last: Exception | None = None
    for i, model in enumerate((settings.opponent_model, settings.opponent_backup_model)):
        if i == 1:
            if model == settings.opponent_model or not isinstance(last, (RateLimited, TransientError)):
                break
            spend(db, settings)
        stream = llm.chat_stream(
            opponent_messages(d), model, temperature=0.7, max_tokens=700, reasoning={"enabled": False}
        )
        try:
            return stream, next(stream)  # fail with a normal HTTP error if the model can't even start
        except (LLMError, StopIteration) as e:
            last = e
    if isinstance(last, RateLimited):
        raise HTTPException(503, BUSY)
    raise HTTPException(502, "The AI couldn't reply. Please try again.")


def sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


@router.post("/debates/{debate_id}/ai-turn")
def ai_turn(
    debate_id: uuid.UUID,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    llm: LLMClient = Depends(get_llm),
    factory: sessionmaker = Depends(get_session_factory),
) -> StreamingResponse:
    row = load(db, debate_id)
    d = to_debate(row)
    if d.whose_turn() != "ai":
        raise HTTPException(409, "It is not the AI's turn.")
    turns_before = len(d.turns)
    # Claim the turn before paying for it, so a second tab, a double click or a reload can't start (and
    # spend an AI call on) the same turn.
    if not claim(db, debate_id, "ai_turn_started_at", AI_TURN_CLAIM_S, "json_array_length(turns) = :n", n=turns_before):
        raise HTTPException(409, "The AI is already replying.")
    try:
        spend(db, settings)
        stream, first = start_opponent(d, llm, settings, db)
    except HTTPException:
        release(db, debate_id, "ai_turn_started_at")
        raise

    def events() -> Iterator[str]:
        parts = [first]
        saved = False
        try:
            yield sse({"delta": first})
            try:
                for piece in stream:
                    parts.append(piece)
                    yield sse({"delta": piece})
            except LLMError:
                yield sse({"error": "The AI's reply was cut off. Please try again."})
                return
            with factory() as fresh:
                locked = load(fresh, debate_id, lock=True)
                current = to_debate(locked)
                if len(current.turns) != turns_before or current.whose_turn() != "ai":
                    yield sse({"error": "This turn was already taken.", "debate": view(locked)})
                    return
                current.add_ai_turn("".join(parts))
                locked.turns = [t.model_dump() for t in current.turns]
                locked.ai_turn_started_at = None
                fresh.commit()
                saved = True
                yield sse({"done": True, "debate": view(locked)})
        finally:
            if not saved:  # cut off, or the browser went away: let the turn be retried at once
                with factory() as cleanup:
                    release(cleanup, debate_id, "ai_turn_started_at")

    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@router.post("/debates/{debate_id}/judge")
def judge_debate(
    debate_id: uuid.UUID,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    llm: LLMClient = Depends(get_llm),
) -> dict:
    row = load(db, debate_id)
    if row.scorecard:
        return view(row)
    d = to_debate(row)
    if not d.finished:
        raise HTTPException(409, "The debate isn't finished yet.")
    # Claim the judgment before paying for it: only one request may judge a debate at a time.
    if not claim(db, debate_id, "judge_started_at", JUDGE_CLAIM_S, "scorecard IS NULL"):
        raise HTTPException(409, "The judge is already deliberating.")
    before = sent(llm)
    try:
        spend(db, settings)
        try:
            res = judge(d.transcript(), llm, settings.judge_model)
        except RateLimited:
            raise HTTPException(503, BUSY) from None
        except LLMError:
            raise HTTPException(502, "The judge couldn't produce a valid scorecard. Please try again.") from None
        finally:
            settle(db, llm, before)
    except HTTPException:
        release(db, debate_id, "judge_started_at")
        raise
    locked = load(db, debate_id, lock=True)
    if not locked.scorecard:  # belt and braces: never overwrite a scorecard that is already saved
        locked.scorecard = res.scorecard.model_dump()
        locked.judge_meta = {
            "version": res.judge_version,
            "model": res.model,
            "dropped_quotes": len(res.dropped_quotes),
            "kept_quotes": res.kept_quotes,
        }
    locked.judge_started_at = None
    db.commit()
    return view(locked)


@router.get("/share/{slug}")
def share(slug: str, db: Session = Depends(get_db)) -> dict:
    row = db.execute(select(DebateRow).where(DebateRow.slug == slug)).scalar_one_or_none()
    if row is None or not row.scorecard:
        raise HTTPException(404, "Debate not found.")
    return view(row, include_id=False)
