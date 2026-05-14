import { state } from "../state.js";
import { artifactPath } from "../router.js";
import { accountName, artifactIconSvg, artifactMeta, formatArtifactType } from "../util/format.js";
import { emptyState, escapeHtml } from "../util/dom.js";
import { renderAlertsPanel } from "./alerts_panel.js";
import { cumulativeCitations, renderCitationsPanel } from "./citations_panel.js";
import { bindConversationPanel, renderConversationPanel } from "./conversation_panel.js";
import { openFakeNoteModal } from "./fake_note_modal.js";
import { openArtifactModal } from "./artifact_modal.js";

export function renderAccountDetail(account) {
  const accountId = account?.account_id;
  const artifacts = state.get("artifactsByAccount")[accountId] || [];
  const alerts = state.get("alertsByAccount")[accountId] || [];
  const allThreads = state.get("threads") || [];
  const threads = allThreads.filter((thread) => thread.account_id === accountId || !thread.account_id);
  const currentThreadId = state.get("currentThreadId");
  const messages = currentThreadId ? (state.get("messagesByThread")[currentThreadId] || []) : [];
  const streamingCitations = state.get("streamingThreadId") === currentThreadId ? state.get("streamingCitations") : [];
  const chatCitations = cumulativeCitations(messages, streamingCitations);

  return `
    <section class="page detail-view-page" data-pcad-view="account-detail">
      <div class="detail-shell">
        <aside class="detail-panel" aria-label="Source artifacts">
          <div class="panel-header">
            <span class="panel-title">Source artifacts</span>
            <span class="badge">${artifacts.length}</span>
          </div>
          <div class="panel-body" data-pcad-scroll-key="artifacts:${escapeHtml(accountId || "none")}">
            ${renderArtifactGroups(artifacts, accountId)}
          </div>
        </aside>
        <section class="detail-panel" aria-label="Conversation">
          ${renderConversationPanel(account, threads, currentThreadId, messages)}
        </section>
        <aside class="detail-panel" aria-label="Citations and alerts">
          <div class="panel-body right-stack">
            <section>
              <div class="panel-header">
                <span class="panel-title">Alerts</span>
                <span class="badge">${alerts.length}</span>
              </div>
              <div class="panel-body" data-pcad-scroll-key="alerts:${escapeHtml(accountId || "none")}">${renderAlertsPanel(alerts, artifacts)}</div>
            </section>
            <section>
              <div class="panel-header">
                <span class="panel-title">Chat citations</span>
                <span class="badge">${chatCitations.length}</span>
              </div>
              <div class="panel-body" data-pcad-scroll-key="citations:${escapeHtml(currentThreadId || accountId || "none")}">${renderCitationsPanel({ citations: chatCitations }, accountId)}</div>
            </section>
          </div>
        </aside>
      </div>
    </section>
  `;
}

export function bindAccountDetail(root, account) {
  root.querySelector("[data-pcad-open-fake-note]")?.addEventListener("click", () => openFakeNoteModal(account.account_id));
  root.querySelectorAll("[data-pcad-artifact]").forEach((link) => {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      openArtifactModal(link.dataset.pcadArtifact, account.account_id, { restoreRouteOnClose: false });
    });
  });
  root.querySelectorAll("[data-pcad-open-artifact]").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.preventDefault();
      openArtifactModal(button.dataset.pcadOpenArtifact, account.account_id, { restoreRouteOnClose: false });
    });
  });
  root.querySelectorAll("[data-pcad-citation-ref]:not([data-pcad-open-artifact])").forEach((link) => {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      root.querySelector(`#citation-${CSS.escape(link.dataset.pcadCitationRef)}`)?.scrollIntoView({ block: "nearest" });
    });
  });
  bindConversationPanel(root, account);
}

function renderArtifactGroups(artifacts, accountId) {
  if (!artifacts.length) return emptyState("No source artifacts have loaded for this account.");
  const groups = new Map();
  for (const artifact of artifacts) {
    const label = formatArtifactType(artifact.artifact_type);
    groups.set(label, [...(groups.get(label) || []), artifact]);
  }

  return Array.from(groups.entries()).map(([label, items]) => `
    <section class="artifact-group">
      <div class="group-label"><span>${escapeHtml(label)}</span><span>${items.length}</span></div>
      ${items.map((artifact) => renderArtifactRow(artifact, accountId)).join("")}
    </section>
  `).join("");
}

function renderArtifactRow(artifact, accountId) {
  const href = artifactPath(accountId, artifact.artifact_id);
  return `
    <a class="artifact-row" href="${href}" data-pcad-artifact="${escapeHtml(artifact.artifact_id)}">
      <span class="icon-tile">${artifactIconSvg(artifact.artifact_type)}</span>
      <span>
        <span class="title">${escapeHtml(artifact.title)}</span>
        <span class="meta">${escapeHtml(artifactMeta(artifact))}${artifact.extraction_method === "ocr" ? '<span class="ocr">Scanned · OCR</span>' : ""}</span>
      </span>
    </a>
  `;
}
