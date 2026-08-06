# ADR-0009: Three hooks, on by default; delete the other twenty-six

- **Status**: accepted
- **Date**: 2026-08-06
- **Phase**: phase 5 / `next`

## Context

kaizen shipped **thirty** hook scripts. Every one was a no-op `exit 0` stub, and
no `hooks.json` existed, so none of them ran. `TODO.md` documented the intended
behaviour of each in a table.

Two separate problems with that state:

1. **Nothing kaizen does happens unless you invoke it.** A plugin whose name
   means *continuous improvement* only acted when typed. The passive layer — the
   thing that makes it feel like a system rather than a set of commands — was
   entirely unimplemented.
2. **The stubs were shipped to users as if they were features.** A developer
   evaluating the plugin who opens `hooks/scripts/stop.sh` finds a comment
   saying what it would do and `exit 0`. That costs more trust than the table
   ever bought.

The question was not *which* hooks to implement. It was **which hooks may be on
without asking**, because a plugin that silently starts blocking commands in
every project the moment it is installed is its own kind of betrayal.

## Decision

Implement **three** hooks, wire them in a real `hooks.json`, and **delete the
other twenty-six**.

| Hook | Does | Why it may be on by default |
|---|---|---|
| `PreToolUse` (Bash) | Blocks a tiny set of catastrophic commands; warns on a slightly larger risky set | Its patterns are anchored so tightly that no legitimate command can match. `rm -rf node_modules` passes; `rm -rf /` does not |
| `SessionStart` | Injects branch, dirty count, last verdict, pending proposals, standards drift | It *replaces* tool calls Claude would otherwise spend rediscovering this. Silent when there is nothing to say |
| `Stop` | Suggests `/kaizen:finish` when source changed and no check has run | Once per session, never writes into the project, silent unless there is real work to flag |

Both behavioural hooks have a documented escape hatch: `KAIZEN_SAFETY=off` and
`KAIZEN_NUDGE=off`.

The bar for the block list is explicit: **a pattern belongs there only if no
legitimate command could ever match it.** A safety net that fires on real work
gets switched off, and then it protects nobody. That is why the harness's
must-NOT-block table is longer than its must-block table, and why it should grow
with every false positive anyone reports.

The generated `settings.json` keeps its own deny list as defence in depth — it
protects the project even with the plugin disabled — but the over-broad
`Bash(rm -rf *)` was removed for the same reason: it blocked `rm -rf dist`, and a
deny rule that stops real work gets the whole list deleted.

## Consequences

**Easier:** kaizen now does something without being asked, in the three places
where that is defensible. A user gets a safety net, a session that starts
oriented, and one nudge — and can turn the last two off with an env var.

**Harder:** kaizen now runs code on every Bash call in every project where it is
enabled. That is a real obligation: the hook must be fast, must never crash, and
must never block legitimate work. The 121 checks in the `safety` suite exist for
that reason, and a false positive is a bug of the highest severity in this
project.

**Costs:**
- The 26 deleted stubs took their inline documentation with them. Intent for
  those events stays in `TODO.md`, which is where unimplemented plans belong.
- `hooks.json` existing at all means the harness can no longer assert "kaizen
  activates zero hooks". The `ACTIVE_HOOKS` set replaces that: a script may only
  be wired if it is declared there, so shipping a hook is a deliberate act.

**Accepted limitation:** `PreToolUse` reads a command as text. It cannot
understand shell semantics, so a sufficiently indirect destructive command
(`eval "$(printf 'rm -rf /')"`) passes. This is a safety net, not a sandbox, and
claiming otherwise would be worse than the gap.

## Alternatives

- **All 29 hooks implemented** — rejected: most have no behaviour worth the code,
  and each one is another thing running on someone else's machine.
- **Hooks off by default, opt-in per project** — rejected for `PreToolUse`: a
  safety net nobody enables protects nobody. Kept in spirit via the env vars.
- **Keep the stubs, wire nothing** — rejected: that is the state being fixed.
- **`PreToolUse` blocks a broad set of destructive commands** — rejected, and this
  is the important one. Breadth is what kills these hooks. `rm -rf` is normal in a
  JavaScript project a dozen times a day.
- **Put the safety patterns in the generated `settings.json` only** — rejected:
  the deny list matches command prefixes and cannot recognise a pipe-to-shell.
  Both layers, doing what each is good at.
