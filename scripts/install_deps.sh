#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec "$ROOT/.venv/bin/python" -m pip install -r "$ROOT/requirements.txt"
