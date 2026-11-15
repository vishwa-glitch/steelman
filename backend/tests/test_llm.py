"""LLM client tests with fake HTTP responses: no network, no free-cap usage."""

import json
from typing import Literal

import httpx
import pytest
from pydantic import BaseModel, ConfigDict

from app.config import Settings
from app.llm import LLMClient, LLMError, RateLimited


class Verdict(BaseModel):
    model_config = ConfigDict(extra="forbid")
    winner: Literal["A", "B"]
    reason: str


SETTINGS = Settings(
    openrouter_api_key="sk-or-test",
    openrouter_base_url="https://example.test/api/v1",
    opponent_model="opp",
    judge_model="judge",
    judge_backup_model="backup",
    request_timeout_s=5,
)


def reply(content: str, model: str = "judge") -> httpx.Response:
    return httpx.Response(200, json={"model": model, "choices": [{"message": {"content": content}}]})


def make_client(responses, max_retries=1):
    """responses: list of httpx.Response or Exception, served in order. Returns (client, sent_payloads, sleeps)."""
    sent, sleeps, queue = [], [], list(responses)

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(json.loads(request.content))
        item = queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    http = httpx.Client(transport=httpx.MockTransport(handler))
    client = LLMClient(SETTINGS, http=http, max_retries=max_retries, sleep=sleeps.append)
    return client, sent, sleeps


MSGS = [{"role": "user", "content": "judge this"}]


def test_valid_json_first_time():
    client, sent, _ = make_client([reply('{"winner": "A", "reason": "evidence"}')])
    r = client.structured(MSGS, "judge", Verdict)
    assert r.data.winner == "A" and not r.repaired and r.attempts == 1
    fmt = sent[0]["response_format"]
    assert fmt["type"] == "json_schema" and fmt["json_schema"]["strict"] is True
    assert fmt["json_schema"]["schema"]["additionalProperties"] is False


def test_invalid_json_is_repaired_once():
    client, sent, _ = make_client([reply("Sure! Winner is A"), reply('{"winner": "B", "reason": "x"}')])
    r = client.structured(MSGS, "judge", Verdict)
    assert r.data.winner == "B" and r.repaired and len(sent) == 2
    # the repair request carries the bad reply and the error back to the model
    assert sent[1]["messages"][-2] == {"role": "assistant", "content": "Sure! Winner is A"}
    assert "not valid" in sent[1]["messages"][-1]["content"]


def test_schema_mismatch_twice_raises():
    client, sent, _ = make_client([reply('{"winner": "C", "reason": "x"}'), reply('{"winner": "C"}')])
    with pytest.raises(LLMError, match="schema"):
        client.structured(MSGS, "judge", Verdict)
    assert len(sent) == 2  # exactly one repair attempt, no more


def test_code_fences_are_tolerated():
    client, _, _ = make_client([reply('```json\n{"winner": "A", "reason": "r"}\n```')])
    assert client.structured(MSGS, "judge", Verdict).data.winner == "A"


def test_server_error_is_retried_then_succeeds():
    client, sent, sleeps = make_client([httpx.Response(502, text="bad gateway"), reply("hello", "opp")])
    r = client.chat(MSGS, "opp")
    assert r.text == "hello" and r.attempts == 2 and len(sent) == 2 and sleeps == [2]


def test_timeout_retries_then_fails():
    client, sent, _ = make_client([httpx.ReadTimeout("slow"), httpx.ReadTimeout("slow")])
    with pytest.raises(LLMError, match="timed out"):
        client.chat(MSGS, "opp")
    assert len(sent) == 2


def test_429_without_retry_after_stops_immediately():
    client, sent, sleeps = make_client([httpx.Response(429, text="daily limit")])
    with pytest.raises(RateLimited) as e:
        client.chat(MSGS, "opp")
    assert e.value.retry_after is None and len(sent) == 1 and sleeps == []


def test_429_with_short_retry_after_waits_then_retries():
    client, sent, sleeps = make_client([httpx.Response(429, headers={"Retry-After": "3"}), reply("ok", "opp")])
    assert client.chat(MSGS, "opp").text == "ok"
    assert sleeps == [3.0] and len(sent) == 2


def test_200_with_error_body_is_retried():
    client, sent, _ = make_client([httpx.Response(200, json={"error": {"code": 502}}), reply("ok", "opp")])
    assert client.chat(MSGS, "opp").text == "ok" and len(sent) == 2


def test_client_error_is_not_retried():
    client, sent, _ = make_client([httpx.Response(400, text="bad model")])
    with pytest.raises(LLMError, match="HTTP 400"):
        client.chat(MSGS, "opp")
    assert len(sent) == 1


def test_missing_key_is_reported():
    no_key = Settings(**{**SETTINGS.__dict__, "openrouter_api_key": ""})
    with pytest.raises(LLMError, match="OPENROUTER_API_KEY"):
        LLMClient(no_key, http=httpx.Client())


def test_reasoning_setting_is_sent_when_given():
    client, sent, _ = make_client([reply('{"winner": "A", "reason": "r"}')])
    client.structured(MSGS, "judge", Verdict, reasoning={"effort": "low"})
    assert sent[0]["reasoning"] == {"effort": "low"}


def test_reasoning_setting_is_omitted_by_default():
    client, sent, _ = make_client([reply("hi", "opp")])
    client.chat(MSGS, "opp")
    assert "reasoning" not in sent[0]


def test_empty_answer_after_hitting_token_limit_says_so():
    from app.llm import OutOfTokens

    body = {
        "model": "judge",
        "choices": [{"finish_reason": "length", "message": {"content": "", "reasoning": "thinking..."}}],
        "usage": {"completion_tokens_details": {"reasoning_tokens": 2500}},
    }
    client, sent, _ = make_client([httpx.Response(200, json=body)])
    with pytest.raises(OutOfTokens, match="reasoning tokens=2500"):
        client.structured(MSGS, "judge", Verdict)
    assert len(sent) == 1  # not "repaired": a repair would hit the same limit
