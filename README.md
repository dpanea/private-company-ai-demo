# private-company-ai-demo

Public demo and open-source reference architecture for a **Private Company Memory Layer** — a system that turns messy company artifacts (emails, PDFs, meeting transcripts, Word documents, CRM exports) into source-backed account briefings, "what changed" summaries, proactive risk alerts, and follow-up drafts, without sending sensitive client data to generic cloud AI tools.

This repository serves three purposes:

1. **Marketing spear** — a concrete object that can be sent to buyers, partners, and conference contacts.
2. **Open-source reference architecture** — a working example of private/sovereign RAG on top of company data.
3. **Credibility artifact** — proof of architectural competence for technical evaluators and partner consultancies.

## Repository status

This repository currently contains specifications only. Implementation is planned across six packages documented in [`docs/`](docs/). See [docs/00-overview.md](docs/00-overview.md) for the orchestration plan.

## Demo scope vs. production scope

The application in this repository is a **reference architecture, not a turnkey product**. Demo-scope shortcuts are documented and intentional. Production deployments require adaptation that lives outside this repo. See [docs/06-package-deployment-landing.md](docs/06-package-deployment-landing.md) for the explicit list.

## License

Apache License 2.0 — see [LICENSE](LICENSE).

## Author

Daniel Panea Lichtig — [danielpanea.com](https://danielpanea.com)
