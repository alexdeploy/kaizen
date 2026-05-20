# TODO

Implementation backlog for kaizen, split by area. Items here are **scaffolded, not implemented** — the stubs and configs are in place; the actual behavior is TODO per the descriptions below.

For deferred polish items with full design context (`/learn --include-session`, `/analyze` v0.10 modes, `/preflight` v0.10 features), see [BACKLOG.md](./BACKLOG.md).

---

## Hooks Implementation

29 hook stubs live at [`plugins/kaizen/hooks/scripts/`](./plugins/kaizen/hooks/scripts/). Each one is a no-op `exit 0` shell script ready to be implemented. None are wired in `hooks.json` yet — kaizen ships zero active plugin-level hooks in v0.10.

For each event below: the **intended kaizen behavior** + **priority** for implementing.

### Session-level

| Hook | Intended kaizen behavior | Priority |
|---|---|---|
| **SessionStart** | Inject `git status --porcelain` + branch name + last `/kaizen:finish` verdict (if `.claude/kaizen/finish-report.md` exists) so Claude starts the session with awareness of repo state and any pending issues. | **high** |
| **SessionEnd** | Append a one-line entry to `.claude/kaizen/session.log` (timestamp, files modified count, did /finish run, verdict). Useful for retrospectives. Optionally suggest `/kaizen:learn` if many uncommitted files. | medium |
| **Setup** | When `claude --init` runs in a fresh project, auto-suggest `/kaizen:init --profile=standard` if no `CLAUDE.md` exists. One-shot helper. | medium |

### Turn-level

| Hook | Intended kaizen behavior | Priority |
|---|---|---|
| **UserPromptSubmit** | Pre-process: detect if the user said something like "commit" or "open PR" and surface a reminder to run `/kaizen:finish` first if not already done in this turn. Never block (no exit 2) — just informational. | low |
| **UserPromptExpansion** | Audit which kaizen skills get invoked in a session — append to a per-session log for usage analytics. Optional, off by default in v1.0. | low |
| **Stop** | The big one. After Claude finishes a turn, check: did files change? Has `/kaizen:finish` been run since? If no AND files changed → surface a one-line suggestion: `"Tip: run /kaizen:finish before committing."` Implement with debouncing (skip if just ran). | **high** |
| **StopFailure** | Capture the API error to `.claude/kaizen/failures.log` for debugging. Don't surface to user (Claude already does). | low |
| **PostToolBatch** | If a batch of Edits touched >5 files, run `format-on-save.sh` on all of them at once instead of per-edit (more efficient than `PostToolUse` per file). | medium |

### Tool-execution

| Hook | Intended kaizen behavior | Priority |
|---|---|---|
| **PreToolUse** (Bash matcher) | Extra safety layer beyond `deny:` rules. Block destructive patterns the permission system can't easily express: `git push --force` to protected branches, `rm -rf` against `~`/`/`, `chmod -R 777`, `curl ... | sh`. Exit 2 with explanation. | **high** |
| **PostToolUse** (Edit/Write matcher) | Currently handled at user-project level via the format-on-save.sh template /init writes. The plugin-level version would: tag files in `.claude/kaizen/modified-this-session.log` for use by `/finish` to know exactly which files changed without re-running git diff. | medium |
| **PostToolUseFailure** | If `npm test` or similar fails, capture last 50 lines of output to `.claude/kaizen/last-failure.log` for `/kaizen:finish` to surface. | medium |
| **PermissionRequest** | Desktop notification when Claude is waiting for permission and the user is AFK. (macOS: `terminal-notifier`; Linux: `notify-send`.) | low |
| **PermissionDenied** | Log to `.claude/kaizen/denied.log` for review — recurring denials suggest a permission rule should be added to `allow:`. | low |

### Agent / task

| Hook | Intended kaizen behavior | Priority |
|---|---|---|
| **SubagentStart** | Track subagent invocations per session: `<timestamp> <subagent_type> spawned by <parent>`. Useful for measuring multi-agent dispatch overhead. | low |
| **SubagentStop** | Same log as start, with duration. Combined with SubagentStart gives subagent timing telemetry. | low |
| **TaskCreated** | When `/kaizen:plan --seed-todos` populated TodoWrite and a task is now created, optionally sync to Linear/Jira via MCP if configured. | low |
| **TaskCompleted** | Auto-suggest `/kaizen:finish` after the last `pending` task becomes `completed` in this session — heuristic for "user finished their planned work". | medium |
| **TeammateIdle** | Agent teams feature — not used by kaizen yet. No planned behavior unless kaizen adds team-mode skills. | none |

