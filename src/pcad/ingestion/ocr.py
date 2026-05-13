from __future__ import annotations

import logging
from pathlib import Path

import pytesseract
from pdf2image import convert_from_path


logger = logging.getLogger(__name__)


def ocr_pdf(path: Path) -> list[str]:
    """OCR a PDF page by page using Tesseract."""
    pages = convert_from_path(path, dpi=200)
    text_per_page = [pytesseract.image_to_string(page, lang="eng").strip() for page in pages]
    total_chars = sum(len(text) for text in text_per_page)
    logger.info("ocr.pdf.done path=%s pages=%s chars=%s", path, len(pages), total_chars)
    return text_per_page

