import { resetSession } from "../api.js";
import { state } from "../state.js";
import { artifactPath, threadPath } from "../router.js";
import { accountName, artifactIconSvg, artifactMeta, formatArtifactType, workflowLabel } from "../util/format.js";
import { emptyState, escapeHtml, showToast } from "../util/dom.js";
import { bindConversationPanel, renderConversationPanel, startThread } from "./conversation_panel.js";
import { openFakeNoteModal } from "./fake_note_modal.js";
import { openArtifactModal } from "./artifact_modal.js";

const workflows = ["new_chat", "call_briefing", "what_changed", "open_risks", "follow_up_draft", "next_action"];
const artifactOrder = ["Email", "PDF", "Word document", "Meeting", "Test notes"];

export function renderAccountDetail(account, accounts = []) {
  const accountId = account?.account_id || null;
  const artifactsByAccount = state.get("artifactsByAccount") || {};
  const artifacts = accountId
    ? (artifactsByAccount[accountId] || [])
    : accounts.flatMap((item) => artifactsByAccount[item.account_id] || []);
  const threads = state.get("threads") || [];
  const currentThreadId = state.get("currentThreadId");
  const messages = currentThreadId ? (state.get("messagesByThread")[currentThreadId] || []) : [];

  return `
    <section class="page detail-view-page" data-pcad-view="company-memory">
      <div class="detail-shell memory-shell">
        <aside class="detail-panel control-panel" aria-label="Chat controls">
          <div class="panel-body control-panel-body">
            <label class="account-picker">
              <span class="kicker">Client context</span>
              <select data-pcad-account-select>
                <option value="">No client selected</option>
                ${accounts.map((item) => `<option value="${escapeHtml(item.account_id)}" ${item.account_id === accountId ? "selected" : ""}>${escapeHtml(accountName(item))}</option>`).join("")}
              </select>
            </label>
            <div class="workflow-stack" data-pcad-workflows>
              ${workflows.map((seed) => `<button class="workflow-btn ${seed === "new_chat" ? "new-chat" : ""}" type="button" data-pcad-workflow="${seed}">${workflowLabel(seed)}</button>`).join("")}
            </div>
            ${renderThreadHistory(threads, currentThreadId)}
            <div class="thread-actions sidebar-actions">
              <button class="secondary-action memory-note-action" type="button" data-pcad-open-fake-note title="${accountId ? "Add a test note for this client" : "Pick a client first to add a test note"}">Add test note</button>
              <button class="secondary-action session-reset-action" type="button" data-pcad-reset-demo-session>Reset demo</button>
            </div>
          </div>
        </aside>
        <section class="detail-panel" aria-label="Conversation">
          ${renderConversationPanel(account, threads, currentThreadId, messages)}
        </section>
        <aside class="detail-panel source-panel" aria-label="Source artifacts">
          <div class="panel-header">
            <span class="panel-title">Source artifacts</span>
            <span class="badge">${artifacts.length}</span>
          </div>
          <div class="panel-body" data-pcad-scroll-key="artifacts:${escapeHtml(accountId || "all")}">
            ${accountId
              ? renderArtifactGroups(artifacts, accountId)
              : renderArtifactGroupsByAccount(accounts, artifactsByAccount)}
          </div>
        </aside>
      </div>
    </section>
  `;
}

