#!/usr/bin/env bash
# Perses interestingness test: accept a reduced candidate only if it still
# produces the same trace-sensitive crash summary as the original input.
#
# Perses stages this script next to the candidate in a temp dir, so the project
# root is taken from PESTO_PROJECT_ROOT (set by the reducer). The CLI is invoked
# as `python src/pesto/cli.py trace` with src/ added to PYTHONPATH.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"

# Determine the project root directory.
if [[ -n "${PESTO_PROJECT_ROOT:-}" ]]; then
  ROOT="$PESTO_PROJECT_ROOT"
elif [[ -f "$SCRIPT_DIR/../../../src/pesto/cli.py" ]]; then
  # In-place layout: src/pesto/data/test-script.sh -> project root is three up.
  ROOT="$(cd "$SCRIPT_DIR/../../.." >/dev/null 2>&1 && pwd)"
else
  echo "PESTO_PROJECT_ROOT is required when test-script.sh is copied outside the repo" >&2
  exit 2
fi

# Validate that trace sensitivity is a non-negative integer.
SENSITIVITY="${PESTO_TRACE_SENSITIVITY:-10}"
if [[ ! "$SENSITIVITY" =~ ^[0-9]+$ ]]; then
  echo "invalid trace sensitivity: $SENSITIVITY" >&2
  exit 2
fi

if [[ -z "${PESTO_TARGET_BASENAME:-}" ]]; then
  echo "PESTO_TARGET_BASENAME is required" >&2
  exit 2
fi

CANDIDATE="./$PESTO_TARGET_BASENAME"

if [[ ! -f "$CANDIDATE" ]]; then
  echo "candidate file does not exist: $CANDIDATE" >&2
  exit 1
fi

PYTHON_BIN="${PESTO_PYTHON:-python3}"
export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"

trace() {
  "$PYTHON_BIN" "$ROOT/src/pesto/cli.py" trace "$1" -s "$SENSITIVITY"
}

# Expected summary is the original program's stderr trace summary.
EXPECTED_SUMMARY="${PESTO_EXPECTED_SUMMARY:-}"
if [[ -z "$EXPECTED_SUMMARY" ]]; then
  if [[ -z "${PESTO_ORIGINAL_INPUT:-}" ]]; then
    echo "PESTO_EXPECTED_SUMMARY or PESTO_ORIGINAL_INPUT is required" >&2
    exit 2
  fi
  # If PESTO_EXPECTED_SUMMARY is not set, compute it from the original input.
  if ! EXPECTED_SUMMARY="$(trace "$PESTO_ORIGINAL_INPUT")"; then
    echo "failed to compute original summary for $PESTO_ORIGINAL_INPUT" >&2
    exit 1
  fi
fi

# Accept the candidate only if it preserves the exact same summary.
if ! CANDIDATE_SUMMARY="$(trace "$CANDIDATE")"; then
  exit 1
fi

if [[ "$CANDIDATE_SUMMARY" != "$EXPECTED_SUMMARY" ]]; then
  {
    echo "stderr summary mismatch"
    echo "expected: $EXPECTED_SUMMARY"
    echo "actual:   $CANDIDATE_SUMMARY"
  } >&2
  exit 1
fi
