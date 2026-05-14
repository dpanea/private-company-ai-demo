/* eslint-disable */
/* Daniel Panea — One-page website mockup */

const { useState, useEffect } = React;

// ——————————————————————————————————————————————————————————————
// Tweak defaults — edited by host on toggle
// ——————————————————————————————————————————————————————————————
const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "theme": "paper",
  "headlineVariant": "control",
  "namingVariant": "fullname",
  "logoVariant": "monogram",
  "heroPhoto": "stage",
  "accentColor": "none",
  "showStrip": true
}/*EDITMODE-END*/;

const ACCENTS = {
  none: null,
  signal: "#2A6BE0",
  amber: "#C99A3F",
  clay: "#C25A3C",
  moss: "#5B7A4F",
};

const HERO_PHOTOS = {
  stage: { src: "assets/photo-stage.jpg", caption: "EDIH · Canarias", duotone: true, label: "stage · 2025" },
  smile: { src: "assets/photo-portrait-smile.jpg", caption: "Berlin", duotone: false, label: "portrait · 01" },
  arms: { src: "assets/photo-portrait-arms.jpg", caption: "Berlin", duotone: false, label: "portrait · 02" },
};

// ——————————————————————————————————————————————————————————————
// Headlines
// ——————————————————————————————————————————————————————————————
function Headline({ variant }) {
  switch (variant) {
    case "control":
      return (
        <h1>Private AI <em>by</em><br/>design.</h1>
      );
    case "workflow":
      return (
        <h1>AI workflows<br/>that <em>fit your</em><br/>business.</h1>
      );
    case "control2":
      return (
        <h1>Modern AI,<br/><em>without</em> the<br/>data exposure.</h1>
      );
    case "european":
      return (
        <h1>Useful AI<br/>for European<br/><em>companies</em>.</h1>
      );
    default:
      return <h1>Private AI <em>by</em> design.</h1>;
  }
}

function NameMark({ variant }) {
  switch (variant) {
    case "fullname":
      return <LogoWordmark size={20} color="var(--fg)" />;
    case "lockup":
      return <LogoLockup size={32} color="var(--fg)" />;
    case "monogram":
      return <LogoMonogram size={32} color="var(--fg)" />;
    case "studio":
      return (
        <span style={{ fontFamily: "var(--font-serif)", fontSize: 22, letterSpacing: "-0.01em" }}>
          Panea <span style={{ fontStyle: "italic" }}>Labs</span>
        </span>
      );
    default:
      return <LogoWordmark size={20} color="var(--fg)" />;
  }
}

// ——————————————————————————————————————————————————————————————
// SECTIONS
// ——————————————————————————————————————————————————————————————
function Nav({ namingVariant }) {
  return (
    <nav className="top">
      <div><NameMark variant={namingVariant} /></div>
      <div className="links">
        <a href="#work">Work</a>
        <a href="#approach">Approach</a>
        <a href="#writing">Writing</a>
        <a href="#about">About</a>
      </div>
      <button className="cta">Book an assessment →</button>
    </nav>
  );
}

function Hero({ headline, photoKey }) {
  const photo = HERO_PHOTOS[photoKey] || HERO_PHOTOS.stage;
  return (
    <section className="hero">
      <div>
        <div className="eyebrow" style={{ marginBottom: 32, color: "var(--fg-muted)" }}>
          Daniel Panea · Private AI Engineering · Europe
        </div>
        <Headline variant={headline} />
        <p className="lede">
          I help European companies build <em>private, workflow-first AI systems</em> — useful automation
          without losing control of their data, tools, or processes.
        </p>
        <div className="actions">
          <button className="btn btn-primary">Book an assessment <span className="arrow">→</span></button>
          <button className="btn btn-ghost">Read the approach</button>
        </div>
        <div className="meta-line">
          <span><span className="dot"></span>Available · Q3 2026</span>
          <span>EU-hosted</span>
          <span>GDPR-aware</span>
          <span>Self-hosted models</span>
        </div>
      </div>
      <div className={"hero-photo" + (photo.duotone ? " duotone" : "")}>
        <img src={photo.src} alt="Daniel Panea" />
        <div className="photo-meta">
          <span>{photo.label}</span>
          <span>{photo.caption}</span>
        </div>
      </div>
    </section>
  );
}

function Strip() {
  return (
    <div className="strip">
      <span>Trusted across</span>
      <span className="sep">·</span>
      <span>EDIH Canarias</span>
      <span className="sep">·</span>
      <span>DES Madrid</span>
      <span className="sep">·</span>
      <span>Red CIDE</span>
      <span className="sep">·</span>
      <span>Elite Network Bayern</span>
      <span className="sep">·</span>
      <span>Featured speaker — CIDIHUB 2025</span>
    </div>
  );
}

