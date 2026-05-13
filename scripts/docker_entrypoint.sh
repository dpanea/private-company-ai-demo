#!/usr/bin/env sh
set -eu

uv run pcad migrate
uv run pcad bootstrap-demo

exec "$@"