export function bindAccountDetail(root, account, accounts = [], options = {}) {
  const loadArtifactsForAccount = options.loadArtifactsForAccount || (async () => []);
  const selectedAccountId = account?.account_id || null;

  root.querySelector("[data-pcad-account-select]")?.addEventListener("change", async (event) => {
    const accountId = event.target.value || null;
    state.set("currentAccountId", accountId);
    if (accountId) {
      try {
        await loadArtifactsForAccount(accountId);
      } catch (error) {
        showToast(error.detail || "Could not load source artifacts.", "error");
      }
    }
  });

  root.querySelectorAll("[data-pcad-workflow]").forEach((button) => {
    button.addEventListener("click", async () => {
      const workflow = button.dataset.pcadWorkflow;
      if (workflow === "new_chat") {
        await startThread(selectedAccountId, null, { streamSeed: false });
        return;
      }
      await startThread(selectedAccountId, workflow, { streamSeed: true, account });
    });
  });

  root.querySelectorAll("[data-pcad-thread-chip]").forEach((button) => {
    button.addEventListener("click", () => {
      window.location.hash = threadPath(null, button.dataset.pcadThreadChip).slice(1);
    });
  });

  root.querySelector("[data-pcad-open-fake-note]")?.addEventListener("click", () => {
    if (!selectedAccountId) {
      const select = root.querySelector("[data-pcad-account-select]");
      select?.focus();
      showToast("Pick a client first — the test note attaches to one client.", "warning");
      return;
    }
    openFakeNoteModal(selectedAccountId);
  });

  root.querySelector("[data-pcad-reset-demo-session]")?.addEventListener("click", async () => {
    try {
      await resetSession();
      window.location.assign("/demo");
    } catch (error) {
      showToast(error.detail || "The demo session could not be reset.", "error");
    }
  });

  root.querySelectorAll("[data-pcad-artifact]").forEach((link) => {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      openArtifactModal(link.dataset.pcadArtifact, selectedAccountId, { restoreRouteOnClose: false });
    });
  });
  root.querySelectorAll("[data-pcad-open-artifact]").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.preventDefault();
      openArtifactModal(button.dataset.pcadOpenArtifact, selectedAccountId, { restoreRouteOnClose: false });
    });
  });
  bindConversationPanel(root, account, { loadArtifactsForAccount });
}

function renderThreadHistory(threads, currentThreadId) {
  if (!threads.length) {
    return `
      <details class="thread-history-group" open>
        <summary class="group-label"><span>Recent chats</span><span>0</span></summary>
        <div class="thread-history-list"><span class="thread-history-empty">Recent chats will appear here.</span></div>
      </details>
    `;
  }
  const items = threads.slice(0, 30);
  return `
    <details class="thread-history-group" open>
      <summary class="group-label"><span>Recent chats</span><span>${threads.length}</span></summary>
      <div class="thread-history-list" data-pcad-scroll-key="threads:sidebar" aria-label="Recent chat history">
        ${items.map((thread) => `
          <button type="button" class="thread-row ${thread.thread_id === currentThreadId ? "active" : ""}" data-pcad-thread-chip="${escapeHtml(thread.thread_id)}">
            <span class="thread-row-title">${escapeHtml(thread.title || "Untitled chat")}</span>
          </button>
        `).join("")}
      </div>
    </details>
  `;
}

function renderArtifactGroups(artifacts, accountId) {
  if (!artifacts.length) return emptyState("No source artifacts have loaded for this client.");
  const groups = new Map();
  for (const artifact of artifacts) {
    const label = artifact.metadata?.test_note ? "Test notes" : formatArtifactType(artifact.artifact_type);
    groups.set(label, [...(groups.get(label) || []), artifact]);
  }
  return Array.from(groups.entries())
    .sort(([a], [b]) => groupRank(a) - groupRank(b))
    .map(([label, items], index) => renderArtifactGroup(label, items, accountId, index < 2))
    .join("");
}

function renderArtifactGroupsByAccount(accounts, artifactsByAccount) {
  if (!accounts.length) return emptyState("No clients available.");
  const sections = accounts
    .map((account) => {
      const items = artifactsByAccount[account.account_id] || [];
      if (!items.length) return "";
      return renderArtifactGroup(account.account_name, items, account.account_id, false);
    })
    .filter(Boolean);
  return sections.length ? sections.join("") : emptyState("No source artifacts have loaded yet.");
}

function renderArtifactGroup(label, items, accountId, open) {
  return `
    <details class="artifact-group"${open ? " open" : ""}>
      <summary class="group-label"><span>${escapeHtml(label)}</span><span>${items.length}</span></summary>
      ${items.map((artifact) => renderArtifactRow(artifact, accountId)).join("")}
    </details>
  `;
}

function groupRank(label) {
  const index = artifactOrder.indexOf(label);
  return index === -1 ? artifactOrder.length : index;
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
