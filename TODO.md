# TODO

Implementation backlog for kaizen, split by area. Items here are **scaffolded, not implemented** — the stubs and configs are in place; the actual behavior is TODO per the descriptions below.

For deferred polish items with full design context (`/learn --include-session`, `/analyze` v0.10 modes, `/preflight` v0.10 features), see [BACKLOG.md](./BACKLOG.md).

---

## Hooks

**Three hooks are implemented, wired and active** (phase 5,
[ADR-0009](./docs/decisions/0009-three-hooks-on-by-default.md)):

| Hook | Behaviour | Off switch |
|---|---|---|
| `PreToolUse` (Bash) | blocks a tiny catastrophic set, warns on a risky set | `KAIZEN_SAFETY=off` |
| `SessionStart` | injects branch, dirty count, last verdict, pending proposals, standards drift | — |
| `Stop` | suggests `/kaizen:finish` once per session when source changed | `KAIZEN_NUDGE=off` |

The other **26 no-op stubs were deleted**. Shipping stubs to users as if they
were features costs more trust than documenting the intent ever bought.

### Events with no implementation, and what they would do

Kept here as intent — **not as shipped code**. Anything promoted from this list
needs a real implementation, an entry in `hooks.json`, its name in `ACTIVE_HOOKS`
in `tests/suites/test_hooks.py`, and behavioural checks in `tests/suites/test_safety.py`.

| Event | Intended behaviour | Priority |
|---|---|---|
| `SessionEnd` | append a one-line session summary for retrospectives | medium |
| `PostToolBatch` | format a whole batch of edits at once instead of per file | medium |
| `TaskCompleted` | suggest `/kaizen:finish` when the last planned task closes | medium |
| `InstructionsLoaded` | warn when `CLAUDE.md` grows past ~200 lines | medium |
| `ConfigChange` | validate `settings.json` before it takes effect | medium |
| `PreCompact` | save branch, verdict and pending state so it survives compaction | medium |
| `Notification` | route notifications to the desktop when the user is away | medium |
| `WorktreeCreate` | carry `.claude/` config into a new worktree | medium |
| `PostToolUseFailure` | capture a failing test run for `/kaizen:finish` to surface | medium |
| `PermissionDenied` | log recurring denials that suggest a missing `allow` rule | low |
| `SubagentStart` / `SubagentStop` | subagent timing telemetry | low |
| `UserPromptSubmit` / `UserPromptExpansion` | usage signal | low |
| `StopFailure`, `PostCompact`, `CwdChanged`, `FileChanged`, `Elicitation*`, `TaskCreated`, `WorktreeRemove`, `Setup`, `TeammateIdle` | see git history for the original notes | low / none |

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
