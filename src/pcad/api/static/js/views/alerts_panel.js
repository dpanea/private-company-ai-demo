import { emptyState, escapeHtml } from "../util/dom.js";
import { renderMarkdown } from "../util/format.js";

export function renderAlertsPanel(alerts = [], artifacts = []) {
  if (!alerts.length) return emptyState("No proactive alerts for this account yet.");
  return alerts.map((alert) => {
    const evidence = (alert.evidence_artifact_ids || []).map((id) => {
      const artifact = artifacts.find((item) => item.artifact_id === id);
      return `<span class="evidence-chip">${escapeHtml(artifact?.title || id)}</span>`;
    }).join("");
    return `
      <article class="alert-card ${escapeHtml(alert.severity)}" id="alert-${escapeHtml(alert.alert_id)}">
        <span class="severity ${escapeHtml(alert.severity)}">${escapeHtml(alert.severity)}</span>
        <h3>${escapeHtml(alert.title)}</h3>
        <div class="markdown">${renderMarkdown(alert.body_markdown)}</div>
        <div class="evidence-list">${evidence || '<span class="evidence-chip">Derived signal</span>'}</div>
      </article>
    `;
  }).join("");
}
