import { escapeHtml } from "./dom.js";

const allowedTags = new Set(["P", "BR", "STRONG", "EM", "UL", "OL", "LI", "BLOCKQUOTE", "CODE", "PRE", "H1", "H2", "H3", "H4", "A"]);
const allowedAttrs = new Map([["A", new Set(["href", "title", "target", "rel"])]]);

export function formatDate(value) {
  if (!value) return "No date";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return new Intl.DateTimeFormat("en", { year: "numeric", month: "short", day: "2-digit" }).format(date);
}

export function formatArtifactType(type) {
  const labels = {
    email: "Email",
    pdf: "PDF",
    docx: "Word document",
    meeting_transcript: "Meeting",
    crm_record: "CRM record",
  };
  return labels[type] || String(type || "Artifact");
}

export function artifactIcon(type) {
  return {
    email: "EM",
    pdf: "PDF",
    docx: "DOC",
    meeting_transcript: "MTG",
    crm_record: "CRM",
  }[type] || "SRC";
}

export function artifactIconSvg(type) {
  const common = 'width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"';
  const icons = {
    email: `<svg ${common}><path d="M4 6h16v12H4z"/><path d="m4 7 8 6 8-6"/></svg>`,
    pdf: `<svg ${common}><path d="M7 3h7l4 4v14H7z"/><path d="M14 3v5h5"/><path d="M9 14h6"/><path d="M9 17h4"/></svg>`,
    docx: `<svg ${common}><path d="M7 3h7l4 4v14H7z"/><path d="M14 3v5h5"/><path d="M9 13h6"/><path d="M9 16h6"/><path d="M9 19h3"/></svg>`,
    meeting_transcript: `<svg ${common}><path d="M7 4v3"/><path d="M17 4v3"/><path d="M5 8h14"/><path d="M6 5h12v15H6z"/><path d="M8.5 12h7"/><path d="M8.5 15h5"/></svg>`,
    crm_record: `<svg ${common}><path d="M4 5h16v14H4z"/><path d="M8 9h8"/><path d="M8 13h8"/><path d="M8 17h5"/></svg>`,
  };
  return icons[type] || `<svg ${common}><path d="M6 4h12v16H6z"/><path d="M9 8h6"/><path d="M9 12h6"/><path d="M9 16h4"/></svg>`;
}

export function workflowLabel(seed) {
  return {
    new_chat: "New chat",
    call_briefing: "Brief me before a call",
    what_changed: "What changed?",
    open_risks: "Open risks",
    follow_up_draft: "Draft follow-up",
    next_action: "Next action",
  }[seed] || seed;
}

export function accountName(account) {
  return account?.account_name || account?.name || "Unnamed account";
}

export function accountCountry(account) {
  return account?.billing_country || account?.country || "Unknown country";
}

export function renderMarkdown(value, options = {}) {
  const { stripSources = true, sourceLinks = false, citations = [] } = options;
  let text = String(value ?? "");
  let citationPlaceholders = [];
  if (sourceLinks) {
    const linked = placeholderSourceCitations(text, citations);
    text = linked.text;
    citationPlaceholders = linked.placeholders;
  } else if (stripSources) {
    text = stripSourceCitations(text);
  }
  const rawHtml = window.marked?.parse ? window.marked.parse(text) : escapeHtml(text).replaceAll("\n", "<br>");
  return restoreCitationPlaceholders(sanitizeHtml(rawHtml), citationPlaceholders);
}

export function stripSourceCitations(value) {
  return String(value ?? "")
    .replace(/\s*\[Source:\s[^\]]+\]/g, "")
    .replace(/\s*\[Source:[^\]]*$/g, "")
    .replace(/\s*Source:\s[A-Za-z][A-Za-z0-9_ -]*\s+[^\s.,;)\]]+/g, "")
    .replace(/\s*Source:\s[^\n]*$/g, "")
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

export function sanitizeHtml(rawHtml) {
  const doc = new DOMParser().parseFromString(String(rawHtml ?? ""), "text/html");
  const walk = document.createTreeWalker(doc.body, NodeFilter.SHOW_ELEMENT);
  const nodes = [];
  while (walk.nextNode()) nodes.push(walk.currentNode);

  for (const node of nodes) {
    if (!allowedTags.has(node.tagName)) {
      node.replaceWith(...Array.from(node.childNodes));
      continue;
    }

    for (const attr of Array.from(node.attributes)) {
      const allowedForTag = allowedAttrs.get(node.tagName);
      if (!allowedForTag?.has(attr.name)) {
        node.removeAttribute(attr.name);
      }
    }

    if (node.tagName === "A") {
      const href = node.getAttribute("href") || "";
      if (!href.startsWith("http://") && !href.startsWith("https://") && !href.startsWith("#")) {
        node.removeAttribute("href");
      }
      node.setAttribute("rel", "noreferrer noopener");
      if (href.startsWith("http")) node.setAttribute("target", "_blank");
    }
  }
  return doc.body.innerHTML;
}

