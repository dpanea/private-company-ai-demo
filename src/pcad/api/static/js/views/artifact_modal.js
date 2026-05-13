import { getArtifact } from "../api.js";
import { state } from "../state.js";
import { navigate, accountPath } from "../router.js";
import { emptyState, escapeHtml, qs, showToast, trapDialogFocus } from "../util/dom.js";
import { artifactIcon, artifactMeta, formatArtifactType, renderMarkdown } from "../util/format.js";

export async function openArtifactModal(artifactId, accountId) {
  const root = qs("#modal-root");
  root.innerHTML = renderLoadingDialog();
  const dialog = root.querySelector("dialog");
  wireDialog(dialog, accountId);
  dialog.showModal();

  try {
    const artifact = await getArtifact(artifactId);
    state.set("currentArtifactId", artifactId);
    root.innerHTML = renderArtifactDialog(artifact, accountId);
    const fullDialog = root.querySelector("dialog");
    wireDialog(fullDialog, accountId);
    fullDialog.showModal();
  } catch (error) {
    closeModal(accountId);
    showToast(error.detail || "Could not load the artifact.", "error");
  }
}

export function closeModal(accountId) {
  qs("#modal-root").innerHTML = "";
  state.set("currentArtifactId", null);
  if (accountId) navigate(accountPath(accountId));
}

function wireDialog(dialog, accountId) {
  const releaseTrap = trapDialogFocus(dialog);
  dialog.addEventListener("close", () => {
    releaseTrap();
    closeModal(accountId);
  }, { once: true });
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  });
  dialog.querySelector("[data-pcad-close-modal]")?.addEventListener("click", () => dialog.close());
}

function renderLoadingDialog() {
  return `
    <dialog aria-label="Loading artifact">
      <div class="modal-head">
        <h2>Loading source artifact</h2>
        <button class="icon-button" type="button" data-pcad-close-modal aria-label="Close">×</button>
      </div>
      <div class="modal-body">${emptyState("Loading source content...")}</div>
    </dialog>
  `;
}

function renderArtifactDialog(artifact, accountId) {
  return `
    <dialog aria-labelledby="artifact-title" data-pcad-artifact-modal="${escapeHtml(artifact.artifact_id)}">
      <div class="modal-head">
        <div>
          <p class="kicker">${escapeHtml(formatArtifactType(artifact.artifact_type))} · ${escapeHtml(artifactIcon(artifact.artifact_type))}</p>
          <h2 id="artifact-title">${escapeHtml(artifact.title)}</h2>
          <p class="meta">${escapeHtml(artifactMeta(artifact))}</p>
        </div>
        <button class="icon-button" type="button" data-pcad-close-modal aria-label="Close artifact">×</button>
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
  if (artifact.artifact_type === "email" || artifact.artifact_type === "email_thread") return renderEmailArtifact(artifact);
  if (artifact.artifact_type === "meeting_transcript") return renderTranscriptArtifact(artifact);
  if (artifact.artifact_type === "docx") return `<div class="markdown">${renderMarkdown(artifact.extracted_text)}</div>`;
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
    <div class="text-block">${escapeHtml(artifact.extracted_text || "")}</div>
  `;
}

function renderTranscriptArtifact(artifact) {
  const turns = String(artifact.extracted_text || "").split(/\n(?=[A-Z][^:\n]{1,40}:)/).filter(Boolean);
  if (!turns.length) return `<div class="text-block">${escapeHtml(artifact.extracted_text || "")}</div>`;
  return turns.map((turn) => {
    const [speaker, ...rest] = turn.split(":");
    return `
      <div class="transcript-turn">
        <p class="kicker">${escapeHtml(speaker.trim())}</p>
        <p>${escapeHtml(rest.join(":").trim())}</p>
      </div>
    `;
  }).join("");
}
