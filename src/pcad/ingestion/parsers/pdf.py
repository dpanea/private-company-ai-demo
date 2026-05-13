from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from pdf2image import convert_from_path
from pypdf import PdfReader

from pcad.ingestion.ocr import ocr_pdf


@dataclass(frozen=True)
class ParsedPdf:
    page_count: int
    text_per_page: list[str]
    extraction_method: Literal["plain_text", "ocr"]
    rendered_image_paths: list[Path] = field(default_factory=list)


def parse_pdf(
    path: Path,
    ocr_fallback: bool = True,
    *,
    rendered_root: Path | None = None,
    artifact_id: str | None = None,
) -> ParsedPdf:
    """Extract text and optional page renderings from a PDF."""
    reader = PdfReader(path)
    text_per_page = [(page.extract_text() or "").strip() for page in reader.pages]
    extraction_method: Literal["plain_text", "ocr"] = "plain_text"
    if sum(len(text) for text in text_per_page) < 50 and ocr_fallback:
        text_per_page = ocr_pdf(path)
        extraction_method = "ocr"
    rendered_paths = render_pdf_pages(path, rendered_root, artifact_id) if rendered_root else []
    return ParsedPdf(
        page_count=len(reader.pages),
        text_per_page=text_per_page,
        extraction_method=extraction_method,
        rendered_image_paths=rendered_paths,
    )


def render_pdf_pages(path: Path, rendered_root: Path | None, artifact_id: str | None) -> list[Path]:
    if rendered_root is None:
        return []
    target = rendered_root / _safe_path_part(artifact_id or path.stem)
    target.mkdir(parents=True, exist_ok=True)
    images = convert_from_path(path, dpi=150)
    rendered_paths: list[Path] = []
    for index, image in enumerate(images, start=1):
        rendered_path = target / f"page_{index}.png"
        image.save(rendered_path, "PNG")
        rendered_paths.append(rendered_path)
    return rendered_paths


def _safe_path_part(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value)

