"""Regression tests for defects found in the fresh review (16 Nov 2026): races and limit bypasses.
Real Postgres test database, fake models, real threads."""

import threading
import time
from concurrent.futures import ThreadPoolExecutor

import httpx
from sqlalchemy import create_engine, text

from app.config import load_settings
from app.debate import TopicCheck
from app.llm import LLMClient, StructuredResult
from tests.test_api import MOTION, TURN, FakeLLM, events, play_full


def db_value(url, sql):
    with create_engine(url).connect() as c:
        return c.execute(text(sql)).scalar()


class SlowJudge(FakeLLM):
    """Each judge call takes a moment and returns a different winner, so an overwrite would be visible."""

    def __init__(self):
        super().__init__()
        self.judge_calls, self.lock = 0, threading.Lock()

    def structured(self, messages, model, schema, **kw):
        if schema is TopicCheck:
            return super().structured(messages, model, schema, **kw)
        with self.lock:
            self.judge_calls += 1
            n = self.judge_calls
        time.sleep(0.4)
        r = super().structured(messages, model, schema, **kw)
        r.data.winner = "pro" if n == 1 else "con"
        return r


def test_overlapping_judge_requests_judge_once_and_keep_one_scorecard(make_client, migrated_db):
    llm = SlowJudge()
    client = make_client(llm)
    debate_id = play_full(client)
    used_before = db_value(migrated_db, "select ai_calls from usage")

    def call(delay):
        time.sleep(delay)
        return client.post(f"/debates/{debate_id}/judge")

    with ThreadPoolExecutor(3) as ex:
        results = list(ex.map(call, [0, 0.1, 0.2]))
    assert sorted(r.status_code for r in results) == [200, 409, 409]
    assert llm.judge_calls == 1
    assert db_value(migrated_db, "select ai_calls from usage") == used_before + 1
    winner = next(r for r in results if r.status_code == 200).json()["scorecard"]["winner"]
    assert client.get(f"/debates/{debate_id}").json()["scorecard"]["winner"] == winner == "pro"
    assert db_value(migrated_db, "select judge_started_at from debates") is None  # claim released


def test_failed_judgment_releases_the_claim_so_retry_works(make_client):
    from app.llm import LLMError

    llm = FakeLLM(judge_error=LLMError("bad json"))
    client = make_client(llm)
    debate_id = play_full(client)
    assert client.post(f"/debates/{debate_id}/judge").status_code == 502
    llm.judge_error = None
    assert client.post(f"/debates/{debate_id}/judge").status_code == 200


class SlowStream(FakeLLM):
    def __init__(self):
        super().__init__()
        self.streams, self.lock = 0, threading.Lock()

    def chat_stream(self, messages, model, **kw):
        with self.lock:
            self.streams += 1
        time.sleep(0.3)
        yield from self.stream


def test_parallel_ai_turn_requests_spend_one_call(make_client, migrated_db):
    llm = SlowStream()
    client = make_client(llm)
    d = client.post("/debates", json={"motion": MOTION, "side": "pro"}).json()
    client.post(f"/debates/{d['id']}/turns", json={"text": TURN})
    used_before = db_value(migrated_db, "select ai_calls from usage")
    with ThreadPoolExecutor(5) as ex:
        results = list(ex.map(lambda _: client.post(f"/debates/{d['id']}/ai-turn"), range(5)))
    assert sorted(r.status_code for r in results) == [200, 409, 409, 409, 409]
    assert llm.streams == 1
    assert db_value(migrated_db, "select ai_calls from usage") == used_before + 1
    assert len(client.get(f"/debates/{d['id']}").json()["turns"]) == 2


def test_cut_off_stream_releases_the_claim_so_retry_works(make_client):
    from app.llm import LLMError

    def broken():
        yield "Half a "
        raise LLMError("the reply was cut off")

    llm = FakeLLM()
    good = llm.chat_stream
    llm.chat_stream = lambda *a, **k: broken()
    client = make_client(llm)
    d = client.post("/debates", json={"motion": MOTION, "side": "pro"}).json()
    client.post(f"/debates/{d['id']}/turns", json={"text": TURN})
    assert "error" in events(client.post(f"/debates/{d['id']}/ai-turn"))[-1]
    llm.chat_stream = good
    assert events(client.post(f"/debates/{d['id']}/ai-turn"))[-1]["done"] is True


def test_rejected_motions_count_against_the_visitor_not_just_the_site(make_client, migrated_db):
    llm = FakeLLM(verdict="not_a_debate_motion")
    client = make_client(llm, debates_per_ip_per_day=2, daily_ai_call_limit=12)
    body = {"motion": "Please write me a poem about cats.", "side": "pro"}
    codes = [client.post("/debates", json=body).status_code for _ in range(6)]
    assert codes == [422, 422, 429, 429, 429, 429]
    assert db_value(migrated_db, "select ai_calls from usage") == 2  # one visitor can't drain the day
    assert client.get("/status").json()["live"] is True


def test_parallel_creates_cannot_pass_the_visitor_limit(make_client, migrated_db):
    class SlowTopic(FakeLLM):
        def structured(self, *a, **k):
            time.sleep(0.3)
            return super().structured(*a, **k)

    client = make_client(SlowTopic(), debates_per_ip_per_day=1)
    with ThreadPoolExecutor(5) as ex:
        codes = sorted(
            ex.map(lambda _: client.post("/debates", json={"motion": MOTION, "side": "pro"}).status_code, range(5))
        )
    assert codes == [201, 429, 429, 429, 429]
    assert db_value(migrated_db, "select count(*) from debates") == 1


def test_busy_model_refunds_the_visitors_attempt(make_client):
    from app.llm import RateLimited

    class Busy(FakeLLM):
        def structured(self, *a, **k):
            raise RateLimited("busy", None)

    llm = Busy()
    client = make_client(llm, debates_per_ip_per_day=1)
    body = {"motion": MOTION, "side": "pro"}
    assert [client.post("/debates", json=body).status_code for _ in range(3)] == [503, 503, 503]  # not 429


def test_retries_and_repairs_are_all_counted(make_client, migrated_db):
    """A real LLMClient over a fake transport: 503, invalid JSON, 503, then valid = 4 provider requests."""
    replies = iter(
        [
            httpx.Response(503, text="down"),
            httpx.Response(200, json={"choices": [{"message": {"content": "not json"}}]}),
            httpx.Response(503, text="down"),
            httpx.Response(200, json={"choices": [{"message": {"content": '{"verdict": "ok"}'}}]}),
        ]
    )
    http = httpx.Client(transport=httpx.MockTransport(lambda request: next(replies)))
    import dataclasses

    llm = LLMClient(dataclasses.replace(load_settings(), openrouter_api_key="t"), http=http, sleep=lambda s: None)
    client = make_client(llm)
    assert client.post("/debates", json={"motion": MOTION, "side": "pro"}).status_code == 201
    assert llm.requests_sent == 4
    assert db_value(migrated_db, "select ai_calls from usage") == 4


def test_forwarded_header_uses_the_proxy_added_entry(make_client):
    client = make_client(FakeLLM(), debates_per_ip_per_day=1, trust_proxy=True)
    body = {"motion": MOTION, "side": "pro"}
    codes = [
        client.post("/debates", json=body, headers={"X-Forwarded-For": f"9.9.9.{i}, 203.0.113.7"}).status_code
        for i in range(3)
    ]
    assert codes == [201, 429, 429]  # a forged first entry doesn't make a new visitor
    assert isinstance(StructuredResult, type)
