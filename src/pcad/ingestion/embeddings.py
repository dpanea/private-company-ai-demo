from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any

import psycopg
from psycopg.rows import dict_row

from pcad.config import Settings


logger = logging.getLogger(__name__)


def index_pending_embeddings(settings: Settings, *, batch_limit: int | None = None) -> int:
    """Embed every rag_documents row with a NULL embedding."""
    if not settings.openrouter_api_key:
        logger.warning("embedding_index.skipped reason=openrouter_api_key_missing")
        return 0
    client = OpenRouterEmbeddingClient(settings)
    with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
        rows = conn.execute(
            """
            SELECT doc_id, title, content_markdown
            FROM rag_documents
            WHERE embedding IS NULL
            ORDER BY doc_id
            LIMIT %s
            """,
            (batch_limit,),
        ).fetchall()
        for row in rows:
            embedding = client.embed(_document_embedding_text(row["title"], row["content_markdown"]))
            conn.execute(
                "UPDATE rag_documents SET embedding = %s::vector WHERE doc_id = %s",
                (_vector_literal(embedding), row["doc_id"]),
            )
        conn.commit()
    logger.info("embedding_index indexed=%s", len(rows))
    return len(rows)


class OpenRouterEmbeddingClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def embed(self, text: str) -> list[float]:
        payload = json.dumps({"model": self.settings.embedding_model, "input": text}).encode("utf-8")
        request = urllib.request.Request(
            self.settings.openrouter_base_url.rstrip("/") + "/embeddings",
            data=payload,
            headers=self._headers(),
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Embedding request failed: {exc}") from exc
        return _extract_embedding(body)

    def _headers(self) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.settings.openrouter_api_key}",
            "Content-Type": "application/json",
        }
        if self.settings.http_referer:
            headers["HTTP-Referer"] = self.settings.http_referer
        headers["X-Title"] = self.settings.app_title
        return headers


def _extract_embedding(body: dict[str, Any]) -> list[float]:
    try:
        values = body["data"][0]["embedding"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Unexpected embedding response shape: {body}") from exc
    return [float(value) for value in values]


def _document_embedding_text(title: str, content: str) -> str:
    return f"{title}\n\n{content}"


def _vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in values) + "]"

