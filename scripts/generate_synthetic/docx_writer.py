from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor

from .accounts import DocxSpec

FIXED_DOCX_TIME = (2026, 1, 1, 0, 0, 0)


def write_docx(path: Path, spec: DocxSpec) -> None:
    """Render a synthetic Word document that actually looks like a Word document.

    We use the built-in Title and Subtitle styles for a recognisable cover block,
    Heading 1 for sections, and explicit body sizing so the rendered page does
    not collapse into one undifferentiated wall of text.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    document = Document()
    props = document.core_properties
    fixed = datetime(2026, 1, 1, tzinfo=timezone.utc)
    props.author = "Daniel Panea Lichtig"
    props.title = spec.title
    props.subject = spec.subtitle
    props.created = fixed
    props.modified = fixed

    _configure_body_style(document)

    # Cover block — big title, lighter subtitle, an author/date line, and a rule
    # between the cover and the content.
    title = document.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.LEFT
    title_run = title.add_run(spec.title)
    title_run.bold = True
    title_run.font.size = Pt(28)
    title_run.font.color.rgb = RGBColor(0x0F, 0x17, 0x2A)

    subtitle = document.add_paragraph()
    subtitle_run = subtitle.add_run(spec.subtitle)
    subtitle_run.italic = True
    subtitle_run.font.size = Pt(13)
    subtitle_run.font.color.rgb = RGBColor(0x4B, 0x55, 0x63)

    meta = document.add_paragraph()
    meta_run = meta.add_run(
        f"Prepared by Daniel Panea Lichtig · Drafted {fixed.date().isoformat()} · "
        "Internal working document"
    )
    meta_run.font.size = Pt(10)
    meta_run.font.color.rgb = RGBColor(0x6B, 0x72, 0x80)

    document.add_paragraph()  # spacing before first section

    _add_section(
        document,
        "Situation",
        spec.paragraphs,
    )

    _add_section(
        document,
        "Working notes",
        bullets=spec.bullets,
    )

    _add_section(
        document,
        "Risks and dependencies",
        (
            "The risks below are summarised from the latest stakeholder conversations. "
            "They are not exhaustive: anything material that comes up between this "
            "version and the next stakeholder review should be added directly so the "
            "document stays usable as a hand-over.",
            "Where a risk has an owner, the owner is named in the working notes above. "
            "Where no owner is named yet, treat that as the first thing to fix rather "
            "than waiting for a meeting to assign it.",
        ),
    )

    _add_section(
        document,
        "Next steps",
        (
            "The next stakeholder review should focus on the open working-note items "
            "rather than restating the situation. If the situation has changed materially "
            "since this document was drafted, update the Situation section first and only "
            "then revisit the working notes.",
            "This document is intended as a short, durable account memory. It is rewritten "
            "rather than appended to, so the version in the repository is always the "
            "current shared view between the people working the account.",
        ),
    )

    _add_section(
        document,
        "Demo boundary",
        (
            "Important: this is synthetic internal account-planning content for a public "
            "reference architecture. It must not be treated as a production engagement plan, "
            "and no information here corresponds to a real customer, contract, or commitment.",
        ),
        emphasise_first=True,
    )

    document.save(path)
    _normalize_docx_zip(path)


def _configure_body_style(document) -> None:
    """Set default body font to something more book-like than the python-docx default."""
    normal = document.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)
    normal.font.color.rgb = RGBColor(0x1F, 0x29, 0x37)
    pf = normal.paragraph_format
    pf.space_after = Pt(6)
    pf.line_spacing = 1.25


def _add_section(
    document,
    heading: str,
    paragraphs: tuple[str, ...] | None = None,
    *,
    bullets: tuple[str, ...] | None = None,
    emphasise_first: bool = False,
) -> None:
    heading_para = document.add_heading(heading, level=1)
    for run in heading_para.runs:
        run.font.color.rgb = RGBColor(0x11, 0x18, 0x27)
    if paragraphs:
        for index, text in enumerate(paragraphs):
            paragraph = document.add_paragraph()
            run = paragraph.add_run(text)
            if emphasise_first and index == 0:
                run.bold = True
    if bullets:
        for bullet in bullets:
            document.add_paragraph(bullet, style="List Bullet")


def _normalize_docx_zip(path: Path) -> None:
    temp_path = path.with_suffix(".tmp.docx")
    with ZipFile(path, "r") as source, ZipFile(temp_path, "w", ZIP_DEFLATED) as target:
        for name in sorted(source.namelist()):
            info = ZipInfo(name, FIXED_DOCX_TIME)
            info.compress_type = ZIP_DEFLATED
            info.external_attr = source.getinfo(name).external_attr
            target.writestr(info, source.read(name))
    temp_path.replace(path)
