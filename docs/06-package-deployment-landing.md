# Package 6 — Deployment and landing

**Purpose.** Make the demo runnable end-to-end on Daniel's Hetzner VPS, ship a working sovereign `deploy/vllm/` path, write the landing page, and finalize the public-facing README. This is the last package; everything else has to be working.

**Depends on:** Packages 4 and 5.

**Blocks:** nothing — this is the final shipping step.

**Estimated size:** small to medium (~300 LOC config + 1 HTML landing page + README).

## Outputs

```text
private-company-ai-demo/
├── README.md                     # final public README (rewrite of the placeholder)
├── docker-compose.yml            # demo stack: postgres + app (expanded from Package 1)
├── Dockerfile                    # application image
├── deploy/
│   ├── vllm/
│   │   ├── docker-compose.yml    # parallel stack swapping OpenRouter for vLLM
│   │   └── README.md             # sovereign-deployment usage notes
│   ├── caddy/
│   │   ├── Caddyfile.example     # reverse proxy config for the Hetzner VPS
│   │   └── README.md
│   └── landing/
│       ├── index.html            # the landing page at demo.danielpanea.com (or root URL)
│       ├── styles.css
│       └── assets/
└── scripts/
    └── deploy_hetzner.sh         # idempotent deployment helper (optional, documented)
```

## Final pyproject.toml

By this point all dependencies from packages 1–5 are present. Audit the file and remove any that ended up unused.

## Dockerfile

```dockerfile
FROM python:3.11-slim-bookworm

# System dependencies for OCR and PDF rendering
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    cp /root/.local/bin/uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY src/ ./src/
COPY sql/ ./sql/
COPY scripts/ ./scripts/

# Synthetic corpus is baked into the image (intentional — the demo is read-mostly).
COPY data/synthetic/ ./data/synthetic/

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "pcad.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
```

A pre-startup migration + ingestion step runs on first container start (idempotent). Implementation: an entrypoint script that runs `pcad migrate` then `pcad ingest-demo --clean` only if `rag_documents` is empty.

## Main docker-compose.yml (demo stack)

