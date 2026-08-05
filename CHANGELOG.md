# Changelog

All notable changes to kaizen are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), versioning follows [SemVer](https://semver.org/).

While v0.x, **minor versions may include breaking changes**. From v1.0.0 onward, semver applies strictly.

---

## [Unreleased]

### Added — configuration lock + `/kaizen:upgrade` (branch `next`)

The first phase of the direction proposed in [ROADMAP.md](./ROADMAP.md): kaizen
now records what it generates, so it can update a project later without
overwriting what the user changed.

- **`bin/kaizen-lock`** — deterministic bookkeeping. `write` hashes every
  generated file and snapshots it under `.claude/kaizen/baseline/`; `status`
  classifies each recorded file as `unchanged` / `modified` / `deleted`;
  `merge` runs a real 3-way merge through `git merge-file` and reports the
  conflict count without writing anything; `forget` untracks. All output is
  JSON — the model reads it and decides, it never hashes or merges by hand.
- **`.claude/kaizen/lock.json` + `baseline/`** — meant to be **committed**, like
  `package-lock.json`. The `.gitignore` template now ignores
  `.claude/kaizen/*` while negating both, and `kaizen-lock write` reports
  `lock_is_gitignored` so the skills can repair an older `.gitignore`.
- **`/kaizen:init` step 7** — records what it wrote. Additive: no existing
  behaviour changes, and a missing `kaizen-lock` degrades to a warning in the
  drift report rather than a failure.
- **`/kaizen:upgrade`** — new skill. Plans before it writes, merges instead of
  overwriting, never touches a file absent from the lock, never resurrects a
  deleted one, and never resolves a conflict on the user's behalf. This is what
  `--force` should have been.
- **`tests/suites/test_lock.py`** — 37 behavioural checks over real temp repos,
  including the two that matter: non-overlapping edits merge cleanly with the
  user's own rule intact, and same-line edits are reported as conflicts rather
  than silently merged away.
- Docs: [`docs/architecture.md` §17](./docs/architecture.md) and a
  "Configuration lock" section in the README.

### Added — validation harness

kaizen now has a test suite. Until now the plugin had no automated verification
of any kind: a renamed agent, an unregistered template placeholder or a version
bumped in one manifest but not the other shipped silently.

- **`tests/run.sh`** — 8 deterministic suites, 772 checks, ~0.5s, Python 3
  stdlib + bash only. Guards manifest/version agreement, skill and agent
  frontmatter contracts, agent dispatch references, **bidirectional
  placeholder/enrichment-directive registry integrity**, shell script health,
  hook-stub no-op invariants, and golden output for `kaizen-detect` across six
  fixture repos.
- **`tests/run.sh --live`** — opt-in behavioural evals. Runs real headless
  Claude Code sessions against throwaway fixture copies and asserts on what
  `/kaizen:init` actually wrote: no unsubstituted `{{PLACEHOLDER}}` or
  `KAIZEN_ENRICH:` marker leaked, hooks are executable, the profile shape is
  right, the boundary contract held, the drift report was printed. A session
  that cannot complete (quota, auth, network) exits **3 — inconclusive**, never
  1, so infrastructure failure is never read as a product regression.
- **`.github/workflows/tests.yml`** — the deterministic layer runs on every push
  and PR, with shellcheck installed. The live evals are deliberately excluded:
  they cost tokens.
- **Documentation** — [`docs/validation.md`](./docs/validation.md) (why it
  exists, what it can and cannot prove, where it sits in the release process)
  and [`tests/README.md`](./tests/README.md) (how to run it, how to add a
  fixture or a suite).

### Fixed
- **`README.md` announced v0.12.0 while the plugin shipped 0.12.1** — found by
  the `manifests` suite on its first run.

### Known gaps now surfaced on every run (as warnings, not failures)
- Six stacks (`go`, `rust`, `java`, `ruby`, `php`, `elixir`) are detected by
  `kaizen-detect` but fall back to the `generic` preset — detection promises
  more adaptation than the templates deliver.
- `{{HAS_CI}}` and `{{STACK_RAW}}` are documented in the placeholder registry
  but no template uses them.
- `detect_maturity` counts only source extensions, so a repo of prose and shell
  scripts reports `maturity: "empty"` — kaizen's own repo included. Encoded as a
  passing golden with a `_note` in the `docs-only` fixture.

### Planned (backlog tracked in BACKLOG.md + TODO.md)
- More hook implementations from `TODO.md "Hooks Implementation"`.
- MCP integrations from `TODO.md "MCP Integration"`.
- `/kaizen:bump --apply`.
- `/kaizen:ci` skill.
- v0.13 agent ecosystem expansion: `migration-planner`, `performance-analyst`, possibly `api-designer`.
- Other items in `BACKLOG.md`.

---

## [0.12.1] — 2026-05-20

### Fixed
- **`code-reviewer.md` brought up to v0.12 conventions** — was lingering with v0.1-era format:
  - `description` now starts with "Use when the user asks for a comprehensive code review..." (auto-invocation pattern). Previously read "Reviews code for correctness, security..." which Claude rarely matched against user input → auto-invocation in general conversation didn't fire reliably.
  - Added `<!-- kaizen-managed: true -->` marker. `/init --force` will now treat code-reviewer the same as the v0.12 ecosystem agents (overwrite if marker `true`, preserve if `false` or absent).
  - Description now explicitly differentiates from sister agents ("For NARROWER concerns use the specialized agents instead — security-auditor for security-only, refactor-helper for restructure proposals, test-writer for missing tests").

### Why this matters
Without this fix, the v0.12 agent ecosystem had 6 well-behaved agents + 1 legacy agent that didn't auto-invoke. Users would get inconsistent behavior — Claude correctly picked test-writer / security-auditor / etc. for narrow requests but failed to pick code-reviewer for broader "review this code" requests, often handling them inline instead.

### How it was caught
Deterministic test suite run post-v0.12 release (frontmatter + description pattern + marker validation across all 7 agents). The 6 new agents passed; code-reviewer was the only one that didn't.

---

## [0.12.0] — 2026-05-20

### The "Project Ecosystem" release

Major shift in what `/kaizen:init --profile=advanced` produces. v0.11 and earlier wrote a thin `.claude/` with only one project-level agent (`code-reviewer`). v0.12 ships a full **project-level agent ecosystem** so Claude has orchestration available whenever the user talks to it in their project — not just when invoking kaizen skills.

### Added — 6 project-level agents (advanced profile)

Written to `<project>/.claude/agents/` by `/kaizen:init --profile=advanced`. Auto-invoked by Claude based on `description` field matching. All are read-only except `test-writer`, `refactor-helper`, `documentation-writer` (which write code per their job).

| Agent | Use when | Tools |
|---|---|---|
| `test-writer` | User adds new functionality without tests, or asks to write tests | Read, Write, Edit, Glob, Grep, Bash |
| `refactor-helper` | User wants to restructure without changing behavior | Read, Write, Edit, Glob, Grep, Bash |
| `documentation-writer` | User asks to write/update docs (README, docstrings, CHANGELOG) | Read, Write, Edit, Glob, Grep, Bash |
| `dependency-auditor` | User asks about deps, outdated packages, vulnerabilities | Read, Glob, Grep, Bash |
| `security-auditor` | User wants broad security review (auth, payments, data handling) | Read, Grep, Glob, Bash |
| `architecture-advisor` | User asks design questions, "should I use X or Y" | Read, Grep, Glob |

**Distinct from plugin-level agents** (`preflight-security`, `commit-suggester`, `versioner`, etc.). Plugin agents serve kaizen skills with narrow scope and "Invoked by /X" descriptions. Project agents serve general conversation with "Use when X happens" descriptions optimized for Claude's auto-invocation.

### Added — 2 project-level hooks (advanced profile)

Written to `<project>/.claude/hooks/` by `--profile=advanced` and wired into `.claude/settings.json`:

| Hook | Event | Behavior |
|---|---|---|
| `secret-detector.sh` | `PreToolUse(Edit|Write)` | Scans intended file content for likely secrets (AWS keys, GitHub PATs, JWTs, private keys, credential-shaped assignments). **Exit 2 BLOCKS** the write with explanation. Same-line `noqa: secret` markers escape false positives. |
| `dependency-changed.sh` | `PostToolUse(Edit|Write)` | Self-filters to manifest files (package.json, pyproject.toml, Cargo.toml, etc.). When one changes, prints an informational suggestion to invoke `@dependency-auditor` or run audit commands. Does NOT run audit itself. |

### Added — KAIZEN_ENRICH directive registry expansion (9 new directives)

To support per-stack agent customization without duplicating templates:

- `test_writer_description`, `test_runner_conventions`, `project_test_patterns` (for `test-writer.md`)
- `refactor_safety_checks` (for `refactor-helper.md`)
- `doc_format_conventions`, `project_doc_locations` (for `documentation-writer.md`)
- `dep_manager_commands` (for `dependency-auditor.md`)
- `stack_security_concerns` (for `security-auditor.md`)
- `detected_architecture_patterns`, `project_principles` (for `architecture-advisor.md`)

Each agent template uses these markers; `/init` fills them per detected stack + project state.

### Added — `kaizen-managed` marker for drift management

Each `/init`-generated agent file contains as the first body line:

```html
<!-- kaizen-managed: true (re-init may overwrite — change to `false` or delete this line to claim ownership) -->
```

On `/kaizen:init --force`:
- If existing agent has `kaizen-managed: true` → overwrite (kaizen owns it).
- If `false` OR marker absent → preserve + log notice in drift report.

Lets users customize agents (set marker to false) without losing changes on re-init.

### Profile system clarification

The `advanced` profile is now **meaningfully different** from `standard`. Concrete differences:

| Profile | Files generated |
|---|---|
| `minimal` | Base only (CLAUDE.md, settings, 1 rule, code-reviewer, 3 hooks) |
| `standard` (default) | Minimal + workflow.md rule + Workflow section in CLAUDE.md |
| `advanced` | Standard + **6 new agents** + **2 new hooks** + kaizen-terse output style + workflow-advanced.md + Versioning + Output style sections in CLAUDE.md |

A fresh `/init --profile=advanced` now writes ~16 files (vs ~8 for minimal). Significant — document well in user-manual.

### Conceptual clarification

**Before v0.12** there was conceptual confusion: kaizen's plugin agents (preflight-security, versioner, etc.) are invoked BY kaizen skills, not by Claude in general conversation. Users with kaizen installed didn't get a broader agent ecosystem for their general work.

**v0.12 separates concerns**:
- Plugin agents = kaizen's internal workers (called by /preflight, /finish, /plan, etc.)
- Project agents = user's general-purpose ecosystem (auto-invoked by Claude as you work)

The two coexist without conflict — plugin agents have skill-tuned descriptions; project agents have auto-invocation-tuned descriptions.

### Notes
- Pure additive: existing `--profile=minimal`/`standard` outputs unchanged.
- `--profile=advanced` output IS bigger than before (6 more agents, 2 more hooks). Users running `/init --force` on existing advanced setups will see the new files written.
- The `kaizen-managed` marker is new but only matters on `--force` (no breaking change for non-force runs).
- v0.13 will likely add `migration-planner`, `performance-analyst`, and possibly `api-designer` to the ecosystem.

---

## [0.11.0] — 2026-05-20

### The "kaizen is now visible" release

Three additions that surface kaizen state in the UI, where v0.10 left it invisible until a skill was invoked.

### Added — Statusline

- **`templates/_shared/.claude/hooks/statusline.sh`** — single-line status shown at the bottom of Claude Code's TUI. Generated by `/kaizen:init` for all profiles (it's broadly useful, not workflow-specific).
- Shows: `[model] dir ⎇ branch  ✓/⚠/✗ verdict  ·  ⚠ learn pending  ·  📋 N plan(s)  ·  N modified`
- Reads kaizen state from `.claude/kaizen/finish-report.md`, `pending.md`, `plans/`, plus git state.
- Per-stack `settings.json` templates updated with `statusLine` declaration.
- Gracefully degrades if `jq` or `git` are absent.

