# Architecture — kaizen runtime

> How the plugin works once it's installed and a user invokes a command. This document is about runtime behavior, not about how to develop kaizen itself.

**This document covers three skills (v0.4.0):**
- `/kaizen:init` — bootstrap a project's Claude Code config. Sections 1-8 below.
- `/kaizen:learn` — propose updates to that config based on git activity. Section 9.
- `/kaizen:analyze` — read-only audit of code against the config. Section 11.

All three skills share the same plugin tree and runtime model. They differ in what they read, what they write, and the directives that govern each. `/init` and `/learn` can mutate config (the former generates, the latter applies user-approved proposals); `/analyze` is strictly read-only.

## Mental model

There are always **two file trees** during a kaizen invocation:

```
┌───────────────────────────────┐        ┌───────────────────────────────┐
│  PLUGIN TREE (read-only)      │        │  USER PROJECT TREE (target)   │
│  ~/.claude/plugins/cache/     │ writes │  $CLAUDE_PROJECT_DIR          │
│  kaizen/...                   │ ────▶  │  (the user's repo / cwd)      │
│                               │        │                               │
│  • SKILL.md (instructions)    │ reads  │  • CLAUDE.md (generated)      │
│  • detect.sh                  │ ◀───── │  • .claude/ (generated)       │
│  • templates/...              │        │  • source code (pre-existing) │
└───────────────────────────────┘        └───────────────────────────────┘
```

The **plugin tree** is immutable at runtime. kaizen only reads from it. The **user project tree** is what kaizen writes into. Templates flow one direction only: plugin → user.

## Components

| Component | Type | Lifetime | Purpose |
|---|---|---|---|
| [`SKILL.md`](../plugins/kaizen/skills/init/SKILL.md) | LLM prompt | Loaded into context when `/kaizen:init` is invoked | Drives the decision tree. The "brain". |
| [`bin/kaizen-detect`](../plugins/kaizen/bin/kaizen-detect) | Bash script | Runs once per invocation (bash injection) | Deterministic project fingerprint. On `PATH` because it lives in `bin/`. |
| [`templates/_shared/`](../plugins/kaizen/skills/init/templates/_shared/) | Static files | Read on demand by SKILL.md | Files Claude writes regardless of stack. |
| [`templates/<preset>/`](../plugins/kaizen/skills/init/templates/) | Static files | Read on demand by SKILL.md | Stack-specific files (CLAUDE.md, settings.json, rules, hooks). |
| **The Claude agent** | LLM session | Active during invocation | Interprets SKILL.md, calls bash for detection, reads templates, writes to user project. |

### `SKILL.md` — the orchestrator

This is the only "active" component. Everything else is data or scripts that SKILL.md instructs Claude to consume.

**What it contains:**
- Frontmatter: `disable-model-invocation: true` (user-triggered only), `argument-hint`.
- A bash injection (`` !`detect.sh` ``) that runs at prompt-time so Claude sees the fingerprint as input.
- Seven-step protocol (read fingerprint → branch on existing config → branch on maturity → pick preset → generate files → optional archeology → report).
- Hard rules (never overwrite without `--force`, never write outside cwd, never commit, chmod hooks).

**What it does NOT do:**
- It does not execute any code itself. It only **instructs** Claude.
- It does not call APIs or write files directly. Claude does that via its tools (Bash, Read, Write, Edit).

### `kaizen-detect` — the deterministic eye

Runs **once** per `/kaizen:init` invocation via bash injection in `SKILL.md` (just `` !`kaizen-detect` ``). Output is JSON to stdout.

Lives in `plugins/kaizen/bin/` because Claude Code automatically adds plugin `bin/` directories to the Bash tool's `PATH` while the plugin is enabled. This is why the bash injection can omit variable substitution — important because Claude Code's permission check rejects `${...}` patterns in skill bash injections.

**Why a script and not pure LLM:**
- Free (no model tokens for file traversal).
- Predictable (a `find` on the same repo always gives the same answer).
- Fast (~50-200ms on small/medium repos).
- LLM does the *reasoning* over the JSON, not the data gathering.

