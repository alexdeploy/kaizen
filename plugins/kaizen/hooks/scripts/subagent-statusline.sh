#!/usr/bin/env bash
# kaizen :: subagent statusline
#
# Shown in the TUI while a subagent (Task tool) is actively running.
# Adds visibility during multi-agent dispatches (/preflight, /plan, /finish).
# Read by Claude Code with subagent context on stdin; outputs a single line.
#
# Receives via stdin: JSON with subagent identifier and optionally task description.
# Field names vary by Claude Code version — we try several with fallbacks.
#
# Docs: https://code.claude.com/docs/en/statusline#subagent-status-lines

set -euo pipefail

payload=$(cat 2>/dev/null || echo '{}')
agent_name="subagent"

if command -v jq >/dev/null 2>&1; then
  # Try common field names — gracefully fall back if absent
  candidate=$(echo "$payload" | jq -r '.subagent_type // .agent_name // .agent // .name // empty' 2>/dev/null)
  [ -n "$candidate" ] && agent_name="$candidate"
fi

# Map known kaizen agents to a more descriptive label
case "$agent_name" in
  preflight-security)  label="🔒 security review" ;;
  commit-suggester)    label="✎ commit suggestion" ;;
  versioner)           label="📦 version bump" ;;
  docs-keeper)         label="📚 doc gap check" ;;
  plan-context)        label="🗺  project context" ;;
  plan-decomposer)     label="📋 spec decomposition" ;;
  code-reviewer)       label="👁  code review" ;;
  *)                   label="🤖 ${agent_name}" ;;
esac

echo "${label} running…"
