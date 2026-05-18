#!/usr/bin/env bash
# Hook: SessionStart — injects fresh repo state into Claude's initial context.
set -euo pipefail
cd "${CLAUDE_PROJECT_DIR:-.}"

echo "## Repo state at session start"
echo ""
echo "**Branch:** $(git branch --show-current 2>/dev/null || echo 'no git')"

if git rev-parse --git-dir > /dev/null 2>&1; then
  modified=$(git status --porcelain 2>/dev/null | head -20)
  if [ -n "$modified" ]; then
    echo ""
    echo "**Modified (top 20):**"
    echo '```'
    echo "$modified"
    echo '```'
  fi
fi
