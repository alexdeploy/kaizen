#!/usr/bin/env bash
# kaizen :: PreToolUse — the safety net
#
# Fires:   before every Bash tool call (matcher: Bash)
# Payload: stdin JSON — tool_name + tool_input.command
# Exit 0 = allow.  Exit 2 = BLOCK, with the reason on stderr.
#
# This is the only kaizen hook that can stop something happening, so its bar is
# deliberately extreme: **a pattern belongs here only if no legitimate command
# could ever match it.** A safety net that fires on real work gets switched off,
# and then it protects nobody. `rm -rf node_modules` and `rm -rf dist` are normal
# and must pass; `rm -rf /` and `rm -rf ~` never are.
#
# Two tiers:
#   BLOCK — catastrophic and irreversible. Exit 2.
#   WARN  — legitimate sometimes, worth a second look. Exit 0 with a note.
#
# Escape hatch: KAIZEN_SAFETY=off disables it entirely. Documented, because a
# safety net nobody can remove is one people work around in worse ways.

set -uo pipefail

payload=$(cat)

[ "${KAIZEN_SAFETY:-on}" = "off" ] && exit 0

# --- extract the command ------------------------------------------------------
# python3 parses the JSON correctly; without it we scan the raw payload, which
# is coarser but never *misses* a dangerous command — it can only over-match,
# and the patterns below are narrow enough that over-matching is unlikely.
command_text=""
if command -v python3 >/dev/null 2>&1; then
  command_text=$(printf '%s' "$payload" | python3 -c '
import json, sys
try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)
value = (data.get("tool_input") or {}).get("command")
if isinstance(value, str):
    print(value)
' 2>/dev/null)
fi
[ -n "$command_text" ] || command_text="$payload"

# Collapse whitespace so `rm   -rf    /` reads like `rm -rf /`.
normalised=$(printf '%s' "$command_text" | tr '\n\t' '  ' | tr -s ' ')

block() {
  printf 'kaizen safety: refusing to run this command.\n\n  %s\n\n%s\n\n%s\n' \
    "$1" "$2" \
    "If this is genuinely what you want, run it yourself in a terminal, or set KAIZEN_SAFETY=off for this session." >&2
  exit 2
}

warn() {
  printf 'kaizen: %s\n' "$1"
}

# --- BLOCK: no legitimate command looks like this -----------------------------

# Recursive delete of the filesystem root or a bare home directory. Note the
# anchors: `rm -rf /` and `rm -rf /*` match, `rm -rf /home/me/project/dist`
# does not, and neither does `rm -rf ./dist` or `rm -rf node_modules`.
if printf '%s' "$normalised" | grep -qE '(^|[;&|] *)(sudo +)?rm +(-[a-zA-Z]* *)*-[a-zA-Z]*r[a-zA-Z]* +(-[a-zA-Z]+ +)*(/|/\*|~|~/|\$HOME|\$\{HOME\})( |$|;|&)'; then
  block "$normalised" \
    "This deletes the filesystem root or your entire home directory." \
    ""
fi

# Piping a network download straight into a shell: the classic supply-chain
# footgun. The script is never reviewed and can change between runs.
if printf '%s' "$normalised" | grep -qE '(curl|wget)[^|]*\| *(sudo +)?(ba|z|k|fi)?sh( |$|;|&)'; then
  block "$normalised" \
    "This pipes a downloaded script straight into a shell — nothing gets reviewed, and the remote content can change between runs." \
    ""
fi

# World-writable, recursively, from the root or home.
if printf '%s' "$normalised" | grep -qE '(^|[;&|] *)(sudo +)?chmod +(-[a-zA-Z]+ +)*-?R[a-zA-Z]* +777 +(/|~|\$HOME)( |$|;|&)'; then
  block "$normalised" \
    "This makes the filesystem root or your home directory world-writable." \
    ""
fi

# git clean at the repository root wiping ignored files including .env
if printf '%s' "$normalised" | grep -qE 'git +clean +(-[a-zA-Z]* )*-[a-zA-Z]*x[a-zA-Z]*'; then
  block "$normalised" \
    "git clean -x deletes ignored files too — including .env files and local credentials that are not recoverable from git." \
    ""
fi

# --- WARN: sometimes right, always worth noticing -----------------------------

if printf '%s' "$normalised" | grep -qE 'git +push +.*(--force|-f)( |$)' \
   && ! printf '%s' "$normalised" | grep -q 'force-with-lease'; then
  warn "force-push without --force-with-lease: this can discard a teammate's commits that you never fetched."
fi

if printf '%s' "$normalised" | grep -qE 'git +reset +--hard'; then
  warn "git reset --hard discards uncommitted work irreversibly. \`git stash\` keeps it recoverable."
fi

if printf '%s' "$normalised" | grep -qE '(^|[;&|] *)(npm|pnpm|yarn|bun) +publish( |$)'; then
  warn "this publishes to a package registry — a published version cannot be unpublished cleanly."
fi

exit 0
