from __future__ import annotations

import logging

import psycopg
from psycopg.rows import dict_row

from pcad.config import Settings
from pcad.llm.client import OpenAICompatibleClient


logger = logging.getLogger(__name__)

EMBED_BATCH_SIZE = 32


def index_pending_embeddings(settings: Settings, *, batch_limit: int | None = None) -> int:
    """Embed every rag_documents row with a NULL embedding, in batches."""
    if not settings.openrouter_api_key:
        logger.warning("embedding_index.skipped reason=openrouter_api_key_missing")
        return 0
    client = OpenAICompatibleClient(settings)
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
        for start in range(0, len(rows), EMBED_BATCH_SIZE):
            batch = rows[start : start + EMBED_BATCH_SIZE]
            texts = [_document_embedding_text(row["title"], row["content_markdown"]) for row in batch]
            vectors = client.embed_batch(texts)
            conn.cursor().executemany(
                "UPDATE rag_documents SET embedding = %s::vector WHERE doc_id = %s",
                [(_vector_literal(vector), row["doc_id"]) for row, vector in zip(batch, vectors)],
            )
        conn.commit()
    logger.info("embedding_index indexed=%s", len(rows))
    return len(rows)


def _document_embedding_text(title: str, content: str) -> str:
    return f"{title}\n\n{content}"


def _vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in values) + "]"
