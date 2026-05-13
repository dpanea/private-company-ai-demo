# Package 2 — Synthetic corpus generation

**Purpose.** Generate the messy, multi-format synthetic dataset that the demo presents. This is what makes the demo visually different from "another CRM copilot". Output is files on disk under `data/synthetic/`, plus a structured CRM dataset JSON. Nothing in this package writes to the database — that's Package 3's job.

**Depends on:** Package 1 (Pydantic models).

**Blocks:** Package 3 (ingestion consumes this output). Package 4 can be developed without this in place using a tiny inline fixture.

**Estimated size:** medium (~800–1200 LOC, mostly content).

## Outputs

```text
data/synthetic/
├── accounts/
│   ├── brannfeld_industrial/
│   │   ├── emails.mbox
│   │   ├── proposal_2026_q2.pdf
│   │   ├── signed_nda_scanned.pdf            # deliberately scanned + slightly rotated for OCR demo
│   │   ├── account_plan.docx
│   │   ├── meeting_2026_04_15_intro.md
│   │   ├── meeting_2026_04_28_technical.md
│   │   └── meeting_2026_05_02_stakeholder.md
│   ├── rynvoss_logistics/
│   │   └── (similar shape)
│   └── caldrisa_dental/
│       └── (similar shape)
├── crm/
│   ├── accounts.csv
│   ├── contacts.csv
│   ├── opportunities.csv
│   ├── contracts.csv
│   ├── activities.csv
│   └── users.csv
└── manifest.json    # machine-readable index of every artifact

scripts/
├── generate_synthetic.py        # CLI: regenerate the whole corpus
├── render_scanned_pdf.py        # helper: takes a clean PDF and produces a scanned-looking variant
└── generate_synthetic/
    ├── __init__.py
    ├── accounts.py              # account-by-account content
    ├── emails.py                # email/mbox writers
    ├── pdfs.py                  # PDF writers (proposals, NDAs)
    ├── meetings.py              # meeting transcript writers
    ├── docx_writer.py           # Word document writer
    ├── csv_writer.py            # CRM CSV writers
    └── render_scanned.py        # OCR-friendly degraded PDF rendering
```

## Dependencies to add to pyproject.toml

```toml
"reportlab>=4.0.0",        # generate PDFs
"python-docx>=1.1.0",      # generate Word documents
"Pillow>=10.0.0",          # image manipulation for scanned PDFs
"pypdf>=4.0.0",            # used here only for combining pages
"pdf2image>=1.17.0",       # render PDF to images for the scanned-look generator
```

Note: `pdf2image` requires `poppler-utils` system package. Document this in the README installation section.

## Synthetic accounts

Generate **3 accounts** for v1. The MVP scope explicitly says 3 to ship faster; expansion to 5 is a v1.1 task.

### Fictional-name discipline

Every account name, contact name, email domain, and product name in the corpus must be **fictional and verifiably non-overlapping with real companies**. Before committing any new account name, the implementing agent must do a quick external search (or ask Daniel to confirm) that the name does not match a real business, especially in the same industry and country. Avoid:

- Famous fictional placeholders that are also used by real companies (e.g., "Acme" — too many real businesses use this).
- Industry-mismatched real brand names (e.g., "Iberia Dental" — Iberia is a major airline; using it as a dental brand is nonsensical and confusing).
- Names that collide with well-known European Mittelstand brands.

The current three names (Brannfeld Industrial GmbH, Rynvoss Logistics BV, Caldrisa Dental Group) were chosen as invented portmanteaus and should be re-verified once before the corpus is published. If a collision is discovered, replace the name throughout the codebase before shipping — the names appear in account IDs, email domains, file paths, story arcs, and embedded prose, so a global rename via `grep -ri` is required.

### Account 1: Brannfeld Industrial GmbH

- **Industry:** Industrial automation / manufacturing
- **Country:** Germany (Bavaria)
- **Story arc:** Mid-funnel deal. Decision committee includes Operations, IT, and Procurement. Security/EU-hosting concerns are an unresolved objection. Champion (Operations Director) is positive; IT lead wants audit posture clarity. Proposal sent two weeks ago, awaiting feedback.
- **Stakeholders:** 4 contacts (Operations Director, IT Lead, Procurement Manager, COO).
- **Open opportunity:** "Production-line workflow automation" — €85,000, close date in ~30 days, stage "Proposal sent".
- **Source artifacts to generate:**
  - 8 emails spanning prospecting → proposal phase (mbox)
  - 1 proposal PDF (~6 pages, clean text-based)
  - 1 signed NDA PDF (deliberately scanned + slightly rotated, for OCR demo)
  - 1 account plan docx (~2 pages, internal Daniel-style notes)
  - 3 meeting transcripts (.md, speaker-labeled)

