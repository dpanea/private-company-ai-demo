from __future__ import annotations

import io
from pathlib import Path

from pdf2image import convert_from_path
from PIL import Image, ImageEnhance, ImageFilter
from pypdf import PdfReader, PdfWriter


def render_scanned_pdf(source_pdf: Path, output_pdf: Path) -> None:
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    pages = convert_from_path(source_pdf, dpi=160, fmt="ppm")
    degraded = [_degrade_page(page, index) for index, page in enumerate(pages)]
    if not degraded:
        raise ValueError(f"No pages were rendered from {source_pdf}")

    temp_pdf = output_pdf.with_suffix(".tmp.pdf")
    first, rest = degraded[0], degraded[1:]
    first.save(
        temp_pdf,
        "PDF",
        save_all=True,
        append_images=rest,
        resolution=160.0,
    )
    _normalize_pdf_metadata(temp_pdf, output_pdf)
    temp_pdf.unlink(missing_ok=True)


def _degrade_page(page: Image.Image, index: int) -> Image.Image:
    image = page.convert("RGB")
    image = ImageEnhance.Brightness(image).enhance(0.94)
    image = image.filter(ImageFilter.GaussianBlur(radius=0.45))
    angle = 1.4 if index % 2 == 0 else -1.1
    image = image.rotate(
        angle,
        resample=Image.Resampling.BICUBIC,
        expand=True,
        fillcolor=(248, 248, 246),
    )
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=70, optimize=False)
    buffer.seek(0)
    return Image.open(buffer).convert("RGB")


def _normalize_pdf_metadata(source: Path, output: Path) -> None:
    reader = PdfReader(str(source))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.add_metadata(
        {
            "/Title": "Scanned synthetic NDA",
            "/Author": "Daniel Panea Lichtig",
            "/Subject": "Synthetic OCR demo artifact",
            "/Creator": "Private Company Memory Demo",
            "/Producer": "Private Company Memory Demo",
            "/CreationDate": "D:20260101000000+00'00'",
            "/ModDate": "D:20260101000000+00'00'",
        }
    )
    with output.open("wb") as handle:
        writer.write(handle)
