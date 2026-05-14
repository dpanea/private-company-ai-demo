/* eslint-disable */
/* PANEA MEMORY — Demo SPA root */

const { useState, useEffect, useRef, useMemo, useCallback } = React;

// ——————————————————————————————————————————————————————————————
// Tweak defaults
// ——————————————————————————————————————————————————————————————
const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "density": "comfortable",
  "showBudgetBanner": false,
  "leftPanelWidth": 320,
  "rightPanelWidth": 340
}/*EDITMODE-END*/;

// ——————————————————————————————————————————————————————————————
// AccountListView
// ——————————————————————————————————————————————————————————————
function AccountListView({ accounts, onOpen }) {
  return (
    <main className="list-view" data-screen-label="01 Account list">
      <div className="list-view-inner">
        <div className="head">
          <div>
            <h1>Accounts</h1>
            <p className="lede">Three synthetic accounts at different deal stages. Pick one to see the conversation surface, alerts, and source-backed citations against its private index.</p>
          </div>
          <div className="right">
            <div className="stat"><span className="n">3</span>accounts</div>
            <div className="stat"><span className="n">30</span>artifacts</div>
            <div className="stat"><span className="n">7</span>alerts</div>
          </div>
        </div>

        <div className="section-heading">
          <span>Active accounts</span>
          <span className="count">3</span>
        </div>

        <div className="account-list">
          {accounts.map((a) => (
            <button
              key={a.id}
              type="button"
              className="account-row"
              onClick={() => onOpen(a.id)}
              aria-label={"Open account: " + a.name}
            >
              <div className="lhs">
                <div className="name-line">
                  <h3>{a.name}</h3>
                  <window.StatusPill status={a.status} label={a.statusLabel} />
                </div>
                <div className="meta-line">
                  <span>{a.industry}</span>
                  <span className="dot" aria-hidden="true"></span>
                  <span>{a.country}</span>
                </div>
                <p className="context">{a.context}</p>
              </div>
              <div className="stats-mini">
                <span><span className="n">{a.stats.artifacts}</span>artifacts</span>
                <span><span className="n">{a.stats.alerts}</span>alerts</span>
                <span><span className="n">{a.stats.days}</span>d ago</span>
              </div>
              <span className="open-arrow" aria-hidden="true">
                <window.Icon.Arrow size={16} />
              </span>
            </button>
          ))}
        </div>
      </div>
    </main>
  );
}