### Added — Output style `kaizen-terse`

- **`templates/_shared/.claude/output-styles/kaizen-terse.md`** — output style appended to Claude's system prompt that enforces terse responses (no preambles, no narration, no padding summaries). Matches the kaizen workflow style.
- Written by `/kaizen:init --profile=advanced` only. Opt-in: user activates via `"outputStyle": "kaizen-terse"` in `.claude/settings.json` (or `/output-style` interactive).
- `keep-coding-instructions: true` — keeps the default software-engineering task instructions intact, only overlays the terseness rules.

### Added — Subagent statusline (plugin-level)

- **`plugins/kaizen/settings.json`** with `subagentStatusLine` declaration — visible during multi-agent dispatches (`/preflight`, `/plan`, `/finish`). Maps known kaizen agents to descriptive labels (e.g., `🔒 security review running…`, `📦 version bump running…`).
- **`plugins/kaizen/hooks/scripts/subagent-statusline.sh`** — the supporting script. Gracefully handles unknown agent names.
- The first plugin-level setting kaizen ships. Per Claude Code docs, plugin's `settings.json` only honors `agent` and `subagentStatusLine` keys — we use the latter.

### Changed
- `/init` SKILL.md base file list now includes `statusline.sh`. Drift report will mention it.
- `/init --profile=advanced` now writes 2 extra files (workflow-advanced.md + kaizen-terse.md) and appends 2 CLAUDE.md sections (output style + versioning).
- The 29 hook stubs from v0.10 are unchanged. Hook activation remains TODO per repo-root TODO.md.

