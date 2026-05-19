from __future__ import annotations

import textwrap
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from .accounts import (
    INTERNAL_ACCOUNT_ID,
    INTERNAL_ACCOUNT_NAME,
    INTERNAL_ACCOUNT_SLUG,
    AccountSpec,
    DocxSpec,
    PdfSpec,
    d,
    shift_date,
)
from .docx_writer import write_docx
from .pdfs import write_pdf


@dataclass(frozen=True)
class MarkdownSpec:
    filename: str
    title: str
    body: str


@dataclass(frozen=True)
class InternalKnowledgeSpec:
    account: AccountSpec
    docx_files: tuple[DocxSpec, ...]
    pdfs: tuple[PdfSpec, ...]
    markdown_files: tuple[MarkdownSpec, ...]


def build_internal_knowledge(reference_date: date) -> InternalKnowledgeSpec:
    account = AccountSpec(
        account_id=INTERNAL_ACCOUNT_ID,
        slug=INTERNAL_ACCOUNT_SLUG,
        name=INTERNAL_ACCOUNT_NAME,
        domain="danielpanea.com",
        industry="Company operations",
        country="",
        city="",
        website="https://danielpanea.example/internal-knowledge",
        phone="",
        story_arc="Internal company knowledge context for policies, delivery decisions, vendors, and operating cadence.",
        opportunity_id="",
        opportunity_name="",
        opportunity_stage="",
        opportunity_amount=0.0,
        opportunity_probability=0.0,
        opportunity_close_date=reference_date,
        contacts=(),
        emails=(),
        pdfs=(),
        docx=DocxSpec("", "", "", (), ()),
        meetings=(),
    )
    return InternalKnowledgeSpec(
        account=account,
        docx_files=(
            DocxSpec(
                "onboarding_handbook.docx",
                "Internal onboarding handbook",
                "How delivery work starts, runs, and stays auditable",
                (
                    "New delivery projects begin with a source inventory, a decision log, and a named owner for every artifact category. The first week is not about building connectors; it is about proving which sources are allowed, which questions matter, and who can approve access.",
                    "The default delivery rhythm is a Monday planning note, a Wednesday evidence review, and a Friday written recap. Every recap must distinguish observed facts from recommendations so the client can audit how the system moved from source artifacts to a proposed next step.",
                    "A new consultant should spend the first day reading the latest strategy memo, the engineering decision record, and any client-specific account plan before touching code. The second day is for reproducing the ingestion locally with synthetic data and writing down gaps in the runbook.",
                    "Project notes should be short, dated, and written for future retrieval. A good note names the decision, the evidence used, the owner, and what would cause the decision to be reopened. Long narrative notes are allowed only when the context would otherwise be lost.",
                ),
                (
                    "Week-one onboarding checklist: run the demo locally, inspect the source artifact list, ask one cited question, and trace the citation back to the raw artifact.",
                    "Delivery rule: no production source is ingested until the source owner, retention window, and deletion path are written down.",
                    "Communication rule: every client-facing summary names open risks even when the commercial story is positive.",
                    "Documentation rule: decisions belong in an engineering decision record, not only in chat or meeting memory.",
                ),
            ),
        ),
        pdfs=(
            PdfSpec(
                "vendor_contract_summary.pdf",
                "Vendor contract summary",
                "Document processing and hosted model service boundaries",
                "proposal",
                shift_date(d("2026-05-06"), reference_date),
                _vendor_contract_sections(reference_date),
            ),
        ),
        markdown_files=(
            MarkdownSpec(
                "all_hands_strategy_recap.md",
                "All-hands strategy recap",
                _strategy_recap(reference_date),
            ),
            MarkdownSpec(
                "engineering_decision_record_postgres_pgvector.md",
                "Engineering decision record: Postgres and pgvector",
                _engineering_decision_record(reference_date),
            ),
        ),
    )


