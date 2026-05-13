from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, Protocol

from pcad.config import Settings


logger = logging.getLogger(__name__)


class EmbeddingClient(Protocol):
    def embed(self, text: str) -> list[float]: ...


class LlmClient(Protocol):
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
    ) -> Iterator[str]: ...


@dataclass
class OpenAICompatibleClient:
    """OpenAI-compatible chat completions and embeddings client."""

    settings: Settings

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

    def _post(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            self._base_url() + endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers=self._headers(),
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            logger.error("llm.request.failed endpoint=%s status=%s", endpoint, exc.code)
            raise RuntimeError(f"OpenAI-compatible HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            logger.error("llm.request.failed endpoint=%s error=%s", endpoint, exc)
            raise RuntimeError(f"OpenAI-compatible request failed: {exc}") from exc

    def embed(self, text: str) -> list[float]:
        payload: dict[str, Any] = {"model": self.settings.embedding_model, "input": text}
        if self.settings.embedding_dimensions:
            payload["dimensions"] = self.settings.embedding_dimensions
        response = self._post("/embeddings", payload)
        try:
            values = response["data"][0]["embedding"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"Unexpected embedding response shape: {response}") from exc
        return [float(value) for value in values]

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
        response = self._post("/chat/completions", payload)
        content = _extract_chat_content(response)
        if not content:
            choice = (response.get("choices") or [{}])[0]
            raise RuntimeError(
                "OpenAI-compatible endpoint returned no assistant text content. "
                f"model={response.get('model')} finish_reason={choice.get('finish_reason')}"
            )
        return content

    def complete_stream(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.1,
        max_tokens: int = 700,
    ) -> Iterator[str]:
        payload = {
            "model": self.settings.llm_model,
            "messages": messages,
            "temperature": temperature,
            "max_completion_tokens": max_tokens,
            "stream": True,
            "reasoning": {"effort": self.settings.llm_reasoning_effort, "exclude": True},
        }
        request = urllib.request.Request(
            self._base_url() + "/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers=self._headers(),
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                for raw_line in response:
                    line = raw_line.decode("utf-8").rstrip("\n").rstrip("\r")
                    if not line.startswith("data: "):
                        continue
                    chunk = line[6:]
                    if chunk == "[DONE]":
                        break
                    try:
                        data = json.loads(chunk)
                    except json.JSONDecodeError:
                        continue
                    delta = (data.get("choices") or [{}])[0].get("delta") or {}
                    text = delta.get("content")
                    if text:
                        yield text
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            logger.error("llm.stream.failed status=%s", exc.code)
            raise RuntimeError(f"OpenAI-compatible HTTP {exc.code}: {detail}") from exc


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
