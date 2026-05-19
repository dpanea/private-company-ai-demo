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
  };
  return labels[type] || String(type || "Artifact");
}

export function artifactIcon(type) {
  return {
    email: "EM",
    pdf: "PDF",
    docx: "DOC",
    meeting_transcript: "MTG",
  }[type] || "SRC";
}

export function artifactIconSvg(type) {
  const common = 'width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"';
  const icons = {
    email: `<svg ${common}><path d="M4 6h16v12H4z"/><path d="m4 7 8 6 8-6"/></svg>`,
    pdf: `<svg ${common}><path d="M7 3h7l4 4v14H7z"/><path d="M14 3v5h5"/><path d="M9 14h6"/><path d="M9 17h4"/></svg>`,
    docx: `<svg ${common}><path d="M7 3h7l4 4v14H7z"/><path d="M14 3v5h5"/><path d="M9 13h6"/><path d="M9 16h6"/><path d="M9 19h3"/></svg>`,
    meeting_transcript: `<svg ${common}><path d="M7 4v3"/><path d="M17 4v3"/><path d="M5 8h14"/><path d="M6 5h12v15H6z"/><path d="M8.5 12h7"/><path d="M8.5 15h5"/></svg>`,
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

export function renderMarkdown(value) {
  const text = String(value ?? "");
  const rawHtml = window.marked?.parse ? window.marked.parse(text) : escapeHtml(text).replaceAll("\n", "<br>");
  return sanitizeHtml(rawHtml);
}

// Render a structured assistant answer: each block becomes a markdown paragraph
// followed by clickable citation chips for the labels in block.citations[].
// Falls back to a plain markdown render of `fallbackText` when no blocks exist
// (legacy messages without metadata.blocks, or clarification messages).
export function renderAssistantBlocks(blocks, citations = [], fallbackText = "") {
  if (!Array.isArray(blocks) || blocks.length === 0) {
    return renderMarkdown(fallbackText);
  }
  return blocks.map((block) => renderBlock(block, citations)).join("");
}

function renderBlock(block, citations) {
  const body = renderMarkdown(String(block?.text ?? ""));
  const chips = Array.isArray(block?.citations)
    ? block.citations.map((label) => renderCitationChip(label, citations)).filter(Boolean).join("")
    : "";
  return chips ? `<div class="answer-block">${body}<div class="answer-block-citations">${chips}</div></div>` : `<div class="answer-block">${body}</div>`;
}

function renderCitationChip(label, citations) {
  if (!label) return "";
  const citation = citations.find((c) => (c?.source_label || c?.label || "") === label) || null;
  const display = citation ? citationLabel(citation) : `Source: ${label}`;
  const artifactId = citation ? citationArtifactId(citation) : null;
  if (!artifactId) {
    return `<span class="inline-citation muted">${escapeHtml(display)}</span>`;
  }
  return `<a class="inline-citation" href="#" data-pcad-open-artifact="${escapeHtml(artifactId)}">${escapeHtml(display)}</a>`;
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

export function citationArtifactId(citation) {
  return citation?.artifact_id
    || citation?.metadata?.artifact_id
    || citation?.source_artifact_id
    || null;
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
