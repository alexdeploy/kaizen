---
description: Analyzes recent changes for documentation gaps. Spawns the docs-keeper agent (scoped to changed files) and writes a report listing which docs may need updating, by severity. Read-only — never edits documentation.
disable-model-invocation: true
argument-hint: "[show] [--since=<ref>] [--limit=<N>] [--base=<ref>]"
allowed-tools: Read, Write, Glob, Grep, Bash(git status), Bash(git rev-parse *), Bash(git diff *), Bash(git log *), Bash(git branch *), Bash(git symbolic-ref *), Bash(test *), Bash(ls *), Bash(cat *), Bash(mkdir *), Task
---

# /kaizen:docs

Surfaces documentation gaps from recent changes. Spawns the `docs-keeper` plugin agent, which reads a diff and identifies which doc files may need updating. **Never edits documentation** — the report is the artifact; you decide what to update.

Mirror skill to `/kaizen:learn` (which updates CLAUDE.md/rules) but scoped to **user-facing documentation** (README, docs/, CHANGELOG mentions, examples).

---

## Arguments

| Arg | Meaning |
|---|---|
| *(none)* | Analyze current state vs auto-detected base ref. |
| `show` | Re-print the last report from `.claude/kaizen/docs-report.md`. Exclusive. |
| `--base=<ref>` | Override the base ref. Same logic as `/preflight`. |
| `--since=<ref>` | Analyze commits since this ref. Default: auto-detected base ref or `HEAD~10`. |
| `--limit=<N>` | Analyze the last N commits (equivalent to `--since=HEAD~<N>`). |

Flags combine. `show` is exclusive.

---

## Mode: `show`

```bash
test -f .claude/kaizen/docs-report.md
```

If absent: print `✗ No docs report exists. Run /kaizen:docs to generate one.`

Otherwise: print verbatim.

---

## Mode: full run

### Step 1: resolve range

Use the same logic as `/preflight` Step 1:

- If `--base=<ref>` provided, use it (stop on invalid ref, no fallback).
- Else if `--since=<ref>` or `--limit=<N>`, build the range.
- Else auto-detect: on `main`/`master` → `HEAD~1`; else → `main` (or `master`); fallback `HEAD~10`.

Print the resolved range up front:

```
kaizen docs: analyzing range <base>..HEAD (<N> commits)
```

### Step 2: enumerate changed source files

```bash
git diff --name-only <base>..HEAD
```

If empty, stop: `✓ No changes since <base>. Nothing to analyze for docs.`

Filter to source files (exclude `.md`, lockfiles, generated artifacts) — docs-keeper cares about what changed in CODE, then checks the DOCS against those changes.

### Step 3: spawn docs-keeper agent

Single Task call (only one agent — no parallelism needed):

```
Task(subagent_type='docs-keeper', prompt=`
  Analyze documentation gaps for these changed files (diff range <base>..HEAD):

  - <file 1>
  - <file 2>
  ...

  Return findings per your output format, grouped by severity. If no findings, say "No documentation updates needed."
`)
```

Capture the agent's output.

### Step 4: write report

Ensure `.claude/kaizen/` exists; ensure `.gitignore` has the entry (same one-time logic as other skills).

Write `.claude/kaizen/docs-report.md` (overwritten each run) with this structure:

```markdown
# kaizen :: docs report

Generated: <ISO 8601>
Plugin version: <v>
Range analyzed: <base>..HEAD (<N> commits)
Changed source files: <count>

---

## Findings

<agent's output verbatim, including "No documentation updates needed." if clean>

---

## Suggestions

<actionable items not captured by docs-keeper findings — e.g., "consider creating CONTRIBUTING.md given the project now has 3+ contributors". Omit section if none.>
```

### Step 5: console summary

```
✓ kaizen docs: analyzed <N> commits

Findings:
  - <H> high · <M> medium · <L> low
  (or: "No documentation updates needed.")

Full report: .claude/kaizen/docs-report.md
  /kaizen:docs show   # re-print
  /kaizen:docs        # re-run after updates
```

Use `⚠` for high, `ℹ` for medium, `·` for low in any per-finding console preview.

---

## Hard rules (never violate)

- **NEVER modify documentation files.** Findings only. The user updates docs by hand.
- **NEVER modify source code.** Read-only across the board (except for the report file + one-time `.gitignore`).
- **NEVER auto-create CONTRIBUTING.md, README.md, or any other doc file.** Suggest creating; never write.
- **NEVER spawn more than one agent.** This is a single-agent skill.
- **Bound output**: agent already bounds at 50 findings / 20 files sampled when diff is huge. Report passes through.

---

## Failure modes

| Failure | Behavior |
|---|---|
| Not a git repo | Refuse. Suggest `git init` + commit. |
| No changes vs base | Stop with friendly message; no report written. |
| Agent fails or returns garbled | Log in report ("agent failure"), skip findings section; still write the report with the failure note. |
| No documentation files exist at all in project | Agent will surface this as a suggestion ("consider creating README.md"); skill passes through. |
| Range too large (>1000 files) | Agent samples top 20 likely-impactful; report notes the sampling. |

---

## Why this design

- **Single-agent skill** (no parallelism) — there's only one job (audit docs against code changes). Adding a second agent would be artificial parallelism.
- **Read-only by hard rule** — identical safety contract to `/analyze` and `/preflight` (default). Doc rewriting is a manual decision; surfacing is automatic.
- **Changed-files-only scope** — agent reads what changed, not the whole repo. Token-cheap and scales with change size.
- **Mirror to `/learn`** — `/learn` updates internal config docs (CLAUDE.md/rules); `/docs` surfaces user-facing doc gaps. Two complementary skills, no overlap.
