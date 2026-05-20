import { createThread } from "../api.js";
import { state } from "../state.js";
import { navigate, threadPath } from "../router.js";
import { streamMessage } from "../sse.js";
import { emptyState, escapeHtml, showToast } from "../util/dom.js";
import { renderAssistantBlocks, workflowLabel } from "../util/format.js";

export function renderConversationPanel(account, threads, currentThreadId, messages) {
  const currentThread = threads.find((thread) => thread.thread_id === currentThreadId);
  const isAnyStreaming = state.get("isStreaming");
  const isStreaming = isAnyStreaming && state.get("streamingThreadId") === currentThreadId;
  const streamingTokens = state.get("streamingTokens");
  const budgetReached = messages.some((message) => message.metadata?.response_type === "budget_exceeded");
  return `
    <section class="conversation" data-app-conversation>
      <div class="middle-top">
        ${budgetReached ? '<div class="budget-banner">The public demo has reached its daily budget. The architecture is still here to explore — try again tomorrow, or book a private walkthrough for live interaction.</div>' : ""}
        <div class="thread-context">
          <div class="thread-context-copy">
            <p class="kicker">${escapeHtml(account?.industry || "Unified company memory")}</p>
            <h2>${escapeHtml(currentThread?.title || "Ask across company data")}</h2>
            <p class="sub">${escapeHtml(account?.account_name || "All company knowledge")} · ${escapeHtml(threads.length ? `${threads.length} recent chats` : "No chats yet")}</p>
          </div>
        </div>
      </div>
      <div class="message-list" data-app-message-list data-app-scroll-key="messages:${escapeHtml(currentThreadId || account?.account_id || "new")}">
        ${messages.length ? messages.map(renderMessage).join("") : emptyState("Start with a workflow button or ask a free-text question.")}
        ${isStreaming ? renderStreamingBubble(streamingTokens) : ""}
      </div>
      <form class="composer" data-app-composer>
        <div class="composer-row">
          <textarea name="message" rows="2" placeholder="Ask about a client, policy, decision, artifact, or risk" ${isAnyStreaming ? "disabled" : ""}></textarea>
          <button class="primary-action" type="submit" ${isAnyStreaming ? "disabled" : ""}>Send</button>
        </div>
        <span class="affordance">Enter to send, Shift+Enter for newline</span>
      </form>
    </section>
  `;
}

export function bindConversationPanel(root, account, options = {}) {
  const textarea = root.querySelector("[data-app-composer] textarea");
  textarea?.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      root.querySelector("[data-app-composer]")?.requestSubmit();
    }
  });

  root.querySelector("[data-app-composer]")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const text = textarea.value.trim();
    if (!text) return;
    await sendCurrentMessage(account, text, options);
    textarea.value = "";
  });

  root.querySelectorAll("[data-app-pick-account]").forEach((button) => {
    button.addEventListener("click", async () => {
      const label = button.textContent.trim();
      if (!label) return;
      await sendCurrentMessage(account, label, options);
    });
  });
}

export async function startThread(accountId, workflowSeed, options = { streamSeed: true, account: null }) {
  try {
    const thread = await createThread({ account_id: accountId, workflow_seed: workflowSeed });
    state.set("threads", [thread, ...state.get("threads").filter((item) => item.thread_id !== thread.thread_id)]);
    state.set("currentThreadId", thread.thread_id);
    state.update("messagesByThread", (messagesByThread) => ({ ...messagesByThread, [thread.thread_id]: [] }));
    navigate(threadPath(accountId, thread.thread_id));
    if (workflowSeed && options.streamSeed) {
      await sendCurrentMessage({ account_id: accountId }, workflowLabel(workflowSeed), options);
    }
  } catch (error) {
    handleStreamError(error);
  }
}

