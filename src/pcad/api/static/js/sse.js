import { ApiError, appendMockMessage, isMockMode, mockThread } from "./api.js";

export function streamMessage(threadId, message, handlers = {}) {
  if (isMockMode()) return streamMockMessage(threadId, message, handlers);

  const controller = new AbortController();
  fetch(`/api/threads/${encodeURIComponent(threadId)}/messages/stream`, {
    method: "POST",
    credentials: "same-origin",
    headers: {
      "Accept": "text/event-stream",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ message }),
    signal: controller.signal,
  }).then(async (response) => {
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
    await parseSse(response.body, handlers);
  }).catch((error) => {
    if (error.name === "AbortError") return;
    handlers.onError?.(error);
  });

  return controller;
}

async function parseSse(body, handlers) {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let splitIndex;
    while ((splitIndex = buffer.indexOf("\n\n")) !== -1) {
      const rawEvent = buffer.slice(0, splitIndex);
      buffer = buffer.slice(splitIndex + 2);
      dispatchSseEvent(rawEvent, handlers);
    }
  }
}

function dispatchSseEvent(rawEvent, handlers) {
  let eventName = "message";
  const dataLines = [];
  for (const line of rawEvent.split("\n")) {
    if (line.startsWith("event:")) eventName = line.slice(6).trim();
    if (line.startsWith("data:")) dataLines.push(line.slice(5).trimStart());
  }
  const rawData = dataLines.join("\n");
  const data = rawData ? JSON.parse(rawData) : {};

  if (eventName === "user_message") handlers.onUserMessage?.(data);
  if (eventName === "status") handlers.onStatus?.(data);
  if (eventName === "token") handlers.onToken?.(data);
  if (eventName === "citations") handlers.onCitations?.(data);
  if (eventName === "replace") handlers.onReplace?.(data);
  if (eventName === "done") handlers.onDone?.(data);
  if (eventName === "error") handlers.onError?.(data);
}

function streamMockMessage(threadId, message, handlers) {
  const controller = new AbortController();
  const thread = mockThread(threadId);
  const accountName = thread?.account_name || "this account";
  const createdAt = new Date().toISOString();
  const userMessage = {
    message_id: `mock-user-${Date.now()}`,
    thread_id: threadId,
    role: "user",
    content: message,
    account_id: thread?.account_id || null,
    account_name: accountName,
    citations: [],
    metadata: {},
    created_at: createdAt,
  };
  const assistantText = `Here is the source-backed readout for ${accountName}.\n\nThe account is moving, but the next step should resolve the explicit blocker before expanding scope. The strongest evidence is in the recent email thread and meeting notes. [Source: Email mock-thread]\n\nRecommended next action: send a concise follow-up that confirms the deployment boundary, names the owner for the blocker, and asks for a date to review the answer. [Source: Meeting mock-review]`;
  const assistantMessage = {
    message_id: `mock-assistant-${Date.now()}`,
    thread_id: threadId,
    role: "assistant",
    content: assistantText,
    account_id: thread?.account_id || null,
    account_name: accountName,
    citations: [
      {
        label: "Source: Email mock-thread",
        source_object: "Email",
        source_record_id: "mock-thread",
        title: "Recent email thread",
        source_date: "2026-05-04",
        excerpt: "Procurement confirmed the data boundary but asked for a written deployment note.",
        metadata: { artifact_id: thread?.account_id === "SYN_ACC_BRANNFELD" ? "art-brann-email-1" : null },
      },
      {
        label: "Source: Meeting mock-review",
        source_object: "Meeting",
        source_record_id: "mock-review",
        title: "Review meeting notes",
        source_date: "2026-04-28",
        excerpt: "The technical sponsor needs confidence before the next procurement checkpoint.",
        metadata: { artifact_id: thread?.account_id === "SYN_ACC_BRANNFELD" ? "art-brann-meeting" : null },
      },
    ],
    metadata: {},
    created_at: createdAt,
  };

  window.setTimeout(() => {
    if (controller.signal.aborted) return;
    appendMockMessage(threadId, userMessage);
    handlers.onUserMessage?.(userMessage);
    handlers.onStatus?.({ status: "thinking" });
    handlers.onCitations?.({ citations: assistantMessage.citations });
  }, 120);

  window.setTimeout(() => {
    if (controller.signal.aborted) return;
    handlers.onStatus?.({ status: "generating" });
    const tokens = assistantText.match(/.{1,34}(\s|$)/g) || [assistantText];
    tokens.forEach((token, index) => {
      window.setTimeout(() => {
        if (controller.signal.aborted) return;
        handlers.onToken?.({ content: token });
        if (index === tokens.length - 1) {
          appendMockMessage(threadId, assistantMessage);
          handlers.onDone?.({ assistant_message: assistantMessage, thread });
        }
      }, index * 38);
    });
  }, 520);

  return controller;
}
