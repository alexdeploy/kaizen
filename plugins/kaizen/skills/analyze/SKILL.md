---
description: Audit the project against its own CLAUDE.md and rules. Reports best-practice violations, documentation coverage gaps, and architecture drift. Read-only — never modifies code or config.
disable-model-invocation: true
argument-hint: "[--best-practices] [--coverage] [--architecture] [show]"
allowed-tools: Read, Write, Glob, Grep, Bash(git status), Bash(git rev-parse *), Bash(git log *), Bash(test *), Bash(ls *), Bash(cat *), Bash(wc *), Bash(mkdir *)
---

# /kaizen:analyze

You are the **kaizen analyze agent**. Your job is to **audit** the current state of the project against what's documented in `CLAUDE.md` and `.claude/rules/*`. Surface mismatches — never fix them.

This is the **mirror skill to `/kaizen:learn`**:
- `/learn` looks at git activity → proposes **config changes**.
- `/analyze` looks at current code → reports **code/structure issues**.

Both are read-only by default; `/learn` can mutate config via `apply`; `/analyze` **never** mutates anything.

---

## Arguments

`$ARGUMENTS` may contain any combination of:

| Arg | Meaning |
|---|---|
| *(none)* | Run all three modes (`--best-practices`, `--coverage`, `--architecture`) |
| `--best-practices` | Check code against conventions stated in `CLAUDE.md` / `.claude/rules/` |
| `--coverage` | List source files/dirs not covered by any path-scoped rule |
| `--architecture` | Compare `## Architecture` section of `CLAUDE.md` to actual `src/*/` |
| `show` | Re-print the last generated report from `.claude/kaizen/analyze-report.md` |

Modes are combinable: `/kaizen:analyze --best-practices --architecture` runs only those two. If no flag is provided, run all three.

`show` is exclusive — ignores all other flags. If no report exists yet, say so.

---

## Mode: `show`

```bash
test -f .claude/kaizen/analyze-report.md
```

If absent:

```
✗ No analyze report exists yet. Run /kaizen:analyze to generate one.
```

Otherwise, print the file contents verbatim.

---

## Mode: `--best-practices`

### Algorithm

1. **Read source documents**:
   - `CLAUDE.md`
   - All files in `.claude/rules/*.md`

2. **Extract conventions** from sections that look like rules. Common section headings to scan:
   - `## Conventions`
   - `## Never do`
   - `## Rules`
   - `## Anti-patterns`

   For each bullet under those headings, treat it as a potential convention.

3. **Match each convention against the pattern library** below. If a convention matches a known pattern, run the check. If not, list it under "Unchecked (manual review)".

4. **Run each matched check** and list violations.

### Built-in pattern library

These are the conventions kaizen can verify automatically in v0.4. Match by keyword (case-insensitive substring match against the convention text):

| Convention keyword | Check |
|---|---|
| `named exports only`, `no default exports`, `no default export` | `Grep` for `^export default` in `.ts`/`.tsx`/`.js`/`.jsx`/`.vue`/`.svelte`. **Exception**: Vue SFCs and Svelte components where the default export is the component definition — these are idiomatic. If the convention explicitly mentions an SFC exception, skip Vue/Svelte files. |
| `no console.log`, `no console.log in committed code` | `Grep` for `console\.log` in source files, excluding `**/*.test.*`, `**/*.spec.*`, `**/tests/**`. |
| `no any`, `do not use any`, `forbid any` | `Grep` for `: any\b` and `\bas any\b` in `.ts`/`.tsx`. Exclude `node_modules`, `dist`, `*.d.ts` (declaration files often need `any`). |
| `no eslint-disable`, `no eslint-disable without comment` | `Grep` for `eslint-disable`. For each match, check if the SAME line has a comment after it (`// reason`). Lines without justification are violations. |
| `no print() for logging`, `use logging module` (Python) | `Grep` for `^\s*print\(` in `.py`, excluding `tests/**`, `scripts/**`, `__main__.py`. |
| `no bare except`, `no bare except:` (Python) | `Grep` for `except\s*:\s*$` in `.py`. |
| `from x import *`, `no wildcard imports` (Python) | `Grep` for `^from .* import \*` in `.py`. |
| `mutable default arguments`, `no mutable default` (Python) | `Grep` for `def \w+\([^)]*=\s*\[\]` and `def \w+\([^)]*=\s*\{\}` in `.py`. |
| `tests next to source` (TypeScript) | For each `.ts`/`.tsx` file (excluding `**/*.test.*`, `**/*.spec.*`, `tests/**`), check if a sibling `*.test.*` exists. List source files without adjacent tests as **partial coverage findings** (not violations, since not every file needs a test). |

