#!/usr/bin/env bash
# kaizen :: live behaviour evals
#
# Runs the plugin for real — a headless Claude Code session per scenario, in a
# throwaway copy of a fixture — and asserts on what landed on disk.
#
# This is the only layer that can catch a SKILL.md regression, and the only one
# that costs tokens and wall-clock. It is opt-in for that reason:
#
#   tests/run.sh --live          # deterministic suites, then these
#   tests/live/run-live.sh       # just these
#
# Env:
#   KZ_CLAUDE_BIN    claude binary (default: claude on PATH)
#   KZ_LIVE_MODEL    model override passed to --model
#   KZ_LIVE_ONLY     run a single scenario by name
#   KZ_LIVE_KEEP=1   keep the temp project dirs for inspection
#   KZ_LIVE_TIMEOUT  per-scenario seconds (default 600)
#   KZ_LIVE_PERMISSION_MODE
#                    --permission-mode for the session (default acceptEdits).
#                    Unattended runs may need bypassPermissions; that is only
#                    reasonable because every scenario runs in a throwaway
#                    temp dir, never in a real project.

set -uo pipefail

LIVE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TESTS_DIR="$(dirname "$LIVE_DIR")"
REPO_ROOT="$(dirname "$TESTS_DIR")"
PLUGIN_DIR="$REPO_ROOT/plugins/kaizen"

CLAUDE_BIN="${KZ_CLAUDE_BIN:-claude}"
TIMEOUT_SECS="${KZ_LIVE_TIMEOUT:-600}"
PYTHON="${KZ_PYTHON:-python3}"
# bypassPermissions, not acceptEdits: acceptEdits refuses writes under .claude/**,
# which is the entire output of /kaizen:init — a live run under acceptEdits
# produces CLAUDE.md and nothing else, and looks like a product failure. Safe
# here because every scenario runs in a throwaway temp copy, never a real repo.
# Verified against a real project (pnpm monorepo) on 2026-08-06.
PERMISSION_MODE="${KZ_LIVE_PERMISSION_MODE:-bypassPermissions}"

# scenario name | fixture | prompt | profile
SCENARIOS=(
  "init-standard-ts|typescript-node|/kaizen:init --profile=standard|standard"
  "init-advanced-py|python-uv|/kaizen:init --profile=advanced|advanced"
)

bold() { printf '\033[1m%s\033[0m\n' "$1"; }
dim()  { printf '\033[2m%s\033[0m\n' "$1"; }
red()  { printf '\033[31m%s\033[0m\n' "$1"; }
green(){ printf '\033[32m%s\033[0m\n' "$1"; }

if ! command -v "$CLAUDE_BIN" >/dev/null 2>&1; then
  red "✗ '$CLAUDE_BIN' not found on PATH."
  echo "  The live layer needs the Claude Code CLI. Set KZ_CLAUDE_BIN to override."
  exit 2
fi

bold ""
bold "kaizen :: live behaviour evals"
dim  "  binary: $(command -v "$CLAUDE_BIN")"
dim  "  plugin: $PLUGIN_DIR"
dim  "  these spawn real sessions and consume tokens"
echo

failures=0
unusable=0
ran=0

for scenario in "${SCENARIOS[@]}"; do
  IFS='|' read -r name fixture prompt profile <<< "$scenario"

  if [ -n "${KZ_LIVE_ONLY:-}" ] && [ "$name" != "$KZ_LIVE_ONLY" ]; then
    continue
  fi

  source_dir="$TESTS_DIR/fixtures/$fixture"
  if [ ! -d "$source_dir" ]; then
    red "✗ $name: fixture '$fixture' not found"
    failures=$((failures + 1))
    continue
  fi

  workdir="$(mktemp -d "${TMPDIR:-/tmp}/kaizen-live-XXXXXX")"
  project="$workdir/$fixture"
  cp -R "$source_dir" "$project"
  rm -f "$project/expected.json" "$project/fixture.json"

  # A real repo: several skills refuse without git, and /init reads its state.
  git -C "$project" init -q -b main
  git -C "$project" -c user.email=harness@kaizen.test -c user.name="kaizen harness" \
      add -A >/dev/null 2>&1
  git -C "$project" -c user.email=harness@kaizen.test -c user.name="kaizen harness" \
      commit -q -m "fixture: initial" >/dev/null 2>&1

  ls -A "$project" > "$workdir/baseline.txt"

  bold "▸ $name"
  dim  "  prompt:  $prompt"
  dim  "  project: $project"

  model_args=()
  [ -n "${KZ_LIVE_MODEL:-}" ] && model_args=(--model "$KZ_LIVE_MODEL")

  start=$(date +%s)
  ( cd "$project" && \
    "$CLAUDE_BIN" -p "$prompt" \
      --plugin-dir "$PLUGIN_DIR" \
      --permission-mode "$PERMISSION_MODE" \
      --add-dir "$project" \
      ${model_args[@]+"${model_args[@]}"} \
  ) > "$workdir/stdout.txt" 2> "$workdir/stderr.txt" &
  session_pid=$!

  elapsed=0
  while kill -0 "$session_pid" 2>/dev/null; do
    sleep 2
    elapsed=$((elapsed + 2))
    if [ "$elapsed" -ge "$TIMEOUT_SECS" ]; then
      kill -9 "$session_pid" 2>/dev/null
      red "  ✗ timed out after ${TIMEOUT_SECS}s"
      break
    fi
  done
  wait "$session_pid"
  session_status=$?
  duration=$(( $(date +%s) - start ))

  dim "  session finished in ${duration}s"

  # An unusable session (quota, auth, network) is NOT a product regression.
  # Reporting it as one would teach everyone to ignore a red live run.
  scenario_unusable=0
  if grep -qiE "session limit|usage limit|rate limit|credit balance" \
        "$workdir/stdout.txt" "$workdir/stderr.txt" 2>/dev/null; then
    scenario_unusable=1
    red "  ⚠ session could not complete: usage/rate limit reached"
    tail -1 "$workdir/stdout.txt" | sed 's/^/      /'
  elif [ "$session_status" -ne 0 ]; then
    scenario_unusable=1
    red "  ⚠ session exited $session_status before finishing"
    tail -3 "$workdir/stderr.txt" | sed 's/^/      /'
  fi

  echo "  assertions (partial if the session did not finish):"
  assert_status=0
  "$PYTHON" "$LIVE_DIR/assert_init.py" "$project" "$profile" \
        --stdout "$workdir/stdout.txt" \
        --baseline "$workdir/baseline.txt" || assert_status=$?

  if [ "$scenario_unusable" -eq 1 ]; then
    red "  $name INCONCLUSIVE — rerun when the session can complete"
    unusable=$((unusable + 1))
  elif [ "$assert_status" -ne 0 ]; then
    red "  $name failed"
    failures=$((failures + 1))
  else
    green "  $name passed"
  fi

  ran=$((ran + 1))

  if [ "${KZ_LIVE_KEEP:-0}" = "1" ]; then
    dim "  kept: $workdir"
  else
    rm -rf "$workdir"
  fi
  echo
done

if [ "$ran" -eq 0 ]; then
  red "no scenarios ran (KZ_LIVE_ONLY=${KZ_LIVE_ONLY:-} matched nothing)"
  exit 2
fi

if [ "$failures" -gt 0 ]; then
  red "live evals: $failures of $ran failed"
  exit 1
fi

if [ "$unusable" -gt 0 ]; then
  red "live evals: $unusable of $ran inconclusive (session could not complete)"
  # Exit 3, not 1: nothing was proven broken, and nothing was proven correct.
  exit 3
fi

green "live evals: $ran/$ran passed"
