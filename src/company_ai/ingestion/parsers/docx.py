from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from docx import Document


@dataclass(frozen=True)
class ParsedDocx:
    paragraph_count: int
    text: str


def parse_docx(path: Path) -> ParsedDocx:
    """Extract paragraph text from a .docx file."""
    document = Document(path)
    rendered: list[str] = []
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if not text:
            continue
        style_name = paragraph.style.name if paragraph.style is not None else ""
        prefix = _heading_prefix(style_name)
        rendered.append(f"{prefix}{text}")
    return ParsedDocx(paragraph_count=len(rendered), text="\n\n".join(rendered))


def _heading_prefix(style_name: str) -> str:
    normalized = style_name.casefold()
    if normalized == "title":
        return "# "
    if normalized == "subtitle":
        return "## "
    if normalized == "heading 1":
        return "# "
    if normalized == "heading 2":
        return "## "
    if normalized == "heading 3":
        return "### "
    return ""
