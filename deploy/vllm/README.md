# Sovereign vLLM deployment

This compose file runs the same app against a local OpenAI-compatible vLLM
server instead of a hosted chat-completions provider. Use it when a client or
prospect wants inference inside their own server, private cloud, or EU-controlled
environment.

The public demo does not use this path; it is included so the private deployment
story is concrete and testable.

Embeddings still use the configured hosted embedding endpoint unless you point
`EMBEDDING_MODEL` and `LLM_BASE_URL` at an embedding-capable local service. Treat
that as a separate production integration decision.

## Requirements

- Linux host with NVIDIA drivers.
- Docker with the NVIDIA container runtime.
- A `.env` file at the repository root with the normal demo variables plus
  `LLM_MODEL_VLLM`.
- Enough GPU VRAM for the selected model, KV cache, CUDA graphs, and runtime
  overhead.
- For gated Hugging Face models such as Google Gemma, accept the model license
  on Hugging Face and set `HF_TOKEN` or `HUGGING_FACE_HUB_TOKEN` in `.env`.

## Current model starting points

These are conservative single-GPU starting points for the compose defaults:
`VLLM_MAX_MODEL_LEN=8192`, `VLLM_MAX_NUM_SEQS=4`, and
`VLLM_GPU_MEMORY_UTILIZATION=0.90`. The sizing estimate is:

`required VRAM ≈ model weights + KV cache + 10-20% runtime overhead`

For BF16 weights, count roughly 2 bytes per parameter. For FP8 checkpoints,
count roughly 1 byte for FP8 tensors plus BF16 for the remaining tensors. KV
cache scales with context length, concurrency, number of layers, KV heads, and
`VLLM_KV_CACHE_DTYPE`; halving `VLLM_MAX_MODEL_LEN` roughly halves the KV-cache
need.

| GPU VRAM | Recommended model | Sizing notes |
| --- | --- | --- |
| 4-6 GB | `Qwen/Qwen3-1.7B` | Smoke-test tier only. BF16 weights are ~3.8 GiB; 8k KV cache is ~0.9 GiB with BF16 or ~0.4 GiB with FP8. On 4 GB, lower `VLLM_MAX_MODEL_LEN` to 4096. |
| 8-12 GB | `Qwen/Qwen3-4B` | Practical low-end default. BF16 weights are ~7.5 GiB; 8k KV cache is ~1.1 GiB BF16 or ~0.6 GiB FP8. |
| 12-16 GB | `google/gemma-4-E2B-it` or `Qwen/Qwen3-4B` | Small Gemma 4 tier. Gemma 4 E2B has ~5.1B BF16 parameters, so weights are ~9.5 GiB despite the E2B name. |
| 24 GB | `google/gemma-4-E4B-it` or `Qwen/Qwen3.5-9B` | Good demo-quality tier. Gemma 4 E4B weights are ~14.9 GiB; Qwen3.5 9B weights are ~18.0 GiB. Both leave room for 8k context and modest batching. |
| 32-48 GB | `google/gemma-4-12B-it`; `Qwen/Qwen3.6-27B-FP8` on 40-48 GB | Gemma 4 12B is ~22.3 GiB BF16 plus ~3.0 GiB BF16 KV at 8k. Qwen3.6 27B BF16 needs ~52 GiB just for weights; use the FP8 checkpoint (~28.7 GiB) for this tier. |
| 64 GB+ | `google/gemma-4-26B-A4B-it` or `Qwen/Qwen3.6-35B-A3B-FP8` | Realistic stronger sovereign tier. Gemma 4 26B-A4B has ~48.1 GiB BF16 weights; Qwen3.6 35B-A3B-FP8 has ~34.9 GiB FP8/BF16 weights. |
| 80 GB+ | `google/gemma-4-31B-it` | High-end single-GPU tier. BF16 weights are ~58.3 GiB and 8k BF16 KV cache is ~7.5 GiB before overhead. |

Notes:

- `Qwen/Qwen3-4B` is the safest default because it is small, current, and does
  not require a gated-model token.
- Google Gemma models can be excellent choices, but the Hugging Face license
  gate makes `HF_TOKEN` setup part of the deployment.
- Do not use old 27B BF16 models as a casual 24 GB recommendation. BF16 weights
  alone are usually above 50 GiB for that class.
- If a model barely fits, reduce `VLLM_MAX_MODEL_LEN`, reduce
  `VLLM_MAX_NUM_SEQS`, or set `VLLM_KV_CACHE_DTYPE=fp8` on hardware where vLLM
  supports FP8 KV cache reliably.

## Run

```bash
docker compose -f deploy/vllm/docker-compose.yml up -d --build
```

The app service receives `LLM_BASE_URL=http://vllm:8080/v1`, so the existing
OpenAI-compatible client is reused. `LLM_MODEL` inside the app is set from
`LLM_MODEL_VLLM`, so the model name sent by the app matches the model served by
vLLM.

## Useful `.env` overrides

```dotenv
# Safe low-end default
LLM_MODEL_VLLM=Qwen/Qwen3-4B

# Required for gated Hugging Face models such as google/gemma-4-*
HF_TOKEN=
# HUGGING_FACE_HUB_TOKEN= also works if your environment standardizes on it.

# vLLM sizing knobs
VLLM_MAX_MODEL_LEN=8192
VLLM_MAX_NUM_SEQS=4
VLLM_MAX_NUM_BATCHED_TOKENS=2048
VLLM_GPU_MEMORY_UTILIZATION=0.90
VLLM_KV_CACHE_DTYPE=auto
```
