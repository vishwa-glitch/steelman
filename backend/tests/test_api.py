"""API tests: real Postgres test database, fake models."""

import json
import uuid

from app.debate import TopicCheck
from app.judge import CRITERIA, Scorecard
from app.llm import LLMError, RateLimited, StructuredResult

TURN = "This is a perfectly reasonable debate turn with enough words in it."
MOTION = "Zoos should be closed."


class FakeLLM:
    def __init__(
        self,
        verdict="ok",
        stream=("AI ", "reply ", "about zoos and why they matter."),
        judge_error=None,
        stream_error=None,
    ):
        self.verdict, self.stream, self.judge_error, self.stream_error = verdict, stream, judge_error, stream_error
        self.calls = []

    def structured(self, messages, model, schema, **kw):
        self.calls.append(schema.__name__)
        if schema is TopicCheck:
            data = TopicCheck(verdict=self.verdict)
        else:
            if self.judge_error:
                raise self.judge_error

            def side(n, s, q):
                return {
                    "side": n,
                    "scores": [{"criterion": c, "score": s, "quotes": q, "reason": "r"} for c in CRITERIA],
                }

            data = Scorecard.model_validate(
                {
                    "sides": [side("pro", 8, [TURN]), side("con", 5, ["made up quote here"])],
                    "winner": "pro",
                    "summary": "s",
                }
            )
        return StructuredResult(data=data, raw_text="{}", model=model, latency_s=0.1, attempts=1, repaired=False)

    def chat_stream(self, messages, model, **kw):
        self.calls.append("stream")
        if self.stream_error:
            raise self.stream_error
        yield from self.stream


def events(res):
    return [json.loads(line[6:]) for line in res.text.splitlines() if line.startswith("data: ")]


def play_full(client):
    d = client.post("/debates", json={"motion": MOTION, "side": "pro"}).json()
    for _ in range(3):
        assert client.post(f"/debates/{d['id']}/turns", json={"text": TURN}).status_code == 200
        ev = events(client.post(f"/debates/{d['id']}/ai-turn"))
        assert ev[-1]["done"] is True
    return d["id"]


def test_full_flow_create_turns_judge_share(make_client):
    llm = FakeLLM()
    client = make_client(llm)
    res = client.post("/debates", json={"motion": f"  {MOTION} ", "side": "pro"})
    assert res.status_code == 201
    d = res.json()
    assert d["motion"] == MOTION and d["next"] == {"side": "pro", "round": "opening", "who": "user"}
    assert d["share_slug"] is None and d["scorecard"] is None

    d = client.post(f"/debates/{d['id']}/turns", json={"text": TURN}).json()
    assert d["next"]["who"] == "ai"
    ev = events(client.post(f"/debates/{d['id']}/ai-turn"))
    assert [e["delta"] for e in ev[:-1]] == list(llm.stream)
    assert ev[-1]["debate"]["turns"][1] == {"side": "con", "round": "opening", "text": "".join(llm.stream).strip()}

    debate_id = d["id"]
    for _ in range(2):
        client.post(f"/debates/{debate_id}/turns", json={"text": TURN})
        client.post(f"/debates/{debate_id}/ai-turn")
    state = client.get(f"/debates/{debate_id}").json()
    assert state["finished"] and state["next"] is None and len(state["turns"]) == 6

    judged = client.post(f"/debates/{debate_id}/judge").json()
    assert judged["scorecard"]["winner"] == "pro" and judged["share_slug"]
    assert judged["judge"]["dropped_quotes"] == 4 and judged["judge"]["kept_quotes"] == 4  # invented quotes removed
    again = client.post(f"/debates/{debate_id}/judge").json()
    assert again["scorecard"] == judged["scorecard"] and llm.calls.count("Scorecard") == 1  # judged once only

    shared = client.get(f"/share/{judged['share_slug']}")
    assert shared.status_code == 200 and "id" not in shared.json() and shared.json()["scorecard"]["winner"] == "pro"


def test_share_needs_the_exact_slug_and_a_judged_debate(make_client):
    client = make_client(FakeLLM())
    assert client.get("/share/not-a-real-slug").status_code == 404
    debate_id = play_full(client)
    # an unjudged debate has no share link, and its id does not work as a slug
    assert client.get(f"/debates/{debate_id}").json()["share_slug"] is None
    assert client.get(f"/share/{debate_id}").status_code == 404


def test_unknown_or_malformed_debate_id(make_client):
    client = make_client(FakeLLM())
    assert client.get(f"/debates/{uuid.uuid4()}").status_code == 404
    assert client.get("/debates/123").status_code == 422
    assert client.post(f"/debates/{uuid.uuid4()}/turns", json={"text": TURN}).status_code == 404