function Problem() {
  const pains = [
    { n: "01", h: "Sensitive data, public APIs", p: "Contracts, financials, employee files, source code — pasted into uncontrolled cloud tools by employees who already use AI informally." },
    { n: "02", h: "Shadow AI in your team", p: "Useful work is happening, but you cannot answer where the data went or who has access. Procurement and legal are asking." },
    { n: "03", h: "Vendor lock-in by default", p: "Your internal knowledge becomes structurally dependent on a black box you do not control. Model choice and deployment location are business decisions." },
    { n: "04", h: "Demos that don't ship", p: "Pilots stall because the data boundary is unclear, the workflow doesn't fit your existing systems, or maintenance falls on no one." },
  ];
  return (
    <section className="section" id="approach">
      <div className="section-grid">
        <div className="section-num">01 / Problem</div>
        <div>
          <h2>Companies want the productivity of modern AI. They <em>cannot afford</em> uncontrolled data exposure.</h2>
          <p className="body">
            Internal knowledge is a strategic asset, not training material for someone else's platform.
            Workflows involving legal, financial, customer, employee, or operational data require
            <em> governance from day one</em> — not as an afterthought.
          </p>
          <div className="pain-grid">
            {pains.map((p) => (
              <div key={p.n} className="pain-cell">
                <div className="pain-num">{p.n}</div>
                <div>
                  <h4>{p.h}</h4>
                  <p>{p.p}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

function Services() {
  const items = [
    {
      n: "01", title: <>Private AI Workflow <em>Assessment</em></>,
      copy: "Two weeks, fixed scope. The lowest-friction way to understand where AI actually belongs in your business — and where it doesn't.",
      list: ["Workflow map", "Use-case scorecard", "Data & control risk review", "Recommended first pilot", "Implementation roadmap"],
      cta: "From €4,800",
    },
    {
      n: "02", title: <>Pilot <em>implementation</em></>,
      copy: "We build one painful workflow into a private AI system you actually own — connected to your existing tools, with humans kept in the loop where they should be.",
      list: ["Self-hosted or EU-private inference", "Tool & data integrations", "Permissions & audit trails", "Eval-driven, not demo-driven", "Handoff with documentation"],
      cta: "8–12 weeks",
    },
    {
      n: "03", title: <>Inference &amp; <em>infrastructure</em></>,
      copy: "What happens below the API call. For technical buyers and infrastructure teams who need depth, not just an integration.",
      list: ["Model serving & GPU efficiency", "Latency & cost optimization", "Open-source model selection", "Capacity planning", "Observability"],
      cta: "By engagement",
    },
  ];
  return (
    <section className="section" id="work">
      <div className="section-grid">
        <div className="section-num">02 / Services</div>
        <div>
          <h2>Three ways to <em>start</em>.</h2>
          <p className="body">
            Most engagements begin with the assessment. It is deliberately small, fixed-fee,
            and structured so leadership, legal, and engineering can all read the output.
          </p>
          <div className="services">
            {items.map((it) => (
              <div key={it.n} className="service">
                <div className="num">{it.n}</div>
                <h3>{it.title}</h3>
                <p>{it.copy}</p>
                <ul className="list">
                  {it.list.map((l) => <li key={l}>— {l}</li>)}
                </ul>
                <div className="more">
                  <a href="#">{it.cta} <span>→</span></a>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

function Process() {
  const steps = [
    { week: "Week 01", h: <>Map the <em>workflow</em></>, p: "Interviews, document review, current tooling. The point is to find the one workflow worth automating, not all of them." },
    { week: "Week 02", h: <>Score the <em>use cases</em></>, p: "AI fit, data sensitivity, regulatory exposure, business value. Three to five candidates ranked, with reasons." },
    { week: "Week 02", h: <>Sketch the <em>architecture</em></>, p: "Where data lives, which models, what is logged, who has access. Concrete enough to brief legal and procurement." },
    { week: "Deliverable", h: <>One pilot, <em>scoped</em></>, p: "A pilot proposal you can act on — or hand to another team. No lock-in, no multi-year contracts, no theatre." },
  ];
  return (
    <section className="section">
      <div className="section-grid">
        <div className="section-num">03 / Process</div>
        <div>
          <h2>How the <em>assessment</em> runs.</h2>
          <div className="process">
            {steps.map((s, i) => (
              <div key={i} className="process-step">
                <div className="week">{s.week}</div>
                <h4>{s.h}</h4>
                <p>{s.p}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

function Pull() {
  return (
    <section className="pull">
      <q>
        Serious companies need clear guarantees about what happens to their data, logs, prompts, outputs, and embeddings. <em>Private AI is not a feature. It is the prerequisite.</em>
      </q>
      <cite>— Note · Daniel Panea · 2026</cite>
    </section>
  );
}

function Foot({ namingVariant }) {
  return (
    <>
      <footer className="foot">
        <div>
          <div style={{ marginBottom: 32 }}><NameMark variant={namingVariant} /></div>
          <p className="signoff">
            Useful AI <em>without</em> the data exposure.<br/>
            Built for European companies.
          </p>
        </div>
        <div>
          <h5>Services</h5>
          <ul>
            <li><a href="#">Workflow Assessment</a></li>
            <li><a href="#">Pilot implementation</a></li>
            <li><a href="#">Inference & infrastructure</a></li>
          </ul>
        </div>
        <div>
          <h5>Network</h5>
          <ul>
            <li><a href="#">EDIH Canarias</a></li>
            <li><a href="#">DES Madrid</a></li>
            <li><a href="#">Red CIDE</a></li>
            <li><a href="#">Elite Network Bayern</a></li>
          </ul>
        </div>
        <div>
          <h5>Contact</h5>
          <ul>
            <li><a href="#">daniel@panea.dev</a></li>
            <li><a href="#">LinkedIn</a></li>
            <li><a href="#">Book a call →</a></li>
          </ul>
        </div>
      </footer>
      <div className="foot-bottom">
        <span>© 2026 Daniel Panea</span>
        <span>Private AI · Engineered in Europe</span>
      </div>
    </>
  );
}

// ——————————————————————————————————————————————————————————————
// APP
// ——————————————————————————————————————————————————————————————
function App() {
  const [t, setT] = window.useTweaks(TWEAK_DEFAULTS);

  // Apply theme + accent
  useEffect(() => {
    document.body.dataset.theme = t.theme;
    const accent = ACCENTS[t.accentColor];
    if (accent) {
      document.documentElement.style.setProperty("--accent-color", accent);
    } else {
      document.documentElement.style.removeProperty("--accent-color");
    }
  }, [t.theme, t.accentColor]);

  return (
    <div className="page">
      <Nav namingVariant={t.namingVariant} />
      <Hero headline={t.headlineVariant} photoKey={t.heroPhoto} />
      {t.showStrip && <Strip />}
      <Problem />
      <Services />
      <Process />
      <Pull />
      <Foot namingVariant={t.namingVariant} />

      <window.TweaksPanel title="Tweaks">
        <window.TweakSection label="Theme" />
          <window.TweakSelect
            label="Background"
            value={t.theme}
            onChange={(v) => setT("theme", v)}
            options={[
              { value: "paper", label: "Paper (warm ivory)" },
              { value: "bone", label: "Bone (cool white)" },
              { value: "dark", label: "Ink (deep navy)" },
            ]}
          />
          <window.TweakSelect
            label="Accent"
            value={t.accentColor}
            onChange={(v) => setT("accentColor", v)}
            options={[
              { value: "none", label: "None — strict mono" },
              { value: "signal", label: "Signal (electric blue)" },
              { value: "amber", label: "Amber (warm gold)" },
              { value: "clay", label: "Clay (red-orange)" },
              { value: "moss", label: "Moss (european green)" },
            ]}
          />

        <window.TweakSection label="Headline" />
          <window.TweakSelect
            label="Variant"
            value={t.headlineVariant}
            onChange={(v) => setT("headlineVariant", v)}
            options={[
              { value: "control", label: "Private AI by design." },
              { value: "workflow", label: "AI workflows that fit." },
              { value: "control2", label: "Modern AI, without exposure." },
              { value: "european", label: "Useful AI for European companies." },
            ]}
          />

        <window.TweakSection label="Identity" />
          <window.TweakSelect
            label="Brand mark"
            value={t.namingVariant}
            onChange={(v) => setT("namingVariant", v)}
            options={[
              { value: "fullname", label: "Full name (wordmark)" },
              { value: "lockup", label: "Lockup (monogram + name)" },
              { value: "monogram", label: "Monogram only" },
              { value: "studio", label: "Studio: Panea Labs" },
            ]}
          />

        <window.TweakSection label="Hero photo" />
          <window.TweakRadio
            label=""
            value={t.heroPhoto}
            onChange={(v) => setT("heroPhoto", v)}
            options={[
              { value: "stage", label: "Stage" },
              { value: "smile", label: "Portrait 01" },
              { value: "arms", label: "Portrait 02" },
            ]}
          />

        <window.TweakSection label="Sections" />
          <window.TweakToggle
            label="Show credibility strip"
            value={t.showStrip}
            onChange={(v) => setT("showStrip", v)}
          />
      </window.TweaksPanel>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
