#!/usr/bin/env sh
set -eu

if [ ! -f .env ]; then
  echo "Missing .env. Copy .env.example, set real values, and rerun." >&2
  exit 1
fi

docker compose pull postgres
docker compose up -d --build
docker compose ps
