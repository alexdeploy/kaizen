#!/usr/bin/env bash
# kaizen :: SessionStart — tell Claude where it is picking up from
#
# Fires:   when a session begins or resumes
# Payload: stdin JSON — matcher: startup | resume | clear
# Exit 0.  stdout is injected into the session as context.
#
# The job is to answer, in as few tokens as possible, the questions Claude would
# otherwise spend a tool call each discovering: what branch is this, is the tree
# dirty, did the last pre-merge check pass, is there anything waiting.
#
# **Silent when there is nothing to say.** A hook that prints on every session
# becomes noise, and noise in the context window is not free.

set -uo pipefail

cat >/dev/null   # consume the payload; nothing in it is needed

cd "${CLAUDE_PROJECT_DIR:-$PWD}" 2>/dev/null || exit 0
git rev-parse --git-dir >/dev/null 2>&1 || exit 0

lines=()

branch=$(git branch --show-current 2>/dev/null)
modified=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
if [ -n "$branch" ]; then
  if [ "$modified" -gt 0 ]; then
    lines+=("branch \`$branch\`, $modified uncommitted file(s)")
  else
    lines+=("branch \`$branch\`, clean tree")
  fi
fi

# The last pre-merge verdict, but only while it still describes the current work.
report=".claude/kaizen/finish-report.md"
[ -f "$report" ] || report=".claude/kaizen/preflight-report.md"
if [ -f "$report" ]; then
  verdict=$(grep -m1 -oE '\b(SHIP|HOLD|BLOCK)\b' "$report" 2>/dev/null || true)
  if [ -n "$verdict" ]; then
    newer=$(find . -newer "$report" -type f \
      \( -name '*.ts' -o -name '*.tsx' -o -name '*.js' -o -name '*.jsx' \
      -o -name '*.py' -o -name '*.go' -o -name '*.rs' -o -name '*.vue' \) \
      -not -path './node_modules/*' -not -path './.git/*' 2>/dev/null | head -1)
    if [ -n "$newer" ]; then
      lines+=("last $verdict verdict is stale — source changed since it ran")
    else
      lines+=("last pre-merge verdict: $verdict")
    fi
  fi
fi

[ -f ".claude/kaizen/pending.md" ] && \
  lines+=("\`/kaizen:learn\` proposals are pending — show, apply or discard them")

# Config generated against an older catalog than the one installed.
if [ -f ".claude/kaizen/lock.json" ] && command -v kaizen-standards >/dev/null 2>&1; then
  locked=$(sed -n 's/.*"standards_version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' \
    .claude/kaizen/lock.json | head -1)
  current=$(kaizen-standards version 2>/dev/null \
    | sed -n 's/.*"standards_version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)
  if [ -n "$locked" ] && [ -n "$current" ] && [ "$locked" != "$current" ] \
     && [ "$locked" != "unset" ]; then
    lines+=("config was generated against standards@$locked, catalog is now $current — \`/kaizen:upgrade\` to see what changed")
  fi
fi

[ ${#lines[@]} -eq 0 ] && exit 0

printf 'kaizen:\n'
for line in "${lines[@]}"; do printf -- '- %s\n' "$line"; done
exit 0