**Output schema** (see [reference: detect schema](#detect-output-schema) below).

### `templates/` — the source of truth for what gets written

Three categories:

1. **`_shared/`** — files written to every project regardless of stack:
   - `.claude/agents/code-reviewer.md`
   - `.claude/hooks/session-start.sh`
   - `.claude/settings.local.json.example`
   - `.gitignore.append` (lines added to user's `.gitignore`)

2. **`<preset>/`** (currently `generic`, `typescript-node`, `python`) — stack-specific files:
   - `CLAUDE.md`
   - `.claude/settings.json`
   - `.claude/rules/<topic>.md` (path-scoped)
   - `.claude/hooks/<event>.sh`

3. **(future) overlays** — composable add-ons (e.g. `+react`, `+fastapi`, `+monorepo`). Not in v0.

**Template substitution variables** (resolved by Claude from `detect` JSON; v0.2+):

| Placeholder | Source | Example |
|---|---|---|
| `{{PROJECT_NAME}}` | `basename` of `cwd` | `my-app` |
| `{{STACK_RAW}}` | `detect.stack` CSV, exact | `typescript,frontend` |
| `{{STACK_FRIENDLY}}` | Claude-derived from `STACK_RAW` + `package.json` | `TypeScript / Vue 3 / Quasar` |
| `{{PACKAGE_MANAGER}}` | `detect.package_manager` | `pnpm` |
| `{{TEST_RUNNER}}` | inferred from `package.json` scripts/deps | `vitest`, `pytest`, `none` |
| `{{HAS_CI}}` | `detect.ci != "none"` | `true` / `false` |

**Enrichment markers** (v0.2+): templates may contain HTML-comment markers like `<!-- KAIZEN_ENRICH:<id> -->`. Claude replaces them with content from a directive registry defined in `SKILL.md`. This is the only way Claude is allowed to add content beyond placeholder substitution. Currently defined:

| Directive id | Where it lives | What Claude does |
|---|---|---|
| `framework_stack` | inside `## Stack` of `CLAUDE.md` | Reads `package.json`, appends `- <Role>: <Lib> v<ver>` bullets for detected frameworks (max 8) |
| `architecture_layout` | inside `## Architecture (brief)` | Globs `src/*/`, appends `` - `src/<dir>/` — <purpose> `` bullets using a known-names lookup |

Outside markers, templates are **rigid** — verbatim after placeholder substitution. Conditional removals (e.g., remove `Test:` line when no test runner) are allowed only per an explicit table in SKILL.md, and each one is logged in the drift report.

## Data flow

```
       (1) /kaizen:init [--args]
              │
              ▼
       ┌────────────────────┐
       │  Claude loads      │
       │  SKILL.md into     │
       │  context           │
       └─────────┬──────────┘
                 │
                 ▼
       ┌────────────────────┐
   (2) │  Bash injection    │   The !`detect.sh` line in SKILL.md
       │  runs detect.sh    │   executes BEFORE Claude sees the prompt.
       └─────────┬──────────┘   Its stdout is interpolated in.
                 │
                 ▼  JSON fingerprint
       ┌────────────────────┐
   (3) │  Claude reasons    │   Reads JSON, picks preset,
       │  over fingerprint  │   decides branch (empty/scaffold/...)
       └─────────┬──────────┘
                 │
                 ▼  (may ask user via interactive prompt)
       ┌────────────────────┐
   (4) │  Claude reads      │   Uses Read tool on
       │  template files    │   templates/_shared/* + templates/<preset>/*
       └─────────┬──────────┘
                 │
                 ▼  in-memory substitution of {{PLACEHOLDERS}}
       ┌────────────────────┐
   (5) │  Claude writes     │   Uses Write tool, target paths under
       │  to user project   │   $CLAUDE_PROJECT_DIR
       └─────────┬──────────┘
                 │
                 ▼
       ┌────────────────────┐
   (6) │  Claude chmod +x   │   For files written to .claude/hooks/
       │  shell scripts     │
       └─────────┬──────────┘
                 │
                 ▼
       ┌────────────────────┐
   (7) │  Claude prints     │   Fixed format: ✓ detected, files created,
       │  summary report    │   files skipped, suggested next steps
       └────────────────────┘
```

## Boundaries

**kaizen writes** (under `$CLAUDE_PROJECT_DIR`):

```
CLAUDE.md
.claude/settings.json
.claude/settings.local.json.example
.claude/rules/*.md
.claude/agents/*.md
.claude/hooks/*.sh         (always chmod +x)
.gitignore                 (appends only, never replaces)
```

**kaizen never touches:**

- Anything outside `$CLAUDE_PROJECT_DIR`.
- Source code in the user's project.
- `package.json`, `pyproject.toml`, or any dependency manifest.
- `.git/` (no commits, no branch ops).
- Existing files at the paths above (without `--force`).

**kaizen may read:**

- Anything under `$CLAUDE_PROJECT_DIR` (via `detect.sh` and Read tool) to inform decisions.
- Template files in the plugin tree.

## Detect output schema

`detect.sh` always emits a JSON object with this exact shape:

```json
{
  "stack": "typescript,frontend",
  "package_manager": "pnpm",
  "maturity": "small",
  "git": {
    "is_repo": true,
    "commits": 47,
    "branch": "main"
  },
  "existing_claude_config": "CLAUDE.md,settings.json",
  "tests_found": 12,
  "ci": "github-actions",
  "cwd": "/Users/alex/projects/my-app"
}
```

| Field | Type | Possible values |
|---|---|---|
| `stack` | string (CSV) | `generic` \| `typescript` \| `javascript` \| `python` \| `go` \| `rust` \| `java` \| `ruby` \| `php` \| `elixir` (optionally `+frontend`, `+backend-node`) |
| `package_manager` | string | `pnpm` \| `yarn` \| `bun` \| `npm` \| `uv` \| `poetry` \| `pipenv` \| `pip` \| `none` |
| `maturity` | string | `empty` (0 src files) \| `scaffold` (1-5) \| `small` (6-50) \| `mature` (50+) |
| `git.is_repo` | bool | true / false |
| `git.commits` | int | 0+ |
| `git.branch` | string | branch name or `"none"` |
| `existing_claude_config` | string (CSV) | empty string if nothing, else CSV of: `CLAUDE.md`, `settings.json`, `skills/`, `agents/`, `hooks/`, `rules/`, `.mcp.json` |
| `tests_found` | int | count of `*.test.*`, `*.spec.*`, `test_*.py`, `*_test.go` |
| `ci` | string | `github-actions` \| `gitlab` \| `circleci` \| `jenkins` \| `none` |
| `cwd` | string | absolute path to user's project root |

## Preset selection logic

The `stack` field maps to a template directory:

| `stack` contains | preset used |
|---|---|
| `typescript` or `javascript` | `typescript-node` |
| `python` | `python` |
| anything else (or `generic`) | `generic` |

Overridden by `--preset <name>` argument. Future versions add `go`, `rust`, `java`, etc.

## Environment variables available at runtime

| Variable | Set by | Used by |
|---|---|---|
| `CLAUDE_PROJECT_DIR` | Claude Code | `detect.sh`, `session-start.sh`, all hook scripts |
| `CLAUDE_SKILL_DIR` | Claude Code (during skill execution) | Bash injections in `SKILL.md` to locate `scripts/` and `templates/` |

## Failure modes and recovery

| Failure | Detection | Behavior |
|---|---|---|
| `detect.sh` errors or non-JSON output | SKILL.md instructs Claude to surface raw output | Abort. No files written. |
| Existing `.claude/` config and no `--force` | `existing_claude_config != ""` | Abort + interactive prompt: abort / force / merge-only. |
| Uncommitted changes touching `.claude/` | (planned for v0.2) | Refuse to write until committed or stashed. |
| Template file missing in plugin | Read tool error | Claude reports the missing template path; aborts. |
| User cwd outside a writable directory | Write tool error | Surfaces filesystem error; aborts. |

## Why this architecture

Four deliberate choices worth knowing:

1. **Deterministic facts, LLM reasoning.** `kaizen-detect` is pure bash because file traversal in a model wastes tokens and can hallucinate. Reasoning over a small JSON is what models are good at.
2. **Templates as data, not code.** Adding a new stack means dropping files in `templates/<new-stack>/`. No SKILL.md changes needed for additions — only when behavior changes.
3. **Hybrid templates (v0.2+): rigid bones + flexible flesh.** Sections like `Commands` and `Never do` are verbatim after placeholder substitution. Sections like `Stack` and `Architecture` have `KAIZEN_ENRICH` markers where Claude fills in detected data. This balances determinism with adaptation: the user knows exactly which sections were customized and which came from the template.
4. **Mandatory drift report.** Every `/kaizen:init` run ends with a per-file list of substitutions, enrichments, and conditional removals applied. No silent customization — if Claude adapted something, it says so.
5. **One LLM session, one invocation.** No subagents spawned for `/kaizen:init` (except optional archeology on mature repos). The skill runs in the user's main context so the user can observe and intervene.

---

# 9. `/kaizen:learn` runtime (v0.3.0+)

> Different goal from `/init`: instead of bootstrapping config, `/learn` **proposes incremental updates** to existing config based on what the project has actually been doing.

## Mental model — three things that exist

```
┌─────────────────────────────┐       ┌─────────────────────────────┐       ┌─────────────────────────────┐
│  PLUGIN TREE (read-only)    │       │  USER PROJECT (mostly read) │       │  PENDING PROPOSALS          │
│  ~/.claude/plugins/cache/   │ reads │  $CLAUDE_PROJECT_DIR        │ reads │  .claude/kaizen/pending.md  │
│                             │ ────▶ │                             │ ────▶ │  (auto-gitignored)          │
│  • SKILL.md (instructions)  │       │  • CLAUDE.md (read)         │       │                             │
│                             │       │  • .claude/rules/* (read)   │       │  Written by analyze mode    │
│                             │       │  • .git/ → log/diff (read)  │       │  Read by show/apply         │
│                             │       │                             │       │  Deleted by apply/discard   │
└─────────────────────────────┘       └─────────────────────────────┘       └─────────────────────────────┘
                                                  │                                       │
                                                  │ writes only in apply mode             │
                                                  ▼                                       │
                                       ┌─────────────────────────────┐                    │
                                       │  Edits to CLAUDE.md /       │ ◀──────────────────┘
                                       │  .claude/rules/*            │
                                       │  + delete pending.md        │
                                       └─────────────────────────────┘
```

## Components

| Component | Type | Lifetime | Purpose |
|---|---|---|---|
| [`skills/learn/SKILL.md`](../plugins/kaizen/skills/learn/SKILL.md) | LLM prompt | Loaded into context when `/kaizen:learn` is invoked | State machine + subcommand dispatch + analyze/apply logic |
| `pending.md` | Markdown file | Created by analyze, consumed by apply/discard | Persistent draft of proposed config changes |

There are **no helper scripts** like `kaizen-detect`. All logic is in the SKILL.md prompt + standard tools (`Read`, `Edit`, `Write`, `Bash(git *)`).

## State machine

```
                       ┌──────────────────────────────┐
                       │  .claude/kaizen/pending.md   │
                       │  exists?                     │
                       └──────────────────────────────┘
                                │
                  ┌─────────────┴─────────────┐
                  │ NO                        │ YES
                  ▼                           ▼
       ┌──────────────────┐         ┌──────────────────────┐
       │  STATE A         │         │  STATE B             │
       │  no pending      │         │  pending exists      │
       └──────────────────┘         └──────────────────────┘
                  │                           │
   /learn (no args)│                          │ /learn (no args)
                  ▼                           ▼
       ┌──────────────────┐         ┌──────────────────────┐
       │  analyze →       │         │  REFUSE              │
       │  write pending   │         │  "use show/apply/    │
       │  → State B       │         │   discard first"     │
       └──────────────────┘         └──────────────────────┘
                                              │
                              ┌───────────────┼───────────────┐
                              │               │               │
                       /learn show     /learn apply    /learn discard
                              │               │               │
                              ▼               ▼               ▼
                       (print file)    (apply edits     (delete
                                        + delete         pending)
                                        pending)         → State A
                                        → State A
```

This prevents proposal accumulation. The user must explicitly resolve a pending batch before generating new proposals.

## `pending.md` schema

Always at `.claude/kaizen/pending.md`. Created with this exact structure:

```markdown
# kaizen :: pending proposals

Generated: <ISO 8601 timestamp>
Plugin version: <plugin version>
Signal sources used: git (range: <ref>..HEAD, <N> commits)

> Review each proposal below. Run `/kaizen:learn apply` to accept all,
> `/kaizen:learn discard` to throw away, or edit this file by hand.

---

## Proposal 1

**Target file**: <path>
**Target section**: <section heading | (new file)>
**Action**: <append | insert after <line> | move <from> to <to> | create new file>

**Content**:
```
<exact text to add, in its target format>
```

**Evidence**:
- <commit SHA>: <commit message> — <what it touched>
- Files affected: <paths>
- Why this matters: <one-sentence rationale>

---

## Proposal 2
...
```

The user **can edit `pending.md` by hand** before applying. Common edits: change the wording in the `Content` block, remove a proposal entirely (delete its `## Proposal N` block), change the target section.

## Boundaries

**`/kaizen:learn` reads**:
- `CLAUDE.md` (always)
- `.claude/rules/*` (always)
- `git log` / `git diff` / `git show` (always)
- `.claude/kaizen/pending.md` (when in show/apply/discard mode)

**`/kaizen:learn` writes**:
- `.claude/kaizen/pending.md` (in analyze mode)
- `.gitignore` (only if `.claude/kaizen/` not already gitignored; one-time append)
- `CLAUDE.md`, `.claude/rules/*` (**only in apply mode**, validated first)

**`/kaizen:learn` never touches**:
- Source code.
- `package.json`, `pyproject.toml`, or any dependency manifest.
- `.git/` (no commits, no branches; only reads).
- Anything outside `$CLAUDE_PROJECT_DIR`.

## Signal sources — current and roadmap

```
                  v0.3 (today)                    v0.4 (planned)               v0.5 (planned)
                  ─────────────                   ──────────────               ──────────────
              ┌──────────────────┐           ┌──────────────────┐         ┌──────────────────┐
              │  git log/diff    │           │  git log/diff    │         │  git log/diff    │
              │                  │           │  + session conv. │         │  + session conv. │
              │                  │           │   (opt-in)       │         │  + auto-memory   │
              │                  │           │                  │         │   (opt-in)       │
              └────────┬─────────┘           └────────┬─────────┘         └────────┬─────────┘
                       │                              │                            │
                       ▼                              ▼                            ▼
                  conservative,             richer (captures             richest (cross-session
                  deterministic             user corrections             learning), needs
                                            not in commits)              anti-circularity
                                                                         safeguards
```

**Why this order**: each step up adds richer signal but also more failure modes. Git is stable and intentional. Session conversation captures real-time guidance but is volatile. Auto-memory is what Claude told itself — most "advanced" but risks self-reinforcement without dedup against current CLAUDE.md content.

Future signal sources will be **opt-in flags** (`--include-session`, `--include-memory`), never default.

## Failure modes

| Failure | Detection | Behavior |
|---|---|---|
| Not a git repo | `git rev-parse --is-inside-work-tree` fails | Refuse. Suggest `git init` + at least one commit. |
| Fewer commits than requested | `git log` returns less | Analyze what exists. Note in report. |
| No CLAUDE.md | File not found | Refuse. Suggest `/kaizen:init` first. |
| `pending.md` malformed during apply | Parse fails | Stop. Print line number. Don't apply any. |
| Target section in apply doesn't exist | `Edit` tool fails | Stop at that proposal. Don't apply remaining. Tell user to edit `pending.md`. |
| `pending.md` already exists (analyze mode) | File exists | Refuse. Tell user to show/apply/discard. |

## Why this architecture

Five deliberate choices specific to `/learn`:

1. **Always file-mediated, never silent.** Proposals live in `pending.md` because a markdown file is auditable, editable, and survives session restarts. In-memory "remembered" proposals would be opaque and fragile.
2. **State machine prevents accumulation.** Refusing to generate new proposals while pending exist is annoying but correct — accumulating drafts is how config files become bloated incoherent messes.
3. **Apply is transactional-ish, not auto-apply.** Even if a user types `/kaizen:learn apply` immediately after the analyze, apply re-reads `pending.md` and validates each target. There's no in-session "memory" of what was just analyzed.
4. **Git only in v0.3 for predictability.** Other signal sources (session, auto-memory) are documented in the SKILL.md roadmap but explicitly out of scope. Each future addition is a separate opt-in flag, never default.
5. **No subagents.** `/learn` runs entirely in the user's main session so they can interrupt mid-analysis. Cheap, transparent, easy to debug.

---

# 11. `/kaizen:analyze` runtime (v0.4.0+)

> Read-only diagnostic. Mirror skill to `/learn`: where `/learn` watches git and proposes config changes, `/analyze` watches **current code** and reports issues against the existing config.

## Mental model — strict read-only

```
┌─────────────────────────────┐       ┌─────────────────────────────┐
│  PLUGIN TREE (read-only)    │       │  USER PROJECT (read-only)   │
│  ~/.claude/plugins/cache/   │ reads │  $CLAUDE_PROJECT_DIR        │
│                             │ ────▶ │                             │
│  • SKILL.md (instructions)  │       │  • CLAUDE.md                │
│                             │       │  • .claude/rules/*          │
│                             │       │  • source files (src/...)   │
│                             │       │  • package.json (optional)  │
└─────────────────────────────┘       └─────────────────────────────┘
                                                  │
                                                  │ writes ONLY to one file
                                                  ▼
                                       ┌─────────────────────────────┐
                                       │  REPORT (overwritten)       │
                                       │  .claude/kaizen/            │
                                       │    analyze-report.md        │
                                       │  (auto-gitignored)          │
                                       └─────────────────────────────┘
```

Unlike `/init` (writes config) and `/learn` (writes pending, optionally applies), `/analyze` writes **exactly one file**: the report. No source code is touched. No CLAUDE.md is touched. No state machine — every run is independent.

## Components

| Component | Type | Lifetime | Purpose |
|---|---|---|---|
| [`skills/analyze/SKILL.md`](../plugins/kaizen/skills/analyze/SKILL.md) | LLM prompt | Loaded into context when `/kaizen:analyze` is invoked | Mode dispatch + pattern library + per-mode algorithms + report writer |
| `analyze-report.md` | Markdown file | Overwritten on every run | Persistent output for re-reading via `show` or for sharing |

No helper scripts. All logic is in SKILL.md + standard tools (`Read`, `Write`, `Glob`, `Grep`, `Bash(test|ls|cat|wc|mkdir)`).

## Modes (combinable)

| Flag | Reads | Reports |
|---|---|---|
| `--best-practices` | `CLAUDE.md`, `.claude/rules/*`, all source files | Violations of stated conventions, by file:line. Plus "Unchecked" list for conventions outside the pattern library. |
| `--coverage` | `.claude/rules/*` (parses `paths:` frontmatter), all source files | Directories with <20% rule coverage. Stale rules (paths match no files). Always-loaded rules. |
| `--architecture` | `CLAUDE.md` (`## Architecture` section), `src/*/`, optionally `package.json` | Documented-but-missing dirs, exists-but-undocumented dirs. Stack section drift vs package.json. |
| *(none)* | All of the above | All three sections in one report |
| `show` | `analyze-report.md` | Re-prints last report. No analysis performed. |

## Built-in pattern library (`--best-practices` v0.4)

Conventions verified automatically when matched by keyword in CLAUDE.md / rules:

```
named exports only      → grep ^export default
no console.log          → grep console\.log (excluding tests)
no any                  → grep ': any\b' and 'as any\b' (TS)
no eslint-disable       → grep eslint-disable lacking inline justification
no print() for logging  → grep ^print( (Python, excl. tests/scripts/__main__)
no bare except          → grep except\s*:\s*$ (Python)
no wildcard imports     → grep 'from .* import \*' (Python)
no mutable defaults     → grep 'def f([^)]*=\[\]' / '=\{\}' (Python)
tests next to source    → for each .ts file, check sibling *.test.* exists
```

Conventions NOT matching any keyword are listed explicitly under **"Unchecked (manual review)"**. This is a feature, not a limitation: users see exactly what kaizen verifies vs. what they need to inspect themselves.

## Report schema

Always at `.claude/kaizen/analyze-report.md`. Overwritten on every run.

```markdown
# kaizen :: analyze report

Generated: <ISO 8601>
Plugin version: <v>
Modes run: <list>

---

## Best practices
[Section per --best-practices; omitted if mode not run]

## Documentation coverage
[Section per --coverage; omitted if mode not run]

## Architecture drift
[Section per --architecture; omitted if mode not run]

---

## Suggestions
[Specific, evidence-based, actionable. Omitted if nothing to suggest.]
```

Console summary printed alongside the file write — concise, with counts per mode.

## Boundaries

**`/analyze` reads**:
- `CLAUDE.md` (always)
- `.claude/rules/*` (always)
- Source files via Glob (project-defined extensions)
- `package.json` (optional, for `--architecture` stack drift)
- `.claude/kaizen/analyze-report.md` (only in `show` mode)

**`/analyze` writes**:
- `.claude/kaizen/analyze-report.md` (overwritten on every run)
- `.gitignore` (only if `.claude/kaizen/` not yet ignored — one-time append, same logic as `/learn`)

**`/analyze` never touches**:
- Source code.
- `CLAUDE.md`, `.claude/rules/*`, `.claude/settings.json`, any other config.
- `package.json` or dependency manifests.
- Anything outside `$CLAUDE_PROJECT_DIR`.
- `pending.md` from `/learn` (independence).

## Relationship to `/learn`

Deliberately **decoupled** in v0.4:

| Aspect | `/learn` | `/analyze` |
|---|---|---|
| Input | Git history (commits, diffs) | Current files (source + config) |
| Output | `.claude/kaizen/pending.md` (proposals) | `.claude/kaizen/analyze-report.md` (findings) |
| Can mutate? | Yes, via `/learn apply` | No, ever |
| State machine | Yes (no-pending ↔ has-pending) | None |
| Shared `.claude/kaizen/` dir | Yes | Yes |

The user can read the analyze report and then run `/learn` to formalize fixes — but kaizen never automates that bridge. Decoupling is the v0.4 contract; future versions may add an opt-in `--feed-to-learn` flag if usage patterns justify it.

## Failure modes

| Failure | Behavior |
|---|---|
| `CLAUDE.md` missing | Refuse all modes. Suggest `/kaizen:init` first. |
| `.claude/rules/` missing | `--coverage` notes "no rules to check against". Other modes proceed. |
| No source files match | `--coverage` / `--architecture` report "No source files detected". `--best-practices` proceeds with empty result set. |
| Not a git repo | All modes work without git. No refusal. |
| Pattern library has no match | `--best-practices` reports ALL conventions as Unchecked. Still produces report. |
| `package.json` missing | `--architecture` skips Stack drift sub-check, notes in report. |
| Grep returns >50 matches | Lists first 20 with "+N more". Bounded. |

## Why this design

Five deliberate choices specific to `/analyze`:

1. **Read-only is the contract, not a side-effect.** Diagnostic and surgery are different jobs. Coupling them is how tools become bossy and lose user trust.
2. **Pattern library over LLM-everything.** Checking "no console.log" should be a `Grep` call, not "Claude reads every file and judges". Patterns are auditable, fast, and reproducible.
3. **Unchecked conventions are explicit.** Silently skipping unverifiable rules would hide kaizen's limitations. Listing them tells the user: "these need eyes."
4. **Single output file, overwritten.** No archive of past reports. Reports are diagnostic snapshots; you take a new one when you want a new snapshot. Archiving adds complexity for little gain.
5. **No state machine.** Unlike `/learn`, there's nothing to gate — every run is read-only and idempotent. The simplicity is deliberate.
