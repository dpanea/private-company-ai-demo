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
    email_thread: "Email thread",
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
    email_thread: "TH",
    pdf: "PDF",
    docx: "DOC",
    meeting_transcript: "MTG",
    crm_record: "CRM",
  }[type] || "SRC";
}

export function workflowLabel(seed) {
  return {
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
  if (artifact?.artifact_type === "email" || artifact?.artifact_type === "email_thread") {
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
