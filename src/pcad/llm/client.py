from __future__ import annotations

import json
import logging
import random
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx

from pcad.config import Settings


logger = logging.getLogger(__name__)

_RETRYABLE_STATUS = {408, 425, 429, 500, 502, 503, 504}


@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0


class EmbeddingClient(Protocol):
    def embed(self, text: str) -> list[float]: ...

    def embed_batch(self, texts: list[str]) -> list[list[float]]: ...


class LlmClient(Protocol):
    last_usage: TokenUsage

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.1,
        max_tokens: int = 700,
        response_format: dict[str, Any] | None = None,
    ) -> str: ...

    def complete_stream(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.1,
        max_tokens: int = 700,
        response_format: dict[str, Any] | None = None,
    ) -> Iterator[str]: ...


@dataclass
class OpenAICompatibleClient:
    """OpenAI-compatible chat completions and embeddings client.

    Uses httpx so we get connection pooling, predictable error handling, and
    retries with exponential backoff on transient failures. Records the last
    call's `usage` block on `self.last_usage` for rate limiting / budget code.
    """

    settings: Settings
    last_usage: TokenUsage = field(default_factory=TokenUsage)
    _client: httpx.Client | None = field(default=None, init=False, repr=False)

    def _base_url(self) -> str:
        return getattr(self.settings, "llm_base_url", self.settings.openrouter_base_url).rstrip("/")

    def _api_key(self) -> str | None:
        return getattr(self.settings, "llm_api_key", None) or self.settings.openrouter_api_key

    def _headers(self) -> dict[str, str]:
        api_key = self._api_key()
        if not api_key:
            logger.error("llm.api_key_missing")
            raise RuntimeError("LLM_API_KEY or OPENROUTER_API_KEY is required. Add it to local .env.")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        if self.settings.http_referer:
            headers["HTTP-Referer"] = self.settings.http_referer
        if self.settings.app_title:
            headers["X-Title"] = self.settings.app_title
        return headers

    def _http_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                base_url=self._base_url(),
                timeout=httpx.Timeout(self.settings.llm_timeout_seconds, connect=10.0),
            )
        return self._client

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def _max_retries(self) -> int:
        return max(1, int(self.settings.llm_max_retries))

    def _post_json(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        """POST a JSON body, retrying on retryable HTTP errors."""
        attempts = self._max_retries()
        last_exc: Exception | None = None
        for attempt in range(1, attempts + 1):
            try:
                response = self._http_client().post(endpoint, json=payload, headers=self._headers())
            except httpx.RequestError as exc:
                last_exc = exc
                logger.warning("llm.request.transport_error endpoint=%s attempt=%s error=%s", endpoint, attempt, exc)
                if attempt >= attempts:
                    raise RuntimeError(f"OpenAI-compatible request failed: {exc}") from exc
                _sleep_with_backoff(attempt)
                continue
            if response.status_code in _RETRYABLE_STATUS and attempt < attempts:
                logger.warning("llm.request.retryable_status endpoint=%s attempt=%s status=%s", endpoint, attempt, response.status_code)
                _sleep_with_backoff(attempt, response.headers.get("retry-after"))
                continue
            if response.status_code >= 400:
                logger.error("llm.request.failed endpoint=%s status=%s", endpoint, response.status_code)
                raise RuntimeError(f"OpenAI-compatible HTTP {response.status_code}: {response.text}")
            return response.json()
        # Defensive — loop should always return or raise.
        raise RuntimeError("LLM request retries exhausted") from last_exc

    def embed(self, text: str) -> list[float]:
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        payload: dict[str, Any] = {"model": self.settings.embedding_model, "input": texts}
        if self.settings.embedding_dimensions:
            payload["dimensions"] = self.settings.embedding_dimensions
        response = self._post_json("/embeddings", payload)
        try:
            data = response["data"]
            return [[float(v) for v in item["embedding"]] for item in data]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"Unexpected embedding response shape: {response}") from exc

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.1,
        max_tokens: int = 700,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        payload: dict[str, Any] = {
            "model": self.settings.llm_model,
            "messages": messages,
            "temperature": temperature,
            "max_completion_tokens": max_tokens,
            "reasoning": {"effort": self.settings.llm_reasoning_effort, "exclude": True},
        }
        if response_format is not None:
            payload["response_format"] = response_format
        response = self._post_json("/chat/completions", payload)
        self._record_usage(response.get("usage"))
        content = _extract_chat_content(response)
        if not content:
            choice = (response.get("choices") or [{}])[0]
            raise _no_content_error(self.settings.llm_model, choice.get("finish_reason"), streaming=False)
        return content

    def complete_stream(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.1,
        max_tokens: int = 700,
        response_format: dict[str, Any] | None = None,
    ) -> Iterator[str]:
        payload: dict[str, Any] = {
            "model": self.settings.llm_model,
            "messages": messages,
            "temperature": temperature,
            "max_completion_tokens": max_tokens,
            "stream": True,
            # Some providers only emit usage on the [DONE] frame when this is set.
            "stream_options": {"include_usage": True},
            "reasoning": {"effort": self.settings.llm_reasoning_effort, "exclude": True},
        }
        if response_format is not None:
            payload["response_format"] = response_format
        client = self._http_client()
        emitted_chars = 0
        finish_reason: str | None = None
        try:
            with client.stream("POST", "/chat/completions", json=payload, headers=self._headers()) as response:
                if response.status_code >= 400:
                    body = response.read().decode("utf-8", errors="replace")
                    logger.error("llm.stream.failed status=%s body=%s", response.status_code, body[:500])
                    raise RuntimeError(f"OpenAI-compatible HTTP {response.status_code}: {body}")
                for raw_line in response.iter_lines():
                    if not raw_line:
                        continue
                    line = raw_line if isinstance(raw_line, str) else raw_line.decode("utf-8")
                    if not line.startswith("data: "):
                        continue
                    chunk = line[6:]
                    if chunk == "[DONE]":
                        break
                    try:
                        data = json.loads(chunk)
                    except json.JSONDecodeError:
                        continue
                    if data.get("usage"):
                        self._record_usage(data["usage"])
                    choice = (data.get("choices") or [{}])[0]
                    if choice.get("finish_reason"):
                        finish_reason = choice["finish_reason"]
                    delta = choice.get("delta") or {}
                    text = delta.get("content")
                    if text:
                        emitted_chars += len(text)
                        yield text
        except httpx.RequestError as exc:
            logger.error("llm.stream.transport_error error=%s", exc)
            raise RuntimeError(f"OpenAI-compatible streaming request failed: {exc}") from exc
        if emitted_chars == 0:
            logger.error("llm.stream.empty model=%s finish_reason=%s", self.settings.llm_model, finish_reason)
            raise _no_content_error(self.settings.llm_model, finish_reason, streaming=True)

    def _record_usage(self, usage: dict[str, Any] | None) -> None:
        if not usage:
            return
        self.last_usage = TokenUsage(
            prompt_tokens=int(usage.get("prompt_tokens") or 0),
            completion_tokens=int(usage.get("completion_tokens") or 0),
        )


def _no_content_error(model: str, finish_reason: str | None, *, streaming: bool) -> RuntimeError:
    mode = "streaming" if streaming else "request"
    return RuntimeError(
        f"OpenAI-compatible {mode} returned no assistant text content. "
        f"model={model} finish_reason={finish_reason}"
    )


def _sleep_with_backoff(attempt: int, retry_after: str | None = None) -> None:
    """Exponential backoff with jitter, honoring Retry-After when sane."""
    delay = min(8.0, 0.5 * (2 ** (attempt - 1))) + random.uniform(0.0, 0.25)
    if retry_after:
        try:
            delay = max(delay, float(retry_after))
        except ValueError:
            pass
    time.sleep(delay)


def _extract_chat_content(response: dict[str, Any]) -> str:
    choices = response.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if isinstance(text, str):
                    parts.append(text)
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(part for part in parts if part.strip()).strip()
    return ""