### Notes
- Pure additive — without using the new features, kaizen v0.11 behaves like v0.10.
- The statusline reads project-local kaizen artifact files — if you've never run `/kaizen:finish` or `/learn`, the kaizen segment is empty and only `[model] dir ⎇ branch` shows.
- v0.12 will likely start implementing the hooks from TODO.md (highest priority: `Stop`, `PreToolUse`, `SessionStart` enrichment).

---

## [0.10.0] — 2026-05-19

### The "advanced workflow scaffold" release

This release expands kaizen from "5 ad-hoc skills" to a **coordinated development workflow system**. New skills cover documentation gaps and version bumping. A new orchestrator (`/kaizen:finish`) chains the full end-of-task ritual. `/kaizen:init` gains a profile system so users can choose how much workflow scaffolding to include.

### Added — 2 new plugin-level agents

- **`docs-keeper`**: analyzes a git diff and surfaces which user-facing documentation files (README, docs/) may need updating. Read-only. Categories: public API surface, CLI flags, configuration schema, behavioral changes, stale examples. Bias toward conservative; emits `"No documentation updates needed."` sentinel when clean.
- **`versioner`**: analyzes diff + commit messages + version manifest, suggests a semver bump (major/minor/patch) with per-commit justification. Detects changesets if `.changeset/` exists and produces draft changeset content. Supports `package.json` (JS/TS), `pyproject.toml` (Python, PEP 621 + Poetry), `Cargo.toml` (Rust).

