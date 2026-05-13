from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable
from datetime import datetime, timezone

from pcad.ingestion.normalize import EmailThread, MeetingSummaryInput
from pcad.models import Account, Activity, Contract, Opportunity, RagDocument, RawArtifact, SourceCitation, SyntheticDataset


RISK_RE = re.compile(
    r"\b(risk|concern|objection|blocked|security|compliance|procurement|unanswered|delay|stalled|budget)\b",
    re.IGNORECASE,
)


def stable_hash(parts: Iterable[str]) -> str:
    return "sha256:" + hashlib.sha256("\n".join(part for part in parts if part).encode("utf-8")).hexdigest()


def line(value: object | None, fallback: str = "Unknown") -> str:
    if value is None or value == "":
        return fallback
    return str(value)


def citation_for(
    doc_id: str,
    source_object: str,
    record_id: str,
    title: str | None,
    source_url: str | None = None,
    source_date=None,
    owner_id: str | None = None,
    excerpt: str | None = None,
) -> SourceCitation:
    return SourceCitation(
        citation_id=f"{doc_id}:{source_object}:{record_id}",
        doc_id=doc_id,
        source_object=source_object,
        source_record_id=record_id,
        source_url=source_url,
        title=title,
        source_date=source_date,
        owner_id=owner_id,
        excerpt=excerpt,
    )