### Context

| Hook | Intended kaizen behavior | Priority |
|---|---|---|
| **InstructionsLoaded** | When CLAUDE.md is loaded, check its line count. If > 200, surface a warning: `"CLAUDE.md is large; consider /kaizen:learn to move sections to rules/."` Just informational. | medium |
| **ConfigChange** | If `.claude/settings.json` changes mid-session, validate the JSON before letting it apply. Block with exit 2 if schema-invalid (would prevent the cascade where bad settings silently break the whole session). | medium |
| **CwdChanged** | Re-run `kaizen-detect` if the user `cd`'d into a different project. Update an in-session stack-detection cache. | low |
| **FileChanged** | When `.env` or `package.json` changes externally, surface: `"detected external change to <file> — Claude should re-read it before next operation"`. | low |

### Compaction

| Hook | Intended kaizen behavior | Priority |
|---|---|---|
| **PreCompact** | Save `.claude/kaizen/pre-compact-state.md` with: current branch, last verdict, pending plans, open `pending.md`. Lets the user reconstruct state if compaction loses something. | medium |
| **PostCompact** | Log compaction stats (input tokens before / after). Useful telemetry for understanding context efficiency. | low |

### Notification & MCP

| Hook | Intended kaizen behavior | Priority |
|---|---|---|
| **Notification** | Route Claude Code notifications to desktop (`terminal-notifier`/`notify-send`) when user is AFK. Configurable by notification type. | medium |
| **Elicitation** | If an MCP server requests input, log the request to `.claude/kaizen/mcp-elicitations.log` for audit. | low |
| **ElicitationResult** | Append the user's response to the same audit log. | low |

### Worktree

| Hook | Intended kaizen behavior | Priority |
|---|---|---|
| **WorktreeCreate** | When Claude creates a worktree, copy `.claude/` config + run a light `kaizen-detect` to confirm the worktree inherits the right setup. Also honor `.worktreeinclude` if present. | medium |
| **WorktreeRemove** | Cleanup any kaizen state files (`.claude/kaizen/*.md`) that don't belong in the parent worktree's git index. | low |

### Implementation order (suggestion)

If we tackle hooks across multiple releases, this is the order I'd implement:

1. **v0.11 high-priority batch**: `Stop`, `PreToolUse` (safety), `SessionStart` (richer state). These three deliver the most "orquestación sincronizada" feeling.
2. **v0.12 medium batch**: `SessionEnd`, `Setup`, `PostToolBatch`, `TaskCompleted`, `InstructionsLoaded`, `ConfigChange`, `PreCompact`, `Notification`, `WorktreeCreate`.
3. **v0.13 polish batch**: the remaining low-priority items.

Each release activates only the hooks it implements (selective entries in `hooks.json` — not the full `hooks.json.example` template).

---

## MCP Integration

kaizen recommends 5 MCP servers in [`plugins/kaizen/.mcp.json.example`](./plugins/kaizen/.mcp.json.example) but **does not bundle or activate any** in v0.10. Documentation: [`docs/mcp-usage.md`](./docs/mcp-usage.md).

The MCPs aren't just "nice to have for the user" — they unlock specific kaizen capabilities that need implementing. Below is the per-MCP integration TODO:

### `github` MCP integrations

| Where | Intended kaizen behavior | Priority |
|---|---|---|
| `/kaizen:plan --from-issue=<N>` | Currently uses `gh issue view <N>` (CLI). Switch to GitHub MCP when present — richer context (labels, comments tree, related PRs, author info). Fallback to `gh` when MCP absent. | **high** |
| `/kaizen:finish --open-pr` (NEW v0.11+ flag) | After SHIP verdict, optionally open a PR using the commit-suggester's message as title + plan reference (if a plan exists for this branch) as body. | **high** |
| `/kaizen:analyze --dependencies` (when implemented) | Cross-reference detected dependency CVEs with the project's repo security advisories tab. | medium |
| `/kaizen:learn` future | Could read recent merged PRs (not just commits) for richer signal on what the team values. | low |

