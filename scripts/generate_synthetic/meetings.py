from __future__ import annotations

from pathlib import Path

from .accounts import MeetingSpec


def write_meeting(path: Path, meeting: MeetingSpec) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    turns = _build_turns(meeting)
    attendees = ", ".join(meeting.attendees)
    body = [
        f"# Meeting: {meeting.title}",
        "",
        f"**Date:** {meeting.meeting_date.isoformat()}",
        f"**Attendees:** {attendees}",
        "",
        "---",
        "",
        *turns,
        "",
    ]
    path.write_text("\n".join(body), encoding="utf-8", newline="\n")


def _build_turns(meeting: MeetingSpec) -> list[str]:
    daniel, lead, stakeholder = meeting.speakers
    beats = [
        (daniel, f"Thanks for making time. I would like to focus on {meeting.theme} and keep the discussion tied to a pilotable workflow."),
        (lead, "That is the right frame. The team is interested, but they need to understand what changes in their day-to-day work."),
        (daniel, "The first change is visibility. Instead of asking someone to reconstruct context from inboxes and documents, the system prepares a cited briefing."),
        (stakeholder, "Citations matter. We cannot have people acting on a confident answer if no one can see where it came from."),
        (daniel, "Agreed. The answer is only useful if the source artifacts remain inspectable and the retrieval path can be audited."),
        (lead, "What would you need from us to make the first version credible without creating a large integration project?"),
        (daniel, "A bounded source set: a few email threads, CRM exports, meeting notes, and policy documents that represent the workflow."),
        (stakeholder, "That sounds manageable, but the source set needs approval before anything leaves our environment."),
        (daniel, "For the public demo I use fully synthetic artifacts. For a pilot, the same architecture can run against approved or de-identified data first."),
        (lead, "The operational pain is not theoretical. Before each review, people spend hours checking which customer promise or internal exception is still current."),
        (daniel, "The workflow I would show is a call briefing, a recent-change summary, a risk alert, and a draft follow-up based on cited context."),
        (stakeholder, f"The risk I want recorded is this: {meeting.risk}"),
        (daniel, "That is a valid blocker to track. I would rather keep it explicit than hide it under generic project language."),
        (lead, "If the tool can surface that blocker automatically, it would already be useful for management review."),
        (daniel, "The system can flag unresolved objections when a source states the concern and no later source closes the loop."),
        (stakeholder, "How do you prevent the model from inventing a resolution because the sales narrative wants one?"),
        (daniel, "The agent validates citations before presenting an answer. If the evidence is missing, it should say the issue is unresolved."),
        (lead, "That would be helpful. People often remember the optimistic part of a discussion and forget the dependency."),
        (daniel, "The account memory is designed to preserve both: positive signals and blocking questions."),
        (stakeholder, "What about deletion? If a source document is removed, the generated memory must stop using it."),
        (daniel, "Deletion requires re-indexing affected documents and dropping derived records from retrieval. That is part of the ingestion contract."),
        (lead, "For the pilot, I want the team to see the raw artifacts beside the AI answer. That will build trust faster than a dashboard alone."),
        (daniel, "That is also how the demo is structured: messy artifacts on one side, answer and citations on the other."),
        (stakeholder, "What success metric would you use for a first pilot?"),
        (daniel, "Reduced preparation time and fewer missed follow-ups. We can measure whether the system finds known risks and recent changes."),
        (lead, "I can support that. It is concrete and avoids pretending this is a full production platform."),
        (stakeholder, "I still want commercial and security boundaries written down before approval."),
        (daniel, "Understood. I will keep the scope narrow and separate demo capabilities from production deployment work."),
        (lead, "That distinction is important internally. We need progress without opening a platform procurement process too early."),
        (daniel, f"Next action: {meeting.next_action}"),
        (stakeholder, "Please include the open risk in the written summary, not just the positive parts."),
        (daniel, "I will. The summary will name the risk, the current owner, and what evidence would close it."),
    ]
    return [f"**{speaker}:** {text}\n" for speaker, text in beats]
