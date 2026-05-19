from __future__ import annotations

import textwrap
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Literal


BASE_REFERENCE_DATE = date(2026, 5, 13)
OWNER_ID = "SYN_USR_0001"
INTERNAL_ACCOUNT_ID = "SYN_ACC_INTERNAL"
INTERNAL_ACCOUNT_SLUG = "internal_company_knowledge"
INTERNAL_ACCOUNT_NAME = "Internal company knowledge"


@dataclass(frozen=True)
class ContactSpec:
    contact_id: str
    first_name: str
    last_name: str
    title: str
    role: str
    email: str
    phone: str

    @property
    def name(self) -> str:
        return f"{self.first_name} {self.last_name}"


@dataclass(frozen=True)
class EmailSpec:
    message_id: str
    sender: str
    recipients: tuple[str, ...]
    cc: tuple[str, ...]
    sent_at: datetime
    subject: str
    body: str
    in_reply_to: str | None = None
    references: tuple[str, ...] = ()


@dataclass(frozen=True)
class PdfSpec:
    filename: str
    title: str
    subtitle: str
    document_type: Literal["proposal", "nda", "product_spec", "compliance_addendum"]
    issue_date: date
    sections: tuple[tuple[str, tuple[str, ...]], ...]
    pricing_rows: tuple[tuple[str, str, str], ...] = ()
    has_text_layer: bool = True
    requires_ocr: bool = False


@dataclass(frozen=True)
class DocxSpec:
    filename: str
    title: str
    subtitle: str
    paragraphs: tuple[str, ...]
    bullets: tuple[str, ...]


@dataclass(frozen=True)
class MeetingSpec:
    filename: str
    title: str
    meeting_date: date
    attendees: tuple[str, ...]
    speakers: tuple[str, ...]
    theme: str
    risk: str
    next_action: str


@dataclass(frozen=True)
class AccountSpec:
    account_id: str
    slug: str
    name: str
    domain: str
    industry: str
    country: str
    city: str
    website: str
    phone: str
    story_arc: str
    opportunity_id: str
    opportunity_name: str
    opportunity_stage: str
    opportunity_amount: float
    opportunity_probability: float
    opportunity_close_date: date
    contacts: tuple[ContactSpec, ...]
    emails: tuple[EmailSpec, ...]
    pdfs: tuple[PdfSpec, ...]
    docx: DocxSpec
    meetings: tuple[MeetingSpec, ...]


def shift_date(value: date, reference_date: date) -> date:
    return value + (reference_date - BASE_REFERENCE_DATE)


def shift_datetime(value: datetime, reference_date: date) -> datetime:
    return value + (reference_date - BASE_REFERENCE_DATE)


def at(day: str, hour: int, minute: int = 0) -> datetime:
    return datetime.combine(date.fromisoformat(day), time(hour, minute), tzinfo=timezone.utc)


def d(day: str) -> date:
    return date.fromisoformat(day)


def _email(
    key: str,
    sender: str,
    recipients: tuple[str, ...],
    sent_at: datetime,
    subject: str,
    body: str,
    cc: tuple[str, ...] = (),
    in_reply_to: str | None = None,
    references: tuple[str, ...] = (),
) -> EmailSpec:
    return EmailSpec(
        message_id=f"<{key}@synthetic.danielpanea.com>",
        sender=sender,
        recipients=recipients,
        cc=cc,
        sent_at=sent_at,
        subject=subject,
        body=_normalise_email_body(body),
        in_reply_to=in_reply_to,
        references=references,
    )


def _normalise_email_body(body: str) -> str:
    raw = textwrap.dedent(body).strip()
    paragraphs = raw.split("\n\n")
    return "\n\n".join(
        " ".join(line.strip() for line in paragraph.splitlines() if line.strip())
        for paragraph in paragraphs
        if paragraph.strip()
    )


