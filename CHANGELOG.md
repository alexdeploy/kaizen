# Changelog

All notable changes to kaizen are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), versioning follows [SemVer](https://semver.org/).

While v0.x, **minor versions may include breaking changes**. From v1.0.0 onward, semver applies strictly.

---

## [Unreleased]

### Planned
- `/kaizen:plan` — turn spec doc into structured task tree (auto-planificador).
- `/kaizen:preflight` v0.6 — `--base=<ref>`, `--skip=<checks>`, `--auto-fix` flags; risk-aware sizing; commit style auto-detection.
- `/kaizen:analyze` v0.6 — additional modes: `--dependencies` (npm outdated, audit), `--security`, `--complexity`.
- `/kaizen:learn` v0.6 — `--include-session` flag (analyze current Claude Code session for user corrections).

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
