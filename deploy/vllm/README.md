# Sovereign vLLM deployment

This compose file runs the same app against a local OpenAI-compatible vLLM
server instead of a hosted LLM provider. The public demo does not use this
path; it exists to make the sovereign deployment option concrete.

Embeddings still use the configured hosted embedding endpoint unless you set
`EMBEDDING_MODEL` and `LLM_BASE_URL` to an embedding-capable local service.
Treat that as an integration decision for a real deployment.

## Requirements

- Linux host with NVIDIA drivers.
- Docker with the NVIDIA container runtime.
- A `.env` file at the repository root with the normal demo variables plus
  `LLM_MODEL_VLLM`.
- Enough VRAM for the selected model.

## Model starting points

| GPU VRAM | Recommended model | Notes |
| --- | --- | --- |
| 4-6 GB | `google/gemma-2-2b-it` | Tight fit. Useful only for smoke-testing the API swap. |
| 12-16 GB | `google/gemma-2-9b-it` | Comfortable default for the compose file. |
| 24 GB+ | `google/gemma-2-27b-it` or `Qwen/Qwen2.5-14B-Instruct` | Realistic sovereign size. |

## Run

```bash
docker compose -f deploy/vllm/docker-compose.yml up -d --build
```

The app service receives `LLM_BASE_URL=http://vllm:8080/v1`, so the existing
OpenAI-compatible client is reused.
