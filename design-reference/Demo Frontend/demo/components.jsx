/* eslint-disable */
/* PANEA MEMORY — shared components for the demo SPA */

const { useState, useEffect, useRef, useCallback } = React;

// ——————————————————————————————————————————————————————————————
// AlertCard — severity-coloured card with evidence chips
// ——————————————————————————————————————————————————————————————
function AlertCard({ alert, account, onEvidence }) {
  const sevLabel = alert.sev === "critical" ? "Critical"
                : alert.sev === "warning" ? "Warning"
                : "Info";
  return (
    <article className={"alert-item " + alert.sev} aria-label={sevLabel + " alert: " + alert.title}>
      <div className="sev">{sevLabel}</div>
      <div className="title">{alert.title}</div>
      <div className="body">{alert.body}</div>
      {alert.evidence?.length > 0 && (
        <div className="evidence">
          {alert.evidence.map((eid) => {
            const a = account.artifacts.find((x) => x.id === eid);
            if (!a) return null;
            return (
              <button
                key={eid}
                className="ev-chip"
                onClick={() => onEvidence(a)}
                aria-label={"Open evidence: " + a.title}
              >
                <span>{window.artifactTypeLabel(a.type).toLowerCase()}</span>
                <span style={{ opacity: 0.5 }}>·</span>
                <span>{eid}</span>
              </button>
            );
          })}
        </div>
      )}
    </article>
  );
}

// ——————————————————————————————————————————————————————————————
// CitationChip
// ——————————————————————————————————————————————————————————————
function CitationChip({ citation, onOpen }) {
  return (
    <button
      className="citation-chip"
      onClick={() => onOpen(citation.artifactId)}
      aria-label={"Open source: " + citation.label}
    >
      <span className="pin" aria-hidden="true"></span>
      <span>{citation.label}</span>
    </button>
  );
}

// ——————————————————————————————————————————————————————————————
// MessageBubble — user or assistant
// ——————————————————————————————————————————————————————————————
function MessageBubble({ message, streaming, onOpenArtifact }) {
  const isUser = message.role === "user";
  return (
    <div className={"msg " + (isUser ? "user" : "assistant")}>
      <div className="role">
        {isUser
          ? <span className="avatar you" aria-hidden="true">DP</span>
          : <span className="avatar" aria-hidden="true">P</span>}
        <span>{isUser ? "You" : "Panea Memory"}</span>
      </div>
      <div className="body">
        {message.text && <p>{message.text}</p>}
        {message.blocks && message.blocks.map((b, i) => {
          if (b.kind === "p") {
            return <p key={i}>{b.text}{streaming && i === message.blocks.length - 1 && <span className="cursor"></span>}</p>;
          }
          if (b.kind === "ul") {
            return (
              <ul key={i}>
                {b.items.map((it, j) => <li key={j}>{it}</li>)}
              </ul>
            );
          }
          return null;
        })}
        {streaming && !message.blocks && <span className="cursor"></span>}
      </div>
      {!isUser && message.citations && message.citations.length > 0 && (
        <div className="citation-row">
          {message.citations.map((c, i) => (
            <CitationChip key={i} citation={c} onOpen={onOpenArtifact} />
          ))}
        </div>
      )}
    </div>
  );
}

// ——————————————————————————————————————————————————————————————
// ArtifactRow — left-panel row
// ——————————————————————————————————————————————————————————————
function ArtifactRow({ artifact, active, onOpen }) {
  const IconCmp = window.artifactIcon(artifact.type);
  return (
    <button
      type="button"
      className={"artifact-row" + (active ? " active" : "")}
      onClick={() => onOpen(artifact)}
      aria-label={"Open artifact: " + artifact.title}
    >
      <span className="icon-tile" aria-hidden="true"><IconCmp size={14} /></span>
      <div>
        <div className="title">{artifact.title}</div>
        <div className="meta">
          <span>{artifact.meta}</span>
          {artifact.ocr && <span className="ocr">OCR</span>}
        </div>
      </div>
    </button>
  );
}

