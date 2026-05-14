import {
  getAccount,
  getAccountAlerts,
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
import { renderAccountList } from "./views/account_list.js";
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
    const [session, accounts] = await Promise.all([getSession(), listAccounts()]);
    state.set("session", session);
    state.set("accounts", accounts);
  } catch (error) {
    state.set("lastError", error);
    showToast(error.detail || "The demo API is not reachable. Add ?mock=1 to use the local mock UI.", "error");
  }
}

async function loadRoute(route) {
  state.set("route", route);
  if (route.name === "accounts" || route.name === "not_found") {
    state.set("currentAccountId", null);
    state.set("currentThreadId", null);
    return;
  }

  const accountId = route.params.accountId;
  state.set("currentAccountId", accountId);

  try {
    const [account, artifacts, alerts, threads] = await Promise.all([
      getAccount(accountId),
      listAccountArtifacts(accountId),
      getAccountAlerts(accountId),
      listThreads(),
    ]);
    state.update("accounts", (accounts) => mergeBy(accounts, account, "account_id"));
    state.update("artifactsByAccount", (current) => ({ ...current, [accountId]: artifacts }));
    state.update("alertsByAccount", (current) => ({ ...current, [accountId]: alerts }));
    state.set("threads", threads);

    const threadId = route.params.threadId || pickThreadId(threads, accountId);
    state.set("currentThreadId", threadId || null);
    if (threadId) {
      const messages = await listMessages(threadId);
      state.update("messagesByThread", (current) => ({ ...current, [threadId]: messages }));
    }

    if (route.name === "account_artifact" && route.params.artifactId) {
      maybeOpenArtifact(route.params.artifactId, accountId, { restoreRouteOnClose: true });
    }
  } catch (error) {
    state.set("lastError", error);
    showToast(error.detail || `Could not load ${accountId}.`, "error");
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
          <p>Run the FastAPI app when Package 4 is available, or open this page with <code>?mock=1</code> for a local smoke test.</p>
        </div>
      </section>
    `;
    return;
  }

  if (route.name === "accounts") {
    root.innerHTML = renderAccountList(accounts);
    document.title = "Private Company Memory Demo";
    return;
  }

  if (!currentAccount) {
    root.innerHTML = `
      <section class="page page-narrow">
        <div class="loading-view">
          <div class="skeleton skeleton-title"></div>
          <div class="skeleton skeleton-row"></div>
          <div class="skeleton skeleton-row short"></div>
        </div>
      </section>
    `;
    return;
  }

  root.innerHTML = renderAccountDetail(currentAccount);
  bindAccountDetail(root, currentAccount);
  restoreScrollSnapshot(root, scrollSnapshot);

  if (route.name === "account_artifact" && route.params.artifactId) {
    maybeOpenArtifact(route.params.artifactId, currentAccount.account_id, { restoreRouteOnClose: true });
  }

  document.title = `${accountName(currentAccount)} · Private Company Memory Demo`;
}

function pickThreadId(threads, accountId) {
  return threads.find((thread) => thread.account_id === accountId)?.thread_id || null;
}

function mergeBy(items, incoming, key) {
  if (!incoming) return items;
  let matched = false;
  const merged = items.map((item) => {
    if (item[key] !== incoming[key]) return item;
    matched = true;
    return { ...item, ...incoming };
  });
  return matched ? merged : [...items, incoming];
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
  root.querySelectorAll("[data-pcad-scroll-key]").forEach((element) => {
    const key = element.dataset.pcadScrollKey;
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
  root.querySelectorAll("[data-pcad-scroll-key]").forEach((element) => {
    const key = element.dataset.pcadScrollKey;
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
