import { resetSession } from "../api.js";
import { state } from "../state.js";
import { accountPath, artifactPath, threadPath, navigate } from "../router.js";
import { accountName, artifactIconSvg, artifactMeta, formatArtifactType, workflowLabel } from "../util/format.js";
import { emptyState, escapeHtml, showToast } from "../util/dom.js";
import { bindConversationPanel, renderConversationPanel, startThread } from "./conversation_panel.js";
import { openDemoNoteModal } from "./demo_note_modal.js";
import { openArtifactModal } from "./artifact_modal.js";

const INTERNAL_ACCOUNT_ID = "SYN_ACC_INTERNAL";
const generalPromptWorkflows = {
  catch_me_up: "Catch me up on ",
  decision_archaeology: "What did we decide about ",
};
const workflows = [
  { seed: "new_chat", scope: "utility" },
  { seed: "catch_me_up", scope: "general" },
  { seed: "decision_archaeology", scope: "general" },
  { seed: "call_briefing", scope: "client" },
  { seed: "open_risks", scope: "client" },
  { seed: "follow_up_draft", scope: "client" },
];
const artifactOrder = ["Email", "PDF", "Word document", "Meeting", "Demo notes"];

export function renderAccountDetail(account, accounts = []) {
  const accountId = account?.account_id || null;
  const internalAccount = accounts.find(isInternalAccount) || null;
  const clientAccounts = accounts.filter((item) => !isInternalAccount(item));
  const artifactsByAccount = state.get("artifactsByAccount") || {};
  const artifacts = accountId
    ? (artifactsByAccount[accountId] || [])
    : accounts.flatMap((item) => artifactsByAccount[item.account_id] || []);
  const threads = state.get("threads") || [];
  const currentThreadId = state.get("currentThreadId");
  const messages = currentThreadId ? (state.get("messagesByThread")[currentThreadId] || []) : [];

  return `
    <section class="page detail-view-page" data-app-view="company-memory">
      <div class="detail-shell memory-shell">
        <aside class="detail-panel control-panel" aria-label="Chat controls">
          <div class="panel-body control-panel-body">
            <label class="account-picker">
              <span class="kicker">Knowledge context</span>
              <select data-app-account-select>
                <option value="">All company knowledge</option>
                ${internalAccount ? `<option value="${escapeHtml(internalAccount.account_id)}" ${internalAccount.account_id === accountId ? "selected" : ""}>Internal company knowledge</option>` : ""}
                ${clientAccounts.length ? `<option value="" disabled> --- Clients --- </option>${clientAccounts.map((item) => `<option value="${escapeHtml(item.account_id)}" ${item.account_id === accountId ? "selected" : ""}>${escapeHtml(accountName(item))}</option>`).join("")}` : ""}
              </select>
            </label>
            <div class="workflow-stack" data-app-workflows>
              ${workflows.map((workflow) => `<button class="workflow-btn ${workflow.seed === "new_chat" ? "new-chat" : ""}" type="button" data-app-workflow="${workflow.seed}" data-app-workflow-scope="${workflow.scope}">${workflowLabel(workflow.seed)}</button>`).join("")}
            </div>
            ${renderThreadHistory(threads, currentThreadId)}
            <div class="thread-actions sidebar-actions">
              <button class="secondary-action memory-note-action" type="button" data-app-open-demo-note title="${accountId && accountId !== INTERNAL_ACCOUNT_ID ? "Add a demo note for this client" : "Pick a client first to add a demo note"}">Add demo note</button>
              <button class="secondary-action session-reset-action" type="button" data-app-reset-demo-session>Reset demo</button>
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
          <div class="panel-body" data-app-scroll-key="artifacts:${escapeHtml(accountId || "all")}">
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

  root.querySelector("[data-app-account-select]")?.addEventListener("change", async (event) => {
    const accountId = event.target.value || null;
    state.set("currentAccountId", accountId);
    if (accountId) {
      try {
        await loadArtifactsForAccount(accountId);
      } catch (error) {
        showToast(error.detail || "Could not load source artifacts.", "error");
      }
    }
    navigate(accountPath(accountId));
  });

  root.querySelectorAll("[data-app-workflow]").forEach((button) => {
    button.addEventListener("click", async () => {
      const workflow = button.dataset.appWorkflow;
      const scope = button.dataset.appWorkflowScope;
      if (workflow === "new_chat") {
        await startThread(selectedAccountId, null, { streamSeed: false });
        return;
      }
      if (scope === "general") {
        prefillComposer(root, generalPromptWorkflows[workflow] || workflowLabel(workflow));
        return;
      }
      if (scope === "client" && (!selectedAccountId || selectedAccountId === INTERNAL_ACCOUNT_ID)) {
        const select = root.querySelector("[data-app-account-select]");
        select?.focus();
        showToast("Pick a client context for this workflow.", "warning");
        return;
      }
      await startThread(selectedAccountId, workflow, { streamSeed: true, account });
    });
  });

  root.querySelectorAll("[data-app-thread-chip]").forEach((button) => {
    button.addEventListener("click", () => {
      const thread = (state.get("threads") || []).find((item) => item.thread_id === button.dataset.appThreadChip);
      navigate(threadPath(thread?.account_id || null, button.dataset.appThreadChip));
    });
  });

  root.querySelector("[data-app-open-demo-note]")?.addEventListener("click", () => {
    openDemoNoteModal(selectedAccountId, accounts);
  });

  root.querySelector("[data-app-reset-demo-session]")?.addEventListener("click", async () => {
    try {
      await resetSession();
      window.location.assign("/demo");
    } catch (error) {
      showToast(error.detail || "The demo session could not be reset.", "error");
    }
  });

  root.querySelectorAll("[data-app-artifact]").forEach((link) => {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      openArtifactModal(link.dataset.appArtifact, selectedAccountId, { restoreRouteOnClose: false });
    });
  });
  root.querySelectorAll("[data-app-open-artifact]").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.preventDefault();
      openArtifactModal(button.dataset.appOpenArtifact, selectedAccountId, { restoreRouteOnClose: false });
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
      <div class="thread-history-list" data-app-scroll-key="threads:sidebar" aria-label="Recent chat history">
        ${items.map((thread) => `
          <button type="button" class="thread-row ${thread.thread_id === currentThreadId ? "active" : ""}" data-app-thread-chip="${escapeHtml(thread.thread_id)}">
            <span class="thread-row-title">${escapeHtml(thread.title || "Untitled chat")}</span>
          </button>
        `).join("")}
      </div>
    </details>
  `;
}

