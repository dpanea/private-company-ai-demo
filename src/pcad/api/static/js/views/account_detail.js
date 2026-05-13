import { state } from "../state.js";
import { artifactPath } from "../router.js";
import { accountName, artifactIcon, artifactMeta, formatArtifactType } from "../util/format.js";
import { emptyState, escapeHtml } from "../util/dom.js";
import { renderAlertsPanel } from "./alerts_panel.js";
import { latestAssistantMessage, renderCitationsPanel } from "./citations_panel.js";
import { bindConversationPanel, renderConversationPanel } from "./conversation_panel.js";
import { openFakeNoteModal } from "./fake_note_modal.js";

export function renderAccountDetail(account) {
  const accountId = account?.account_id;
  const artifacts = state.get("artifactsByAccount")[accountId] || [];
  const alerts = state.get("alertsByAccount")[accountId] || [];
  const allThreads = state.get("threads") || [];
  const threads = allThreads.filter((thread) => thread.account_id === accountId || !thread.account_id);
  const currentThreadId = state.get("currentThreadId");
  const messages = currentThreadId ? (state.get("messagesByThread")[currentThreadId] || []) : [];
  const latestAssistant = latestAssistantMessage(messages);

  return `
    <section class="page" data-pcad-view="account-detail">
      <div class="top-strip">
        <a class="breadcrumb" href="#/">← Accounts</a>
        <span class="warning-chip">Synthetic data only</span>
      </div>
      <div class="page-head">
        <div>
          <p class="eyebrow">${escapeHtml(account?.industry || "Account")}</p>
          <h1>${escapeHtml(accountName(account))}</h1>
          <p class="lede">${escapeHtml(account?.context || "Source-backed account memory for the public demo.")}</p>
        </div>
        <button class="secondary-action" type="button" data-pcad-open-fake-note>Add a synthetic note</button>
      </div>
      <div class="detail-shell">
        <aside class="detail-panel" aria-label="Source artifacts">
          <div class="panel-header">
            <span class="panel-title">Source artifacts</span>
            <span class="badge">${artifacts.length}</span>
          </div>
          <div class="panel-body">
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
              <div class="panel-body">${renderAlertsPanel(alerts, artifacts)}</div>
            </section>
            <section>
              <div class="panel-header">
                <span class="panel-title">Latest citations</span>
                <span class="badge">${latestAssistant?.citations?.length || 0}</span>
              </div>
              <div class="panel-body">${renderCitationsPanel(latestAssistant, accountId)}</div>
            </section>
          </div>
        </aside>
      </div>
    </section>
  `;
}

export function bindAccountDetail(root, account) {
  root.querySelector("[data-pcad-open-fake-note]")?.addEventListener("click", () => openFakeNoteModal(account.account_id));
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
      <span class="type-icon">${escapeHtml(artifactIcon(artifact.artifact_type))}</span>
      <span>
        <span class="artifact-title">${escapeHtml(artifact.title)}</span>
        <span class="artifact-meta">${escapeHtml(artifactMeta(artifact))}</span>
        ${artifact.extraction_method === "ocr" ? '<span class="warning-chip">Scanned · OCR</span>' : ""}
      </span>
    </a>
  `;
}
