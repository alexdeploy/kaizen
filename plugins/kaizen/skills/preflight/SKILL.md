---
description: Pre-merge sanity check. Runs tests, typecheck, lint, security review (changed files only), and suggests a conventional commit message. Produces a single SHIP/HOLD/BLOCK verdict.
disable-model-invocation: true
argument-hint: "[show] [--base=<ref>] [--skip=<checks>] [--auto-fix]"
allowed-tools: Read, Write, Glob, Grep, Bash(git status), Bash(git rev-parse *), Bash(git diff *), Bash(git log *), Bash(git branch *), Bash(git show *), Bash(git symbolic-ref *), Bash(npm test *), Bash(npm run *), Bash(npx tsc *), Bash(npx eslint *), Bash(npx eslint --fix *), Bash(npx prettier *), Bash(npx prettier --write *), Bash(pnpm test *), Bash(pnpm run *), Bash(yarn test *), Bash(yarn run *), Bash(bun test *), Bash(bun run *), Bash(pytest *), Bash(mypy *), Bash(ruff *), Bash(ruff check --fix *), Bash(ruff format *), Bash(go test *), Bash(go vet *), Bash(go fmt *), Bash(gofmt *), Bash(cargo test *), Bash(cargo check *), Bash(cargo fmt *), Bash(test *), Bash(ls *), Bash(cat *), Bash(mkdir *), Task
---

# /kaizen:preflight

You are the **kaizen preflight orchestrator**. Your job is to run a pre-merge gate locally that mirrors what CI would catch — but with faster feedback and intelligent commit message suggestion. Output a clear SHIP / HOLD / BLOCK verdict so the user can decide whether to commit/PR right now or fix issues first.

This is the **operational counterpart** to `/init`, `/learn`, `/analyze`:

| Skill | When | What |
|---|---|---|
| `/init` | once at project start | bootstrap config |
| `/learn` | after tasks finish | propose config updates |
| `/analyze` | when curious | audit code vs config |
| `/preflight` | **before commit/PR** | gate the change |

---

## Arguments

| Arg | Meaning |
|---|---|
| *(none)* | Run full preflight: tests + typecheck + lint + security review + commit suggestion |
| `show` | Re-print the last report from `.claude/kaizen/preflight-report.md`. Does not re-run checks. |
| `--base=<ref>` | Override the auto-detected base ref. Examples: `--base=develop`, `--base=v1.0.0`, `--base=HEAD~3`. When omitted, auto-detection runs (see Step 1). |
| `--skip=<checks>` | Skip specific checks. CSV of check names: `tests`, `typecheck`, `lint`, `security`, `commit`. Example: `--skip=security,commit` runs only the deterministic trio. Skipped checks appear in the report as `skipped (--skip)` and never affect the verdict. |
| `--auto-fix` | **Before** running lint, attempt safe auto-fixes per stack: `eslint --fix` + `prettier --write` (JS/TS), `ruff check --fix` + `ruff format` (Python), `gofmt -w` (Go), `cargo fmt` (Rust). **MODIFIES SOURCE FILES** — opt-in only, never default. Recommended only on a clean git tree (warn if uncommitted changes exist). Lint then reports what auto-fix couldn't resolve. |

Flag parsing rules:
- All flags can combine: `/kaizen:preflight --base=main --skip=security --auto-fix`.
- `show` is exclusive — ignores other flags.

Future args planned for v0.9+ (DO NOT implement in v0.8):
- Risk-aware sizing (lighter security review for small diffs)
- Commit style auto-detection from `git log` (vs. always-Conventional Commits)

---

## Mode: `show`

```bash
test -f .claude/kaizen/preflight-report.md
```

If absent: print `✗ No preflight report exists. Run /kaizen:preflight to generate one.`

Otherwise: print the file verbatim.

---

## Mode: full run

Execute the 7 steps below **in order**. Step 5 spawns subagents **in parallel** (single message with multiple Task tool calls).

### Step 1: resolve base ref

**If `--base=<ref>` was provided in `$ARGUMENTS`**, use that value directly. Verify it exists:

```bash
git rev-parse --verify <user_base> 2>/dev/null
```

If verification fails, **stop with a clear error** — do not silently fall back. The user explicitly named the ref; if it's wrong, that's a typo to surface.

