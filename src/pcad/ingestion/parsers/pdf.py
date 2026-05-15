from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from pdf2image import convert_from_path
from pypdf import PdfReader

from pcad.ingestion.ocr import ocr_images


RENDER_DPI = 200  # high enough for both readable PNG display and Tesseract OCR
PAGE_TEXT_MIN_CHARS = 40  # a page with fewer printable chars is treated as text-less


@dataclass(frozen=True)
class ParsedPdf:
    page_count: int
    text_per_page: list[str]
    extraction_method: Literal["plain_text", "ocr"]
    rendered_image_paths: list[Path] = field(default_factory=list)
    ocr_page_indices: list[int] = field(default_factory=list)


def parse_pdf(
    path: Path,
    ocr_fallback: bool = True,
    *,
    rendered_root: Path | None = None,
    artifact_id: str | None = None,
) -> ParsedPdf:
    """Extract text from a PDF and optionally save page renderings.

    Each page is checked independently. Pages without a usable text layer fall
    back to OCR, while pages that already have text are kept verbatim. This
    avoids running OCR on a long PDF just because one page is image-only.
    """
    reader = PdfReader(path)
    text_per_page = [(page.extract_text() or "").strip() for page in reader.pages]
    ocr_targets = [
        index
        for index, text in enumerate(text_per_page)
        if len(text) < PAGE_TEXT_MIN_CHARS
    ]
    needs_ocr = ocr_fallback and bool(ocr_targets)
    rendered_paths: list[Path] = []
    extraction_method: Literal["plain_text", "ocr"] = "plain_text"
    applied_ocr_targets: list[int] = []

    if needs_ocr or rendered_root is not None:
        images = convert_from_path(path, dpi=RENDER_DPI)
        if needs_ocr:
            ocr_subset = [images[index] for index in ocr_targets]
            ocr_pages = ocr_images(ocr_subset)
            for index, ocr_text in zip(ocr_targets, ocr_pages):
                text_per_page[index] = ocr_text
            applied_ocr_targets = list(ocr_targets)
            extraction_method = "ocr"
        if rendered_root is not None:
            rendered_paths = _save_pages(images, rendered_root, artifact_id or path.stem)

    return ParsedPdf(
        page_count=len(reader.pages),
        text_per_page=text_per_page,
        extraction_method=extraction_method,
        rendered_image_paths=rendered_paths,
        ocr_page_indices=applied_ocr_targets,
    )


def _save_pages(images: list, rendered_root: Path, artifact_id: str) -> list[Path]:
    target = rendered_root / _safe_path_part(artifact_id)
    target.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for index, image in enumerate(images, start=1):
        out = target / f"page_{index}.png"
        image.save(out, "PNG")
        paths.append(out)
    return paths


def _safe_path_part(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value)

