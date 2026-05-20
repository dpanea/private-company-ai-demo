from __future__ import annotations

from pathlib import Path
from typing import Callable

from reportlab import rl_config
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .accounts import AccountSpec, PdfSpec

rl_config.invariant = 1


def write_pdf(path: Path, account: AccountSpec, spec: PdfSpec) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="Small",
            parent=styles["Normal"],
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#4b5563"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="CoverTitle",
            parent=styles["Title"],
            fontSize=24,
            leading=30,
            spaceAfter=16,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CoverKicker",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#6b7280"),
            spaceAfter=4,
        )
    )
    # Body copy: justified, generous leading, modest space below each paragraph
    # so pages fill out naturally instead of looking like skeleton drafts.
    styles.add(
        ParagraphStyle(
            name="BodyPara",
            parent=styles["Normal"],
            fontSize=10.5,
            leading=15,
            alignment=TA_JUSTIFY,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SectionHeading",
            parent=styles["Heading1"],
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#0f172a"),
            spaceBefore=10,
            spaceAfter=8,
        )
    )
    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        rightMargin=2.2 * cm,
        leftMargin=2.2 * cm,
        topMargin=2.2 * cm,
        bottomMargin=2.2 * cm,
        title=spec.title,
        author="Daniel Panea Lichtig",
        subject=spec.subtitle,
    )
    story: list[object] = [
        Paragraph(account.name, styles["CoverKicker"]),
        Paragraph(spec.title, styles["CoverTitle"]),
        Paragraph(spec.subtitle, styles["Heading2"]),
        Spacer(1, 0.4 * cm),
        Paragraph(f"Issue date: {spec.issue_date.isoformat()}", styles["Normal"]),
        Paragraph("Prepared by: Daniel Panea Lichtig", styles["Normal"]),
        Spacer(1, 0.4 * cm),
        Paragraph(
            "Synthetic business document generated for the The Company Knowledge AI. "
            "All companies, people, domains, and scenarios are fictional and any resemblance "
            "to a real engagement is unintended.",
            styles["Small"],
        ),
        Spacer(1, 0.8 * cm),
    ]

    last_index = len(spec.sections) - 1
    for index, (heading, paragraphs) in enumerate(spec.sections):
        # Avoid widow headings: keep the heading and the first paragraph together.
        head_block: list[object] = [Paragraph(heading, styles["SectionHeading"])]
        if paragraphs:
            head_block.append(Paragraph(paragraphs[0], styles["BodyPara"]))
        story.append(KeepTogether(head_block))
        for paragraph in paragraphs[1:]:
            story.append(Paragraph(paragraph, styles["BodyPara"]))
        if heading == "Scope of work":
            story.append(Spacer(1, 0.15 * cm))
            story.append(_scope_table(styles["Small"]))
        if index != last_index:
            story.append(Spacer(1, 0.35 * cm))

    if spec.pricing_rows:
        story.append(Spacer(1, 0.6 * cm))
        story.append(Paragraph("Commercial summary", styles["SectionHeading"]))
        rows = [("Item", "Duration", "Fee")] + list(spec.pricing_rows)
        table = Table(rows, colWidths=[7 * cm, 4 * cm, 4 * cm])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5e7eb")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111827")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#9ca3af")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(table)
        story.append(Spacer(1, 0.4 * cm))
        story.append(
            Paragraph(
                "Production-grade connector hardening, multi-tenant operations, billing, and "
                "admin dashboards are explicitly outside this pilot. They can be scoped as a "
                "separate engagement once the pilot has been reviewed.",
                styles["BodyPara"],
            )
        )

    footer = _footer(spec.title)
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


def _scope_table(style: ParagraphStyle) -> Table:
    rows = [
        ("Capability", "Pilot behavior"),
        ("Source ingestion", "Email archives, PDFs, Word documents, CRM CSV exports, and meeting notes."),
        ("Retrieval", "Hybrid search over normalized account memory with visible source citations."),
        ("Answer generation", "Guided workflows and free-text questions with citation validation."),
        ("Boundaries", "No production automation, no autonomous actions, no broad SaaS feature set."),
    ]
    table = Table(rows, colWidths=[4 * cm, 11 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f4f6")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d1d5db")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    for row in table._cellvalues[1:]:
        row[1] = Paragraph(row[1], style)
    return table


def _footer(title: str) -> Callable[[object, object], None]:
    def draw(canvas: object, doc: object) -> None:
        canvas.saveState()
        canvas.setAuthor("Daniel Panea Lichtig")
        canvas.setTitle(title)
        canvas.setSubject("Synthetic corpus artifact")
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#6b7280"))
        canvas.drawString(2 * cm, 1 * cm, "The Company Knowledge AI synthetic artifact")
        canvas.drawRightString(19 * cm, 1 * cm, f"Page {doc.page}")
        canvas.restoreState()

    return draw
