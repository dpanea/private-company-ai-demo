import { createThread, listMessages } from "../api.js";
import { state } from "../state.js";
import { navigate, threadPath } from "../router.js";
import { streamMessage } from "../sse.js";
import { emptyState, escapeHtml, showToast } from "../util/dom.js";
import { renderMarkdown, stripSourceCitations, workflowLabel } from "../util/format.js";

const workflows = ["new_chat", "call_briefing", "what_changed", "open_risks", "follow_up_draft", "next_action"];

export function renderConversationPanel(account, threads, currentThreadId, messages) {
  const currentThread = threads.find((thread) => thread.thread_id === currentThreadId);
  const isStreaming = state.get("isStreaming");
  const streamingTokens = state.get("streamingTokens");
  const budgetReached = messages.some((message) => /daily budget|daily budget for this account/i.test(message.content || ""));
  return `
    <section class="conversation" data-pcad-conversation>
      <div class="middle-top">
        ${budgetReached ? '<div class="budget-banner">The public demo has reached its daily budget. The architecture is still here to explore — try again tomorrow, or book a private walkthrough for live interaction.</div>' : ""}
        <div class="thread-context">
          <div>
            <p class="kicker">${escapeHtml(account?.industry || "Account memory")}</p>
            <h2>${escapeHtml(currentThread?.title || `Ask about ${account?.account_name || "this account"}`)}</h2>
            <p class="sub">${escapeHtml(account?.account_name || "Selected account")} · ${escapeHtml(threads.length ? `${threads.length} recent chats` : "No chats yet")}</p>
          </div>
        </div>
        <div class="workflow-row" data-pcad-workflows>
          ${workflows.map((seed) => `<button class="workflow-btn ${seed === "new_chat" ? "new-chat" : ""}" type="button" data-pcad-workflow="${seed}">${workflowLabel(seed)}</button>`).join("")}
        </div>
        ${renderThreadHistory(threads, currentThreadId)}
      </div>
      <div class="message-list" data-pcad-message-list>
        ${messages.length ? messages.map(renderMessage).join("") : emptyState("Start with a workflow button or ask a free-text question.")}
        ${isStreaming ? renderStreamingBubble(streamingTokens) : ""}
      </div>
      <form class="composer" data-pcad-composer>
        <div class="composer-row">
          <textarea name="message" rows="2" placeholder="Ask a follow-up about this account" ${isStreaming ? "disabled" : ""}></textarea>
          <button class="primary-action" type="submit" ${isStreaming ? "disabled" : ""}>Send</button>
        </div>
        <span class="affordance">Enter to send, Shift+Enter for newline</span>
      </form>
    </section>
  `;
}

export function bindConversationPanel(root, account) {
  root.querySelectorAll("[data-pcad-workflow]").forEach((button) => {
    button.addEventListener("click", async () => {
      if (button.dataset.pcadWorkflow === "new_chat") {
        await startThread(account.account_id, null, { streamSeed: false });
      } else {
        await startThread(account.account_id, button.dataset.pcadWorkflow, { streamSeed: true, account });
      }
    });
  });

  root.querySelectorAll("[data-pcad-thread-chip]").forEach((button) => {
    button.addEventListener("click", () => {
      navigate(threadPath(account.account_id, button.dataset.pcadThreadChip));
    });
  });

  const textarea = root.querySelector("[data-pcad-composer] textarea");
  textarea?.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      root.querySelector("[data-pcad-composer]")?.requestSubmit();
    }
  });

  root.querySelector("[data-pcad-composer]")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const text = textarea.value.trim();
    if (!text) return;
    await sendCurrentMessage(account, text);
    textarea.value = "";
  });
}

async function startThread(accountId, workflowSeed, options = { streamSeed: true, account: null }) {
  try {
    const thread = await createThread({ account_id: accountId, workflow_seed: workflowSeed });
    state.set("threads", [thread, ...state.get("threads").filter((item) => item.thread_id !== thread.thread_id)]);
    state.set("currentThreadId", thread.thread_id);
    state.update("messagesByThread", (messagesByThread) => ({ ...messagesByThread, [thread.thread_id]: [] }));
    state.set("streamingCitations", []);
    navigate(threadPath(accountId, thread.thread_id));
    if (workflowSeed && options.streamSeed) {
      await sendCurrentMessage({ account_id: accountId }, workflowLabel(workflowSeed));
    }
  } catch (error) {
    handleStreamError(error);
  }
}

async function sendCurrentMessage(account, text) {
  let threadId = state.get("currentThreadId");
  if (!threadId) {
    const thread = await createThread({ account_id: account.account_id, workflow_seed: null });
    state.set("threads", [thread, ...state.get("threads")]);
    state.set("currentThreadId", thread.thread_id);
    threadId = thread.thread_id;
    navigate(threadPath(account.account_id, threadId));
  }

  state.set("isStreaming", true);
  state.set("streamingThreadId", threadId);
  state.set("streamingTokens", "");
  state.set("streamingCitations", []);

  streamMessage(threadId, text, {
    onUserMessage(message) {
      appendMessage(threadId, message);
    },
    onStatus(status) {
      if (status.status === "thinking") state.set("streamingTokens", "Searching company memory...");
      if (status.status === "generating") state.set("streamingTokens", "");
    },
    onToken(token) {
      state.set("streamingTokens", `${state.get("streamingTokens")}${token.content || ""}`);
    },
    onCitations(payload) {
      state.set("streamingCitations", payload.citations || []);
    },
    onReplace(payload) {
      state.set("streamingTokens", payload.content || "");
    },
    onDone(payload) {
      appendMessage(threadId, payload.assistant_message);
      if (payload.thread) {
        state.set("threads", [payload.thread, ...state.get("threads").filter((thread) => thread.thread_id !== payload.thread.thread_id)]);
      }
      state.set("isStreaming", false);
      state.set("streamingThreadId", null);
      state.set("streamingTokens", "");
      state.set("streamingCitations", []);
    },
    onError(error) {
      handleStreamError(error);
    },
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
  state.set("streamingTokens", "");
  state.set("streamingCitations", []);
  if (error.status === 429) {
    state.set("rateLimitedUntil", Date.now() + 60000);
    showToast("Slow down — too many requests. Try again in a minute.", "warning");
    return;
  }
  showToast(error.detail || error.message || "The message could not be sent.", "error");
}

function renderThreadHistory(threads, currentThreadId) {
  if (!threads.length) {
    return '<div class="thread-history"><span class="thread-history-empty">Recent chats will appear here.</span></div>';
  }
  return `
    <div class="thread-history" aria-label="Recent chat history">
      ${threads.slice(0, 5).map((thread) => `
        <button type="button" class="thread-chip ${thread.thread_id === currentThreadId ? "active" : ""}" data-pcad-thread-chip="${escapeHtml(thread.thread_id)}">
          <span>${escapeHtml(thread.title || "Untitled chat")}</span>
        </button>
      `).join("")}
    </div>
  `;
}

function renderMessage(message) {
  const body = message.role === "assistant" ? renderMarkdown(message.content) : escapeHtml(message.content);
  return `
    <article class="message ${escapeHtml(message.role)}" data-pcad-message="${escapeHtml(message.message_id)}">
      <div class="${message.role === "assistant" ? "markdown" : ""}">${body}</div>
    </article>
  `;
}

function renderStreamingBubble(text) {
  return `
    <article class="message assistant" data-pcad-streaming>
      <div class="markdown stream-cursor">${renderMarkdown(stripSourceCitations(text || "Searching company memory..."))}</div>
    </article>
  `;
}