async function sendCurrentMessage(account, text, options = {}) {
  let threadId = state.get("currentThreadId");
  if (!threadId) {
    const thread = await createThread({ account_id: account?.account_id || null, workflow_seed: null });
    state.set("threads", [thread, ...state.get("threads")]);
    state.set("currentThreadId", thread.thread_id);
    threadId = thread.thread_id;
    navigate(threadPath(account?.account_id || null, threadId));
  }

  state.set("isStreaming", true);
  state.set("streamingThreadId", threadId);
  state.set("streamingTokens", "");

  streamMessage(threadId, text, {
    onUserMessage(message) {
      appendMessage(threadId, message);
    },
    onStatus(status) {
      if (status.status === "thinking") setStreamingTokens("Searching company memory...");
      if (status.status === "generating") setStreamingTokens("");
    },
    onToken(token) {
      appendStreamingToken(token.content || "");
    },
    onReplace(payload) {
      setStreamingTokens(payload.content || "");
    },
    onDone(payload) {
      appendMessage(threadId, payload.assistant_message);
      if (payload.thread) {
        state.set("threads", [payload.thread, ...state.get("threads").filter((thread) => thread.thread_id !== payload.thread.thread_id)]);
        if (payload.thread.account_id) {
          state.set("currentAccountId", payload.thread.account_id);
          options.loadArtifactsForAccount?.(payload.thread.account_id).catch((error) => {
            showToast(error.detail || "Could not load source artifacts.", "error");
          });
        }
      }
      state.set("isStreaming", false);
      state.set("streamingThreadId", null);
      setStreamingTokens("");
    },
    onError(error) {
      handleStreamError(error);
    },
  });
}

let streamingTokenBuffer = "";
let streamingRafHandle = null;

function appendStreamingToken(chunk) {
  if (!chunk) return;
  streamingTokenBuffer += chunk;
  scheduleStreamingFlush();
}

function setStreamingTokens(value) {
  streamingTokenBuffer = "";
  if (streamingRafHandle !== null) {
    cancelAnimationFrame(streamingRafHandle);
    streamingRafHandle = null;
  }
  state.set("streamingTokens", value);
}

function scheduleStreamingFlush() {
  if (streamingRafHandle !== null) return;
  streamingRafHandle = requestAnimationFrame(() => {
    streamingRafHandle = null;
    if (!streamingTokenBuffer) return;
    const next = `${state.get("streamingTokens")}${streamingTokenBuffer}`;
    streamingTokenBuffer = "";
    const node = document.querySelector("[data-app-streaming] [data-app-streaming-body]");
    if (node) {
      // Direct DOM mutation avoids triggering a full app re-render per frame.
      // The state.data slot stays in sync so any subsequent full render uses
      // the same string we just wrote to the DOM.
      state.setSilent("streamingTokens", next);
      node.textContent = next;
    } else {
      state.set("streamingTokens", next);
    }
  });
}

function appendMessage(threadId, message) {
  state.update("messagesByThread", (current) => {
    const existing = current[threadId] || [];
    if (existing.some((item) => item.message_id === message.message_id)) return current;
    return { ...current, [threadId]: [...existing, message] };
  });
}

function handleStreamError(error) {
  state.set("isStreaming", false);
  state.set("streamingThreadId", null);
  setStreamingTokens("");
  if (error.status === 429) {
    state.set("rateLimitedUntil", Date.now() + 60000);
    showToast("Slow down — too many requests. Try again in a minute.", "warning");
    return;
  }
  showToast(error.detail || error.message || "The message could not be sent.", "error");
}

function renderMessage(message) {
  const body = message.role === "assistant"
    ? renderAssistantBlocks(message.metadata?.blocks, message.citations || [], message.content)
    : escapeHtml(message.content);
  const candidateButtons = message.role === "assistant" ? renderCandidateButtons(message.metadata?.account_candidates) : "";
  return `
    <article class="message ${escapeHtml(message.role)}" data-app-message="${escapeHtml(message.message_id)}">
      <div class="${message.role === "assistant" ? "markdown" : ""}">${body}</div>
      ${candidateButtons}
    </article>
  `;
}

function renderCandidateButtons(candidates) {
  if (!Array.isArray(candidates) || !candidates.length) return "";
  return `
    <div class="account-candidates" data-app-account-candidates>
      ${candidates.map((candidate) => `
        <button type="button" class="account-candidate" data-app-pick-account="${escapeHtml(candidate.account_id)}">
          ${escapeHtml(candidate.account_name)}
        </button>
      `).join("")}
    </div>
  `;
}

function renderStreamingBubble(text) {
  const body = text || "Searching company memory...";
  return `
    <article class="message assistant" data-app-streaming>
      <div class="markdown stream-cursor">
        <div data-app-streaming-body>${escapeHtml(body)}</div>
      </div>
    </article>
  `;
}
