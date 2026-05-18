---
description: Analyzes a git diff and suggests a semver bump (major/minor/patch) with justification. Detects changeset usage and produces draft changeset content if applicable. Read-only — never modifies version manifests. Supports JS/TS, Python, Rust in v0.10.
disable-model-invocation: true
argument-hint: "[show] [--since=<ref>] [--limit=<N>] [--base=<ref>]"
allowed-tools: Read, Write, Glob, Grep, Bash(git status), Bash(git rev-parse *), Bash(git diff *), Bash(git log *), Bash(git tag *), Bash(git symbolic-ref *), Bash(test *), Bash(ls *), Bash(cat *), Bash(mkdir *), Task
---

# /kaizen:bump

Suggests a semver version bump based on recent changes. Spawns the `versioner` plugin agent (which reads the diff + manifest + changeset config) and writes a bump-suggestion report. **Never modifies version manifests** in v0.10 — applying the bump is your decision.

---

## Arguments

| Arg | Meaning |
|---|---|
| *(none)* | Analyze since auto-detected base (last tag if any, else `HEAD~10`). |
| `show` | Re-print the last report from `.claude/kaizen/bump-report.md`. Exclusive. |
| `--base=<ref>` | Override the base ref. Stop on invalid (no fallback). |
| `--since=<ref>` | Analyze commits since this ref. |
| `--limit=<N>` | Analyze the last N commits. |

Flags combine. `show` is exclusive.

`--apply` flag (auto-modify the manifest or write changeset) is **deferred to v0.11**. v0.10 is suggestion-only.

---

## Mode: `show`

```bash
test -f .claude/kaizen/bump-report.md
```

If absent: print `✗ No bump report exists. Run /kaizen:bump to generate one.`

Otherwise: print verbatim.

---

## Mode: full run

### Step 1: detect version manifest

Check for supported manifest files in priority order:

| File | Stack | Version field path |
|---|---|---|
| `package.json` | JS/TS | `.version` |
| `pyproject.toml` | Python | `project.version` (PEP 621) OR `tool.poetry.version` |
| `Cargo.toml` | Rust | `package.version` |

If none found: stop with `✗ kaizen bump: no supported version manifest found. Supported in v0.10: package.json, pyproject.toml, Cargo.toml.`

If multiple found (monorepo with mixed stacks): use the first by priority. Note in the report.

### Step 2: detect changesets

```bash
test -f .changeset/config.json && echo "changesets"
```

If present, the project uses changesets — bump output will include a draft changeset block.

### Step 3: resolve range

Priority order:
1. `--base=<ref>` if provided (stop on invalid).
2. `--since=<ref>` or `--limit=<N>` if provided.
3. **Most recent git tag** if any (`git tag --sort=-creatordate | head -1`). Compare since that tag.
4. Fallback: `HEAD~10..HEAD`.

Print the resolved range up front:

```
kaizen bump: analyzing range <base>..HEAD (<N> commits, current version <X.Y.Z> from <manifest>)
```

### Step 4: collect signals for the agent

```bash
git log <base>..HEAD --format='%h %s' --no-merges    # commit subjects
git log <base>..HEAD --format='%h %B' --no-merges    # full bodies (for BREAKING CHANGE detection)
git diff <base>..HEAD --stat                          # file change counts
```

Bound the body output to ~200 lines — the agent doesn't need full commit messages, just the headers and any breaking-change markers.

### Step 5: spawn versioner agent

Single Task call:

```
Task(subagent_type='versioner', prompt=`
  Recommend a semver bump for this project.

  Current version: <X.Y.Z>
  Manifest path: <path>
  Stack: <node|python|rust>
  Uses changesets: <yes|no>

  Diff range: <base>..HEAD
  Commits:
    <truncated log>

  Stat summary:
    <git diff --stat output>

  Return per your output format.
`)
```

### Step 6: write report

Write `.claude/kaizen/bump-report.md` (overwritten each run):

```markdown
# kaizen :: bump report

Generated: <ISO 8601>
Plugin version: <v>
Range analyzed: <base>..HEAD (<N> commits)
Current version: <X.Y.Z> (from <manifest>)
Changesets mode: <yes|no>

---

<versioner agent output verbatim>

---

## Apply guidance

<if changesets mode:>
1. Create the changeset file: `.changeset/<auto-slug>.md` (or use `npx changeset`)
2. Paste the draft content above
3. Commit the changeset alongside your code change
4. CI/CD release tool (changesets-action, etc.) handles the actual version bump

<if direct mode:>
1. Edit `<manifest-path>` and update the version field from "<X.Y.Z>" to "<X.Y.Z>"
2. Commit the manifest change (e.g., `chore: bump version to <X.Y.Z>`)
3. Tag the release: `git tag v<X.Y.Z> && git push --tags`
4. Optionally update CHANGELOG.md with the highlights

(v0.11 will add `--apply` to do this automatically.)
```

### Step 7: console summary

```
✓ kaizen bump: <bump-type> recommended

Current:    <X.Y.Z>
Suggested:  <X.Y.Z>
Mode:       <changesets | direct>

Top reasons:
  - <type>: <commit subject>
  - <type>: <commit subject>
  ...

Full report: .claude/kaizen/bump-report.md
  /kaizen:bump show       # re-print
  /kaizen:bump            # re-analyze after more commits
```

If no bump recommended:

```
ℹ kaizen bump: no version bump recommended for this range.
Reason: <agent's reason>
```

---

## Hard rules (never violate)

- **NEVER modify the version manifest.** v0.10 is suggestion-only. `--apply` comes in v0.11 with explicit user opt-in.
- **NEVER write a changeset file.** v0.10 outputs draft content for the user to paste; no auto-creation.
- **NEVER commit anything.** Same as all read-only skills.
- **NEVER guess unsupported manifest formats.** Surface "manual bump required" honestly.
- **Bias toward patch** for ambiguous diffs. Over-bumping causes downstream perception of breakage.

---

## Failure modes

| Failure | Behavior |
|---|---|
| Not a git repo | Refuse. Suggest `git init` + commit. |
| No supported manifest | Stop with the explicit "supported in v0.10" message. |
| Multiple manifests (monorepo) | Use first by priority order; note in report. |
| No tags AND user didn't pass --since/--limit/--base | Fall back to `HEAD~10`; note in report ("no release tags found, analyzed last 10 commits"). |
| Agent fails | Log in report; surface the failure to console. |
| Manifest exists but version field is malformed | Stop with `✗ Could not parse version from <manifest>: <reason>`. |

---

## Why this design

- **Suggestion-only in v0.10** preserves the read-only contract by default. Version bumps are consequential — gating with `--apply` (v0.11) is the right opt-in pattern.
- **Changeset detection** removes the "should I use changesets or direct bump?" friction for the user — the skill matches the project's existing workflow.
- **Versioner agent does the reasoning, skill does the orchestration** — same pattern as `/preflight` and `/plan`. The agent's output is the authoritative recommendation; the skill wraps it with apply guidance.
- **Stack support starts narrow (JS/TS, Python, Rust)** — covers the most common use cases. Others get an honest "manual bump required" rather than wrong auto-detection.