def _proposal_sections(account_name: str, focus: str, risk: str) -> tuple[tuple[str, tuple[str, ...]], ...]:
    return (
        (
            "Executive summary",
            (
                f"{account_name} is evaluating a focused private company memory layer for {focus}. "
                "The proposed pilot turns fragmented operational notes, CRM exports, and team documents into a cited account workspace that internal staff can query in plain language.",
                "The strategic problem is recurring: relevant context exists somewhere in the company, but the people who need it before a customer-facing decision spend more time hunting for it than acting on it. Sales, operations, and customer-facing roles each rebuild the same context multiple times a week from email threads, attachments, and CRM exports, and the resulting briefings are inconsistent because each person stops at a different point.",
                "Our recommendation is a bounded pilot with synthetic and approved business data first, followed by a measured expansion only after security review. The pilot is deliberately scoped to validate the architecture in a real environment without depending on production-grade connectors or autonomous actions, so the value can be evaluated against an honest cost.",
                "The deliverable at the end of the pilot is a working demo on customer-controlled infrastructure, an evidence pack documenting retrieval quality and citation behaviour, and a rollout recommendation that names the next two or three concrete workflows that would justify a broader engagement.",
            ),
        ),
        (
            "Scope of work",
            (
                "The pilot configures ingestion for email archives, CRM exports, meeting notes, PDFs, and Word documents. Each artifact is parsed into raw extracted text, then normalised into AI-ready account memory documents with full source citations and retrieval metadata. The raw-artifact inventory remains visible behind every answer so internal reviewers can audit any claim.",
                "Retrieval is hybrid: full-text search and dense embeddings are merged with reciprocal rank fusion, and an intent classifier picks the document types most likely to answer a given question. The classifier is conservative by design; when it cannot resolve which account a question refers to, the system asks rather than guessing.",
                "Answer generation runs through a strict citation contract. Every substantive paragraph or bullet is paired with an exact source label that points back to the underlying artifact, and the system retries when the model produces unsupported claims. Operators can inspect both the cited and the rejected attempts in the evidence pack.",
                "Guided workflows are wired up for call briefing, recent-change review, open-risk surfacing, next-action recommendation, and follow-up drafting. These are entry points, not closed paths: every workflow opens a thread the user can extend with free-text follow-ups against the same retrieval context.",
            ),
        ),
        (
            "Risk and dependency notes",
            (
                risk,
                "Any production deployment would require customer-owned credentials, access review, logging policies, and a jointly approved retention policy. The pilot intentionally avoids touching production data so this approval can take its normal cadence without blocking the architecture review.",
                "Two dependencies sit on the customer side and are worth flagging early. First, the source inventory needs at least one owner per artifact category — without that, the ingestion gets stuck on permission questions rather than on technical ones. Second, the evaluation framing must be agreed up front: a pilot that ends without a clear bar for success or failure tends to be relitigated rather than concluded.",
                "On the architecture side, the main risk is over-broadening scope. The system intentionally does not orchestrate autonomous actions in the pilot; it produces cited briefings and drafts that a human approves. Where customer stakeholders ask for autonomous behaviour, that conversation is staged as a follow-on engagement with its own evaluation plan.",
            ),
        ),
        (
            "Timeline",
            (
                "Week 1 focuses on source inventory, access review, and success criteria. The goal is to leave the week with a shared list of artifact categories, named owners, and a written definition of what \"good\" looks like for the chosen workflows. No code change is more important than this alignment.",
                "Week 2 builds the ingestion prototype and runs the first retrieval evaluation. Sample questions are drawn from the customer's actual workflows, and the evaluation captures retrieval quality, answer quality, and any citation failures, with the underlying retrieved context preserved for review.",
                "Week 3 enables the guided workflows, hardens citation validation, and runs a stakeholder review with operations, IT, and any compliance contacts. The output is a working environment that internal reviewers can use, plus a written readout of the open issues and their mitigations.",
                "Week 4 closes the pilot with a readout and a rollout recommendation. The recommendation explicitly names which next workflows would benefit, which integrations would have to be built, and which questions would still need to be answered before broader rollout. We treat \"do not roll out\" as an honest possible outcome.",
            ),
        ),
    )


def _nda_sections(account_name: str) -> tuple[tuple[str, tuple[str, ...]], ...]:
    return (
        (
            "Parties and purpose",
            (
                f"This mutual non-disclosure agreement is entered into between Daniel Panea Lichtig (\"the Architect\") and {account_name} (\"the Customer\") for the purpose of evaluating a private company memory layer reference architecture and any related professional services engagement.",
                "The agreement governs information exchanged between the parties from the effective date until two years after the last exchange, or until superseded by a signed services agreement that includes its own confidentiality terms.",
            ),
        ),
        (
            "Confidential information",
            (
                f"Each party may disclose business, technical, operational, and commercial information related to the {account_name} evaluation. This includes proposals, architecture documents, deployment diagrams, retrieval and evaluation results, financial estimates, pilot timelines, and any data the Customer chooses to share as part of the evaluation.",
                "Confidential information excludes material already known to the receiving party at the time of disclosure, independently developed without reference to the disclosed information, publicly available without breach of this agreement, or lawfully received from another source without confidentiality obligations.",
                "Marking is not required for information to be confidential, but parties should label particularly sensitive material so reviewers can apply the appropriate handling. Where the same information could reasonably be considered either business-sensitive or commercially neutral, the parties default to treating it as confidential.",
            ),
        ),
        (
            "Permitted use",
            (
                "The receiving party may use confidential information only to evaluate a potential pilot and related professional services, and may not use it for any other purpose, including product development unrelated to the evaluation, marketing, or competitive analysis.",
                "Access must be limited to personnel and advisers who need the information for the evaluation and who are bound by comparable confidentiality obligations through employment, contract, or professional duty. Each party is responsible for the acts and omissions of its personnel and advisers.",
                "Neither party acquires any licence, ownership, or other right in the other party's intellectual property by virtue of disclosure under this agreement. Any rights to derivative work product produced during a pilot will be set out in a separate services agreement.",
            ),
        ),
        (
            "Data handling",
            (
                "No production customer data is required for the reference demo. Any later pilot will use a jointly approved data handling plan that specifies the categories of source artifacts, the retention period, the deletion process, and the named points of contact on each side.",
                "Security documentation, deployment diagrams, retrieval logs, and audit evidence may be shared under this agreement. Where logs contain personal data, both parties agree to apply the minimum necessary disclosure and to redact identifiers that are not relevant to the evaluation.",
                "If either party becomes aware of an actual or suspected unauthorised disclosure of confidential information, that party will notify the other without undue delay and cooperate in good faith on the remediation steps.",
            ),
        ),
        (
            "Term and signatures",
            (
                "This agreement takes effect on the date of last signature and remains in force for two years from the most recent exchange of confidential information unless extended in writing or superseded by a services agreement.",
                "Signed for Daniel Panea Lichtig: Daniel Panea Lichtig, Principal Architect.",
                f"Signed for {account_name}: Authorised business representative.",
            ),
        ),
    )


