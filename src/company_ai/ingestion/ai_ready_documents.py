from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable
from datetime import datetime, timezone

from company_ai.models import Account, RagDocument, RawArtifact, SourceCitation, SyntheticDataset
from company_ai.util import safe_id


_MARKDOWN_HEADING_RE = re.compile(r"^(#{1,3})\s+(.+)$")
_PARAGRAPH_SPLIT_RE = re.compile(r"\n{2,}")
_TRANSCRIPT_TURN_SPLIT_RE = re.compile(r"\n(?=(?:\*\*)?[A-Z][^:\n]{1,50}:(?:\*\*)?)")


ARTIFACT_SOURCE_OBJECTS = {
    "email": "Email",
    "pdf": "PDF",
    "docx": "WordDocument",
    "meeting_transcript": "Meeting",
}


def stable_hash(parts: Iterable[str]) -> str:
    return "sha256:" + hashlib.sha256("\n".join(part for part in parts if part).encode("utf-8")).hexdigest()


class DocumentBuilder:
    def __init__(
        self,
        dataset: SyntheticDataset,
        *,
        raw_artifacts: list[RawArtifact] | None = None,
    ) -> None:
        self.dataset = dataset
        self.accounts = {a.account_id: a for a in dataset.accounts}
        self.raw_artifacts = raw_artifacts or dataset.raw_artifacts
        self.raw_artifacts_by_account: dict[str, list[RawArtifact]] = {}
        for artifact in self.raw_artifacts:
            if artifact.account_id:
                self.raw_artifacts_by_account.setdefault(artifact.account_id, []).append(artifact)

    def build_all(self) -> list[RagDocument]:
        docs: list[RagDocument] = []
        for account in self.dataset.accounts:
            for artifact in self.raw_artifacts_by_account.get(account.account_id, []):
                docs.extend(self._artifact_chunks(account, artifact))
        return docs

    def _artifact_chunks(self, account: Account, artifact: RawArtifact) -> list[RagDocument]:
        source_object = ARTIFACT_SOURCE_OBJECTS.get(artifact.artifact_type)
        if not source_object:
            return []
        record_id = artifact.artifact_id.rsplit(":", 1)[-1]
        title = artifact.title or artifact.artifact_id
        chunks: list[RagDocument] = []
        for index, (chunk_label, chunk_text) in enumerate(_artifact_segments(artifact), start=1):
            if not chunk_text.strip():
                continue
            doc_id = f"source_artifact_chunk:{artifact.artifact_id}:{safe_id(chunk_label or str(index))}"
            content = (
                f"# Source artifact: {title}\n\n"
                f"## Artifact metadata\n"
                f"- Account: {account.account_name}\n"
                f"- Artifact type: {artifact.artifact_type}\n"
                f"- Segment: {chunk_label}\n\n"
                f"## Extracted text\n{chunk_text.strip()}\n"
            )
            citation = SourceCitation(
                citation_id=f"{doc_id}:{source_object}:{record_id}",
                doc_id=doc_id,
                source_object=source_object,
                source_record_id=record_id,
                title=title,
                source_date=artifact.created_at.date() if artifact.created_at else None,
                owner_id=account.owner_id,
                excerpt=excerpt(chunk_text),
            )
            metadata = {
                "doc_type": "source_artifact_chunk",
                "source_system": "synthetic",
                "source_objects": [source_object],
                "account_id": account.account_id,
                "account_name": account.account_name,
                "owner_id": account.owner_id,
                "visibility_scope": ["public_demo"],
                "source_artifact_id": artifact.artifact_id,
                "source_artifact_type": artifact.artifact_type,
                "chunk_label": chunk_label,
            }
            chunks.append(
                RagDocument(
                    doc_id=doc_id,
                    doc_type="source_artifact_chunk",
                    title=f"{title} ({chunk_label})",
                    content_markdown=content,
                    metadata_json=metadata,
                    source_record_ids=[artifact.artifact_id],
                    source_record_hashes=[stable_hash([artifact.artifact_id, chunk_text])],
                    account_id=account.account_id,
                    owner_id=account.owner_id,
                    last_source_updated_at=artifact.created_at,
                    generated_at=datetime.now(timezone.utc),
                    source_hash=stable_hash([artifact.artifact_id, content]),
                    citations=[citation],
                )
            )
        return chunks


def _artifact_segments(artifact: RawArtifact) -> list[tuple[str, str]]:
    text = artifact.extracted_text.strip()
    if artifact.artifact_type == "pdf":
        pages = artifact.metadata.get("text_per_page")
        if isinstance(pages, list) and pages:
            return [(f"page {index}", str(page).strip()) for index, page in enumerate(pages, start=1) if str(page).strip()]
        return [("document", text)]
    if artifact.artifact_type == "docx":
        return _markdown_sections(text)
    if artifact.artifact_type == "meeting_transcript":
        return _turn_groups(text)
    return [("message", text)]


def _markdown_sections(text: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, list[str]]] = []
    current_title = "document"
    current_lines: list[str] = []
    for block in _PARAGRAPH_SPLIT_RE.split(text.strip()):
        stripped = block.strip()
        if not stripped:
            continue
        heading = _MARKDOWN_HEADING_RE.match(stripped)
        if heading and current_lines:
            sections.append((current_title, current_lines))
            current_title = heading.group(2).strip()
            current_lines = [stripped]
            continue
        if heading:
            current_title = heading.group(2).strip()
        current_lines.append(stripped)
    if current_lines:
        sections.append((current_title, current_lines))
    return [(title, "\n\n".join(lines)) for title, lines in sections] or [("document", text)]


def _turn_groups(text: str, group_size: int = 6) -> list[tuple[str, str]]:
    turns = _TRANSCRIPT_TURN_SPLIT_RE.split(text.strip())
    turns = [turn.strip() for turn in turns if turn.strip()]
    if len(turns) <= group_size:
        return [("transcript", text.strip())]
    groups: list[tuple[str, str]] = []
    for start in range(0, len(turns), group_size):
        index = (start // group_size) + 1
        groups.append((f"turn group {index}", "\n".join(turns[start : start + group_size])))
    return groups


def excerpt(text: str, limit: int = 300) -> str:
    compact = " ".join(text.split())
    return compact if len(compact) <= limit else compact[: limit - 3].rstrip() + "..."
