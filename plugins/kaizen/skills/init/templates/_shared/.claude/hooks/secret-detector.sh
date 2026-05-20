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

set -euo pipefail

payload=$(cat)

# Extract intended write content. Edit and Write tools have different shapes:
# - Write: tool_input.content
# - Edit:  tool_input.new_string
content=$(echo "$payload" | jq -r '.tool_input.content // .tool_input.new_string // empty' 2>/dev/null)
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
if echo "$filtered" | grep -q -- '-----BEGIN \(RSA \|EC \|OPENSSH \|DSA \|PRIVATE\) KEY-----'; then
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
