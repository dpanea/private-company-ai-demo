import { accountCountry, accountName } from "../util/format.js";
import { escapeHtml } from "../util/dom.js";
import { accountPath } from "../router.js";

export function renderAccountList(accounts) {
  const totals = summarizeAccounts(accounts);
  return `
    <section class="page page-narrow" data-pcad-view="account-list">
      <div class="page-head">
        <div>
          <h1>Accounts</h1>
          <p class="lede">Three synthetic accounts at different deal stages. Pick one to see the conversation surface, alerts, and source-backed citations against its private index.</p>
        </div>
        <div class="account-stats" aria-label="Demo totals">
          <span><strong>${totals.accounts}</strong>accounts</span>
          <span><strong>${totals.artifacts}</strong>artifacts</span>
          <span><strong>${totals.alerts}</strong>alerts</span>
        </div>
      </div>
      <div class="section-heading">
        <span>Active accounts</span>
        <span class="count">${totals.accounts}</span>
      </div>
      <div class="account-list" data-pcad-account-list>
        ${accounts.map(renderAccountCard).join("")}
      </div>
    </section>
  `;
}

function renderAccountCard(account) {
  const name = accountName(account);
  const status = account.status || account.account_type || "Synthetic account";
  const context = account.context || `${account.industry || "B2B account"} account in ${accountCountry(account)}.`;
  const artifactCount = countValue(account, "artifact_count", "artifacts_count");
  const alertCount = countValue(account, "alert_count", "alerts_count");
  const daysAgo = countValue(account, "days_since_activity", "days_since_last_activity");
  return `
    <a class="account-row" href="${accountPath(account.account_id)}" data-pcad-account-card="${escapeHtml(account.account_id)}">
      <span class="account-main">
        <span class="name-line">
          <h2>${escapeHtml(name)}</h2>
          ${renderStatusDot(status)}
        </span>
        <span class="meta-line">
          <span>${escapeHtml(account.industry || "Industry")}</span>
          <span class="dot" aria-hidden="true"></span>
          <span>${escapeHtml(accountCountry(account))}</span>
        </span>
        <span class="context">${escapeHtml(context)}</span>
      </span>
      <span class="stats-mini" aria-label="Account metrics">
        ${renderMiniStat(artifactCount, "artifacts")}
        ${renderMiniStat(alertCount, "alerts")}
        ${renderMiniStat(daysAgo, "d ago")}
      </span>
      <span class="open-arrow" aria-hidden="true">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="m13 6 6 6-6 6"/></svg>
      </span>
    </a>
  `;
}

function summarizeAccounts(accounts) {
  const sums = accounts.reduce((total, account) => ({
    artifacts: total.artifacts + numericCount(account, "artifact_count", "artifacts_count"),
    alerts: total.alerts + numericCount(account, "alert_count", "alerts_count"),
  }), { artifacts: 0, alerts: 0 });
  return {
    accounts: accounts.length,
    artifacts: sums.artifacts || "—",
    alerts: sums.alerts || "—",
  };
}

function renderStatusDot(status) {
  const label = String(status || "Synthetic account");
  return `
    <span class="status-dot ${escapeHtml(statusClass(label))}" aria-label="Status: ${escapeHtml(label)}">
      <span class="dot" aria-hidden="true"></span>
      ${escapeHtml(label)}
    </span>
  `;
}

function renderMiniStat(value, label) {
  if (value === null || value === undefined || value === "—") return "";
  return `<span><strong>${escapeHtml(value)}</strong>${escapeHtml(label)}</span>`;
}

function countValue(account, ...keys) {
  for (const key of keys) {
    if (account?.[key] !== undefined && account?.[key] !== null) return String(account[key]);
  }
  return "—";
}

function numericCount(account, ...keys) {
  const value = Number(countValue(account, ...keys));
  return Number.isFinite(value) ? value : 0;
}

function statusClass(status) {
  const normalized = status.toLowerCase();
  if (normalized.includes("stall")) return "stalled";
  if (normalized.includes("mid") || normalized.includes("compliance") || normalized.includes("review")) return "midfunnel";
  if (normalized.includes("late") || normalized.includes("positive") || normalized.includes("won")) return "late";
  return "neutral";
}