// ——————————————————————————————————————————————————————————————
// Artifact modal — renders email / meeting / pdf / docx
// ——————————————————————————————————————————————————————————————
function ArtifactModal({ artifact, onClose }) {
  const closeRef = useRef(null);

  useEffect(() => {
    if (!artifact) return;
    const onKey = (e) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", onKey);
    // Focus trap: send focus to close button
    setTimeout(() => closeRef.current?.focus(), 0);
    return () => document.removeEventListener("keydown", onKey);
  }, [artifact, onClose]);

  if (!artifact) return null;

  const IconCmp = window.artifactIcon(artifact.type);
  const typeLabel = window.artifactTypeLabel(artifact.type);

  return (
    <div className="modal-backdrop" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }} role="dialog" aria-modal="true" aria-labelledby="modal-title">
      <div className="modal" role="document">
        <div className="modal-head">
          <span className="icon-tile" aria-hidden="true"><IconCmp size={16} /></span>
          <div className="titleblock">
            <h3 id="modal-title">{artifact.title}</h3>
            <div className="sub">{typeLabel} · {artifact.meta} · id {artifact.id}</div>
          </div>
          <button className="closeb" onClick={onClose} ref={closeRef} aria-label="Close artifact viewer">
            <window.Icon.X size={20} />
          </button>
        </div>
        <div className="modal-body">
          {artifact.ocr && (
            <div className="ocr-callout" role="note">
              <span className="icon" aria-hidden="true"><window.Icon.Warning /></span>
              <div>
                <div className="title">Text extracted via OCR</div>
                <div className="body">
                  This content was extracted from a scanned PDF. The original is image-only; the text below is the result of optical character recognition and may contain transcription errors. The source artifact identifier is preserved.
                </div>
              </div>
            </div>
          )}
          {artifact.type === "email" && <EmailView artifact={artifact} />}
          {artifact.type === "meeting" && <MeetingView artifact={artifact} />}
          {artifact.type === "pdf" && <PdfView artifact={artifact} />}
          {artifact.type === "docx" && <DocxView artifact={artifact} />}
        </div>
      </div>
    </div>
  );
}

function EmailView({ artifact }) {
  return (
    <>
      <div className="email-head">
        <div className="k">From</div><div className="v">{artifact.from}</div>
        <div className="k">To</div><div className="v">{artifact.to}</div>
        <div className="k">Date</div><div className="v">{artifact.date}</div>
        <div className="k">Subject</div><div className="v subj">{artifact.subject}</div>
      </div>
      <div className="email-body">
        {artifact.body.map((p, i) => <p key={i}>{p}</p>)}
      </div>
    </>
  );
}

function MeetingView({ artifact }) {
  return (
    <>
      <div className="meeting-head">
        <div className="k">Date</div><div className="v">{artifact.date}</div>
        <div className="k">Duration</div><div className="v">{artifact.duration}</div>
        <div className="k">Attendees</div>
        <div className="v">{artifact.attendees.join(" · ")}</div>
      </div>
      <div className="transcript">
        {artifact.transcript.map((t, i) => (
          <div className="transcript-turn" key={i}>
            <div className="who">
              <span className="name">{t.who}</span>
              <span className="ts">{t.ts}</span>
            </div>
            <div className="what">{t.text}</div>
          </div>
        ))}
      </div>
    </>
  );
}

function PdfView({ artifact }) {
  return (
    <div>
      {artifact.pages.map((p, i) => (
        <div className={"pdf-page" + (artifact.ocr ? " scanned" : "")} key={i}>
          <div className="pagenum">page {p.n}</div>
          <h4>{p.title}</h4>
          {p.paras.map((para, j) => <p key={j}>{para}</p>)}
        </div>
      ))}
    </div>
  );
}

function DocxView({ artifact }) {
  const md = artifact.bodyMarkdown;
  return (
    <div className="doc-view">
      <h4>{md.title}</h4>
      {md.sections.map((s, i) => (
        <div key={i}>
          <h5>{s.h}</h5>
          {s.p && <p>{s.p}</p>}
          {s.list && (
            <ul>
              {s.list.map((it, j) => <li key={j}>{it}</li>)}
            </ul>
          )}
        </div>
      ))}
    </div>
  );
}

