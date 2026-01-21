#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

PORT="${PIBUCKET_PORT:-8081}"
exec .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT"