**Otherwise (auto-detection)**, use the **first** applicable:

```bash
git symbolic-ref --short HEAD 2>/dev/null
```

| Current branch | Base ref to use |
|---|---|
| `main` | `HEAD~1` |
| `master` | `HEAD~1` |
| anything else | `main` (if exists), else `master`, else `HEAD~1` |

Verify the chosen base ref exists:

```bash
git rev-parse --verify <base_ref> 2>/dev/null
```

If verification fails, fall back to `HEAD~1`. Surface the chosen base — and whether it was auto-detected vs. user-specified — in the report.

### Step 2: enumerate changed files

```bash
git diff --name-only <base_ref>..HEAD
```

If empty: print `✓ No changes since <base_ref>. Nothing to preflight.` and stop. Do not write a report.

Filter the file list to source files (exclude lockfiles, generated files, large binaries) — keep extensions: `.ts`, `.tsx`, `.js`, `.jsx`, `.vue`, `.svelte`, `.py`, `.go`, `.rs`, `.java`, `.rb`, `.php`, `.ex`, `.exs`, `.kt`, `.swift`, `.c`, `.cpp`, `.h`, `.hpp`. **The unfiltered list (with lockfiles etc.) still goes to commit-suggester** — those changes are relevant for the message.

### Step 3: detect stack and resolve commands

Determine package manager and available scripts:

```bash
test -f package.json && cat package.json
test -f pyproject.toml && cat pyproject.toml
test -f go.mod && cat go.mod
test -f Cargo.toml && cat Cargo.toml
```

Build a map: which check command for each phase, OR `skip` if not detectable:

| Phase | TypeScript/Node detection | Python detection | Go detection | Rust detection |
|---|---|---|---|---|
| tests | script `test` in package.json → `<pm> test` | `pytest` available → `pytest` | always → `go test ./...` | always → `cargo test` |
| typecheck | script `typecheck`, OR `tsc` in devDeps → `npx tsc --noEmit` | `mypy` in deps → `mypy .` | `go vet ./...` | `cargo check` |
| lint | script `lint`, OR `eslint` in devDeps → `npx eslint .` | `ruff` in deps → `ruff check .` | skip (use vet for now) | skip (rust has built-in lint) |

If a check has no detectable command, mark its result as `skip (no <tool> detected)`. Do NOT fail the verdict on a skipped check.

### Step 3.5: auto-fix (only if `--auto-fix` in `$ARGUMENTS`)

**Skip this step entirely if `--auto-fix` was not passed.** Default behavior is read-only.

If `--auto-fix` is present:

1. **Check for uncommitted changes**:
   ```bash
   git status --porcelain
   ```
   If output is non-empty, **warn** the user but proceed:
   ```
   ⚠ --auto-fix on a dirty git tree. Auto-fixes will mix with your uncommitted edits.
     Recommended: commit or stash WIP first. Proceeding anyway.
   ```

2. **Run the auto-fix commands** per detected stack. Sequential is fine — these are deterministic.

   | Stack | Commands to attempt (skip if tool not detected) |
   |---|---|
   | TypeScript / JavaScript | `npx eslint --fix .` then `npx prettier --write .` |
   | Python | `ruff check --fix .` then `ruff format .` |
   | Go | `gofmt -w .` (or `go fmt ./...`) |
   | Rust | `cargo fmt` |

   For each command: capture exit code + output (bounded 50 lines). Tools that aren't installed are silently skipped — `--auto-fix` is best-effort.

3. **Detect what changed** after the fixes:
   ```bash
   git diff --name-only
   ```
   Track this list — it goes into the report so the user knows what was modified.

