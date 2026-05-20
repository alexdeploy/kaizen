# User manual

> Install kaizen, run `/kaizen:init`, get a Claude Code config tailored to your project. This manual covers v0.1.0.

For internal architecture, see [architecture.md](./architecture.md). For decision flow, see [runtime-flow.md](./runtime-flow.md).

## Requirements

- [Claude Code](https://claude.com/code) v2.1.0 or later.
- `bash`, `jq`, `find`, `git` (all standard on macOS/Linux).
- A terminal in the project you want to configure.

## Install

### Option A — local development (today)

Clone or pull the kaizen repo, then load it directly with `--plugin-dir`:

```bash
git clone https://github.com/alexdeploy/kaizen.git ~/kaizen
cd /path/to/your/project
claude --plugin-dir ~/kaizen/plugins/kaizen
```

Inside Claude Code, the skill is now available:

```
/kaizen:init
```

### Option B — marketplace (when published)

```bash
# Inside Claude Code, once:
/plugin marketplace add alexdeploy/kaizen
/plugin install kaizen@kaizen
```

Then **restart Claude Code** so the new skills load. (Some versions support `/reload-plugins` for hot reload; if your install message says "Restart Claude Code to load new plugins", do that.)

From then on, `/kaizen:init` is available in any project.

To update later:

```
/plugin marketplace update kaizen
```
Then restart Claude Code.

## Quickstart

```bash
cd /your/project
claude --plugin-dir ~/kaizen/plugins/kaizen
```

```
/kaizen:init
```

You'll see Claude run `detect.sh`, report what it found, and either generate files or ask you a question. Approve the file writes when prompted.

## Command reference

Commands shipped in v0.12.0 (same 8 skills as v0.11 + agent ecosystem in `advanced` profile):
- [`/kaizen:init`](#kaizeninit-arguments) — bootstrap project config (with `--profile` system)
- [`/kaizen:learn`](#kaizenlearn-arguments) — propose config updates from git activity
- [`/kaizen:analyze`](#kaizenanalyze-arguments) — read-only audit of code vs. stated rules
- [`/kaizen:preflight`](#kaizenpreflight-arguments) — pre-merge gate (tests + LLM review + verdict)
- [`/kaizen:plan`](#kaizenplan-arguments) — auto-planner: spec doc → annotated task tree
- [`/kaizen:docs`](#kaizendocs-arguments) — documentation gap analyzer (v0.10+)
- [`/kaizen:bump`](#kaizenbump-arguments) — semver bump suggester (v0.10+)
- [`/kaizen:finish`](#kaizenfinish-arguments) — end-of-task orchestrator (v0.10+)

### `/kaizen:init [arguments]` {#kaizeninit-arguments}

Bootstrap a Claude Code configuration tailored to the current project. Detects stack, package manager, project maturity, and existing config, then generates `CLAUDE.md`, `.claude/settings.json`, path-scoped rules, a code-reviewer agent, and hooks.

#### Arguments

| Argument | Meaning |
|---|---|
| *(no args)* | Auto-detect everything. Recommended for first runs. Uses `--profile=standard` by default. |
| `--preset <name>` | Skip stack auto-detection, use a named preset. Values: `generic`, `typescript-node`, `python`. |
| `--profile=<level>` | Control workflow scaffolding (v0.10+). Values: `minimal`, `standard` (default), `advanced`. See "Profile system" below. |
| `--force` | Overwrite existing Claude config files. **Use only after committing or backing up.** Without this flag, kaizen will refuse to overwrite. |
| `--minimal` | Only generate `CLAUDE.md` + `.claude/settings.json` + `.gitignore` patch. Independent of `--profile=minimal` (this is a file-count flag, profile controls workflow scaffolding). |

Combine freely: `/kaizen:init --preset python --profile=advanced`, `/kaizen:init --force --preset typescript-node`.

#### Profile system (v0.10+)

The `--profile=<level>` flag controls how much **workflow scaffolding** kaizen includes in the generated config:

| Profile | What it adds beyond the base scaffold |
|---|---|
| `minimal` | **Nothing extra**. Identical to v0.6 output. Use for throwaway projects or when you want to opt out of workflow recommendations. |
| `standard` (default) | Adds `.claude/rules/workflow.md` documenting the kaizen-skill flow (when to run `/learn`, `/analyze`, `/preflight`, `/docs`, `/bump`, `/finish`). Appends a "Workflow" section to `CLAUDE.md`. No automation forced. |
| `advanced` | Standard + `.claude/rules/workflow-advanced.md` with the **end-of-task ritual** (recommends `/kaizen:finish` before every commit). Adds a stack-specific Versioning section to `CLAUDE.md`. |

**Important**: the plugin's new skills (`/docs`, `/bump`, `/finish`) and agents (`docs-keeper`, `versioner`) are **always available** when kaizen is installed. The profile only controls whether your `CLAUDE.md` and rules **document** them. To upgrade an existing project from `minimal` to `standard`, re-run `/kaizen:init --profile=standard --force` (requires existing-config approval).

#### What gets written

| File | Created by default | `--minimal` |
|---|---|---|
| `CLAUDE.md` | ✓ | ✓ |
| `.claude/settings.json` | ✓ | ✓ |
| `.claude/settings.local.json.example` | ✓ | ✗ |
| `.claude/rules/<topic>.md` (path-scoped) | ✓ (preset-dependent) | ✗ |
| `.claude/agents/code-reviewer.md` | ✓ | ✗ |
| `.claude/hooks/session-start.sh` | ✓ | ✗ |
| `.claude/hooks/format-on-save.sh` | ✓ (preset-dependent) | ✗ |
| `.gitignore` (appends a section) | ✓ | ✓ |

#### What kaizen never touches

- Anything outside your project directory (`$CLAUDE_PROJECT_DIR`).
- Your source code.
- Your `package.json`, `pyproject.toml`, or any dependency manifest.
- Your git history (no commits, no branches).
- Existing config files **without `--force`**.

## Common scenarios

### Scenario 1 — Brand new empty project

```
mkdir my-new-app && cd my-new-app
git init
claude --plugin-dir ~/kaizen/plugins/kaizen
```

```
/kaizen:init
```

kaizen sees no code and asks: "What kind of project? (typescript / python / go / other)". You pick one. It generates a minimal scaffolding plus a `CLAUDE.md` with placeholders to fill in once you have `package.json`/`pyproject.toml`.

### Scenario 2 — Adopting kaizen in an existing project

```bash
cd /existing/repo
claude --plugin-dir ~/kaizen/plugins/kaizen
```

```
/kaizen:init
```

kaizen detects your stack and maturity. If the project is **mature** (50+ source files), it offers to run **archeology mode**: an Explore subagent reads your git history and produces a `.claude/rules/lessons.md` with recurring patterns. Say `yes` to enable, `no` to skip.

### Scenario 3 — You already have `CLAUDE.md` from before

```
/kaizen:init
```

kaizen sees existing config and stops. It asks:

> I found existing Claude config: `CLAUDE.md, settings.json`. Options:
> (a) abort, (b) re-run with `--force` (overwrites), (c) merge only missing pieces

Pick `(c)` to add what's missing without touching what you already wrote. Pick `(b)` only if you want a clean reset (commit first!).

### Scenario 4 — Starting over

```bash
git add . && git commit -m "Pre-kaizen reset"
```

```
/kaizen:init --force
```

Overwrites everything. The commit is your safety net.

### Scenario 5 — You only want CLAUDE.md, nothing else

```
/kaizen:init --minimal
```

Generates just `CLAUDE.md` + `settings.json` + a `.gitignore` patch. No rules, agents, or hooks.

### Scenario 6 — Force a specific preset

```
/kaizen:init --preset typescript-node
```

Useful if detection is wrong (e.g., a polyglot monorepo where the TypeScript piece is what you want config for).

## After `/kaizen:init` finishes

You'll see a summary like:

```
✓ kaizen init complete

Detected: typescript,frontend / pnpm / small
Preset:   typescript-node

Files created:
  - CLAUDE.md (52 lines)
  - .claude/settings.json
  - .claude/rules/testing.md
  - .claude/agents/code-reviewer.md
  - .claude/hooks/session-start.sh (chmod +x done)
  - .claude/hooks/format-on-save.sh (chmod +x done)
  - .gitignore (appended 3 lines)

Suggested next steps:
  1. Review CLAUDE.md and adjust the "Commands" section
  2. Run `claude` and try the code-reviewer agent
  3. When you start writing tests, /kaizen:learn will tune rules/testing.md
```

**What to do immediately:**

1. **Review `CLAUDE.md`**. Adjust the `## Commands` section to match what your project actually runs. Delete lines for commands you don't have.
2. **Restart Claude Code** or run `/reload-plugins` so it loads the new config.
3. **Try the code-reviewer agent**: `@code-reviewer review src/`.

**Optional:**

- Copy `.claude/settings.local.json.example` → `.claude/settings.local.json` and add personal overrides (extra permissions, different model).
- Commit `CLAUDE.md` and `.claude/` (minus `settings.local.json`, which is auto-gitignored).

### `/kaizen:learn [subcommand] [flags]` {#kaizenlearn-arguments}

Analyzes recent git activity and proposes updates to `CLAUDE.md` / `.claude/rules/`. **Never modifies your config silently** — proposals are written to `.claude/kaizen/pending.md` for review.

#### Subcommands

| Subcommand | Action |
|---|---|
| *(none)* | Analyze and write up to 3 proposals to `pending.md`. Refuses if `pending.md` already exists (use `apply` or `discard` first). |
| `show` | Print the contents of `pending.md`. |
| `apply` | Apply every proposal in `pending.md` to its target file, then delete `pending.md`. |
| `discard` | Delete `pending.md` without applying. |

#### Flags

| Flag | Meaning |
|---|---|
| `--since=<git-ref>` | Analyze commits since this ref. Examples: `--since=HEAD~25`, `--since=v1.0.0`, `--since=2 weeks ago`. |
| `--limit=<N>` | Analyze the last N commits. Equivalent to `--since=HEAD~<N>` but more intuitive for "just look at the last N". |

**Default range** (no flag): `HEAD~10..HEAD` (last 10 commits). If both `--since` and `--limit` are given, `--since` wins.

The resolved range is **always shown** at the top of the console summary AND the `pending.md` header — you never need to guess what was analyzed.

#### Typical workflow

```
# After a few days of work, see what kaizen suggests:
/kaizen:learn

# Or scope to a specific range:
/kaizen:learn --since=v1.0.0
/kaizen:learn --limit=20

# Review the proposals:
/kaizen:learn show

# Either apply them all:
/kaizen:learn apply

# ...or throw them away if not useful:
/kaizen:learn discard

# You can also EDIT pending.md by hand to refine before applying.
```

#### When to run `/kaizen:learn` (vs other skills)

`/learn` is for **incremental config evolution after work has happened** — NOT for initial deep knowledge seeding.

| Situation | Use this |
|---|---|
| Fresh project, no `CLAUDE.md` yet | `/kaizen:init` |
| You just finished a task and want to ask "did anything emerge worth documenting?" | `/kaizen:learn` |
| `CLAUDE.md` exists but feels stale because the project has grown | `/kaizen:learn --since=<old-tag>` |
| You want to audit current code against existing rules | `/kaizen:analyze` |
| You want a pre-merge gate | `/kaizen:preflight` |

**Recommended cadence**: end of a sprint, end of a feature branch, or after a multi-day chunk of work. Not after every single Claude response — running too frequently produces low-signal proposals and adds friction.

**If you find yourself running `/learn` and consistently discarding proposals**: the default range (`HEAD~10`) may not match your work rhythm. Try `--since=<feature-branch-base>` to scope to the actual change set, or `--limit=<N>` to match your team's typical sprint commit count.

#### What gets proposed

`/kaizen:learn` looks for **patterns in recent commits not yet documented**:

- Recurring file structures (e.g., 5 new `src/services/*.ts` files but Architecture section doesn't mention `services/`).
- Recurring fix patterns (e.g., 3 commits with `fix:` for the same kind of bug → candidate for `## Never do`).
- New libraries introduced and used across files.
- Conventions emerging in new code (e.g., new files all use factory pattern).
- `CLAUDE.md` exceeding ~150 lines → proposes moving a section to `.claude/rules/`.
- Path-specific patterns → proposes new path-scoped rule file.

Maximum **3 proposals per analysis**. Each cites concrete evidence (commit SHAs, file paths, counts).

#### Where proposals live

`.claude/kaizen/pending.md`. The directory is **auto-added to `.gitignore`** the first time `/kaizen:learn` runs — pending proposals are WIP and shouldn't pollute team commits.

You can edit `pending.md` by hand before applying: tweak wording, delete a proposal, change the target section, etc.

#### Signal sources

- **v0.7 (today)**: git only — `git log` and `git diff` from the resolved range.
- **v0.8 (planned)**: optional `--include-session` flag to also analyze the current Claude Code conversation for user corrections.
- **v0.9+ (planned)**: optional `--include-memory` flag to read Claude's auto-memory (with anti-circularity safeguards).

See the [SKILL.md source](../plugins/kaizen/skills/learn/SKILL.md) for the full roadmap with tradeoffs.

#### Limits and safety

- **Never modifies files outside `apply`** — even in analyze mode, nothing in `CLAUDE.md` or `.claude/rules/` is touched until you explicitly `/kaizen:learn apply`.
- **Never proposes deletions** of user-written content. Only append, insert, move, or create new files.
- **Validates before applying**: if a proposal's target section no longer exists, the whole apply stops with a clear error.
- **Never auto-commits**. Changes land in your working tree; you commit when ready.

### `/kaizen:analyze [flags] [show]` {#kaizenanalyze-arguments}

Read-only audit of the current project against its own `CLAUDE.md` and `.claude/rules/*`. Surfaces three kinds of mismatches: best-practice violations, documentation coverage gaps, and architecture drift. **Never modifies any file** other than the report itself.

#### Modes (combinable; no flag = run all three)

| Flag | What it checks |
|---|---|
| `--best-practices` | Violations of conventions stated in CLAUDE.md / rules. Uses a built-in pattern library; unmatched conventions are listed as "Unchecked". |
| `--coverage` | Directories with <20% of files matched by any path-scoped rule. Also flags stale rules whose `paths:` matches no files. |
| `--architecture` | Compares the `## Architecture` section of CLAUDE.md to actual `src/*/`. Also compares Stack section to `package.json` dependencies. |
| `show` | Re-prints the last generated report. Exclusive — ignores other flags. |

#### Built-in pattern library (v0.4)

`--best-practices` can automatically verify these conventions when their keywords appear in CLAUDE.md / rules:

| Convention keyword | Check |
|---|---|
| `named exports only`, `no default exports` | Grep for `^export default` in source files |
| `no console.log` | Grep for `console\.log` outside tests |
| `no any` (TypeScript) | Grep for `: any` and `as any` outside `.d.ts` |
| `no eslint-disable` (without comment) | Grep for `eslint-disable` lacking inline justification |
| `no print() for logging` (Python) | Grep for `print(` outside tests/scripts |
| `no bare except` (Python) | Grep for `except:` |
| `no wildcard imports` (Python) | Grep for `from x import *` |
| `no mutable default arguments` (Python) | Grep for `def f(x=[])` and `def f(x={})` |
| `tests next to source` | Reports source files without a sibling `*.test.*` |

Conventions that don't match any keyword are reported as **"Unchecked — manual review"**, so you always know what kaizen can and can't verify automatically.

#### Typical workflow

```
# Full audit:
/kaizen:analyze

# Just check architecture drift:
/kaizen:analyze --architecture

# Best practices + coverage, skip architecture:
/kaizen:analyze --best-practices --coverage

# Re-display the last report (after some time has passed):
/kaizen:analyze show
```

#### Where the report lives

`.claude/kaizen/analyze-report.md`. The file is **overwritten on every run** (it's output, not state). The `.claude/kaizen/` directory is auto-gitignored (shared with `/kaizen:learn`'s `pending.md`).

#### Report format (excerpt)

```markdown
# kaizen :: analyze report

Generated: 2026-05-18T16:42:01Z
Modes run: --best-practices, --coverage, --architecture

## Best practices
### 3 violations of "No console.log in committed code" (CLAUDE.md:35)
- `src/services/auth.ts:108`
- `src/utils/logger.ts:24`
- `src/components/Debug.vue:42`

### Unchecked conventions
- "Errors are typed. Throw Error subclasses, not strings." — no automated check

## Documentation coverage
### Directories with low rule coverage
- `src/composables/` — 0/12 files covered

## Architecture drift
### Exists in src/ but not documented
- `src/composables/` — 12 files

## Suggestions
- Add a `.claude/rules/composables.md` with `paths: ["src/composables/**"]`.
```

#### Limits and safety

- **Read-only** by hard rule. Cannot Edit/Write anything except the report file and (one-time) `.gitignore`.
- **No auto-fix**. Findings are surfaced; action is the user's call.
- **Bounded output**. If a check returns >50 matches, only the first 20 are listed with a `+N more` summary.
- **No external tool dependencies**. v0.4 doesn't shell out to `npm`/`pip`/etc. — that's deferred to v0.5+ (`--dependencies`).

### `/kaizen:preflight [show]` {#kaizenpreflight-arguments}

Pre-merge sanity check. Runs deterministic checks (tests, typecheck, lint) sequentially, then dispatches two specialized agents (security review + commit message suggestion) **in parallel**, then aggregates everything into a single **SHIP / HOLD / BLOCK** verdict. Use it before committing or opening a PR.

#### Subcommands and flags

| Arg | Action |
|---|---|
| *(none)* | Run full preflight — all 5 checks |
| `show` | Re-print the last report from `.claude/kaizen/preflight-report.md` without re-running |
| `--base=<ref>` | Override the auto-detected base ref. Examples: `--base=develop`, `--base=v1.0.0`, `--base=HEAD~3`. If the ref doesn't exist, kaizen stops with an error (no silent fallback). |
| `--skip=<checks>` | Skip specific checks. CSV of: `tests`, `typecheck`, `lint`, `security`, `commit`. Example: `--skip=security,commit` runs only the deterministic trio. Skipped checks appear in the report and never affect the verdict. |
| `--auto-fix` | **Opt-in mutation**. Before running lint, applies safe auto-fixes per stack (`eslint --fix` + `prettier --write` for JS/TS; `ruff check --fix` + `ruff format` for Python; `gofmt -w` for Go; `cargo fmt` for Rust). Warns if git tree is dirty. Files modified are listed in the report header. |

Flags combine freely: `/kaizen:preflight --base=develop --skip=security --auto-fix`. `show` is exclusive — ignores other flags.

**`--auto-fix` safety**: it's the only way kaizen modifies source code anywhere. The default behavior remains strictly read-only. When used:
- Run on a clean git tree if possible (warn surfaces otherwise).
- The list of modified files goes in the report so you can `git diff` and inspect.
- If a subsequent step fails after auto-fix already ran, files stay modified (no rollback) — you can `git checkout -- .` to undo if you don't like the result.

(v0.9 will add: risk-aware sizing for the security agent; commit style auto-detection from `git log`.)

#### What gets checked

| Phase | Check | How |
|---|---|---|
| 1 (deterministic, sequential) | Tests | Auto-detects `<pm> test` (or `pytest` / `go test` / `cargo test`). Skipped if no command resolvable. |
| 1 | Typecheck | `npx tsc --noEmit` (TS) / `mypy .` (Python) / `go vet ./...` (Go) / `cargo check` (Rust). Skipped if tooling absent. |
| 1 | Lint | `npx eslint .` (JS/TS) / `ruff check .` (Python). Skipped otherwise. |
| 2 (LLM, parallel) | Security review | `preflight-security` agent reads ONLY changed files vs base ref. Reports findings by severity (critical/high/medium/low). |
| 2 (LLM, parallel) | Commit message | `commit-suggester` agent analyzes the diff, returns a Conventional Commits message + 2 alternatives. |

The two LLM agents run **simultaneously** in fresh subagent contexts — neither blocks the other.

#### Verdict tiers

| Verdict | When |
|---|---|
| **BLOCK** | Tests failed OR typecheck failed OR security has `critical` findings |
| **HOLD** | Lint has errors (not just warnings) OR security has `high` findings |
| **SHIP** | Everything else (passes, skips, only warnings, only low/medium findings) |

Skipped checks (no tooling installed) **never** trigger a verdict — they're reported but don't block.

#### Base ref auto-detection

When `--base=<ref>` is NOT given, `/kaizen:preflight` compares your current state against a base ref:

| Current branch | Base ref used |
|---|---|
| `main` | `HEAD~1` (last commit) |
| `master` | `HEAD~1` |
| any other branch | `main` (if exists), else `master`, else `HEAD~1` |

Override with `--base=<ref>` whenever needed (e.g., git-flow with `develop` as the integration branch).

#### Typical workflow

```
# Before committing, gate the change:
/kaizen:preflight

# Read the verdict + summary in console. Full report:
/kaizen:preflight show

# Make fixes for any HOLD/BLOCK issues, then re-run:
/kaizen:preflight

# Once SHIP, commit (use the suggested message or your own):
git add . && git commit -m "feat(api): add zod validation to user endpoints"
```

#### Example output (console)

```
╔══════════════════════════════════════════════╗
║  PREFLIGHT — HOLD ⚠                          ║
║  0c · 1h · 3m · 0l                           ║
╚══════════════════════════════════════════════╝

✓ Tests       (47 passed, 0 failed)
✓ Typecheck   (0 errors)
⚠ Lint        (2e, 5w)
⚠ Security    (0c / 1h / 3m / 0l)
ℹ Commit msg  (feat(api): add zod validation to user endpoints)

Verdict: HOLD. Lint errors must be fixed and 1 high security finding to address.

Full report: .claude/kaizen/preflight-report.md
  /kaizen:preflight show   # re-print the report
  /kaizen:preflight        # re-run after fixes
```

#### Architecture (the agents involved)

`/kaizen:preflight` doesn't do the LLM work itself — it **delegates** to two plugin-level agents:

- **`preflight-security`**: read-only auditor that checks the diff for hardcoded secrets, injection, auth gaps, unsafe deserialization, path traversal, weak crypto, CORS/CSRF issues, and secret leaks in logs/errors. Returns findings tagged with severity, or `"No security findings."` when clean.
- **`commit-suggester`**: analyzes the diff via `git diff` / `git diff --stat`, picks the dominant Conventional Commits type (`feat`/`fix`/`refactor`/etc.), produces a primary message + 2 alternatives + optional body. Imperative tense, ≤72 chars subject.

Both are plugin agents (live in `plugins/kaizen/agents/`) — they're **not** the `code-reviewer.md` that `/kaizen:init` generates in your project. That one stays user-customizable for manual general-purpose review. No overlap.

#### Limits and safety

- **Read-only by default** except for the report file. The only exception is `--auto-fix`, which is opt-in and runs your configured formatters/linters (kaizen itself never edits files manually).
- **Never auto-commits** — even with SHIP verdict, even with `--auto-fix`.
- **Bounded output**: deterministic check commands have output capped at 50 lines (tail kept).
- **Spawns at most 2 subagents per run**, both in parallel. No recursive spawning.
- **Changed-files-only scope** for security agent — token cost grows with change size, not project size.
- **`--base` validation is strict**: if the ref doesn't exist, kaizen stops rather than silently falling back. Typos surface as errors.
- **`--skip` requires at least one check left**: rejects `--skip=tests,typecheck,lint,security,commit` (everything skipped → nothing to do).

### `/kaizen:plan <spec-path> [list|show <plan-id>]` {#kaizenplan-arguments}

Auto-planner. Reads a written specification document and produces a **structured, dependency-ordered, annotated task tree**. Dispatches `plan-context` and `plan-decomposer` agents in parallel; synthesizes their outputs into the final plan.

#### Args and flags

Exactly **one input source** is required. Flags can combine.

| Arg | Action |
|---|---|
| `<path-to-spec>` | Generate a new plan from a spec file. Any text file works (`.md`, `.txt`, `.rst`, `.adoc`, README, SPEC, plain). |
| `--from-prompt="..."` | Use the quoted string as the spec content directly — no file needed. Useful for quick ad-hoc planning. |
| `--from-issue=<N>` | Fetch a GitHub issue via `gh issue view <N>`. Body + comments become the spec. Requires `gh` CLI installed and authenticated. |
| `--seed-todos` | After writing the plan, also push each task into TodoWrite as a pending entry. Use when you intend to start executing right away. |
| `list` | List all plans saved in `.claude/kaizen/plans/`. Exclusive. |
| `show <plan-id>` | Print a specific plan verbatim. `<plan-id>` is the filename without `.md`. `show latest` resolves to the most recent. Exclusive. |

Specifying multiple input sources (e.g., `<path>` and `--from-prompt` together) is an error.

#### Auto-conversion of binary formats (v0.9+)

When the appropriate converter is installed on PATH, kaizen handles binary specs transparently:

| Format | Required tool | Install |
|---|---|---|
| PDF (`.pdf`) | `pdftotext` (from poppler) | macOS: `brew install poppler` · Linux: `sudo apt install poppler-utils` |
| DOCX / ODT / RTF / EPUB / MOBI | `pandoc` | macOS: `brew install pandoc` · Linux: `sudo apt install pandoc` |
| `.pages` | (no good converter) | Export from Pages to PDF first |

Converted files **persist** at `.claude/kaizen/converted/<basename>.txt` so you can inspect what kaizen actually extracted. Subsequent re-runs reuse the conversion. The directory is gitignored.

If the required converter is NOT installed, kaizen surfaces both options:
- Install the tool (kaizen handles future conversions automatically), or
- Convert manually and re-run with the `.txt`/`.md` path.

#### Typical workflows

```
# File-based spec:
/kaizen:plan docs/specs/auth-rewrite.md

# Quick inline planning:
/kaizen:plan --from-prompt="Add user search with autocomplete to the products page"

# From a GitHub issue:
/kaizen:plan --from-issue=42

# PDF spec (auto-converts if pdftotext is installed):
/kaizen:plan docs/specs/contract.pdf

# Plan + immediately start executing in this session:
/kaizen:plan docs/specs/sprint-5.md --seed-todos

# Combine: GitHub issue + seed todos:
/kaizen:plan --from-issue=42 --seed-todos

# Browse / re-read:
/kaizen:plan list
/kaizen:plan show latest
```

#### What gets generated

A plan file at `.claude/kaizen/plans/<slug>-<YYYYMMDD-HHMM>.md`. **Plans accumulate** — unlike `/learn`'s `pending.md` or `/analyze`'s `analyze-report.md` (overwritten each run), re-planning the same spec produces a new file with a different timestamp. This lets you compare plan evolutions.

#### Plan structure

```markdown
# Plan: <spec-name>

Generated: <ISO 8601>
Plugin version: 0.6.0
Spec source: <path>
Tasks: <N>

## Project context (auto-detected)
Stack: TypeScript / Vue 3 / Quasar / Pinia
Convention notes: <2-3 lines>
**Key areas potentially affected**: src/api/, src/stores/

---

## Task 1: Replace mock auth with JWT issuance
**Type**: feat
**Complexity**: medium (2-8h)
**Impact areas**: `src/api/auth/`, `src/stores/user.ts`
**Depends on**: none
**Risks**: schema migration of `users` table required

### Description
Replace the dev mock auth handler with real JWT issuance to enable cross-service authentication.

### Acceptance criteria
- [ ] `/api/login` returns JWT signed with `JWT_SECRET`
- [ ] Token TTL = 24h, refresh token TTL = 7d
- [ ] Existing session middleware unchanged

### Suggested approach
Use `jsonwebtoken` (already in deps). Add `JWT_SECRET` to env validation.

---

## Task 2: ...

## Summary
- Total tasks: 8 (5 feat, 2 test, 1 chore)
- Foundational (no deps): Tasks 1, 4
- Estimated effort: medium-to-large
```

#### Task annotations

Each task is annotated with:

| Field | Values |
|---|---|
| `type` | `feat` / `fix` / `refactor` / `docs` / `test` / `chore` / `infra` / `spike` |
| `complexity` | `trivial` (<30min) / `small` (1-2h) / `medium` (2-8h) / `large` (1-3d) / `epic` (split me) |
| `impact areas` | Directories likely touched, inferred from project context |
| `depends on` | Other tasks that must complete first (or `none`) |
| `risks` | One-line if the area is flagged critical (auth, payments, migrations); `none` otherwise |
| `acceptance criteria` | 2-5 specific testable bullets |

Tasks are **ordered by dependencies**, not by their appearance in the spec.

#### Typical workflow

```
# Generate a plan from a spec file:
/kaizen:plan docs/specs/auth-rewrite.md

# Read the plan in detail:
/kaizen:plan show auth-rewrite-20260519-1030

# See all plans accumulated:
/kaizen:plan list

# Edit the plan file by hand if needed (it's just markdown), then execute manually.
# Re-plan later (e.g., after spec changes): produces a new file with a new timestamp.
```

#### Architecture (the agents involved)

`/kaizen:plan` is a 4-phase orchestrator:

1. **Phase 0 — validate**: extension check, binary detection, file read.
2. **Phase 1 — setup**: light project signals (existence of CLAUDE.md, package.json, etc.).
3. **Phase 2 — parallel agents** (two `Task` calls in one message):
   - `plan-context` profiles the project (stack, architecture, conventions, key areas).
   - `plan-decomposer` reads ONLY the spec and produces a raw task list.
4. **Phase 3 — synthesis** (in the skill, no third agent): cross-references each task with project context to add impact areas, dependencies, risks; reorders by dependency; caps at 20 tasks.
5. **Phase 4 — write**: produces the plan file under `.claude/kaizen/plans/`.

#### Limits and safety

- **Strictly read-only** except for the plan file. Never modifies source code, never executes the plan.
- **Max 20 tasks per plan in v0.6.** If the spec produces more, decomposer groups related tasks. If still too many, the report notes "spec may be too broad — consider splitting".
- **Spec size warning** if >2000 lines or >100 KB — proceeds but notes large input in the plan header.
- **No external API calls** in v0.6 — purely local file analysis.
- **No execution mode** in v0.6 — `--execute` is a v0.7+ concern (autonomy boundaries, checkpointing).

#### Composition with other skills

Independent in v0.6. You can manually chain:

```
/kaizen:analyze --architecture     # see current architecture
/kaizen:plan docs/specs/new.md     # plan against current state
# (work the tasks)
/kaizen:preflight                  # gate before commit
/kaizen:learn                      # propose config updates from what was done
```

v0.7 may add explicit composition flags (e.g., `--seed-todos` to push plan tasks into TodoWrite).

### `/kaizen:docs [show] [--base=<ref>] [--since=<ref>] [--limit=<N>]` {#kaizendocs-arguments}

Analyzes recent changes for **user-facing documentation gaps**. Spawns the `docs-keeper` plugin agent, which reads the diff and identifies which docs may be stale. **Never edits documentation** — surfacing only.

Mirror skill to `/kaizen:learn` (which updates internal config docs in `CLAUDE.md`/rules) but scoped to user-facing docs (`README.md`, `docs/`, examples, CHANGELOG mentions).

#### Subcommands and flags

| Arg | Action |
|---|---|
| *(none)* | Analyze current state vs auto-detected base ref. |
| `show` | Re-print last report from `.claude/kaizen/docs-report.md`. Exclusive. |
| `--base=<ref>` | Override base ref (same logic as `/preflight`). |
| `--since=<ref>` | Analyze commits since this ref. |
| `--limit=<N>` | Analyze the last N commits. |

#### Categories checked

- Public API surface changes (new/renamed/removed exports)
- CLI flag/command changes
- Configuration schema changes
- Behavioral changes (breaking changes, default changes)
- Stale examples (renamed function still appears in docs)
- Architecture/structure changes

#### Typical workflow

```
# After implementing a feature, check if docs need updating:
/kaizen:docs

# Review:
/kaizen:docs show

# Update the flagged files manually, then optionally re-run to confirm clean.
```

#### Limits

- Read-only. No edits to docs or source.
- Bounded to 50 findings / 20 files sampled when diff is huge.
- Never suggests creating new doc files (only "consider creating `README.md`" if NONE exist and changes are user-facing).

---

### `/kaizen:bump [show] [--base=<ref>] [--since=<ref>] [--limit=<N>]` {#kaizenbump-arguments}

Suggests a semver bump (major/minor/patch) based on recent changes. Spawns the `versioner` plugin agent, which reads the diff + commit messages + version manifest. Detects changesets if `.changeset/config.json` exists. **Read-only** in v0.10 (suggestion only).

#### Subcommands and flags

| Arg | Action |
|---|---|
| *(none)* | Analyze since most recent git tag (fallback `HEAD~10`). |
| `show` | Re-print last report from `.claude/kaizen/bump-report.md`. Exclusive. |
| `--base=<ref>` | Override base ref. |
| `--since=<ref>` | Analyze commits since this ref. |
| `--limit=<N>` | Analyze the last N commits. |

`--apply` is **deferred to v0.11** — v0.10 is suggestion-only. To apply: follow the report's "Apply guidance" section manually.

#### Supported version manifests in v0.10

| File | Stack | Version field |
|---|---|---|
| `package.json` | JS/TS | `.version` |
| `pyproject.toml` | Python | `project.version` (PEP 621) OR `tool.poetry.version` |
| `Cargo.toml` | Rust | `package.version` |

Other formats: surfaced as "manual bump required" — no incorrect guessing.

#### Semver classification

- **`major`** — breaking changes (removed/renamed public API, incompatible signature changes, `BREAKING CHANGE:` in commit body, `feat!:` / `fix!:` conventional commit syntax).
- **`minor`** — new functionality, backward-compatible (Conventional Commits `feat:`).
- **`patch`** — bug fixes, refactors, docs, tests, chores (Conventional Commits `fix:`/`refactor:`/`docs:`/`test:`/`chore:`/`perf:`/`style:`/`build:`/`ci:`).

For mixed-type diffs: highest applicable wins (any breaking → major; any feat → minor; else patch).

#### Typical workflow

```
# After a sprint of work:
/kaizen:bump

# Review:
/kaizen:bump show

# Apply (manually in v0.10):
# - If changesets mode: paste draft changeset into .changeset/<slug>.md
# - If direct mode: edit the version field in your manifest

# Tag and commit per your release process.
```

---

### `/kaizen:finish [show] [--base=<ref>] [--skip=<phases>] [--auto-fix]` {#kaizenfinish-arguments}

The **end-of-task ritual**. Runs everything you'd want to check before commit/PR in a single command. Combines `/preflight`'s checks with `/bump`'s version suggestion and `/docs`'s documentation gap analysis.

**Architecturally**, this is the first kaizen skill to spawn **4 agents in parallel** in a single message: `preflight-security`, `commit-suggester`, `versioner`, `docs-keeper`.

#### Subcommands and flags

| Arg | Action |
|---|---|
| *(none)* | Full run: deterministic checks (tests/typecheck/lint) + 4 parallel agents + unified verdict. |
| `show` | Re-print last report from `.claude/kaizen/finish-report.md`. Exclusive. |
| `--base=<ref>` | Override the auto-detected base ref. |
| `--skip=<phases>` | Skip phases. CSV of: `tests`, `typecheck`, `lint`, `security`, `commit`, `bump`, `docs`. |
| `--auto-fix` | Same as `/preflight --auto-fix`: opt-in mutation. Applies lint/format fixes before checking. Only mutation path. |

#### Phases

1. **Setup** — resolve base ref, enumerate changes, detect stack + manifests.
2. **Optional auto-fix** (only if `--auto-fix`).
3. **Deterministic checks** (sequential, Bash): tests → typecheck → lint.
4. **Parallel agents** (single message, up to 4 Task calls): security review + commit msg + version bump + docs gaps.
5. **Verdict + report** — aggregated SHIP/HOLD/BLOCK with per-concern guidance.

#### Verdict rules

| Verdict | When |
|---|---|
| **BLOCK** | tests failed OR typecheck failed OR `critical` security finding |
| **HOLD** | lint errors OR `high` security finding OR `high` docs finding |
| **SHIP** | everything else |

**Bump and docs are advisory** — they appear in the report but don't gate the verdict (the user calls those judgments).

#### Typical workflow

```
# At task end:
/kaizen:finish

# Read the verdict + checklist:
/kaizen:finish show

# Address HOLD/BLOCK issues, re-run until SHIP:
/kaizen:finish

# Then commit (use the suggested message), bump (apply manually per /bump), update docs (per /docs findings).
```

#### When to use `/finish` vs the individual skills

- **`/finish`** — closing a meaningful chunk of work. One report, one ritual.
- **`/preflight`** — just want to verify before committing (no bump/docs analysis).
- **`/bump`** alone — when you specifically need the version recommendation.
- **`/docs`** alone — when you want to audit docs without running tests.

`/finish` reuses the same plugin agents — no duplication, just one orchestrated invocation.

## Visibility layer (v0.11+)

Three additions that surface kaizen state in the UI:

### Statusline

`/kaizen:init` generates `.claude/hooks/statusline.sh` for all profiles. Declared in `settings.json` as the `statusLine` command. Renders a single line at the bottom of Claude Code's TUI showing:

```
[opus-4.7] my-app ⎇ feat/auth  ✓ SHIP  ·  ⚠ learn pending  ·  📋 2 plan(s)  ·  5 modified
```

Components (each optional, only shown if applicable):

| Segment | Source |
|---|---|
| `[model]` | Session payload `.model.display_name` |
| `dir` | basename of cwd |
| `⎇ branch` | `git branch --show-current` |
| `✓/⚠/✗ verdict` | Last `/kaizen:finish` verdict from `.claude/kaizen/finish-report.md` |
| `⚠ learn pending` | If `.claude/kaizen/pending.md` exists |
| `📋 N plan(s)` | Count of plans in `.claude/kaizen/plans/` modified in last 7 days |
| `N modified` | `git status --porcelain` line count |

Gracefully degrades if `jq` or `git` are absent. Customize by editing the script — it's yours.

### Subagent statusline (plugin-level)

When `/preflight`, `/plan`, or `/finish` run in parallel multi-agent mode, the subagent statusline shows which kaizen agent is currently active:

```
🔒 security review running…
📦 version bump running…
📚 doc gap check running…
```

Mapped from agent name to descriptive label (preflight-security → 🔒 security review, etc.). Configured via `plugins/kaizen/settings.json`'s `subagentStatusLine` key — no project-level setup needed; just works when kaizen is installed.

### Output style `kaizen-terse` (opt-in)

`/kaizen:init --profile=advanced` writes `.claude/output-styles/kaizen-terse.md`. To activate:

```json
// .claude/settings.json
{ "outputStyle": "kaizen-terse" }
```

Or pick interactively via `/output-style` if your Claude Code version supports it.

What it enforces:
- No preambles ("Sure!", "Of course!", "I'll start by…")
- No narration of upcoming actions
- No closing summaries of what just happened
- Lead with the answer, context after
- Match response length to question

Uses `keep-coding-instructions: true` so default software-engineering task instructions stay intact — only the terseness layer is added.

Return to default by setting `"outputStyle": "default"` or removing the key.

## Project agent ecosystem (v0.12+, `--profile=advanced`)

When you run `/kaizen:init --profile=advanced`, kaizen writes 6 project-level agents to `<project>/.claude/agents/`. These are **distinct from kaizen's plugin agents** — they're yours, customizable, and Claude auto-invokes them based on what you ask for in conversation.

### The 6 agents and when each gets used

| Agent | Auto-invocation triggers | Read-only? |
|---|---|---|
| `test-writer` | "Write tests for X"; new functionality added without tests | No (writes test files) |
| `refactor-helper` | "Refactor X to Y"; "extract this into a helper"; "deduplicate this" | No (modifies code per the refactor) |
| `documentation-writer` | "Write a README section about X"; "add docstrings"; "update CHANGELOG" | No (writes docs) |
| `dependency-auditor` | "Audit deps"; "any outdated packages?"; "vulnerabilities?" | **Yes** — runs audit tools, never installs/updates |
| `security-auditor` | "Audit security of the auth system"; "review payments for security" | **Yes** — read-only, surfaces findings |
| `architecture-advisor` | "Should I use X or Y?"; "does this fit the architecture?" | **Yes** — advises, never writes code |

Plus `code-reviewer` (shipped in all profiles) for comprehensive review on demand.

### How they differ from plugin-level agents

| Plugin agents (used by kaizen skills) | Project agents (used by Claude generally) |
|---|---|
| `preflight-security`, `commit-suggester`, `versioner`, `docs-keeper`, `plan-context`, `plan-decomposer` | `code-reviewer`, `test-writer`, `refactor-helper`, `documentation-writer`, `dependency-auditor`, `security-auditor`, `architecture-advisor` |
| Live in plugin tree (`plugins/kaizen/agents/`) | Live in project (`<project>/.claude/agents/`) |
| Invoked by kaizen skills (`/preflight`, `/finish`, etc.) | Auto-invoked by Claude based on conversation |
| You CAN'T customize easily | You CAN customize (it's your project) |
| Scope tuned to skill flow ("Invoked by /X") | Scope tuned to general use ("Use when X happens") |
| Updates ship via kaizen plugin releases | Updates via `/kaizen:init --force` (controlled by kaizen-managed marker) |

### The `kaizen-managed` marker

Each project agent starts with this line in its body:

```html
<!-- kaizen-managed: true (re-init may overwrite — change to `false` or delete this line to claim ownership) -->
```

**On `/kaizen:init --force`**:
- `kaizen-managed: true` → kaizen overwrites the file (you get the latest version).
- `kaizen-managed: false` OR marker absent → kaizen preserves your file (you customized it).

Want to customize an agent and keep it across kaizen updates? Edit the file, change `true` to `false` (or just delete the line). Want to revert to kaizen's version? Re-run `/kaizen:init --force` and the marker decides.

### Stack adaptation

Agent descriptions and stack-specific sections (test runner conventions, security concerns, dep manager commands, etc.) are filled at `/init` time per the detected stack. Run on a Python project → docs-writer knows about Google docstrings; on a TS project → it knows TSDoc.

This uses the same KAIZEN_ENRICH marker system as `CLAUDE.md`. See the agent file body for which markers fill which sections.

### Additional hooks (advanced profile)

Two new hooks complement the agent ecosystem:

| Hook | Event | What it does |
|---|---|---|
| `secret-detector.sh` | `PreToolUse` on Edit/Write | Scans intended content for likely secrets (AWS keys, GitHub PATs, JWTs, etc.). **Blocks the write** (exit 2) if found. Same-line `noqa: secret` marker bypasses |
| `dependency-changed.sh` | `PostToolUse` on Edit/Write | Self-filters to manifest files. When `package.json`/`pyproject.toml`/`Cargo.toml`/etc. changes, suggests invoking `@dependency-auditor` or running audit commands |

These are wired into `.claude/settings.json` only for `--profile=advanced`.

## Troubleshooting

### "Skill `/kaizen:init` not found"

The plugin isn't loaded. Either:
- You forgot `--plugin-dir <path>` when launching Claude Code.
- The path you passed doesn't contain `.claude-plugin/plugin.json`. The correct path ends in `plugins/kaizen/`, not just `kaizen/`.
- You installed the plugin from a marketplace but didn't restart Claude Code afterwards. The install message will say "Restart Claude Code to load new plugins" when restart is needed.

### `detect.sh: jq: command not found`

Install `jq`:

```bash
brew install jq          # macOS
sudo apt install jq      # Debian/Ubuntu
```

### "Permission denied" when kaizen tries to write

You're running kaizen from a directory you don't own (e.g., a system path). Run from a project you own.

### `detect.sh` output looks wrong

Run it manually to see what's happening:

```bash
bash ~/kaizen/plugins/kaizen/skills/init/scripts/detect.sh
```

If `stack` says `generic` for what should be a TypeScript project, check:
- Is there a `package.json` at the repo root? (If it's nested under `apps/`, detection misses it in v0.1.0.)
- Did you `cd` into the right directory?

Workaround until v0.2: use `--preset` to override.

### kaizen overwrote my `CLAUDE.md` even though I didn't pass `--force`

This should never happen. If it did:
1. Recover from git: `git restore CLAUDE.md`.
2. File an issue with the exact command and Claude Code version.

### The hooks don't run

Two possible causes:
- The scripts aren't executable. Check: `ls -l .claude/hooks/`. They should show `rwxr-xr-x`. Fix: `chmod +x .claude/hooks/*.sh`.
- Claude Code session started before the hooks existed. Restart Claude Code (or `/reload-plugins`).

### Hooks fire but do nothing

Check the script directly:

```bash
echo '{"tool_input":{"file_path":"./test.ts"}}' | bash .claude/hooks/format-on-save.sh
```

You should see `prettier` or `ruff` run. If not, the formatter binary isn't on `PATH`. Install it.

## FAQ

**Q: Will kaizen change my source code?**
No. It only writes to `CLAUDE.md`, `.claude/`, and appends to `.gitignore`.

**Q: Can I undo a `/kaizen:init` run?**
With `git restore` if you had a clean working tree. Without git, no — make a backup before running `--force`.

**Q: Does kaizen send my code anywhere?**
No. `detect.sh` runs locally and returns a small JSON. Claude reads template files locally. Nothing in this skill makes network calls.

**Q: What happens if my project mixes stacks?**
`detect.sh` reports a CSV like `typescript,python`. The preset picker uses the first match in priority order (`typescript-node` > `python` > `generic`). Use `--preset python` to override if the priority is wrong.

**Q: Can I customize the templates?**
Yes — clone kaizen, edit files in `plugins/kaizen/skills/init/templates/<preset>/`, point `--plugin-dir` at your fork. For permanent customization, fork and publish your own marketplace.

**Q: Does kaizen work with Windows?**
Not officially in v0. The hooks use bash scripts (`.sh`) and `jq`. WSL works. Native Windows support is planned for v0.2.

**Q: Will future kaizen commands be available?**
v0.1.0 ships only `/kaizen:init`. Planned for v0.2+:
- `/kaizen:learn` — auto-update `CLAUDE.md` with diff-review after tasks.
- `/kaizen:analyze` — deep audit (best-practices, deps, upgrades).
- `/kaizen:plan` — turn a spec doc into a task tree.
- `/kaizen:preflight` — pre-PR chain.

**Q: Should I commit the generated files?**
Yes. Commit `CLAUDE.md` and the whole `.claude/` directory **except** `settings.local.json` (auto-gitignored). Your team should share the same Claude config.

**Q: I want different config than the template provides.**
Edit the generated files directly. They're yours now. kaizen won't touch them again unless you re-run with `--force`.

## Getting help

- Architecture detail: [architecture.md](./architecture.md)
- Decision flow with diagrams: [runtime-flow.md](./runtime-flow.md)
- Issue tracker: https://github.com/alexdeploy/kaizen/issues
