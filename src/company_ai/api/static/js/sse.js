import { ApiError } from "./api.js";

export function streamMessage(threadId, message, handlers = {}) {
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
  if (eventName === "replace") handlers.onReplace?.(data);
  if (eventName === "done") handlers.onDone?.(data);
  if (eventName === "error") handlers.onError?.(data);
}