### Added — 3 new skills

- **`/kaizen:docs`** — wraps `docs-keeper`. Auto-detects base ref (same logic as `/preflight`). Writes report to `.claude/kaizen/docs-report.md`. Subcommands: `show`. Flags: `--base`, `--since`, `--limit`.
- **`/kaizen:bump`** — wraps `versioner`. Auto-detects most recent git tag as base (fallback `HEAD~10`). Writes report to `.claude/kaizen/bump-report.md`. Suggestion-only in v0.10 (no `--apply` yet — that's v0.11).
- **`/kaizen:finish`** — end-of-task orchestrator. **First skill to spawn 4 agents in parallel** in a single message (`preflight-security` + `commit-suggester` + `versioner` + `docs-keeper`). Combines `/preflight`'s deterministic checks (tests/typecheck/lint) with all four LLM agents into a unified SHIP/HOLD/BLOCK verdict. Bump and docs findings are **advisory only** — they appear in the report but don't gate the verdict (the user calls those judgments).

### Added — `/kaizen:init` profile system

New flag `--profile=<minimal|standard|advanced>`:

- `minimal` — identical to v0.6 output. No workflow scaffolding. Use for throwaway projects.
- `standard` (default) — adds `.claude/rules/workflow.md` documenting all kaizen skills + workflow. Appends a "Workflow" section to `CLAUDE.md`. The new skills are **always available** when kaizen is installed; the profile only controls whether the project's CLAUDE.md surfaces them.
- `advanced` — standard + `.claude/rules/workflow-advanced.md` with the end-of-task ritual (recommend `/kaizen:finish` before every commit) + a stack-specific Versioning section in CLAUDE.md (changesets-aware for JS/TS with `.changeset/`, direct manifest bump otherwise).

Default is `standard` — new users get the workflow recommendations. `--profile=minimal` available for opt-out.

### Architectural notes

- **First 4-agent parallel dispatch**: `/finish` scales the parallel-Task pattern from 2 agents (`/preflight`, `/plan`) to 4. Validates the pattern at larger fan-out. Same single-message-multi-Task primitive.
- **Skills coordinate, agents do the work**: `/finish` doesn't shell out to `/preflight`/`/bump`/`/docs` as sub-skills — it directly invokes the same plugin agents. Skills are coordination layers; agents are reusable units of work.
- **Bump/docs are advisory, not gating**: keeping `BLOCK`/`HOLD` triggered only by security + deterministic checks. Doc/version judgments belong to the user.
- **`/kaizen:init` profile system is additive**: existing users on `minimal` (= v0.6 default) get the same files; new users get the workflow recommendations.

### Backlog moved to BACKLOG.md

A new top-level `BACKLOG.md` tracks deferred polish items with design context, acceptance criteria, and estimated effort. Three items: `/learn` `--include-session`, `/analyze` v0.10 modes, `/preflight` risk-aware + commit style auto-detection.

### Notes
- Pure additive — without using new flags/skills, v0.10 behaves like v0.9 for the existing 5-skill workflow.
- v0.11 will likely add: `/kaizen:bump --apply`, `/kaizen:ci` skill, branch-namer + PR generator (Phase 2 of the workflow initiative).

---

## [0.9.0] — 2026-05-19

### Added — `/kaizen:plan` input methods + TodoWrite integration

Closes the `/plan` polish backlog by removing the "must be a markdown file already" friction.

- **`--from-prompt="..."`** — inline prompt as the spec content. Useful for quick ad-hoc planning when writing a spec file is overkill. Skill slugifies the first ~40 chars for the plan filename.

- **`--from-issue=<N>`** — fetch a GitHub issue via `gh issue view <N>`. Body + comments form the spec content. Requires `gh` CLI installed and authenticated. If `gh` is missing or the issue can't be fetched, kaizen surfaces gh's error directly rather than pretending to succeed.

- **Auto-conversion of PDF/DOCX/ODT/RTF/EPUB/MOBI** — when `pdftotext` (from poppler) or `pandoc` is on PATH, kaizen converts transparently:
  - PDFs use `pdftotext -layout` (preserves text layout for spec extraction)
  - DOCX/ODT/RTF/EPUB/MOBI use `pandoc <input> -o <output>.md` (markdown output)
  - Converted files **persist** at `.claude/kaizen/converted/<basename>.txt` (or `.md`) so the user can inspect what kaizen actually extracted. Subsequent re-runs reuse the conversion.
  - `.claude/kaizen/` already gitignored — converted files don't pollute commits.
  - When no converter is installed, the error message now mentions auto-conversion as an alternative to manual conversion.

- **`--seed-todos`** — after writing the plan, also push each task into TodoWrite as a pending entry. Appends to (doesn't replace) any existing todos. Useful when you intend to start executing the plan in the current session. Use intentionally — TodoWrite is session-scoped, not project-scoped, so todos vanish when the session ends (the plan file persists).

### Changed
- Args table reorganized: exactly **one** input source must be specified (file path / `--from-prompt` / `--from-issue`). Multiple → error.
- Plan header now records the original spec source + auto-conversion provenance (e.g., `Spec source: docs/spec.pdf (auto-converted via pdftotext → .claude/kaizen/converted/spec.pdf.txt)`).
- Failure modes table expanded for new failure cases (gh missing, conversion fails, multiple inputs, empty `--from-prompt`, etc.).

### Notes
- Pure additive — without any new flags, v0.9 behaves exactly like v0.6/v0.8 for the existing file-path workflow.
- v0.10 still on the docket for `/plan`: `--scope` and `--depth` for granularity control. `--execute` further out (needs autonomy boundaries design).

---

## [0.8.0] — 2026-05-19

### Added — `/kaizen:preflight` flag suite

Three new flags, all opt-in, all combinable (e.g., `/kaizen:preflight --base=develop --skip=security --auto-fix`):

- **`--base=<ref>`** — Override the auto-detected base ref. Examples: `--base=develop` (git-flow projects), `--base=v1.0.0` (release-branch comparisons), `--base=HEAD~3`. When the user names a ref explicitly, kaizen does NOT silently fall back if it's invalid — it stops with a clear error.

- **`--skip=<checks>`** — Skip specific checks. CSV of: `tests`, `typecheck`, `lint`, `security`, `commit`. Example: `--skip=security,commit` runs only the deterministic trio (useful for quick iterative gates). Skipped checks appear in the report and never affect the verdict.

- **`--auto-fix`** — **Modifies source files**. Before running lint, attempts safe auto-fixes per stack: `eslint --fix` + `prettier --write` (JS/TS), `ruff check --fix` + `ruff format` (Python), `gofmt -w` (Go), `cargo fmt` (Rust). Opt-in only, never default. Warns if git tree is dirty (auto-fixes will mix with WIP). Lint then reports only what auto-fix couldn't resolve. Files modified are listed in the report header.

### Changed
- The `## Hard rules` section of preflight's SKILL.md now reads "NEVER modify source code UNLESS `--auto-fix` was passed" — the read-only contract is now conditionally relaxed only when the user explicitly opts in.
- The report header gained two new lines: `Flags: <list>` and (when `--auto-fix` was used) `Auto-fix applied: <N files>`.
- Failure modes expanded: invalid `--base` stops with error (no silent fallback); unknown `--skip=<x>` target is warned and ignored; `--skip` excluding all checks is rejected.

### Notes
- Pure additive. Without any of the new flags, v0.8.0 behaves exactly like v0.7.0/v0.5.0 — no breaking changes.
- Risk-aware sizing and commit-style auto-detection (also planned for /preflight) remain deferred to v0.9. Both need more design work to avoid false negatives or misdetection.

---

## [0.7.0] — 2026-05-19

### Improved — `/kaizen:learn` UX (addresses user feedback from real usage)

- **Range visibility is now prominent** — the analyzed git range (`<base>..HEAD` + commit count) is shown at the top of both the console summary and the `pending.md` header. No more "wait, what commits did this look at?". The `pending.md` header now also includes oldest/newest commit SHAs and subjects for unambiguous context.
- **New `--limit=<N>` flag** — analyze the last N commits explicitly. Equivalent to `--since=HEAD~<N>` but more intuitive for the common case of "just look at the last N". Both flags can coexist; `--since` wins if both given (noted in report).
- **"When to run" guidance** — new section in SKILL.md and user-manual that explicitly disambiguates `/learn` from `/init` and other skills. Recommended cadence (end of sprint / feature branch / multi-day chunk — not after every Claude response). Addresses a user-observed ambiguity in v0.3-v0.6.
- **Honest signal source labeling** — `pending.md` header now says `Signal sources used: git only (v0.7 — opt-in --include-session planned for v0.8)`. Sets expectations.

### Acknowledged but deferred
- `--include-session` flag remains v0.8. It needs design work on **how** the skill accesses prior conversation in Claude Code (not a trivial tool call). v0.7 documents the limitation rather than ships a half-baked version.

### Notes
- Pure additive changes to `/kaizen:learn`. No breaking changes. Old `--since=<ref>` continues to work; `--limit` is a new alternative.
- The user feedback that drove this release came from `NOTES.md` in the kaizen repo (now gitignored) — captured into memory and resolved in this version. Demonstrates the "observed-in-use → atendido" loop.

---

## [0.6.0] — 2026-05-19

### Added
- **New skill `/kaizen:plan`**: auto-planner that turns a written specification into a structured, dependency-ordered task tree.
  - **Input**: any text-format spec file (markdown, txt, rst, adoc, plain). Binary formats (PDF, DOCX, ODT, RTF) detected by extension and rejected with explicit conversion suggestion (`pdftotext` / `pandoc`).
  - **4-phase execution**: validate → setup signals → **parallel agents** → synthesis → write.
  - **2 new plugin-level agents** (parallel via single-message dual-Task dispatch, mirroring `/preflight`):
    - `plan-context` — reads project state (CLAUDE.md, rules, `src/*/`, package.json) and produces a project profile (stack, architecture, conventions, key areas, libraries).
    - `plan-decomposer` — reads ONLY the spec and produces a raw task list with type/complexity/acceptance criteria. Doesn't touch project state.
  - **Synthesis in the orchestrator (no third agent)**: cross-references each task with the project context to add impact areas, dependencies, and risks. Reorders tasks by dependencies (foundational first). Caps at 20 tasks.
  - **Output**: `.claude/kaizen/plans/<slug>-<YYYYMMDD-HHMM>.md`. Plans **accumulate** (versioned by timestamp) unlike `/learn`'s `pending.md` or `/analyze`'s `analyze-report.md` (which overwrite).
  - **Subcommands**: `list` (show all plans), `show <plan-id>` (print specific plan; `latest` resolves to most recent).
  - **Read-only contract**: no source modifications, no auto-execution. The plan is the artifact.

### Architectural note
- v0.6.0 closes the planned skill set for kaizen v0.x. After this, focus shifts to UX polish, signal-source expansion (`/learn` v0.7), and additional analyze modes (`/analyze` v0.7) rather than new top-level skills.
- The parallel-Task pattern is now used by both `/preflight` (v0.5.0) and `/plan` (v0.6.0). Both follow the same shape: parallel research agents + skill-level synthesis. `/plan` adds the "plans accumulate" pattern (vs. single-file overwrite).
- v0.7+ may add `--execute` as a separate concern (autonomy boundaries, checkpointing) — premature in v0.6.

---

## [0.5.0] — 2026-05-18

### Added
- **New skill `/kaizen:preflight`**: pre-merge gate combining deterministic checks (tests, typecheck, lint) with LLM-driven reasoning (security review, commit suggestion). Produces a single **SHIP / HOLD / BLOCK** verdict.
  - **Phase 1 (sequential, Bash tool)**: runs `<pm> test` / `tsc --noEmit` / `eslint .` (or Python/Go/Rust equivalents auto-detected). Captures exit codes and bounded output.
  - **Phase 2 (parallel, Task tool)**: dispatches `preflight-security` and `commit-suggester` agents simultaneously in a single message — ~2× faster than sequential.
  - **Phase 3**: aggregates everything into `.claude/kaizen/preflight-report.md` (overwritten each run) + prints console banner with verdict.
  - **Base ref auto-detection**: `HEAD~1` on main/master, else `main` (or `master`), with fallback. Changed-files list scoped to source extensions for the security agent.
  - **Verdict tiers**: BLOCK = tests fail / typecheck fail / critical security; HOLD = lint errors / high security; SHIP = everything else.
  - `show` subcommand re-prints last report without re-running.

### Added — new plugin-level agents
- **`preflight-security`**: read-only security auditor scoped to the changed files only. Categories: hardcoded secrets, injection, auth gaps, unsafe deserialization, path traversal, weak crypto, CORS/CSRF, secret leakage in logs. Severity tiered. Returns "No security findings." sentinel when clean.
- **`commit-suggester`**: produces Conventional Commits messages from a diff. Returns primary + 2 alternatives + optional body. Handles mixed-type diffs by priority order. Style auto-detection deferred to v0.6.

### Design notes
- **Hybrid execution model**: deterministic checks via Bash are cheap and predictable; LLM agents are reserved for reasoning. No agents for `npm test` — that's just a process invocation.
- **Parallel agent dispatch**: both agents spawned in a single message via two `Task` tool calls. Fresh contexts each, no bloat in the main session.
- **Independent of `/init`'s `code-reviewer`**: `preflight-security` is plugin-level and narrowly scoped to diffs; user's `code-reviewer.md` (if `/init` was run) stays for manual general-purpose review. Two agents, two jobs, no overlap.
- **Conventional Commits as default**: integrates with semver bots and changelog generators. Other styles (gitmoji, plain, custom) supported in v0.6 via auto-detection from `git log`.
- **Read-only by hard rule**: writes only `.claude/kaizen/preflight-report.md` and (one-time) `.gitignore`. Never touches source, never commits.
- v0.5 scope explicitly excludes: `--base` / `--skip` / `--auto-fix` flags, format check, coverage check, risk-aware sizing. All in v0.6 backlog.

---

## [0.4.0] — 2026-05-18

### Added
- **New skill `/kaizen:analyze`**: read-only audit of the current project against its own `CLAUDE.md` and `.claude/rules/*`. Three modes (combinable):
  - `--best-practices` — checks code for violations of stated conventions. Uses a built-in pattern library (10 known patterns covering JS/TS/Python common rules). Unmatched conventions are listed under "Unchecked" so users know what isn't verified.
  - `--coverage` — identifies directories not covered by any path-scoped rule. Also flags stale rules whose `paths:` glob matches zero files.
  - `--architecture` — compares the `## Architecture` section of `CLAUDE.md` to actual `src/*/`. Optionally checks Stack section against `package.json` dependencies for drift.
- No-flag invocation runs all three modes.
- `show` subcommand re-prints the last report.
- Report written to `.claude/kaizen/analyze-report.md` (overwritten each run; gitignored).
- **Documentation**: full coverage in `docs/architecture.md` (section 11), `docs/runtime-flow.md` (section 11), `docs/user-manual.md`. Per the docs-completeness commitment.

### Design notes
- **`/analyze` is independent of `/learn`**: produces only a report, never proposes mutations. The two skills are mirror images: `/learn` looks at git → proposes config; `/analyze` looks at current code → reports issues.
- **Read-only by hard rule**: no Edit/Write to any file except `.claude/kaizen/analyze-report.md` and (one-time) `.gitignore`.
- Modes not in v0.4 scope (deferred to v0.5+): `--dependencies`, `--security`, `--complexity`, `--upgrade <pkg>`.

---

## [0.3.0] — 2026-05-18

### Added
- **New skill `/kaizen:learn`**: analyzes recent git activity and proposes updates to `CLAUDE.md` / `.claude/rules/`. Subcommands: `show`, `apply`, `discard`. Never modifies config silently — all proposals live in `.claude/kaizen/pending.md` for user review.
  - State machine prevents proposal accumulation (refuses new analysis while pending exist).
  - Max 3 proposals per analysis, each with explicit evidence (commit SHAs + file paths).
  - `--since=<git-ref>` flag for custom commit range (default `HEAD~10`).
  - `.claude/kaizen/` auto-added to `.gitignore` first time skill runs.
- **Documentation**: full coverage in `docs/architecture.md` (section 9), `docs/runtime-flow.md` (section 10), `docs/user-manual.md`. Mermaid diagrams for state machine, sequence (analyze + apply), decision tree, validate-then-mutate flowchart.
- **Documented v0.4/v0.5 roadmap** for `/learn` signal sources (session conversation, auto-memory) with tradeoffs and anti-circularity considerations.

### Notes
- `/learn` v0.3 uses **git as the only signal source**. Other sources (session, auto-memory) are opt-in flags planned for later minors.

---

## [0.2.1] — 2026-05-17

### Fixed
- **#1** — Drift report no longer includes inaccurate substitution counts (`×N`). Lists placeholder names only. Inaccurate counts were undermining the credibility of the whole report.
- **#2** — `architecture_layout` directive lookup table extended with: `css`, `styles`, `public`, `static`, `scripts`, `config`, `docs`, `test`. Quasar projects no longer show `src/css/ — (purpose: TBD)`.
- **#4** — New conditional rule `test_script_but_no_runner`: when `package.json` has a `test` script but no actual runner installed (vitest/jest/etc.), kaizen inserts an explanatory note in `CLAUDE.md` under Commands.

### Added
- **#3** — Mandatory "Suggestions" section in drift report, with per-file checks. For each verbatim file, kaizen evaluates whether the detected stack would benefit from stack-specific additions and surfaces them as actionable suggestions (e.g., "format-on-save.sh does not include `.vue`/`.scss` — your Quasar project uses both"). Replaces the v0.1.x pattern where Claude silently added them.

---

## [0.2.0] — 2026-05-17

### Changed (BREAKING for template format)
- **Hybrid templates**: introduced `<!-- KAIZEN_ENRICH:<id> -->` markers. Templates now have:
  - **Rigid sections** — verbatim after placeholder substitution (Commands, Conventions, Never do).
  - **Flexible sections** — Claude fills enrichment markers per directive registry (Stack, Architecture).
- **`{{STACK}}` → `{{STACK_FRIENDLY}}` + `{{STACK_RAW}}`**: split the ambiguous single placeholder into two with clear semantics. `STACK_RAW` is the literal CSV from `kaizen-detect`; `STACK_FRIENDLY` is a Claude-derived human-readable name.
- **Conditional removals** are now formalized with rule ids (`no_test_script`, `no_typecheck`, `no_build`, `no_package_manager`, `dev_script_present`). Each is logged in the drift report.
- **SKILL.md hard rule**: "NEVER modify template content outside markers and conditional rules." Suggestions for improvements outside this scope go to a separate Suggestions section in the report (not auto-applied).

### Added
- **Drift report** at the end of every `/kaizen:init` run. Per-file list of substitutions, enrichments (by directive id), conditional removals (by rule id), with explicit "(no customizations — written verbatim)" for files untouched. Solves the v0.1 problem of "Claude rewrote CLAUDE.md and I can't tell what came from where."
- **Suggestions section** in the report: things Claude noticed but didn't auto-apply (e.g., Vue Test Utils for testing.md, `.vue`/`.scss` for format-on-save.sh).
- **Plugin version in header**: generated CLAUDE.md shows `Generated by kaizen v0.2.0` in the `✓ kaizen init complete` banner.

---

## [0.1.3] — 2026-05-17

### Fixed
- `permissions.defaultMode` value `"ask"` is invalid in Claude Code (silently rejected the entire settings.json). Changed to `"default"` across all stack templates (`generic`, `typescript-node`, `python`). Without this fix, the generated `.claude/settings.json` is skipped wholesale at session start.

### Notes
- Discovery cost: cost the user an entire session iteration. Documented in memory as "Settings.json fails silently on schema mismatch."

---

## [0.1.2] — 2026-05-17

### Changed
- **`/kaizen:init` no longer uses bash injection** (`` !`...` `` lines) for `kaizen-detect`. Instead, SKILL.md instructs Claude to invoke the Bash tool with the bare command name.
- **Why**: bash injections in skills do NOT inherit the plugin's `bin/` PATH in Claude Code v2.1.45, despite the docs claiming `bin/` is added to the Bash tool's PATH while the plugin is enabled. They run in a subshell with the parent shell's PATH only. The Bash tool's runtime environment DOES include the plugin `bin/`, so calling from Claude's reasoning loop works.

### Added
- Manual detection fallback in SKILL.md: if `kaizen-detect` isn't on PATH, Claude can gather equivalent facts using `Read`/`Glob`/`Bash(git *)`. Slower but always works.

---

## [0.1.1] — 2026-05-17

### Added
- `allowed-tools` frontmatter in SKILL.md: pre-authorizes the bash commands the skill needs. Without this, every `/kaizen:init` invocation prompted the user to approve each helper command.
- Bumped to force the local marketplace cache to refresh (Claude Code's marketplace cache is sticky for local paths).

### Changed
- Moved `skills/init/scripts/detect.sh` → `bin/kaizen-detect`. The intent was to make it available via plugin `bin/` PATH; the actual fix came in v0.1.2 (see above).

---

## [0.1.0] — 2026-05-16

### Added
- **Initial release** of kaizen as a Claude Code plugin distributable via marketplace.
- **`/kaizen:init`**: bootstrap a project's Claude Code configuration. Detects stack, package manager, maturity, git state, existing config. Generates `CLAUDE.md`, `.claude/settings.json`, path-scoped rules, code-reviewer agent, hooks. Works on empty and existing projects.
- **Detection script `bin/kaizen-detect`** (originally `skills/init/scripts/detect.sh`): deterministic bash fingerprint of the project, emits JSON with stack/PM/maturity/git/tests/CI.
- **Stack templates**: `_shared`, `generic`, `typescript-node`, `python`.
- **Maturity-aware logic**: `empty` (ask user), `scaffold` (warn early), `small` (full scaffold), `mature` (full + offer archeology subagent).
- **Existing-config guard**: refuses to overwrite without `--force`; offers abort/force/merge-only choice interactively.
- **`--minimal` flag**: only generates `CLAUDE.md` + `.claude/settings.json` + `.gitignore` patch.
- Local marketplace structure (`.claude-plugin/marketplace.json` at repo root, plugin at `plugins/kaizen/`).

### Known issues at release (all resolved in later versions)
- `$schema` and `engines` in `plugin.json` — rejected at install (fixed pre-0.1.0 final by removal).
- `defaultMode: "ask"` in generated `settings.json` — invalid value, fixed in 0.1.3.
- Bash injection with `${CLAUDE_SKILL_DIR}` — rejected by permission check (fixed in 0.1.1+ by moving to `bin/`, then 0.1.2 by avoiding injection entirely).

---

## Versioning policy (while v0.x)

| Version bump | When |
|---|---|
| **Patch** (`0.x.Y`) | Bug fixes, doc updates, template tweaks that don't change behavior |
| **Minor** (`0.X.0`) | New skills, new directives, new conditional rules. **May include breaking changes** in template format or skill contract. |
| **Major** (`X.0.0`) | Reserved for v1.0.0+. Will switch to strict semver. |

Users should always read the changelog entry for the version they're upgrading to.