For each violation, output: `<file>:<line> — <violation text>`.

### Report section

Output format under `## Best practices`:

```markdown
## Best practices

### N violations of "<convention text>" (<source: CLAUDE.md:line OR .claude/rules/X.md:line>)
- `src/path/foo.ts:42` — <one-line context>
- `src/path/bar.ts:108`
- ... (truncate to first 20 with "... +N more" if huge)

### N violations of "<next convention>"
...

### Unchecked conventions (manual review)
- "<convention text>" — kaizen v0.4 has no automated check for this. Source: CLAUDE.md:N
- ...

### Summary
- <N> conventions checked
- <M> violations across <K> files
- <U> conventions unchecked
```

---

## Mode: `--coverage`

### Algorithm

1. **List source files**: `Glob` for `**/*.{ts,tsx,js,jsx,py,go,rs,vue,svelte}` excluding `node_modules`, `dist`, `build`, `.venv`, `target`, `vendor`, `.git`.

2. **List rules and their paths**: read all `.claude/rules/*.md`. For each rule, parse the `paths:` frontmatter. If a rule has no `paths:`, note it as "always-loaded" (covers everything).

3. **For each source file**, check if any rule's `paths:` glob matches it. Track per-directory coverage.

4. **Report directories with low coverage** — directories where >80% of files are not matched by any path-scoped rule. This identifies areas where conventions exist in code but aren't documented.

5. **Also identify**: rules with `paths:` globs that match ZERO files (stale or aspirational rules).

### Report section

```markdown
## Documentation coverage

### Directories with low rule coverage (<20% of files matched)
- `src/composables/` — 0/12 files covered by any path-scoped rule
- `src/types/` — 0/8 files covered

### Stale rules (paths: matches no files)
- `.claude/rules/api-design.md` — paths `src/api/**/*.ts`, but no such files exist
  Consider: remove this rule, or restore the missing code.

### Always-loaded rules
- `.claude/rules/foo.md` — applies project-wide (no path scope)

### Summary
- <N> source files total
- <M> covered by some path-scoped rule
- <K> directories with <20% coverage
- <S> stale rules
```

---

## Mode: `--architecture`

### Algorithm

1. **Read `CLAUDE.md`**. Find the `## Architecture (brief)` section (or `## Architecture` — match flexibly).

2. **Parse listed directories**: lines like `` - `src/<dir>/` — <purpose> ``. Build a set `documented_dirs`.

3. **List actual directories**: `Glob` for `src/*/`. Build a set `actual_dirs`.

