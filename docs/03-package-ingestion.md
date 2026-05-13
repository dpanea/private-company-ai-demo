# Package 3 — Ingestion pipeline

**Purpose.** Read the synthetic corpus from `data/synthetic/`, parse each format into text + metadata, store `raw_artifacts`, build normalized CRM records, then build AI-ready documents and index their embeddings into Postgres. This is the demo-grade ingestion path. Production-grade ingestion is explicitly out of scope and documented as such in the README.

**Depends on:** Package 1, Package 2.

**Blocks:** Package 4 (retrieval needs a populated DB).

**Estimated size:** medium (~1500 LOC including parsers, AI-ready doc builder, and tests).

## Outputs

```text
src/pcad/
├── ingestion/
│   ├── __init__.py
│   ├── manifest.py             # load + validate manifest.json
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── mbox.py             # mbox → list of email artifacts
│   │   ├── pdf.py              # PDF → text (with OCR fallback)
│   │   ├── docx.py             # docx → text
│   │   ├── meeting_md.py       # speaker-labeled markdown → text + metadata
│   │   └── csv_crm.py          # CRM CSVs → Pydantic records
│   ├── ocr.py                  # Tesseract wrapper + scanned-page rendering
│   ├── normalize.py            # raw artifacts + CRM records → AI-ready inputs
│   ├── ai_ready_documents.py   # builds rag_documents (all 8 doc types)
│   ├── embeddings.py           # index embeddings into rag_documents.embedding
│   └── runner.py               # the one-shot orchestrator
└── cli.py                      # add `ingest-demo` subcommand
scripts/
└── ingest_demo.py              # thin shim that calls runner.run_demo_ingestion()
```

## Dependencies to add to pyproject.toml

```toml
"pypdf>=4.0.0",            # PDF text extraction
"python-docx>=1.1.0",      # docx parsing (reused from Package 2)
"pytesseract>=0.3.10",     # OCR
"pdf2image>=1.17.0",       # PDF → image for OCR (reused from Package 2)
"Pillow>=10.0.0",          # image handling (reused from Package 2)
```

System-level dependencies (documented in README):

- `poppler-utils` (for `pdf2image`)
- `tesseract-ocr` and `tesseract-ocr-eng` (for OCR)

## High-level flow

```text
manifest.json
   │
   ▼
For each account:
  ├─ Parse CRM CSVs → CRM Pydantic records → INSERT into normalized tables
  ├─ For each artifact in manifest:
  │     ├─ Dispatch by type:
  │     │     - mbox: split into emails, then group into email_threads
  │     │     - pdf: extract text; if no text layer → OCR via Tesseract
  │     │     - docx: extract paragraphs
  │     │     - meeting_md: parse speaker turns + metadata block
  │     │     - csv_crm: handled in the CRM phase above
  │     ├─ Render PDF pages to images for left-panel display (data/rendered/<artifact_id>/page_N.png)
  │     ├─ INSERT raw_artifacts row
  │     └─ INSERT source_citations entries
  └─ Build AI-ready documents (account_memory, recent_activity_timeline,
                                opportunity_snapshot, contract_snapshot, stakeholder_map,
                                email_thread_summary, meeting_summary, risk_summary)
     and INSERT into rag_documents
   │
   ▼
For each rag_document with NULL embedding:
   └─ Call embedding model (OpenRouter), UPDATE embedding
```

The entire flow runs in one transactional pass with `runner.run_demo_ingestion()`. This is intentionally non-incremental.

## src/pcad/ingestion/parsers/mbox.py

```python
def parse_mbox(path: Path) -> list[ParsedEmail]:
    """Parse an mbox file into a list of ParsedEmail records.

    Uses the stdlib `mailbox` module. Preserves headers (From, To, Cc, Date,
    Subject, In-Reply-To, References, Message-ID). Body is plain text only;
    attachments are noted in metadata but not extracted.
    """
```

`ParsedEmail` is an in-module dataclass with: `message_id`, `subject`, `from_addr`, `to_addrs`, `cc_addrs`, `date`, `in_reply_to`, `references`, `body_text`.

The parser must also group emails by thread (using `References` / `In-Reply-To` headers) and produce one `email_thread` raw artifact per thread, in addition to one `email` artifact per individual message. The thread artifact's `extracted_text` is the concatenation of all messages in chronological order with clear separators.

## src/pcad/ingestion/parsers/pdf.py

