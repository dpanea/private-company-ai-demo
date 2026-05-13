# Package 5 — Frontend

**Purpose.** Wire the Claude Design-produced HTML/CSS into a working single-page demo: account selector, source artifact explorer, conversation panel with workflow buttons and free-text input, citations sidebar, alerts panel, and the fake-note form. Vanilla HTML / CSS / JavaScript only — **no framework, no build step**.

**Depends on:** Package 1 (for API contract knowledge — schemas only).

**Soft-depends on:** Package 4 (real API). Can be developed against a JSON mock first.

**Blocks:** Package 6.

**Estimated size:** medium (~1500 LOC JS, plus the HTML/CSS that Claude Design provides).

## Source of the visual design

Daniel will produce HTML+CSS via Claude Design (web). The exported markup is the **canonical source for visual design and structure**. The coding agent's job is to:

1. Place the Claude Design HTML/CSS files into the repo at the paths below.
2. Add the JavaScript that wires the markup to the API.
3. Add minimal markup hooks (`data-*` attributes, IDs) where wiring needs them — only if not already present.

**Do not redesign.** If the Claude Design markup is missing a hook the JS needs, prefer adding a `data-pcad-*` attribute over restructuring the DOM.

## Claude Design brief

This section is the brief to paste into Claude Design (and to keep next to the design session as a reference). It defines what the design must produce and the brand constraints it must respect. It is **not** instructions for the coding agent — it is upstream of that.

### Project context

The product is a **public demo of a private "company memory" copilot** for B2B sales and account teams. Visitors are technical evaluators, partner consultancies (Salesforce/HubSpot consultants, RevOps shops, GDPR consultants), and Mittelstand digitalization buyers in DACH. The site needs to feel like a serious technical product, not a consumer chatbot. Daniel Panea is the author — PhD in physics, sovereign-AI specialist, premium freelance positioning.

### Tone of voice

- Direct, technical, restrained.
- "Scientific rigor meets hacker pragmatism" — see [CONTEXT ANCHOR, PROFESSIONAL PROFILE & EXPERTISE](../../../Notes/08%20Personal%20Brand/CONTEXT%20ANCHOR,%20PROFESSIONAL%20PROFILE%20&%20EXPERTISE.md) in Daniel's vault.
- Treat the visitor as a peer who understands B2B sales and basic infrastructure terms.
- No marketing fluff. Avoid: "magical", "smart", "powerful", "unleash", "supercharge", "AI-powered", "revolutionary", "intelligent".
- Prefer: "private", "source-backed", "your data", "company memory", "on your infrastructure", "audit-friendly", "open weights".

### Visual references (in spirit, not in detail)

- **Inspirations:** Linear, Anthropic site, Notion's enterprise pages, well-built developer tools. Restrained typography, generous whitespace, monospace accents for IDs and citations.
- **Anti-inspirations:** generic AI startup landing pages with rainbow gradients, cute illustrations of robots or brains, bouncy emoji-heavy chat UIs, B2C SaaS marketing pages.

### Color and typography constraints

