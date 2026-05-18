#!/usr/bin/env bash
# Hook: PostToolUse (matcher: Edit|Write)
# Formats the file Claude just touched, if a formatter is available.
set -euo pipefail

payload=$(cat)
file=$(echo "$payload" | jq -r '.tool_input.file_path // empty')
[ -z "$file" ] || [ ! -f "$file" ] && exit 0

case "$file" in
  *.ts|*.tsx|*.js|*.jsx|*.json|*.md|*.css|*.html|*.yaml|*.yml)
    command -v npx >/dev/null 2>&1 && npx --no-install prettier --write "$file" 2>/dev/null || true
    ;;
esac
exit 0
