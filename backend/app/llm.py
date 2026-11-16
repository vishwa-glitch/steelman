"""OpenRouter client: plain chat, and structured (JSON-schema) output with validation and one repair attempt.

Free models allow 50 requests a day per account, so retries are deliberately few: every attempt counts.
"""

import json
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

import httpx
from pydantic import BaseModel, ValidationError

from app.config import Settings, load_settings

RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}


class LLMError(Exception):
    """The model call failed after retries, or returned output we could not use."""


class OutOfTokens(LLMError):
    """The model hit max_tokens before giving an answer, typically by spending them all on reasoning."""


class RateLimited(LLMError):
    """429 from OpenRouter. retry_after is in seconds when the server said so."""

    def __init__(self, message: str, retry_after: float | None):
        super().__init__(message)
        self.retry_after = retry_after


@dataclass
class CallResult:
    text: str
    model: str
    latency_s: float
    attempts: int
    usage: dict[str, Any] = field(default_factory=dict)


@dataclass
class StructuredResult:
    data: BaseModel
    raw_text: str
    model: str
    latency_s: float
    attempts: int
    repaired: bool


class LLMClient:
    def __init__(
        self,
        settings: Settings | None = None,
        http: httpx.Client | None = None,
        max_retries: int = 1,
        sleep=time.sleep,
    ):
        self.settings = settings or load_settings()
        if not self.settings.openrouter_api_key:
            raise LLMError("OPENROUTER_API_KEY is not set (see backend/.env.example)")
        self.http = http or httpx.Client(timeout=self.settings.request_timeout_s)
        self.max_retries = max_retries
        self.sleep = sleep
        self.requests_sent = 0  # every HTTP request to the provider, including retries and repairs

    def _post(self, payload: dict[str, Any]) -> tuple[dict[str, Any], int]:
        """POST to chat/completions, retrying transient failures. Returns (json, attempts)."""
        url = f"{self.settings.openrouter_base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.settings.openrouter_api_key}",
            "X-Title": "Steelman",
        }
        last_error = "unknown error"
        for attempt in range(1, self.max_retries + 2):
            self.requests_sent += 1
            try:
                res = self.http.post(url, json=payload, headers=headers)
            except httpx.TimeoutException:
                last_error = "timed out"
            except httpx.HTTPError as e:
                last_error = f"network error: {e}"
            else:
                if res.status_code == 200:
                    body = res.json()
                    if "error" in body:  # OpenRouter can return 200 with an error body
                        last_error = f"provider error: {body['error']}"
                    else:
                        return body, attempt
                elif res.status_code == 429:
                    retry_after = _retry_after_seconds(res)
                    # Daily cap or long waits: don't burn more requests, let the caller decide.
                    if retry_after is None or retry_after > 60 or attempt > self.max_retries:
                        raise RateLimited(f"rate limited: {res.text[:300]}", retry_after)
                    self.sleep(retry_after)
                    continue
                elif res.status_code in RETRYABLE_STATUS:
                    last_error = f"HTTP {res.status_code}: {res.text[:300]}"
                else:
                    raise LLMError(f"HTTP {res.status_code}: {res.text[:300]}")
            if attempt <= self.max_retries:
                self.sleep(2**attempt)
        raise LLMError(f"failed after {self.max_retries + 1} attempts: {last_error}")

    def chat(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 800,
        reasoning: dict[str, Any] | None = None,
    ) -> CallResult:
        start = time.monotonic()
        payload = {"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
        if reasoning is not None:
            payload["reasoning"] = reasoning
        body, attempts = self._post(payload)
        return CallResult(
            text=_message_text(body),
            model=body.get("model", model),
            latency_s=time.monotonic() - start,
            attempts=attempts,
            usage=body.get("usage") or {},
        )

    def chat_stream(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 800,
        reasoning: dict[str, Any] | None = None,
    ) -> Iterator[str]:
        """Yield the reply piece by piece. No retries: a retry mid-stream would repeat text already shown."""
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        if reasoning is not None:
            payload["reasoning"] = reasoning
        headers = {"Authorization": f"Bearer {self.settings.openrouter_api_key}", "X-Title": "Steelman"}
        url = f"{self.settings.openrouter_base_url}/chat/completions"
        got_text = False
        finished = False  # the provider said the reply is complete ([DONE] or a finish_reason)
        self.requests_sent += 1
        try:
            with self.http.stream("POST", url, json=payload, headers=headers) as res:
                if res.status_code != 200:
                    body = res.read().decode("utf8", "ignore")[:300]
                    if res.status_code == 429:
                        raise RateLimited(f"rate limited: {body}", _retry_after_seconds(res))
                    raise LLMError(f"HTTP {res.status_code}: {body}")
                for line in res.iter_lines():
                    if not line.startswith("data: "):
                        continue  # blank lines and ": keep-alive" comments
                    data = line[len("data: ") :]
                    if data.strip() == "[DONE]":
                        finished = True
                        break
                    try:
                        chunk = json.loads(data)
                    except json.JSONDecodeError as e:
                        raise LLMError("the stream contained a malformed event") from e
                    if "error" in chunk:
                        raise LLMError(f"provider error: {str(chunk['error'])[:300]}")
                    choices = chunk.get("choices") or []
                    delta = (choices[0].get("delta") or {}).get("content") if choices else None
                    if choices and choices[0].get("finish_reason"):
                        finished = True
                    if delta:
                        got_text = True
                        yield delta
        except httpx.TimeoutException as e:
            raise LLMError("timed out") from e
        except httpx.HTTPError as e:
            raise LLMError(f"network error: {e}") from e
        if not got_text:
            raise LLMError("model returned an empty message")
        if not finished:  # the connection closed mid-reply: don't pass half a sentence off as a whole turn
            raise LLMError("the reply was cut off")

    def structured(
        self,
        messages: list[dict[str, str]],
        model: str,
        schema: type[BaseModel],
        temperature: float = 0.2,
        max_tokens: int = 1500,
        reasoning: dict[str, Any] | None = None,
    ) -> StructuredResult:
        """Ask for JSON matching `schema`. If it doesn't validate, send the error back once and ask for a fix."""
        start = time.monotonic()
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema.__name__,
                    "strict": True,
                    "schema": schema.model_json_schema(),
                },
            },
        }
        if reasoning is not None:  # e.g. {"effort": "low"} or {"enabled": False}; see OpenRouter docs
            payload["reasoning"] = reasoning
        body, attempts = self._post(payload)
        text = _message_text(body)
        try:
            data = _parse(text, schema)
            repaired = False
        except LLMError as first_error:
            repair_messages = [
                *messages,
                {"role": "assistant", "content": text},
                {
                    "role": "user",
                    "content": f"That reply was not valid: {first_error}. Reply again with only the JSON object "
                    "that matches the schema. No prose, no code fences.",
                },
            ]
            body, more = self._post({**payload, "messages": repair_messages})
            attempts += more
            text = _message_text(body)
            data = _parse(text, schema)  # a second failure propagates as LLMError
            repaired = True
        return StructuredResult(
            data=data,
            raw_text=text,
            model=body.get("model", model),
            latency_s=time.monotonic() - start,
            attempts=attempts,
            repaired=repaired,
        )


def _message_text(body: dict[str, Any]) -> str:
    try:
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise LLMError(f"unexpected response shape: {str(body)[:300]}") from e
    if not isinstance(content, str) or not content.strip():
        choice = body["choices"][0]
        if choice.get("finish_reason") == "length":
            used = ((body.get("usage") or {}).get("completion_tokens_details") or {}).get("reasoning_tokens")
            raise OutOfTokens(f"ran out of tokens before answering (finish_reason=length, reasoning tokens={used})")
        raise LLMError("model returned an empty message")
    return content


def _parse(text: str, schema: type[BaseModel]) -> BaseModel:
    cleaned = text.strip()
    if cleaned.startswith("```"):  # tolerate code fences, which some models add anyway
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else ""
        cleaned = cleaned.rsplit("```", 1)[0]
    try:
        return schema.model_validate(json.loads(cleaned))
    except json.JSONDecodeError as e:
        raise LLMError(f"not valid JSON ({e.msg} at position {e.pos})") from e
    except ValidationError as e:
        raise LLMError(f"JSON did not match the schema: {e.errors()[:3]}") from e


def _retry_after_seconds(res: httpx.Response) -> float | None:
    value = res.headers.get("retry-after")
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None