def write_internal_knowledge(output: Path, reference_date: date) -> dict[str, Any]:
    spec = build_internal_knowledge(reference_date)
    internal_dir = output / "accounts" / INTERNAL_ACCOUNT_SLUG
    internal_dir.mkdir(parents=True, exist_ok=True)

    artifacts: list[dict[str, Any]] = []
    for docx in spec.docx_files:
        write_docx(internal_dir / docx.filename, docx)
        artifacts.append(
            {
                "path": f"accounts/{INTERNAL_ACCOUNT_SLUG}/{docx.filename}",
                "type": "docx",
                "format": "docx",
            }
        )
    for pdf in spec.pdfs:
        write_pdf(internal_dir / pdf.filename, spec.account, pdf)
        artifacts.append(
            {
                "path": f"accounts/{INTERNAL_ACCOUNT_SLUG}/{pdf.filename}",
                "type": "pdf",
                "format": "pdf",
                "has_text_layer": pdf.has_text_layer,
            }
        )
    for markdown in spec.markdown_files:
        (internal_dir / markdown.filename).write_text(markdown.body, encoding="utf-8", newline="\n")
        artifacts.append(
            {
                "path": f"accounts/{INTERNAL_ACCOUNT_SLUG}/{markdown.filename}",
                "type": "meeting_transcript",
                "format": "markdown",
            }
        )

    return {
        "account_id": INTERNAL_ACCOUNT_ID,
        "account_slug": INTERNAL_ACCOUNT_SLUG,
        "account_name": INTERNAL_ACCOUNT_NAME,
        "artifacts": artifacts,
    }


def _vendor_contract_sections(reference_date: date) -> tuple[tuple[str, tuple[str, ...]], ...]:
    renewal_date = shift_date(d("2026-08-31"), reference_date)
    return (
        (
            "Summary",
            (
                "The document processing vendor contract covers OCR rendering, PDF page image storage, and hosted embedding/model API access used only for synthetic public-demo traffic and approved pilot environments. It does not authorize the vendor to train on customer content, resell source artifacts, or retain prompts beyond the operational logging window.",
                "The current commercial term runs through the end of August 2026. Renewal should not be automatic: Procurement wants a written review of usage, incident history, and export feasibility before extending the service.",
            ),
        ),
        (
            "Security and data handling",
            (
                "The contract requires encrypted transport, EU-region processing for approved pilot workloads, and deletion of raw processing queues within thirty days. Debug logs may contain file names and processing metadata, but they must not contain full prompt text, full extracted documents, or model responses at INFO level.",
                "Production client data remains out of scope for the public demo. A paid pilot may use the same vendor only after the client approves the subprocessor list and the deployment notes explain which artifacts leave the client's infrastructure.",
            ),
        ),
        (
            "Commercial terms",
            (
                "The contract is usage-based with a monthly cap. Daniel reviews spend weekly during live demos and can disable hosted calls if daily budget alarms trip. The contract allows export of derived indexes and raw artifacts without penalty if the architecture moves to a sovereign self-hosted path.",
                f"The next procurement decision is due by {renewal_date.isoformat()}. The open question is whether hosted embeddings remain acceptable for private walkthroughs, or whether all paid pilots should default to the vLLM deployment path.",
            ),
        ),
        (
            "Decision notes",
            (
                "The vendor is acceptable for the public reference demo because the corpus is synthetic and the architecture clearly labels the hosted dependency. It is not a blanket approval for client data.",
                "If a prospect asks for strict sovereignty, the response should point to the documented vLLM path and explain the trade-off: higher operational burden, lower third-party exposure, and more hardware planning before launch.",
            ),
        ),
    )