### Account 2: Rynvoss Logistics

- **Industry:** Logistics / freight
- **Country:** Netherlands (Rotterdam)
- **Story arc:** Stalled account. Strong initial interest 6 weeks ago, then silence. Last activity was a procurement question that went unanswered. Close date set for next week but no recent engagement.
- **Stakeholders:** 3 contacts (Head of Operations, Finance Director, IT Manager).
- **Open opportunity:** "Cross-border shipment routing optimization" — €52,000, close date in ~10 days, stage "Negotiation".
- **Source artifacts:**
  - 6 emails (last one from procurement, no response)
  - 1 proposal PDF (~4 pages)
  - 1 NDA PDF (clean text-based)
  - 1 account plan docx
  - 2 meeting transcripts (intro + procurement question call)

### Account 3: Caldrisa Dental Group

- **Industry:** Healthcare / dental clinic chain
- **Country:** Spain (Madrid) — note: account is Spanish-headquartered but **all content is in English** per the language decision in [00-overview.md](00-overview.md). Treat it as an international group with English business operations.
- **Story arc:** Late-stage positive momentum. Champion (Clinical Director) just replied enthusiastically. Compliance question (GDPR + healthcare data) was resolved last week. Ready for pilot proposal.
- **Stakeholders:** 4 contacts (Clinical Director, Compliance Officer, IT Director, CFO).
- **Open opportunity:** "Patient-flow analytics pilot" — €34,000, close date in ~45 days, stage "Proposal preparation".
- **Source artifacts:**
  - 7 emails
  - 1 product specification PDF (~3 pages)
  - 1 data processing addendum PDF (clean text-based)
  - 1 compliance memo docx
  - 3 meeting transcripts

## Content guidelines

These guidelines exist because the demo's credibility depends on the content feeling *real* rather than template-generated.

### Emails

- Each email has a clear sender, recipient(s), date, subject, and body.
- Email threads must have reply chains (`In-Reply-To` and `References` headers) so that a real `mailbox.mbox` parser sees them as threads.
- Realistic email style: short, often forwarded, sometimes with quoted history. Include at least:
  - One forwarded internal handoff email per account.
  - One email with a clear unresolved question (used by alerts in Package 4).
  - One email with positive customer signal (e.g. "this looks great, let's move forward with…").
  - One email that explicitly raises a procurement, security, or compliance concern.
- Email domains should match the account: `*@brannfeld-industrial.de`, `*@rynvoss-logistics.nl`, `*@caldrisa-dental.es`. Daniel's side uses `*@danielpanea.com`.
- Use plausible business sentences, not lorem ipsum. ~80–250 words per email.

### Proposal and product-spec PDFs

- Generated via `reportlab` from structured content. Multi-page with:
  - Cover page (account name, proposal title, date)
  - Executive summary
  - Scope of work
  - Pricing table
  - Timeline
- Plain prose, no images required.

### Scanned NDA PDF (OCR demo target)

This is the highlighted demo element. The pipeline is:

1. Generate a clean text-based NDA PDF with `reportlab` (~2 pages).
2. Convert each page to an image via `pdf2image`.
3. Degrade each page image: small rotation (±2°), light Gaussian blur, JPEG re-compression to ~70% quality, slight brightness reduction.
4. Re-combine the degraded images into a new PDF using `pypdf` / `Pillow` (image-only PDF, no text layer).

This produces a PDF that *looks like* a faxed/scanned legal document. Package 3 will detect that it has no text layer and run Tesseract OCR.

`scripts/render_scanned_pdf.py` does this transformation as a reusable function so the spec can be regenerated.

### Word documents (.docx)

- Use `python-docx`.
- Style: internal account plans / handover memos. Bullet points, short paragraphs, occasional bold for headers.
- ~1–2 pages each.

### Meeting transcripts (.md)

- Plain Markdown with speaker labels, e.g.:

  ```markdown
  # Meeting: Brannfeld — Technical deep-dive

  **Date:** 2026-04-28
  **Attendees:** Lukas Wagner (Brannfeld IT Lead), Daniel Panea, Stefan Möller (Brannfeld Operations Director)

  ---

  **Daniel:** Thanks for the time. I'd like to walk through how our system handles data residency for your team.

  **Lukas:** Before that, the main concern from our side is whether the AI inference runs in the EU. Anything that touches our production data has to stay inside Germany.

  **Daniel:** Understood. The reference architecture supports two deployment modes: ...
  ```

- 30–60 turns per transcript, ~600–1200 words.
- At least one transcript per account should contain a clearly stated objection or risk.
- At least one transcript should contain a clear next-action commitment ("we'll send the audit posture summary by end of week").

### CRM CSV exports

Six CSVs covering all accounts:

