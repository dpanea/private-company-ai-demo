import { addDemoNote, listAccountArtifacts, listDemoNotes } from "../api.js";
import { state } from "../state.js";
import { escapeHtml, qs, showToast, trapDialogFocus } from "../util/dom.js";
import { accountName } from "../util/format.js";

const INTERNAL_ACCOUNT_ID = "SYN_ACC_INTERNAL";

export function openDemoNoteModal(selectedAccountId, accounts = []) {
  const root = qs("#modal-root");
  const targetAccounts = accounts.length ? accounts : state.get("accounts");
  const defaultAccountId = defaultDemoNoteAccountId(selectedAccountId, targetAccounts);
  root.innerHTML = renderDemoNoteDialog(targetAccounts, defaultAccountId);
  const dialog = root.querySelector("dialog");
  const releaseTrap = trapDialogFocus(dialog);

  dialog.addEventListener("close", () => {
    releaseTrap();
    root.innerHTML = "";
  }, { once: true });
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  });
  dialog.querySelector("[data-app-close-modal]")?.addEventListener("click", () => dialog.close());
  dialog.querySelector("form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    await submitDemoNote(dialog);
  });

  dialog.showModal();
  dialog.querySelector("input[name='title']")?.focus();
}

async function submitDemoNote(dialog) {
  const form = dialog.querySelector("form");
  const data = new FormData(form);
  const accountId = String(data.get("account_id") || "").trim();
  const payload = {
    note_type: data.get("note_type"),
    title: String(data.get("title") || "").trim(),
    body: String(data.get("body") || "").trim(),
    note_date: data.get("note_date"),
  };
  if (!accountId) {
    showToast("Choose a knowledge context for this demo note.", "warning");
    return;
  }
  if (!payload.title || !payload.body || !payload.note_date) {
    showToast("Fill in the title, body, and date before adding the demo note.", "warning");
    return;
  }

  try {
    setDemoNoteSubmitting(dialog, true);
    await addDemoNote(accountId, payload);
    const [notes, artifacts] = await Promise.all([listDemoNotes(accountId), listAccountArtifacts(accountId)]);
    state.update("demoNotesByAccount", (notesByAccount) => ({ ...notesByAccount, [accountId]: notes }));
    state.update("artifactsByAccount", (artifactsByAccount) => ({ ...artifactsByAccount, [accountId]: artifacts }));
    dialog.close();
    showToast("Demo note added. The system has updated this demo session's company memory.", "success");
  } catch (error) {
    setDemoNoteSubmitting(dialog, false);
    showToast(error.detail || "The demo note could not be added.", "error");
  }
}

function setDemoNoteSubmitting(dialog, isSubmitting) {
  const form = dialog.querySelector("form");
  form?.querySelectorAll("input, select, textarea, button").forEach((element) => {
    element.disabled = isSubmitting;
  });
  const submit = form?.querySelector("button[type='submit']");
  if (submit) {
    submit.innerHTML = isSubmitting
      ? '<span class="button-spinner" aria-hidden="true"></span><span>Adding...</span>'
      : "Add demo note";
  }
  dialog.querySelector("[data-app-close-modal]")?.toggleAttribute("disabled", isSubmitting);
}

function renderDemoNoteDialog(accounts, defaultAccountId) {
  const today = new Date().toISOString().slice(0, 10);
  const noteTypes = [
    ["meeting_transcript", "Meeting"],
    ["docx", "Word document"],
    ["pdf", "PDF"],
    ["email", "Email"],
  ];
  return `
    <dialog aria-labelledby="demo-note-title" data-app-demo-note-modal>
      <div class="modal-head">
        <div>
          <p class="kicker">Session-scoped demo input</p>
          <h2 id="demo-note-title">Add a demo note</h2>
        </div>
        <button class="icon-button" type="button" data-app-close-modal aria-label="Close note form">×</button>
      </div>
      <div class="modal-body">
        <div class="callout warning">This public demo uses synthetic data only. Do not enter real or confidential client information. Demo notes are kept only for this temporary demo session.</div>
        <form class="field-grid">
          <div class="form-field">
            <label for="demo-note-context">Knowledge context</label>
            <select id="demo-note-context" name="account_id" required>
              ${renderKnowledgeContextOptions(accounts, defaultAccountId)}
            </select>
          </div>
          <div class="form-field">
            <label for="note-type">Type</label>
            <select id="note-type" name="note_type">
              ${noteTypes.map(([value, label]) => `<option value="${value}">${escapeHtml(label)}</option>`).join("")}
            </select>
          </div>
          <div class="form-field">
            <label for="note-title">Title</label>
            <input id="note-title" name="title" type="text" maxlength="140" required>
          </div>
          <div class="form-field">
            <label for="note-body">Body</label>
            <textarea id="note-body" name="body" required></textarea>
          </div>
          <div class="form-field">
            <label for="note-date">Note date</label>
            <input id="note-date" name="note_date" type="date" value="${today}" required>
          </div>
          <div class="modal-actions">
            <button class="secondary-action" type="button" data-app-close-modal>Cancel</button>
            <button class="primary-action" type="submit">Add demo note</button>
          </div>
        </form>
      </div>
    </dialog>
  `;
}

function renderKnowledgeContextOptions(accounts, selectedAccountId) {
  const internalAccount = accounts.find(isInternalAccount) || null;
  const clientAccounts = accounts.filter((account) => !isInternalAccount(account));
  const options = [];
  if (internalAccount) {
    options.push(
      `<option value="${escapeHtml(internalAccount.account_id)}" ${internalAccount.account_id === selectedAccountId ? "selected" : ""}>Internal company knowledge</option>`,
    );
  }
  if (clientAccounts.length) {
    options.push('<option value="" disabled> --- Clients --- </option>');
    options.push(...clientAccounts.map((account) => (
      `<option value="${escapeHtml(account.account_id)}" ${account.account_id === selectedAccountId ? "selected" : ""}>${escapeHtml(accountName(account))}</option>`
    )));
  }
  return options.length ? options.join("") : '<option value="">No knowledge contexts available</option>';
}

function defaultDemoNoteAccountId(selectedAccountId, accounts) {
  if (selectedAccountId && accounts.some((account) => account.account_id === selectedAccountId)) {
    return selectedAccountId;
  }
  const internalAccount = accounts.find(isInternalAccount);
  return internalAccount?.account_id || accounts[0]?.account_id || "";
}

function isInternalAccount(account) {
  return account?.account_id === INTERNAL_ACCOUNT_ID || account?.account_type === "internal_knowledge";
}