// ——————————————————————————————————————————————————————————————
// AccountDetailView — three-panel layout
// ——————————————————————————————————————————————————————————————
function AccountDetailView({ account, onBack, openArtifact, addToast }) {
  const [thread, setThread] = useState(() => account.threads[0]);
  const [messages, setMessages] = useState(() => thread.messages);
  const [composer, setComposer] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [showNoteForm, setShowNoteForm] = useState(false);
  const scrollRef = useRef(null);
  const composerRef = useRef(null);

  // When thread changes, reset messages
  useEffect(() => {
    setMessages(thread.messages);
  }, [thread.id]);

  // Auto-scroll thread on new messages
  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, streaming]);

  // Latest assistant citations for the right panel
  const latestCitations = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      const m = messages[i];
      if (m.role === "assistant" && m.citations) return m.citations;
    }
    return [];
  }, [messages]);

  const findArtifact = (id) => account.artifacts.find((a) => a.id === id);

  const handleEvidence = (artifact) => openArtifact(artifact);

  const sendMessage = (text) => {
    if (!text.trim()) return;
    const userMsg = { role: "user", text: text.trim() };
    setMessages((prev) => [...prev, userMsg]);
    setComposer("");
    setStreaming(true);

    // Generate a synthetic assistant response after a moment
    setTimeout(() => {
      // Pick a reasonable canned response based on the current account
      const cannedReply = makeCannedResponse(account, text);
      setMessages((prev) => [...prev, cannedReply]);
      setStreaming(false);
    }, 1100);
  };

  const runWorkflow = (wf) => {
    sendMessage(wf.prompt);
  };

  const onKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(composer);
    }
  };

  const submitNote = ({ type, title, body, date }) => {
    setShowNoteForm(false);
    addToast({ kind: "success", title: "Note added", body: `"${title}" added to ${account.name} for this session.` });
  };

  return (
    <main className="detail-view" data-screen-label="02 Account detail">
      {/* LEFT PANEL — artifacts */}
      <aside className="panel left" aria-label="Source artifacts">
        <div className="panel-section-label">
          <span>Source artifacts</span>
          <span className="count">{account.artifacts.length}</span>
        </div>
        <div className="panel-body">
          {window.groupArtifacts(account.artifacts).map((g) => (
            <div key={g.type}>
              <div className="artifact-group">
                <span>{g.label}</span>
                <span className="count-sm">{g.items.length}</span>
              </div>
              {g.items.map((a) => (
                <window.ArtifactRow key={a.id} artifact={a} onOpen={openArtifact} />
              ))}
            </div>
          ))}
        </div>
      </aside>

      {/* MIDDLE PANEL — conversation */}
      <section className="panel middle" aria-label="Conversation">
        <div className="middle-stack">
          <div className="thread-header">
            <div className="eyebrow"><span className="pulse" aria-hidden="true"></span>{thread.workflow}</div>
            <h2>{thread.title}</h2>
            <div className="sub">{thread.sub}</div>
          </div>

          <div className="thread-scroll" ref={scrollRef}>
            {messages.map((m, i) => (
              <window.MessageBubble
                key={i}
                message={m}
                streaming={false}
                onOpenArtifact={(aid) => { const a = findArtifact(aid); if (a) openArtifact(a); }}
              />
            ))}
            {streaming && (
              <window.MessageBubble
                message={{ role: "assistant", blocks: [{ kind: "p", text: "Retrieving and reading source artifacts" }] }}
                streaming={true}
                onOpenArtifact={() => {}}
              />
            )}
          </div>

          <div className="starter-chips" role="toolbar" aria-label="Workflows">
            {window.WORKFLOWS.map((wf) => (
              <button
                key={wf.id}
                type="button"
                className="chip"
                onClick={() => runWorkflow(wf)}
                disabled={streaming}
              >
                {wf.label}
              </button>
            ))}
          </div>

          <div className="composer-wrap">
            <div className="composer">
              <textarea
                ref={composerRef}
                placeholder={"Ask about " + account.name + "…"}
                value={composer}
                onChange={(e) => setComposer(e.target.value)}
                onKeyDown={onKeyDown}
                rows={1}
                aria-label="Message composer"
              />
              <button
                type="button"
                className="send"
                onClick={() => sendMessage(composer)}
                disabled={!composer.trim() || streaming}
                aria-label="Send message"
              >
                <window.Icon.Send size={14} />
              </button>
            </div>
            <div className="composer-hint">
              <span><kbd>Enter</kbd> to send · <kbd>Shift</kbd>+<kbd>Enter</kbd> for newline</span>
              <button type="button" className="add-note" onClick={() => setShowNoteForm(true)}>
                <window.Icon.Plus size={11} /> Add synthetic note
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* RIGHT PANEL — alerts + citations */}
      <aside className="panel right" aria-label="Alerts and citations">
        <div className="right-stack">
          <div className="right-section">
            <div className="panel-section-label">
              <span>Alerts</span>
              <span className="count">{account.alerts.length}</span>
            </div>
            <div className="panel-body">
              {account.alerts.length > 0
                ? account.alerts.map((al, i) => (
                    <window.AlertCard key={i} alert={al} account={account} onEvidence={handleEvidence} />
                  ))
                : <window.Empty title="No open alerts" sub="When something shifts on this account — a tone change, a stall, a new signal — alerts will surface here." />}
            </div>
          </div>
          <div className="right-section">
            <div className="panel-section-label">
              <span>Citations · latest reply</span>
              <span className="count">{latestCitations.length}</span>
            </div>
            <div className="panel-body citation-list-wrap">
              {latestCitations.length > 0 ? (
                <div className="inner">
                  {latestCitations.map((c, i) => (
                    <window.CitationChip key={i} citation={c} onOpen={(aid) => { const a = findArtifact(aid); if (a) openArtifact(a); }} />
                  ))}
                </div>
              ) : <window.Empty title="No citations yet" sub="Ask the copilot anything. Each cited claim will land here, linked to the underlying artifact." />}
            </div>
          </div>
        </div>
      </aside>

      <window.NoteFormModal open={showNoteForm} onClose={() => setShowNoteForm(false)} onSubmit={submitNote} />
    </main>
  );
}

