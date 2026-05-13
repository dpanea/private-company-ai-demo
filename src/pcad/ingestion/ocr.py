from __future__ import annotations

import logging
from typing import Any

import pytesseract


logger = logging.getLogger(__name__)


def ocr_images(images: list[Any]) -> list[str]:
    """OCR a list of PIL images page by page using Tesseract."""
    text_per_page = [pytesseract.image_to_string(image, lang="eng").strip() for image in images]
    total_chars = sum(len(text) for text in text_per_page)
    logger.info("ocr.pages.done pages=%s chars=%s", len(images), total_chars)
    return text_per_page

