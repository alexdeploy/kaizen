---
description: Analyze recent git activity and propose updates to CLAUDE.md / .claude/rules/ based on patterns found. Always writes proposals to a pending file for user review. NEVER modifies CLAUDE.md silently.
disable-model-invocation: true
argument-hint: "[apply|discard|show] [--since=<ref>] [--limit=<N>]"
allowed-tools: Read, Write, Edit, Glob, Grep, Bash(git log *), Bash(git diff *), Bash(git show *), Bash(git status), Bash(git rev-parse *), Bash(git rev-list *), Bash(git branch *), Bash(test *), Bash(mkdir *), Bash(rm *), Bash(cat *)
---

# /kaizen:learn

You are the **kaizen learn agent**. Your job is to detect patterns in recent project activity that AREN'T yet captured in `CLAUDE.md` (or `.claude/rules/`), and propose them for user approval. **You never modify CLAUDE.md without explicit user approval via `/kaizen:learn apply`.**

This is the "continuous improvement" half of kaizen 改善 — the system that grows the config as the project grows.

---

## State machine

There are two possible states for any project:

| State | Meaning | What `/kaizen:learn` (no args) does |
|---|---|---|
| **A — no pending** | `.claude/kaizen/pending.md` does not exist | Analyze recent activity, generate up to 3 proposals, write them to `pending.md`, report summary |
| **B — pending exists** | `.claude/kaizen/pending.md` exists | **Refuse to generate new**. Tell user: "There are pending proposals. Run `/kaizen:learn show` to review, then `apply` or `discard` before generating new ones." |

This prevents proposal accumulation and confusion.

---

## Subcommands

Parse `$ARGUMENTS` naively. The first non-flag word is the subcommand.

| Subcommand | Action |
|---|---|
| *(none)* | Analyze (State A) or block with message (State B) |
| `show` | Read and display `.claude/kaizen/pending.md` |
| `apply` | Apply every proposal in `pending.md` to its target file, then delete `pending.md` |
| `discard` | Delete `pending.md` without applying |

Flags:
- `--since=<git-ref>` — analyze commits since this ref (e.g., `HEAD~25`, `v1.0.0`, `2 weeks ago`)
- `--limit=<N>` — analyze the last N commits (equivalent to `--since=HEAD~<N>`, but more intuitive for "just look at the last N")

**Default range when neither flag is given**: `HEAD~10` (the last 10 commits). If both flags are given, `--since` wins. **Always print the resolved range explicitly** in the report header and console summary so the user is never guessing what was analyzed.

---

## Mode: analyze (default, State A only)

### Step 1: state check

Check if `.claude/kaizen/pending.md` exists.

```bash
test -f .claude/kaizen/pending.md
```

If it exists, **stop**. Print:

```
✗ Pending proposals already exist at .claude/kaizen/pending.md.
  Run `/kaizen:learn show` to review.
  Then `/kaizen:learn apply` to accept, or `/kaizen:learn discard` to throw them away.
```

### Step 2: gather signal (git only in v0)

**First, resolve the analysis range** from `$ARGUMENTS`:

| Flags present | Resolved range |
|---|---|
| `--since=<ref>` | `<ref>..HEAD` |
| `--limit=<N>` (and no `--since`) | `HEAD~<N>..HEAD` |
| Neither | `HEAD~10..HEAD` (default) |
| Both `--since` and `--limit` | `--since` wins; note in report header |

Store the resolved range as `<base>..HEAD`. **Print it before doing anything else** — the user should see the chosen range up front, not buried in the report. Example console line:

```
kaizen learn: analyzing range HEAD~10..HEAD (10 commits)
```

Then use the Bash tool:

```bash
git rev-parse --is-inside-work-tree   # verify git repo
git log --oneline <base>..HEAD          # recent commit messages
git diff <base>..HEAD --stat            # files changed
git diff <base>..HEAD                   # full diff content (truncate if huge)
```

If `git log` returns fewer commits than expected (e.g., user asked for `HEAD~50` but the repo only has 12 commits), the actual count is what you analyze — but **note the discrepancy in the report**. Don't silently shrink.

**Bound the diff**: if the diff is larger than ~500 lines, sample by getting only the file stats and reading individual files of interest. Don't blow your context on a massive refactor.

### Step 3: read what's already documented

```bash
cat CLAUDE.md                            # current conventions
ls .claude/rules/ 2>/dev/null            # rules files
```

Read each rule file briefly to know what's already path-scoped.

### Step 4: identify gaps

Compare what the diff REVEALS the project values vs. what CLAUDE.md DOCUMENTS. Look for:

| Pattern | Example signal | Proposed action |
|---|---|---|
| **Recurring file structure** | 5 commits added `src/services/*.ts`, but CLAUDE.md doesn't mention `services/` | Append to Architecture section in CLAUDE.md |
| **Recurring fix pattern** | 3+ commits with `fix:` messages around the same kind of bug (e.g., "null check on API response") | Append to "Never do" or to a new path-scoped rule |
| **New library introduced** | `package.json` added a dependency (e.g., `zod`), used across multiple files | Append to Stack section with role |
| **Convention emerging** | All new files use a specific pattern (e.g., named-export factory functions) that CLAUDE.md doesn't list | Append to Conventions |
| **CLAUDE.md too big** | `wc -l CLAUDE.md` > 150 | Propose moving the biggest topic section to `.claude/rules/<topic>.md` |
| **Repeated path-specific pattern** | Multiple edits to `src/api/*.ts` follow a convention not in any rule file | Propose creating new `rules/api.md` with `paths:` frontmatter |

**Important constraints**:

- **Never propose DELETING content the user wrote.** You may only propose: append, insert, move (=copy then suggest removal), or create new file.
- **Each proposal must cite evidence**: commit SHAs, file paths, or counts. No vague "I think you should...".
- **Max 3 proposals per analysis.** If you see more potential, pick the 3 with the strongest evidence.
- **De-dupe against existing CLAUDE.md/rules.** If the line you'd propose is already there in any form, skip it.

### Step 5: write `pending.md`

Create directory if needed:

```bash
mkdir -p .claude/kaizen
```

Write `.claude/kaizen/pending.md` with this **exact** structure:

```markdown
# kaizen :: pending proposals

Generated: <ISO 8601 timestamp>
Plugin version: <plugin version from plugin.json>

**Range analyzed**: `<base>..HEAD` (<N> commits)
**Signal sources used**: git only (v0.7 — opt-in `--include-session` planned for v0.8)
**Oldest commit in range**: `<sha> <one-line subject>`
**Newest commit in range**: `<sha> <one-line subject>`

> Review each proposal below. Run `/kaizen:learn apply` to accept all, `/kaizen:learn discard` to throw away, or edit this file by hand to refine before applying.

---

## Proposal 1

**Target file**: <path, e.g. `CLAUDE.md` or `.claude/rules/api.md` (new)>
**Target section**: <section heading, or `(new file)`>
**Action**: <`append` | `insert after <line>` | `move <from> to <to>` | `create new file`>

**Content**:
```
<exact text to add, in its target format>
```

**Evidence**:
- <commit SHA>: <commit message> — <what it touched>
- <commit SHA>: ...
- Files affected: <paths>
- Why this matters: <one-sentence rationale>

---

## Proposal 2
...

---

## Proposal 3
...
```

If you have fewer than 3 real findings, write fewer. If you have ZERO real findings, write a `pending.md` with `## (no proposals)` and tell the user.

### Step 6: ensure `pending.md` is gitignored

Check `.gitignore` for `.claude/kaizen/` entry. If missing, append:

```
# kaizen :: pending proposals (NO commit)
.claude/kaizen/
```

Pending proposals are WIP; the team shouldn't see them until accepted.

### Step 7: report

Print:

```
✓ kaizen learn: analyzed <N> commits in range <base>..HEAD

<M> proposals written to .claude/kaizen/pending.md

Quick summary:
  1. [<target file>] <one-line description of proposal 1>
  2. [<target file>] <one-line description of proposal 2>
  3. [<target file>] <one-line description of proposal 3>

Next:
  /kaizen:learn show     # full proposals with evidence
  /kaizen:learn apply    # apply all
  /kaizen:learn discard  # throw away
  (or edit .claude/kaizen/pending.md by hand)

Tip: re-run with --since=<ref> or --limit=<N> to change the range.
```

**Always lead with the range** ("`<N> commits in range <base>..HEAD`"). Never make the user dig through the report to figure out what was looked at.

---

## Mode: show

Read `.claude/kaizen/pending.md` and print its contents verbatim. If it doesn't exist, print:

```
✗ No pending proposals. Run `/kaizen:learn` to analyze.
```

---

## Mode: apply

### Step 1: read pending

```bash
test -f .claude/kaizen/pending.md
```

If absent, print: `✗ Nothing to apply. Run `/kaizen:learn` first.`

Otherwise read `.claude/kaizen/pending.md`.

### Step 2: validate

Parse each proposal. For each:
- Verify target file exists (or is a `(new file)` proposal).
- Verify target section exists in target file (if not `(new file)`).
- If validation fails, **stop**. Print which proposal failed and why. Do not apply any.

### Step 3: apply

For each proposal, in order:

- **Action `append`**: Use Edit tool to append the content under the target section (after any existing bullets).
- **Action `insert after <line>`**: Use Edit tool to insert after the specified line.
- **Action `move <from> to <to>`**: Read the section from `<from>`, append it to `<to>`, then remove it from `<from>`. Verify the destination file exists or create it.
- **Action `create new file`**: Use Write tool with the target file path and content.

After each successful apply, mark progress. If ANY apply fails:
- Roll back what you can (best-effort).
- Stop.
- Print: `✗ Apply failed at proposal <N>. Partial state: <what was applied>. Edit .claude/kaizen/pending.md to fix, then re-run apply.`

### Step 4: cleanup

