#!/usr/bin/env bash
# Hook: PostToolUse (matcher: Edit|Write)
# Formats the file Claude just touched, if a formatter is available.
# A hook must never fail the user's session. `set -e` is deliberately absent:
# these scripts branch on commands that legitimately return non-zero.
set -uo pipefail

# Read a field from the hook payload without requiring jq: jq when present,
# python3 next, sed last. A formatter hook that errors on every edit because jq
# is missing is worse than no hook at all.
payload_field() { # payload_field <json> <dotted.path>
  local json="$1" path="$2" value=""
  if command -v jq >/dev/null 2>&1; then
    value=$(printf '%s' "$json" | jq -r ".$path // empty" 2>/dev/null)
  fi
  if [ -z "$value" ] && command -v python3 >/dev/null 2>&1; then
    value=$(printf '%s' "$json" | python3 -c '
import json, sys
try:
    node = json.load(sys.stdin)
except Exception:
    sys.exit(0)
for key in sys.argv[1].split("."):
    if not isinstance(node, dict):
        sys.exit(0)
    node = node.get(key)
print(node if isinstance(node, str) else "")
' "$path" 2>/dev/null)
  fi
  if [ -z "$value" ]; then
    value=$(printf '%s' "$json" \
      | sed -n "s/.*\"${path##*.}\"[[:space:]]*:[[:space:]]*\"\([^\"]*\)\".*/\1/p" \
      | head -1)
  fi
  printf '%s' "$value"
}

payload=$(cat)
file=$(payload_field "$payload" "tool_input.file_path")
[ -z "$file" ] || [ ! -f "$file" ] && exit 0

case "$file" in
  *.ts|*.tsx|*.js|*.jsx|*.json|*.md|*.css|*.html|*.yaml|*.yml)
    command -v npx >/dev/null 2>&1 && npx --no-install prettier --write "$file" 2>/dev/null || true
    ;;
esac
exit 0