```python
def parse_pdf(path: Path, ocr_fallback: bool = True) -> ParsedPdf:
    """Extract text and metadata from a PDF.

    Tries pypdf first. If the extracted text is empty or below a low threshold
    (~50 chars total), falls back to OCR via ingestion.ocr.ocr_pdf when
    ocr_fallback is True.
    """
```

`ParsedPdf` includes: `page_count`, `text_per_page: list[str]`, `extraction_method: Literal["plain_text", "ocr"]`, `rendered_image_paths: list[Path]`.

The `rendered_image_paths` are produced by `pdf2image.convert_from_path` and saved under `data/rendered/<artifact_id>/page_N.png`. These are the images the frontend's source viewer will display.

## src/pcad/ingestion/ocr.py

```python
def ocr_pdf(path: Path) -> list[str]:
    """OCR a PDF page by page using Tesseract. Returns text per page."""
```

- Uses `pdf2image.convert_from_path` to rasterize pages (DPI 200).
- Pipes each page through `pytesseract.image_to_string(..., lang="eng")`.
- Returns the per-page text.

Log: `logger.info("ocr.pdf.done path=%s pages=%s chars=%s", path, pages, total_chars)`.

## src/pcad/ingestion/parsers/docx.py

```python
def parse_docx(path: Path) -> ParsedDocx:
    """Extract paragraph text from a .docx file using python-docx."""
```

Concatenate paragraphs with double newlines. Preserve heading levels by prefixing `# `, `## `, `### ` based on `style.name`.

## src/pcad/ingestion/parsers/meeting_md.py

```python
def parse_meeting_md(path: Path) -> ParsedMeeting:
    """Parse a speaker-labeled markdown transcript.

    Expected format: a header block with Meeting/Date/Attendees fields,
    a `---` separator, then `**Speaker:** text` turns.
    """
```

`ParsedMeeting` includes: `meeting_title`, `meeting_date`, `attendees: list[str]`, `turns: list[tuple[str, str]]` (speaker, text), `full_text: str`.

## src/pcad/ingestion/parsers/csv_crm.py

```python
def parse_crm_csvs(crm_dir: Path) -> SyntheticDataset:
    """Load the 6 CRM CSVs into a SyntheticDataset (Pydantic model from Package 1)."""
```

Uses `csv.DictReader` from stdlib (no pandas). Each row is constructed into the corresponding model. Field name mismatches must raise loudly with a clear message — silent defaults are forbidden.

## src/pcad/ingestion/normalize.py

Transforms parsed artifacts + CRM records into the inputs the AI-ready document builder needs.

```python
def normalize_email_threads(parsed: list[ParsedEmail]) -> list[EmailThread]:
    """Group emails into threads via Message-ID / References / In-Reply-To."""

def normalize_meeting_for_summary(parsed: ParsedMeeting) -> MeetingSummaryInput:
    """Strip prose down to: bullet-style takeaways, attendees, key decisions, action items."""
```

`EmailThread` and `MeetingSummaryInput` are local dataclasses with the minimum fields the downstream document builder needs.

For the meeting → summary normalization, the v1 implementation can be **rule-based and simple**: take the first N sentences from each speaker plus any sentence containing certain keyword classes (next step, action, risk, decision, concern, approval). The LLM-driven summarization is explicitly out of scope for ingestion-time; it's better to keep ingestion deterministic and let the agent (Package 4) re-summarize from raw text when needed.

## src/pcad/ingestion/ai_ready_documents.py

Adapt [core/documents.py](../../uniendo-nodos-private-ai/src/un_private_ai/core/documents.py) (the `DocumentBuilder` class) with these changes:

- All content rewritten to **English** (headings, labels, fallback strings, prefixes).
- Add three new document types:
  - `email_thread_summary` — one per `EmailThread`, with content: thread subject, participants, chronological summary of messages (first sentence + last sentence per message), an "Open questions" section derived from unanswered emails, and citation entries linking to each `raw_artifacts` row for emails in the thread.
  - `meeting_summary` — one per meeting transcript, with content: meeting title, date, attendees, key topics (rule-based bullet extraction from `normalize.py`), action items, risks/concerns, and citations linking back to the meeting transcript artifact.
  - `risk_summary` — one per account, aggregating risks/objections/unresolved questions found in emails, meeting transcripts, and high-priority open Tasks. Generated by simple keyword/regex matching at this stage. Citations link to the source artifacts and activities.

The existing 5 doc types (`account_memory`, `recent_activity_timeline`, `opportunity_snapshot`, `contract_snapshot`, `stakeholder_map`) keep their structure but the prose is rewritten to English. Reuse the patterns from Uniendo Nodos almost verbatim with `s/spanish/english/` and Spanish strings translated.