def _strategy_recap(reference_date: date) -> str:
    recap_date = shift_date(d("2026-05-09"), reference_date)
    return _markdown(
        f"""
        # Meeting: All-hands strategy recap

        **Date:** {recap_date.isoformat()}
        **Attendees:** Daniel Panea, Delivery collaborators, Advisory reviewers

        ---

        **Daniel:** The naming is moving from account memory toward Company Knowledge AI because the demo needs to prove more than CRM retrieval. The sales wedge stays, but internal policies, vendor decisions, and delivery knowledge have to be visible in the same source-backed interface.

        **Delivery:** The account workflows are still the clearest demo moment. Briefing before a client call remains concrete and relatable, especially for consultancies and Mittelstand buyers.

        **Daniel:** Agreed. The change is not to flatten the sales use case. The change is to make the account picker optional context instead of a gate. If someone asks about SOC 2 status, onboarding, or a vendor decision, the system should answer from internal artifacts without demanding a client.

        **Advisory:** SOC 2 should be described carefully. The current state is readiness work, not certification. Evidence collection is underway, but no public claim should say the company is certified or audited.

        **Daniel:** Record that as a decision. Public copy may say audit-friendly architecture and SOC 2 readiness work. It must not say SOC 2 certified.

        **Delivery:** What is the DES focus?

        **Daniel:** The DES demo should show two registers. First, a client call briefing with citations. Second, a general company question such as onboarding or "what did we decide about Postgres and pgvector?" That gives non-sales buyers a way into the demo.

        **Advisory:** The risk is breadth. More buttons can make the interface feel unfocused.

        **Daniel:** We will keep the button count tight. "What changed?" and "Next action" are removed from the primary workflow set for now. "Catch me up" and "What did we decide about..." become editable prompt starters rather than automatic model calls.

        **Delivery:** What should happen when the user clicks a general workflow?

        **Daniel:** It should prefill the composer and focus it. The user supplies the topic. No LLM call should be spent asking what topic they meant.

        **Advisory:** What is the current SOC 2 status phrase?

        **Daniel:** "SOC 2 readiness work is underway; certification is not claimed." The evidence pack target is a first internal draft in June 2026, focused on source retention, deletion behavior, logging boundaries, and subprocessor review.
        """
    )


def _engineering_decision_record(reference_date: date) -> str:
    decision_date = shift_date(d("2026-04-26"), reference_date)
    return _markdown(
        f"""
        # Meeting: Engineering decision record - Postgres and pgvector

        **Date:** {decision_date.isoformat()}
        **Attendees:** Daniel Panea, Architecture reviewers

        ---

        **Daniel:** Decision proposed: use PostgreSQL 16 with pgvector and pg_trgm as the retrieval store for the public demo instead of introducing a separate vector database.

        **Reviewer:** What problem does that solve?

        **Daniel:** It keeps the reference architecture legible. The demo needs accounts, raw artifacts, AI-ready documents, source citations, sessions, and embeddings. Keeping them in one database makes migrations, local setup, and deletion behavior easier to explain.

        **Reviewer:** What alternatives were considered?

        **Daniel:** A managed vector database, OpenSearch, and a document store with a separate embedding index. Each is reasonable in production under the right constraints, but each adds another operational surface for a public reference demo.

        **Reviewer:** What is the trade-off?

        **Daniel:** pgvector is good enough for the small corpus and for paid-pilot prototypes. It is not a claim that one Postgres instance is the correct answer for every large enterprise memory system. At larger scale, ranking, sharding, and evaluation may justify a separate retrieval service.

        **Reviewer:** Why include full-text search?

        **Daniel:** Company questions often contain exact names, policy terms, dates, and contract phrases. Dense vector search alone can miss exact terms. The retrieval plan uses English full-text search, embeddings, and reciprocal rank fusion so exact and semantic matches both have a path.

        **Reviewer:** What is the operational decision?

        **Daniel:** Ship the demo on Postgres plus pgvector, document the boundary, and avoid production-grade ingestion claims. The decision can be reopened if corpus size, latency, or customer isolation requirements exceed what a single database can handle cleanly.

        **Reviewer:** How does this affect citations?

        **Daniel:** Source citations stay relational. Every answerable chunk points back to a raw artifact citation. If an artifact is deleted, derived documents and citations can be removed with standard database operations and the embedding index can be rebuilt.
        """
    )


def _markdown(text: str) -> str:
    return textwrap.dedent(text).strip() + "\n"
