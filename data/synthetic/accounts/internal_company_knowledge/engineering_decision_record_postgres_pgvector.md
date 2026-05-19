# Meeting: Engineering decision record - Postgres and pgvector

**Date:** 2026-04-26
**Attendees:** Daniel Panea, Architecture reviewers

---

**Daniel:** Decision proposed: use PostgreSQL 16 with pgvector and pg_trgm as the retrieval store for the public demo instead of introducing a separate vector database.

**Reviewer:** What problem does that solve?

**Daniel:** It keeps the reference architecture legible. The demo needs accounts, raw artifacts, AI-ready documents, source citations, sessions, and embeddings. Keeping them in one database makes migrations, local setup, and deletion behavior easier to explain.

**Reviewer:** What alternatives were considered?

**Daniel:** A managed vector database, OpenSearch, and a document store with a separate embedding index. Each is reasonable in production under the right constraints, but each adds another operational surface for a public reference demo.

**Reviewer:** What is the trade-off?

**Daniel:** pgvector is good enough for the small corpus and for paid-pilot prototypes. It is not a claim that one Postgres instance is the correct answer for every large enterprise memory system. At larger scale, ranking, sharding, and evaluation may justify a separate retrieval service.

**Reviewer:** Why include full-text search?

**Daniel:** Company questions often contain exact names, policy terms, dates, and contract phrases. Dense vector search alone can miss exact terms. The retrieval plan uses English full-text search, embeddings, and reciprocal rank fusion so exact and semantic matches both have a path.

**Reviewer:** What is the operational decision?

**Daniel:** Ship the demo on Postgres plus pgvector, document the boundary, and avoid production-grade ingestion claims. The decision can be reopened if corpus size, latency, or customer isolation requirements exceed what a single database can handle cleanly.

**Reviewer:** How does this affect citations?

**Daniel:** Source citations stay relational. Every answerable chunk points back to a raw artifact citation. If an artifact is deleted, derived documents and citations can be removed with standard database operations and the embedding index can be rebuilt.