4. **Proceed to Step 4** (lint will now report only what auto-fix couldn't resolve).

### Step 4: run deterministic checks (sequential)

For each phase (tests → typecheck → lint), run the resolved command via Bash. **Capture**: exit code, full output. **Bound** output to last 50 lines if longer (keep tail; failures are usually at the end).

**If `--skip=<checks>` was provided**, skip any check whose name appears in the CSV. Valid names: `tests`, `typecheck`, `lint`, `security`, `commit`. Skipped checks are reported but never affect the verdict.

For each result, classify:
- `pass` — exit 0
- `fail` — exit non-zero
- `skip` — no command resolved OR explicitly skipped via `--skip`

Don't stop on first failure — collect all three before moving on. This lets the user see the full picture, not iterate one fix at a time.

### Step 5: spawn LLM agents in parallel

**If `--skip=<checks>` was provided**, check whether `security` and/or `commit` are in the skip list:
- If both are skipped, omit Phase 2 entirely.
- If only one is skipped, only spawn the other agent.
- If neither is skipped, spawn both (default behavior below).

In a **single message** (when spawning multiple), issue the `Task` tool call(s):

**Call 1**:
- `subagent_type`: `preflight-security`
- prompt: A short brief listing the changed source files (full paths). Example:
  ```
  Review these files for security issues (changed in current diff vs <base_ref>):

  - src/api/auth.ts
  - src/services/db.ts
  - src/components/Login.vue

  Return findings using the format specified in your system prompt. If no findings, say so explicitly.
  ```

**Call 2**:
- `subagent_type`: `commit-suggester`
- prompt: A brief instructing the agent to analyze the diff and propose a conventional commit. Example:
  ```
  Analyze the diff <base_ref>..HEAD and propose a conventional commit message.

  Use `git diff <base_ref>..HEAD` and `git diff --stat <base_ref>..HEAD` to understand the change.

  Return the primary suggestion + 2 alternatives + an optional body, per your system prompt format.
  ```

Both agents return when done. Aggregate their outputs in your context.

### Step 6: compute verdict

| Verdict | When |
|---|---|
| **BLOCK** | tests failed OR typecheck failed OR security has `critical` findings |
| **HOLD** | lint has errors (not just warnings) OR security has `high` findings |
| **SHIP** | everything else (pass, skip, only warnings, only low/medium findings) |

A check skipped because tooling isn't installed is **not** a verdict trigger. Note it in the report.

### Step 7: write report and print summary

Create dir if needed: `mkdir -p .claude/kaizen`. The `.claude/kaizen/` dir should already be in `.gitignore` from prior `/learn`/`/analyze` runs; if not, ensure it is added.

Write `.claude/kaizen/preflight-report.md` (overwrite each run) with this exact structure:

```markdown
# kaizen :: preflight report

Generated: <ISO 8601 timestamp>
Plugin version: <version>
Base ref: <base_ref> (<auto-detected | --base override>)
Changed files: <count> source files (+ <N> non-source)
Flags: <comma-separated list of flags passed, or "none">
<if --auto-fix was used:>
Auto-fix applied: <N files modified> (<comma-separated short list>)

---

## Verdict: <SHIP | HOLD | BLOCK>

<one-line reason — e.g. "All checks passed." | "Lint errors must be fixed." | "1 critical security finding + tests failed.">

| Counts |
|---|---|
| critical | <N> |
| high | <N> |
| medium | <N> |
| low | <N> |
| lint errors | <N> |
| lint warnings | <N> |
| test failures | <N> |
| typecheck errors | <N> |

---

## Phase 1 — Deterministic checks

### Tests
Status: <pass | fail | skip>
Command: `<command run>`
<if fail or skip, include relevant output excerpt>

### Typecheck
Status: <pass | fail | skip>
Command: `<command run>`
<output excerpt if fail/skip>

### Lint
Status: <pass | fail | skip>
Command: `<command run>`
<output excerpt if fail/skip>

---

## Phase 2 — LLM review

### Security (preflight-security agent)
<verbatim output of the agent, including findings or "No security findings.">

### Suggested commit message (commit-suggester agent)
<verbatim output of the agent>

---

## Suggestions

- <Stack/project specific suggestions, e.g. "Consider running /kaizen:analyze --best-practices for non-security style issues">
- <Suggestion to install a missing tool if a check was skipped>
- ...

(Omit this section entirely if nothing specific to suggest.)
```

Then print to console:

```
╔══════════════════════════════════════════════╗
║  PREFLIGHT — <SHIP|HOLD|BLOCK>               ║
║  <critical>c · <high>h · <medium>m · <low>l  ║
╚══════════════════════════════════════════════╝

✓ Tests       (<N> passed, <M> failed, <skip if applicable>)
✓ Typecheck   (<errors>)
✓ Lint        (<errors>e, <warnings>w)
✓ Security    (<critical>c / <high>h / <medium>m / <low>l findings)
ℹ Commit msg  (<primary suggestion one-liner>)

Verdict: <SHIP|HOLD|BLOCK>. <one-line reason>

Full report: .claude/kaizen/preflight-report.md
  /kaizen:preflight show   # re-print the report
  /kaizen:preflight        # re-run after fixes
```

Use ✓ for pass, ✗ for fail, ⚠ for warning-only, ⊘ for skip, ℹ for info.

---

## Hard rules (never violate)

- **NEVER modify source code UNLESS `--auto-fix` was passed.** Without that flag, preflight is strictly read-only. With it, the modifications are limited to what the configured formatters/linters do — kaizen itself never edits files manually.
- **NEVER auto-commit** — even if SHIP verdict, even with `--auto-fix`. The user commits.
- **NEVER skip checks silently.** A skipped check is shown explicitly with the reason (`"no \`tsc\` in devDeps"` for tooling skips, `"skipped (--skip)"` for explicit skips).
- **NEVER block on a check that was skipped** for tooling reasons OR via `--skip`.
- **NEVER read files outside `cwd`.**
- **Bound output**: max 50 lines per check command output. Tail kept (failures usually end-of-output).
- **Always run all three deterministic checks** before spawning agents (unless individually skipped via `--skip`). Don't fail-fast on first deterministic failure.
- **Spawn agents in a single message** (parallel via Task) when both are needed. If only one survives `--skip`, spawn just that one.
- **If `--base` is given and the ref is invalid, STOP** — do not silently fall back. The user named it explicitly; a typo deserves an error, not a guess.

---

## Failure modes

| Failure | Behavior |
|---|---|
| Not a git repo | Refuse. Suggest `git init` + at least one commit. |
| No changes vs base | Stop with `✓ No changes since <base_ref>. Nothing to preflight.` No report written. |
| `CLAUDE.md` missing | Don't refuse — preflight does NOT require kaizen-bootstrapped config. But add a suggestion: "Consider running /kaizen:init to bootstrap config." |
| All three deterministic check commands resolve to skip | Run agents anyway, but warn in the report that no deterministic checks fired. |
| Agent fails or returns garbled output | Log the failure in the report's relevant section; verdict computed from the parts that succeeded. Do not fail the whole preflight. |
| Diff is huge (>1000 files) | Run anyway but warn in report. Agents work on the source-filtered subset, which should be smaller. |
| `--base=<ref>` ref doesn't exist | Stop with `✗ Base ref '<ref>' not found. Available refs: <list>`. Do not auto-fall-back. |
| `--skip=<x>` includes an unknown check name | Warn (`⚠ Unknown skip target 'x' — ignored. Valid: tests, typecheck, lint, security, commit`). Continue with the rest. |
| `--skip` includes ALL checks | Refuse with `✗ --skip excluded every check. Nothing to do.` |
| `--auto-fix` but no fixers detected for the stack | Skip Step 3.5 silently, log in report: "auto-fix requested but no formatters/linters detected for <stack>". |
| `--auto-fix` modifies files but a subsequent step fails | Files stay modified (no rollback). Report makes clear what was auto-fixed BEFORE the failure. User decides whether to keep or `git checkout` the changes. |

---

## Why this design

- **Hybrid execution** — deterministic checks are fast and predictable, no need for LLM overhead. LLM agents are reserved for what actually needs reasoning (security review, commit message). Best use of tokens.
- **Parallel agent dispatch** — two Task calls in one message means both agents work simultaneously in fresh contexts. ~2× faster than sequential, no context bloat in the main session.
- **Changed-files-only scope** for security review — instead of auditing the whole repo every time, the agent reads ONLY what's in the diff. Scales with change size, not project size.
- **Three-tier verdict** — binary green/red loses nuance. SHIP/HOLD/BLOCK gives the user real signal: BLOCK = don't merge, HOLD = fix before merging, SHIP = good to go.
- **Conventional commits by default** — established standard, integrates with changelog/semver tools. v0.6+ auto-detects other styles from history.
- **Independent of /init's code-reviewer** — preflight's security agent is plugin-level, narrowly scoped to changes. The user's `code-reviewer.md` (if /init was run) remains for manual general review. No competition, no overlap.
- **Read-only by hard rule** (except for the report file and one-time .gitignore append). Same safety model as /analyze.
