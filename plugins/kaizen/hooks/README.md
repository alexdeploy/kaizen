# kaizen :: hooks/

Lifecycle hook stubs for the kaizen Claude Code plugin.

## What hooks are

A **hook** is a side-effect that fires automatically when Claude Code reaches a specific event in its lifecycle — a tool call, a session start, a context compaction, etc. Hooks complement skills and agents:

| Mechanism | Triggered by | Effect |
|---|---|---|
| **Skill** | User typing `/<name>` | Loads a prompt into context for Claude to follow |
| **Agent** (subagent) | Claude calling Task tool | Spawns a fresh-context worker |
| **Hook** | A lifecycle event (e.g. `PostToolUse`) | **Always fires** — runs a script / HTTP call / sub-prompt |

The key property of hooks is **automatic execution**. Where skills wait for the user and agents wait for Claude to delegate, **hooks fire deterministically** on their event. This makes them the right mechanism for any "always do X when Y happens" rule.

## Why use hooks

Use a hook when you need a guarantee, not a recommendation. For example:
- "Always run the formatter after Claude edits a file" → `PostToolUse` hook (kaizen already does this in user projects via `format-on-save.sh`).
- "Never let Claude run `rm -rf /`" → `PreToolUse` hook returning exit 2.
- "Save a session summary when Claude finishes a turn" → `Stop` hook.
- "Notify Slack when context compaction happens" → `PreCompact` hook.

In contrast, instructions in `CLAUDE.md` like "never do X" are guidance — Claude follows them most of the time. Hooks are enforcement.

**Official docs**: https://code.claude.com/docs/en/hooks

---

## All 29 hook events

Stubs for every Claude Code hook event live in [`scripts/`](./scripts/) as no-op `.sh` files ready to be filled in. Wire them via [`hooks.json.example`](./hooks.json.example).

### Session-level (3)

| Event | Fires when | Typical use |
|---|---|---|
| **SessionStart** | A session begins (matcher: `startup` / `resume` / `clear`) | Inject fresh repo state, load context |
| **Setup** | Claude Code starts with `--init-only` / `--init` / `--maintenance` | First-time setup automation |
| **SessionEnd** | A session terminates (`/exit`, `/clear`, timeout) | Save session metrics, cleanup temp files |

### Turn-level (5)

| Event | Fires when | Typical use |
|---|---|---|
| **UserPromptSubmit** | User submits a prompt, BEFORE Claude sees it | Pre-process prompt; exit 2 BLOCKS the prompt |
| **UserPromptExpansion** | A user command/skill expands into a prompt | Log usage, audit which skills run |
| **Stop** | Claude finishes responding (turn end) | End-of-turn rituals, suggest follow-up skill |
| **StopFailure** | Turn ends due to API error | Capture failure context, retry logic |
| **PostToolBatch** | Full batch of parallel tool calls resolves | Aggregate post-batch validation |

### Tool-execution (5)

| Event | Fires when | Typical use |
|---|---|---|
| **PreToolUse** | BEFORE a tool call executes | Safety guards; exit 2 BLOCKS the tool call |
| **PostToolUse** | After a tool call succeeds | Format-on-save, lint-on-edit, log changes |
| **PostToolUseFailure** | After a tool call fails | Retry logic, error reporting |
| **PermissionRequest** | Permission dialog appears | Desktop notification, log decisions |
| **PermissionDenied** | Tool call denied by auto-mode classifier | Log, suggest the user adjust permissions |

### Agent / task (5)

| Event | Fires when | Typical use |
|---|---|---|
| **SubagentStart** | A subagent is spawned via Task tool | Track agent lineage, log start |
| **SubagentStop** | A subagent finishes | Capture stats, summarize result |
| **TaskCreated** | A TodoWrite task is created | Sync to external tracker |
| **TaskCompleted** | A TodoWrite task is marked completed | Trigger next-task ritual |
| **TeammateIdle** | An agent-team teammate goes idle | Coordinate handoff |

### Context (4)

| Event | Fires when | Typical use |
|---|---|---|
| **InstructionsLoaded** | CLAUDE.md or a rules file is loaded into context | Verify staleness, warn on conflicts |
| **ConfigChange** | A config file changes during the session | Re-validate, hot-reload settings |
| **CwdChanged** | Working directory changes | Re-detect stack, reload project context |
| **FileChanged** | A watched file changes on disk (external edit) | Re-read state, invalidate caches |

### Compaction (2)

| Event | Fires when | Typical use |
|---|---|---|
| **PreCompact** | BEFORE context compaction starts | Save important state to disk |
| **PostCompact** | AFTER compaction completes | Verify post-compaction state |

### Notification & MCP (3)

| Event | Fires when | Typical use |
|---|---|---|
| **Notification** | Claude Code sends a notification (permission, idle, etc.) | Forward to desktop notifications, Slack, etc. |
| **Elicitation** | An MCP server requests user input | Auto-respond patterns, audit |
| **ElicitationResult** | User responds to an MCP elicitation | Capture for audit log |

### Worktree (2)

| Event | Fires when | Typical use |
|---|---|---|
| **WorktreeCreate** | A worktree is being created (`--worktree`, `EnterWorktree`) | Copy gitignored files, setup tooling |
| **WorktreeRemove** | A worktree is being removed | Cleanup leftover state |

---

## How to wire a hook

Hooks live in `plugins/kaizen/hooks/hooks.json` (plugin-level — fires for any project with kaizen installed). The file maps event names to handlers:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/scripts/post-tool-use.sh"
          }
        ]
      }
    ]
  }
}
```

See [`hooks.json.example`](./hooks.json.example) for a fully-wired template covering every event.

### Stubs are no-ops

All scripts in [`scripts/`](./scripts/) currently `exit 0` immediately — they don't do anything in production. To activate one:

1. **Implement the logic** in the relevant `<event>.sh` script.
2. **Register it** in `hooks.json` (use `hooks.json.example` as reference; copy only the entries you've implemented).
3. **Update** the repo-root [`TODO.md`](../../../TODO.md) "Hooks Implementation" section to mark the hook as done and describe the implemented behavior.
4. **Test** by triggering the relevant Claude Code event and verifying the script ran.

### Exit code semantics

| Exit code | Meaning |
|---|---|
| `0` | Continue normally |
| `2` | **Block** the action (only valid for `PreToolUse` and `UserPromptSubmit`). The message printed to `stderr` is shown to Claude. |
| any other | Error — Claude surfaces the failure but continues |

### Available environment variables

When a hook script runs, these are set:

| Variable | Value |
|---|---|
| `CLAUDE_PLUGIN_ROOT` | Path to the kaizen plugin root in the install cache |
| `CLAUDE_PROJECT_DIR` | Path to the user's project root |

For event-specific JSON payloads (tool inputs, file paths, etc.), read from **stdin** and parse with `jq`:

```bash
payload=$(cat)
file=$(echo "$payload" | jq -r '.tool_input.file_path // empty')
```

---

## Why kaizen ships all 29 stubs

Two reasons:

1. **Documentation by structure** — having every hook visible as a file makes Claude Code's full automation surface immediately discoverable to anyone reading the kaizen source.
2. **Implementation backlog** — the kaizen [`TODO.md`](../../../TODO.md) "Hooks Implementation" section enumerates the intended behavior of each. Stubs make implementation cheap: edit the file, wire in `hooks.json`, ship.

The current state — **all 29 as no-ops** — means kaizen doesn't yet leverage hooks for its workflow. v0.10 added the foundation; v0.11+ will activate selected hooks per the TODO priorities.
