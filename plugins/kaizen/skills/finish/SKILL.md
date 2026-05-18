---
description: End-of-task orchestrator. Chains the full pre-merge ritual: deterministic checks (tests/typecheck/lint) → 4 parallel agents (security review, commit suggestion, version bump, docs gap) → unified SHIP/HOLD/BLOCK verdict + apply guidance. Read-only by default.
disable-model-invocation: true
argument-hint: "[show] [--base=<ref>] [--skip=<phases>] [--auto-fix]"
allowed-tools: Read, Write, Glob, Grep, Bash(git status), Bash(git rev-parse *), Bash(git diff *), Bash(git log *), Bash(git tag *), Bash(git branch *), Bash(git symbolic-ref *), Bash(git show *), Bash(npm test *), Bash(npm run *), Bash(npx tsc *), Bash(npx eslint *), Bash(npx eslint --fix *), Bash(npx prettier *), Bash(npx prettier --write *), Bash(pnpm test *), Bash(pnpm run *), Bash(yarn test *), Bash(yarn run *), Bash(bun test *), Bash(bun run *), Bash(pytest *), Bash(mypy *), Bash(ruff *), Bash(ruff check --fix *), Bash(ruff format *), Bash(go test *), Bash(go vet *), Bash(go fmt *), Bash(gofmt *), Bash(cargo test *), Bash(cargo check *), Bash(cargo fmt *), Bash(test *), Bash(ls *), Bash(cat *), Bash(mkdir *), Task
---

# /kaizen:finish

The **end-of-task ritual**. Runs everything you'd want to check before commit/PR, in a single skill:

