#!/usr/bin/env bash
# kaizen :: hook stub for UserPromptSubmit
#
# Fires:    Fires when the user submits a prompt, BEFORE Claude processes it
# Payload:  stdin JSON — prompt text + metadata
# Exit 0 = continue. Exit 2 BLOCKS the prompt with the message printed to stderr.
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

# TODO: implement UserPromptSubmit logic for kaizen here.
# See repo-root TODO.md "Hooks Implementation" section for the intended behavior.

exit 0
