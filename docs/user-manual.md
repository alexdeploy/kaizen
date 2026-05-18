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

Commands shipped in v0.5.0:
- [`/kaizen:init`](#kaizeninit-arguments) — bootstrap project config
- [`/kaizen:learn`](#kaizenlearn-arguments) — propose config updates from git activity
- [`/kaizen:analyze`](#kaizenanalyze-arguments) — read-only audit of code vs. stated rules
- [`/kaizen:preflight`](#kaizenpreflight-arguments) — pre-merge gate (tests + LLM review + verdict)

### `/kaizen:init [arguments]` {#kaizeninit-arguments}

Bootstrap a Claude Code configuration tailored to the current project. Detects stack, package manager, project maturity, and existing config, then generates `CLAUDE.md`, `.claude/settings.json`, path-scoped rules, a code-reviewer agent, and hooks.

#### Arguments

| Argument | Meaning |
|---|---|
| *(no args)* | Auto-detect everything. Recommended for first runs. |
| `--preset <name>` | Skip auto-detection, use a named preset. Values: `generic`, `typescript-node`, `python`. |
| `--force` | Overwrite existing Claude config files. **Use only after committing or backing up.** Without this flag, kaizen will refuse to overwrite. |
| `--minimal` | Only generate `CLAUDE.md` + `.claude/settings.json` + `.gitignore` patch. Skip rules, agents, hooks. |

Combine freely: `/kaizen:init --preset python --minimal`, `/kaizen:init --force --preset typescript-node`.

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
| `--since=<git-ref>` | Analyze commits since this ref. Default: `HEAD~10`. Examples: `--since=HEAD~25`, `--since=v1.0.0`, `--since=2 weeks ago`. |

#### Typical workflow

```
# After a few days of work, see what kaizen suggests:
/kaizen:learn

# Review the proposals:
/kaizen:learn show

# Either apply them all:
/kaizen:learn apply

# ...or throw them away if not useful:
/kaizen:learn discard

# You can also EDIT pending.md by hand to refine before applying.
```

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

- **v0.3 (today)**: git only — `git log` and `git diff` from the last N commits.
- **v0.4 (planned)**: optional `--include-session` flag to also analyze the current conversation for user corrections.
- **v0.5 (planned)**: optional `--include-memory` flag to read Claude's auto-memory.

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

#### Subcommands

| Subcommand | Action |
|---|---|
| *(none)* | Run full preflight — all 5 checks |
| `show` | Re-print the last report from `.claude/kaizen/preflight-report.md` without re-running |

(v0.6 will add `--base=<ref>`, `--skip=<checks>`, `--auto-fix`.)

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

`/kaizen:preflight` compares your current state against a base ref:

| Current branch | Base ref used |
|---|---|
| `main` | `HEAD~1` (last commit) |
| `master` | `HEAD~1` |
| any other branch | `main` (if exists), else `master`, else `HEAD~1` |

Override via `--base=<ref>` planned for v0.6.

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

- **Strictly read-only** except for the report file. Never modifies source code, never commits.
- **Bounded output**: deterministic check commands have output capped at 50 lines (tail kept).
- **No auto-fix in v0.5**: `--auto-fix` for lint/format is deferred to v0.6.
- **Spawns at most 2 subagents per run**, both in parallel. No recursive spawning.
- **Changed-files-only scope** for security agent — token cost grows with change size, not project size.

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