// ——————————————————————————————————————————————————————————————
// Canned response generator — chooses a plausible answer to free-text
// ——————————————————————————————————————————————————————————————
function makeCannedResponse(account, text) {
  const t = (text || "").toLowerCase();
  const arts = account.artifacts;
  const pickCites = (ids) => ids.map((id) => {
    const a = arts.find((x) => x.id === id);
    if (!a) return null;
    return { label: window.artifactTypeLabel(a.type) + " · " + a.id, artifactId: a.id };
  }).filter(Boolean);

  // Match common asks
  if (t.includes("risk") || t.includes("risks")) {
    return {
      role: "assistant",
      blocks: [
        { kind: "p", text: "Open risks for " + account.name + ", ranked by severity:" },
        { kind: "ul", items: account.alerts.map((a) => a.title + " — " + (a.sev === "critical" ? "critical" : a.sev === "warning" ? "warning" : "info")) },
        { kind: "p", text: "Each alert has linked evidence in the right panel. The single highest-leverage move this week is closing the open ask flagged in the critical alert." },
      ],
      citations: pickCites(account.alerts.flatMap((a) => a.evidence || [])).slice(0, 4),
    };
  }
  if (t.includes("next") || t.includes("action") || t.includes("week")) {
    if (account.id === "helvetica") {
      return {
        role: "assistant",
        blocks: [
          { kind: "p", text: "Single highest-leverage next action: a short note to Karin and Stefan together, acknowledging the freeze without pressing, and offering the encryption-at-rest evidence package as a no-cost preview. Two reasons:" },
          { kind: "ul", items: [
            "It addresses the one technical blocker Karin explicitly flagged before the freeze.",
            "It signals continuity to Stefan in the same thread — useful given Karin's role change.",
          ]},
          { kind: "p", text: "Avoid pushing on contract timing. The freeze is not specific to this engagement and the exception process is heavy." },
        ],
        citations: pickCites(["msg-2f9a", "mtg-feb14", "mtg-feb28"]),
      };
    }
    if (account.id === "nordbau") {
      return {
        role: "assistant",
        blocks: [
          { kind: "p", text: "Send the architecture pre-read to Lukas before Tuesday's call, then ask Andreas to formally name a single contracting owner. The pre-read closes Lukas's four questions; the contracting-owner move closes the largest active risk on the account." },
        ],
        citations: pickCites(["n-msg-it", "n-msg-ops", "n-doc-arch"]),
      };
    }
    return {
      role: "assistant",
      blocks: [
        { kind: "p", text: "Reply to Camille today with three kickoff slots between Mar 24-28, and agree the three Schedule 2 redlines explicitly inline. The deal is sign-ready; further delay only increases the Q2 holiday risk." },
      ],
      citations: pickCites(["cp-msg-kickoff", "cp-msg-legal"]),
    };
  }
  if (t.includes("changed") || t.includes("change") || t.includes("update")) {
    return {
      role: "assistant",
      blocks: [
        { kind: "p", text: "Material changes on " + account.name + " in the last two weeks:" },
        { kind: "ul", items: account.alerts.map((a) => a.title + " — " + a.body.split(".")[0] + ".") },
      ],
      citations: pickCites(account.alerts.flatMap((a) => a.evidence || [])).slice(0, 4),
    };
  }
  if (t.includes("draft") || t.includes("follow")) {
    const primary = arts.find((a) => a.type === "email");
    return {
      role: "assistant",
      blocks: [
        { kind: "p", text: "Draft below. Tone matches prior correspondence on the account; confirm before sending." },
        { kind: "p", text: "Subject: Following up — next steps" },
        { kind: "p", text: primary
          ? "Hi " + (primary.from?.split(" ")[0] || "there") + " — quick check-in on the open items from our last exchange. Happy to send three slots for a 30-minute call this week to align on next steps. — Daniel"
          : "Hi — quick check-in on the open items from our last exchange. Happy to send three slots for a 30-minute call this week. — Daniel" },
      ],
      citations: primary ? pickCites([primary.id]) : [],
    };
  }
  if (t.includes("brief") || t.includes("call") || t.includes("prep")) {
    // Re-use the existing brief
    const t0 = account.threads[0];
    if (t0 && t0.messages[1]) return t0.messages[1];
  }
  // Default: pull a short summary of the account
  return {
    role: "assistant",
    blocks: [
      { kind: "p", text: account.name + " is currently " + account.statusLabel.toLowerCase() + ". " + account.context },
      { kind: "p", text: "Indexed: " + account.stats.artifacts + " artifacts across emails, meetings, and documents. " + account.stats.alerts + " open alerts." },
      { kind: "p", text: "Ask about risks, next actions, or what's changed — or use the workflow buttons above for a structured brief." },
    ],
    citations: pickCites(arts.slice(0, 3).map((a) => a.id)),
  };
}

