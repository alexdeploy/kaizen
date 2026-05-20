# kaizen — bootstrap and continuous improvement for Claude Code

> 改善 (kaizen) = continuous improvement.
> A Claude Code plugin that scaffolds a complete, adapted `.claude/` setup for any project — empty or existing — and (in future versions) evolves it as the project grows.

## What it does today (v0.12.0)

`/kaizen:init --profile=advanced` now scaffolds a **project-level agent ecosystem** — 6 agents in `<project>/.claude/agents/` that Claude auto-invokes during general conversation (not just when invoking kaizen skills). Plus 2 new hooks (secret-detector + dependency-changed).

**8 skills**, **6 plugin-level agents**, and a **profile system** for `/init`:

- `/kaizen:init` — bootstraps the project config. Profile flag: `--profile=<minimal|standard|advanced>` (default `standard`). The base scaffolding generates `CLAUDE.md`, settings, rules, code-reviewer agent, and hooks; standard+ profiles add a `workflow.md` rule documenting the kaizen-skill flow.
- `/kaizen:learn` — proposes CLAUDE.md/rules updates from git activity. `--limit=<N>` / `--since=<ref>` for scope. Subcommands: `show`, `apply`, `discard`.
- `/kaizen:analyze` — read-only audit. Modes: `--best-practices`, `--coverage`, `--architecture`.
- `/kaizen:preflight` — pre-merge gate. Tests + typecheck + lint + parallel security review + commit msg. SHIP/HOLD/BLOCK verdict. Flags: `--base`, `--skip`, `--auto-fix`.
- `/kaizen:plan` — auto-planner. Spec (file / `--from-prompt` / `--from-issue`) → annotated task tree. Auto-converts PDF/DOCX. `--seed-todos`.
- `/kaizen:docs` — surfaces user-facing documentation gaps from recent changes via the `docs-keeper` agent. Read-only.
- `/kaizen:bump` — suggests semver bump (major/minor/patch) via the `versioner` agent. Detects changesets. Supports JS/TS, Python, Rust.
- `/kaizen:finish` — **end-of-task orchestrator**. Chains deterministic checks + 4 parallel agents (security + commit + bump + docs) into a unified verdict and per-concern guidance.

## Project agent ecosystem (v0.12+, `--profile=advanced`)

| Agent | Use when (auto-invocation) |
|---|---|
| `test-writer` | New code without tests, or "write tests for X" |
| `refactor-helper` | "Refactor X without changing behavior" |
| `documentation-writer` | "Write/update docs (README, docstrings, CHANGELOG)" |
| `dependency-auditor` | "Audit deps", "any outdated packages?", "vulnerabilities?" |
| `security-auditor` | "Security review of auth/payments/data layer" — broader than per-diff |
| `architecture-advisor` | "Should I use X or Y?", "does this fit the architecture?" |

Plus `code-reviewer` (already shipped) for comprehensive review on demand.

All marked with `kaizen-managed: true` so `--force` re-init can update them. Change to `false` to claim ownership.

## Visibility (v0.11+)

- **Statusline**: `/kaizen:init` generates `.claude/hooks/statusline.sh` that surfaces `[model] dir ⎇ branch  ✓/⚠/✗ verdict  ·  ⚠ learn pending  ·  📋 N plan(s)  ·  N modified` at the bottom of the TUI.
- **Subagent statusline**: plugin-level, shows which kaizen agent is running during `/preflight` / `/plan` / `/finish` parallel dispatch (e.g., `🔒 security review running…`).
- **Output style `kaizen-terse`** (opt-in, written by `--profile=advanced`): enforces terse responses — no preambles, no narration, no padding.

## Plugin-level agents (shipped with kaizen)

- `preflight-security` — security audit (changed files). Used by `/preflight` + `/finish`.
- `commit-suggester` — Conventional Commits message author. Used by `/preflight` + `/finish`.
- `plan-context` — project profiler. Used by `/plan`.
- `plan-decomposer` — spec → task list. Used by `/plan`.
- `docs-keeper` — documentation gap analyzer. Used by `/docs` + `/finish`.
- `versioner` — semver bump analyzer. Used by `/bump` + `/finish`.

(All distinct from the project-level `.claude/agents/code-reviewer.md` that `/kaizen:init` generates — that one is user-customizable for manual review.)

## What's coming next