- **Palette:** keep it small. One accent color (Daniel's existing site uses a deep blue/teal — match if you have access to `danielpanea.com`, otherwise pick one cool accent). Otherwise: a neutral background (light *or* dark — pick one and commit), strong text, subtle borders.
- **Severity colors** for alert cards must be semantic and recognisable: a calm info color (e.g. blue/gray), a warning color (amber/orange), and a critical color (red). These three are non-negotiable for alert semantics.
- **Typography:** one sans-serif for body and headings (Inter, IBM Plex Sans, or system stack). One monospace for citation labels, record IDs, and any code-shaped content (JetBrains Mono, IBM Plex Mono, or system mono). Max one webfont family loaded from a CDN; ideally use a system stack and avoid the CDN entirely.
- **Density:** the demo is information-dense by design (three panels, lists of artifacts, citations). Default to comfortable density, not airy. Linear-style row heights are a good reference.
- **Elevation:** use borders and very subtle shadows. No heavy drop shadows, no card "lift on hover" effects.

### Required screens and components

The design must include all of the following. Naming below is for reference only; Claude Design can rename for the actual UI text.

#### 1. Landing page (separate from the demo SPA)

Lives at the root of the subdomain. One static HTML file. Sections defined in [06-package-deployment-landing.md](06-package-deployment-landing.md). Visual style consistent with the demo SPA so the transition is seamless.

#### 2. Demo SPA — three core views

a. **Account list view**
- Header with product name and a one-line tagline.
- A row or grid of three account cards. Each card shows: account name, industry, country, a small status pill (e.g. "Mid-funnel", "Stalled", "Late stage positive"), and one-line context.
- A clear primary action per card to enter the account view.
- No login, no sign-up, no email gate.

b. **Account detail view (three-panel layout)**
- Top bar with breadcrumb back to account list, account name, and the synthetic-data warning chip.
- **Left panel — Source artifacts**: a scrollable list of artifacts grouped by type. Each artifact row needs a clear icon for its type, a title, a short metadata line (sender + date for emails, page count for PDFs, attendees count + date for meetings, etc.), and a badge for "Scanned · OCR" on the one OCR'd PDF. Clicking opens the artifact modal.
- **Middle panel — Conversation**: sticky workflow button row at the top (5 buttons), the thread title and account context underneath, the message list (user / assistant bubbles), and a sticky free-text composer at the bottom with a send button. The composer must accommodate multi-line input and an "Enter to send, Shift+Enter for newline" affordance.
- **Right panel — Citations and alerts**: two stacked sections. Top: alerts for the current account (cards with severity badge, title, body, evidence chips). Bottom: citations from the most recent assistant message (each citation is a chip linking to the relevant artifact).

c. **Artifact modal**
- Triggered from the left panel.
- Header with artifact title, type icon, and close button.
- Body: scrollable content area. For PDFs: vertically stacked page images. For emails: a header block (From / To / Date / Subject) followed by body text. For meeting transcripts: speaker-labelled turns. For Word documents: rendered markdown.
- For OCR'd artifacts: a clearly visible callout at the top stating that the text was extracted via OCR from a scanned document.

#### 3. Component-level designs

These appear inside the views above but warrant explicit attention:

- **Workflow button row** — five buttons with concise labels: "Brief me before a call", "What changed?", "Open risks", "Draft follow-up", "Next action". Visually grouped, sticky at top of middle panel, become the entry point for new conversation threads.
- **Conversation bubbles** — user bubble (right-aligned, accent background, white text or contrasting), assistant bubble (left-aligned, light background, dark text). Assistant bubble has space below for citation chips. Streaming state shows a subtle pulsing cursor at the end of the in-progress text.
- **Citation chip** — small inline pill with monospace label `Source: Email msg-abc-123`. Clickable; should visually communicate "this is a link to a source".
- **Alert card** — severity icon + colored left border, title in regular weight, body text below, evidence chips at the bottom. Three severity levels visually distinct.
- **Fake-note form (modal)** — clear synthetic-data warning at top (amber banner, unmissable), four form fields (type select, title, body textarea, date picker), submit and cancel buttons.
- **Toast / banner** — non-intrusive feedback for "added", "rate limited", "budget exhausted". Three styles: success, warning, error.
- **Loading skeleton** — neutral gray blocks matching the shape of the content being loaded. Used for the left panel, the alerts panel, and the message list during fetch.
- **Empty states** — every list view (artifacts, alerts, threads, citations) has an explicit "nothing here yet" state, not blank space.

#### 4. Persistent UI elements across all views

- **Header**: product name on the left, a "What is this?" link to the landing page on the right.
- **Synthetic-data warning chip**: present somewhere in every view of the SPA so it's never forgotten that this is a demo with fake data.

### Microcopy

All in English. Plain professional language. No exclamation marks. No emoji in the UI (icons via inline SVG or an icon font are fine — emoji are not).

Specific microcopy that must appear somewhere visible:

- Landing hero: *"Never walk into a client call cold again."*
- Subline: *"Turn scattered emails, meeting notes, CRM history, and account documents into a private AI copilot — without uploading your accounts to anyone's cloud."*
- Synthetic-data warning on the fake-note form: *"This public demo uses synthetic data only. Do not enter real or confidential client information. Notes are stored only for your browser session."*
- Daily-budget exhaustion banner: *"The public demo has reached its daily budget. The architecture is still here to explore — try again tomorrow, or book a private walkthrough for live interaction."*

### Layout and responsiveness

- **Primary target:** 1280px+ desktop width. The three-panel layout assumes a wide viewport.
- **Acceptable degradation at narrower widths:**
  - Below 1024px: the left panel collapses to a top tab bar.
  - Below 768px: the layout becomes a single column with a tab switcher for artifacts / conversation / alerts.
- **Mobile is not a primary target.** A passable mobile experience is fine; perfect mobile is out of scope.

### Accessibility

- Color contrast meets WCAG AA.
- All interactive elements are buttons or links, never `<div>` with a click handler.
- Focus states are visible (do not remove the focus outline; restyle it instead).
- Modals trap focus and close on `Esc`.
- All icons have an associated text label (visible or `aria-label`).

### What Claude Design must NOT do

- No JavaScript framework (no React, Vue, Svelte). No build tooling.
- No Tailwind. Plain CSS only — one file is fine, multiple files organized by component is also fine. Pure utility-class soup like Tailwind makes the wiring step harder.
- No emoji used as UI elements.
- No stock photos of people.
- No animated illustrations or robot/brain motifs.
- No carousels or auto-playing anything.
- No third-party UI component libraries.
- No analytics/tracking scripts.
- No advertising-style call-to-action banners ("Limited time!", "Trusted by 1000+ teams!", etc.).

### Output format expected

- A single `index.html` for the demo SPA.
- A single `index.html` (or a small set of HTML files if multi-section) for the landing page.
- One or more plain `.css` files. No preprocessor (no SCSS, no PostCSS).
- All asset files (icons, any images) in an `assets/` folder. SVG icons preferred for crispness at any size.
- Semantic HTML: `<header>`, `<main>`, `<aside>`, `<button>`, `<form>`, `<dialog>` for modals, etc.
- Class names are stable enough for JS wiring (BEM, plain semantic names, or hash-free single names — all acceptable).
- No `<script>` tags with logic. A single `<script type="module" src="/static/js/main.js"></script>` is added later by the coding agent.

### What the coding agent will add after Claude Design

The coding agent (this Package 5's implementer) will:

- Add `data-pcad-*` attributes to elements that need to be found by JS.
- Add `id="app-root"`, `id="modal-root"`, `id="toast-root"` if not already present.
- Add the `<script src="https://cdn.jsdelivr.net/npm/marked@12/marked.min.js"></script>` and the `<script type="module" src="/static/js/main.js"></script>` lines to `index.html`.
- Wire the API client, state, routing, and SSE consumer per the rest of this document.

Claude Design does not need to think about any of these — focus on the visual and structural design.

## Outputs

```text
src/pcad/api/static/
├── index.html              # provided by Claude Design, lightly augmented with data-attrs
├── css/
│   └── styles.css          # provided by Claude Design (one or more files)
├── js/
│   ├── main.js             # entry: bootstraps the SPA on DOMContentLoaded
│   ├── api.js              # thin fetch wrappers per API endpoint
│   ├── state.js            # in-memory app state + simple pub/sub
│   ├── router.js           # hash-based routing (#/accounts/{id})
│   ├── views/
│   │   ├── account_list.js
│   │   ├── account_detail.js
│   │   ├── artifact_modal.js
│   │   ├── conversation_panel.js
│   │   ├── citations_panel.js
│   │   ├── alerts_panel.js
│   │   └── fake_note_modal.js
│   ├── sse.js              # SSE consumer for /messages/stream
│   └── util/
│       ├── dom.js          # tiny dom helpers (qs, qsa, on, html-escape)
│       └── format.js       # date formatting, markdown-to-html (use a small CDN-loaded lib)
└── assets/
    └── (icons, images Claude Design ships)
```

No bundler, no transpilation. All `js/` files are native ES modules loaded via `<script type="module">`.

If a markdown-to-HTML conversion is needed for assistant messages, use a small CDN-loaded library like [marked.js](https://cdn.jsdelivr.net/npm/marked/marked.min.js) loaded as a `<script>` (no npm). Sanitize the output via simple regex or by rendering only into elements with restricted innerHTML.

## SPA structure and routing

Hash-based routing:

| Route | View |
|---|---|
| `#/` or empty | Account list |
| `#/accounts/{account_id}` | Account detail (default thread, or list of threads if any exist) |
| `#/accounts/{account_id}/threads/{thread_id}` | Account detail with a specific thread open |
| `#/accounts/{account_id}/artifacts/{artifact_id}` | Account detail with the artifact modal open |

Browser back/forward navigation should work naturally with hash changes.

## App state shape (state.js)

A single mutable object held by `state.js` with `subscribe(key, callback)` and `set(key, value)` helpers. Views subscribe to the slices they need.

```javascript
const state = {
  session: null,                    // { session_id, created_at }
  accounts: [],                     // [Account]
  currentAccountId: null,           // string | null
  currentArtifactId: null,          // string | null
  artifactsByAccount: {},           // {account_id: [RawArtifact]}
  alertsByAccount: {},              // {account_id: [ProactiveAlert]}
  fakeNotesByAccount: {},           // {account_id: [FakeNote]}
  threads: [],                      // [ConversationThread] for current session
  currentThreadId: null,            // string | null
  messagesByThread: {},             // {thread_id: [ConversationMessage]}
  isStreaming: false,
  streamingThreadId: null,
  streamingTokens: '',              // running buffer of streamed tokens
  lastError: null,                  // {message, code} | null
  rateLimitedUntil: null,           // unix ms timestamp | null
};
```

State mutations are always done via `state.set(key, value)`. No direct mutation. Subscribers are called synchronously after a `set`.

## API client (api.js)

Thin wrappers around `fetch`. Every call:

- Sends credentials so the session cookie travels (`credentials: 'same-origin'`).
- Throws on non-2xx responses with a typed error that carries `{ status, code, detail }`.
- Returns the JSON body on success.

One function per endpoint. Names mirror the route paths:

```javascript
export async function getSession(): Promise<Session>
export async function listAccounts(): Promise<Account[]>
export async function getAccount(id): Promise<Account>
export async function listAccountArtifacts(id): Promise<RawArtifact[]>
export async function getAccountAlerts(id): Promise<ProactiveAlert[]>
export async function getArtifact(id): Promise<RawArtifact>
export async function listThreads(): Promise<ConversationThread[]>
export async function createThread({account_id, workflow_seed}): Promise<ConversationThread>
export async function getThread(id): Promise<ConversationThread>
export async function listMessages(threadId): Promise<ConversationMessage[]>
export function streamMessage(threadId, message, handlers): AbortController
export async function listFakeNotes(accountId): Promise<FakeNote[]>
export async function addFakeNote(accountId, payload): Promise<{note: FakeNote, alerts: ProactiveAlert[]}>
export async function deleteFakeNote(noteId): Promise<void>
```

## SSE consumer (sse.js)

The `streamMessage` function is the only non-fetch API call. It uses `EventSource` if available, but because POST is required for the body, **fall back to `fetch` with a `ReadableStream` reader** to parse SSE manually.

Recommended implementation: `fetch` + manual SSE parsing. The stream produces these events:

| Event | Data shape | Handler call |
|---|---|---|
| `user_message` | `ConversationMessage` (the user message that was inserted) | `handlers.onUserMessage(msg)` |
| `status` | `{ status: "thinking" \| "generating" }` | `handlers.onStatus(s)` |
| `token` | `{ content: string }` | `handlers.onToken(s) — appends to a buffer` |
| `done` | `{ assistant_message: ConversationMessage, thread: ConversationThread }` | `handlers.onDone(d)` |
| `error` | `{ detail: string, code?: string }` | `handlers.onError(e)` |

Return an `AbortController` so the caller can cancel.

## Views

### account_list.js

Renders the three synthetic accounts as cards (Claude Design provides the card markup). Each card click navigates to `#/accounts/{id}`.

### account_detail.js

The three-panel layout:

- **Left panel** (`artifact_modal.js` triggers from here): list of `raw_artifacts` for the account, grouped by `artifact_type`, with visual indicators per type:
  - Email → envelope icon + sender + subject + date
  - PDF → document icon, with a "scanned" badge if `extraction_method == "ocr"`
  - Word document → docx icon
  - Meeting transcript → calendar icon + date + attendees count
  - CRM record → CRM icon

  Clicking an artifact opens the artifact modal.

- **Middle panel**: conversation. See `conversation_panel.js`.

- **Right panel**: citations + alerts. See `citations_panel.js` and `alerts_panel.js`.

### artifact_modal.js

Modal showing the artifact's content:

- For PDFs: render the rendered page PNGs (`/api/artifacts/{id}/page/{n}`) in a vertical scroll. Show a callout for OCR'd PDFs explaining that the text was extracted via OCR.
- For emails: render `extracted_text` with a header block (from, to, date, subject).
- For meeting transcripts: render speaker turns with styling.
- For docx: render `extracted_text` with preserved markdown headings.

Close on `Esc`, backdrop click, or X button.

### conversation_panel.js

The center of the demo. Renders:

- A row of workflow buttons at the top: *Brief me before a call*, *What changed?*, *Open risks*, *Draft follow-up*, *Next action*. Each click POSTs to `/api/threads` with the corresponding `workflow_seed`, then opens the new thread.
- A thread selector dropdown (when multiple threads exist for the current account).
- The message list (user + assistant turns). User messages right-aligned, assistant left-aligned. Assistant messages render their `content` as markdown.
- Citation chips at the end of each assistant message that link/scroll to entries in the right panel.
- A free-text input box with a Send button. Pressing Enter (without Shift) submits.

When sending a message:

1. Disable the input.
2. Set `state.isStreaming = true`.
3. Call `streamMessage(threadId, text, handlers)`.
4. On `user_message`: append the user bubble.
5. On `status === "thinking"`: show a "Searching company memory…" placeholder.
6. On `status === "generating"`: replace with a streaming bubble.
7. On each `token`: append to `state.streamingTokens` and re-render the streaming bubble.
8. On `done`: replace the streaming bubble with the final assistant message (with citations), refresh `messagesByThread`, re-enable input.
9. On `error`: show an error toast and re-enable input.

If the API returns 429 (rate limited), show a friendly toast: *"Slow down — too many requests. Try again in a minute."* and set `state.rateLimitedUntil` to a 60-second cooldown.

If the API response indicates the daily budget is exhausted (the canned assistant message), still display it as a normal assistant turn but show a banner at the top of the conversation suggesting booking a private walkthrough.

### citations_panel.js

Listens to the active assistant message. For each citation in `message.citations`:

- Show the citation label (`Source: Email msg-123`), the source title, the source date, and the excerpt.
- Click the citation → open the artifact modal for the corresponding `artifact_id` if present in metadata.

### alerts_panel.js

Lists `state.alertsByAccount[currentAccountId]`. Each alert card shows:

- Severity badge (info / warning / critical).
- Alert title.
- Body markdown (rendered).
- Evidence links — chips for each artifact referenced.

Refreshes when:

- Account changes.
- A fake note is added (the POST response includes the new alerts; merge them in).

### fake_note_modal.js

Triggered by a "Add a synthetic note" button on the account detail view.

Form fields:

- Note type (select: `meeting_summary` / `email_summary` / `task` / `risk` / `general`)
- Title (text input)
- Body (textarea)
- Note date (date picker, defaults to today)

Below the form, a clearly visible warning banner:

> This public demo uses synthetic data only. Do not enter real or confidential client information here. Notes are stored only for your browser session.

Submit → `POST /api/accounts/{aid}/fake-notes` → on success:

- Close modal.
- Toast: "Synthetic note added. The system has updated its company memory."
- Refresh fake-notes list and alerts list for this account.
- Optionally surface a small inline prompt: "Try 'What changed?' to see how the system reacts."

## Markdown rendering

Use `marked.js` via CDN, loaded once in `index.html`:

```html
<script src="https://cdn.jsdelivr.net/npm/marked@12/marked.min.js"></script>
```

Use `marked.parse(text)` to convert assistant message content to HTML. Inject into a container with `innerHTML`. Sanitize aggressively:

- Strip `<script>`, `<style>`, `<iframe>` tags via post-processing regex.
- Allow only a whitelist of tags: `p, br, strong, em, ul, ol, li, blockquote, code, pre, h1-h4, a`. Strip everything else.

A minimal sanitizer using DOMParser is preferable to regex if Claude Design ships it; otherwise the regex approach is acceptable for the demo's controlled content.

## Error and loading states

Every view handles:

- **Loading**: show a skeleton or spinner during the initial fetch.
- **Empty**: explicit "no data" message rather than blank.
- **Error**: an inline error banner with a "Retry" button.

## Accessibility

- All interactive elements are buttons or links, not divs with click handlers.
- Modals trap focus and close on `Esc`.
- All images and icons have `alt` text.
- Color is never the only signal for severity — text labels accompany badges.

## Index.html shape

The single `index.html` Claude Design produces should follow this skeleton (the AI design may flesh it out):

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Private Company Memory Demo</title>
  <link rel="stylesheet" href="/static/css/styles.css">
</head>
<body>
  <header>...</header>
  <main id="app-root">
    <!-- Views are rendered into here by JS -->
  </main>
  <div id="modal-root"></div>
  <div id="toast-root"></div>

  <script src="https://cdn.jsdelivr.net/npm/marked@12/marked.min.js"></script>
  <script type="module" src="/static/js/main.js"></script>
</body>
</html>
```

## Tests

Frontend tests for vanilla JS without a framework are minimal. The recommended approach:

- A small `tests/frontend/test_smoke.html` that opens the demo, performs a scripted interaction via `playwright` (run via Python `pytest-playwright`), and asserts:
  - Account list loads three accounts.
  - Clicking an account shows artifacts, conversation panel, alerts.
  - Clicking "Brief me before a call" starts a thread and streams a response.
  - Adding a fake note shows a new alert.

This requires `playwright` as a dev dependency. Mark these tests `@pytest.mark.requires_playwright` and skip if not installed. Acceptance criteria does not require these to pass in CI — the manual demo walkthrough is sufficient for v1.

## Reuse from Uniendo Nodos

- The SSE event protocol from [web/chat_service.py](../../uniendo-nodos-private-ai/src/un_private_ai/web/chat_service.py).
- The session-cookie pattern from [web/auth.py](../../uniendo-nodos-private-ai/src/un_private_ai/web/auth.py) — adapted to anonymous (no password).

**Do not copy** the Uniendo Nodos frontend code itself — Claude Design provides the visual layer.

## Acceptance criteria

1. `index.html` loads at `/` and renders the account list with three accounts after the API is reachable.
2. Selecting an account renders the three-panel layout with real data.
3. Clicking a workflow button starts a thread, streams an assistant response within ~15 seconds, and shows citations.
4. Free-text follow-ups in the same thread work and respect account stickiness.
5. Clicking an artifact opens the modal with the artifact's content (PDFs render as images).
6. Clicking the OCR'd PDF clearly shows the scanned-look image and a banner indicating OCR.
7. Adding a fake note via the modal triggers a refresh of alerts.
8. Per-session isolation works: opening the demo in a private window shows no fake notes from the main session.
9. No JavaScript framework is in `package.json` (which itself should not exist).
10. The page loads and runs with all assets self-served from the FastAPI app (no external CDN dependency other than `marked.js`).
