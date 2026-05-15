import { addFakeNote, listAccountArtifacts, listFakeNotes } from "../api.js";
import { state } from "../state.js";
import { escapeHtml, qs, showToast, trapDialogFocus } from "../util/dom.js";

export function openFakeNoteModal(accountId) {
  const root = qs("#modal-root");
  root.innerHTML = renderFakeNoteDialog();
  const dialog = root.querySelector("dialog");
  const releaseTrap = trapDialogFocus(dialog);

  dialog.addEventListener("close", () => {
    releaseTrap();
    root.innerHTML = "";
  }, { once: true });
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  });
  dialog.querySelector("[data-pcad-close-modal]")?.addEventListener("click", () => dialog.close());
  dialog.querySelector("form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    await submitFakeNote(dialog, accountId);
  });

  dialog.showModal();
  dialog.querySelector("input[name='title']")?.focus();
}

async function submitFakeNote(dialog, accountId) {
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
    setFakeNoteSubmitting(dialog, true);
    await addFakeNote(accountId, payload);
    const [notes, artifacts] = await Promise.all([listFakeNotes(accountId), listAccountArtifacts(accountId)]);
    state.update("fakeNotesByAccount", (notesByAccount) => ({ ...notesByAccount, [accountId]: notes }));
    state.update("artifactsByAccount", (artifactsByAccount) => ({ ...artifactsByAccount, [accountId]: artifacts }));
    dialog.close();
    showToast("Test note added. The system has updated this demo session's company memory.", "success");
  } catch (error) {
    setFakeNoteSubmitting(dialog, false);
    showToast(error.detail || "The test note could not be added.", "error");
  }
}

function setFakeNoteSubmitting(dialog, isSubmitting) {
  const form = dialog.querySelector("form");
  form?.querySelectorAll("input, select, textarea, button").forEach((element) => {
    element.disabled = isSubmitting;
  });
  const submit = form?.querySelector("button[type='submit']");
  if (submit) {
    submit.innerHTML = isSubmitting
      ? '<span class="button-spinner" aria-hidden="true"></span><span>Adding...</span>'
      : "Add test note";
  }
  dialog.querySelector("[data-pcad-close-modal]")?.toggleAttribute("disabled", isSubmitting);
}

function renderFakeNoteDialog() {
  const today = new Date().toISOString().slice(0, 10);
  const noteTypes = [
    ["meeting_transcript", "Meeting"],
    ["docx", "Word document"],
    ["pdf", "PDF"],
    ["email", "Email"],
  ];
  return `
    <dialog aria-labelledby="fake-note-title" data-pcad-fake-note-modal>
      <div class="modal-head">
        <div>
          <p class="kicker">Session-scoped demo input</p>
          <h2 id="fake-note-title">Add a test note</h2>
        </div>
        <button class="icon-button" type="button" data-pcad-close-modal aria-label="Close note form">×</button>
      </div>
      <div class="modal-body">
        <div class="callout warning">This public demo uses synthetic data only. Do not enter real or confidential client information. Test notes are kept only for this temporary demo session.</div>
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
            <button class="secondary-action" type="button" data-pcad-close-modal>Cancel</button>
            <button class="primary-action" type="submit">Add test note</button>
          </div>
        </form>
      </div>
    </dialog>
  `;
}
