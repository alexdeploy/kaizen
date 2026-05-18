---
description: Pre-merge sanity check. Runs tests, typecheck, lint, security review (changed files only), and suggests a conventional commit message. Produces a single SHIP/HOLD/BLOCK verdict.
disable-model-invocation: true
argument-hint: "[show]"
allowed-tools: Read, Write, Glob, Grep, Bash(git status), Bash(git rev-parse *), Bash(git diff *), Bash(git log *), Bash(git branch *), Bash(git show *), Bash(git symbolic-ref *), Bash(npm test *), Bash(npm run *), Bash(npx tsc *), Bash(npx eslint *), Bash(npx prettier *), Bash(pnpm test *), Bash(pnpm run *), Bash(yarn test *), Bash(yarn run *), Bash(bun test *), Bash(bun run *), Bash(pytest *), Bash(mypy *), Bash(ruff *), Bash(go test *), Bash(go vet *), Bash(cargo test *), Bash(cargo check *), Bash(test *), Bash(ls *), Bash(cat *), Bash(mkdir *), Task
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

Future args planned for v0.6+ (DO NOT implement in v0.5):
- `--base=<ref>` — override the base ref for the diff
- `--skip=<check,check>` — skip specific checks
- `--auto-fix` — apply auto-fixes for lint/format before failing

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

### Step 1: detect base ref

Determine what to diff against. Use the **first** applicable:

```bash
# 1. Current branch
git symbolic-ref --short HEAD 2>/dev/null
```

| Current branch | Base ref to use |
|---|---|
| `main` | `HEAD~1` |
| `master` | `HEAD~1` |
| anything else | `main` (if exists), else `master`, else `HEAD~1` |

Verify the base ref exists:

```bash
git rev-parse --verify <base_ref> 2>/dev/null
```

If verification fails, fall back to `HEAD~1`. Surface the chosen base in the report.

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

### Step 4: run deterministic checks (sequential)

For each phase (tests → typecheck → lint), run the resolved command via Bash. **Capture**: exit code, full output. **Bound** output to last 50 lines if longer (keep tail; failures are usually at the end).

For each result, classify:
- `pass` — exit 0
- `fail` — exit non-zero
- `skip` — no command resolved

Don't stop on first failure — collect all three before moving on. This lets the user see the full picture, not iterate one fix at a time.

### Step 5: spawn LLM agents in parallel

In a **single message**, issue TWO `Task` tool calls:

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
Base ref: <base_ref>
Changed files: <count> source files (+ <N> non-source)

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

- **NEVER modify source code.** preflight is a gate, not a fixer. Auto-fix flags are deferred to v0.6.
- **NEVER auto-commit** even if SHIP verdict. The user commits.
- **NEVER skip checks silently.** A skipped check is shown explicitly with the reason ("no `tsc` in devDeps").
- **NEVER block on a check that was skipped** for tooling reasons.
- **NEVER read files outside `cwd`.**
- **Bound output**: max 50 lines per check command output. Tail kept (failures usually end-of-output).
- **Always run all three deterministic checks** before spawning agents. Don't fail-fast on first deterministic failure.
- **Spawn both agents in a single message** (parallel via Task), not sequential.

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

---

## Why this design

- **Hybrid execution** — deterministic checks are fast and predictable, no need for LLM overhead. LLM agents are reserved for what actually needs reasoning (security review, commit message). Best use of tokens.
- **Parallel agent dispatch** — two Task calls in one message means both agents work simultaneously in fresh contexts. ~2× faster than sequential, no context bloat in the main session.
- **Changed-files-only scope** for security review — instead of auditing the whole repo every time, the agent reads ONLY what's in the diff. Scales with change size, not project size.
- **Three-tier verdict** — binary green/red loses nuance. SHIP/HOLD/BLOCK gives the user real signal: BLOCK = don't merge, HOLD = fix before merging, SHIP = good to go.
- **Conventional commits by default** — established standard, integrates with changelog/semver tools. v0.6+ auto-detects other styles from history.
- **Independent of /init's code-reviewer** — preflight's security agent is plugin-level, narrowly scoped to changes. The user's `code-reviewer.md` (if /init was run) remains for manual general review. No competition, no overlap.
- **Read-only by hard rule** (except for the report file and one-time .gitignore append). Same safety model as /analyze.