### Citation format

Citations follow the same `[Source: Type RecordId]` label format as Uniendo Nodos, but the label uses **English**: `[Source: Email <message_id>]`, `[Source: Meeting <meeting_id>]`, `[Source: Account <account_id>]`, etc.

The agent prompts (Package 4) must match this English label format.

## src/pcad/ingestion/embeddings.py

Adapt the `index_document_embeddings` function from [core/retrieval.py](../../uniendo-nodos-private-ai/src/un_private_ai/core/retrieval.py).

```python
def index_pending_embeddings(settings: Settings, *, batch_limit: int | None = None) -> int:
    """For every rag_documents row with embedding IS NULL, call the embedding
    API and UPDATE the row. Returns the number of documents embedded.
    """
```

The embedding text is `f"{title}\n\n{content_markdown}"`.

If `OPENROUTER_API_KEY` is missing, log a warning and skip embedding (downstream retrieval falls back to full-text only). This lets the demo work in a degraded mode for local testing.

## src/pcad/ingestion/runner.py

```python
def run_demo_ingestion(
    settings: Settings,
    *,
    synthetic_dir: Path = Path("data/synthetic"),
    clean: bool = False,
    skip_embeddings: bool = False,
) -> IngestionReport:
    """One-shot ingestion of the synthetic corpus into Postgres.

    Pipeline:
      1. If clean: TRUNCATE all application tables.
      2. Load and validate manifest.json.
      3. Parse and INSERT CRM CSVs (users_or_owners, accounts, contacts,
         opportunities, contracts, activities).
      4. For each account, parse each artifact, insert raw_artifacts row,
         render PDF pages to images.
      5. Build AI-ready documents and INSERT into rag_documents.
      6. INSERT source_citations entries.
      7. If not skip_embeddings: index pending embeddings.

    Idempotent only if `clean=True`. Without --clean, re-running will fail
    on unique key conflicts (intentional; the runner is not a sync engine).
    """
```

`IngestionReport` is a dataclass that totals records ingested per table, OCR runs performed, embedding calls made, and elapsed time. Returned for logging and inclusion in tests.

## CLI

Add to `src/pcad/cli.py`:

```text
uv run pcad ingest-demo [--clean] [--skip-embeddings] [--synthetic-dir data/synthetic]
```

Wraps `runner.run_demo_ingestion`. Prints the `IngestionReport` to stdout.

## Reuse from Uniendo Nodos

- [core/documents.py](../../uniendo-nodos-private-ai/src/un_private_ai/core/documents.py) — the `DocumentBuilder` class. Rewrite content to English, extend with 3 new doc types.
- The embedding indexer logic in [core/retrieval.py:422](../../uniendo-nodos-private-ai/src/un_private_ai/core/retrieval.py) — copy verbatim into `ingestion/embeddings.py`.
- The Pydantic synthetic dataset shape from Package 1.

## Tests

`tests/test_parsers.py`:

- mbox parser produces N messages and groups into M threads given a fixture file.
- PDF parser extracts expected text from a text-layer PDF.
- PDF parser falls back to OCR for a known scanned PDF fixture and returns non-empty text.
- docx parser preserves headings.
- meeting_md parser extracts attendees and N turns.

`tests/test_ingestion_runner.py`:

- Against a small fixture corpus (a subset committed under `tests/fixtures/mini_corpus/`), running `run_demo_ingestion(clean=True)` populates all expected tables with the expected row counts.
- AI-ready documents include at least one of each new type (`email_thread_summary`, `meeting_summary`, `risk_summary`).
- Re-running with `clean=False` raises a unique-constraint error (expected).
- Re-running with `clean=True` produces identical row counts and document hashes.

OCR test should be marked `@pytest.mark.requires_tesseract` and skipped gracefully if Tesseract is not installed.

## Acceptance criteria

1. `uv run pcad ingest-demo --clean` runs end-to-end against a freshly migrated DB and the Package-2 corpus.
2. After ingestion, the DB contains: 1 user-set, 3 accounts, ~10 contacts, 3 opportunities, ≥1 contract, 15–25 activities, ~30–40 raw_artifacts, ~30–50 rag_documents, embeddings populated for every rag_document.
3. The scanned NDA PDF was successfully OCRed and its `raw_artifacts.extraction_method = 'ocr'`.
4. Every `raw_artifacts.rendered_path` for PDFs points to an existing PNG.
5. All AI-ready documents use English-only prose and English citation labels.
6. The full ingestion completes in under 2 minutes on a developer laptop (OpenRouter network latency dominates).