// ——————————————————————————————————————————————————————————————
// Header (persistent)
// ——————————————————————————————————————————————————————————————
function Header({ view, account, onHome }) {
  return (
    <header className="app-header">
      <button className="brand" onClick={onHome} aria-label="Back to account list">
        <window.Icon.Logo size={22} />
        <span className="name">
          <span className="product">Panea Memory</span>
          <span className="by">demo</span>
        </span>
      </button>
      <div className="crumbs" aria-label="Breadcrumb">
        {view === "list" && <span className="here">Accounts</span>}
        {view === "detail" && account && (
          <>
            <button onClick={onHome}>Accounts</button>
            <span className="sep">/</span>
            <span className="here">{account.name}</span>
          </>
        )}
      </div>
      <div className="header-right">
        <span className="synthetic-chip" title="This demo uses synthetic, fictional data only.">
          <span className="dot" aria-hidden="true"></span>
          Synthetic data
        </span>
        <a className="what-link" href="Landing.html">What is this?</a>
      </div>
    </header>
  );
}

// ——————————————————————————————————————————————————————————————
// Budget banner (toggleable via Tweaks)
// ——————————————————————————————————————————————————————————————
function BudgetBanner({ onDismiss }) {
  return (
    <div className="budget-banner" role="status">
      <div className="lhs">
        <span className="tag">Demo state</span>
        <span>
          The public demo has reached its daily budget. The architecture is still here to explore — try again tomorrow, or <a href="mailto:daniel@panea.dev">book a private walkthrough</a> for live interaction.
        </span>
      </div>
      <button className="closeb" onClick={onDismiss} aria-label="Dismiss banner">
        <window.Icon.X size={16} />
      </button>
    </div>
  );
}

