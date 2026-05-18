---
description: Auto-planner — reads a spec (file, inline prompt, or GitHub issue) and produces a structured, dependency-ordered task tree. Auto-converts PDF/DOCX when pdftotext/pandoc are available. Dispatches plan-context and plan-decomposer agents in parallel, then synthesizes into an annotated plan. Optionally seeds TodoWrite.
disable-model-invocation: true
argument-hint: "<path-to-spec> | --from-prompt=\"...\" | --from-issue=<N> [--seed-todos] [list|show <plan-id>]"
allowed-tools: Read, Write, Glob, Grep, Bash(test *), Bash(ls *), Bash(cat *), Bash(file *), Bash(mkdir *), Bash(rm *), Bash(date *), Bash(wc *), Bash(head *), Bash(command -v *), Bash(which *), Bash(pdftotext *), Bash(pandoc *), Bash(gh issue view *), Task, TodoWrite
---

# /kaizen:plan

You are the **kaizen plan orchestrator**. Your job is to turn a written specification into a **structured, actionable task tree** the user can execute (manually or via Claude). This is the *input* counterpart to `/preflight` (the output gate).

The architectural shape mirrors `/preflight`: a 4-phase execution with two parallel research agents whose outputs the skill synthesizes into the final artifact.

---

## Arguments

Exactly **one source** is required (file path, inline prompt, or gh issue). Flags can combine.

| Arg | Meaning |
|---|---|
| `<path-to-spec>` | Path to a text-format spec document (markdown, txt, rst, adoc, plain). Binary formats (PDF, DOCX) **auto-converted** when `pdftotext`/`pandoc` is on PATH (v0.9+); otherwise rejected with conversion suggestion. |
| `--from-prompt="..."` | Inline prompt as the spec content. Useful for quick ad-hoc planning. Skill slugifies the first ~40 chars for the filename. |
| `--from-issue=<N>` | Fetch a GitHub issue via `gh issue view <N>`. Body + comments form the spec. Requires `gh` CLI installed and authenticated. |
| `--seed-todos` | After writing the plan file, also push each task into TodoWrite. Tasks land as todo entries in the current session for immediate execution. **Use only when you intend to start executing now** — TodoWrite is session-scoped, not project-scoped. |
| `list` | List all plans in `.claude/kaizen/plans/` with timestamps. Exclusive — ignores other args. |
| `show <plan-id>` | Print a specific plan verbatim. `<plan-id>` is the filename without `.md` extension, or `latest` for the most recent. Exclusive. |

Future args planned for v0.10+ (DO NOT implement in v0.9):
- `--scope=<area>` (limit decomposition to a directory)
- `--depth=<shallow|medium|deep>` (granularity control)
- `--execute` (autonomy boundaries needed first)

---

## Mode: `list`

```bash
ls .claude/kaizen/plans/ 2>/dev/null
```

If directory absent or empty: print `✗ No plans yet. Run /kaizen:plan <spec-path> to create one.`

Otherwise list each plan with its generation date (parse from filename or read header).

## Mode: `show <plan-id>`

Resolve `<plan-id>`:
- If literal `latest`: pick the most recently modified file in `.claude/kaizen/plans/`.
- Otherwise: look for `.claude/kaizen/plans/<plan-id>.md`.

If not found: print error with available plan IDs. Otherwise print the file verbatim.

---

## Mode: full run (the main flow)

The argument is `<path-to-spec>`. Run the 4 phases below.

### Phase 0: resolve and validate input

Determine the **input source** (exactly one must be specified):

| `$ARGUMENTS` contains | Source resolution |
|---|---|
| `--from-prompt="..."` | Use the quoted string as the spec content directly. Slug = first ~40 chars (slugified). Skip file/conversion logic. |
| `--from-issue=<N>` | Run `gh issue view <N>` (must have `gh` available). Concatenate body + comments as spec content. Slug = `issue-<N>`. |
| `<path>` (no other source flag) | Treat as file path. Continue with steps below. |
| none / multiple sources | Stop with `✗ kaizen plan: specify exactly one of <path>, --from-prompt, --from-issue.` |

For **file path** input:

1. Verify the file exists: `test -f "$spec_path"`. If not, error and stop.

2. Detect binary formats by extension:

