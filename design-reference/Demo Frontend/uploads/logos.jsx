/* eslint-disable */
/* Logo set for Daniel Panea — Private AI Engineering
   All logos are SVG, scale to any size, accept `color` prop. */

const { useState } = React;

// 1. REFINED MONOGRAM — current DP, cleaner geometry, balanced strokes
function LogoMonogram({ size = 80, color = "currentColor", bg = "transparent" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" style={{ display: "block" }}>
      {bg !== "transparent" && <rect width="100" height="100" fill={bg} />}
      {/* Outer D */}
      <path d="M 28 22 L 28 78 L 56 78 A 28 28 0 0 0 56 22 Z" fill="none" stroke={color} strokeWidth="5" strokeLinejoin="miter"/>
      {/* Inner P loop, tucked inside D */}
      <path d="M 40 34 L 40 86 M 40 34 L 54 34 A 11 11 0 0 1 54 56 L 40 56" fill="none" stroke={color} strokeWidth="5" strokeLinecap="square" strokeLinejoin="miter"/>
    </svg>
  );
}

// 1-A. MONOGRAM TIGHT — same outline language, tighter strokes, more refined
function LogoMonogramTight({ size = 80, color = "currentColor", bg = "transparent" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" style={{ display: "block" }}>
      {bg !== "transparent" && <rect width="100" height="100" fill={bg} />}
      <path d="M 26 20 L 26 80 L 56 80 A 30 30 0 0 0 56 20 Z" fill="none" stroke={color} strokeWidth="3" strokeLinejoin="miter"/>
      <path d="M 40 34 L 40 88 M 40 34 L 56 34 A 12 12 0 0 1 56 58 L 40 58" fill="none" stroke={color} strokeWidth="3" strokeLinecap="square" strokeLinejoin="miter"/>
    </svg>
  );
}

// 1-B. MONOGRAM ROUNDED — softer corners, friendlier without being cute
function LogoMonogramRounded({ size = 80, color = "currentColor", bg = "transparent" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" style={{ display: "block" }}>
      {bg !== "transparent" && <rect width="100" height="100" fill={bg} />}
      <path d="M 28 22 L 28 78 L 56 78 A 28 28 0 0 0 56 22 Z" fill="none" stroke={color} strokeWidth="5" strokeLinejoin="round" strokeLinecap="round"/>
      <path d="M 40 34 L 40 86 M 40 34 L 54 34 A 11 11 0 0 1 54 56 L 40 56" fill="none" stroke={color} strokeWidth="5" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );
}

// 1-C. MONOGRAM OFFSET — D and P share spine, P descender extends below
function LogoMonogramOffset({ size = 80, color = "currentColor", bg = "transparent" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" style={{ display: "block" }}>
      {bg !== "transparent" && <rect width="100" height="100" fill={bg} />}
      {/* D */}
      <path d="M 22 24 L 22 70 L 50 70 A 23 23 0 0 0 50 24 Z" fill="none" stroke={color} strokeWidth="4" strokeLinejoin="miter"/>
      {/* P, offset down-right, descender past baseline */}
      <path d="M 42 38 L 42 90 M 42 38 L 60 38 A 13 13 0 0 1 60 64 L 42 64" fill="none" stroke={color} strokeWidth="4" strokeLinecap="square" strokeLinejoin="miter"/>
    </svg>
  );
}

// 1-D. MONOGRAM SQUARE — D and P inscribed in a circle, more emblematic
function LogoMonogramCircle({ size = 80, color = "currentColor", bg = "transparent" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" style={{ display: "block" }}>
      {bg !== "transparent" && <rect width="100" height="100" fill={bg} />}
      <circle cx="50" cy="50" r="42" fill="none" stroke={color} strokeWidth="2"/>
      <path d="M 32 30 L 32 70 L 54 70 A 20 20 0 0 0 54 30 Z" fill="none" stroke={color} strokeWidth="4" strokeLinejoin="miter"/>
      <path d="M 42 40 L 42 78 M 42 40 L 54 40 A 9 9 0 0 1 54 58 L 42 58" fill="none" stroke={color} strokeWidth="4" strokeLinecap="square" strokeLinejoin="miter"/>
    </svg>
  );
}

// 1b. MONOGRAM SOLID — filled version, more weight, more authority
function LogoMonogramSolid({ size = 80, color = "currentColor", bg = "transparent" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" style={{ display: "block" }}>
      {bg !== "transparent" && <rect width="100" height="100" fill={bg} />}
      <path d="M 22 18 L 22 82 L 56 82 A 32 32 0 0 0 56 18 Z M 32 28 L 56 28 A 22 22 0 0 1 56 72 L 32 72 Z" fill={color} fillRule="evenodd"/>
      <rect x="40" y="38" width="4" height="50" fill={color}/>
      <path d="M 44 38 L 56 38 A 9 9 0 0 1 56 56 L 44 56 L 44 50 L 54 50 A 3 3 0 0 0 54 44 L 44 44 Z" fill={color}/>
    </svg>
  );
}

