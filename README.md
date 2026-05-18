# kaizen — bootstrap and continuous improvement for Claude Code

> 改善 (kaizen) = continuous improvement.
> A Claude Code plugin that scaffolds a complete, adapted `.claude/` setup for any project — empty or existing — and (in future versions) evolves it as the project grows.

## What it does today (v0.7.0)

- `/kaizen:init` — analyzes your project (stack, maturity, git state, existing config) and generates a tailored `CLAUDE.md`, `.claude/settings.json`, path-scoped rules, a code-reviewer agent, and hooks. Outputs a per-file drift report.
- `/kaizen:learn` — analyzes recent git activity (default: last 10 commits; `--since=<ref>` or `--limit=<N>` to scope) and proposes updates to `CLAUDE.md` / `.claude/rules/`. Writes proposals to `.claude/kaizen/pending.md` for review. Subcommands: `show`, `apply`, `discard`. Range analyzed is always shown up front. **Never modifies your config without explicit approval.**
- `/kaizen:analyze` — read-only audit of the project against its own conventions and rules. Modes: `--best-practices`, `--coverage`, `--architecture`. Writes report to `.claude/kaizen/analyze-report.md`.
- `/kaizen:preflight` — pre-merge gate. Runs tests/typecheck/lint sequentially, then dispatches `preflight-security` + `commit-suggester` agents in parallel. **SHIP / HOLD / BLOCK** verdict. Writes report to `.claude/kaizen/preflight-report.md`.
- `/kaizen:plan` — auto-planner. Reads a spec doc, dispatches `plan-context` + `plan-decomposer` agents in parallel, synthesizes an annotated task tree (type/complexity/dependencies/risks). Plans accumulate at `.claude/kaizen/plans/<slug>-<timestamp>.md`. Subcommands: `list`, `show`.

## Plugin-level agents (shipped with kaizen)

- `preflight-security` — security audit scoped to changed files. Invoked by `/kaizen:preflight`.
- `commit-suggester` — Conventional Commits message author from diff analysis. Invoked by `/kaizen:preflight`.
- `plan-context` — project state profiler (stack, architecture, conventions). Invoked by `/kaizen:plan`.
- `plan-decomposer` — spec-to-task-list decomposer. Invoked by `/kaizen:plan`.

(These are distinct from the `code-reviewer.md` that `/kaizen:init` generates in your project — that one is user-customizable for manual general-purpose review.)

## What's coming next (focus on polish, not new skills)

- `/kaizen:learn` v0.7 — `--include-session` flag, better range visibility.
- `/kaizen:analyze` v0.7 — `--dependencies`, `--security`, `--complexity` modes.
- `/kaizen:preflight` v0.7 — `--base`, `--skip`, `--auto-fix` flags; commit style auto-detection.
- `/kaizen:plan` v0.7 — inline prompt input, gh issue input, auto-conversion of PDF/DOCX, `--seed-todos`.

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
        │   ├── preflight-security.md         ← invoked by /kaizen:preflight (security audit)
        │   ├── commit-suggester.md           ← invoked by /kaizen:preflight (commit msg)
        │   ├── plan-context.md               ← invoked by /kaizen:plan (project profile)
        │   └── plan-decomposer.md            ← invoked by /kaizen:plan (spec → task list)
        └── skills/
            ├── init/
            │   ├── SKILL.md                  ← /kaizen:init entrypoint
            │   └── templates/                ← what /init writes into user projects
            │       ├── _shared/              ← stack-agnostic files
            │       ├── generic/
            │       ├── typescript-node/
            │       └── python/
            ├── learn/
            │   └── SKILL.md                  ← /kaizen:learn (analyze/show/apply/discard)
            ├── analyze/
            │   └── SKILL.md                  ← /kaizen:analyze (--best-practices/--coverage/--architecture/show)
            ├── preflight/
            │   └── SKILL.md                  ← /kaizen:preflight (full run / show)
            └── plan/
                └── SKILL.md                  ← /kaizen:plan <spec> (full run / list / show)
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
