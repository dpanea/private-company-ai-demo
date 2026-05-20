#!/usr/bin/env sh
set -eu

uv run company-ai migrate
uv run company-ai bootstrap-demo

exec "$@"