def build_accounts(reference_date: date) -> list[AccountSpec]:
    brannfeld_contacts = (
        ContactSpec("SYN_CON_0001", "Stefan", "Moeller", "Operations Director", "Operations", "stefan.moeller@brannfeld-industrial.de", "+49 89 5550 101"),
        ContactSpec("SYN_CON_0002", "Lukas", "Wagner", "IT Lead", "IT", "lukas.wagner@brannfeld-industrial.de", "+49 89 5550 102"),
        ContactSpec("SYN_CON_0003", "Mara", "Klein", "Procurement Manager", "Procurement", "mara.klein@brannfeld-industrial.de", "+49 89 5550 103"),
        ContactSpec("SYN_CON_0004", "Hanna", "Reuter", "COO", "Executive", "hanna.reuter@brannfeld-industrial.de", "+49 89 5550 104"),
    )
    rynvoss_contacts = (
        ContactSpec("SYN_CON_0005", "Niels", "Koster", "Head of Operations", "Operations", "niels.koster@rynvoss-logistics.nl", "+31 10 555 2101"),
        ContactSpec("SYN_CON_0006", "Femke", "de Vries", "Finance Director", "Finance", "femke.devries@rynvoss-logistics.nl", "+31 10 555 2102"),
        ContactSpec("SYN_CON_0007", "Joris", "Bakker", "IT Manager", "IT", "joris.bakker@rynvoss-logistics.nl", "+31 10 555 2103"),
    )
    caldrisa_contacts = (
        ContactSpec("SYN_CON_0008", "Isabel", "Navarro", "Clinical Director", "Clinical Operations", "isabel.navarro@caldrisa-dental.es", "+34 91 555 3101"),
        ContactSpec("SYN_CON_0009", "Clara", "Ramos", "Compliance Officer", "Compliance", "clara.ramos@caldrisa-dental.es", "+34 91 555 3102"),
        ContactSpec("SYN_CON_0010", "Mateo", "Soler", "IT Director", "IT", "mateo.soler@caldrisa-dental.es", "+34 91 555 3103"),
        ContactSpec("SYN_CON_0011", "Elena", "Cortes", "CFO", "Finance", "elena.cortes@caldrisa-dental.es", "+34 91 555 3104"),
    )

    brannfeld_emails = (
        _email(
            "brannfeld-001",
            "daniel@danielpanea.com",
            ("stefan.moeller@brannfeld-industrial.de",),
            at("2026-04-08", 9, 20),
            "Workflow automation pilot for Brannfeld",
            """
            Stefan, thanks for the short conversation after the Munich operations forum.
            The pattern you described is exactly where a private company memory layer helps:
            maintenance notes, shift handovers, supplier emails, and CRM context all exist, but
            no one has a reliable view before a production-line decision. I suggest a narrow
            first discussion around one packaging line and the surrounding vendor workflow.
            The output would be a cited briefing rather than an autonomous decision system.
            If useful, I can bring a small synthetic example so your team can inspect how raw
            source artifacts stay visible behind each answer.
            """,
        ),
        _email(
            "brannfeld-002",
            "stefan.moeller@brannfeld-industrial.de",
            ("daniel@danielpanea.com",),
            at("2026-04-09", 14, 5),
            "Re: Workflow automation pilot for Brannfeld",
            """
            Daniel, this is timely. We lose too much time rebuilding context before weekly
            production reviews, especially when procurement questions and engineering notes are
            scattered. I want Lukas from IT involved early because he will ask about EU hosting,
            audit logs, and whether any inference leaves Germany. If you can keep the first demo
            practical and tied to one line, I think we can get a useful conversation going.
            Please suggest two times next week and include a short description I can forward to
            Hanna, our COO.
            """,
            in_reply_to="<brannfeld-001@synthetic.danielpanea.com>",
            references=("<brannfeld-001@synthetic.danielpanea.com>",),
        ),
        _email(
            "brannfeld-003",
            "stefan.moeller@brannfeld-industrial.de",
            ("hanna.reuter@brannfeld-industrial.de", "lukas.wagner@brannfeld-industrial.de"),
            at("2026-04-10", 8, 45),
            "Fwd: Private memory layer discussion",
            """
            Forwarding Daniel's note. My read is that this could reduce the manual preparation
            we do before production exception meetings. I am not asking for a purchase decision;
            I want us to understand whether the architecture is credible and whether IT can live
            with the deployment model. Lukas, please pressure-test the data residency claims.
            Hanna, the practical angle is that shift handovers and supplier issues would become
            searchable with citations, so managers stop relying on someone remembering the right
            email thread.

            Forwarded message follows with Daniel's proposed agenda and a synthetic artifact demo.
            """,
        ),
        _email(
            "brannfeld-004",
            "lukas.wagner@brannfeld-industrial.de",
            ("daniel@danielpanea.com",),
            at("2026-04-22", 16, 10),
            "Security questions before proposal",
            """
            Daniel, before Stefan pushes this further, I need clarity on three points. First,
            can inference run inside an EU-controlled environment, and can we disable any generic
            model training use? Second, what audit evidence exists for retrieval decisions and
            generated answers? Third, how would secrets and source connectors be isolated if this
            ever touched production data? The demo was useful, but we cannot evaluate pricing until
            those questions are answered in writing. Please treat this as an open blocker from IT.
            """,
        ),
        _email(
            "brannfeld-005",
            "daniel@danielpanea.com",
            ("lukas.wagner@brannfeld-industrial.de", "stefan.moeller@brannfeld-industrial.de"),
            at("2026-04-23", 10, 30),
            "Re: Security questions before proposal",
            """
            Lukas, understood. I will send a short audit posture summary by Friday. The reference
            architecture has two deployment modes: a hosted API path for the public demo and a
            sovereign path where inference is exposed through an OpenAI-compatible endpoint inside
            customer-controlled infrastructure. Retrieval logs can capture document ids, source
            citations, and validation failures without logging full prompts at INFO level. For a
            Brannfeld pilot, I would recommend starting with approved synthetic or redacted data
            until your security review is complete.
            """,
            in_reply_to="<brannfeld-004@synthetic.danielpanea.com>",
            references=("<brannfeld-004@synthetic.danielpanea.com>",),
        ),
        _email(
            "brannfeld-006",
            "daniel@danielpanea.com",
            ("stefan.moeller@brannfeld-industrial.de", "hanna.reuter@brannfeld-industrial.de"),
            at("2026-04-29", 12, 15),
            "Proposal attached: production-line workflow automation",
            """
            Stefan and Hanna, attached is the proposal for a four-week pilot around production-line
            workflow automation. The commercial scope is EUR 85,000 and assumes one bounded source
            set, cited answers, and a final architecture review. I have kept the production scope
            deliberately narrow: no autonomous actions, no direct write-back, and no broad connector
            rollout. Lukas's security questions remain tracked as a dependency, and the proposal
            separates the public-demo pattern from the deployment posture Brannfeld would require.
            """,
        ),
        _email(
            "brannfeld-007",
            "mara.klein@brannfeld-industrial.de",
            ("daniel@danielpanea.com",),
            at("2026-05-05", 9, 50),
            "Procurement review: pilot proposal",
            """
            Daniel, Procurement has started reviewing the pilot proposal. The price is within the
            range Stefan mentioned, but I need confirmation on payment milestones, cancellation
            terms, and whether travel expenses are included. We also need the signed NDA copy for
            our supplier folder. Please send a clean commercial summary that separates optional
            production work from the four-week pilot. Until that is clear, I cannot move the file
            to final approval.
            """,
        ),
        _email(
            "brannfeld-008",
            "stefan.moeller@brannfeld-industrial.de",
            ("daniel@danielpanea.com",),
            at("2026-05-09", 15, 35),
            "Re: Proposal attached: production-line workflow automation",
            """
            Daniel, the proposal reads well and Hanna liked that it stays tied to a concrete line
            instead of becoming a broad platform discussion. Lukas still wants the written audit
            posture note before he is comfortable, and Mara is waiting on procurement terms. If you
            can send both early next week, I think we can keep the decision meeting on the calendar.
            This looks promising from Operations; the only real blockers are security evidence and
            procurement packaging.
            """,
            in_reply_to="<brannfeld-006@synthetic.danielpanea.com>",
            references=("<brannfeld-006@synthetic.danielpanea.com>",),
        ),
    )

    rynvoss_emails = (
        _email(
            "rynvoss-001",
            "daniel@danielpanea.com",
            ("niels.koster@rynvoss-logistics.nl",),
            at("2026-03-25", 10, 0),
            "Routing optimization memory layer",
            """
            Niels, following up on your note about cross-border shipment exceptions. A private
            memory layer can help your planners see why a route changed, which customer exceptions
            apply, and what finance has already approved. The useful first slice is not a route
            optimizer by itself; it is a cited briefing layer over the messy operational context
            that planners currently reconstruct manually. I can show this with synthetic freight
            artifacts before any Rynvoss data is involved.
            """,
        ),
        _email(
            "rynvoss-002",
            "niels.koster@rynvoss-logistics.nl",
            ("daniel@danielpanea.com", "joris.bakker@rynvoss-logistics.nl"),
            at("2026-03-27", 13, 15),
            "Re: Routing optimization memory layer",
            """
            Daniel, yes, let's explore it. We have too many exceptions living in mailboxes and
            spreadsheets, especially for Germany-Benelux lanes. Joris will want to understand the
            integration surface, and I want Finance involved because accessorial charges are a
            constant source of rework. Please keep the first call practical. If the system can
            explain why a shipment should take a different route and cite the underlying notes,
            it will get attention here.
            """,
            in_reply_to="<rynvoss-001@synthetic.danielpanea.com>",
            references=("<rynvoss-001@synthetic.danielpanea.com>",),
        ),
        _email(
            "rynvoss-003",
            "niels.koster@rynvoss-logistics.nl",
            ("femke.devries@rynvoss-logistics.nl",),
            at("2026-04-01", 8, 20),
            "Fwd: AI memory pilot for routing context",
            """
            Femke, forwarding this because the finance angle matters. Daniel is not pitching a
            black-box optimizer; the first version would summarize routing context and cite the
            underlying notes. That might reduce disputes over detention, fuel adjustments, and
            manual exception approvals. I would like you on the procurement call if we reach that
            point. The main question for you is whether the EUR 52,000 pilot can be justified
            against avoided rework in the Rotterdam desk.
            """,
        ),
        _email(
            "rynvoss-004",
            "daniel@danielpanea.com",
            ("niels.koster@rynvoss-logistics.nl", "femke.devries@rynvoss-logistics.nl"),
            at("2026-04-08", 17, 40),
            "Proposal: cross-border shipment routing optimization",
            """
            Niels and Femke, attached is the four-week proposal for a cited routing-context pilot.
            The scope covers CRM exports, planner notes, meeting transcripts, and selected PDF
            policies. It does not include a production-grade optimizer, autonomous dispatching, or
            customer-facing workflow changes. The commercial amount is EUR 52,000. The strongest
            success metric would be reduced planner preparation time and fewer finance escalations
            for exceptions on cross-border lanes.
            """,
        ),
        _email(
            "rynvoss-005",
            "femke.devries@rynvoss-logistics.nl",
            ("daniel@danielpanea.com",),
            at("2026-04-17", 11, 25),
            "Procurement question on proposal",
            """
            Daniel, I am reviewing the proposal with Procurement. Can you confirm whether the pilot
            fee includes the connector work for our exported shipment spreadsheets, and whether
            the second payment milestone depends on a measurable reduction in planner preparation
            time? The document mentions success criteria, but not a commercial consequence if the
            pilot misses them. Please clarify this before next Wednesday, otherwise we may need to
            push the close date. This is currently the open item on our side.
            """,
        ),
        _email(
            "rynvoss-006",
            "joris.bakker@rynvoss-logistics.nl",
            ("niels.koster@rynvoss-logistics.nl", "femke.devries@rynvoss-logistics.nl"),
            at("2026-04-21", 15, 5),
            "No update from vendor yet",
            """
            Niels and Femke, I do not see a response to Femke's procurement question. From IT's
            side the pilot is still feasible, but the timeline is getting unrealistic if the close
            date remains next week. I suggest we wait for Daniel's answer before scheduling another
            technical review. The use case is interesting, but I do not want the team to rush into
            a pilot with unclear acceptance terms or spreadsheet connector assumptions.
            """,
            in_reply_to="<rynvoss-005@synthetic.danielpanea.com>",
            references=("<rynvoss-005@synthetic.danielpanea.com>",),
        ),
    )

    caldrisa_emails = (
        _email(
            "caldrisa-001",
            "daniel@danielpanea.com",
            ("isabel.navarro@caldrisa-dental.es",),
            at("2026-04-14", 9, 10),
            "Patient-flow analytics pilot",
            """
            Isabel, thank you for outlining the clinic coordination problem. A private memory layer
            can help regional leads understand appointment bottlenecks, referral context, and open
            follow-ups without exposing patient-level details in the demo. I suggest we frame the
            first pilot around operational notes, de-identified schedules, and compliance-approved
            summaries. The output would be a cited briefing for clinical operations, not a clinical
            decision system.
            """,
        ),
        _email(
            "caldrisa-002",
            "isabel.navarro@caldrisa-dental.es",
            ("daniel@danielpanea.com", "clara.ramos@caldrisa-dental.es"),
            at("2026-04-15", 16, 30),
            "Re: Patient-flow analytics pilot",
            """
            Daniel, this is very relevant. Our Madrid and Valencia clinics are sharing operational
            lessons, but the context is buried in meeting notes and manager emails. Clara will need
            comfort on GDPR and healthcare data handling before we use anything real. If we can
            start with de-identified operational artifacts and still show useful answers with
            citations, I think the clinical team will support a pilot proposal.
            """,
            in_reply_to="<caldrisa-001@synthetic.danielpanea.com>",
            references=("<caldrisa-001@synthetic.danielpanea.com>",),
        ),
        _email(
            "caldrisa-003",
            "clara.ramos@caldrisa-dental.es",
            ("daniel@danielpanea.com",),
            at("2026-04-24", 10, 45),
            "Compliance questions for healthcare pilot",
            """
            Daniel, before we proceed, please document how the pilot avoids patient-level data,
            how access to operational notes is scoped, and how generated answers retain source
            citations. I also need the retention period and deletion process for any de-identified
            source files. We can approve a narrow operational pilot, but only if it is explicit
            that the system does not make clinical recommendations or process unnecessary health
            data.
            """,
        ),
        _email(
            "caldrisa-004",
            "daniel@danielpanea.com",
            ("clara.ramos@caldrisa-dental.es", "isabel.navarro@caldrisa-dental.es"),
            at("2026-04-28", 15, 0),
            "Compliance memo and retention approach",
            """
            Clara and Isabel, I have attached the compliance memo. The recommended pilot uses
            de-identified operational artifacts, excludes patient-level clinical records, keeps
            source citations visible, and treats every generated answer as operational support.
            Retention is limited to the pilot window unless Caldrisa approves an extension. The
            architecture supports deletion by source artifact and re-indexing so removed material
            no longer appears in retrieved context.
            """,
            in_reply_to="<caldrisa-003@synthetic.danielpanea.com>",
            references=("<caldrisa-003@synthetic.danielpanea.com>",),
        ),
        _email(
            "caldrisa-005",
            "clara.ramos@caldrisa-dental.es",
            ("daniel@danielpanea.com", "isabel.navarro@caldrisa-dental.es"),
            at("2026-05-04", 11, 15),
            "Compliance review resolved",
            """
            Daniel, the memo resolves my main concern for the pilot phase. Please keep the wording
            that the system is operational support and not clinical decision support. I am also
            comfortable with the proposed deletion process for de-identified source files. From
            Compliance, the next step can be a pilot proposal as long as Mateo has reviewed the
            access controls and Elena sees the commercial scope.
            """,
        ),
        _email(
            "caldrisa-006",
            "isabel.navarro@caldrisa-dental.es",
            ("daniel@danielpanea.com",),
            at("2026-05-08", 18, 5),
            "This looks great for the pilot",
            """
            Daniel, the product specification and compliance memo landed well with the clinical
            leads. This looks great, and I would like to move forward with a pilot proposal for
            patient-flow analytics. Please include the Madrid and Valencia clinic managers in the
            first workshop and make the success metric practical: fewer missed follow-ups after
            complex appointments and faster preparation for regional operations calls.
            """,
        ),
        _email(
            "caldrisa-007",
            "elena.cortes@caldrisa-dental.es",
            ("daniel@danielpanea.com", "isabel.navarro@caldrisa-dental.es"),
            at("2026-05-11", 12, 40),
            "Pilot proposal timing",
            """
            Daniel, Isabel briefed me on the clinical value and Clara confirmed that the compliance
            objections are resolved for a narrow pilot. Please send the EUR 34,000 proposal this
            week with clear milestones and no production-grade integration language. If the scope
            stays focused on de-identified operational context, Finance should be able to review it
            quickly. I would also like a short note on what would remain out of scope for any public
            reference architecture.
            """,
        ),
    )

    accounts = [
        AccountSpec(
            account_id="SYN_ACC_0001",
            slug="brannfeld_industrial",
            name="Brannfeld Industrial GmbH",
            domain="brannfeld-industrial.de",
            industry="Industrial automation / manufacturing",
            country="Germany",
            city="Munich",
            website="https://brannfeld-industrial.example",
            phone="+49 89 5550 100",
            story_arc="Mid-funnel deal with positive Operations support and unresolved security plus procurement blockers.",
            opportunity_id="SYN_OPP_0001",
            opportunity_name="Production-line workflow automation",
            opportunity_stage="Proposal sent",
            opportunity_amount=85000.0,
            opportunity_probability=0.55,
            opportunity_close_date=shift_date(d("2026-06-12"), reference_date),
            contacts=brannfeld_contacts,
            emails=tuple(_shift_email(email, reference_date) for email in brannfeld_emails),
            pdfs=(
                PdfSpec(
                    "proposal_2026_q2.pdf",
                    "Production-line workflow automation",
                    "Four-week cited memory pilot",
                    "proposal",
                    shift_date(d("2026-04-29"), reference_date),
                    _proposal_sections(
                        "Brannfeld Industrial GmbH",
                        "production-line workflow automation",
                        "EU hosting and audit posture are explicit dependencies before production data is introduced.",
                    ),
                    (("Pilot implementation", "4 weeks", "EUR 85,000"), ("Optional production readiness", "Scoped later", "Not included")),
                ),
                PdfSpec(
                    "signed_nda_scanned.pdf",
                    "Mutual non-disclosure agreement",
                    "Signed evaluation copy",
                    "nda",
                    shift_date(d("2026-04-16"), reference_date),
                    _nda_sections("Brannfeld Industrial GmbH"),
                    has_text_layer=False,
                    requires_ocr=True,
                ),
            ),
            docx=DocxSpec(
                "account_plan.docx",
                "Brannfeld Industrial account plan",
                "Internal handover notes",
                (
                    "Operations is the champion function. Stefan sees clear value in reducing manual context gathering before production exception meetings.",
                    "IT is not blocking the concept, but Lukas needs written evidence on EU inference, audit logs, and source isolation before he supports approval.",
                    "Procurement is active and waiting for commercial packaging details rather than broad architecture language.",
                ),
                (
                    "Send audit posture summary and procurement terms before the next decision meeting.",
                    "Keep pilot scope tied to one production line and approved source sets.",
                    "Do not imply autonomous control of production workflows.",
                ),
            ),
            meetings=(
                _meeting("meeting_2026_04_15_intro.md", "Brannfeld intro", d("2026-04-15"), brannfeld_contacts, "production review preparation", "Operations wants value, IT wants EU-hosting proof.", "Daniel will send a concise architecture note after the technical deep-dive.", reference_date),
                _meeting("meeting_2026_04_28_technical.md", "Brannfeld technical deep-dive", d("2026-04-28"), brannfeld_contacts, "data residency and audit posture", "Lukas states that anything touching production data must stay inside Germany.", "Daniel will send the audit posture summary by end of week.", reference_date),
                _meeting("meeting_2026_05_02_stakeholder.md", "Brannfeld stakeholder review", d("2026-05-02"), brannfeld_contacts, "proposal review and approval path", "Procurement needs clearer commercial terms before final routing.", "Mara will collect procurement questions and Daniel will answer them in writing.", reference_date),
            ),
        ),
        AccountSpec(
            account_id="SYN_ACC_0002",
            slug="rynvoss_logistics",
            name="Rynvoss Logistics BV",
            domain="rynvoss-logistics.nl",
            industry="Logistics / freight",
            country="Netherlands",
            city="Rotterdam",
            website="https://rynvoss-logistics.example",
            phone="+31 10 555 2100",
            story_arc="Stalled account after a procurement question went unanswered.",
            opportunity_id="SYN_OPP_0002",
            opportunity_name="Cross-border shipment routing optimization",
            opportunity_stage="Negotiation",
            opportunity_amount=52000.0,
            opportunity_probability=0.4,
            opportunity_close_date=shift_date(d("2026-05-23"), reference_date),
            contacts=rynvoss_contacts,
            emails=tuple(_shift_email(email, reference_date) for email in rynvoss_emails),
            pdfs=(
                PdfSpec(
                    "proposal_2026_q2.pdf",
                    "Cross-border shipment routing optimization",
                    "Cited routing-context pilot",
                    "proposal",
                    shift_date(d("2026-04-08"), reference_date),
                    _proposal_sections(
                        "Rynvoss Logistics BV",
                        "cross-border routing context",
                        "The open commercial dependency is whether spreadsheet connector work and success metrics affect payment milestones.",
                    ),
                    (("Pilot implementation", "4 weeks", "EUR 52,000"), ("Autonomous dispatching", "Out of scope", "Not included")),
                ),
                PdfSpec(
                    "mutual_nda.pdf",
                    "Mutual non-disclosure agreement",
                    "Clean executed copy",
                    "nda",
                    shift_date(d("2026-04-03"), reference_date),
                    _nda_sections("Rynvoss Logistics BV"),
                ),
            ),
            docx=DocxSpec(
                "account_plan.docx",
                "Rynvoss Logistics account plan",
                "Internal stalled-account review",
                (
                    "The account showed strong early interest, especially from Operations, but momentum has stopped after Finance asked a procurement question.",
                    "The close date is too near for the current engagement level. Treat the opportunity as at risk unless the procurement question is answered immediately.",
                    "IT is neutral-positive but does not want to schedule more review time until the commercial ambiguity is resolved.",
                ),
                (
                    "Answer Femke's milestone and connector question before any next meeting.",
                    "Ask Niels whether the close date should move rather than pretending negotiation is active.",
                    "Prepare a short recovery note focused on planner time savings.",
                ),
            ),
            meetings=(
                _meeting("meeting_2026_03_31_intro.md", "Rynvoss intro", d("2026-03-31"), rynvoss_contacts, "routing exception context", "Finance needs a measurable link between reduced rework and pilot value.", "Daniel will send a narrow proposal with success criteria.", reference_date),
                _meeting("meeting_2026_04_17_procurement.md", "Rynvoss procurement question call", d("2026-04-17"), rynvoss_contacts, "payment milestones and connector assumptions", "Femke says the close date may move if the commercial question is not answered.", "Daniel needs to clarify spreadsheet connector scope before Wednesday.", reference_date),
            ),
        ),
        AccountSpec(
            account_id="SYN_ACC_0003",
            slug="caldrisa_dental",
            name="Caldrisa Dental Group",
            domain="caldrisa-dental.es",
            industry="Healthcare / dental clinic chain",
            country="Spain",
            city="Madrid",
            website="https://caldrisa-dental.example",
            phone="+34 91 555 3100",
            story_arc="Late-stage positive momentum with compliance resolved and a pilot proposal requested.",
            opportunity_id="SYN_OPP_0003",
            opportunity_name="Patient-flow analytics pilot",
            opportunity_stage="Proposal preparation",
            opportunity_amount=34000.0,
            opportunity_probability=0.7,
            opportunity_close_date=shift_date(d("2026-06-27"), reference_date),
            contacts=caldrisa_contacts,
            emails=tuple(_shift_email(email, reference_date) for email in caldrisa_emails),
            pdfs=(
                PdfSpec(
                    "product_specification.pdf",
                    "Patient-flow analytics pilot",
                    "Product specification for operational support",
                    "product_spec",
                    shift_date(d("2026-05-02"), reference_date),
                    _proposal_sections(
                        "Caldrisa Dental Group",
                        "patient-flow analytics using de-identified operational context",
                        "The product is explicitly not clinical decision support and excludes patient-level records from the pilot.",
                    ),
                    (("Pilot implementation", "3 weeks", "EUR 34,000"), ("Production EHR integration", "Out of scope", "Not included")),
                ),
                PdfSpec(
                    "data_processing_addendum.pdf",
                    "Pilot data processing addendum",
                    "De-identified operational-data handling",
                    "compliance_addendum",
                    shift_date(d("2026-05-04"), reference_date),
                    (
                        (
                            "Purpose",
                            (
                                "The pilot processes de-identified operational notes, schedules, and meeting transcripts to improve the briefings clinical operations leads prepare before regional reviews. The intended use is to summarise workflow context, surface open follow-ups, and link claims back to specific source artifacts.",
                                "The pilot is explicitly framed as operational support. It is not a clinical decision support tool and does not produce diagnoses, treatment plans, or any recommendation that would substitute for clinical judgement. Clinical staff retain full authority and accountability for clinical decisions.",
                                "This addendum sits alongside the pilot proposal and applies for the duration of the evaluation. Any decision to move beyond the pilot will be governed by a separate services agreement and a new data processing addendum scoped to the production use case.",
                            ),
                        ),
                        (
                            "Excluded data",
                            (
                                "Patient-level clinical records, diagnostics, treatment plans, and any direct identifiers (full name, national identifier, contact details, date of birth, address) are out of scope for the pilot.",
                                "Where operational notes incidentally reference patient information, those notes are excluded from ingestion at the source. Where exclusion is impractical at the source, the relevant fields are redacted before the artifact enters the raw store. Redaction is performed by Caldrisa-named personnel using an agreed redaction guide.",
                                "Free-text fields that may contain incidental personal data are subject to spot-check audits during the pilot. Any artifact found to contain in-scope-excluded data is removed from the raw store, the embedding index is rebuilt, and a short note is added to the pilot evidence pack documenting the removal.",
                            ),
                        ),
                        (
                            "Retention",
                            (
                                "Pilot source files are retained only for the evaluation period and for up to thirty days after the pilot ends to allow the joint readout, unless Caldrisa explicitly approves a written extension. After this window, the raw store and the derived retrieval index are deleted.",
                                "Retention applies equally to raw artifacts, derived AI-ready documents, embedding vectors, and any cached evaluation outputs. Log files used for operations and audit are kept for the same window unless a longer retention is required to investigate an incident.",
                            ),
                        ),
                        (
                            "Deletion",
                            (
                                "Deleted source artifacts are removed from the raw store and the retrieval index is rebuilt so the removed content is no longer surfaced in retrieved context. Deletion requests can be submitted by Caldrisa's named compliance contact and are acknowledged within five business days.",
                                "End-of-pilot deletion is performed by the Architect, witnessed by Caldrisa's compliance contact, and confirmed in writing. A short deletion report is added to the evidence pack and shared with both parties.",
                                "If a request to delete a specific artifact arrives during the pilot, that artifact is removed within five business days, with the index rebuild completed in the same window. Where retrieval has already produced an answer that cited the removed artifact, that answer is annotated so reviewers understand the source is no longer available.",
                            ),
                        ),
                    ),
                ),
            ),
            docx=DocxSpec(
                "compliance_memo.docx",
                "Caldrisa Dental compliance memo",
                "Operational pilot controls",
                (
                    "Compliance review is resolved for a narrow operational pilot using de-identified clinic coordination artifacts.",
                    "Generated answers must show source citations and must not be presented as clinical recommendations.",
                    "The pilot should make deletion and retention behavior visible enough for Compliance to explain internally.",
                ),
                (
                    "Keep patient-level records out of scope.",
                    "Use access-controlled operational summaries and de-identified schedules only.",
                    "Include a Finance-ready milestone plan in the proposal.",
                ),
            ),
            meetings=(
                _meeting("meeting_2026_04_18_clinical.md", "Caldrisa clinical discovery", d("2026-04-18"), caldrisa_contacts, "clinic workflow and follow-up gaps", "Clinical leads need proof that the tool improves operational handoffs without clinical advice.", "Isabel will collect two de-identified workflow examples.", reference_date),
                _meeting("meeting_2026_04_29_compliance.md", "Caldrisa compliance review", d("2026-04-29"), caldrisa_contacts, "GDPR and healthcare data controls", "Clara requires clear exclusion of patient-level records and a deletion process.", "Daniel will revise the memo and keep operational-support wording.", reference_date),
                _meeting("meeting_2026_05_07_pilot_scope.md", "Caldrisa pilot scope", d("2026-05-07"), caldrisa_contacts, "pilot proposal readiness", "Finance needs milestones but no production integration language.", "Daniel will send the pilot proposal this week.", reference_date),
            ),
        ),
    ]
    return accounts


