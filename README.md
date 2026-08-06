# kaizen — bootstrap and continuous improvement for Claude Code

> 改善 (kaizen) = continuous improvement.
> A Claude Code plugin that scaffolds a complete, adapted `.claude/` setup for any project — empty or existing — and (in future versions) evolves it as the project grows.

## What it does today (v0.12.1)

**Shipped (v0.12.1):** 8 skills, 6 plugin-level agents, 7 project-level agents in the `advanced` profile, and a profile system for `/init`.

**On the `next` branch, unreleased:** a configuration lock so updates cannot destroy your edits, a versioned standards catalog with provenance, workspace/monorepo detection, `/kaizen:upgrade`, `/kaizen:doctor`, three active hooks, and a validation harness of ~1.800 checks. See [ROADMAP.md](./ROADMAP.md) for why, [docs/decisions/](./docs/decisions/README.md) for each decision, and [HANDOFF.md](./HANDOFF.md) for what is verified and what is not.

- `/kaizen:init` — bootstraps the project config. Profile flag: `--profile=<minimal|standard|advanced>` (default `standard`). The base scaffolding generates `CLAUDE.md`, settings, rules, code-reviewer agent, and hooks; standard+ profiles add a `workflow.md` rule documenting the kaizen-skill flow.
- `/kaizen:learn` — proposes CLAUDE.md/rules updates from git activity. `--limit=<N>` / `--since=<ref>` for scope. Subcommands: `show`, `apply`, `discard`.
- `/kaizen:analyze` — read-only audit. Modes: `--best-practices`, `--coverage`, `--architecture`.
- `/kaizen:preflight` — pre-merge gate. Tests + typecheck + lint + parallel security review + commit msg. SHIP/HOLD/BLOCK verdict. Flags: `--base`, `--skip`, `--auto-fix`.
- `/kaizen:plan` — auto-planner. Spec (file / `--from-prompt` / `--from-issue`) → annotated task tree. Auto-converts PDF/DOCX. `--seed-todos`.
- `/kaizen:docs` — surfaces user-facing documentation gaps from recent changes via the `docs-keeper` agent. Read-only.
- `/kaizen:bump` — suggests semver bump (major/minor/patch) via the `versioner` agent. Detects changesets. Supports JS/TS, Python, Rust.
- `/kaizen:finish` — **end-of-task orchestrator**. Chains deterministic checks + 4 parallel agents (security + commit + bump + docs) into a unified verdict and per-concern guidance.
- `/kaizen:doctor` — **(unreleased, `next` branch)** is this setup actually working? Finds hooks pointing at missing scripts, misspelled hook events that silently never fire, deprecated settings keys, unsubstituted template markers, a gitignored lock, and missing tools. `--fix` applies only the unambiguous repairs.
- `/kaizen:upgrade` — **(unreleased, `next` branch)** updates a project's generated config to the current plugin version **without overwriting your customisations**. Uses the lock file to tell untouched files from edited ones, and `git merge-file` for the rest. Plans before it writes. See [Configuration lock](#configuration-lock).

## Standards catalog

The rules kaizen writes into your `CLAUDE.md` are **versioned data with
provenance**, not prose baked into a template:

```bash
kaizen-standards show TS-003
```

```json
{
  "id": "TS-003",
  "statement": "**No `any`.** Use `unknown` and narrow.",
  "rationale": "`any` disables checking for every expression it touches, and it spreads…",
  "sources": [{ "label": "TypeScript Handbook — unknown", "url": "…" }],
  "added": "2026-08-05",
  "check": { "type": "grep", "pattern": ": any\\b|\\bas any\\b" }
}
```

Every generated line carries its id (`<!-- TS-003 -->`), so any rule in your
config can be traced back to its reasoning, its source and its date. The catalog
is versioned independently of the plugin (`2026.08` — calendar versioning,
because freshness is the point), which is what lets practices update without
waiting for a plugin release.

It also closes a real gap: a rule's *statement* and the *check* that verifies it
are now one object with a stable id. Previously they lived in different files and
were matched by substring, so rewording a convention silently disabled its check.

## Configuration lock

`/kaizen:init` records exactly what it wrote — a hash per file in
`.claude/kaizen/lock.json`, plus a verbatim snapshot under
`.claude/kaizen/baseline/`. Both are meant to be **committed**, like
`package-lock.json`.

That record is what turns updating from a gamble into an operation:

| Your file | kaizen knows | On `/kaizen:upgrade` |
|---|---|---|
| Untouched since generation | hash matches the lock | Replaced silently with the new version |
| You edited it | hash differs | **3-way merged** — your edits and the new template both survive; genuine collisions are shown, never auto-resolved |
| You deleted it | recorded but absent | Left deleted |
| kaizen never wrote it | not in the lock | Never touched |

Before the lock, the only update path was `--force`, which overwrites. The lock
is what makes "keeps improving without breaking anything" a mechanism rather
than a promise.

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
        ├── bin/                  ← auto-added to PATH when plugin is enabled
        │   ├── kaizen-detect     ← project fingerprint (bash)
        │   ├── kaizen-lock       ← what was generated; hashing + 3-way merge (bash)
        │   ├── kaizen-standards  ← query/render the rule catalog (python3)
        │   └── kaizen-doctor     ← config + platform health (python3)
        ├── standards/            ← the versioned rule catalog
        ├── compat/               ← what kaizen knows about Claude Code
        ├── hooks/
        │   ├── hooks.json        ← the three active hooks
        │   └── scripts/          ← their implementations
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

## Validation

kaizen is made of prompts, so nothing about it is checked by a compiler. The
harness in [`tests/`](./tests/README.md) closes that gap:

```bash
tests/run.sh          # deterministic suites — ~0.5s, no dependencies
tests/run.sh --live   # + real headless sessions, asserting on what /init wrote
```

The deterministic layer verifies that the manifests agree on a version, every
dispatched agent exists, every `{{PLACEHOLDER}}` and `KAIZEN_ENRICH` marker in a
template has a matching directive in `init/SKILL.md` (both directions), every
script parses, every hook stub is still a silent no-op, and `kaizen-detect`
returns exactly what it used to for each fixture repo. It runs on every push via
[GitHub Actions](./.github/workflows/tests.yml).

## Design principles

1. **Never silently overwrite.** If config exists, ask before touching it. `--force` is opt-in.
2. **Deterministic detection, LLM reasoning.** Bash scripts gather facts (fast, free); the model interprets and adapts.
3. **Adapt to maturity.** Empty repo → ask. Small repo → minimal scaffolding. Mature repo → offer archeology mode.
4. **English internally.** All config templates are in English (loads every session → cache-friendly). User-facing output adapts to user's language.
5. **Start small, grow on signal.** v0 generates the bare-essential scaffolding. Future skills (`/kaizen:learn`) add complexity only when the project earns it.

## Versioning

- v0 → v0.x: breaking changes likely. Anchor `version` in `plugin.json` so users opt into updates.
- v1.x+: semver. Breaking changes only on majors.