| Extension | Action |
|---|---|
| `.pdf` | **Auto-convert** if `pdftotext` is on PATH (see below); else STOP with conversion suggestion |
| `.docx`, `.doc` | **Auto-convert** if `pandoc` is on PATH; else STOP with conversion suggestion |
| `.odt`, `.rtf`, `.epub`, `.mobi` | **Auto-convert** if `pandoc` is on PATH; else STOP |
| `.pages` | STOP with conversion suggestion (no good auto-converter) |
| any other | proceed (try to read) |

3. **Auto-conversion** (v0.9+):

   Check tool availability:
   ```bash
   command -v pdftotext   # for PDFs
   command -v pandoc      # for DOCX/ODT/RTF/EPUB/MOBI
   ```

   If the appropriate tool is **present**:
   - Ensure target dir: `mkdir -p .claude/kaizen/converted`.
   - Convert: write to `.claude/kaizen/converted/<basename-with-original-ext>.txt`.
     - PDF: `pdftotext -layout "<input>" "<output>"`
     - DOCX/ODT/RTF/EPUB/MOBI: `pandoc "<input>" -o "<output>.md"` (markdown output is best)
   - **Use the converted file as the spec** for the rest of the pipeline.
   - **Persist the conversion** (don't delete) so the user can inspect what kaizen extracted. Add `.claude/kaizen/converted/` to .gitignore via the usual one-time append logic.
   - In the plan header, note: `Spec source: <original> (auto-converted via <tool> → <converted-path>)`.

   If the tool is **absent**, stop with the conversion suggestion message (which now mentions auto-conversion as an alternative):

   ```
   ✗ kaizen plan: detected <format> input — no auto-converter found.

     Option 1 — install the converter and let kaizen handle it automatically:
       PDF:  brew install poppler   (macOS) / sudo apt install poppler-utils (Linux)
       DOCX: brew install pandoc    (macOS) / sudo apt install pandoc (Linux)

     Option 2 — convert manually and re-run with the .txt/.md path:
       PDF:  pdftotext <file> <file>.txt
       DOCX: pandoc <file> -o <file>.md

     Then: /kaizen:plan <converted-file>
   ```

4. Read the resolved spec content (either the original text file, or the converted output, or the inline prompt, or the gh issue body+comments). If a text file read succeeds but content appears mostly non-printable, treat as binary and apply the same auto-convert-or-stop logic.

5. **Bound input size**: if the spec is >2000 lines (or >100 KB), warn the user. Proceed anyway but note "input was large" in the plan header.

### Phase 1: setup context

Gather lightweight signals the agents will need. Use Bash + Read:

```bash
# Stack signals (just check existence, agents will read deeper)
test -f package.json && echo "node"
test -f pyproject.toml && echo "python"
test -f go.mod && echo "go"
test -f Cargo.toml && echo "rust"

# Existing kaizen config
test -f CLAUDE.md && echo "has-claude-md"
test -d .claude/rules && echo "has-rules"
```

These signals don't need to be perfect — the `plan-context` agent will read deeper. You're just building a small briefing for it.

### Phase 2: parallel agents (single message, two Task calls)

In a **single message**, issue these TWO Task tool calls:

**Call 1**:
- `subagent_type`: `plan-context`
- prompt: A brief instructing the context agent to gather project state. Example:
  ```
  Build a "project context" profile for the project at the current working directory.

  Signals already detected: <list from Phase 1>
  Spec being planned (for awareness only, do not over-fit): <spec-file-path>

  Return a project profile following your output format (stack, architecture, conventions, key areas, dependency overview).
  ```

**Call 2**:
- `subagent_type`: `plan-decomposer`
- prompt: A brief instructing the decomposer agent to extract tasks. Example:
  ```
  Read the spec file at <absolute-path-to-spec>. Extract a raw task list per your output format.

  Do NOT cross-reference the project — your job is purely to understand the spec and propose discrete tasks. The orchestrator will merge with project context after.
  ```

Both agents return when done. Capture both outputs.

### Phase 3: synthesis (in skill, no third agent)

You are the synthesizer. Take the two agent outputs and produce the final annotated plan:

1. **Start with the decomposer's raw task list**. Each entry has: title, type, complexity, acceptance criteria, suggested approach.

2. **For each task, cross-reference against the context profile**:
   - **Impact areas**: which directories from context's "key areas" does this task likely touch? Use heuristics from the task title + acceptance criteria.
   - **Dependencies**: does this task depend on another in the list? Read the criteria — e.g., "Task 3 requires the schema from Task 1 to exist" → Task 3 depends on Task 1. Surface explicitly.
   - **Risks**: if context mentions the affected area is critical (auth, payments, data migration), flag it. Conservative — under-flag rather than over-flag.

3. **Order tasks by dependencies**. Tasks with `Depends on: none` come first; downstream tasks follow. If circular dependencies are detected, break the cycle with the highest-complexity task first and note it.

4. **Cap the task count**: 20 max for v0.6. If decomposer returned more, group related tasks or suggest the user split the spec into multiple plans.

5. **Add a "Project context" preamble** at the top, summarizing what the agent profile found (2-4 lines). This is so the plan is self-contained — the reader doesn't need to know the project beforehand.

### Phase 4: write the plan

1. Compute filename:
   - Slug from spec path: `path/to/auth-rewrite.md` → `auth-rewrite`. If basename collides with existing plans, that's fine — timestamp differentiates them.
   - Timestamp: `YYYYMMDD-HHMM` from `date +%Y%m%d-%H%M`.
   - Full filename: `.claude/kaizen/plans/<slug>-<timestamp>.md`.

2. Ensure `.claude/kaizen/plans/` exists: `mkdir -p .claude/kaizen/plans`.

3. Ensure `.claude/kaizen/` is gitignored. The pattern was added by prior `/learn` or `/analyze` runs; if not, append `.claude/kaizen/` to `.gitignore`.

4. Write the plan file using **this exact structure**:

```markdown
# Plan: <spec-name>

Generated: <ISO 8601 timestamp>
Plugin version: <plugin version>
Spec source: <path-to-spec, relative if possible>
Tasks: <N>

## Project context (auto-detected)

<2-4 line summary from plan-context agent — stack, architecture, conventions>

**Key areas potentially affected**: <comma-separated dirs>

---

## Task 1: <one-line summary, imperative present tense>

**Type**: <feat | fix | refactor | docs | test | chore | infra | spike>
**Complexity**: <trivial (<30min) | small (1-2h) | medium (2-8h) | large (1-3d) | epic (split me)>
**Impact areas**: `<path>`, `<path>`
**Depends on**: <Task M, Task K, or "none">
**Risks**: <one-line risk if context flagged the area as critical; "none" otherwise>

### Description
<2-4 sentences: what and why>

### Acceptance criteria
- [ ] <Specific testable outcome 1>
- [ ] <Specific testable outcome 2>
- [ ] ...

### Suggested approach
<2-3 lines optional, only if non-obvious>

---

## Task 2: ...

[... repeat for each task ...]

---

## Summary

- Total tasks: <N>
- By type: <feat: K, fix: M, ...>
- By complexity: <trivial: K, small: M, ...>
- Foundational tasks (no deps): <list of task numbers>
- Estimated total effort: <if complexities sum cleanly, give range; otherwise omit>

## Suggestions (not auto-applied)

- <Specific suggestions: e.g., "Task 5 might benefit from running /kaizen:analyze --architecture first to confirm assumed structure">
- <Or: "Spec mentions ${feature X} without acceptance criteria — clarify before starting">

(Omit Suggestions section entirely if none.)
```

5. **If `--seed-todos` was passed**, use the **TodoWrite** tool to push each task into the session's todo list:
   - Each plan task becomes one TodoWrite entry.
   - `content` = task title (imperative, as in the plan).
   - `activeForm` = present-continuous form of the title (e.g., "Replace mock auth with JWT issuance" → "Replacing mock auth with JWT issuance").
   - `status` = `pending` for all (the user picks which to start).
   - **Append, do not replace** any existing todos in the session.
   - Cap at the 20 plan tasks (already capped in Phase 3).
   - Note this in the console output (`+ N tasks pushed to TodoWrite`).

   If `--seed-todos` was NOT passed, skip this step entirely.

6. Print to console:

```
✓ kaizen plan: <N> tasks written

Plan: <slug>
File: .claude/kaizen/plans/<slug>-<timestamp>.md
<if --seed-todos:>
  + <N> tasks pushed to TodoWrite (visible in this session)

Quick summary:
  - <N> total tasks (<feat>f, <fix>fx, <refactor>r, ...)
  - <K> foundational (no dependencies)
  - <L> with risks flagged

Next:
  /kaizen:plan show <slug>-<timestamp>      # full plan
  /kaizen:plan list                          # all plans
```

---

## Hard rules (never violate)

- **NEVER modify source code or any other file** except the plan file and (one-time) `.gitignore`.
- **NEVER execute the plan.** The plan is the artifact. The user (or another /kaizen skill) executes.
- **NEVER auto-trigger `/preflight` or other skills.** Composition is the user's decision.
- **NEVER read files outside the project root** (cwd). The spec path is allowed; everything else must be within cwd.
- **NEVER invent dependencies between tasks.** Only mark `Depends on` if the criteria genuinely imply ordering.
- **NEVER exceed 20 tasks in v0.6.** If decomposer returns more, group or suggest splitting.
- **NEVER pad with speculative tasks** not present in the spec. The decomposer should be faithful to what's written.
- **Spawn both agents in a single message** (parallel via Task), not sequential.

---

## Failure modes

| Failure | Behavior |
|---|---|
| Spec path doesn't exist | Stop with `✗ File not found: <path>` |
| Binary file, auto-converter NOT installed | Stop with the conversion suggestion (install + convert + retry, OR install for auto-conversion next time) |
| Binary file, auto-converter available but conversion FAILS | Stop with `✗ Conversion failed (<tool> exit <code>): <stderr excerpt>`. Don't proceed with garbage |
| Read returns garbled / mostly non-printable (e.g., wrong extension) | Treat as binary, apply auto-convert-or-stop logic |
| Spec is empty | Stop with `✗ Spec is empty. Nothing to plan.` |
| `--from-prompt=""` (empty) | Same as empty spec — stop |
| `--from-issue=<N>` but `gh` not installed | Stop with `✗ gh CLI not found. Install from https://cli.github.com/ then re-run.` |
| `--from-issue=<N>` but `gh issue view` fails (not authenticated, no repo, issue doesn't exist) | Surface gh's error to the user. Don't pretend to succeed. |
| Multiple input sources given | Stop with `✗ Specify exactly one of <path>, --from-prompt, --from-issue.` |
| Agent fails or returns garbled output | Log the failure in the plan file; mark affected sections as `<unavailable>`; do not fail the whole skill |
| Decomposer returns zero tasks | Write a plan file with `## (no actionable tasks extracted)` + Suggestions like "Spec may be too abstract — try adding concrete acceptance criteria" |
| `mkdir -p .claude/kaizen/plans` fails | Stop with filesystem error message |
| Spec >2000 lines or >100 KB | Warn but proceed; note "input was large" in the plan header |
| `--seed-todos` but TodoWrite tool unavailable (rare — version mismatch) | Skip the push silently; note in console "TodoWrite unavailable in this Claude Code version — plan file written, but todos not seeded" |

---

## Why this design

Six choices specific to `/plan`:

1. **Spec-as-input, not prompt** — plans derived from a written document are reproducible, auditable, and editable. Free-form prompts are ephemeral. v0.7 can add prompt input as a quick-mode for trivial cases.
2. **Two-phase research, single-phase synthesis** — project context and spec decomposition are independent inputs; they parallelize naturally. Synthesis requires holding both — single agent (the skill itself reasoning over agent outputs) is the right place.
3. **Plans accumulate, reports overwrite** — unlike `/analyze`'s and `/preflight`'s single-file reports, plans persist (`plans/<slug>-<ts>.md`). Re-planning the same spec after iteration produces a new file you can diff against the old.
4. **Per-task annotation, not just titles** — type, complexity, impact areas, dependencies, risks, acceptance criteria. A task without these is a wish; with them, it's a unit of work. Modern planning tools (Linear, Shortcut, JIRA's well-used incarnations) all converge on this richness.
5. **Dependency-ordered output** — the decomposer returns tasks in spec order; the synthesizer reorders by dependencies. This way the plan reads as an execution order, not a parse order.
6. **Read-only, never executes** — same contract as `/analyze` and `/preflight`. v0.7+ may add `--execute` to actually run the plan via Claude, but that's a separate skill-shaped concern (autonomy boundaries, checkpointing) — premature in v0.6.
