---
description: Audit the project against its own CLAUDE.md and rules, verifying each rule with the check from the versioned standards catalog it came from. Reports violations by rule id with rationale and source, plus rules deprecated or newly available since the config was generated, documentation coverage gaps, and architecture drift. Read-only — never modifies code or config.
disable-model-invocation: true
argument-hint: "[--best-practices] [--coverage] [--architecture] [show]"
allowed-tools: Read, Write, Glob, Grep, Bash(kaizen-detect), Bash(kaizen-detect *), Bash(kaizen-standards *), Bash(kaizen-lock status), Bash(git status), Bash(git rev-parse *), Bash(git log *), Bash(test *), Bash(ls *), Bash(cat *), Bash(wc *), Bash(mkdir *)
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

Every rule kaizen wrote into this project carries its catalog id as an HTML
comment:

```markdown
- **No `any`.** Use `unknown` and narrow. <!-- TS-003 -->
```

That id is the whole point of this mode. It replaces what v0.4 did — matching a
convention's *prose* against a hardcoded keyword table — which meant rewording a
convention silently un-checked it, with no error anywhere. Now the rule and its
check are the same object, joined by a stable id.

### Step 1 — establish context

```
kaizen-detect
kaizen-standards version
kaizen-lock status
```

From these you get the stack and maturity (to filter the catalog), the installed
catalog version, and — if a lock exists — the `standards_version` the project's
config was **generated** against. Keep both versions: their difference is the
staleness report in step 5.

If `kaizen-standards` is unavailable, say so plainly and fall back to reading
`CLAUDE.md` conventions as prose with **no** automated checks; report everything
as unchecked. Never guess a rule's check from memory.

### Step 2 — classify every convention in the project's config

Read `CLAUDE.md` and `.claude/rules/*.md`. For each bullet under `## Conventions`,
`## Never do`, `## Never`, `## Rules` or `## Anti-patterns`, sort it into one of
three populations. **These are different things and must never be mixed in the
report.**

| Population | How to tell | How to treat it |
|---|---|---|
| **A — catalog rule** | Line ends with `<!-- RULE-ID -->` | Verify with the catalog's own check. Report by id. |
| **B — the user's own** | No id comment | **Not kaizen's to judge.** Try one exact-text match against catalog statements; if it matches, use that check and note it was matched by text. Otherwise: unchecked. |
| **C — available, not adopted** | In the catalog for this stack/maturity, but no line in the config carries its id | Report as a gap, never as a violation. |

Population B exists because most projects have hand-written conventions, and
configs generated before ids existed. An exact statement match is deterministic
and gets reported as such — it is not the old fuzzy substring matching, and it
must not become that.

### Step 3 — run the checks

```
kaizen-standards checks --stack <detect.stack> --maturity <detect.maturity>
```

Each entry carries `id`, `statement` and a `check`. Run only the checks whose id
appeared in population A (or was text-matched in B).

| `check.type` | How to run it |
|---|---|
| `grep` | `Grep` with the rule's `pattern`, restricted to `include` globs, minus `exclude` globs. Every match is a violation. |
| `sibling_file` | For each file matching `include` (minus `exclude`), check that a file matching `pattern` (with `{basename}` substituted) exists beside it. Report misses as **partial coverage**, not violations. |
| `none` | Not runnable. Goes under "Unchecked" with the rule's own `reason`. |

Hard rules for running checks:

- **Use the pattern exactly as the catalog gives it.** Do not "improve" it, widen
  it, or translate it. If a pattern looks wrong, report that as a finding about
  the catalog — do not silently substitute your own.
- **Honour `include` and `exclude`.** A violation reported in `node_modules` or a
  `.d.ts` destroys trust in the whole report.
- **In a workspace** (`detect.workspaces.type != "none"`), run each check across
  all members and attribute findings per package, so a monorepo report says
  which package is affected.
- **Bound the output**: more than 50 matches for one rule → report the count and
  the first 20 with `... +N more`.
- **Surface the check's own `note` when it has one.** Several patterns have known
  false positives — a regex has no idea whether a match sits inside a comment or
  a string. Print the note under the rule's findings so the reader can dismiss
  what should be dismissed. Hiding a known limitation to make a report look
  cleaner is the fastest way to make the next report worthless.
- **Show enough context to judge a match**: the matching line, not just the line
  number.

### Step 4 — enrich each violation with its provenance

For every rule that produced findings, you already have `statement`, `severity`,
`rationale` and `sources` from the catalog. Include the first sentence of the
rationale and the first source link. **This is the difference between "you broke
a rule" and "here is why this rule exists and where it comes from"** — and it is
free, because the data is in the object you already read.

Do not paraphrase a rationale. Quote it or trim it to its first sentence.

### Step 5 — standards staleness

Two questions, both answerable from the catalog:

1. **Deprecated or vanished rules.** For each id in population A, look it up
   (`kaizen-standards show <ID>`). If `status` is `deprecated`, report it with
   its `deprecated_by` successor. If the id does not exist in the catalog at all,
   report it as removed — the config predates a catalog change, or the id was
   hand-edited.
2. **Rules added since this config was generated.** If the lock recorded a
   `standards_version`:
   ```
   kaizen-standards list --stack <stack> --maturity <maturity> --added-after <lock standards_version> --json
   ```
   Everything returned is a rule the project never had the chance to adopt.

