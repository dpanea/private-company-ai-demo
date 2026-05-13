from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from docx import Document

from .accounts import DocxSpec

FIXED_DOCX_TIME = (2026, 1, 1, 0, 0, 0)


def write_docx(path: Path, spec: DocxSpec) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    document = Document()
    props = document.core_properties
    fixed = datetime(2026, 1, 1, tzinfo=timezone.utc)
    props.author = "Daniel Panea Lichtig"
    props.title = spec.title
    props.subject = spec.subtitle
    props.created = fixed
    props.modified = fixed

    document.add_heading(spec.title, 0)
    document.add_paragraph(spec.subtitle)
    document.add_heading("Situation", level=1)
    for paragraph in spec.paragraphs:
        document.add_paragraph(paragraph)

    document.add_heading("Working notes", level=1)
    for bullet in spec.bullets:
        document.add_paragraph(bullet, style="List Bullet")

    document.add_heading("Demo boundary", level=1)
    p = document.add_paragraph()
    p.add_run("Important: ").bold = True
    p.add_run(
        "This is synthetic internal account-planning content for a public reference architecture. "
        "It should not be treated as a production engagement plan."
    )

    document.save(path)
    _normalize_docx_zip(path)


def _normalize_docx_zip(path: Path) -> None:
    temp_path = path.with_suffix(".tmp.docx")
    with ZipFile(path, "r") as source, ZipFile(temp_path, "w", ZIP_DEFLATED) as target:
        for name in sorted(source.namelist()):
            info = ZipInfo(name, FIXED_DOCX_TIME)
            info.compress_type = ZIP_DEFLATED
            info.external_attr = source.getinfo(name).external_attr
            target.writestr(info, source.read(name))
    temp_path.replace(path)
