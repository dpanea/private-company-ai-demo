# Meeting: Rynvoss intro

**Date:** 2026-03-31
**Attendees:** Niels Koster (Head of Operations), Femke de Vries (Finance Director), Joris Bakker (IT Manager), Daniel Panea

---

**Daniel:** Thanks for making time. I would like to focus on routing exception context and keep the discussion tied to a pilotable workflow.

**Niels:** That is the right frame. The team is interested, but they need to understand what changes in their day-to-day work.

**Daniel:** The first change is visibility. Instead of asking someone to reconstruct context from inboxes and documents, the system prepares a cited briefing.

**Joris:** Citations matter. We cannot have people acting on a confident answer if no one can see where it came from.

**Daniel:** Agreed. The answer is only useful if the source artifacts remain inspectable and the retrieval path can be audited.

**Niels:** What would you need from us to make the first version credible without creating a large integration project?

**Daniel:** A bounded source set: a few email threads, CRM exports, meeting notes, and policy documents that represent the workflow.

**Joris:** That sounds manageable, but the source set needs approval before anything leaves our environment.

**Daniel:** For the public demo I use fully synthetic artifacts. For a pilot, the same architecture can run against approved or de-identified data first.

**Niels:** The operational pain is not theoretical. Before each review, people spend hours checking which customer promise or internal exception is still current.

**Daniel:** The workflow I would show is a call briefing, a recent-change summary, a risk alert, and a draft follow-up based on cited context.

**Joris:** The risk I want recorded is this: Finance needs a measurable link between reduced rework and pilot value.

**Daniel:** That is a valid blocker to track. I would rather keep it explicit than hide it under generic project language.

**Niels:** If the tool can surface that blocker automatically, it would already be useful for management review.

**Daniel:** The system can flag unresolved objections when a source states the concern and no later source closes the loop.

**Joris:** How do you prevent the model from inventing a resolution because the sales narrative wants one?

**Daniel:** The agent validates citations before presenting an answer. If the evidence is missing, it should say the issue is unresolved.

**Niels:** That would be helpful. People often remember the optimistic part of a discussion and forget the dependency.

**Daniel:** The account memory is designed to preserve both: positive signals and blocking questions.

**Joris:** What about deletion? If a source document is removed, the generated memory must stop using it.

**Daniel:** Deletion requires re-indexing affected documents and dropping derived records from retrieval. That is part of the ingestion contract.

**Niels:** For the pilot, I want the team to see the raw artifacts beside the AI answer. That will build trust faster than a dashboard alone.

**Daniel:** That is also how the demo is structured: messy artifacts on one side, answer and citations on the other.

**Joris:** What success metric would you use for a first pilot?

**Daniel:** Reduced preparation time and fewer missed follow-ups. We can measure whether the system finds known risks and recent changes.

**Niels:** I can support that. It is concrete and avoids pretending this is a full production platform.

**Joris:** I still want commercial and security boundaries written down before approval.

**Daniel:** Understood. I will keep the scope narrow and separate demo capabilities from production deployment work.

**Niels:** That distinction is important internally. We need progress without opening a platform procurement process too early.

**Daniel:** Next action: Daniel will send a narrow proposal with success criteria.

**Joris:** Please include the open risk in the written summary, not just the positive parts.

**Daniel:** I will. The summary will name the risk, the current owner, and what evidence would close it.