export function citationLabel(citation) {
  return citation?.label
    || citation?.source_label
    || citation?.citation_label
    || (citation?.source_object && citation?.source_record_id ? `Source: ${citation.source_object} ${citation.source_record_id}` : "Source");
}

export function citationSourceLabel(citation) {
  return citation?.source_label
    || citation?.raw_label
    || (citation?.source_object && citation?.source_record_id ? `${citation.source_object} ${citation.source_record_id}` : citationLabel(citation));
}

export function citationArtifactId(citation) {
  return citation?.artifact_id
    || citation?.metadata?.artifact_id
    || citation?.source_artifact_id
    || null;
}

function placeholderSourceCitations(value, citations) {
  const placeholders = [];
  const text = String(value ?? "").replace(/\[Source:\s*([^\]]+)\]/g, (match, rawLabel) => {
    const citation = findCitation(rawLabel, citations);
    const index = citation ? citations.indexOf(citation) : -1;
    const label = citation ? citationLabel(citation) : `Source: ${rawLabel.trim()}`;
    const artifactId = citation ? citationArtifactId(citation) : null;
    const token = `PCAD_CITATION_${placeholders.length}_TOKEN`;
    placeholders.push({ token, html: citationAnchor(label, index, artifactId) });
    return token;
  });
  return { text, placeholders };
}

function restoreCitationPlaceholders(html, placeholders) {
  return placeholders.reduce((current, placeholder) => current.replaceAll(placeholder.token, placeholder.html), html);
}

function findCitation(rawLabel, citations) {
  const normalized = normalizeCitationLabel(rawLabel);
  return citations.find((citation) => citationLabelCandidates(citation).some((candidate) => normalizeCitationLabel(candidate) === normalized)) || null;
}

function citationLabelCandidates(citation) {
  return [
    citationSourceLabel(citation),
    citationLabel(citation),
    citation?.citation_label,
    citation?.source_label,
    citation?.raw_label,
    citation?.source_object && citation?.source_record_id ? `${citation.source_object} ${citation.source_record_id}` : "",
    citation?.source_object && citation?.source_record_id ? `Source: ${citation.source_object} ${citation.source_record_id}` : "",
  ].filter(Boolean);
}

function normalizeCitationLabel(value) {
  return String(value || "")
    .replace(/^Source:\s*/i, "")
    .replace(/\s+/g, " ")
    .trim()
    .toLowerCase();
}

function citationAnchor(label, index, artifactId) {
  if (index < 0) {
    return `<span class="inline-citation muted">${escapeHtml(label)}</span>`;
  }
  const href = index >= 0 ? `#citation-${index}` : "#";
  const attrs = [
    'class="inline-citation"',
    `href="${escapeHtml(href)}"`,
    index >= 0 ? `data-pcad-citation-ref="${index}"` : "",
    artifactId ? `data-pcad-open-artifact="${escapeHtml(artifactId)}"` : "",
  ].filter(Boolean).join(" ");
  return `<a ${attrs}>${escapeHtml(label)}</a>`;
}

export function artifactMeta(artifact) {
  const metadata = artifact?.metadata || {};
  if (artifact?.artifact_type === "email") {
    return [metadata.from || metadata.sender, formatDate(metadata.date || artifact.created_at)].filter(Boolean).join(" · ");
  }
  if (artifact?.artifact_type === "pdf") {
    const pages = metadata.page_count || metadata.pages || artifact.page_urls?.length;
    return [pages ? `${pages} pages` : "PDF document", formatDate(artifact.created_at)].join(" · ");
  }
  if (artifact?.artifact_type === "meeting_transcript") {
    const attendees = metadata.attendees_count || metadata.attendees?.length;
    return [attendees ? `${attendees} attendees` : "Meeting transcript", formatDate(metadata.date || artifact.created_at)].join(" · ");
  }
  return [formatArtifactType(artifact?.artifact_type), formatDate(artifact?.created_at)].join(" · ");
}
