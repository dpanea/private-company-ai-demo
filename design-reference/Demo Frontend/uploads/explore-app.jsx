/* eslint-disable */
/* Logo & Font Exploration page */

const { useState } = React;

// ─────────── DOC HEAD ───────────
function DocHead() {
  return (
    <>
      <header className="doc-head">
        <div>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, letterSpacing: "0.18em", textTransform: "uppercase", color: "var(--fg-muted)", marginBottom: 24 }}>
            Round 02 · More logos, alt fonts
          </div>
          <h1>Five <em>monograms</em>,<br/>two <em>type systems</em>.</h1>
        </div>
        <div className="meta">
          <div>Daniel Panea</div>
          <div>Brand · v0.2</div>
          <div>2026</div>
        </div>
      </header>
      <p className="intro">
        Five monogram tunings of the existing outline letterform, plus two locked font systems.
        Pick a monogram and we'll thread it through the brand.
      </p>
    </>
  );
}

// ─────────── 01 · NEW LOGO DIRECTIONS ───────────
function NewLogoSection() {
  const cells = [
    { name: "Aperture", tag: "New · Symbolic", note: "Frame + corner notch. What enters, what doesn't.", Comp: () => <LogoAperture size={120} color="var(--ink-900)" /> },
    { name: "Node", tag: "New · Workflow", note: "Three nodes, one path. Signal flow, not data flow.", Comp: () => <LogoNode size={120} color="var(--ink-900)" /> },
    { name: "Shield", tag: "New · Control", note: "Half-filled european shield. Privacy without a lock.", Comp: () => <LogoShield size={120} color="var(--ink-900)" /> },
    { name: "Aperture", tag: "Inverted", Comp: () => <LogoAperture size={120} color="var(--paper-50)" />, dark: true },
    { name: "Node", tag: "Inverted", Comp: () => <LogoNode size={120} color="var(--paper-50)" />, dark: true },
    { name: "Shield", tag: "Inverted", Comp: () => <LogoShield size={120} color="var(--paper-50)" />, dark: true },
  ];
  return (
    <section className="block">
      <div className="section-head">
        <div className="num">01 / New directions</div>
        <h2>Three <em>new</em> marks.</h2>
      </div>
      <p className="section-note">Non-initial, non-stamp. Each carries a meaning tied to the positioning: aperture (controlled capture), node (workflow), shield (control). All work as monochrome and inverted.</p>
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

// ─────────── 01 · LOCKED FONT SYSTEMS (P1 + P4) ───────────
function LockedSystemsSection() {
  const systems = [
    {
      label: "System A · P1 — Newsreader + IBM Plex Sans",
      hFamily: "'Newsreader', serif",
      bFamily: "'IBM Plex Sans', sans-serif",
      mFamily: "'IBM Plex Mono', monospace",
      hWeight: 400,
      use: "Default. Use for the main public site, decks, proposals.",
    },
    {
      label: "System B · P4 — IBM Plex Sans (300/600) + IBM Plex Mono",
      hFamily: "'IBM Plex Sans', sans-serif",
      bFamily: "'IBM Plex Sans', sans-serif",
      mFamily: "'IBM Plex Mono', monospace",
      hWeight: 300,
      use: "Stripped, no-serif alternative. For technical writeups, code-heavy pages, infra credibility lane.",
    },
  ];
  return (
    <section className="block">
      <div className="section-head">
        <div className="num">01 / Locked systems</div>
        <h2>Two <em>systems</em>, one brand.</h2>
      </div>
      <p className="section-note">Both are in. P1 (System A) is the default voice for marketing and the main site. P4 (System B) is the alt voice for technical content — inference notes, infrastructure pages, GitHub-adjacent docs. Same color tokens, same monogram, different type.</p>
      <div className="pair-grid" style={{ marginTop: 40 }}>
        {systems.map((p, i) => (
          <div key={i} className="pair-cell">
            <div className="label">{p.label}</div>
            <div className="pair-h" style={{ fontFamily: p.hFamily, fontWeight: p.hWeight }}>
              AI on <em>your</em> data,<br/>under <em>your</em> control.
            </div>
            <div className="pair-body" style={{ fontFamily: p.bFamily }}>
              I help European companies build private, workflow-first AI systems — useful automation
              without losing control of their data, tools, or processes.
            </div>
            <div className="pair-mono" style={{ fontFamily: p.mFamily }}>
              <span>01 / Assessment</span>
              <span>02 / Architecture</span>
              <span>03 / Implementation</span>
            </div>
            <div style={{ fontSize: 13, color: "var(--ink-700)", fontStyle: "italic", fontFamily: "var(--font-display)" }}>
              {p.use}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

// ─────────── 02 · DP MONOGRAM VARIANTS ───────────
function MonogramVariantSection() {
  const cells = [
    { name: "Original", tag: "v1 · 5px outline", Comp: () => <LogoMonogram size={120} color="var(--ink-900)" /> },
    { name: "Tight", tag: "v2 · 3px outline, refined", Comp: () => <LogoMonogramTight size={120} color="var(--ink-900)" /> },
    { name: "Rounded", tag: "v3 · soft corners", Comp: () => <LogoMonogramRounded size={120} color="var(--ink-900)" /> },
    { name: "Offset", tag: "v4 · P descends past baseline", Comp: () => <LogoMonogramOffset size={120} color="var(--ink-900)" /> },
    { name: "Circle", tag: "v5 · inscribed, emblematic", Comp: () => <LogoMonogramCircle size={120} color="var(--ink-900)" /> },
    { name: "Original · Inv", tag: "v1 inverted", Comp: () => <LogoMonogram size={120} color="var(--paper-50)" />, dark: true },
  ];
  return (
    <section className="block">
      <div className="section-head">
        <div className="num">02 / DP variants</div>
        <h2>Same <em>letterform</em>, five tunings.</h2>
      </div>
      <p className="section-note">All in the original outline lineage you liked. Differences are stroke weight, corner treatment, and proportion. Tight (v2) reads most refined at small sizes; Original (v1) holds best at favicon scale.</p>
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

// ─────────── 03 · WORDMARK VARIANTS ───────────
function WordmarkSection() {
  const cells = [
    { label: "A · Newsreader (humanist serif)", family: "'Newsreader', serif", italic: true },
    { label: "B · Fraunces (warm + technical)", family: "'Fraunces', serif", italic: true },
    { label: "C · IBM Plex Sans Light (no serif)", family: "'IBM Plex Sans', sans-serif", italic: false, weight: 300 },
    { label: "D · Geist Mono (mono display)", family: "'Geist Mono', monospace", italic: false, weight: 400 },
    { label: "E · Space Grotesk Medium", family: "'Space Grotesk', sans-serif", italic: false, weight: 500 },
    { label: "F · IBM Plex Mono Italic", family: "'IBM Plex Mono', monospace", italic: true, weight: 400 },
  ];
  return (
    <section className="block">
      <div className="section-head">
        <div className="num">03 / Wordmark</div>
        <h2>Same name, <em>six</em> voices.</h2>
      </div>
      <p className="section-note">"Daniel Panea" rendered in different families. The mono and grotesk options dial down the consultant feel; the serifs keep some warmth. Mono italic (F) is unconventional but reads <em>technical, with confidence</em>.</p>
      <div className="wordmark-grid" style={{ marginTop: 40 }}>
        {cells.map((c, i) => (
          <div key={i} className="wordmark-cell">
            <div className="label">{c.label}</div>
            <div className="specimen">
              <span style={{ fontFamily: c.family, fontWeight: c.weight || 400, fontSize: 56, letterSpacing: "-0.015em", lineHeight: 1, color: "var(--ink-900)", whiteSpace: "nowrap" }}>
                Daniel <span style={{ fontStyle: c.italic ? "italic" : "normal" }}>Panea</span>
              </span>
            </div>
            <div className="meta">
              <span>{c.family.split(",")[0].replace(/'/g, "")}</span>
              <span>· wt {c.weight || 400}</span>
              {c.italic && <span>· italic</span>}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

// ─────────── 04 · TYPE SPECIMENS ───────────
function TypeSpecimens() {
  const fonts = [
    { name: "Newsreader", meta: "Google · Variable · 6→72", role: "Display\nHumanist serif\nWarm, less stiff", family: "'Newsreader', serif", italic: true },
    { name: "Fraunces", meta: "Google · Variable", role: "Display alt\nQuirkier, more soul", family: "'Fraunces', serif", italic: true },
    { name: "IBM Plex Sans", meta: "IBM · OFL", role: "Body\nGrounded, technical heritage", family: "'IBM Plex Sans', sans-serif", italic: false },
    { name: "Space Grotesk", meta: "Florian Karsten · OFL", role: "Body alt\nGeometric, modern", family: "'Space Grotesk', sans-serif", italic: false },
    { name: "Geist Mono", meta: "Vercel · OFL", role: "Display mono\nTechnical, not terminal", family: "'Geist Mono', monospace", italic: false },
    { name: "IBM Plex Mono", meta: "IBM · OFL", role: "Caption mono\nDocs, code, captions", family: "'IBM Plex Mono', monospace", italic: false },
  ];
  return (
    <section className="block">
      <div className="section-head">
        <div className="num">04 / Type</div>
        <h2>Less <em>editorial</em>, more <em>technical-warm</em>.</h2>
      </div>
      <p className="section-note">Four font candidates, picked to feel grounded and slightly unconventional. Newsreader replaces Instrument Serif as the default headline (more humanist warmth). IBM Plex Sans replaces Geist for body (technical heritage, less SaaS). Geist Mono can carry display weight at large sizes.</p>
      <div style={{ marginTop: 40, borderTop: "1px solid var(--hairline)" }}>
        {fonts.map((f, i) => (
          <div key={i} className="font-row">
            <div className="name">
              <span className="fname">{f.name}</span>
              <span className="fmeta">{f.meta}</span>
            </div>
            <div className="specimen-large" style={{ fontFamily: f.family }}>
              Private AI <span style={{ fontStyle: f.italic ? "italic" : "normal" }}>by design</span>
            </div>
            <div className="role">{f.role.split("\n").map((line, j) => <div key={j}>{line}</div>)}</div>
          </div>
        ))}
      </div>
    </section>
  );
}

// ─────────── 05 · PAIRING TESTS ───────────
function PairingSection() {
  const pairs = [
    {
      label: "P1 · Newsreader + IBM Plex Sans",
      hFamily: "'Newsreader', serif",
      bFamily: "'IBM Plex Sans', sans-serif",
      mFamily: "'IBM Plex Mono', monospace",
      note: "Default. Humanist serif + technical sans. Warm but credible.",
    },
    {
      label: "P2 · Geist Mono + IBM Plex Sans",
      hFamily: "'Geist Mono', monospace",
      hWeight: 500,
      bFamily: "'IBM Plex Sans', sans-serif",
      mFamily: "'IBM Plex Mono', monospace",
      note: "Display mono. Very technical, almost no editorial feel. Best for engineer-buyers.",
    },
    {
      label: "P3 · Fraunces + Space Grotesk",
      hFamily: "'Fraunces', serif",
      bFamily: "'Space Grotesk', sans-serif",
      mFamily: "'IBM Plex Mono', monospace",
      note: "More personality, slightly studio-leaning. Less corporate, more independent practitioner.",
    },
    {
      label: "P4 · IBM Plex Sans Light + IBM Plex Mono",
      hFamily: "'IBM Plex Sans', sans-serif",
      hWeight: 300,
      bFamily: "'IBM Plex Sans', sans-serif",
      mFamily: "'IBM Plex Mono', monospace",
      note: "No serif at all. Stripped, technical, european. Most unconventional.",
    },
  ];
  return (
    <section className="block">
      <div className="section-head">
        <div className="num">05 / Pairings</div>
        <h2>Four <em>pairings</em> tested.</h2>
      </div>
      <p className="section-note">Same headline, body, and mono caption — different font systems. P1 is the recommended default; P2 leans hardest into technical credibility; P4 is the unconventional, no-serif option.</p>
      <div className="pair-grid" style={{ marginTop: 40 }}>
        {pairs.map((p, i) => (
          <div key={i} className="pair-cell">
            <div className="label">{p.label}</div>
            <div className="pair-h" style={{ fontFamily: p.hFamily, fontWeight: p.hWeight || 400 }}>
              AI on <em>your</em> data,<br/>under <em>your</em> control.
            </div>
            <div className="pair-body" style={{ fontFamily: p.bFamily }}>
              I help European companies build private, workflow-first AI systems — useful automation
              without losing control of their data, tools, or processes.
            </div>
            <div className="pair-mono" style={{ fontFamily: p.mFamily }}>
              <span>01 / Assessment</span>
              <span>02 / Architecture</span>
              <span>03 / Implementation</span>
            </div>
            <div style={{ fontSize: 13, color: "var(--ink-700)", fontStyle: "italic", fontFamily: "var(--font-display)" }}>
              {p.note}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function App() {
  return (
    <>
      <DocHead />
      <LockedSystemsSection />
      <MonogramVariantSection />
    </>
  );
}

ReactDOM.createRoot(document.getElementById("doc-root")).render(<App />);
