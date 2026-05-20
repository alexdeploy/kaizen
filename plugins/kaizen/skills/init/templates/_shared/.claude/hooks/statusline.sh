#!/usr/bin/env bash
# kaizen :: statusline
#
# Single-line status shown at the bottom of Claude Code's TUI.
# Read periodically by Claude Code — must be fast (<100ms target).
# Receives session JSON on stdin; outputs to stdout (first line only is rendered).
#
# Shows: [model] dir ⎇ branch [kaizen state segment] [modified count]
#
# Kaizen state segment surfaces:
#   ✓/⚠/✗ <SHIP|HOLD|BLOCK>   — last /kaizen:finish verdict (from finish-report.md)
#   ⚠ learn pending           — when .claude/kaizen/pending.md exists
#   📋 N plan(s)              — count of plan files modified in last 7 days
#
# Docs: https://code.claude.com/docs/en/statusline

set -euo pipefail

# -- session payload (model + cwd) ----------------------------------------

payload=$(cat 2>/dev/null || echo '{}')
model="claude"
cwd_dir="$(basename "$(pwd)")"

if command -v jq >/dev/null 2>&1; then
  m=$(echo "$payload" | jq -r '.model.display_name // .model // empty' 2>/dev/null)
  [ -n "$m" ] && model="$m"
  c=$(echo "$payload" | jq -r '.workspace.current_dir // .cwd // empty' 2>/dev/null)
  [ -n "$c" ] && cwd_dir="$(basename "$c")"
fi

# -- git branch -----------------------------------------------------------

branch=""
if git rev-parse --git-dir >/dev/null 2>&1; then
  cb=$(git branch --show-current 2>/dev/null)
  [ -n "$cb" ] && branch=" ⎇ $cb"
fi

# -- kaizen state segment -------------------------------------------------

kaizen_parts=()

# Last /finish verdict
if [ -f .claude/kaizen/finish-report.md ]; then
  verdict=$(grep -m1 '^## Verdict:' .claude/kaizen/finish-report.md 2>/dev/null | sed 's/^## Verdict: //' | awk '{print $1}')
  case "$verdict" in
    SHIP) kaizen_parts+=("✓ SHIP") ;;
    HOLD) kaizen_parts+=("⚠ HOLD") ;;
    BLOCK) kaizen_parts+=("✗ BLOCK") ;;
  esac
fi

# Pending /learn proposals
[ -f .claude/kaizen/pending.md ] && kaizen_parts+=("⚠ learn pending")

# Recent plans (last 7 days)
if [ -d .claude/kaizen/plans ]; then
  recent_plans=$(find .claude/kaizen/plans -name "*.md" -mtime -7 2>/dev/null | wc -l | tr -d ' ')
  [ "${recent_plans:-0}" -gt 0 ] && kaizen_parts+=("📋 ${recent_plans} plan(s)")
fi

kaizen_segment=""
if [ ${#kaizen_parts[@]} -gt 0 ]; then
  joined=""
  for part in "${kaizen_parts[@]}"; do
    [ -z "$joined" ] && joined="$part" || joined="$joined · $part"
  done
  kaizen_segment="  ${joined}"
fi

# -- modified files (git) -------------------------------------------------

modified_segment=""
if git rev-parse --git-dir >/dev/null 2>&1; then
  count=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
  [ "${count:-0}" -gt 0 ] && modified_segment="  ·  ${count} modified"
fi

# -- compose final line ---------------------------------------------------

echo "[${model}] ${cwd_dir}${branch}${kaizen_segment}${modified_segment}"