- `users.csv` — internal Daniel-side owners (matches `UserOwner` model).
- `accounts.csv` — 3 rows, matches `Account` model.
- `contacts.csv` — ~10 rows total across accounts.
- `opportunities.csv` — 3 rows, one per account.
- `contracts.csv` — at most 1 row (account 3 may have a draft contract).
- `activities.csv` — 15–25 rows: tasks (`source_object = 'Task'`) and events (`source_object = 'Event'`) tied to opportunities and accounts. Use a mix of completed and open tasks; include at least one `priority = 'High'` open task per account.

Field shapes match the Pydantic models from Package 1. IDs use a clear synthetic prefix like `SYN_ACC_0001`, `SYN_OPP_0001`, etc., so it's visually obvious these are not Salesforce IDs.

### Dates and timeline coherence

- Use consistent dates throughout: emails, meetings, activities, and contract dates should tell the same story per account.
- Anchor "today" at **2026-05-13** (the date of spec authoring) so retrieval logic for "what changed this week" makes sense. The `generate_synthetic.py` script accepts a `--reference-date` parameter that defaults to `2026-05-13` so dates can be shifted later without rewriting content.
- Most recent activity per account should be within the last 14 days for Brannfeld and Caldrisa, and ~21 days ago for Rynvoss (to make the "stalled" alert fire).

## manifest.json

A machine-readable index that Package 3 reads to discover artifacts:

```json
{
  "reference_date": "2026-05-13",
  "accounts": [
    {
      "account_id": "SYN_ACC_0001",
      "account_slug": "brannfeld_industrial",
      "account_name": "Brannfeld Industrial GmbH",
      "artifacts": [
        {
          "path": "accounts/brannfeld_industrial/emails.mbox",
          "type": "email_thread",
          "format": "mbox"
        },
        {
          "path": "accounts/brannfeld_industrial/proposal_2026_q2.pdf",
          "type": "pdf",
          "format": "pdf",
          "has_text_layer": true
        },
        {
          "path": "accounts/brannfeld_industrial/signed_nda_scanned.pdf",
          "type": "pdf",
          "format": "pdf",
          "has_text_layer": false,
          "requires_ocr": true
        },
        {
          "path": "accounts/brannfeld_industrial/account_plan.docx",
          "type": "docx",
          "format": "docx"
        },
        {
          "path": "accounts/brannfeld_industrial/meeting_2026_04_15_intro.md",
          "type": "meeting_transcript",
          "format": "markdown"
        }
      ]
    }
  ],
  "crm": {
    "users": "crm/users.csv",
    "accounts": "crm/accounts.csv",
    "contacts": "crm/contacts.csv",
    "opportunities": "crm/opportunities.csv",
    "contracts": "crm/contracts.csv",
    "activities": "crm/activities.csv"
  }
}
```

## CLI

`scripts/generate_synthetic.py` exposes:

```text
uv run python scripts/generate_synthetic.py --output data/synthetic [--reference-date 2026-05-13] [--clean]
```

- `--clean` removes `data/synthetic/` first.
- The script is idempotent: running it twice with the same `--reference-date` produces byte-identical output (use fixed random seeds where any randomness is needed).

## Reuse from Uniendo Nodos

- The CRM-side data shape (account / contact / opportunity / contract / activity records) can be patterned after [core/synthetic.py](../../uniendo-nodos-private-ai/src/un_private_ai/core/synthetic.py), but **content must be rewritten** to:
  - English
  - The three new accounts (Brannfeld, Rynvoss, Caldrisa Dental)
  - Story arcs documented above
- Do **not** copy the Spanish account names (Comercio Norte Azul, etc.) — those are Uniendo Nodos client-flavored.

## Tests

`tests/test_synthetic_corpus.py`:

- Asserts `generate_synthetic.py --reference-date 2026-05-13` runs without errors.
- Asserts `data/synthetic/manifest.json` validates against an expected schema.
- Asserts every artifact path in the manifest exists on disk.
- Asserts at least one PDF per account exists.
- Asserts exactly one PDF in the corpus is flagged `requires_ocr: true`.
- Asserts each CRM CSV parses cleanly into the matching Pydantic model.
- Asserts running the generator twice with the same reference date produces identical files (SHA-256).

## Acceptance criteria

1. `uv run python scripts/generate_synthetic.py --output data/synthetic --reference-date 2026-05-13 --clean` produces a complete corpus with no errors.
2. All 3 accounts have at least: 6 emails, 2 PDFs (one with a text layer, one without), 1 docx, 2 meeting transcripts.
3. The scanned NDA PDF visibly looks like a scan when opened (rotation, slight blur, JPEG artifacts).
4. The CRM CSVs parse cleanly into Pydantic models.
5. `manifest.json` lists every artifact with correct paths and types.
6. Running the generator twice in a row produces no diff.
7. No Spanish text appears in any generated content.
