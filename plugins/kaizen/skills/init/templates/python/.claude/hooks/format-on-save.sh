#!/usr/bin/env bash
# Hook: PostToolUse (matcher: Edit|Write)
set -euo pipefail

payload=$(cat)
file=$(echo "$payload" | jq -r '.tool_input.file_path // empty')
[ -z "$file" ] || [ ! -f "$file" ] && exit 0

case "$file" in
  *.py)
    command -v ruff >/dev/null 2>&1 && ruff format "$file" 2>/dev/null || true
    ;;
esac
exit 0