- All the deterministic checks (`/preflight`'s Phase 1)
- All four reasoning agents in parallel: security review, commit suggestion, version bump suggestion, docs gap
- A unified report with verdict + per-concern guidance

This is the orchestrator that the `standard` and `advanced` `/kaizen:init` profiles document and recommend running before commits.

---

## Relationship to other skills

`/kaizen:finish` doesn't "call" `/preflight`, `/bump`, or `/docs` as functions — it **directly invokes the same underlying agents** that those skills use. This way:
- Single context window (no spawning sub-skills)
- One unified report instead of three
- ~Same token cost as running the three individually, but coordinated

The individual skills (`/preflight`, `/bump`, `/docs`) remain useful for focused runs (e.g., "I just want a bump suggestion"). `/finish` is for the full ritual.

---

## Arguments

| Arg | Meaning |
|---|---|
| *(none)* | Full run: all deterministic checks + all 4 agents + aggregate verdict. |
| `show` | Re-print the last report from `.claude/kaizen/finish-report.md`. Exclusive. |
| `--base=<ref>` | Override the auto-detected base ref. Stop on invalid (no fallback). |
| `--skip=<phases>` | Skip phases. CSV of: `tests`, `typecheck`, `lint`, `security`, `commit`, `bump`, `docs`. Example: `--skip=docs,bump` runs everything except docs gap and bump suggestion. |
| `--auto-fix` | Same as `/preflight --auto-fix`: opt-in mutation. Applies lint/format fixes before running checks. The only way `/finish` writes outside the report file. |

Flags combine. `show` is exclusive.

---

## Mode: `show`

```bash
test -f .claude/kaizen/finish-report.md
```

If absent: print `✗ No finish report exists. Run /kaizen:finish to generate one.`

Otherwise: print verbatim.

---

## Mode: full run

Execute the 6 phases below in order. Phase 4 spawns up to **4 agents in parallel** via a single message with multiple `Task` tool calls.

### Phase 1: setup (resolve base ref, enumerate changes, detect stack/manifests)

Same logic as `/preflight` Step 1-3:
- Resolve base ref (auto-detect or `--base` override)
- `git diff --name-only <base>..HEAD` for changed files
- Detect package manager + version manifest + changeset config (combining `/preflight` and `/bump` detection)

If no changes vs base, stop: `✓ No changes since <base>. Nothing to finish.`

### Phase 2: optional auto-fix (only if `--auto-fix` passed)

Same logic as `/preflight` Step 3.5:
- Warn if dirty git tree
- Run formatter/linter fix commands per stack
- Track what was modified for the report

### Phase 3: deterministic checks (sequential, Bash)

Same as `/preflight` Step 4:
- tests / typecheck / lint, sequential
- Capture exit code + bounded output
- Respect `--skip` for `tests`, `typecheck`, `lint`

### Phase 4: parallel agents (single message, up to 4 Task calls)

Issue up to **four** `Task` tool calls in ONE message:

1. `preflight-security` — unless `--skip=security`
2. `commit-suggester` — unless `--skip=commit`
3. `versioner` — unless `--skip=bump`
4. `docs-keeper` — unless `--skip=docs`

Each agent gets the appropriate prompt (changed files for security/docs; diff range for commit/versioner). Reuse the prompt patterns from `/preflight`, `/bump`, `/docs`.

**This is the new architectural primitive of `/finish`**: 4-agent parallel dispatch. Same shape as `/preflight`'s 2-agent dispatch, scaled up.

### Phase 5: compute verdict

Same verdict rules as `/preflight`, plus new tiers for bump/docs (advisory only — they don't BLOCK):

| Verdict | When |
|---|---|
| **BLOCK** | tests failed OR typecheck failed OR `critical` security finding |
| **HOLD** | lint errors OR `high` security finding OR `high` docs finding |
| **SHIP** | everything else |

`docs-keeper` and `versioner` outputs are **advisory only** in v0.10 — they don't trigger BLOCK or HOLD, they appear in the report as recommendations. Reason: docs/bump being "missing" is the user's call, not a merge-blocker.

### Phase 6: write report + console summary

Write `.claude/kaizen/finish-report.md` (overwritten each run) with this structure:

```markdown
# kaizen :: finish report

Generated: <ISO 8601>
Plugin version: <v>
Base ref: <ref> (<auto-detected | --base override>)
Changed files: <count> source files
Flags: <list, or "none">
<if --auto-fix:>
Auto-fix applied: <N files modified>

---

## Verdict: <SHIP | HOLD | BLOCK>

<one-line reason>

| Counts |
|---|---|
| critical / high / medium / low (security) | ... |
| lint errors / warnings | ... |
| test failures, typecheck errors | ... |
| docs findings (high / medium / low) | ... |
| version bump recommended | <type or "none"> |

---

## Phase 1 — Deterministic checks

### Tests / Typecheck / Lint
(Same per-check format as /preflight)

---

## Phase 2 — LLM agents

### Security (preflight-security agent)
<verbatim output>

### Suggested commit message (commit-suggester agent)
<verbatim output>

### Suggested version bump (versioner agent)
<verbatim output>

### Documentation gaps (docs-keeper agent)
<verbatim output>

---

## End-of-task checklist

Based on the agents above, here is your suggested ritual to close this task:

1. <If lint errors>: Fix lint errors first.
2. <If security findings>: Address critical/high security findings.
3. <If docs gaps>: Update the flagged doc files.
4. <If bump recommended>: Apply the bump (manually or via `npx changeset` if changesets mode).
5. Stage and commit with:
   ```
   git commit -m "<commit-suggester's primary suggestion>"
   ```
6. Push and open PR.

(Each step is the user's call. /finish never executes any of them.)
```

### Console summary

```
╔══════════════════════════════════════════════╗
║  FINISH — <SHIP|HOLD|BLOCK>                  ║
║  <c>c · <h>h · <m>m · <l>l                   ║
╚══════════════════════════════════════════════╝

✓ Tests          (47 passed)
✓ Typecheck      (0 errors)
⚠ Lint           (2e, 5w)
✓ Security       (No findings)
ℹ Commit msg     (feat(api): add zod validation)
ℹ Version bump   (minor: 1.2.3 → 1.3.0)
⚠ Docs           (2 medium findings — README.md, docs/api.md)

Verdict: HOLD. Address lint errors and review doc updates.

Full report: .claude/kaizen/finish-report.md
  /kaizen:finish show   # re-print
  /kaizen:finish        # re-run after fixes
```

---

## Hard rules (never violate)

- **NEVER modify source code, manifests, or docs** without `--auto-fix` (and even then, only via configured formatters/linters — kaizen itself never edits).
- **NEVER auto-commit** even on SHIP. The user commits.
- **NEVER auto-apply a version bump.** That's `/kaizen:bump --apply` territory (v0.11).
- **NEVER auto-update docs.** That's manual.
- **NEVER spawn more than 4 agents.** All in one parallel batch.
- **Bump and docs findings are advisory only.** They surface in the report but don't gate the verdict (BLOCK/HOLD only triggered by security + deterministic checks).
- **All other hard rules from `/preflight` apply.**

---

## Failure modes

Same as `/preflight`, plus:

| Failure | Behavior |
|---|---|
| `versioner` fails (no manifest) | Mark bump section as `<unavailable>` in report. Don't affect verdict. |
| `docs-keeper` fails or returns no findings | Mark as `No documentation updates needed.` in report (the expected sentinel). |
| `--skip=tests,typecheck,lint,security,commit,bump,docs` (everything) | Refuse with `✗ --skip excluded every phase. Nothing to do.` |
| 4 agents fail | Report still written with all sections marked `<unavailable>`; verdict computed only from deterministic checks. |

---

## Why this design

Five deliberate choices specific to `/finish`:

1. **One ritual, one report.** Running `/preflight`, `/bump`, `/docs` separately is fine for focused work, but for "I'm closing this task" you want everything in one place. `/finish` is that single place.
2. **4-agent parallel dispatch.** First skill to scale the parallel-Task pattern to 4 agents (vs `/preflight`'s 2, `/plan`'s 2). Validates the pattern at larger fan-out. Cost is similar to running 4 single-agent skills sequentially; wall-clock is ~4× faster.
3. **Bump/docs are advisory.** Adding them to BLOCK/HOLD verdicts would create false negatives — sometimes you DON'T want to update docs in the same commit (e.g., for a refactor). Letting them be informational keeps the gate clean.
4. **Reuses agents, not skills.** /finish doesn't shell out to /preflight; it directly invokes the same plugin agents. Skills are coordination patterns; agents are the units of work.
5. **Read-only by default + same --auto-fix opt-in as /preflight.** The only mutation path is one explicit flag, and even then only formatters/linters do the work.
