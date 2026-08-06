#!/usr/bin/env bash
# kaizen :: secret-detector
#
# Hook: PreToolUse (matcher: Edit|Write)
# Scans the file content Claude is about to write for likely secrets.
# Exit 2 BLOCKS the write with an explanation on stderr.
#
# Detects (heuristics, no false-positive-free guarantee):
#   - AWS access keys: AKIA[0-9A-Z]{16}
#   - GitHub PATs:     ghp_/ghs_/gho_/ghu_/ghr_ + 36 chars
#   - Generic API keys/tokens with high-entropy strings near suggestive variable names
#   - JWT tokens (3 base64url segments separated by dots)
#   - Private key PEM blocks
#
# Skip-by-marker: lines with `# noqa: secret` or `// noqa: secret` are not flagged.

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

# Extract intended write content. Edit and Write tools have different shapes:
# - Write: tool_input.content
# - Edit:  tool_input.new_string
# Both fields, via payload_field so this works without jq. A secret detector
# that silently scans nothing is worse than no secret detector at all.
content=$(payload_field "$payload" "tool_input.content")
[ -n "$content" ] || content=$(payload_field "$payload" "tool_input.new_string")
file_path=$(echo "$payload" | jq -r '.tool_input.file_path // empty' 2>/dev/null)

# Skip if no content (no risk) or if file is itself a known-public template
[ -z "$content" ] && exit 0
case "$file_path" in
  *.env.example|*.env.sample|*/secrets.example/*) exit 0 ;;
  */node_modules/*|*/.venv/*|*/dist/*|*/build/*) exit 0 ;;
esac

# Build a filtered version that strips noqa-marked lines, so we don't flag those.
filtered=$(echo "$content" | grep -v -E '(noqa:\s*secret|kaizen-allow-secret)' || true)

found=()

# AWS access key
if echo "$filtered" | grep -E -q 'AKIA[0-9A-Z]{16}'; then
  found+=("AWS Access Key ID pattern (AKIA...)")
fi

# GitHub personal access tokens
if echo "$filtered" | grep -E -q '(ghp|ghs|gho|ghu|ghr)_[A-Za-z0-9]{36,}'; then
  found+=("GitHub PAT pattern (ghp_/ghs_/...)")
fi

# JWT tokens (rough heuristic)
if echo "$filtered" | grep -E -q '\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b'; then
  found+=("JWT token")
fi

# Private key blocks
# Real PEM headers put the algorithm BEFORE "PRIVATE KEY", e.g.
# -----BEGIN RSA PRIVATE KEY-----. The previous pattern demanded
# "BEGIN RSA KEY-----", which no tool ever emits, so it matched nothing.
if echo "$filtered" | grep -qE -- '-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----'; then
  found+=("Private key (PEM block)")
fi

# Suggestive var-name + long opaque value, e.g. SECRET="x..." or apiKey: "x..."
# Catches: api[_-]?key, secret, token, password, auth[_-]?token paired with >=20-char opaque strings
suspicious_assignment=$(echo "$filtered" | grep -E -i '(api[_-]?key|secret|token|password|auth[_-]?token)\s*[:=]\s*[''"]?[A-Za-z0-9+/=_-]{20,}' || true)
if [ -n "$suspicious_assignment" ]; then
  found+=("Likely credential assignment (key/secret/token/password = '...')")
fi

# Report and block if anything found
if [ ${#found[@]} -gt 0 ]; then
  {
    echo "✗ kaizen secret-detector BLOCKED this write to: $file_path"
    echo ""
    echo "Detected likely secret(s):"
    for item in "${found[@]}"; do
      echo "  - $item"
    done
    echo ""
    echo "If this is a false positive, you can:"
    echo "  - Add a same-line marker: '# noqa: secret' or '// noqa: secret'"
    echo "  - Move the value to an env var / vault / .env file (and add to .gitignore)"
    echo "  - For truly public example values, name the file *.env.example"
  } >&2
  exit 2
fi

exit 0
