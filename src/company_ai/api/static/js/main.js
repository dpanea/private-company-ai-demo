import {
  getSession,
  listAccountArtifacts,
  listAccounts,
  listMessages,
  listThreads,
} from "./api.js";
import { parseRoute } from "./router.js";
import { state } from "./state.js";
import { qs, showToast } from "./util/dom.js";
import { accountName } from "./util/format.js";
import { renderAccountDetail, bindAccountDetail } from "./views/account_detail.js";
import { openArtifactModal } from "./views/artifact_modal.js";

let pendingArtifactId = null;

document.addEventListener("DOMContentLoaded", async () => {
  window.addEventListener("hashchange", () => loadRoute(parseRoute()));
  state.subscribe("*", renderApp);
  await bootstrap();
  await loadRoute(parseRoute());
});

async function bootstrap() {
  try {
    const [session, accounts, threads] = await Promise.all([getSession(), listAccounts(), listThreads()]);
    state.set("session", session);
    state.set("accounts", accounts);
    state.set("threads", threads);
    // Eagerly load every knowledge context's artifacts so the unified panel can
    // show internal sources and client sources before the user narrows context.
    await Promise.all(accounts.map((account) => loadArtifactsForAccount(account.account_id)));
  } catch (error) {
    state.set("lastError", error);
    showToast(error.detail || "The demo API is not reachable.", "error");
  }
}

async function loadRoute(route) {
  state.set("route", route);
  try {
    const threads = await listThreads();
    state.set("threads", threads);

    if (route.name === "memory") {
      state.set("currentAccountId", null);
    }

    if (route.name === "account" || route.name === "account_thread" || route.name === "account_artifact") {
      state.set("currentAccountId", route.params.accountId);
      await loadArtifactsForAccount(route.params.accountId);
    }

    const threadId = route.params.threadId || null;
    state.set("currentThreadId", threadId || null);
    if (threadId) {
      const messages = await listMessages(threadId);
      state.update("messagesByThread", (current) => ({ ...current, [threadId]: messages }));
      const thread = threads.find((item) => item.thread_id === threadId);
      if (thread?.account_id) {
        state.set("currentAccountId", thread.account_id);
        await loadArtifactsForAccount(thread.account_id);
      }
    }

    if ((route.name === "artifact" || route.name === "account_artifact") && route.params.artifactId) {
      maybeOpenArtifact(route.params.artifactId, state.get("currentAccountId"), { restoreRouteOnClose: true });
    }
  } catch (error) {
    state.set("lastError", error);
    showToast(error.detail || "Could not load the demo workspace.", "error");
  }
}

function renderApp() {
  const root = qs("#app-root");
  const scrollSnapshot = captureScrollSnapshot(root);
  const route = state.get("route");
  const accounts = state.get("accounts");
  const currentAccount = accounts.find((account) => account.account_id === state.get("currentAccountId"));

  if (state.get("lastError") && !accounts.length) {
    root.innerHTML = `
      <section class="page page-narrow">
        <div class="inline-error">
          <strong>The frontend loaded, but the API did not respond.</strong>
          <p>Start the backend with <code>uv run company-ai serve</code>, then refresh.</p>
        </div>
      </section>
    `;
    return;
  }

  root.innerHTML = renderAccountDetail(currentAccount, accounts);
  bindAccountDetail(root, currentAccount, accounts, { loadArtifactsForAccount });
  restoreScrollSnapshot(root, scrollSnapshot);

  if ((route.name === "artifact" || route.name === "account_artifact") && route.params.artifactId) {
    maybeOpenArtifact(route.params.artifactId, currentAccount?.account_id || null, { restoreRouteOnClose: true });
  }

  document.title = currentAccount
    ? `${accountName(currentAccount)} · The Company Knowledge AI Demo`
    : "The Company Knowledge AI Demo";
}

async function loadArtifactsForAccount(accountId) {
  if (!accountId) return [];
  const existing = state.get("artifactsByAccount")[accountId];
  if (existing) return existing;
  const artifacts = await listAccountArtifacts(accountId);
  state.update("artifactsByAccount", (current) => ({ ...current, [accountId]: artifacts }));
  return artifacts;
}

function maybeOpenArtifact(artifactId, accountId, options = { restoreRouteOnClose: true }) {
  if (state.get("currentArtifactId") === artifactId || pendingArtifactId === artifactId) return;
  pendingArtifactId = artifactId;
  openArtifactModal(artifactId, accountId, options).finally(() => {
    pendingArtifactId = null;
  });
}

function captureScrollSnapshot(root) {
  const snapshot = new Map();
  root.querySelectorAll("[data-app-scroll-key]").forEach((element) => {
    const key = element.dataset.appScrollKey;
    if (!key) return;
    snapshot.set(key, {
      left: element.scrollLeft,
      top: element.scrollTop,
      nearBottom: element.scrollHeight - element.scrollTop - element.clientHeight < 48,
    });
  });
  return snapshot;
}

function restoreScrollSnapshot(root, snapshot) {
  root.querySelectorAll("[data-app-scroll-key]").forEach((element) => {
    const key = element.dataset.appScrollKey;
    if (!key) return;
    const previous = snapshot.get(key);
    if (key.startsWith("messages:") && (!previous || previous.nearBottom)) {
      element.scrollTop = element.scrollHeight;
      element.scrollLeft = previous?.left || 0;
      return;
    }
    if (previous) {
      element.scrollTop = previous.top;
      element.scrollLeft = previous.left;
    }
  });
}
