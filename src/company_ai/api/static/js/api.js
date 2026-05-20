const API_ROOT = "/api";

export class ApiError extends Error {
  constructor(message, { status = 0, code = "api_error", detail = null } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.detail = detail || message;
  }
}

async function request(path, options = {}) {
  const response = await fetch(`${API_ROOT}${path}`, {
    ...options,
    credentials: "same-origin",
    headers: {
      "Accept": "application/json",
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...(options.headers || {}),
    },
  });

  if (!response.ok) {
    let body = {};
    try {
      body = await response.json();
    } catch {
      body = { detail: response.statusText };
    }
    throw new ApiError(body.detail || response.statusText, {
      status: response.status,
      code: body.code || `http_${response.status}`,
      detail: body.detail || response.statusText,
    });
  }

  if (response.status === 204) return null;
  return response.json();
}

export function getSession() {
  return request("/session");
}

export function resetSession() {
  return request("/session", { method: "DELETE" });
}

export function listAccounts() {
  return request("/accounts");
}

export function getAccount(id) {
  return request(`/accounts/${encodeURIComponent(id)}`);
}

export function listAccountArtifacts(id) {
  return request(`/accounts/${encodeURIComponent(id)}/artifacts`);
}

export function getArtifact(id) {
  return request(`/artifacts/${encodeURIComponent(id)}`);
}

export function listThreads() {
  return request("/threads");
}

export function createThread({ account_id, workflow_seed }) {
  return request("/threads", {
    method: "POST",
    body: JSON.stringify({ account_id, workflow_seed }),
  });
}

export function getThread(id) {
  return request(`/threads/${encodeURIComponent(id)}`);
}

export function listMessages(threadId) {
  return request(`/threads/${encodeURIComponent(threadId)}/messages`);
}

export function listDemoNotes(accountId) {
  return request(`/accounts/${encodeURIComponent(accountId)}/demo-notes`);
}

export function addDemoNote(accountId, payload) {
  return request(`/accounts/${encodeURIComponent(accountId)}/demo-notes`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function deleteDemoNote(noteId) {
  return request(`/demo-notes/${encodeURIComponent(noteId)}`, { method: "DELETE" });
}