Tracked in [BACKLOG.md](./BACKLOG.md). Highlights:
- `/kaizen:bump --apply` (auto-modify manifest / write changeset)
- `/kaizen:ci` skill (Phase 2 workflow initiative — CI/CD scaffolds)
- `/kaizen:learn` `--include-session`
- `/kaizen:analyze` `--dependencies` / `--security` / `--complexity` modes
- `/kaizen:preflight` risk-aware sizing + commit style auto-detection

## Repo layout

```
kaizen/
├── .claude-plugin/
│   └── marketplace.json          ← marketplace manifest (this repo IS the marketplace)
└── plugins/
    └── kaizen/                   ← the plugin itself
        ├── .claude-plugin/
        │   └── plugin.json
        ├── bin/
        │   └── kaizen-detect     ← auto-added to PATH when plugin is enabled
        ├── agents/
        │   ├── preflight-security.md         ← /preflight + /finish (security audit)
        │   ├── commit-suggester.md           ← /preflight + /finish (commit msg)
        │   ├── plan-context.md               ← /plan (project profile)
        │   ├── plan-decomposer.md            ← /plan (spec → task list)
        │   ├── docs-keeper.md                ← /docs + /finish (doc gap analyzer)
        │   └── versioner.md                  ← /bump + /finish (semver bump)
        └── skills/
            ├── init/
            │   ├── SKILL.md                  ← /kaizen:init (--profile=minimal|standard|advanced)
            │   └── templates/                ← what /init writes into user projects
            │       ├── _shared/              ← stack-agnostic files (incl. workflow.md)
            │       ├── generic/
            │       ├── typescript-node/
            │       └── python/
            ├── learn/SKILL.md                ← /kaizen:learn
            ├── analyze/SKILL.md              ← /kaizen:analyze
            ├── preflight/SKILL.md            ← /kaizen:preflight
            ├── plan/SKILL.md                 ← /kaizen:plan
            ├── docs/SKILL.md                 ← /kaizen:docs (v0.10+)
            ├── bump/SKILL.md                 ← /kaizen:bump (v0.10+)
            └── finish/SKILL.md               ← /kaizen:finish (v0.10+ orchestrator)
```

## Local development

No need to publish. Load the plugin straight from this directory:

```bash
cd /path/to/your/project
claude --plugin-dir /Users/alex/Development/projects/kaizen/plugins/kaizen
```

Then in Claude Code:

```
/kaizen:init
```

After making changes to the plugin source, restart Claude Code to pick up the new version. (Some Claude Code versions expose `/reload-plugins` for hot reload; v2.1.45 does not — the install message will tell you when restart is required.)

## Smoke test

```bash
# In any project directory:
/Users/alex/Development/projects/kaizen/plugins/kaizen/bin/kaizen-detect
```

You should see a JSON payload with `stack`, `package_manager`, `maturity`, `git`, `existing_claude_config`, `tests_found`, `ci`.

## Publishing (when ready)

1. `git init && git add . && git commit -m "v0.1.0 - init skill"`.
2. Push to GitHub: `git remote add origin git@github.com:alexdeploy/kaizen.git && git push -u origin main`.
3. Users add the marketplace once:
   ```
   /plugin marketplace add alexdeploy/kaizen
   /plugin install kaizen@kaizen
   ```
   Then restart Claude Code so the new skills/agents are loaded.
4. Future releases: bump `version` in **both** `plugins/kaizen/.claude-plugin/plugin.json` **and** `.claude-plugin/marketplace.json`, then push. Users update with `/plugin marketplace update kaizen` and restart Claude Code.

## Design principles

1. **Never silently overwrite.** If config exists, ask before touching it. `--force` is opt-in.
2. **Deterministic detection, LLM reasoning.** Bash scripts gather facts (fast, free); the model interprets and adapts.
3. **Adapt to maturity.** Empty repo → ask. Small repo → minimal scaffolding. Mature repo → offer archeology mode.
4. **English internally.** All config templates are in English (loads every session → cache-friendly). User-facing output adapts to user's language.
5. **Start small, grow on signal.** v0 generates the bare-essential scaffolding. Future skills (`/kaizen:learn`) add complexity only when the project earns it.

## Versioning

- v0 → v0.x: breaking changes likely. Anchor `version` in `plugin.json` so users opt into updates.
- v1.x+: semver. Breaking changes only on majors.
