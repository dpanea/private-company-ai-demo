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

export function isMockMode() {
  return window.location.protocol === "file:" || new URLSearchParams(window.location.search).has("mock");
}

async function request(path, options = {}) {
  if (isMockMode()) return mockRequest(path, options);

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

export function listAccounts() {
  return request("/accounts");
}

export function getAccount(id) {
  return request(`/accounts/${encodeURIComponent(id)}`);
}

export function listAccountArtifacts(id) {
  return request(`/accounts/${encodeURIComponent(id)}/artifacts`);
}

export function getAccountAlerts(id) {
  return request(`/accounts/${encodeURIComponent(id)}/alerts`);
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

export function listFakeNotes(accountId) {
  return request(`/accounts/${encodeURIComponent(accountId)}/fake-notes`);
}

export function addFakeNote(accountId, payload) {
  return request(`/accounts/${encodeURIComponent(accountId)}/fake-notes`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function deleteFakeNote(noteId) {
  return request(`/fake-notes/${encodeURIComponent(noteId)}`, { method: "DELETE" });
}

const today = "2026-05-13T09:00:00Z";
const mockSession = { session_id: "mock-session-browser", created_at: today };

const mockAccounts = [
  {
    account_id: "SYN_ACC_BRANNFELD",
    account_name: "Brannfeld Industrial",
    industry: "Industrial automation",
    billing_country: "Germany",
    status: "Late stage positive",
    context: "Procurement is aligned, but the technical sponsor needs confidence around sovereign deployment.",
  },
  {
    account_id: "SYN_ACC_CALDRISA",
    account_name: "Caldrisa Dental Group",
    industry: "Healthcare services",
    billing_country: "Spain",
    status: "Compliance review",
    context: "Pilot scope is narrow and privacy review is the gating item before a clinical rollout.",
  },
  {
    account_id: "SYN_ACC_RYNVOSS",
    account_name: "Rynvoss Logistics",
    industry: "Logistics",
    billing_country: "Netherlands",
    status: "Stalled",
    context: "Operations sees value, while finance is waiting on a clearer integration estimate.",
  },
];

const mockArtifacts = {
  SYN_ACC_BRANNFELD: [
    artifact("art-brann-email-1", "SYN_ACC_BRANNFELD", "email_thread", "Procurement thread: deployment boundary", "plain_text", { sender: "Marta Keller", date: "2026-05-04", subject: "Deployment boundary" }),
    artifact("art-brann-proposal", "SYN_ACC_BRANNFELD", "pdf", "Q2 proposal for private memory layer", "plain_text", { page_count: 4 }),
    artifact("art-brann-nda-scan", "SYN_ACC_BRANNFELD", "pdf", "Signed NDA scan", "ocr", { page_count: 2 }),
    artifact("art-brann-meeting", "SYN_ACC_BRANNFELD", "meeting_transcript", "Technical review transcript", "plain_text", { attendees_count: 5, date: "2026-04-28" }),
    artifact("art-brann-plan", "SYN_ACC_BRANNFELD", "docx", "Account plan", "docx_xml", {}),
  ],
  SYN_ACC_CALDRISA: [
    artifact("art-cald-email", "SYN_ACC_CALDRISA", "email_thread", "Compliance questions thread", "plain_text", { sender: "Ines Rubio", date: "2026-05-07", subject: "DPA review" }),
    artifact("art-cald-dpa", "SYN_ACC_CALDRISA", "pdf", "Data processing addendum", "plain_text", { page_count: 6 }),
    artifact("art-cald-meeting", "SYN_ACC_CALDRISA", "meeting_transcript", "Pilot scope meeting", "plain_text", { attendees_count: 4, date: "2026-05-07" }),
  ],
  SYN_ACC_RYNVOSS: [
    artifact("art-ryn-email", "SYN_ACC_RYNVOSS", "email_thread", "Finance follow-up thread", "plain_text", { sender: "Niels Voss", date: "2026-04-21", subject: "Integration estimate" }),
    artifact("art-ryn-proposal", "SYN_ACC_RYNVOSS", "pdf", "Logistics proposal", "plain_text", { page_count: 5 }),
    artifact("art-ryn-meeting", "SYN_ACC_RYNVOSS", "meeting_transcript", "Procurement review transcript", "plain_text", { attendees_count: 6, date: "2026-04-17" }),
  ],
};

const mockAlerts = {
  SYN_ACC_BRANNFELD: [
    alert("al-brann-1", "SYN_ACC_BRANNFELD", "warning", "Sponsor confidence is the active risk", "The technical sponsor asked for a written explanation of the sovereign deployment path before procurement moves the deal forward.", ["art-brann-meeting"]),
    alert("al-brann-2", "SYN_ACC_BRANNFELD", "info", "Champion signal remains positive", "Procurement confirmed that the private deployment model matches their internal data boundary requirements.", ["art-brann-email-1"]),
  ],
  SYN_ACC_CALDRISA: [
    alert("al-cald-1", "SYN_ACC_CALDRISA", "critical", "Compliance review blocks expansion", "The pilot cannot expand until the DPA questions around clinical notes and retention are answered.", ["art-cald-dpa"]),
  ],
  SYN_ACC_RYNVOSS: [
    alert("al-ryn-1", "SYN_ACC_RYNVOSS", "warning", "No recent activity", "There has been no logged activity for more than two weeks after finance requested the integration estimate.", ["art-ryn-email"]),
  ],
};

let mockThreads = [];
let mockMessages = {};
let mockFakeNotes = {};

function artifact(artifact_id, account_id, artifact_type, title, extraction_method, metadata) {
  return {
    artifact_id,
    account_id,
    artifact_type,
    title,
    mime_type: artifact_type === "pdf" ? "application/pdf" : "text/plain",
    source_path: `synthetic/${artifact_id}`,
    rendered_path: null,
    page_urls: artifact_type === "pdf" ? [`/api/artifacts/${artifact_id}/page/0`, `/api/artifacts/${artifact_id}/page/1`] : [],
    extracted_text: `# ${title}\n\nThis is mock extracted text for the frontend package. It mirrors the API shape without using real or confidential data.\n\nKey points:\n- The account has source-backed memory.\n- Citations should open the referenced artifact.\n- Follow-ups stay attached to the selected account.`,
    metadata,
    extraction_method,
    created_at: today,
    ingested_at: today,
  };
}

function alert(alert_id, account_id, severity, title, body_markdown, evidence_artifact_ids) {
  return {
    alert_id,
    account_id,
    alert_type: "unresolved_objection",
    severity,
    title,
    body_markdown,
    evidence_doc_ids: [],
    evidence_artifact_ids,
    created_at: today,
  };
}

async function mockRequest(path, options) {
  await new Promise((resolve) => window.setTimeout(resolve, 90));
  const method = options.method || "GET";
  const body = options.body ? JSON.parse(options.body) : {};

  if (path === "/session") return mockSession;
  if (path === "/accounts") return mockAccounts;
  if (path === "/threads") {
    if (method === "POST") return createMockThread(body.account_id, body.workflow_seed);
    return mockThreads;
  }

  const accountArtifacts = path.match(/^\/accounts\/([^/]+)\/artifacts$/);
  if (accountArtifacts) return mockArtifacts[decodeURIComponent(accountArtifacts[1])] || [];

  const accountAlerts = path.match(/^\/accounts\/([^/]+)\/alerts$/);
  if (accountAlerts) return mockAlerts[decodeURIComponent(accountAlerts[1])] || [];

  const accountFakeNotes = path.match(/^\/accounts\/([^/]+)\/fake-notes$/);
  if (accountFakeNotes) {
    const accountId = decodeURIComponent(accountFakeNotes[1]);
    if (method === "POST") return addMockNote(accountId, body);
    return mockFakeNotes[accountId] || [];
  }

  const account = path.match(/^\/accounts\/([^/]+)$/);
  if (account) return mockAccounts.find((item) => item.account_id === decodeURIComponent(account[1]));

  const artifactMatch = path.match(/^\/artifacts\/([^/]+)$/);
  if (artifactMatch) return Object.values(mockArtifacts).flat().find((item) => item.artifact_id === decodeURIComponent(artifactMatch[1]));

  const threadMessages = path.match(/^\/threads\/([^/]+)\/messages$/);
  if (threadMessages) return mockMessages[decodeURIComponent(threadMessages[1])] || [];

  const threadMatch = path.match(/^\/threads\/([^/]+)$/);
  if (threadMatch) return mockThreads.find((item) => item.thread_id === decodeURIComponent(threadMatch[1]));

  const deleteNote = path.match(/^\/fake-notes\/([^/]+)$/);
  if (deleteNote && method === "DELETE") {
    for (const accountId of Object.keys(mockFakeNotes)) {
      mockFakeNotes[accountId] = mockFakeNotes[accountId].filter((note) => note.note_id !== decodeURIComponent(deleteNote[1]));
    }
    return null;
  }

  throw new ApiError(`Mock route not found: ${path}`, { status: 404, code: "not_found" });
}

function createMockThread(accountId, workflowSeed) {
  const account = mockAccounts.find((item) => item.account_id === accountId);
  const thread = {
    thread_id: `mock-thread-${Date.now()}`,
    session_id: mockSession.session_id,
    account_id: accountId,
    account_name: account?.account_name,
    title: workflowSeed ? workflowSeed.replaceAll("_", " ") : "Account question",
    workflow_seed: workflowSeed,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
  mockThreads = [thread, ...mockThreads];
  mockMessages[thread.thread_id] = [];
  return thread;
}

function addMockNote(accountId, payload) {
  const note = {
    note_id: `mock-note-${Date.now()}`,
    session_id: mockSession.session_id,
    account_id: accountId,
    note_type: payload.note_type,
    title: payload.title,
    body: payload.body,
    note_date: payload.note_date,
    created_at: new Date().toISOString(),
  };
  mockFakeNotes[accountId] = [note, ...(mockFakeNotes[accountId] || [])];
  const newAlert = alert(`mock-alert-${Date.now()}`, accountId, "info", `New synthetic note: ${payload.title}`, "The session-scoped note is now part of this browser session's company memory.", []);
  mockAlerts[accountId] = [newAlert, ...(mockAlerts[accountId] || [])];
  return { note, alerts: mockAlerts[accountId] };
}

export function appendMockMessage(threadId, message) {
  mockMessages[threadId] = [...(mockMessages[threadId] || []), message];
}

export function mockThread(threadId) {
  return mockThreads.find((thread) => thread.thread_id === threadId);
}