def test_turn_order_and_length_are_enforced(make_client):
    client = make_client(FakeLLM())
    d = client.post("/debates", json={"motion": MOTION, "side": "pro"}).json()
    assert client.post(f"/debates/{d['id']}/ai-turn").status_code == 409  # AI can't go first when user is pro
    assert client.post(f"/debates/{d['id']}/turns", json={"text": "short"}).status_code == 422
    assert client.post(f"/debates/{d['id']}/turns", json={"text": TURN}).status_code == 200
    assert client.post(f"/debates/{d['id']}/turns", json={"text": TURN}).status_code == 409  # twice in a row
    assert client.post(f"/debates/{d['id']}/judge").status_code == 409  # not finished
    assert len(client.get(f"/debates/{d['id']}").json()["turns"]) == 1


def test_blocked_motions(make_client):
    llm = FakeLLM()
    client = make_client(llm)
    res = client.post("/debates", json={"motion": "The caste system is good.", "side": "pro"})
    assert res.status_code == 422 and llm.calls == []  # word list: no AI call spent
    client = make_client(FakeLLM(verdict="religion_or_partisan_politics"))
    assert client.post("/debates", json={"motion": "The ruling party should win.", "side": "pro"}).status_code == 422
    assert client.post("/debates", json={"motion": MOTION, "side": "sideways"}).status_code == 422


def test_per_visitor_limit_returns_429(make_client):
    client = make_client(FakeLLM(), debates_per_ip_per_day=2)
    body = {"motion": MOTION, "side": "pro"}
    assert [client.post("/debates", json=body).status_code for _ in range(3)] == [201, 201, 429]


def test_daily_ai_limit_returns_503_and_status_reports_it(make_client):
    client = make_client(FakeLLM(), daily_ai_call_limit=6)
    assert client.get("/status").json() == {"live": True, "message": None}
    d = client.post("/debates", json={"motion": MOTION, "side": "pro"}).json()  # 1 call
    assert client.get("/status").json()["live"] is True  # 5 left: one debate can still finish
    client.post(f"/debates/{d['id']}/turns", json={"text": TURN})
    client.post(f"/debates/{d['id']}/ai-turn")  # 2
    assert client.get("/status").json()["live"] is False
    for _ in range(2):
        client.post(f"/debates/{d['id']}/turns", json={"text": TURN})
        client.post(f"/debates/{d['id']}/ai-turn")  # 3, 4
    assert client.post(f"/debates/{d['id']}/judge").status_code == 200  # 5
    assert client.post("/debates", json={"motion": MOTION, "side": "pro"}).status_code == 201  # 6
    res = client.post("/debates", json={"motion": MOTION, "side": "pro"})
    assert res.status_code == 503 and "resting" in res.json()["detail"]


def test_model_failures_map_to_clean_errors_and_do_not_corrupt_state(make_client):
    client = make_client(FakeLLM(stream_error=RateLimited("busy", None)))
    d = client.post("/debates", json={"motion": MOTION, "side": "pro"}).json()
    client.post(f"/debates/{d['id']}/turns", json={"text": TURN})
    assert client.post(f"/debates/{d['id']}/ai-turn").status_code == 503
    assert len(client.get(f"/debates/{d['id']}").json()["turns"]) == 1  # still the AI's turn; can retry

    client = make_client(FakeLLM(judge_error=LLMError("bad json")))
    debate_id = play_full(client)
    assert client.post(f"/debates/{debate_id}/judge").status_code == 502
    assert client.get(f"/debates/{debate_id}").json()["scorecard"] is None


def test_stream_cut_off_midway_saves_nothing(make_client):
    def broken():
        yield "Half a "
        raise LLMError("network error")

    llm = FakeLLM()
    llm.chat_stream = lambda *a, **k: broken()
    client = make_client(llm)
    d = client.post("/debates", json={"motion": MOTION, "side": "pro"}).json()
    client.post(f"/debates/{d['id']}/turns", json={"text": TURN})
    ev = events(client.post(f"/debates/{d['id']}/ai-turn"))
    assert ev[0] == {"delta": "Half a "} and "error" in ev[-1]
    assert len(client.get(f"/debates/{d['id']}").json()["turns"]) == 1


def test_ip_is_stored_only_as_a_hash(make_client, migrated_db):
    from sqlalchemy import create_engine, text

    client = make_client(FakeLLM())
    client.post("/debates", json={"motion": MOTION, "side": "pro"})
    with create_engine(migrated_db).connect() as c:
        stored = c.execute(text("select client_hash from debates")).scalar()
    assert len(stored) == 64 and "testclient" not in stored