### `playwright` MCP integrations

| Where | Intended kaizen behavior | Priority |
|---|---|---|
| `/kaizen:preflight` + `/kaizen:finish` (Phase 1 deterministic checks) | NEW check: `browser-test`. Activates automatically when playwright MCP is present AND a `playwright.config.*` exists. Runs `playwright test` for the changed files' related tests. Adds to verdict tier `BLOCK` on failures. | **high** for web projects |
| `/kaizen:analyze` future | New mode `--ui-coverage`: which UI components have no Playwright tests covering them. | medium |

### `filesystem` MCP integrations

| Where | Intended kaizen behavior | Priority |
|---|---|---|
| `/kaizen:plan` `plan-context` agent | Use filesystem MCP for the recursive `src/*/` enumeration on huge repos where Glob alone times out. | low |
| `/kaizen:analyze --coverage` | Faster recursive source enumeration via MCP. | low |

### `memory` MCP integrations

| Where | Intended kaizen behavior | Priority |
|---|---|---|
| `/kaizen:learn` future | Optional `--include-memory-mcp` flag (alongside the BACKLOG'd `--include-session`). Reads structured project facts from the memory graph as additional signal. | medium |
| `code-reviewer` agent (project-level, from /init) | Could query memory graph for "known flaky patterns" or "preferred conventions per module" to avoid re-flagging the same things every review. | medium |
| `/kaizen:init` | Could read pre-existing memory entries (set by prior tools) to seed CLAUDE.md content. | low |

### `sequential-thinking` MCP integrations

| Where | Intended kaizen behavior | Priority |
|---|---|---|
| `/kaizen:plan --deep` (NEW v0.11+ flag) | When this MCP is present, use sequential-thinking for the decomposer's reasoning on large/ambiguous specs. Falls back to standard mode when absent. | low |

### Generic MCP awareness (across all skills)

| Where | Intended kaizen behavior | Priority |
|---|---|---|
| `/kaizen:init --profile=advanced` | Write `.mcp.json.example` to the user's project root (currently only the plugin has it). User sees the recommendations as soon as they bootstrap. | **high** (cheap) |
| `/kaizen:init --profile=advanced` | Add a `## MCP servers` section to the generated CLAUDE.md explaining which MCPs unlock which kaizen features. | medium |
| All skills | When invoking a skill, detect which MCPs are connected via `/mcp` semantics and **adapt behavior accordingly** — don't fail if MCP absent, but use it if present. (Pattern: "graceful enhancement, not hard dependency".) | medium |

### Implementation order (suggestion)

1. **v0.11 cheap wins**: `/init --profile=advanced` writes `.mcp.json.example` + CLAUDE.md MCP section. No code changes to other skills, just generation.
2. **v0.12 GitHub-aware**: Replace `gh` CLI calls in `/plan --from-issue` with GitHub MCP detection + fallback. Add `/finish --open-pr` flag using GitHub MCP.
3. **v0.13 Playwright integration**: New `browser-test` deterministic check in `/preflight` + `/finish` when MCP detected.
4. **v0.14+ polish**: `memory` MCP integration in `/learn` and `code-reviewer`; `sequential-thinking` for `/plan --deep`.

---

## Cross-cutting

Things that don't fit cleanly into Hooks or MCP but are worth tracking:

- **`/init` should auto-add `.mcp.json.example`** to user projects on `--profile=advanced` (cross-references MCP TODO above).
- **`hooks/README.md`'s table is the source of truth** for kaizen's hook understanding — keep it in sync with whatever Claude Code's docs say (review on each minor version bump).
- **The TODO sections above should shrink as items get done**; move completed items into the CHANGELOG entry for the relevant release.

---

## How to use this file

- When picking next work: scan the **high priority** items first.
- When implementing one: do the work, remove the row, add a CHANGELOG entry under the release version that included it.
- For ideas not yet planned: add a row with priority `idea` and brief description — promote to higher priority when the design is settled.
- For things blocked by external research (e.g., `/learn --include-session`), promote to [BACKLOG.md](./BACKLOG.md) where design context lives.