// ——————————————————————————————————————————————————————————————
// APP root
// ——————————————————————————————————————————————————————————————
function App() {
  const [t, setT] = window.useTweaks(TWEAK_DEFAULTS);
  const [view, setView] = useState("list"); // 'list' | 'detail'
  const [accountId, setAccountId] = useState(null);
  const [modalArtifact, setModalArtifact] = useState(null);
  const [toasts, setToasts] = useState([]);
  const [showBudget, setShowBudget] = useState(false);

  const account = useMemo(() => window.ACCOUNTS.find((a) => a.id === accountId) || null, [accountId]);

  // Apply density via root data attribute
  useEffect(() => {
    document.body.dataset.density = t.density;
  }, [t.density]);

  useEffect(() => {
    setShowBudget(!!t.showBudgetBanner);
  }, [t.showBudgetBanner]);

  // Apply panel widths from tweaks
  useEffect(() => {
    const root = document.documentElement;
    root.style.setProperty("--lp-w", t.leftPanelWidth + "px");
    root.style.setProperty("--rp-w", t.rightPanelWidth + "px");
    // Apply to the actual grid:
    const dv = document.querySelector(".detail-view");
    if (dv) dv.style.gridTemplateColumns = `${t.leftPanelWidth}px 1fr ${t.rightPanelWidth}px`;
  }, [t.leftPanelWidth, t.rightPanelWidth, view]);

  const openAccount = (id) => { setAccountId(id); setView("detail"); };
  const goHome = () => { setView("list"); setAccountId(null); };

  const addToast = useCallback((tt) => {
    const id = Math.random().toString(36).slice(2);
    setToasts((prev) => [...prev, { id, ...tt }]);
  }, []);
  const dismissToast = useCallback((id) => {
    setToasts((prev) => prev.filter((x) => x.id !== id));
  }, []);

  return (
    <div className="app">
      <Header view={view} account={account} onHome={goHome} />
      {showBudget && <BudgetBanner onDismiss={() => { setShowBudget(false); setT("showBudgetBanner", false); }} />}
      {view === "list" && <AccountListView accounts={window.ACCOUNTS} onOpen={openAccount} />}
      {view === "detail" && account && (
        <AccountDetailView
          account={account}
          onBack={goHome}
          openArtifact={setModalArtifact}
          addToast={addToast}
        />
      )}

      <window.ArtifactModal artifact={modalArtifact} onClose={() => setModalArtifact(null)} />
      <window.ToastStack toasts={toasts} dismiss={dismissToast} />

      <window.TweaksPanel title="Tweaks">
        <window.TweakSection label="Demo state" />
          <window.TweakToggle
            label="Show budget-exhausted banner"
            value={t.showBudgetBanner}
            onChange={(v) => setT("showBudgetBanner", v)}
          />
          <window.TweakButton
            label="Trigger a 'rate limited' toast"
            onClick={() => addToast({ kind: "warning", title: "Rate limited", body: "Public demo is sharing inference capacity. Try again in 20 seconds." })}
          />
          <window.TweakButton
            label="Trigger a success toast"
            onClick={() => addToast({ kind: "success", title: "Note added", body: "Synthetic note added to the account index for this session." })}
          />

        <window.TweakSection label="Layout" />
          <window.TweakSlider
            label="Left panel width"
            value={t.leftPanelWidth}
            min={260} max={420} step={10}
            onChange={(v) => setT("leftPanelWidth", v)}
          />
          <window.TweakSlider
            label="Right panel width"
            value={t.rightPanelWidth}
            min={280} max={420} step={10}
            onChange={(v) => setT("rightPanelWidth", v)}
          />

        <window.TweakSection label="Navigation" />
          <window.TweakButton
            label="Open Helvetica Banking (stalled)"
            onClick={() => openAccount("helvetica")}
          />
          <window.TweakButton
            label="Open Nordbau Logistik (mid-funnel)"
            onClick={() => openAccount("nordbau")}
          />
          <window.TweakButton
            label="Open Crédit Provence (late stage)"
            onClick={() => openAccount("credit-provence")}
          />
          <window.TweakButton
            label="Back to account list"
            onClick={goHome}
          />
      </window.TweaksPanel>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
