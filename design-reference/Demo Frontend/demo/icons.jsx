/* eslint-disable */
/* PANEA MEMORY — SVG icon set
   Minimal line icons, 24x24 viewBox, currentColor stroke. */

const Icon = {
  Email: ({ size = 16, stroke = 1.6 }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={stroke} strokeLinecap="square" strokeLinejoin="miter">
      <rect x="3" y="5" width="18" height="14" />
      <path d="M3 7l9 6 9-6" />
    </svg>
  ),
  Pdf: ({ size = 16, stroke = 1.6 }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={stroke} strokeLinecap="square" strokeLinejoin="miter">
      <path d="M14 3H6v18h12V7l-4-4z" />
      <path d="M14 3v4h4" />
      <text x="12" y="17" textAnchor="middle" fontFamily="var(--font-mono)" fontSize="5.5" fontWeight="500" fill="currentColor" stroke="none">PDF</text>
    </svg>
  ),
  Doc: ({ size = 16, stroke = 1.6 }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={stroke} strokeLinecap="square" strokeLinejoin="miter">
      <path d="M14 3H6v18h12V7l-4-4z" />
      <path d="M14 3v4h4" />
      <path d="M9 12h6M9 15h6M9 18h4" />
    </svg>
  ),
  Meeting: ({ size = 16, stroke = 1.6 }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={stroke} strokeLinecap="square" strokeLinejoin="miter">
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </svg>
  ),
  X: ({ size = 16, stroke = 1.6 }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={stroke} strokeLinecap="square">
      <path d="M6 6l12 12M18 6L6 18" />
    </svg>
  ),
  Send: ({ size = 14, stroke = 1.6 }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={stroke} strokeLinecap="square" strokeLinejoin="miter">
      <path d="M3 12l18-8-7 18-3-7-8-3z" />
    </svg>
  ),
  Arrow: ({ size = 14, stroke = 1.6 }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={stroke} strokeLinecap="square" strokeLinejoin="miter">
      <path d="M4 12h16M14 6l6 6-6 6" />
    </svg>
  ),
  Warning: ({ size = 14, stroke = 1.7 }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={stroke} strokeLinejoin="miter" strokeLinecap="square">
      <path d="M12 3L2 21h20L12 3z" />
      <path d="M12 10v5" />
      <path d="M12 18v.01" strokeLinecap="round" />
    </svg>
  ),
  Critical: ({ size = 14, stroke = 1.7 }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={stroke}>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v6" strokeLinecap="square" />
      <path d="M12 16v.01" strokeLinecap="round" />
    </svg>
  ),
  Info: ({ size = 14, stroke = 1.7 }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={stroke}>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 11v6" strokeLinecap="square" />
      <path d="M12 7.5v.01" strokeLinecap="round" />
    </svg>
  ),
  Plus: ({ size = 14, stroke = 1.6 }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={stroke} strokeLinecap="square">
      <path d="M12 5v14M5 12h14" />
    </svg>
  ),
  Empty: ({ size = 32, stroke = 1.4 }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={stroke} strokeLinejoin="miter" strokeLinecap="square">
      <rect x="4" y="6" width="16" height="14" />
      <path d="M4 10h16M8 14h8M8 17h5" strokeDasharray="2 2" />
    </svg>
  ),
  Logo: ({ size = 28, stroke = 5 }) => (
    <svg width={size} height={size} viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" style={{ display: "block" }}>
      <path d="M 28 22 L 28 78 L 56 78 A 28 28 0 0 0 56 22 Z" fill="none" stroke="currentColor" strokeWidth={stroke} strokeLinejoin="miter" />
      <path d="M 40 34 L 40 86 M 40 34 L 54 34 A 11 11 0 0 1 54 56 L 40 56" fill="none" stroke="currentColor" strokeWidth={stroke} strokeLinecap="square" strokeLinejoin="miter" />
    </svg>
  ),
  Check: ({ size = 14, stroke = 1.8 }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={stroke} strokeLinecap="square" strokeLinejoin="miter">
      <path d="M4 12l5 5 11-11" />
    </svg>
  ),
};

window.Icon = Icon;

// Map artifact type → icon
window.artifactIcon = (type) => {
  switch (type) {
    case "email": return Icon.Email;
    case "pdf": return Icon.Pdf;
    case "docx": return Icon.Doc;
    case "meeting": return Icon.Meeting;
    default: return Icon.Doc;
  }
};

// Map artifact type → label
window.artifactTypeLabel = (type) => {
  switch (type) {
    case "email": return "Email";
    case "pdf": return "PDF";
    case "docx": return "DOCX";
    case "meeting": return "Meeting";
    default: return "Document";
  }
};

// Group artifacts by type
window.groupArtifacts = (artifacts) => {
  const groups = { email: [], meeting: [], pdf: [], docx: [] };
  for (const a of artifacts) {
    if (groups[a.type]) groups[a.type].push(a);
  }
  return [
    { type: "email", label: "Emails", items: groups.email },
    { type: "meeting", label: "Meetings", items: groups.meeting },
    { type: "pdf", label: "PDF documents", items: groups.pdf },
    { type: "docx", label: "Word documents", items: groups.docx },
  ].filter((g) => g.items.length > 0);
};
