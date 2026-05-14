import { emptyState, escapeHtml } from "../util/dom.js";
import { citationArtifactId, citationLabel, formatDate } from "../util/format.js";

export function renderCitationsPanel(message, accountId) {
  const citations = message?.citations || [];
  if (!citations.length) return emptyState("Citations from the next assistant answer will appear here.");
  return citations.map((citation, index) => {
    const artifactId = citationArtifactId(citation);
    return `
      <button class="citation-card" type="button" data-pcad-citation="${index}" ${artifactId ? `data-pcad-open-artifact="${escapeHtml(artifactId)}"` : "disabled"}>
        <span class="citation-chip"><span class="pin" aria-hidden="true"></span>${escapeHtml(citationLabel(citation))}</span>
        <h3>${escapeHtml(citation.title || citation.source_title || "Source artifact")}</h3>
        <p class="meta">${escapeHtml(formatDate(citation.source_date || citation.date))}</p>
        <p class="excerpt">${escapeHtml(citation.excerpt || "Open the source artifact for the supporting context.")}</p>
      </button>
    `;
  }).join("");
}

export function latestAssistantMessage(messages = []) {
  return [...messages].reverse().find((message) => message.role === "assistant") || null;
}
