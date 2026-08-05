#!/usr/bin/env bash
# kaizen :: validation harness entrypoint
#
#   tests/run.sh                 # all deterministic suites (seconds, free)
#   tests/run.sh -v              # print every passing check
#   tests/run.sh --only skills   # one suite
#   tests/run.sh --list          # suite names
#   tests/run.sh --live          # also run the LLM behaviour evals (costs tokens)
#
# Exit 0 = every invariant holds. Exit 1 = at least one failed.
# Warnings never fail the run; they are drift worth seeing, not breakage.

set -euo pipefail

TESTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PYTHON="${KZ_PYTHON:-}"
if [ -z "$PYTHON" ]; then
  for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
      PYTHON="$candidate"
      break
    fi
  done
fi

if [ -z "$PYTHON" ]; then
  echo "✗ python3 not found. The harness needs Python 3.7+ (stdlib only)." >&2
  echo "  Override the interpreter with KZ_PYTHON=/path/to/python3" >&2
  exit 2
fi

# --live is handled here; everything else is passed through to the runner.
run_live=0
args=()
for arg in "$@"; do
  if [ "$arg" = "--live" ]; then
    run_live=1
  else
    args+=("$arg")
  fi
done

status=0
"$PYTHON" "$TESTS_DIR/lib/runner.py" ${args[@]+"${args[@]}"} || status=$?

if [ "$run_live" -eq 1 ]; then
  echo
  "$TESTS_DIR/live/run-live.sh" || status=$?
fi

exit "$status"