// 1c. MONOGRAM SLAB — geometric / grotesk feel, square cuts
function LogoMonogramSlab({ size = 80, color = "currentColor", bg = "transparent" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" style={{ display: "block" }}>
      {bg !== "transparent" && <rect width="100" height="100" fill={bg} />}
      {/* D as bracket */}
      <path d="M 20 20 L 60 20 L 76 36 L 76 64 L 60 80 L 20 80 Z M 30 30 L 30 70 L 56 70 L 66 60 L 66 40 L 56 30 Z" fill={color} fillRule="evenodd"/>
      {/* P descender */}
      <rect x="38" y="40" width="6" height="48" fill={color}/>
      <path d="M 44 40 L 56 40 L 62 46 L 62 54 L 56 60 L 44 60 L 44 52 L 54 52 L 54 48 L 44 48 Z" fill={color}/>
    </svg>
  );
}

// 2. WORDMARK — full name, supports font-family override
function LogoWordmark({ size = 22, color = "currentColor", weight, family = "var(--font-display)", italicSecond, emphasizeSecond }) {
  const isSystemA = typeof window !== "undefined" && window.BRAND_TYPE_SYSTEM === "A";
  // Defaults differ by system: A uses italic-emphasis, B uses weight-contrast.
  const w = weight ?? (isSystemA ? 400 : 300);
  const italic = italicSecond ?? isSystemA;
  const emph = emphasizeSecond ?? !isSystemA;
  return (
    <span style={{ fontFamily: family, fontSize: size, fontWeight: w, color, letterSpacing: isSystemA ? '-0.015em' : '-0.025em', lineHeight: 1, whiteSpace: 'nowrap' }}>
      Daniel <span style={{ fontStyle: italic ? 'italic' : 'normal', fontWeight: emph ? 600 : w }}>Panea</span>
    </span>
  );
}

// 3. LOCKUP — monogram + name + role
function LogoLockup({ size = 36, color = "currentColor", Mark = LogoMonogram, family = "var(--font-display)" }) {
  const isSystemA = typeof window !== "undefined" && window.BRAND_TYPE_SYSTEM === "A";
  return (
    <div style={{ display: 'inline-flex', alignItems: 'center', gap: 14, color }}>
      <Mark size={size} color={color} />
      <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.1 }}>
        <span style={{ fontFamily: family, fontSize: size * 0.55, letterSpacing: isSystemA ? '-0.01em' : '-0.02em', fontWeight: isSystemA ? 400 : 300 }}>
          Daniel <span style={{ fontStyle: isSystemA ? 'italic' : 'normal', fontWeight: isSystemA ? 400 : 600 }}>Panea</span>
        </span>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: size * 0.28, letterSpacing: '0.14em', textTransform: 'uppercase', color: 'var(--fg-muted)', marginTop: 2 }}>
          Private AI Engineering
        </span>
      </div>
    </div>
  );
}

// 4. APERTURE — a film frame / sensor mark. Symbolic of "private capture" — what enters and what doesn't.
function LogoAperture({ size = 80, color = "currentColor", bg = "transparent" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" style={{ display: "block" }}>
      {bg !== "transparent" && <rect width="100" height="100" fill={bg} />}
      {/* Outer frame */}
      <rect x="14" y="14" width="72" height="72" fill="none" stroke={color} strokeWidth="3"/>
      {/* Notch — top-right corner cut */}
      <path d="M 70 14 L 86 14 L 86 30" fill={color} stroke="none"/>
      <path d="M 70 14 L 86 30" stroke={color} strokeWidth="3" fill="none"/>
      {/* Inner rectangle — sensor area */}
      <rect x="30" y="30" width="40" height="40" fill={color}/>
      {/* Inner notch echo */}
      <rect x="62" y="30" width="8" height="8" fill="none" stroke={bg !== "transparent" ? bg : "var(--bg)"} strokeWidth="2"/>
    </svg>
  );
}

// 4b. BRACKETS — [ dp ] — code-adjacent without being terminal
function LogoBrackets({ size = 80, color = "currentColor", bg = "transparent" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" style={{ display: "block" }}>
      {bg !== "transparent" && <rect width="100" height="100" fill={bg} />}
      {/* Left bracket */}
      <path d="M 22 26 L 14 26 L 14 74 L 22 74" fill="none" stroke={color} strokeWidth="4" strokeLinecap="square"/>
      {/* Right bracket */}
      <path d="M 78 26 L 86 26 L 86 74 L 78 74" fill="none" stroke={color} strokeWidth="4" strokeLinecap="square"/>
      {/* dp glyphs — newsreader-ish serif */}
      <text x="50" y="63" textAnchor="middle" fontFamily="var(--font-display)" fontSize="38" fontWeight="500" fill={color}>dp</text>
    </svg>
  );
}

