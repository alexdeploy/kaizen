#!/usr/bin/env bash
# kaizen :: Stop — the only nudge kaizen gives
#
# Fires:   when Claude finishes a turn
# Payload: stdin JSON — includes session_id
# Exit 0 always. Never blocks, never writes into the project.
#
# Suggests `/kaizen:finish` when source files have changed and no pre-merge
# check has run since. That is the whole behaviour.
#
# Two properties it must keep, or it becomes the reason people uninstall:
#   1. **Once per session.** The marker lives in the temp dir, keyed by session
#      id — nothing is written into the user's project to track this.
#   2. **Silent unless there is real work to flag.** No changed source files, or
#      a fresh verdict already exists → say nothing at all.
#
# KAIZEN_NUDGE=off disables it.

set -uo pipefail

payload=$(cat)

[ "${KAIZEN_NUDGE:-on}" = "off" ] && exit 0

cd "${CLAUDE_PROJECT_DIR:-$PWD}" 2>/dev/null || exit 0
git rev-parse --git-dir >/dev/null 2>&1 || exit 0

# --- once per session ---------------------------------------------------------
session_id=$(printf '%s' "$payload" \
  | sed -n 's/.*"session_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)
[ -n "$session_id" ] || session_id="nosession"
marker="${TMPDIR:-/tmp}/kaizen-nudge-$(printf '%s' "$session_id" | tr -c 'a-zA-Z0-9' '_')"
[ -f "$marker" ] && exit 0

# --- is there source work to flag? --------------------------------------------
changed=$(git status --porcelain 2>/dev/null \
  | grep -cE '\.(ts|tsx|js|jsx|vue|svelte|py|go|rs|rb|php|java|kt|swift|c|cpp|h)$' \
  || true)
[ "${changed:-0}" -gt 0 ] || exit 0

# --- has a pre-merge check already run since those changes? -------------------
for report in .claude/kaizen/finish-report.md .claude/kaizen/preflight-report.md; do
  if [ -f "$report" ]; then
    stale=$(find . -newer "$report" -type f \
      \( -name '*.ts' -o -name '*.tsx' -o -name '*.js' -o -name '*.jsx' \
      -o -name '*.py' -o -name '*.go' -o -name '*.rs' -o -name '*.vue' \) \
      -not -path './node_modules/*' -not -path './.git/*' 2>/dev/null | head -1)
    [ -z "$stale" ] && exit 0    # verdict is newer than every source change
  fi
done

touch "$marker" 2>/dev/null || true

printf 'kaizen: %s source file(s) changed and no pre-merge check has run since. `/kaizen:finish` when you are ready to close this out.\n' \
  "$changed"
exit 0