Both belong under a `### Standards status` heading, not under violations. A
missing rule is not a violation of anything.

If there is no lock, say so: staleness cannot be computed, only population C.

### Report section

Output format under `## Best practices`:

```markdown
## Best practices

### Standards status

| | |
|---|---|
| Config generated against | standards@2026.08 (from `.claude/kaizen/lock.json`) |
| Catalog installed | standards@2026.09 |
| Stack / maturity used | `backend-node,frontend,typescript` / `mature` |

- **2 rules added since your config was generated** — `<ID>`, `<ID>`.
  Run `/kaizen:upgrade` to adopt them.
- **1 rule in your config is deprecated** — `<ID>`, superseded by `<ID>`.
- **0 rules in your config are unknown to the catalog.**

(Omit any bullet that is zero. If there is no lock, replace the first two rows
with: `Config generated against | unknown (no lock file — run /kaizen:init to start tracking)`.)

### Violations

#### [safety] PY-008 — No bare `except:`
`backend/src/features/scan/ocr.py:142`
`backend/src/features/scan/ocr.py:207`
> A bare except also catches `KeyboardInterrupt` and `SystemExit`, so it makes a
> program that cannot be stopped.
Source: PEP 8 — Programming Recommendations · https://peps.python.org/pep-0008/#programming-recommendations

#### [convention] TS-003 — No `any`
`frontend/src/services/api.ts:88` (matched `: any`)
... +14 more
> `any` disables checking for every expression it touches, and it spreads.
Source: TypeScript Handbook — unknown · https://www.typescriptlang.org/docs/handbook/2/functions.html#unknown

(Order: severity first — security, safety, convention — then by id.)

### Partial coverage

- **TS-002** (tests next to source): 34 of 41 source files have no adjacent test.
  Not a violation; not every file warrants one.

### Available but not adopted

- **TS-009** (safety) — No tests that depend on real wall-clock time without
  freezing it. Added 2026-08-05, applies to this stack, not present in your config.

### Unchecked (manual review)

**Your own conventions** (no catalog id — kaizen does not judge these):
- "Nunca usar `lean()` sin proyección explícita en rutas multi-tenant." — CLAUDE.md:48

**Catalog rules with no mechanical check:**
- **UNI-001** — requires branch protection state, not file content.
- **PY-001** — coverage of hints is mypy's job, not a grep's.

**Matched by text, not by id** (consider `/kaizen:upgrade` so these carry ids):
- "No `console.log` in committed code." → TS-004

### Summary
- <N> catalog rules verified, <M> violations across <K> files
- <P> partial-coverage findings
- <U> conventions unchecked (<U1> yours, <U2> not mechanically checkable)
- Standards: <added> newer rules available, <dep> deprecated in use
```

**Never report a population C rule as a violation**, and never present a
hand-written convention of the user's as a kaizen standard. Those two mistakes
turn a useful audit into an argument.

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

   **In a workspace** (`kaizen-detect` reports `workspaces.type != "none"`): there
   is usually no root `src/`. Glob `<package>/src/*/` for each package in
   `workspaces.packages` instead, and keep the package prefix in the set so the
   comparison against the documented list is like-for-like. Globbing a root
   `src/` that does not exist would report every documented directory as missing.

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
- **NEVER claim a convention is checked when it isn't.** A convention with no catalog id and no exact text match goes under "Unchecked" with its exact text.
- **NEVER invent or adjust a check.** Patterns come from the catalog verbatim. If one looks wrong, report that as a finding about the catalog.
- **NEVER judge a convention the user wrote themselves** against catalog rules. Population B is theirs.
- **NEVER report an unadopted catalog rule as a violation.** A rule the project never had is a gap, not a breach.
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
- **Deterministic checks over LLM grep.** A rule like "no logging calls in committed code" is verified by running the catalog's pattern through `Grep`, not by "Claude reads every file and decides". Auditable, fast, and reproducible. (The patterns themselves live in the catalog and appear nowhere in this file — see the harness check that enforces it.)
- **The rule and its check are one object.** Until v0.14 the convention's prose lived in a template and its check lived in this file, joined by case-insensitive substring matching — so rewording a convention silently disabled its verification, with no error anywhere. Now both come from the catalog, joined by a stable id.
- **Provenance is free, so it is mandatory.** The catalog entry already carries the rationale and the source, so every violation reports *why the rule exists*, not just that it was broken. A finding a developer can evaluate is a finding they might act on.
- **Three populations, never mixed.** Catalog rules kaizen wrote, conventions the user wrote, and catalog rules not yet adopted are three different things. Presenting a user's own rule as a kaizen standard, or an unadopted rule as a violation, turns an audit into an argument.
- **Unchecked conventions are explicit.** Rather than silently skipping conventions kaizen can't verify, list them. The user knows what's checked and what isn't.
- **Per-mode reports, single output file.** One report file at `.claude/kaizen/analyze-report.md` makes the output discoverable, shareable (paste to a teammate), and persistent.
- **No `apply`/`discard` state machine.** Unlike `/learn`, `/analyze` doesn't propose mutations. The report is the artifact. State machines exist only where there's mutation to gate.