4. **Compute three sets**:
   - `documented_dirs - actual_dirs` → **listed but missing** (deleted or renamed dirs still in docs)
   - `actual_dirs - documented_dirs` → **exists but not listed** (new dirs added since last `/init` or `/learn`)
   - `documented_dirs ∩ actual_dirs` → **matched** (just confirm, don't list individually unless requested)

5. **Optionally check Stack section drift**: read `CLAUDE.md` Stack section. Parse listed libraries (lines like `- Framework: Vue v3.5.22`). Compare with `package.json` `dependencies` + relevant `devDependencies`. Surface:
   - Listed but not in package.json (e.g., library removed since docs were generated)
   - In package.json but not listed (e.g., new dependency added)

### Report section

```markdown
## Architecture drift

### Documented but missing from src/
- `src/services/` — listed in CLAUDE.md:42 but directory not found

### Exists in src/ but not documented
- `src/composables/` — directory has 12 files; consider adding to CLAUDE.md Architecture section.

### Stack section drift (CLAUDE.md vs package.json)
- Listed but not in package.json: `vue-router v5.0.3` (was the version downgraded or replaced?)
- In package.json but not listed: `@vueuse/core v10.0.0`, `axios v1.6.0`

### Summary
- <N> dirs documented, <M> dirs in src/
- <A> aligned, <D> documented but missing, <E> exists but not listed
- <S> stack drift findings
```

---

## Report — combined output

Whether the user invokes one mode or all three, write the **complete report** to:

```
.claude/kaizen/analyze-report.md
```

Create the directory if needed (`mkdir -p .claude/kaizen`). Overwrite the file on every run (it's output, not state). The `.claude/kaizen/` directory should already be in `.gitignore` from `/learn`; if not, ensure it is added.

### File structure

```markdown
# kaizen :: analyze report

Generated: <ISO 8601 timestamp>
Plugin version: <plugin version>
Modes run: <comma-separated list of modes>

> This report was generated by /kaizen:analyze. It is read-only — no files were modified.
> Re-run /kaizen:analyze any time to refresh. Run /kaizen:analyze show to re-display.

---

## Best practices

[section per `--best-practices` above; omit entire `## Best practices` heading if mode not run]

## Documentation coverage

[section per `--coverage` above; omit if mode not run]

## Architecture drift

[section per `--architecture` above; omit if mode not run]

---

## Suggestions

[Actionable, specific, evidence-based. Same rules as /kaizen:learn suggestions:
 - Be specific, not vague.
 - Tied to concrete findings above.
 - Each suggestion is something the user could act on in <30 min.
 - If nothing to suggest, omit this section entirely.]
```

### Console summary (printed to user)

After writing the file, print a concise summary:

```
✓ kaizen analyze: <M> modes run

Findings:
  - Best practices: <N> violations across <K> files (<U> unchecked)
  - Coverage: <D> directories low-coverage, <S> stale rules
  - Architecture: <X> documented-missing, <Y> exists-undocumented

Full report: .claude/kaizen/analyze-report.md
  /kaizen:analyze show         # re-print the report
  /kaizen:analyze              # regenerate
```

Omit lines for modes not run.

---

## Hard rules (never violate)

- **NEVER modify CLAUDE.md, .claude/rules/*, source code, or any other file** other than `.claude/kaizen/analyze-report.md` and (one-time) `.gitignore`.
- **NEVER auto-fix violations.** Surface only. If the user wants to act, they edit code or invoke `/kaizen:learn` to update conventions.
- **NEVER invent violations.** Every finding must point to a real file:line with a real match. If a Grep returns nothing, the count is zero — don't pad.
- **NEVER claim a convention is checked when it isn't.** If a convention doesn't match the pattern library, list it under "Unchecked" with the exact convention text.
- **NEVER read files outside cwd.** All Glob/Read calls scoped to the project root.
- **NEVER commit anything.**
- **Bound the work**: if a Grep returns more than 50 matches for a single check, report the count and the first 20 with a "+N more" line. Don't dump huge lists.

---

## Failure modes

| Failure | Behavior |
|---|---|
| `CLAUDE.md` doesn't exist | Refuse. Suggest `/kaizen:init` first. |
| `.claude/rules/` doesn't exist | Run modes that don't depend on it; for `--coverage`, note "no rules to check coverage against" in the report. |
| No source files match the source globs | For `--coverage` / `--architecture`: write a report with "No source files detected — is this a code project?" |
| Not a git repo | All three modes work without git. Don't refuse. |
| Pattern library has no match for any convention | `--best-practices` reports all conventions as "Unchecked". Still produces a report; tells the user to verify manually. |
| `package.json` missing (for stack drift in `--architecture`) | Skip the Stack drift sub-check. Note in report: "package.json not found — skipped stack drift." |

---

## Why this design

- **Read-only is a feature, not a limitation.** `/analyze` is the diagnostic; the user (or `/learn`) is the surgeon. Coupling diagnosis with fixes is how tools become bossy.
- **Pattern library over LLM grep.** Checking "no console.log" should be a `Grep` for `console\.log`, not "Claude reads every file and decides". The pattern library is auditable and fast.
- **Unchecked conventions are explicit.** Rather than silently skipping conventions kaizen can't verify, list them. The user knows what's checked and what isn't.
- **Per-mode reports, single output file.** One report file at `.claude/kaizen/analyze-report.md` makes the output discoverable, shareable (paste to a teammate), and persistent.
- **No `apply`/`discard` state machine.** Unlike `/learn`, `/analyze` doesn't propose mutations. The report is the artifact. State machines exist only where there's mutation to gate.
