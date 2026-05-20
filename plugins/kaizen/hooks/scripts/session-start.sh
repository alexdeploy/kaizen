#!/usr/bin/env bash
# kaizen :: hook stub for SessionStart
#
# Fires:    Fires when a session begins or resumes
# Payload:  stdin JSON — matcher: startup/resume/clear
# Exit 0 = continue.
# Docs:     https://code.claude.com/docs/en/hooks
#
# This is a no-op stub shipped by the kaizen plugin as a template.
# It does nothing in production. To activate:
#   1. Implement the logic below.
#   2. Wire this script in plugins/kaizen/hooks/hooks.json (see hooks.json.example).
#   3. Update kaizen TODO.md "Hooks Implementation" with the implemented behavior.

set -euo pipefail

# Consume stdin so the JSON payload doesn't pipe-break.
payload=$(cat)

# TODO: implement SessionStart logic for kaizen here.
# See repo-root TODO.md "Hooks Implementation" section for the intended behavior.

exit 0
