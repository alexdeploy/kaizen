#!/usr/bin/env bash
# kaizen :: dependency-changed
#
# Hook: PostToolUse (matcher: Edit|Write)
# Self-filters to dependency manifest files only.
# When a manifest changes, prints a one-line reminder to consider re-auditing.
# Does NOT run any audit itself — purely informational.

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
file_path=$(echo "$payload" | jq -r '.tool_input.file_path // empty' 2>/dev/null)

[ -z "$file_path" ] && exit 0

# Only react to dependency manifest files
case "$(basename "$file_path")" in
  package.json|pnpm-lock.yaml|yarn.lock|package-lock.json|bun.lockb)
    manifest_kind="JS/TS dependencies"
    suggested_audit="npm audit, or \`/kaizen:bump\` for version-change analysis"
    ;;
  pyproject.toml|requirements.txt|Pipfile|Pipfile.lock|poetry.lock|uv.lock)
    manifest_kind="Python dependencies"
    suggested_audit="pip-audit (if installed), or \`/kaizen:bump\` for version-change analysis"
    ;;
  Cargo.toml|Cargo.lock)
    manifest_kind="Rust dependencies"
    suggested_audit="cargo audit (if installed), or \`/kaizen:bump\` for version-change analysis"
    ;;
  go.mod|go.sum)
    manifest_kind="Go dependencies"
    suggested_audit="govulncheck (if installed), or review the diff manually"
    ;;
  Gemfile|Gemfile.lock)
    manifest_kind="Ruby dependencies"
    suggested_audit="bundler-audit (if installed)"
    ;;
  *)
    # Not a manifest we recognize — silent skip
    exit 0
    ;;
esac

# Print a single informational line to stdout (Claude will see it as hook output)
echo "ℹ kaizen: $manifest_kind manifest changed ($(basename "$file_path"))."
echo "  Consider: @dependency-auditor for audit, or $suggested_audit"
exit 0
