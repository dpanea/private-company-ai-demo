# Meeting: All-hands strategy recap

**Date:** 2026-05-09
**Attendees:** Daniel Panea, Delivery collaborators, Advisory reviewers

---

**Daniel:** The naming is moving from account memory toward Company Knowledge AI because the demo needs to prove more than CRM retrieval. The sales wedge stays, but internal policies, vendor decisions, and delivery knowledge have to be visible in the same source-backed interface.

**Delivery:** The account workflows are still the clearest demo moment. Briefing before a client call remains concrete and relatable, especially for consultancies and Mittelstand buyers.

**Daniel:** Agreed. The change is not to flatten the sales use case. The change is to make the account picker optional context instead of a gate. If someone asks about SOC 2 status, onboarding, or a vendor decision, the system should answer from internal artifacts without demanding a client.

**Advisory:** SOC 2 should be described carefully. The current state is readiness work, not certification. Evidence collection is underway, but no public claim should say the company is certified or audited.

**Daniel:** Record that as a decision. Public copy may say audit-friendly architecture and SOC 2 readiness work. It must not say SOC 2 certified.

**Delivery:** What is the DES focus?

**Daniel:** The DES demo should show two registers. First, a client call briefing with citations. Second, a general company question such as onboarding or "what did we decide about Postgres and pgvector?" That gives non-sales buyers a way into the demo.

**Advisory:** The risk is breadth. More buttons can make the interface feel unfocused.

**Daniel:** We will keep the button count tight. "What changed?" and "Next action" are removed from the primary workflow set for now. "Catch me up" and "What did we decide about..." become editable prompt starters rather than automatic model calls.

**Delivery:** What should happen when the user clicks a general workflow?

**Daniel:** It should prefill the composer and focus it. The user supplies the topic. No LLM call should be spent asking what topic they meant.

**Advisory:** What is the current SOC 2 status phrase?

**Daniel:** "SOC 2 readiness work is underway; certification is not claimed." The evidence pack target is a first internal draft in June 2026, focused on source retention, deletion behavior, logging boundaries, and subprocessor review.