def _shift_email(email: EmailSpec, reference_date: date) -> EmailSpec:
    return EmailSpec(
        message_id=email.message_id,
        sender=email.sender,
        recipients=email.recipients,
        cc=email.cc,
        sent_at=shift_datetime(email.sent_at, reference_date),
        subject=email.subject,
        body=email.body,
        in_reply_to=email.in_reply_to,
        references=email.references,
    )


def _meeting(
    filename: str,
    title: str,
    meeting_date: date,
    contacts: tuple[ContactSpec, ...],
    theme: str,
    risk: str,
    next_action: str,
    reference_date: date,
) -> MeetingSpec:
    speakers = ("Daniel", contacts[0].first_name, contacts[-1].first_name)
    return MeetingSpec(
        filename=filename,
        title=title,
        meeting_date=shift_date(meeting_date, reference_date),
        attendees=tuple([f"{contact.name} ({contact.title})" for contact in contacts] + ["Daniel Panea"]),
        speakers=speakers,
        theme=theme,
        risk=risk,
        next_action=next_action,
    )


def build_crm_records(accounts: list[AccountSpec], reference_date: date) -> dict[str, list[dict[str, Any]]]:
    now = datetime.combine(reference_date, time(9, 0), tzinfo=timezone.utc)
    users = [
        {
            "user_id": OWNER_ID,
            "name": "Daniel Panea Lichtig",
            "email": "daniel@danielpanea.com",
            "is_active": True,
            "profile_or_role": "Principal Architect",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
    ]
    account_rows: list[dict[str, Any]] = []
    for index, account in enumerate(accounts, start=1):
        created_at = datetime.combine(shift_date(d("2026-03-20"), reference_date), time(8), tzinfo=timezone.utc)
        updated_at = now - timedelta(days=index)
        account_rows.append(
            {
                "account_id": account.account_id,
                "account_name": account.name,
                "account_type": "Prospect",
                "industry": account.industry,
                "website": account.website,
                "phone": account.phone,
                "billing_country": account.country,
                "billing_city": account.city,
                "owner_id": OWNER_ID,
                "parent_account_id": "",
                "created_at": created_at.isoformat(),
                "updated_at": updated_at.isoformat(),
                "source_url": "",
                "raw_record_id": f"CRM_ACC_{index:04d}",
                "raw_record_hash": f"hash_account_{index:04d}",
            }
        )
    account_rows.append(
        {
            "account_id": INTERNAL_ACCOUNT_ID,
            "account_name": INTERNAL_ACCOUNT_NAME,
            "account_type": "internal_knowledge",
            "industry": "Company operations",
            "website": "https://danielpanea.example/internal-knowledge",
            "phone": "",
            "billing_country": "",
            "billing_city": "",
            "owner_id": OWNER_ID,
            "parent_account_id": "",
            "created_at": datetime.combine(shift_date(d("2026-03-20"), reference_date), time(8), tzinfo=timezone.utc).isoformat(),
            "updated_at": now.isoformat(),
            "source_url": "",
            "raw_record_id": "CRM_ACC_INTERNAL",
            "raw_record_hash": "hash_account_internal",
        }
    )
    return {"users": users, "accounts": account_rows}