// 4c. NODE — diagram / signal-flow mark. Three nodes, one path. Workflow.
function LogoNode({ size = 80, color = "currentColor", bg = "transparent" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" style={{ display: "block" }}>
      {bg !== "transparent" && <rect width="100" height="100" fill={bg} />}
      {/* connecting lines */}
      <path d="M 22 28 L 50 50 L 78 28 M 50 50 L 50 78" fill="none" stroke={color} strokeWidth="2.5"/>
      {/* nodes */}
      <circle cx="22" cy="28" r="7" fill={color}/>
      <circle cx="78" cy="28" r="7" fill="none" stroke={color} strokeWidth="2.5"/>
      <circle cx="50" cy="50" r="9" fill={color}/>
      <circle cx="50" cy="78" r="7" fill="none" stroke={color} strokeWidth="2.5"/>
    </svg>
  );
}

// 4d. SHIELD — minimal european shield form, half-filled. Privacy/control without literal lock icon.
function LogoShield({ size = 80, color = "currentColor", bg = "transparent" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" style={{ display: "block" }}>
      {bg !== "transparent" && <rect width="100" height="100" fill={bg} />}
      <defs>
        <clipPath id="shield-clip">
          <path d="M 50 16 L 80 26 L 80 56 Q 80 76 50 86 Q 20 76 20 56 L 20 26 Z"/>
        </clipPath>
      </defs>
      <path d="M 50 16 L 80 26 L 80 56 Q 80 76 50 86 Q 20 76 20 56 L 20 26 Z" fill="none" stroke={color} strokeWidth="3"/>
      <rect x="50" y="0" width="50" height="100" fill={color} clipPath="url(#shield-clip)"/>
    </svg>
  );
}

// 5 (legacy alt — kept for compat) — geometric, dot-and-bar (P with serif foot, D as shelter)
function LogoAlt({ size = 80, color = "currentColor", bg = "transparent" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" style={{ display: "block" }}>
      {bg !== "transparent" && <rect width="100" height="100" fill={bg} />}
      {/* Single line forming D and P */}
      <g fill="none" stroke={color} strokeWidth="4" strokeLinecap="square">
        {/* horizontal bracket — top */}
        <line x1="22" y1="24" x2="78" y2="24" />
        {/* left stem */}
        <line x1="22" y1="24" x2="22" y2="76" />
        {/* horizontal bracket — bottom */}
        <line x1="22" y1="76" x2="50" y2="76" />
        {/* D curve */}
        <path d="M 50 24 Q 78 50 50 76" />
        {/* P loop inside */}
        <path d="M 36 38 L 36 64 M 36 38 L 50 38 A 8 8 0 0 1 50 54 L 36 54" />
      </g>
    </svg>
  );
}

// 5. STAMP — square enclosed mark, like a passport stamp
function LogoStamp({ size = 80, color = "currentColor", bg = "transparent" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" style={{ display: "block" }}>
      {bg !== "transparent" && <rect width="100" height="100" fill={bg} />}
      <rect x="8" y="8" width="84" height="84" fill="none" stroke={color} strokeWidth="2"/>
      <text x="50" y="44" textAnchor="middle" fontFamily="var(--font-serif)" fontSize="32" fontStyle="italic" fill={color}>dp</text>
      <line x1="20" y1="56" x2="80" y2="56" stroke={color} strokeWidth="1"/>
      <text x="50" y="72" textAnchor="middle" fontFamily="var(--font-mono)" fontSize="7" letterSpacing="2" fill={color}>PRIVATE · AI</text>
    </svg>
  );
}

// 6. INITIALS DOT — minimal "dp." style, pure typographic
function LogoInitials({ size = 80, color = "currentColor", bg = "transparent" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" style={{ display: "block" }}>
      {bg !== "transparent" && <rect width="100" height="100" fill={bg} />}
      <text x="50" y="68" textAnchor="middle" fontFamily="var(--font-serif)" fontSize="64" fontWeight="400" fill={color}>dp</text>
      <circle cx="80" cy="68" r="3.5" fill={color}/>
    </svg>
  );
}

Object.assign(window, {
  LogoMonogram, LogoMonogramTight, LogoMonogramRounded, LogoMonogramOffset, LogoMonogramCircle,
  LogoMonogramSolid, LogoMonogramSlab,
  LogoWordmark, LogoLockup,
  LogoAperture, LogoBrackets, LogoNode, LogoShield,
  LogoAlt, LogoStamp, LogoInitials,
});