class DocumentBuilder:
    def __init__(
        self,
        dataset: SyntheticDataset,
        *,
        email_threads: list[EmailThread] | None = None,
        meeting_summaries: list[MeetingSummaryInput] | None = None,
        raw_artifacts: list[RawArtifact] | None = None,
    ) -> None:
        self.dataset = dataset
        self.users = {u.user_id: u for u in dataset.users}
        self.accounts = {a.account_id: a for a in dataset.accounts}
        self.opps_by_id = {o.opportunity_id: o for o in dataset.opportunities}
        self.contacts_by_account = self._group(dataset.contacts, "account_id")
        self.opps_by_account = self._group(dataset.opportunities, "account_id")
        self.contracts_by_account = self._group(dataset.contracts, "account_id")
        self.activities_by_account = self._group([a for a in dataset.activities if a.account_id], "account_id")
        self.activities_by_opportunity = self._group([a for a in dataset.activities if a.opportunity_id], "opportunity_id")
        self.email_threads = email_threads or []
        self.meeting_summaries = meeting_summaries or []
        self.raw_artifacts = raw_artifacts or dataset.raw_artifacts
        self.raw_by_id = {artifact.artifact_id: artifact for artifact in self.raw_artifacts}
        self.raw_artifacts_by_account = self._group(self.raw_artifacts, "account_id")
        self.email_threads_by_account = self._group(self.email_threads, "account_id")
        self.meetings_by_account = self._group(self.meeting_summaries, "account_id")

    @staticmethod
    def _group(items: Iterable[object], attr: str) -> dict[str, list]:
        grouped: dict[str, list] = {}
        for item in items:
            key = getattr(item, attr, None)
            if key:
                grouped.setdefault(key, []).append(item)
        return grouped

    def owner_name(self, owner_id: str | None) -> str:
        if not owner_id:
            return "Unknown"
        user = self.users.get(owner_id)
        return user.name if user else owner_id

    def build_all(self) -> list[RagDocument]:
        docs: list[RagDocument] = []
        for account in self.dataset.accounts:
            docs.append(self.account_memory(account))
            docs.append(self.recent_activity_timeline(account))
            if self.contacts_by_account.get(account.account_id):
                docs.append(self.stakeholder_map(account))
            docs.extend(self.email_thread_summary(account, thread) for thread in self.email_threads_by_account.get(account.account_id, []))
            docs.extend(self.meeting_summary(account, meeting) for meeting in self.meetings_by_account.get(account.account_id, []))
            docs.append(self.risk_summary(account))
        for opportunity in self.dataset.opportunities:
            docs.append(self.opportunity_snapshot(opportunity))
        for contract in self.dataset.contracts:
            docs.append(self.contract_snapshot(contract))
        return docs

    def account_memory(self, account: Account) -> RagDocument:
        contacts = self.contacts_by_account.get(account.account_id, [])
        opportunities = self.opps_by_account.get(account.account_id, [])
        contracts = self.contracts_by_account.get(account.account_id, [])
        activities = _recent(self.activities_by_account.get(account.account_id, []), 8)
        doc_id = f"account_memory:{account.account_id}"
        content = _section_lines(
            f"# Account: {account.account_name}",
            [
                ("## Account data", [
                    f"- Account ID: {account.account_id}",
                    f"- Owner: {self.owner_name(account.owner_id)}",
                    f"- Type: {line(account.account_type)}",
                    f"- Industry: {line(account.industry)}",
                    f"- Website: {line(account.website)}",
                    f"- Location: {line(account.billing_city)}, {line(account.billing_country)}",
                    f"- [Source: Account {account.account_id}]",
                ]),
                ("## Key contacts", [f"- {c.name} - {line(c.title)} - {line(c.email)} [Source: Contact {c.contact_id}]" for c in contacts]),
                ("## Opportunities", [
                    f"- {o.name} - Stage: {line(o.stage)} - Amount: {line(o.amount)} {line(o.currency, '')} - Close date: {line(o.close_date)} - Owner: {self.owner_name(o.owner_id)} [Source: Opportunity {o.opportunity_id}]"
                    for o in opportunities
                ]),
                ("## Contracts", [
                    f"- {c.contract_number} - Status: {line(c.status)} - Start: {line(c.start_date)} - End: {line(c.end_date)} [Source: Contract {c.contract_id}]"
                    for c in contracts
                ]),
                ("## Recent activity", [_activity_line(a) for a in activities]),
            ],
        )
        source_ids = [account.account_id] + [c.contact_id for c in contacts] + [o.opportunity_id for o in opportunities] + [c.contract_id for c in contracts] + [a.activity_id for a in activities]
        citations = [citation_for(doc_id, "Account", account.account_id, account.account_name, account.source_url, owner_id=account.owner_id)]
        citations.extend(_activity_citation(doc_id, a) for a in activities)
        return self._build_doc(doc_id, "account_memory", f"Account memory: {account.account_name}", content, ["Account", "Contact", "Opportunity", "Contract", "Task", "Event"], source_ids, citations, account, last_source_updated_at=account.updated_at)

    def opportunity_snapshot(self, opportunity: Opportunity) -> RagDocument:
        account = self.accounts[opportunity.account_id]
        contacts = self.contacts_by_account.get(account.account_id, [])
        activities = _recent(self.activities_by_opportunity.get(opportunity.opportunity_id, []), 8)
        doc_id = f"opportunity_snapshot:{opportunity.opportunity_id}"
        status = "Won" if opportunity.is_won else "Closed" if opportunity.is_closed else "Open"
        content = _section_lines(
            f"# Opportunity: {opportunity.name}",
            [
                ("## Opportunity data", [
                    f"- Opportunity ID: {opportunity.opportunity_id}",
                    f"- Account: {account.account_name}",
                    f"- Owner: {self.owner_name(opportunity.owner_id)}",
                    f"- Stage: {line(opportunity.stage)}",
                    f"- Amount: {line(opportunity.amount)} {line(opportunity.currency, '')}",
                    f"- Close date: {line(opportunity.close_date)}",
                    f"- Probability: {line(opportunity.probability)}",
                    f"- Status: {status}",
                    f"- [Source: Opportunity {opportunity.opportunity_id}]",
                ]),
                ("## Related contacts", [f"- {c.name} - {line(c.title)} - {line(c.email)}" for c in contacts]),
                ("## Recent opportunity activity", [_activity_line(a) for a in activities]),
            ],
        )
        source_ids = [opportunity.opportunity_id, account.account_id] + [c.contact_id for c in contacts] + [a.activity_id for a in activities]
        citations = [citation_for(doc_id, "Opportunity", opportunity.opportunity_id, opportunity.name, opportunity.source_url, opportunity.close_date, opportunity.owner_id)]
        citations.extend(_activity_citation(doc_id, a) for a in activities)
        return self._build_doc(doc_id, "opportunity_snapshot", f"Opportunity snapshot: {opportunity.name}", content, ["Opportunity", "Account", "Contact", "Task", "Event"], source_ids, citations, account, opportunity_id=opportunity.opportunity_id, owner_id=opportunity.owner_id, last_source_updated_at=opportunity.updated_at, extra_metadata={"opportunity_id": opportunity.opportunity_id, "stage": opportunity.stage})

    def recent_activity_timeline(self, account: Account) -> RagDocument:
        activities = sorted(self.activities_by_account.get(account.account_id, []), key=lambda a: a.activity_date or datetime.min.date(), reverse=True)
        doc_id = f"recent_activity_timeline:{account.account_id}:180d"
        content = _section_lines(
            f"# Recent activity timeline: {account.account_name}",
            [
                ("## Scope", [f"- Account: {account.account_name}", "- Time window: latest synthetic CRM activities"]),
                ("## Timeline", [_activity_line(activity) for activity in activities]),
            ],
        )
        source_ids = [account.account_id] + [a.activity_id for a in activities]
        last = max((a.updated_at for a in activities if a.updated_at), default=account.updated_at)
        return self._build_doc(doc_id, "recent_activity_timeline", f"Recent activity timeline: {account.account_name}", content, ["Task", "Event"], source_ids, [_activity_citation(doc_id, a) for a in activities], account, last_source_updated_at=last)

    def contract_snapshot(self, contract: Contract) -> RagDocument:
        account = self.accounts[contract.account_id]
        opportunity = self.opps_by_id.get(contract.opportunity_id_if_available) if contract.opportunity_id_if_available else None
        activities = _recent(self.activities_by_account.get(account.account_id, []), 5)
        doc_id = f"contract_snapshot:{contract.contract_id}"
        content = _section_lines(
            f"# Contract: {contract.contract_number}",
            [
                ("## Contract data", [
                    f"- Contract ID: {contract.contract_id}",
                    f"- Account: {account.account_name}",
                    f"- Status: {line(contract.status)}",
                    f"- Start date: {line(contract.start_date)}",
                    f"- End date: {line(contract.end_date)}",
                    f"- Owner: {self.owner_name(contract.owner_id)}",
                    f"- [Source: Contract {contract.contract_id}]",
                ]),
                ("## Related opportunity", [f"- {opportunity.name if opportunity else 'Unknown'}"]),
                ("## Related activity", [f"- {line(a.activity_date)} - {line(a.subject)} - {short_description(a)}" for a in activities]),
            ],
        )
        source_ids = [contract.contract_id, account.account_id] + ([opportunity.opportunity_id] if opportunity else []) + [a.activity_id for a in activities]
        return self._build_doc(doc_id, "contract_snapshot", f"Contract snapshot: {contract.contract_number}", content, ["Contract", "Account", "Opportunity", "Task", "Event"], source_ids, [citation_for(doc_id, "Contract", contract.contract_id, contract.contract_number, contract.source_url, contract.start_date, contract.owner_id)], account, opportunity_id=opportunity.opportunity_id if opportunity else None, contract_id=contract.contract_id, owner_id=contract.owner_id, last_source_updated_at=contract.updated_at, extra_metadata={"contract_id": contract.contract_id})

    def stakeholder_map(self, account: Account) -> RagDocument:
        contacts = self.contacts_by_account.get(account.account_id, [])
        activities = self.activities_by_account.get(account.account_id, [])
        doc_id = f"stakeholder_map:{account.account_id}"
        content = _section_lines(
            f"# Stakeholder map: {account.account_name}",
            [
                ("## Contacts", [
                    f"- {c.name} - {line(c.title)} - {line(c.role_or_department)} - Recent interactions: {sum(1 for a in activities if a.contact_id == c.contact_id)} [Source: Contact {c.contact_id}]"
                    for c in contacts
                ]),
            ],
        )
        source_ids = [account.account_id] + [c.contact_id for c in contacts]
        citations = [citation_for(doc_id, "Contact", c.contact_id, c.name, c.source_url, owner_id=c.owner_id) for c in contacts]
        return self._build_doc(doc_id, "stakeholder_map", f"Stakeholder map: {account.account_name}", content, ["Account", "Contact", "Task", "Event"], source_ids, citations, account, last_source_updated_at=account.updated_at)

    def email_thread_summary(self, account: Account, thread: EmailThread) -> RagDocument:
        doc_id = f"email_thread_summary:{account.account_id}:{thread.thread_id}"
        message_lines = []
        for email in thread.emails:
            summary = _first_last_sentence(email.body_text)
            message_lines.append(
                f"- {line(email.date)} - {email.from_addr} to {', '.join(email.to_addrs)}: {summary} [Source: Email {email.message_id}]"
            )
        open_questions = [
            f"- {email.from_addr}: {_first_sentence(email.body_text)} [Source: Email {email.message_id}]"
            for email in thread.emails
            if "?" in email.body_text
        ]
        content = _section_lines(
            f"# Email thread: {thread.subject}",
            [
                ("## Participants", [f"- {participant}" for participant in thread.participants]),
                ("## Chronological summary", message_lines),
                ("## Open questions", open_questions or ["- No explicit unanswered questions detected."]),
            ],
        )
        citations = [
            citation_for(doc_id, "Email", email.message_id, email.subject, None, email.date.date() if email.date else None, excerpt=_first_sentence(email.body_text))
            for email in thread.emails
        ]
        return self._build_doc(doc_id, "email_thread_summary", f"Email thread summary: {thread.subject}", content, ["Email"], thread.artifact_ids, citations, account, last_source_updated_at=thread.emails[-1].date if thread.emails else None, extra_metadata={"thread_id": thread.thread_id, "participants": thread.participants})

    def meeting_summary(self, account: Account, meeting: MeetingSummaryInput) -> RagDocument:
        doc_id = f"meeting_summary:{account.account_id}:{meeting.meeting_id}"
        source_id = meeting.source_artifact_id or meeting.meeting_id
        content = _section_lines(
            f"# Meeting summary: {meeting.meeting_title}",
            [
                ("## Meeting data", [
                    f"- Account: {account.account_name}",
                    f"- Date: {line(meeting.meeting_date)}",
                    f"- Attendees: {', '.join(meeting.attendees) if meeting.attendees else 'Unknown'}",
                    f"- [Source: Meeting {source_id}]",
                ]),
                ("## Key topics", [f"- {item}" for item in meeting.key_topics] or ["- No key topics extracted."]),
                ("## Action items", [f"- {item}" for item in meeting.action_items] or ["- No action items detected."]),
                ("## Risks and concerns", [f"- {item}" for item in meeting.risks] or ["- No risks or concerns detected."]),
            ],
        )
        citation_date = None
        if meeting.meeting_date:
            citation_date = datetime.fromisoformat(meeting.meeting_date).date()
        citation = citation_for(doc_id, "Meeting", source_id, meeting.meeting_title, None, citation_date)
        return self._build_doc(doc_id, "meeting_summary", f"Meeting summary: {meeting.meeting_title}", content, ["Meeting"], [source_id], [citation], account, last_source_updated_at=datetime.now(timezone.utc), extra_metadata={"meeting_id": meeting.meeting_id})

    def risk_summary(self, account: Account) -> RagDocument:
        doc_id = f"risk_summary:{account.account_id}"
        risks: list[tuple[str, str, str]] = []
        for artifact in self.raw_artifacts_by_account.get(account.account_id, []):
            for sentence in _risk_sentences(artifact.extracted_text):
                risks.append((artifact.artifact_id, artifact.title, sentence))
        for activity in self.activities_by_account.get(account.account_id, []):
            text = " ".join(part for part in [activity.subject, activity.description] if part)
            if activity.priority == "High" and activity.status != "Completed":
                risks.append((activity.activity_id, activity.subject or activity.activity_id, text or "High-priority open task."))
            else:
                for sentence in _risk_sentences(text):
                    risks.append((activity.activity_id, activity.subject or activity.activity_id, sentence))
        content = _section_lines(
            f"# Risk summary: {account.account_name}",
            [
                ("## Detected risks, objections, and unresolved questions", [
                    f"- {title}: {sentence} [Source: RiskEvidence {record_id}]"
                    for record_id, title, sentence in risks[:15]
                ] or ["- No risk keywords detected in the ingested sources."]),
            ],
        )
        citations = [
            SourceCitation(
                citation_id=f"{doc_id}:RiskEvidence:{index}:{record_id}",
                doc_id=doc_id,
                source_object="RiskEvidence",
                source_record_id=record_id,
                title=title,
                excerpt=sentence[:300],
            )
            for index, (record_id, title, sentence) in enumerate(risks[:15], start=1)
        ]
        source_ids = [record_id for record_id, _, _ in risks[:15]] or [account.account_id]
        return self._build_doc(doc_id, "risk_summary", f"Risk summary: {account.account_name}", content, ["RawArtifact", "Task", "Event"], source_ids, citations, account, last_source_updated_at=account.updated_at)

    def _build_doc(
        self,
        doc_id: str,
        doc_type: str,
        title: str,
        content: str,
        source_objects: list[str],
        source_ids: list[str],
        citations: list[SourceCitation],
        account: Account,
        *,
        opportunity_id: str | None = None,
        contract_id: str | None = None,
        owner_id: str | None = None,
        last_source_updated_at: datetime | None = None,
        extra_metadata: dict | None = None,
    ) -> RagDocument:
        metadata = {
            "doc_type": doc_type,
            "source_system": "synthetic",
            "source_objects": source_objects,
            "account_id": account.account_id,
            "account_name": account.account_name,
            "owner_id": owner_id or account.owner_id,
            "visibility_scope": ["public_demo"],
        }
        if extra_metadata:
            metadata.update(extra_metadata)
        return RagDocument(
            doc_id=doc_id,
            doc_type=doc_type,
            title=title,
            content_markdown=content,
            metadata_json=metadata,
            source_record_ids=source_ids,
            source_record_hashes=[stable_hash(source_ids)],
            account_id=account.account_id,
            opportunity_id=opportunity_id,
            contract_id=contract_id,
            owner_id=owner_id or account.owner_id,
            last_source_updated_at=last_source_updated_at,
            generated_at=datetime.now(timezone.utc),
            source_hash=stable_hash(source_ids + [content]),
            citations=citations,
        )