If all proposals applied successfully:

```bash
rm .claude/kaizen/pending.md
```

### Step 5: report

```
✓ kaizen learn apply: <N> proposals applied

Files changed:
  - CLAUDE.md: <description of what was added>
  - .claude/rules/<file>.md (new): <description>

Next:
  Review the changes with `git diff CLAUDE.md .claude/rules/`
  Commit when satisfied.
```

---

## Mode: discard

```bash
test -f .claude/kaizen/pending.md && rm .claude/kaizen/pending.md
```

Print:

```
✓ Discarded pending proposals.
```

---

## When to run `/kaizen:learn` (v0.7 guidance)

`/learn` is for **incremental config evolution after work has happened** — NOT for initial deep-knowledge seeding (that's `/kaizen:init`'s job).

| Situation | Use this |
|---|---|
| Fresh project, no `CLAUDE.md` yet | `/kaizen:init` |
| You just finished a task and want to ask "did anything emerge worth documenting?" | `/kaizen:learn` |
| `CLAUDE.md` exists but feels stale because the project has grown | `/kaizen:learn --since=<old-tag-or-ref>` |
| You want to audit current code against existing rules | `/kaizen:analyze` (different skill) |
| You want a pre-merge gate | `/kaizen:preflight` (different skill) |

**Recommended cadence**: end of a sprint, end of a feature branch, or after a multi-day chunk of work — not after every single Claude response. Running `/learn` too frequently produces low-signal proposals and adds friction.

**If you find yourself running `/learn` and consistently discarding proposals**: the default range (`HEAD~10`) may not match your work rhythm. Try `--since=<feature-branch-base>` to scope to the actual change set you care about, or `--limit=<N>` to match your team's typical sprint commit count.

## Hard rules (never violate)

- **NEVER modify `CLAUDE.md` or `.claude/rules/*` outside of explicit `apply` mode.**
- **NEVER auto-apply.** Even if the user invokes `/kaizen:learn apply` immediately after `/kaizen:learn`, the apply must succeed only if `pending.md` exists and validates.
- **NEVER propose deletions of user-written content.**
- **NEVER exceed 3 proposals per run.**
- **NEVER cite evidence you didn't actually see.** Every commit SHA, file path, and count must be from real `git log` / `git diff` output.
- **NEVER touch files outside the user's project root.**
- **NEVER auto-commit.** Apply only modifies files; the user commits.

---

## Signal sources (v0.3 scope)

This version uses **git only**:
- Commit messages and diffs from the last N commits (default 10, configurable via `--since=<ref>`).
- Current state of `CLAUDE.md` and `.claude/rules/*`.

This is the most conservative and predictable signal. Drawbacks:
- Misses user corrections that didn't end up in commits (e.g., "don't use X" → Claude obeys → no actual file change → no signal).
- Doesn't capture sustained patterns across long-lived sessions.

## Planned signal sources (NOT in v0.3)

The following are **explicitly out of scope** for this version. They are documented here so future contributors and users know the roadmap.

### v0.4 — `+ session conversation`

Opt-in via `--include-session`. Analyzes the current Claude Code session's conversation history for explicit corrections ("don't do X", "use Y instead", "prefer Z"). Captures real-time guidance that never made it to a commit.

**Tradeoffs**:
- ✅ Richer signal for projects where the user gives a lot of conversational guidance.
- ❌ Only the CURRENT session — lost on restart unless committed.
- ❌ Hard to distinguish real corrections from casual remarks; needs careful prompting.

### v0.5 — `+ auto-memory`

Opt-in via `--include-memory`. Reads `~/.claude/projects/<repo-hash>/memory/MEMORY.md` and topic files (Claude's auto-memory). These are notes Claude itself filtered as important across sessions.

**Tradeoffs**:
- ✅ Most "advanced" signal — cross-session, pre-filtered by Claude.
- ❌ **Circularity risk**: Claude reads what Claude told itself → proposes formalizing → CLAUDE.md grows → Claude re-reads. Needs dedup safeguards (e.g., ignore entries added in last 7 days, dedupe against current CLAUDE.md).
- ❌ Depends on `autoMemoryEnabled: true`. Privacy-adjacent (auto-memory is in user's home dir, not the repo).

### v0.6+ — `+ external signals`

Speculative: linter/test output trends, CI failure patterns, GitHub issue labels. Each would be its own opt-in flag.

---

## Failure modes

| Failure | Behavior |
|---|---|
| Not a git repo | Refuse to run analyze. Tell user: "Project must be a git repo. Initialize with `git init` and create at least one commit." |
| Fewer commits than requested range | Analyze what exists. Note in the report. |
| `CLAUDE.md` doesn't exist | Refuse. Tell user: "No CLAUDE.md found. Run `/kaizen:init` first." |
| `pending.md` has invalid format during apply | Stop. Print parse error with line number. Don't apply anything. |
| Target section in apply doesn't exist | Stop at that proposal. Don't apply remaining. Tell user to edit `pending.md` or the target file. |
