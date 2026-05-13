import { accountCountry, accountName } from "../util/format.js";
import { escapeHtml } from "../util/dom.js";
import { accountPath } from "../router.js";

export function renderAccountList(accounts) {
  return `
    <section class="page page-narrow" data-pcad-view="account-list">
      <div class="page-head">
        <div>
          <p class="eyebrow">Public demo · private company memory</p>
          <h1>Never walk into a client call cold again.</h1>
          <p class="lede">Turn scattered emails, meeting notes, CRM history, and account documents into a private AI copilot without uploading your accounts to anyone's cloud.</p>
        </div>
        <span class="warning-chip">Synthetic data only</span>
      </div>
      <div class="account-grid" data-pcad-account-list>
        ${accounts.map(renderAccountCard).join("")}
      </div>
    </section>
  `;
}

function renderAccountCard(account) {
  const name = accountName(account);
  const status = account.status || account.account_type || "Synthetic account";
  const context = account.context || `${account.industry || "B2B account"} account in ${accountCountry(account)}.`;
  return `
    <a class="account-card" href="${accountPath(account.account_id)}" data-pcad-account-card="${escapeHtml(account.account_id)}">
      <div class="card-meta">
        <span class="badge">${escapeHtml(account.industry || "Industry")}</span>
        <span class="badge">${escapeHtml(accountCountry(account))}</span>
        <span class="warning-chip">${escapeHtml(status)}</span>
      </div>
      <h2>${escapeHtml(name)}</h2>
      <p class="context">${escapeHtml(context)}</p>
      <span class="primary-action">Open account</span>
    </a>
  `;
}
