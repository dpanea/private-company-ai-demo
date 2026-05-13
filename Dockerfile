FROM python:3.11-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    cp /root/.local/bin/uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/
COPY sql/ ./sql/
COPY scripts/ ./scripts/
COPY data/synthetic/ ./data/synthetic/

RUN uv sync --frozen --no-dev

EXPOSE 8000

ENTRYPOINT ["scripts/docker_entrypoint.sh"]
CMD ["uv", "run", "uvicorn", "pcad.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