function renderArtifactGroups(artifacts, accountId) {
  if (!artifacts.length) return emptyState("No source artifacts have loaded for this context.");
  const groups = new Map();
  for (const artifact of artifacts) {
    const label = artifact.metadata?.demo_note ? "Demo notes" : formatArtifactType(artifact.artifact_type);
    let bucket = groups.get(label);
    if (!bucket) {
      bucket = [];
      groups.set(label, bucket);
    }
    bucket.push(artifact);
  }
  return Array.from(groups.entries())
    .sort(([a], [b]) => groupRank(a) - groupRank(b))
    .map(([label, items], index) => renderArtifactGroup(label, items, accountId, index < 2))
    .join("");
}

function renderArtifactGroupsByAccount(accounts, artifactsByAccount) {
  if (!accounts.length) return emptyState("No knowledge contexts available.");
  const demoNotes = accounts.flatMap((account) => (
    (artifactsByAccount[account.account_id] || [])
      .filter((artifact) => artifact.metadata?.test_note)
  ));
  const orderedAccounts = [
    ...accounts.filter(isInternalAccount),
    ...accounts.filter((account) => !isInternalAccount(account)),
  ];
  const sections = orderedAccounts
    .map((account) => {
      const items = (artifactsByAccount[account.account_id] || [])
        .filter((artifact) => !artifact.metadata?.test_note);
      if (!items.length) return "";
      const label = isInternalAccount(account) ? "Internal company knowledge" : account.account_name;
      return renderArtifactGroup(label, items, account.account_id, isInternalAccount(account));
    })
    .filter(Boolean);
  const demoSection = demoNotes.length
    ? renderArtifactGroup("Demo notes", demoNotes, null, true)
    : "";
  const rendered = [demoSection, ...sections].filter(Boolean);
  return rendered.length ? rendered.join("") : emptyState("No source artifacts have loaded yet.");
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
  const artifactAccountId = accountId || artifact.account_id || null;
  const href = artifactPath(artifactAccountId, artifact.artifact_id);
  return `
    <a class="artifact-row" href="${href}" data-app-artifact="${escapeHtml(artifact.artifact_id)}">
      <span class="icon-tile">${artifactIconSvg(artifact.artifact_type)}</span>
      <span>
        <span class="title">${escapeHtml(artifact.title)}</span>
        <span class="meta">${escapeHtml(artifactMeta(artifact))}${artifact.extraction_method === "ocr" ? '<span class="ocr">Scanned · OCR</span>' : ""}</span>
      </span>
    </a>
  `;
}

function prefillComposer(root, text) {
  const textarea = root.querySelector("[data-app-composer] textarea");
  if (!textarea) return;
  textarea.value = text;
  textarea.focus();
  textarea.setSelectionRange(text.length, text.length);
}

function isInternalAccount(account) {
  return account?.account_id === INTERNAL_ACCOUNT_ID || account?.account_type === "internal_knowledge";
}