def _section_lines(header: str, sections: list[tuple[str, list[str]]]) -> str:
    lines = [header]
    for title, items in sections:
        lines.extend(["", title, *items])
    return "\n".join(lines).strip() + "\n"


def _recent(activities: list[Activity], limit: int) -> list[Activity]:
    return sorted(activities, key=lambda a: a.activity_date or datetime.min.date(), reverse=True)[:limit]


def short_description(activity: Activity, limit: int = 220) -> str:
    text = activity.description or ""
    return text if len(text) <= limit else text[: limit - 3].rstrip() + "..."


def _activity_line(activity: Activity) -> str:
    return f"- {line(activity.activity_date)} - {activity.source_object} - {line(activity.subject)} - {short_description(activity)} [Source: {activity.source_object} {activity.activity_id}]"


def _activity_citation(doc_id: str, activity: Activity) -> SourceCitation:
    return citation_for(doc_id, activity.source_object, activity.activity_id, activity.subject, activity.source_url, activity.activity_date, activity.owner_id, short_description(activity))


def _first_sentence(text: str) -> str:
    sentences = _sentences(text)
    return sentences[0] if sentences else ""


def _first_last_sentence(text: str) -> str:
    sentences = _sentences(text)
    if not sentences:
        return ""
    if len(sentences) == 1:
        return sentences[0]
    return f"{sentences[0]} ... {sentences[-1]}"


def _sentences(text: str) -> list[str]:
    return [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", text.strip()) if sentence.strip()]


def _risk_sentences(text: str) -> list[str]:
    return [sentence for sentence in _sentences(text) if RISK_RE.search(sentence)]
