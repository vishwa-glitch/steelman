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
import secrets
import uuid
from collections.abc import Iterator
from functools import lru_cache
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
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
    check_debate_quota,
    hash_client,
    spend_ai_call,
)
from app.llm import LLMClient, LLMError, RateLimited
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
    row = db.execute(q.with_for_update() if lock else q).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "Debate not found.")
    return row


def client_ip(request: Request, settings: Settings) -> str:
    if settings.trust_proxy:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def spend(db: Session, settings: Settings, n: int = 1) -> None:
    try:
        spend_ai_call(db, settings.daily_ai_call_limit, n)
    except LiveModeResting:
        raise HTTPException(503, RESTING) from None


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
        check_debate_quota(db, client_hash, settings.debates_per_ip_per_day)
    except TooManyDebates:
        raise HTTPException(429, "You've reached today's limit of new debates. Come back tomorrow.") from None
    try:
        validate_motion_text(body.motion)  # free checks first, so a blocked motion costs no AI call
        spend(db, settings)
        motion = check_topic(body.motion, llm, settings.judge_backup_model)
    except DebateError as e:
        raise HTTPException(422, str(e)) from None
    except RateLimited:
        raise HTTPException(503, BUSY) from None
    except LLMError:
        raise HTTPException(502, "The topic check failed. Please try again.") from None
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
    spend(db, settings)
    stream = llm.chat_stream(
        opponent_messages(d), settings.opponent_model, temperature=0.7, max_tokens=700, reasoning={"enabled": False}
    )
    try:
        first = next(stream)  # fail with a normal HTTP error if the model can't even start
    except RateLimited:
        raise HTTPException(503, BUSY) from None
    except LLMError, StopIteration:
        raise HTTPException(502, "The AI couldn't reply. Please try again.") from None

    def events() -> Iterator[str]:
        parts = [first]
        yield sse({"delta": first})
        try:
            for piece in stream:
                parts.append(piece)
                yield sse({"delta": piece})
        except LLMError:
            yield sse({"error": "The AI's reply was cut off. Please try again."})
            return
        # Save only if the debate hasn't moved on meanwhile (two tabs, or a double click).
        with factory() as fresh:
            locked = load(fresh, debate_id, lock=True)
            current = to_debate(locked)
            if len(current.turns) != turns_before or current.whose_turn() != "ai":
                yield sse({"error": "This turn was already taken.", "debate": view(locked)})
                return
            current.add_ai_turn("".join(parts))
            locked.turns = [t.model_dump() for t in current.turns]
            fresh.commit()
            yield sse({"done": True, "debate": view(locked)})

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
    spend(db, settings)
    try:
        res = judge(d.transcript(), llm, settings.judge_model)
    except RateLimited:
        raise HTTPException(503, BUSY) from None
    except LLMError:
        raise HTTPException(502, "The judge couldn't produce a valid scorecard. Please try again.") from None
    locked = load(db, debate_id, lock=True)
    if not locked.scorecard:  # another request may have finished first; keep the first scorecard
        locked.scorecard = res.scorecard.model_dump()
        locked.judge_meta = {
            "version": res.judge_version,
            "model": res.model,
            "dropped_quotes": len(res.dropped_quotes),
            "kept_quotes": res.kept_quotes,
        }
        db.commit()
    return view(locked)


@router.get("/share/{slug}")
def share(slug: str, db: Session = Depends(get_db)) -> dict:
    row = db.execute(select(DebateRow).where(DebateRow.slug == slug)).scalar_one_or_none()
    if row is None or not row.scorecard:
        raise HTTPException(404, "Debate not found.")
    return view(row, include_id=False)
