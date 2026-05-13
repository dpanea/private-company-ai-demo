from __future__ import annotations

import json
import shutil
from datetime import date
from pathlib import Path
from typing import Any

from .accounts import AccountSpec, build_accounts, build_crm_records
from .csv_writer import write_crm_csvs
from .docx_writer import write_docx
from .emails import write_mbox
from .meetings import write_meeting
from .pdfs import write_pdf
from .render_scanned import render_scanned_pdf


def generate_corpus(output: Path, reference_date: date, clean: bool = False) -> dict[str, Any]:
    if clean and output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)

    accounts = build_accounts(reference_date)
    manifest_accounts: list[dict[str, Any]] = []

    for account in accounts:
        account_dir = output / "accounts" / account.slug
        account_dir.mkdir(parents=True, exist_ok=True)
        artifacts: list[dict[str, Any]] = []

        write_mbox(account_dir / "emails.mbox", account.emails)
        artifacts.append(
            {
                "path": f"accounts/{account.slug}/emails.mbox",
                "type": "email_thread",
                "format": "mbox",
                "message_count": len(account.emails),
            }
        )

        for pdf in account.pdfs:
            pdf_path = account_dir / pdf.filename
            if pdf.requires_ocr:
                clean_pdf = account_dir / "_signed_nda_clean.pdf"
                text_pdf = _text_layer_copy(pdf)
                write_pdf(clean_pdf, account, text_pdf)
                render_scanned_pdf(clean_pdf, pdf_path)
                clean_pdf.unlink(missing_ok=True)
            else:
                write_pdf(pdf_path, account, pdf)
            artifacts.append(
                {
                    "path": f"accounts/{account.slug}/{pdf.filename}",
                    "type": "pdf",
                    "format": "pdf",
                    "has_text_layer": pdf.has_text_layer,
                    **({"requires_ocr": True} if pdf.requires_ocr else {}),
                }
            )

        write_docx(account_dir / account.docx.filename, account.docx)
        artifacts.append(
            {
                "path": f"accounts/{account.slug}/{account.docx.filename}",
                "type": "docx",
                "format": "docx",
            }
        )

        for meeting in account.meetings:
            write_meeting(account_dir / meeting.filename, meeting)
            artifacts.append(
                {
                    "path": f"accounts/{account.slug}/{meeting.filename}",
                    "type": "meeting_transcript",
                    "format": "markdown",
                }
            )

        manifest_accounts.append(
            {
                "account_id": account.account_id,
                "account_slug": account.slug,
                "account_name": account.name,
                "artifacts": artifacts,
            }
        )

    crm_paths = write_crm_csvs(output / "crm", build_crm_records(accounts, reference_date))
    manifest = {
        "reference_date": reference_date.isoformat(),
        "accounts": manifest_accounts,
        "crm": crm_paths,
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return manifest


def _text_layer_copy(pdf: Any) -> Any:
    return type(pdf)(
        filename=pdf.filename,
        title=pdf.title,
        subtitle=pdf.subtitle,
        document_type=pdf.document_type,
        issue_date=pdf.issue_date,
        sections=pdf.sections,
        pricing_rows=pdf.pricing_rows,
        has_text_layer=True,
        requires_ocr=False,
    )