Expands the Postgres-only compose from Package 1.

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  app:
    build: .
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      OPENROUTER_API_KEY: ${OPENROUTER_API_KEY}
      OPENROUTER_BASE_URL: ${OPENROUTER_BASE_URL:-https://openrouter.ai/api/v1}
      LLM_MODEL: ${LLM_MODEL}
      EMBEDDING_MODEL: ${EMBEDDING_MODEL}
      EMBEDDING_DIMENSIONS: ${EMBEDDING_DIMENSIONS}
      APP_TITLE: ${APP_TITLE}
      HTTP_REFERER: ${HTTP_REFERER}
      LOG_LEVEL: ${LOG_LEVEL:-INFO}
      SESSION_SECRET: ${SESSION_SECRET}
      RATE_LIMIT_PER_IP_PER_MINUTE: ${RATE_LIMIT_PER_IP_PER_MINUTE:-20}
      RATE_LIMIT_PER_SESSION_PER_HOUR: ${RATE_LIMIT_PER_SESSION_PER_HOUR:-50}
      DAILY_TOKEN_BUDGET: ${DAILY_TOKEN_BUDGET:-1500000}
    volumes:
      - rendered_data:/app/data/rendered
    ports:
      - "127.0.0.1:8000:8000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

volumes:
  postgres_data:
  rendered_data:
```

Port `8000` binds only to `127.0.0.1` because Caddy on the host terminates TLS and reverse-proxies to it. Tailscale is used for admin access; only HTTP/HTTPS is open to the internet.

## deploy/vllm/docker-compose.yml (sovereign stack)

A parallel compose file that swaps OpenRouter for self-hosted vLLM. Pattern adapted from `~/projects/123go/chathub/docker-compose.yml`.

```yaml
services:
  postgres:
    extends:
      file: ../../docker-compose.yml
      service: postgres

  vllm:
    image: vllm/vllm-openai:latest
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: ["gpu"]
    command: >
      --model ${LLM_MODEL_VLLM}
      --max-model-len 8192
      --max-num-batched-tokens 2048
      --gpu-memory-utilization 0.95
      --kv-cache-dtype fp8
      --enable-prefix-caching
      --max-num-seqs 8
      --host 0.0.0.0
      --port 8080
    volumes:
      - huggingface_cache:/root/.cache/huggingface
    shm_size: "8gb"
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 5
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  app:
    extends:
      file: ../../docker-compose.yml
      service: app
    depends_on:
      postgres:
        condition: service_healthy
      vllm:
        condition: service_healthy
    environment:
      # Override OpenRouter with vLLM
      OPENROUTER_BASE_URL: http://vllm:8080/v1
      OPENROUTER_API_KEY: ${LLM_API_KEY:-local}
      LLM_MODEL: ${LLM_MODEL_VLLM}
      # Embeddings still hit OpenRouter unless an embedding-capable vLLM model is configured.
      # The sovereign path documents this as a known trade-off.

volumes:
  postgres_data:
  rendered_data:
  huggingface_cache:
```

Default `LLM_MODEL_VLLM` recommendations (documented in `deploy/vllm/README.md`):

| GPU VRAM | Recommended model | Notes |
|---|---|---|
| 4–6 GB (Daniel's laptop) | `google/gemma-2-2b-it` with `--quantization awq` if an AWQ build is available; otherwise switch to llama.cpp (out of scope for this compose file) | Tight fit. Useful only for smoke-testing the swap. |
| 12–16 GB | `google/gemma-2-9b-it` | Comfortable. |
| 24 GB+ (production sovereign) | `google/gemma-2-27b-it` or `Qwen/Qwen2.5-14B-Instruct` | The realistic production size. |

The README spells out that the vLLM compose is **not** used by the public demo; it exists to make the sovereignty pitch concrete. Daniel must test it once on real GPU hardware before publishing the repo. Acceptance criterion below.

## deploy/caddy/Caddyfile.example

```caddyfile
demo.danielpanea.com {
    encode gzip
    reverse_proxy 127.0.0.1:8000

    # Rate limiting at the proxy level (defense in depth on top of app-level limits)
    @api path /api/*
    rate_limit @api {
        zone api {
            key {client_ip}
            events 60
            window 1m
        }
    }

    log {
        output file /var/log/caddy/demo.log
        format json
    }
}
```

Caddy auto-provisions a Let's Encrypt cert for the subdomain. The `rate_limit` directive requires the [caddy-ratelimit](https://github.com/mholt/caddy-ratelimit) module — document the build command in `deploy/caddy/README.md`.

## deploy/landing/index.html

A single-page landing at the root URL or a separate `/private-company-memory` path. Plain HTML/CSS (no framework). Claude Design produces the visual; the structure must include:

1. **Hero** — "Never walk into a client call cold again." + subline + primary CTA "Try the synthetic demo".
2. **What the demo does (90 seconds)** — short illustrated explainer of the three steps: messy sources → AI-ready memory → source-backed answers.
3. **Why private** — short list: on-prem / EU deployment, open weights, audit posture, you own everything.
4. **Three flagship workflows** — screenshots of briefing / what changed / follow-up draft.
5. **Open-source reference architecture** — link to GitHub repo with the right framing ("reference architecture, not turnkey product").
6. **Who it's for** — bulleted list of fit and trigger situations.
7. **Implementation offer** — link to the assessment offer on `danielpanea.com`.
8. **Book a private walkthrough** — secondary CTA.

The landing page is served as a separate static site (or under the same FastAPI app at a `/landing` path). Decision: keep it inside the same repo for simplicity, served by FastAPI from `src/pcad/api/static/landing/`.

## Final README (public-facing)

Replaces the placeholder created in Package 1. Sections (each ~1–4 paragraphs):

1. **What this is** — one paragraph, no marketing.
2. **Try it** — link to the demo URL.
3. **Architecture** — diagram (ASCII or mermaid) + paragraph. Reference the package docs for depth.
4. **Why this exists** — pointer to the Obsidian commercial-positioning doc public summary; one paragraph on the company-memory-layer concept.
5. **Demo scope vs. production scope** — full enumeration of what's *not* in the repo:
   - Incremental and event-driven ingestion sync.
   - Format detection and content-type sniffing.
   - OCR for arbitrary scanned documents (the demo OCRs one known PDF; production-grade OCR requires layout-aware models).
   - Deduplication.
   - Attachment recovery from email threads.
   - Mail thread reconstruction beyond In-Reply-To / References headers.
   - Schema evolution and migrations against live data.
   - Per-user permissions and row-level security.
   - Multi-tenant isolation.
   - Audit logging and retention controls.
   - Failure handling, dead-letter queues, observability beyond basic logs.
   - Evaluation methodology, gold-question test sets, hallucination measurement.
   - Production deployment runbooks (backup, monitoring, model rotation, incident response).
6. **Local development** — `docker compose up -d`, `pcad migrate`, `pcad ingest-demo --clean`, `pcad serve`.
7. **Sovereign deployment (vLLM)** — point to `deploy/vllm/` and the README there. Includes the screenshot from Daniel's GPU test as proof that the swap works.
8. **License and credits** — Apache-2.0, link to Daniel's site.

## Acceptance criteria

1. `docker compose up -d` on a freshly cloned repo + `.env` brings up Postgres and the app. The app runs migrations and ingests the demo corpus on first boot.
2. The full demo works end-to-end on a clean Hetzner CPU instance reachable at `https://demo.danielpanea.com` (or chosen subdomain) via Caddy.
3. `deploy/vllm/docker-compose.yml` has been tested once on real GPU hardware (Daniel performs this). A screenshot or short Loom of the demo running against vLLM is captured for the README and a LinkedIn post.
4. The landing page is reachable at the root URL of the chosen subdomain and renders correctly.
5. The README's "Demo scope vs. production scope" section is present and matches the enumeration above.
6. The repo passes a final `grep -ri "spanish\|espanol\|fuente"` sweep with zero hits.
7. A daily-budget exhaustion test produces the canned response and stops calling OpenRouter for the rest of the day.
8. Caddy is configured with HTTPS, rate-limit module, and JSON logging.
9. The OpenRouter API key is present only in the server's `.env`; no key value appears in any committed file.
