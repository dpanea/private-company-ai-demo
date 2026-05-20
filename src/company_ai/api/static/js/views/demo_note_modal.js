import { addDemoNote, listAccountArtifacts, listDemoNotes } from "../api.js";
import { state } from "../state.js";
import { escapeHtml, qs, showToast, trapDialogFocus } from "../util/dom.js";

export function openDemoNoteModal(accountId) {
  const root = qs("#modal-root");
  root.innerHTML = renderDemoNoteDialog();
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
    await submitDemoNote(dialog, accountId);
  });

  dialog.showModal();
  dialog.querySelector("input[name='title']")?.focus();
}

async function submitDemoNote(dialog, accountId) {
  const form = dialog.querySelector("form");
  const data = new FormData(form);
  const payload = {
    note_type: data.get("note_type"),
    title: String(data.get("title") || "").trim(),
    body: String(data.get("body") || "").trim(),
    note_date: data.get("note_date"),
  };
  if (!payload.title || !payload.body || !payload.note_date) {
    showToast("Fill in the title, body, and date before adding the note.", "warning");
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

function renderDemoNoteDialog() {
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
