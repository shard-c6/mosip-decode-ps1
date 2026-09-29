#!/usr/bin/env bash
#
# One-command conformance execution, as required by the problem statement.
#
#   ./run-conformance.sh --component verify
#   ./run-conformance.sh --component certify
#   ./run-conformance.sh --combined
#
# Deliberately thin: every argument is passed straight through to the Python
# runner, so there is no logic here worth testing separately.
#
# Exit status is the gate's verdict -- 0 when no module regressed against the
# recorded baseline, 1 when one did. That is what CI should fail on.

set -euo pipefail

cd "$(dirname "$0")"

PYTHON="${PYTHON:-python3}"

if ! "$PYTHON" -c "import httpx" 2>/dev/null; then
  echo "error: httpx is not installed. Run: $PYTHON -m pip install -r requirements.txt" >&2
  exit 2
fi

exec "$PYTHON" -m runner "$@"
