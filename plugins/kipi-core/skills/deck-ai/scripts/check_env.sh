#!/usr/bin/env bash
# Runtime preflight for deck-ai. Verifies:
#   - UNSPLASH_ACCESS_KEY is set (reads from .env in caller CWD if present)
#   - python3 + python-pptx are importable
#
# Usage:
#   bash scripts/check_env.sh

set -euo pipefail

if [ -f "./.env" ]; then
  set -a
  # shellcheck disable=SC1091
  . "./.env"
  set +a
fi

missing=0

if [ -z "${UNSPLASH_ACCESS_KEY:-}" ]; then
  echo "MISSING: UNSPLASH_ACCESS_KEY. Add it to ./.env:" >&2
  echo "  echo 'UNSPLASH_ACCESS_KEY=<your-key>' >> ./.env" >&2
  missing=1
fi

if ! python3 -c "import pptx" 2>/dev/null; then
  echo "MISSING: python-pptx. Install with:" >&2
  echo "  python3 -m pip install python-pptx" >&2
  missing=1
fi

if [ "$missing" -ne 0 ]; then
  exit 1
fi

echo "[deck-ai check_env] OK"
