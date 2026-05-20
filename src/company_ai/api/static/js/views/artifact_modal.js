import { getArtifact } from "../api.js";
import { state } from "../state.js";
import { navigate, accountPath } from "../router.js";
import { emptyState, escapeHtml, qs, showToast, trapDialogFocus } from "../util/dom.js";
import { artifactIcon, artifactIconSvg, artifactMeta, formatArtifactType, renderMarkdown } from "../util/format.js";

export async function openArtifactModal(artifactId, accountId, options = { restoreRouteOnClose: true }) {
  const root = qs("#modal-root");
  root.innerHTML = renderLoadingDialog();
  const dialog = root.querySelector("dialog");
  wireDialog(dialog, accountId, options);
  dialog.showModal();

  try {
    const artifact = await getArtifact(artifactId);
    state.set("currentArtifactId", artifactId);
    root.innerHTML = renderArtifactDialog(artifact, accountId);
    const fullDialog = root.querySelector("dialog");
    wireDialog(fullDialog, accountId, options);
    fullDialog.showModal();
  } catch (error) {
    closeModal(accountId);
    showToast(error.detail || "Could not load the artifact.", "error");
  }
}

export function closeModal(accountId, options = { restoreRouteOnClose: true }) {
  qs("#modal-root").innerHTML = "";
  state.set("currentArtifactId", null);
  if (accountId && options.restoreRouteOnClose) navigate(accountPath(accountId));
}

function wireDialog(dialog, accountId, options) {
  const releaseTrap = trapDialogFocus(dialog);
  dialog.addEventListener("close", () => {
    releaseTrap();
    closeModal(accountId, options);
  }, { once: true });
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  });
  dialog.querySelector("[data-app-close-modal]")?.addEventListener("click", () => dialog.close());
}

function renderLoadingDialog() {
  return `
    <dialog aria-label="Loading artifact">
      <div class="modal-head">
        <div class="modal-head-text">
          <h2>Loading source artifact</h2>
        </div>
        <button class="icon-button" type="button" data-app-close-modal aria-label="Close">×</button>
      </div>
      <div class="modal-body">${emptyState("Loading source content...")}</div>
    </dialog>
  `;
}

function renderArtifactDialog(artifact, accountId) {
  return `
    <dialog class="artifact-dialog" aria-labelledby="artifact-title" data-app-artifact-modal="${escapeHtml(artifact.artifact_id)}">
      <div class="modal-head">
        <div class="modal-head-text">
          <span class="icon-tile modal-type-icon">${artifactIconSvg(artifact.artifact_type)}</span>
          <div>
            <p class="kicker">${escapeHtml(formatArtifactType(artifact.artifact_type))} · ${escapeHtml(artifactIcon(artifact.artifact_type))}</p>
            <h2 id="artifact-title">${escapeHtml(artifact.title)}</h2>
            <p class="meta">${escapeHtml(artifactMeta(artifact))}</p>
          </div>
        </div>
        <button class="icon-button" type="button" data-app-close-modal aria-label="Close artifact">×</button>
      </div>
      <div class="modal-body">
        <div class="artifact-content">
          ${artifact.extraction_method === "ocr" ? '<div class="callout warning">Text for this artifact was extracted via OCR from a scanned document. Verify against the page image when precision matters.</div>' : ""}
          ${renderArtifactBody(artifact, accountId)}
        </div>
      </div>
    </dialog>
  `;
}

function renderArtifactBody(artifact) {
  if (artifact.artifact_type === "pdf") return renderPdfArtifact(artifact);
  if (artifact.artifact_type === "email") return renderEmailArtifact(artifact);
  if (artifact.artifact_type === "meeting_transcript") return renderTranscriptArtifact(artifact);
  if (artifact.artifact_type === "docx") return `<article class="document-page docx-page word-document markdown">${renderMarkdown(promoteDocxTitleLines(artifact.extracted_text))}</article>`;
  return `<div class="text-block">${escapeHtml(artifact.extracted_text || "No extracted text available.")}</div>`;
}

function renderPdfArtifact(artifact) {
  const urls = artifact.page_urls || artifact.metadata?.page_urls || [];
  if (!urls.length) {
    return `
      <div class="rendered-page">Rendered PDF page images are not available yet.</div>
      <div class="text-block">${escapeHtml(artifact.extracted_text || "")}</div>
    `;
  }
  return urls.map((url, index) => `
    <figure class="rendered-page">
      <img src="${escapeHtml(url)}" alt="${escapeHtml(artifact.title)} page ${index + 1}">
    </figure>
  `).join("");
}

function renderEmailArtifact(artifact) {
  const metadata = artifact.metadata || {};
  return `
    <div class="artifact-header-block">
      <p><strong>From:</strong> ${escapeHtml(metadata.from || metadata.sender || "Unknown")}</p>
      <p><strong>To:</strong> ${escapeHtml(metadata.to || "Unknown")}</p>
      <p><strong>Date:</strong> ${escapeHtml(metadata.date || artifact.created_at || "Unknown")}</p>
      <p><strong>Subject:</strong> ${escapeHtml(metadata.subject || artifact.title)}</p>
    </div>
      <div class="email-body">${renderParagraphs(artifact.extracted_text)}</div>
  `;
}

function renderTranscriptArtifact(artifact) {
  const turns = String(artifact.extracted_text || "").split(/\n(?=(?:\*\*)?[A-Z][^:\n]{1,40}:(?:\*\*)?)/).filter(Boolean);
  if (!turns.length || turns.length === 1) {
    return `<article class="document-page meeting-page markdown">${renderMarkdown(withMarkdownLineBreaks(artifact.extracted_text || ""))}</article>`;
  }
  return turns.map((turn) => {
    const [speaker, ...rest] = turn.replaceAll("**", "").split(":");
    return `
      <div class="transcript-turn">
        <p class="kicker">${escapeHtml(speaker.trim())}</p>
        <p>${escapeHtml(rest.join(":").trim())}</p>
      </div>
    `;
  }).join("");
}

function renderParagraphs(text) {
  const paragraphs = String(text || "")
    .replace(/^#\s+.+(?:\n+|$)/, "")
    .split(/\n{2,}/)
    .map((part) => part.trim())
    .filter(Boolean);
  if (!paragraphs.length) return '<p>No extracted text available.</p>';
  return paragraphs.map((part) => `<p>${escapeHtml(reflowParagraph(part))}</p>`).join("");
}

function reflowParagraph(text) {
  return String(text || "")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .join(" ");
}

function promoteDocxTitleLines(text) {
  const raw = String(text || "");
  if (!raw.trim()) return raw;
  const paragraphs = raw.split(/\n{2,}/);
  let promoted = 0;
  for (let i = 0; i < paragraphs.length && promoted < 2; i += 1) {
    const part = paragraphs[i];
    const trimmed = part.trim();
    if (!trimmed) continue;
    if (/^#{1,6}\s/.test(trimmed)) break;
    if (/^[-*+]\s|^\d+\.\s|^>\s/.test(trimmed)) break;
    paragraphs[i] = `${promoted === 0 ? "# " : "## "}${trimmed}`;
    promoted += 1;
  }
  return paragraphs.join("\n\n");
}

function withMarkdownLineBreaks(text) {
  return String(text || "")
    .split("\n")
    .map((line) => line.trimEnd())
    .join("  \n");
}