// ——————————————————————————————————————————————————————————————
// Note form modal (synthetic data only)
// ——————————————————————————————————————————————————————————————
function NoteFormModal({ open, onClose, onSubmit }) {
  const [type, setType] = useState("note");
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10));
  const closeRef = useRef(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (e) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", onKey);
    setTimeout(() => closeRef.current?.focus(), 0);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  const submit = (e) => {
    e.preventDefault();
    if (!title.trim() || !body.trim()) return;
    onSubmit({ type, title: title.trim(), body: body.trim(), date });
    setTitle(""); setBody(""); setType("note");
  };

  return (
    <div className="modal-backdrop" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }} role="dialog" aria-modal="true" aria-labelledby="note-modal-title">
      <form className="modal note-form" onSubmit={submit}>
        <div className="modal-head">
          <span className="icon-tile" aria-hidden="true"><window.Icon.Plus size={16} /></span>
          <div className="titleblock">
            <h3 id="note-modal-title">Add a synthetic note</h3>
            <div className="sub">browser-session storage only</div>
          </div>
          <button type="button" className="closeb" onClick={onClose} ref={closeRef} aria-label="Close form">
            <window.Icon.X size={20} />
          </button>
        </div>
        <div className="warning" role="alert">
          <span className="icon" aria-hidden="true"><window.Icon.Warning /></span>
          <div>
            <div className="title">Synthetic data only</div>
            <div className="body">
              This public demo uses synthetic data only. Do not enter real or confidential client information. Notes are stored only for your browser session.
            </div>
          </div>
        </div>
        <div className="body-padded">
          <div className="field-row">
            <label htmlFor="note-type">Type</label>
            <select id="note-type" value={type} onChange={(e) => setType(e.target.value)}>
              <option value="note">Note</option>
              <option value="email">Email</option>
              <option value="meeting">Meeting note</option>
              <option value="docx">Document</option>
            </select>
          </div>
          <div className="field-row">
            <label htmlFor="note-title">Title</label>
            <input id="note-title" type="text" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Short, descriptive title" required />
          </div>
          <div className="field-row">
            <label htmlFor="note-body">Body</label>
            <textarea id="note-body" value={body} onChange={(e) => setBody(e.target.value)} placeholder="Plain-text content. No real client information." rows={6} required />
          </div>
          <div className="field-row">
            <label htmlFor="note-date">Date</label>
            <input id="note-date" type="date" value={date} onChange={(e) => setDate(e.target.value)} />
          </div>
        </div>
        <div className="actions">
          <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn btn-primary" disabled={!title.trim() || !body.trim()}>
            Add note <window.Icon.Arrow />
          </button>
        </div>
      </form>
    </div>
  );
}

// ——————————————————————————————————————————————————————————————
// Toast stack
// ——————————————————————————————————————————————————————————————
function ToastStack({ toasts, dismiss }) {
  useEffect(() => {
    if (!toasts.length) return;
    const timers = toasts.map((t) => setTimeout(() => dismiss(t.id), 4500));
    return () => timers.forEach(clearTimeout);
  }, [toasts, dismiss]);
  if (!toasts.length) return null;
  return (
    <div className="toast-stack" role="status" aria-live="polite">
      {toasts.map((t) => {
        const IconCmp = t.kind === "success" ? window.Icon.Check
                      : t.kind === "warning" ? window.Icon.Warning
                      : t.kind === "error" ? window.Icon.Critical
                      : window.Icon.Info;
        return (
          <div className={"toast " + t.kind} key={t.id}>
            <span className="icon-tile" aria-hidden="true"><IconCmp /></span>
            <div>
              <div className="t-title">{t.title}</div>
              <div className="t-body">{t.body}</div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ——————————————————————————————————————————————————————————————
// Empty state
// ——————————————————————————————————————————————————————————————
function Empty({ title, sub }) {
  return (
    <div className="empty">
      <div className="icon" aria-hidden="true"><window.Icon.Empty /></div>
      <div className="title">{title}</div>
      <div className="sub">{sub}</div>
    </div>
  );
}

// ——————————————————————————————————————————————————————————————
// Skeleton (used by demonstrations of loading state)
// ——————————————————————————————————————————————————————————————
function Skeleton({ lines = 3, withTitle = true }) {
  return (
    <div style={{ padding: "12px 18px" }}>
      {withTitle && <div className="skel title" />}
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className="skel line" style={{ width: (80 - i * 8) + "%" }} />
      ))}
    </div>
  );
}

// ——————————————————————————————————————————————————————————————
// Status pill
// ——————————————————————————————————————————————————————————————
function StatusPill({ status, label }) {
  return (
    <span className={"status-dot " + status} aria-label={"Status: " + label}>
      <span className="dot" aria-hidden="true"></span>
      {label}
    </span>
  );
}

// Export everything to window
Object.assign(window, {
  AlertCard, CitationChip, MessageBubble, ArtifactRow,
  ArtifactModal, NoteFormModal, ToastStack, Empty, Skeleton, StatusPill,
  EmailView, MeetingView, PdfView, DocxView,
});
