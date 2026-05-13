# Sovereign vLLM deployment

This compose file runs the same app against a local OpenAI-compatible vLLM server instead of OpenRouter for chat completions. The public demo does not use this path; it exists to make the sovereign deployment option concrete.

Embeddings still use the configured OpenRouter-compatible embedding endpoint unless you set `EMBEDDING_MODEL` and `OPENROUTER_BASE_URL` to an embedding-capable local service. Treat that as an integration decision for a real deployment.

## Requirements

- Linux host with NVIDIA drivers.
- Docker with the NVIDIA container runtime.
- A `.env` file at the repository root with the normal demo variables plus `LLM_MODEL_VLLM`.
- Enough VRAM for the selected model.

## Model starting points

| GPU VRAM | Recommended model | Notes |
| --- | --- | --- |
| 4-6 GB | `google/gemma-2-2b-it` | Tight fit. Useful only for smoke-testing the API swap. Use AWQ or a llama.cpp path if needed. |
| 12-16 GB | `google/gemma-2-9b-it` | Comfortable default for the compose file. |
| 24 GB+ | `google/gemma-2-27b-it` or `Qwen/Qwen2.5-14B-Instruct` | Realistic production sovereign size. |

## Run

```bash
docker compose -f deploy/vllm/docker-compose.yml up -d --build
```

Then open the same URL used by the main app. The app service receives `OPENROUTER_BASE_URL=http://vllm:8080/v1`, so the existing OpenAI-compatible client is reused.

Before publishing the repository, Daniel should run this once on real GPU hardware and add a screenshot or short recording to the README and launch post.
