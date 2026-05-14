/* eslint-disable */
/* Brand Reference Document — Daniel Panea */

const { useState } = React;

// ——————————————————————————————————————————————————————————————
// SECTIONS
// ——————————————————————————————————————————————————————————————

function DocHead() {
  return (
    <>
      <header className="doc-head">
        <div>
          <div className="eyebrow" style={{ marginBottom: 24 }}>Brand System · v0.1 · Internal Reference</div>
          <h1>Daniel <em>Panea</em></h1>
        </div>
        <div className="meta">
          <div>Private AI</div>
          <div>Engineering</div>
          <div>Europe — 2026</div>
        </div>
      </header>
      <p className="doc-intro">
        A reference document for a personal brand built around <em>private, workflow-first AI</em> for European companies.
        Editorial in tone, technical underneath. Use the tokens below as the canonical source — every component, page, and
        deliverable should derive from this sheet.
      </p>
    </>
  );
}

// ——————————————————————————————————————————————————————————————
// 01. LOGOS
// ——————————————————————————————————————————————————————————————

function LogoSection() {
  const cells = [
    { name: "Monogram", tag: "V1 · Primary", Comp: () => <LogoMonogram size={120} color="var(--ink-900)" /> },
    { name: "Wordmark", tag: "Secondary", Comp: () => <LogoWordmark size={42} color="var(--ink-900)" /> },
    { name: "Lockup", tag: "Email · Footer", Comp: () => <LogoLockup size={48} color="var(--ink-900)" /> },
    { name: "Monogram", tag: "V1 · Inverted", Comp: () => <LogoMonogram size={120} color="var(--paper-50)" />, dark: true },
    { name: "Wordmark", tag: "Inverted", Comp: () => <LogoWordmark size={42} color="var(--paper-50)" />, dark: true },
    { name: "Lockup", tag: "Inverted", Comp: () => <LogoLockup size={48} color="var(--paper-50)" />, dark: true },
  ];
  return (
    <section className="block">
      <div className="section-head">
        <div className="num">01 / Identity</div>
        <h2>The <em>marks</em></h2>
      </div>
      <p className="section-note">The refined V1 outline monogram is the primary mark — it preserves the existing brand equity. Wordmark and lockup are used in nav, footer, and email signatures. Each comes with an inverted version for navy backgrounds.</p>
      <div className="logo-grid" style={{ marginTop: 40 }}>
        {cells.map((c, i) => (
          <div key={i} className={"logo-cell" + (c.dark ? " dark" : "")}>
            <div className="logo-area"><c.Comp /></div>
            <div className="logo-foot">
              <span className="logo-name">{c.name}</span>
              <span className="logo-tag">{c.tag}</span>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

// ——————————————————————————————————————————————————————————————
// 02. COLOR
// ——————————————————————————————————————————————————————————————

function ColorSection() {
  const ink = [
    { name: "Ink 900", hex: "#0A1A2F", role: "Brand · Logo · Headlines" },
    { name: "Ink 800", hex: "#112540", role: "Dark surfaces" },
    { name: "Ink 700", hex: "#1B3252", role: "Elevated dark" },
    { name: "Ink 500", hex: "#4A5C75", role: "Body on light" },
    { name: "Ink 400", hex: "#768294", role: "Muted, captions" },
    { name: "Ink 300", hex: "#B6BFCC", role: "Hairlines on dark" },
  ];
  const paper = [
    { name: "Paper 50", hex: "#F7F4EE", role: "Primary background", bordered: true },
    { name: "Paper 100", hex: "#EFEAE0", role: "Section break", bordered: true },
    { name: "Paper 200", hex: "#E2DBCE", role: "Surface", bordered: true },
    { name: "Paper 300", hex: "#C9C0AF", role: "Border / hairline" },
    { name: "Bone 50", hex: "#F4F5F7", role: "Cool alt bg", bordered: true },
    { name: "Bone 200", hex: "#D7DAE0", role: "Cool hairline" },
  ];
  const accents = [
    { name: "None / Mono", hex: "—", role: "Strict monochrome", swatch: "var(--paper-50)", bordered: true },
    { name: "Signal", hex: "#2A6BE0", role: "Link · CTA accent", swatch: "#2A6BE0" },
    { name: "Amber", hex: "#C99A3F", role: "Editorial warm", swatch: "#C99A3F" },
    { name: "Clay", hex: "#C25A3C", role: "Alert · highlight", swatch: "#C25A3C" },
    { name: "Moss", hex: "#5B7A4F", role: "European calm", swatch: "#5B7A4F" },
  ];

  return (
    <section className="block">
      <div className="section-head">
        <div className="num">02 / Palette</div>
        <h2>Ink &amp; <em>paper</em></h2>
      </div>
      <p className="section-note">Two anchors and nothing else: deep navy from the existing logo, and a warm ivory paper that signals European, considered, non-tech-bro. Strict monochrome — no accent color. The restraint is the brand.</p>

      <div style={{ marginTop: 40 }}>
        <div className="eyebrow" style={{ marginBottom: 16 }}>Ink — primary</div>
        <div className="swatch-row">
          {ink.map((s, i) => (
            <div key={i} className="swatch">
              <div className="chip" style={{ background: s.hex }} />
              <div className="label"><span className="name">{s.name}</span><span className="hex">{s.hex}</span></div>
              <div style={{ fontSize: 11, color: "var(--fg-muted)" }}>{s.role}</div>
            </div>
          ))}
        </div>

        <div className="eyebrow" style={{ marginTop: 48, marginBottom: 16 }}>Paper — backgrounds</div>
        <div className="swatch-row">
          {paper.map((s, i) => (
            <div key={i} className="swatch">
              <div className={"chip" + (s.bordered ? " bordered" : "")} style={{ background: s.hex }} />
              <div className="label"><span className="name">{s.name}</span><span className="hex">{s.hex}</span></div>
              <div style={{ fontSize: 11, color: "var(--fg-muted)" }}>{s.role}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ——————————————————————————————————————————————————————————————
// 03. TYPOGRAPHY
// ——————————————————————————————————————————————————————————————

function TypeSection() {
  const isSystemA = typeof window !== "undefined" && window.BRAND_TYPE_SYSTEM === "A";
  if (isSystemA) {
    return (
      <section className="block">
        <div className="section-head">
          <div className="num">03 / Type</div>
          <h2>System A — <em>locked</em></h2>
        </div>
        <p className="section-note">Newsreader (humanist serif) for display, IBM Plex Sans for body, IBM Plex Mono for captions. Reads technical-grounded with editorial warmth. Italic of Newsreader carries personality — use it on key words.</p>

        <div className="type-grid" style={{ marginTop: 40 }}>
          <div className="type-cell">
            <div className="label">Display — Newsreader</div>
            <div className="specimen-display">Private <em>by design</em>.</div>
            <div className="type-spec">
              <span>Family · Newsreader</span>
              <span>Weight · 400</span>
              <span>Tracking · -0.02em</span>
              <span>Use · H1, H2, hero</span>
            </div>
          </div>

          <div className="type-cell">
            <div className="label">Sub-display — Newsreader</div>
            <div className="specimen-h2">AI on <em>your</em> data,<br/>under <em>your</em> control.</div>
            <div className="type-spec">
              <span>Sizes · 52 / 40 / 32 px</span>
              <span>Line-height · 1.06</span>
              <span>Italic for emphasis</span>
            </div>
          </div>

          <div className="type-cell">
            <div className="label">Body — IBM Plex Sans</div>
            <p className="specimen-body">
              European companies cannot responsibly build core workflows by pasting client data, contracts, or financials
              into uncontrolled external tools. Workflow-first AI implementation, with privacy and maintainability built in.
            </p>
            <div className="type-spec">
              <span>Family · IBM Plex Sans</span>
              <span>Weight · 400 / 500</span>
              <span>Size · 16–17 px</span>
              <span>Line-height · 1.55</span>
            </div>
          </div>

          <div className="type-cell">
            <div className="label">Mono — IBM Plex Mono</div>
            <div className="specimen-mono">
              01 / Assessment<br/>
              02 / Architecture<br/>
              03 / Implementation<br/>
              04 / Governance &amp; handoff
            </div>
            <div className="type-spec">
              <span>Family · IBM Plex Mono</span>
              <span>Size · 11–13 px</span>
              <span>Tracking · 0.14em</span>
              <span>Use · Eyebrows, labels, code</span>
            </div>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="block">
      <div className="section-head">
        <div className="num">03 / Type</div>
        <h2>System B · P4 — <em>locked</em></h2>
      </div>
      <p className="section-note">A single typeface family used at extremes — IBM Plex Sans Light (300) for display, Plex Sans Semibold (600) for emphasis, Plex Mono for captions. No serif. Reads engineered, restrained, European-technical. Hierarchy comes from weight contrast and scale, not family changes.</p>

      <div className="type-grid" style={{ marginTop: 40 }}>
        <div className="type-cell">
          <div className="label">Display — IBM Plex Sans 300</div>
          <div className="specimen-display" style={{ fontFamily: "var(--font-display)", fontWeight: 300, letterSpacing: "-0.03em" }}>Private <em style={{ fontWeight: 600, fontStyle: "normal" }}>by design</em>.</div>
          <div className="type-spec">
            <span>Family · IBM Plex Sans</span>
            <span>Weight · 300 / 600</span>
            <span>Tracking · -0.03em</span>
            <span>Use · H1, H2, hero</span>
          </div>
        </div>

        <div className="type-cell">
          <div className="label">Sub-display — IBM Plex Sans 300</div>
          <div className="specimen-h2" style={{ fontFamily: "var(--font-display)", fontWeight: 300, fontStyle: "normal", letterSpacing: "-0.025em" }}>AI on <em style={{ fontWeight: 600, fontStyle: "normal" }}>your</em> data,<br/>under <em style={{ fontWeight: 600, fontStyle: "normal" }}>your</em> control.</div>
          <div className="type-spec">
            <span>Sizes · 52 / 40 / 32 px</span>
            <span>Line-height · 1.06</span>
            <span>Emphasis via 600</span>
          </div>
        </div>

        <div className="type-cell">
          <div className="label">Body — IBM Plex Sans 400</div>
          <p className="specimen-body">
            European companies cannot responsibly build core workflows by pasting client data, contracts, or financials
            into uncontrolled external tools. Workflow-first AI implementation, with privacy and maintainability built in.
          </p>
          <div className="type-spec">
            <span>Family · IBM Plex Sans</span>
            <span>Weight · 400 / 600</span>
            <span>Size · 16–17 px</span>
            <span>Line-height · 1.55</span>
          </div>
        </div>

        <div className="type-cell">
          <div className="label">Mono — IBM Plex Mono</div>
          <div className="specimen-mono">
            01 / Assessment<br/>
            02 / Architecture<br/>
            03 / Implementation<br/>
            04 / Governance &amp; handoff
          </div>
          <div className="type-spec">
            <span>Family · IBM Plex Mono</span>
            <span>Size · 11–13 px</span>
            <span>Tracking · 0.14em</span>
            <span>Use · Eyebrows, labels, code</span>
          </div>
        </div>
      </div>
    </section>
  );
}

// ——————————————————————————————————————————————————————————————
// 04. COMPONENTS
// ——————————————————————————————————————————————————————————————

function ComponentSection() {
  return (
    <section className="block">
      <div className="section-head">
        <div className="num">04 / Components</div>
        <h2>Building <em>blocks</em></h2>
      </div>
      <p className="section-note">A small set, used consistently. Buttons are square — no rounded SaaS chrome. Cards rely on hairlines and breathing room rather than shadows.</p>

      <div className="comp-grid" style={{ marginTop: 40 }}>
        <div className="comp">
          <div className="label">Buttons</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 16, alignItems: "center" }}>
            <button className="btn btn-primary">Book an assessment <span className="arrow">→</span></button>
            <button className="btn btn-ghost">View case studies</button>
            <button className="btn btn-link">Read the note <span className="arrow">→</span></button>
          </div>
        </div>

        <div className="comp">
          <div className="label">Pills · Tags</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 12 }}>
            <span className="pill"><span className="dot"></span>Available · Q3 2026</span>
            <span className="pill">EU-hosted</span>
            <span className="pill">GDPR-aware</span>
            <span className="pill">Self-hosted models</span>
          </div>
        </div>

        <div className="comp" style={{ gridColumn: "span 2" }}>
          <div className="label">Service cards</div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 32 }}>
            <div className="service-card">
              <div className="num">01</div>
              <div>
                <h4>Private AI Workflow Assessment</h4>
                <p>Two weeks, fixed scope. Workflow map, risk review, recommended first pilot, and a rough technical architecture.</p>
              </div>
            </div>
            <div className="service-card">
              <div className="num">02</div>
              <div>
                <h4>Pilot implementation</h4>
                <p>Build one painful workflow into a private AI system you actually own — connected to your existing tools, with humans kept in the loop where they should be.</p>
              </div>
            </div>
            <div className="service-card">
              <div className="num">03</div>
              <div>
                <h4>Inference &amp; infrastructure</h4>
                <p>What happens below the API call: model serving, GPU efficiency, latency, cost. For technical buyers and infrastructure teams.</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

// ——————————————————————————————————————————————————————————————
// 05. PHOTOGRAPHY
// ——————————————————————————————————————————————————————————————

function PhotoSection() {
  return (
    <section className="block">
      <div className="section-head">
        <div className="num">05 / Photography</div>
        <h2>Image <em>treatment</em></h2>
      </div>
      <p className="section-note">Two modes: full-color, generous crop, paper-warm tones for portraits — and a navy duotone for credibility shots (stage, conferences). Always plenty of negative space; the figure is small inside the frame.</p>

      <div className="photo-grid" style={{ marginTop: 40 }}>
        <div className="photo-frame">
          <img src="assets/photo-portrait-smile.jpg" alt="Portrait — relaxed" />
          <div className="frame-meta"><span>portrait · 01</span><span>color</span></div>
        </div>
        <div className="photo-frame">
          <img src="assets/photo-portrait-arms.jpg" alt="Portrait — arms crossed" />
          <div className="frame-meta"><span>portrait · 02</span><span>color</span></div>
        </div>
        <div className="photo-frame duotone">
          <img src="assets/photo-stage.jpg" alt="Stage — credibility" />
          <div className="frame-meta"><span>stage · cidihub</span><span>duotone</span></div>
        </div>
      </div>
    </section>
  );
}

// ——————————————————————————————————————————————————————————————
// 06. VOICE
// ——————————————————————————————————————————————————————————————

function VoiceSection() {
  return (
    <section className="block">
      <div className="section-head">
        <div className="num">06 / Voice</div>
        <h2>How it <em>reads</em></h2>
      </div>
      <p className="section-note">Plain, declarative, slightly cool. No jargon, no hype, no exclamation marks. The italic carries the sharpness; the rest stays calm.</p>

      <div className="voice-grid" style={{ marginTop: 40 }}>
        <div className="voice-card do-card">
          <h4>↗ Use</h4>
          <ul>
            <li>“Private AI systems for companies that <em>cannot paste their business</em> into generic cloud tools.”</li>
            <li>“Modern AI productivity, <em>without uncontrolled data exposure</em>.”</li>
            <li>“Workflow-first, not <em>model-first</em>.”</li>
            <li>“Your first <em>trustworthy</em> AI workflow.”</li>
          </ul>
        </div>
        <div className="voice-card dont-card">
          <h4>↘ Avoid</h4>
          <ul>
            <li>“Unlock the power of AI for your business!”</li>
            <li>“Revolutionary AI solutions tailored to you.”</li>
            <li>“Provider X is stealing your data.”</li>
            <li>“Cutting-edge, next-gen, game-changing.”</li>
          </ul>
        </div>
      </div>
    </section>
  );
}

// ——————————————————————————————————————————————————————————————
// APP
// ——————————————————————————————————————————————————————————————

function App() {
  return (
    <>
      <DocHead />
      <LogoSection />
      <ColorSection />
      <TypeSection />
      <ComponentSection />
      <PhotoSection />
      <VoiceSection />
      <footer style={{ marginTop: 120, paddingTop: 32, borderTop: "1px solid var(--hairline)", display: "flex", justifyContent: "space-between", fontFamily: "var(--font-mono)", fontSize: 11, letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--fg-muted)" }}>
        <span>End of reference</span>
        <span>Daniel Panea · 2026</span>
      </footer>
    </>
  );
}

ReactDOM.createRoot(document.getElementById("doc-root")).render(<App />);
