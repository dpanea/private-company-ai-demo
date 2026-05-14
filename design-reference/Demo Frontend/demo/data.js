/* eslint-disable */
/* PANEA MEMORY — synthetic account data
   All names, companies and content are fictional. */

window.ACCOUNTS = [
  // ============================================================
  // 1. HELVETICA BANKING AG — Stalled, mid-funnel
  // ============================================================
  {
    id: "helvetica",
    name: "Helvetica Banking AG",
    industry: "Financial Services",
    country: "Zürich, Switzerland",
    status: "stalled",
    statusLabel: "Stalled",
    context: "Procurement freeze tied to a group security review. Champion went quiet 14 days ago after the encryption-at-rest evidence ask.",
    stats: { artifacts: 11, alerts: 3, days: 22 },
    artifacts: [
      // — Emails —
      {
        id: "msg-2f9a",
        type: "email",
        title: "Re: Q3 procurement freeze",
        meta: "Karin Lundberg → Daniel · Mar 04",
        date: "Mar 04, 2026",
        from: "Karin Lundberg <k.lundberg@helvetica-banking.ch>",
        to: "Daniel Panea <daniel@panea.dev>",
        subject: "Re: Q3 procurement freeze",
        body: [
          "Daniel,",
          "Apologies for the silence. The group risk office triggered a wider security review on Feb 28 and procurement is paused on all new contracts until end of Q3. This is not specific to your engagement — it touches the seven other RFPs we had in flight.",
          "I'm being moved to the Conduct & Operational Risk team in two weeks. Stefan from CTO office will pick up sponsorship of the AI initiative, but realistically nothing moves until the review concludes.",
          "Two questions while we wait: (1) the encryption-at-rest evidence we discussed Feb 14 — is the SOC 2-style attestation a feasible deliverable on your end, or do we need to use the ISAE 3000 path? (2) The EU residency clause for the MSA — can your counsel confirm Frankfurt is acceptable, or would Helsinki be a better default?",
          "Will loop in Stefan when the org change is announced.",
          "— Karin",
        ],
      },
      {
        id: "msg-1c44",
        type: "email",
        title: "Renewal timing & internal alignment",
        meta: "Andreas Weiss → Daniel · Feb 22",
        date: "Feb 22, 2026",
        from: "Andreas Weiss <a.weiss@helvetica-banking.ch>",
        to: "Daniel Panea <daniel@panea.dev>",
        subject: "Renewal timing & internal alignment",
        body: [
          "Daniel,",
          "Following up on the discovery call. Karin and I need a week of internal alignment before we can move on the pilot. The two outstanding items: encryption-at-rest evidence and the EU-residency clause in the MSA.",
          "I'll come back to you by end of next week with a position.",
          "Best,",
          "Andreas",
        ],
      },
      {
        id: "msg-8d11",
        type: "email",
        title: "Discovery call — agenda",
        meta: "Karin Lundberg → Daniel · Feb 11",
        date: "Feb 11, 2026",
        from: "Karin Lundberg <k.lundberg@helvetica-banking.ch>",
        to: "Daniel Panea <daniel@panea.dev>",
        subject: "Discovery call — agenda",
        body: [
          "Daniel,",
          "Confirming Feb 14, 10:00 CET. Andreas (procurement), Marcus (CISO office), and myself. Stefan from CTO office may join if his schedule clears.",
          "Three topics on our side: (1) data flow — what leaves our boundary and what doesn't; (2) model selection — open-weights vs hosted; (3) what the pilot scope realistically looks like in 8 weeks vs 12.",
          "Looking forward.",
          "— Karin",
        ],
      },
      {
        id: "msg-4a01",
        type: "email",
        title: "Initial inquiry — referred by EDIH Zürich",
        meta: "Karin Lundberg → Daniel · Jan 19",
        date: "Jan 19, 2026",
        from: "Karin Lundberg <k.lundberg@helvetica-banking.ch>",
        to: "Daniel Panea <daniel@panea.dev>",
        subject: "Introduction — referred by EDIH Zürich",
        body: [
          "Daniel,",
          "We were referred by the EDIH Zürich office, who suggested your assessment offering for a workflow we're trying to scope responsibly. Context: we're a mid-cap private bank with significant exposure to GDPR and FINMA constraints, and we want to deploy AI for internal knowledge workflows without becoming the next Glassdoor story.",
          "Would the assessment format be the right starting point? Happy to share more on a call.",
          "— Karin Lundberg, Head of Information Security",
        ],
      },

      // — Meetings —
      {
        id: "mtg-feb14",
        type: "meeting",
        title: "Discovery call — security review",
        meta: "4 attendees · Feb 14",
        date: "Feb 14, 2026",
        attendees: ["Karin Lundberg (Helvetica, InfoSec)", "Andreas Weiss (Helvetica, Procurement)", "Marcus Brun (Helvetica, CISO office)", "Daniel Panea (Panea)"],
        duration: "52 minutes",
        transcript: [
          { who: "Karin", ts: "00:01", text: "Thanks for making time. The way we want to structure this — three blocks, twenty minutes each. Data flow, model selection, scope." },
          { who: "Daniel", ts: "00:18", text: "Works for me. Before we start: are there any topics that are out of scope from your side? Better to flag now than discover at hour fifty." },
          { who: "Marcus", ts: "00:35", text: "Anything that touches customer financial data is out of scope for the pilot. We'd want to see the system run on internal knowledge artifacts first — policies, internal email, our own meeting notes — before we even think about customer-adjacent workflows." },
          { who: "Daniel", ts: "01:02", text: "Understood. That actually makes the scoping easier, not harder — internal-only is the cleanest pilot shape." },
          { who: "Karin", ts: "08:12", text: "Two specific concerns from the InfoSec side. First, encryption-at-rest evidence. We need something we can hand to our group risk office. Second, the residency clause — Frankfurt or Helsinki, but not Dublin." },
          { who: "Daniel", ts: "08:48", text: "Both are doable. On encryption-at-rest, I can provide a SOC 2-style attestation or the ISAE 3000 path — your call which one your auditors prefer. Residency: Frankfurt is the default; Helsinki is available, Dublin is excluded by config." },
          { who: "Andreas", ts: "22:30", text: "On scope and timeline — what's a realistic 8-week deliverable versus 12-week?" },
          { who: "Daniel", ts: "22:50", text: "Eight weeks gets you a private index of a single source corpus — say, the policies repository — and the conversation surface. Twelve weeks adds the alerting layer and the CRM-side integration. I'd suggest starting at eight and extending only if the eval set looks healthy." },
        ],
      },
      {
        id: "mtg-jan22",
        type: "meeting",
        title: "Initial scoping — Karin & Daniel",
        meta: "2 attendees · Jan 22",
        date: "Jan 22, 2026",
        attendees: ["Karin Lundberg (Helvetica)", "Daniel Panea (Panea)"],
        duration: "38 minutes",
        transcript: [
          { who: "Karin", ts: "00:00", text: "Quick intro call before we put a wider group together. Your assessment format — how prescriptive is it?" },
          { who: "Daniel", ts: "00:14", text: "Two weeks fixed, fixed fee. The output is a workflow map, a use-case scorecard, a data-and-control risk review, and one recommended pilot. It's deliberately small. Procurement and legal usually find it easier to approve than an open-ended scoping engagement." },
          { who: "Karin", ts: "12:40", text: "What we want to avoid is six months of pilot-of-the-pilot. We've seen that pattern with the big consultancies." },
          { who: "Daniel", ts: "13:05", text: "Agreed. The structure is intentionally adversarial to that — the deliverable is a pilot you can either green-light or hand to another team. No path-of-least-resistance into a multi-quarter engagement." },
        ],
      },
      {
        id: "mtg-feb28",
        type: "meeting",
        title: "Internal Helvetica review — partial recording",
        meta: "3 attendees · Feb 28",
        date: "Feb 28, 2026",
        attendees: ["Stefan Roth (Helvetica, CTO office)", "Karin Lundberg", "Andreas Weiss"],
        duration: "Excerpt — 8 minutes (forwarded by Karin)",
        transcript: [
          { who: "Stefan", ts: "00:00", text: "Group risk has triggered a wider security review. Effective immediately, all AI vendor contracts pause until end of Q3." },
          { who: "Andreas", ts: "00:22", text: "Does that include the Panea engagement? We were close to signing on the assessment." },
          { who: "Stefan", ts: "00:34", text: "It includes the assessment. The exception process exists but it's heavy — I wouldn't pursue it unless there's a concrete revenue dependency, which there isn't." },
          { who: "Karin", ts: "01:18", text: "I'll write to Daniel today and explain. They've been transparent so far — I don't want to ghost them." },
        ],
      },

      // — Documents —
      {
        id: "doc-pilot-r3",
        type: "docx",
        title: "Pilot scope — revision 3",
        meta: "DOCX · 6 pp · Feb 20",
        date: "Feb 20, 2026",
        bodyMarkdown: {
          title: "Pilot Scope · Helvetica Banking AG · Rev 3",
          sections: [
            { h: "Objective", p: "Deploy a private, source-backed conversation surface over Helvetica's internal policy and meeting-note corpus. Single-tenant, EU-hosted, open-weight model defaults. No customer-financial data in scope for the pilot." },
            { h: "Corpus", list: ["~2,400 internal policy documents (current + 12-month archive)", "~18 months of internal meeting transcripts (filtered subset)", "Excludes: customer files, transaction data, employee personnel records"] },
            { h: "Models", p: "Llama 3.x-70B (instruction-tuned) for synthesis; mxbai-embed-large for retrieval. EU GPU pool, Frankfurt-primary, Helsinki-secondary." },
            { h: "Evaluation", p: "Pilot ships with a 240-question eval set drawn from real internal queries. Citation precision and answer faithfulness tracked over deploys. Failure of the eval gate blocks production handover." },
            { h: "Deliverables", list: ["Private index + conversation surface (web)", "CRM panel integration (Slack first, Salesforce later)", "Audit log + per-query trace exporter", "Eval set + runbook"] },
            { h: "Timeline", p: "8 weeks engagement, extending to 12 weeks if eval gate looks healthy. Weekly sync, written status, no demoware." },
          ],
        },
      },
      {
        id: "doc-secpol",
        type: "pdf",
        title: "Information security policy — excerpt",
        meta: "PDF · OCR · 12 pp · Feb 12",
        date: "Feb 12, 2026",
        ocr: true,
        pages: [
          {
            n: "001",
            title: "Information Security Policy — Excerpt",
            paras: [
              "[OCR] This document is a controlled excerpt of Helvetica Banking AG's Information Security Policy, Group Standard ISP-2024-04, Revision 3. Reproduction outside the named recipient is prohibited.",
              "[OCR] The provisions in this excerpt cover (a) classification of information assets; (b) third-party access and data residency; (c) cryptographic controls; (d) audit trail and review obligations. The full policy is approximately 84 pages and is not included here.",
              "[OCR] Recipients are reminded that the contents of this excerpt are classified as 'Internal — Restricted Distribution' under the ISP-2024-04 framework. Forwarding is permitted only to named delegates of the recipient's organization.",
            ],
          },
          {
            n: "002",
            title: "Section 3 — Cryptographic Controls",
            paras: [
              "[OCR] 3.1 All information assets classified as 'Confidential' or above shall be encrypted at rest using AES-256 or an equivalent algorithm approved by the Group Cryptography Standard.",
              "[OCR] 3.2 Cryptographic key management shall follow NIST SP 800-57 Part 1 Rev 5 principles, with key custody held by the Group Information Security Office.",
              "[OCR] 3.3 Third-party service providers handling 'Confidential' information assets shall provide evidence of equivalent or superior cryptographic controls, attested via SOC 2 Type II or ISAE 3000.",
              "[OCR] 3.4 Data residency for 'Confidential' assets shall be restricted to jurisdictions named in Annex B of the Group Data Residency Standard (DRS-2024-01). The named jurisdictions are: Switzerland, Germany, Finland, Liechtenstein.",
            ],
          },
          {
            n: "003",
            title: "Section 4 — Audit Trail and Review",
            paras: [
              "[OCR] 4.1 All systems processing 'Confidential' information assets shall maintain a tamper-evident audit log retained for not less than 84 months.",
              "[OCR] 4.2 The audit log shall record, at minimum: actor identity, timestamp, action class, target asset identifier, and source IP address.",
              "[OCR] 4.3 Quarterly review of the audit log is the responsibility of the Information Security Office. Material anomalies shall be reported to the Group Risk Committee within ten business days.",
            ],
          },
        ],
      },
      {
        id: "doc-msa",
        type: "pdf",
        title: "MSA template — group standard",
        meta: "PDF · 18 pp · Feb 20",
        date: "Feb 20, 2026",
        pages: [
          {
            n: "001",
            title: "Master Services Agreement — Template",
            paras: [
              "This Master Services Agreement (the \"Agreement\") is entered into by and between Helvetica Banking AG, a corporation organized under the laws of Switzerland (\"Client\"), and the Service Provider identified in the cover page.",
              "Capitalized terms used herein shall have the meanings set out in Schedule 1.",
            ],
          },
          {
            n: "008",
            title: "Section 7 — Data Residency",
            paras: [
              "7.1 The Service Provider shall ensure that all Client Data is processed and stored exclusively within the jurisdictions named in Annex B (the \"Permitted Jurisdictions\").",
              "7.2 For the avoidance of doubt, the United States, Ireland, and the United Kingdom are NOT Permitted Jurisdictions for the purposes of this Agreement.",
              "7.3 Any change to the Permitted Jurisdictions requires prior written approval of the Client's Group Information Security Office.",
            ],
          },
        ],
      },
      {
        id: "doc-deckv1",
        type: "docx",
        title: "Approach memo — sent post-discovery",
        meta: "DOCX · 4 pp · Feb 16",
        date: "Feb 16, 2026",
        bodyMarkdown: {
          title: "Approach Memo — Helvetica Banking AG",
          sections: [
            { h: "What we heard", p: "Internal-only pilot. No customer-financial data in scope. Encryption-at-rest evidence is a procurement-blocker. EU residency is non-negotiable; Frankfurt or Helsinki acceptable, Dublin and London are not." },
            { h: "What we propose", list: ["Single-tenant deployment in your VPC or Panea-managed Frankfurt pool", "Open-weight model defaults (Llama 3.x / mxbai-embed)", "SOC 2-style attestation for encryption-at-rest, deliverable in week 2 of engagement", "EU-only data residency, configured at the infrastructure layer, not policy layer"] },
            { h: "What we won't do", list: ["Train models on Client Data", "Cross-tenant index sharing", "Silent fallback to non-EU regions under load"] },
          ],
        },
      },
    ],
    alerts: [
      {
        sev: "critical",
        title: "No reply in 14 days",
        body: "Two open asks on encryption evidence and the MSA residency clause sent Feb 22. Champion went quiet after the Feb 28 procurement freeze. Pattern matches prior stalled-and-revived accounts only 32% of the time.",
        evidence: ["msg-1c44", "msg-2f9a"],
      },
      {
        sev: "warning",
        title: "Champion role change announced",
        body: "Karin Lundberg mentioned moving to Conduct & Operational Risk in two weeks. Sponsorship handed to Stefan Roth (CTO office). Continuity of executive support not yet confirmed.",
        evidence: ["msg-2f9a"],
      },
      {
        sev: "info",
        title: "Procurement freeze is account-wide",
        body: "The Feb 28 freeze touches seven other RFPs, not specific to this engagement. Reduces probability that the pause signals dissatisfaction.",
        evidence: ["msg-2f9a", "mtg-feb28"],
      },
    ],
    threads: [
      {
        id: "thread-brief",
        workflow: "Brief me before a call",
        title: "Brief: call with Karin tomorrow",
        sub: "Helvetica Banking AG · 11 artifacts indexed",
        messages: [
          { role: "user", text: "Brief me before my call with Karin tomorrow. Where did we leave it?" },
          {
            role: "assistant",
            blocks: [
              { kind: "p", text: "Last contact was a procurement-freeze email from Karin Lundberg on Mar 04. Three things to know going in:" },
              { kind: "ul", items: [
                "The freeze is account-wide, not specific to this engagement. Seven other RFPs are paused.",
                "Karin is rotating to Conduct & Operational Risk in two weeks. Sponsorship is being handed to Stefan Roth (CTO office).",
                "Two technical asks are still open: SOC 2-style encryption-at-rest attestation, and EU-residency clause confirmation (Frankfurt acceptable; Dublin excluded).",
              ]},
              { kind: "p", text: "Recommended posture for the call: acknowledge the freeze without pressing, confirm continuity of sponsorship plan with Stefan, and offer the encryption-at-rest deliverable as a no-cost preview to keep momentum during the pause." },
            ],
            citations: [
              { label: "Email · msg-2f9a", artifactId: "msg-2f9a" },
              { label: "Email · msg-1c44", artifactId: "msg-1c44" },
              { label: "Meeting · mtg-feb28", artifactId: "mtg-feb28" },
              { label: "Doc · doc-secpol", artifactId: "doc-secpol" },
            ],
          },
        ],
      },
    ],
  },

  // ============================================================
  // 2. NORDBAU LOGISTIK GMBH — Mid-funnel
  // ============================================================
  {
    id: "nordbau",
    name: "Nordbau Logistik GmbH",
    industry: "Logistics & Supply Chain",
    country: "Hamburg, Germany",
    status: "midfunnel",
    statusLabel: "Mid-funnel",
    context: "Buying committee forming. Operations sees value, IT wants more architecture detail. Procurement engaged but informally.",
    stats: { artifacts: 9, alerts: 2, days: 11 },
    artifacts: [
      {
        id: "n-msg-ops",
        type: "email",
        title: "Re: workflow demo — internal forwards",
        meta: "Andreas Weiss → Daniel · Mar 02",
        date: "Mar 02, 2026",
        from: "Andreas Weiss <a.weiss@nordbau-logistik.de>",
        to: "Daniel Panea <daniel@panea.dev>",
        subject: "Re: workflow demo — internal forwards",
        body: [
          "Daniel,",
          "Quick update from this side. I've shared the workflow demo with three people internally: Lukas (IT), Petra (Procurement), and Markus (Group Ops Director). Reactions:",
          "Markus is sold — he sees the dispatcher-handover workflow as the one to start with. Petra wants a fixed-fee structure, not T&M. Lukas has a long list of architecture questions and would like a 60-minute technical call before we move forward.",
          "Can we put something on the calendar for next week? I'll send three slots from Lukas's side.",
          "Best,",
          "Andreas",
        ],
      },
      {
        id: "n-msg-it",
        type: "email",
        title: "Architecture questions — pre-call",
        meta: "Lukas Bauer → Daniel · Mar 05",
        date: "Mar 05, 2026",
        from: "Lukas Bauer <l.bauer@nordbau-logistik.de>",
        to: "Daniel Panea <daniel@panea.dev>",
        subject: "Architecture questions — pre-call",
        body: [
          "Daniel,",
          "Sending these ahead of next Tuesday's call so we can use the time efficiently. In rough order of importance:",
          "1. We run on-prem (Hamburg DC) with a small Azure West Europe footprint for non-sensitive workloads. Is on-prem inference realistic for the pilot, or do you strongly recommend the EU GPU pool? Cost vs control trade-off.",
          "2. We have an in-house data lake (Iceberg on S3-compatible storage). Can your indexer read from that directly, or does it expect filesystem mounts?",
          "3. Audit log format — we feed everything into Splunk. JSON over HTTP is preferred. Is your audit log schema documented?",
          "4. Open weights — fine in principle, but our Group Compliance has an explicit blocklist of model providers. Can you confirm Llama 3.x and Mistral are on neither the EU-prohibited list nor your own opinion-of-shouldn't-use list?",
          "See you Tuesday.",
          "— Lukas",
        ],
      },
      {
        id: "n-msg-intro",
        type: "email",
        title: "Introduction — DES Madrid referral",
        meta: "Andreas Weiss → Daniel · Feb 04",
        date: "Feb 04, 2026",
        from: "Andreas Weiss <a.weiss@nordbau-logistik.de>",
        to: "Daniel Panea <daniel@panea.dev>",
        subject: "Introduction — DES Madrid referral",
        body: [
          "Daniel,",
          "Met you briefly at DES Madrid last month. We're a mid-cap logistics group, six European hubs, 1,800 employees. We have a specific workflow problem — dispatcher handover at shift change — that I think your private AI angle could solve elegantly. Open to a call?",
          "— Andreas Weiss, Head of Operations",
        ],
      },
      // Meetings
      {
        id: "n-mtg-demo",
        type: "meeting",
        title: "Workflow demo — Andreas + ops team",
        meta: "5 attendees · Feb 21",
        date: "Feb 21, 2026",
        attendees: ["Andreas Weiss (Ops)", "Markus Beier (Group Ops Dir)", "Petra Lange (Procurement)", "Sandra Holm (Dispatch lead)", "Daniel Panea"],
        duration: "67 minutes",
        transcript: [
          { who: "Sandra", ts: "00:14", text: "I'll show you what the handover binder looks like today. Twenty-six pages, hand-written in places, three of the dispatchers have their own shorthand. It takes the incoming shift forty minutes to read it before they're operational." },
          { who: "Daniel", ts: "00:48", text: "And the cost of a missed handover detail — what does that look like in your data?" },
          { who: "Sandra", ts: "01:02", text: "Last quarter, four high-severity dispatch errors traced back to handover gaps. Each one is roughly €14,000 in penalties plus operational disruption." },
          { who: "Markus", ts: "12:30", text: "What I want to know is — how do we keep the dispatchers in the loop? I don't want a system that summarises the binder and the dispatchers stop reading the binder. That's how you lose institutional knowledge." },
          { who: "Daniel", ts: "12:55", text: "Right. The framing isn't 'replace the binder.' It's 'the binder plus a copilot that points to the binder.' Citations into the underlying handover entries, not synthesis without them. Dispatchers still write the entries; the copilot makes them queryable." },
          { who: "Petra", ts: "44:20", text: "Procurement-side question. Fixed-fee or time-and-materials?" },
          { who: "Daniel", ts: "44:30", text: "Assessment is fixed-fee. Pilot is fixed-fee for the eight-week scope. Extension beyond the eval gate can be either; most clients choose fixed-fee with a defined scope per cycle." },
        ],
      },
      {
        id: "n-mtg-intro",
        type: "meeting",
        title: "Intro call — Andreas & Daniel",
        meta: "2 attendees · Feb 10",
        date: "Feb 10, 2026",
        attendees: ["Andreas Weiss (Ops)", "Daniel Panea (Panea)"],
        duration: "32 minutes",
        transcript: [
          { who: "Andreas", ts: "00:08", text: "The pitch from your side — what's the headline?" },
          { who: "Daniel", ts: "00:14", text: "Source-backed copilot over the materials your team already produces, deployed on infrastructure you control. The differentiation isn't the model — it's the data line." },
          { who: "Andreas", ts: "08:42", text: "Markus is going to ask about lock-in. I should have an answer." },
          { who: "Daniel", ts: "08:55", text: "Index, prompts, eval set, audit log — exportable on request. No multi-year contract required. The leverage we have is the engagement quality, not the contract." },
        ],
      },
      // Docs
      {
        id: "n-doc-handover",
        type: "pdf",
        title: "Dispatcher handover — sample binder",
        meta: "PDF · 26 pp · Feb 21",
        date: "Feb 21, 2026",
        pages: [
          {
            n: "001",
            title: "Hamburg Hub · Dispatcher Handover Binder",
            paras: [
              "Date: 21 February 2026. Outgoing shift: Sandra H. (lead), Tomasz R., Greta M. Incoming shift: Karim A. (lead), Frieda S., Marek W.",
              "Status at handover: 14 active dispatches in HH-east corridor, 3 vehicles awaiting cross-dock allocation, 1 pending exception on the Rostock route (see entry 14:22, page 8).",
              "Note: ferry slot at Travemünde has been pulled forward by 45 minutes — Frieda please confirm with port ops before 17:00.",
            ],
          },
          {
            n: "008",
            title: "Page 8 — Exception log",
            paras: [
              "14:22 — Rostock route. Vehicle HH-2847. Customer (KLN-Industrie) requested split delivery: 6 pallets to dock A, 4 to dock C. Driver flagged that dock C accepts only 24h-notice deliveries. Decision deferred to incoming shift.",
              "14:48 — Hamburg-Süd. Vehicle HH-2901. Driver reported tail-lift fault. Re-routed via HH-2911. No customer impact. Maintenance ticket #4471 raised.",
              "15:30 — Travemünde ferry. Port ops advised 45-minute earlier departure. Affects three dispatches (HH-2855, HH-2867, HH-2873). Outgoing shift unable to reach Frieda in time.",
            ],
          },
        ],
      },
      {
        id: "n-doc-pilot",
        type: "docx",
        title: "Pilot scope — Nordbau",
        meta: "DOCX · 5 pp · Feb 25",
        date: "Feb 25, 2026",
        bodyMarkdown: {
          title: "Pilot Scope · Nordbau Logistik GmbH",
          sections: [
            { h: "Objective", p: "Index the dispatcher handover binder corpus (Hamburg hub, 18 months of entries) and expose a private conversation surface to the dispatch leads. Citations land on the underlying binder entry." },
            { h: "Corpus", list: ["~3,200 dispatcher handover entries across 18 months", "Driver-side exception logs (linked, read-only)", "Excludes: HR records, employee performance data, customer-financial records"] },
            { h: "Models", p: "Llama 3.x-70B / Mistral Large 2; mxbai-embed-large. Hamburg DC deployment preferred; EU GPU pool fallback for burst capacity." },
            { h: "Evaluation", p: "Eval set drawn from real dispatcher questions across the last 6 months. Two gates: citation precision ≥ 92%, and dispatcher-rated usefulness ≥ 4.0 / 5.0 in week-3 review." },
          ],
        },
      },
      {
        id: "n-doc-arch",
        type: "docx",
        title: "Architecture sketch — for Lukas's call",
        meta: "DOCX · 3 pp · Mar 08",
        date: "Mar 08, 2026",
        bodyMarkdown: {
          title: "Architecture Sketch — Nordbau / IT Pre-Read",
          sections: [
            { h: "Deployment topology", p: "On-prem (Hamburg DC) preferred. Two-node inference cluster, single embedding index, audit log streamed to Splunk over JSON-HTTP. Burst capacity to Panea-managed Frankfurt pool when on-prem queue depth > threshold." },
            { h: "Data lake integration", p: "Iceberg-native indexer. Reads from Nordbau's S3-compatible storage via IAM-scoped credentials. No data copied off the lake; embeddings stored alongside Iceberg metadata in a sibling table." },
            { h: "Model selection", p: "Llama 3.x-70B (synthesis) and Mistral Large 2 (alternative) — both on the EU open-weights list. mxbai-embed-large (retrieval)." },
          ],
        },
      },
    ],
    alerts: [
      {
        sev: "warning",
        title: "Multi-stakeholder alignment risk",
        body: "Operations is convinced. IT wants depth. Procurement wants fixed-fee structure. Without explicit owner, the next 6 weeks can drift. Recommend asking Markus to name a single contracting owner.",
        evidence: ["n-msg-ops", "n-msg-it"],
      },
      {
        sev: "info",
        title: "Quantified pain — €56k / quarter",
        body: "Sandra cited four high-severity dispatch errors last quarter at ~€14k each. Strong economic anchor for the pilot conversation. Worth referencing.",
        evidence: ["n-mtg-demo"],
      },
    ],
    threads: [
      {
        id: "thread-changed",
        workflow: "What changed?",
        title: "What changed since the demo call?",
        sub: "Nordbau Logistik GmbH · 9 artifacts indexed",
        messages: [
          { role: "user", text: "What's changed in this account in the last two weeks?" },
          {
            role: "assistant",
            blocks: [
              { kind: "p", text: "Three things since the Feb 21 demo call:" },
              { kind: "ul", items: [
                "Three internal stakeholders are now in the loop: Markus (Group Ops, supportive), Petra (Procurement, wants fixed-fee), Lukas (IT, has architecture questions).",
                "A 60-minute technical pre-call is being scheduled with Lukas. He sent four pre-read questions on Mar 05 covering on-prem inference, data-lake integration, audit-log schema, and the open-weights blocklist.",
                "No movement on the contracting side yet — Andreas has not named a single contracting owner, which is the largest active risk for the next six weeks.",
              ]},
            ],
            citations: [
              { label: "Email · n-msg-ops", artifactId: "n-msg-ops" },
              { label: "Email · n-msg-it", artifactId: "n-msg-it" },
              { label: "Meeting · n-mtg-demo", artifactId: "n-mtg-demo" },
            ],
          },
        ],
      },
    ],
  },

  // ============================================================
  // 3. CRÉDIT PROVENCE — Late stage positive
  // ============================================================
  {
    id: "credit-provence",
    name: "Crédit Provence",
    industry: "Insurance & Mutual Finance",
    country: "Marseille, France",
    status: "late",
    statusLabel: "Late stage positive",
    context: "Contract redlines in flight. Legal is engaged, scope is settled, eval set drafted. Camille is pressing for kickoff before quarter-end.",
    stats: { artifacts: 10, alerts: 2, days: 4 },
    artifacts: [
      {
        id: "cp-msg-kickoff",
        type: "email",
        title: "Kickoff date — before April?",
        meta: "Camille Aubert → Daniel · Mar 09",
        date: "Mar 09, 2026",
        from: "Camille Aubert <c.aubert@credit-provence.fr>",
        to: "Daniel Panea <daniel@panea.dev>",
        subject: "Kickoff date — before April?",
        body: [
          "Daniel,",
          "Legal returned the redlined MSA Friday — three substantive comments, all on Schedule 2 (eval set ownership and the export-on-exit timeline). I've replied to all three. Margaux thinks we're 48 hours from clean execution.",
          "Can we slot kickoff before April 1? The team is ready, the eval set is drafted, and I'd rather not let the momentum slip into Q2 holidays.",
          "Best,",
          "Camille",
        ],
      },
      {
        id: "cp-msg-legal",
        type: "email",
        title: "MSA redlines — Schedule 2",
        meta: "Margaux Petit → Daniel · Mar 06",
        date: "Mar 06, 2026",
        from: "Margaux Petit <m.petit@credit-provence.fr>",
        to: "Daniel Panea <daniel@panea.dev>",
        subject: "MSA redlines — Schedule 2",
        body: [
          "Daniel,",
          "Three comments on Schedule 2, all on eval set ownership:",
          "1. §2.3 — clarify that the eval set is jointly owned, not Panea-owned. The set is composed of our questions and our judgements; we cannot accept it being treated as a Panea work product.",
          "2. §2.5 — the export-on-exit timeline of 30 days is too long. Our standard is 10 business days. Propose 15.",
          "3. §2.7 — the indemnification carve-out for 'model-generated content that paraphrases without citing' is ambiguous. Propose narrower language tied to the eval gate threshold.",
          "Otherwise the document is clean.",
          "— Margaux Petit, Senior Counsel",
        ],
      },
      {
        id: "cp-msg-eval",
        type: "email",
        title: "Eval set — first 80 questions",
        meta: "Camille Aubert → Daniel · Feb 26",
        date: "Feb 26, 2026",
        from: "Camille Aubert <c.aubert@credit-provence.fr>",
        to: "Daniel Panea <daniel@panea.dev>",
        subject: "Eval set — first 80 questions",
        body: [
          "Daniel,",
          "Attached, the first 80 questions for the eval set. Drawn from three sources: claims-handler tickets that escalated last year (40), open audit-trail review queries (25), and a sample of underwriter-side knowledge questions (15). Two of my team will review your judgements once retrieval is running.",
          "Camille",
        ],
      },
      {
        id: "cp-msg-intro",
        type: "email",
        title: "Introduction — referred by Red CIDE",
        meta: "Camille Aubert → Daniel · Jan 12",
        date: "Jan 12, 2026",
        from: "Camille Aubert <c.aubert@credit-provence.fr>",
        to: "Daniel Panea <daniel@panea.dev>",
        subject: "Introduction — referred by Red CIDE",
        body: [
          "Daniel,",
          "Red CIDE recommended your assessment process. We are a regional mutualist insurer, 380 staff, with a specific need around claims-handler decision support. Our current vendor evaluation is at the 'shortlist of two' stage, and we'd like to add a third option that takes the private-AI angle seriously.",
          "— Camille Aubert, COO",
        ],
      },
      // Meetings
      {
        id: "cp-mtg-scope",
        type: "meeting",
        title: "Scope freeze — Camille + Daniel",
        meta: "2 attendees · Feb 20",
        date: "Feb 20, 2026",
        attendees: ["Camille Aubert (COO)", "Daniel Panea"],
        duration: "44 minutes",
        transcript: [
          { who: "Camille", ts: "00:00", text: "Let's freeze the scope today. Claims-handler decision support, 8-week pilot, eval gate at 92% citation precision, audit-trail-exportable from day one." },
          { who: "Daniel", ts: "00:18", text: "Agreed. One open item from my side — the corpus. We were debating whether to include the 2019-2022 claims archive. Decision?" },
          { who: "Camille", ts: "00:34", text: "Include it. The handlers reach back that far on edge cases more often than we'd like." },
          { who: "Daniel", ts: "01:02", text: "Adds about 18% to the embedding cost. Within the fixed-fee envelope, so no contract change." },
          { who: "Camille", ts: "22:10", text: "Margaux from legal will start on the MSA next week. She's pragmatic but precise — expect comments on Schedule 2." },
        ],
      },
      {
        id: "cp-mtg-team",
        type: "meeting",
        title: "Claims team intro session",
        meta: "6 attendees · Feb 12",
        date: "Feb 12, 2026",
        attendees: ["Camille Aubert", "Yves Martin (Claims lead)", "Sophie Roux (Senior handler)", "Antoine Dubois (Underwriter rep)", "Daniel Panea"],
        duration: "58 minutes",
        transcript: [
          { who: "Yves", ts: "02:10", text: "What I want to avoid is a system that gives confident wrong answers. We've evaluated two vendors that did exactly that. The second one was confident-wrong on a coverage interpretation that would have cost us €120k if we hadn't caught it." },
          { who: "Daniel", ts: "02:34", text: "That's the eval-gate point. Citation precision is the metric, not 'helpfulness.' If the system can't tie an answer to the underlying policy clause or claim record, it shouldn't synthesize one." },
          { who: "Sophie", ts: "18:42", text: "Edge case I want to see handled — claims where the policy was amended mid-term. Coverage at the time of incident, not coverage at time of claim. That's where the other vendors fell over." },
          { who: "Daniel", ts: "19:00", text: "Temporal grounding. That's a specific eval bucket — we'll write it explicitly into the eval set." },
        ],
      },
      // Docs
      {
        id: "cp-doc-msa",
        type: "pdf",
        title: "MSA — redlined (Schedule 2)",
        meta: "PDF · 24 pp · Mar 06",
        date: "Mar 06, 2026",
        pages: [
          {
            n: "012",
            title: "Schedule 2 — Eval Set Ownership",
            paras: [
              "§2.1 The Parties acknowledge that the Eval Set, as defined in Section 4 of the Main Agreement, is a deliverable jointly developed by the Client and the Service Provider.",
              "§2.3 [redline] The Eval Set shall be jointly owned by the Client and the Service Provider, with each Party holding non-exclusive rights to use the Eval Set for the duration of the Engagement and, with respect to the Client, in perpetuity thereafter. [STRUCK: 'The Eval Set shall be a work product of the Service Provider.']",
              "§2.5 [redline] On termination of the Engagement, the Service Provider shall export the Eval Set and all related artifacts to the Client within fifteen (15) business days. [STRUCK: 'thirty (30) days']",
              "§2.7 [redline] The indemnification carve-out for model-generated content shall be limited to outputs that fall below the citation-precision threshold defined in the Eval Gate (Section 4.3 of the Main Agreement). [STRUCK: 'shall include all model-generated content that paraphrases without citing.']",
            ],
          },
        ],
      },
      {
        id: "cp-doc-pilot",
        type: "docx",
        title: "Pilot scope — final",
        meta: "DOCX · 7 pp · Feb 20",
        date: "Feb 20, 2026",
        bodyMarkdown: {
          title: "Pilot Scope · Crédit Provence · Final",
          sections: [
            { h: "Objective", p: "Claims-handler decision support over the full claims corpus (2019-present), policy library, and the underwriter-side knowledge base. Citations land on the underlying record. Confident-wrong outputs are the primary failure mode being engineered against." },
            { h: "Corpus", list: ["Claims archive 2019-2025 (~84,000 records)", "Policy library, current + 5-year archive of amendments", "Underwriter knowledge base (~2,400 entries)", "Excludes: customer PII not relevant to the claim record"] },
            { h: "Models", p: "Llama 3.x-70B (synthesis), mxbai-embed-large (retrieval). EU GPU pool, Paris-primary, Frankfurt-secondary. Camille's preference: French data residency where available." },
            { h: "Evaluation", p: "Eval set: 240 questions drawn from real handler tickets, audit-review queries, and underwriter questions. Two gates: citation precision ≥ 92%, temporal-grounding accuracy ≥ 95% on the policy-amendment subset." },
            { h: "Engagement", p: "8 weeks, fixed-fee. Weekly sync. Extension to 12 weeks contingent on eval-gate clearance. Production handover with runbook + eval set + audit-log schema." },
          ],
        },
      },
      {
        id: "cp-doc-evalset",
        type: "docx",
        title: "Eval set — first 80 questions",
        meta: "DOCX · 12 pp · Feb 26",
        date: "Feb 26, 2026",
        bodyMarkdown: {
          title: "Eval Set v0.1 — Crédit Provence (first 80)",
          sections: [
            { h: "Section A — Claims handler escalations (40 questions)", list: [
              "Q01: For claim CP-2023-44712, what was the coverage limit at the time of incident, and was there a policy amendment between policy inception and the incident date?",
              "Q02: For a claim involving a third-party liability denial in 2022, what was the precedent established in policy interpretation memo IPM-2022-09?",
              "Q03: When the handler note references 'standard exception 7,' which clause of the policy library is being invoked?",
            ]},
            { h: "Section B — Audit-trail review (25 questions)", list: [
              "Q41: Show all claims handled by Sophie Roux in Q3 2024 where the citation chain referenced a policy clause that has since been amended.",
              "Q42: What is the audit-log record for the decision on claim CP-2024-19842?",
            ]},
            { h: "Section C — Underwriter knowledge (15 questions)", list: [
              "Q66: Under what conditions does the regional mutualist guidance for coastal-property underwriting deviate from the national standard?",
            ]},
          ],
        },
      },
      {
        id: "cp-doc-secpolicy",
        type: "pdf",
        title: "Policy library — OCR sample",
        meta: "PDF · OCR · 9 pp · Feb 18",
        date: "Feb 18, 2026",
        ocr: true,
        pages: [
          {
            n: "001",
            title: "Crédit Provence — Standard Policy Library, Excerpt",
            paras: [
              "[OCR] CONTRAT-CADRE D'ASSURANCE — ANNEXE 4. The following pages reproduce sections relevant to the claims-handler decision support pilot. Original document is the French-language standard policy; the English content here is a working translation for evaluation purposes only and is not legally binding.",
              "[OCR] §4.1 Coverage at incident. For the purposes of claim adjudication, the coverage in force at the time of the insured incident shall be determined by reference to the policy schedule in effect on the date of incident, not the date of claim notification or claim adjudication.",
              "[OCR] §4.2 Amendments. Where a policy schedule has been amended between the date of policy inception and the date of incident, the schedule effective on the date of incident shall govern.",
            ],
          },
        ],
      },
    ],
    alerts: [
      {
        sev: "info",
        title: "Path to kickoff in 48 hours",
        body: "Legal redlines on Schedule 2 are tractable: §2.3 ownership, §2.5 export timeline, §2.7 indemnification scope. Camille is pressing for kickoff before April 1.",
        evidence: ["cp-msg-kickoff", "cp-msg-legal"],
      },
      {
        sev: "warning",
        title: "Q2 holiday risk",
        body: "If kickoff slips past Mar 31, the engagement runs into the French May/Whitsun holiday band. Effective week-1 onboarding compresses to 3 working days unless schedule accommodates.",
        evidence: ["cp-msg-kickoff"],
      },
    ],
    threads: [
      {
        id: "thread-followup",
        workflow: "Draft follow-up",
        title: "Reply to Camille — kickoff timing",
        sub: "Crédit Provence · 10 artifacts indexed",
        messages: [
          { role: "user", text: "Draft a reply to Camille agreeing to her kickoff timing and acknowledging Margaux's redlines." },
          {
            role: "assistant",
            blocks: [
              { kind: "p", text: "Draft below. Citations point to the source emails — confirm before sending." },
              { kind: "p", text: "Subject: Re: Kickoff date — before April?" },
              { kind: "p", text: "Camille — yes to a kickoff before April 1. Once Margaux's three Schedule 2 comments are settled (§2.3 joint ownership, §2.5 15-day export, §2.7 indemnification scope), we can sign and run a half-day kickoff the same week. I'll send three slots between Mar 24 and Mar 28." },
              { kind: "p", text: "On Margaux's points: §2.3 and §2.5 are agreed as-is. On §2.7, the eval-gate-threshold language she proposes is cleaner than ours — happy to adopt verbatim." },
              { kind: "p", text: "Looking forward. — Daniel" },
            ],
            citations: [
              { label: "Email · cp-msg-kickoff", artifactId: "cp-msg-kickoff" },
              { label: "Email · cp-msg-legal", artifactId: "cp-msg-legal" },
              { label: "Doc · cp-doc-msa", artifactId: "cp-doc-msa" },
            ],
          },
        ],
      },
    ],
  },
];

window.WORKFLOWS = [
  { id: "brief", label: "Brief me before a call", prompt: "Brief me for my next call on this account. Three things I should know going in." },
  { id: "changed", label: "What changed?", prompt: "What's changed in this account in the last two weeks?" },
  { id: "risks", label: "Open risks", prompt: "What are the open risks on this account, ranked by severity, with evidence?" },
  { id: "followup", label: "Draft follow-up", prompt: "Draft a follow-up message to the primary contact. Match the tone of prior correspondence." },
  { id: "next", label: "Next action", prompt: "What's the single highest-leverage next action I can take on this account this week?" },
];
