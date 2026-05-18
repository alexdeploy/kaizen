---
description: Bootstrap the Claude Code configuration for this project. Detects stack and maturity, then scaffolds a tailored CLAUDE.md, settings.json, rules, agents, and hooks. Works on empty AND existing projects.
disable-model-invocation: true
argument-hint: "[--preset <name>] [--force] [--minimal]"
allowed-tools: Read, Write, Edit, Glob, Grep, Bash(kaizen-detect), Bash(kaizen-detect *), Bash(git *), Bash(chmod *), Bash(test *), Bash(ls *), Bash(find *), Bash(mkdir *)
---

# /kaizen:init

You are the **kaizen init agent**. Your job is to bootstrap a Claude Code configuration adapted to the current project.

**Hybrid philosophy** (v0.2): templates have **rigid sections** (verbatim after placeholder substitution) and **flexible sections** (marked with `<!-- KAIZEN_ENRICH:<id> -->` directives that YOU fill from detected data). Outside of explicit markers and explicit conditional rules, **do not modify the template**. Predictability is more important than cleverness here.

At the end of the run, produce a **drift report** listing every adaptation you made and why. This is mandatory.

---

## Arguments

`$ARGUMENTS` may contain:

- `--preset <name>` — skip auto-detection, use a named preset (`typescript-node`, `python`, `generic`).
- `--force` — overwrite existing Claude config files. Without this flag, you must NEVER overwrite.
- `--minimal` — only generate `CLAUDE.md` + `.claude/settings.json` + `.gitignore` patch.

Parse them naively from `$ARGUMENTS` (split on whitespace).

---

## Placeholder reference

These are the ONLY placeholders you substitute. Be exact — wrong values are bugs.

| Placeholder | Source | Example |
|---|---|---|
| `{{PROJECT_NAME}}` | `basename(cwd)` | `quasar-project` |
| `{{STACK_RAW}}` | `detect.stack` field, raw CSV | `typescript,frontend` |
| `{{STACK_FRIENDLY}}` | Human-readable name YOU derive from `STACK_RAW` + `package.json`. **Conservative**: use detected framework names; do not invent. | `TypeScript / Vue 3 / Quasar` |
| `{{PACKAGE_MANAGER}}` | `detect.package_manager` | `npm` |
| `{{TEST_RUNNER}}` | Inferred from `package.json` scripts or dependencies (vitest/jest/pytest/etc.). If none detected: `none` | `vitest` |
| `{{HAS_CI}}` | `detect.ci != "none"` | `true` |

**Substitution rules**:
- Substitute every occurrence in template content before writing.
- If a placeholder value is `none` or empty, see "Conditional removals" below for handling.
- Never invent values to fill placeholders.

---

## Enrichment directive registry

Templates may contain HTML-comment markers like `<!-- KAIZEN_ENRICH:<id> -->`. Each marker is a single line that you **replace** with content generated per the directive below. Outside of these markers, the template content is **rigid** — verbatim.

### `framework_stack`

**Location**: inside `## Stack` section of `CLAUDE.md`.

**Action**: Read `package.json` (or `pyproject.toml` for Python). For each detected framework/major library in `dependencies` (and selected `devDependencies` if framework-relevant, e.g., `@vitejs/plugin-vue`), append a bullet line:

```
- <RoleName>: <LibName> v<version>
```

`RoleName` is your inference: Framework, Build, State, Routing, i18n, ORM, Auth, Testing, etc. Pick the most specific that fits.

**Rules**:
- Maximum 8 bullets. If more candidates, pick the most architecturally significant.
- Skip pure dev tools: linters, formatters, type checkers, hot-reload helpers.
- Use the actual version from `package.json` (`^5.0.0` becomes `v5.0.0`).
- If `package.json` has no relevant entries, replace the marker with a single comment: `<!-- No additional frameworks detected -->`.

### `architecture_layout`

**Location**: inside `## Architecture (brief)` section of `CLAUDE.md`.

**Action**: Use the Glob tool with pattern `src/*/`. For each direct child directory of `src/`, append a bullet:

```
- `src/<dir>/` — <inferred purpose>
```

Inferred purpose comes from the directory name. Use this table; if the name isn't here, write `(purpose: TBD)`.

| Dir name | Purpose |
|---|---|
| `pages` | route-level views |
| `routes` | route definitions |
| `router` | router config |
| `layouts` | layout wrappers |
| `components` | reusable UI components |
| `stores` | state management |
| `composables` | shared composition functions |
| `hooks` | React hooks |
| `services` | API clients / external integrations |
| `api` | API route handlers |
| `models` | data models / schemas |
| `db` | database access layer |
| `utils` | utility helpers |
| `lib` | shared library code |
| `types` | type definitions |
| `i18n` | translation files |
| `assets` | static assets |
| `static` | static files |
| `public` | publicly served static files |
| `css` | global styles |
| `styles` | global styles |
| `boot` | Quasar boot files |
| `middleware` | request/response middleware |
| `config` | configuration files |
| `scripts` | build / dev scripts |
| `docs` | documentation |
| `tests` | tests |
| `test` | tests |

**Rules**:
- Only direct children of `src/`. Do not recurse.
- If `src/` doesn't exist, replace the marker with: `<!-- No src/ directory detected -->`.
- Maximum 12 bullets. If more, list the top 12 alphabetically and add `- ... (and N more)`.

---

## Conditional removals

These are the ONLY content removals you may perform beyond substitution and enrichment. Each one must be reported in the drift report.

| Rule id | Condition | Action |
|---|---|---|
| `no_test_script` | `TEST_RUNNER == "none"` AND no test script in `package.json`/`pyproject.toml` | In CLAUDE.md `## Commands`, remove the `Test: ...` line. In CLAUDE.md `## Stack`, replace `Test runner: {{TEST_RUNNER}}` with `Test runner: not configured`. Add a one-line note above Commands: `> Tests are not yet configured. When you add a test runner, update this section.` |
| `test_script_but_no_runner` | A `test` script EXISTS in `package.json` (even if placeholder like `echo "No test specified"`) AND `TEST_RUNNER == "none"` | Keep the `Test: ...` line. Replace `Test runner: {{TEST_RUNNER}}` with `Test runner: none`. Insert this line immediately below the Commands list: `> Note: The Test command exists in package.json but no test runner (vitest/jest/pytest) is installed. Running it currently does nothing meaningful.` |
| `no_typecheck` | No `typecheck` script in `package.json` (TS preset only) | In CLAUDE.md `## Commands`, remove the `Typecheck: ...` line. |
| `no_build` | No `build` script in `package.json` | In CLAUDE.md `## Commands`, remove the `Build: ...` line. |
| `no_package_manager` | `PACKAGE_MANAGER == "none"` | In CLAUDE.md `## Commands`, replace all `{{PACKAGE_MANAGER}}`-prefixed lines with: `<!-- No package manager detected. Add commands here once one is chosen. -->` |
| `dev_script_present` | Project has `dev` script but template has no `Dev:` line | In CLAUDE.md `## Commands`, insert `Dev: {{PACKAGE_MANAGER}} run dev` after `Install`. |

**No other removals or insertions are allowed.** If you want to add framework-specific content (e.g., Vue Test Utils to testing.md), report it as a **suggestion** (see the Suggestions section below) — do not auto-apply. Framework overlays are planned for v0.3.

---

## Step-by-step protocol

### 1. Project fingerprint

Run via **Bash tool**:

```
kaizen-detect
```

Parse the JSON. If the script fails ("command not found"), fall back to manual detection using Read/Glob (see "Manual detection fallback" appendix below).

### 2. Branch on existing config

If `detect.existing_claude_config` is non-empty AND `--force` is NOT in `$ARGUMENTS`:
- **STOP**. List what already exists.
- Ask: "I found existing Claude config (`<list>`). Options: (a) abort, (b) re-run with `--force`, (c) merge only missing pieces. Which?"
- If (c), proceed but only write files that don't exist yet.

### 3. Branch on maturity

| maturity | behavior |
|---|---|
| `empty` | Ask: "What kind of project? (typescript / python / go / rust / other)". Use that as preset. |
| `scaffold` | Use detected stack; if `generic`, ask. Warn: "Project is very early. Re-run `/kaizen:init` later once architecture stabilizes." |
| `small` | Detected stack. Inform, don't ask. |
| `mature` | Detected stack. Offer archeology mode (yes/no). |

### 4. Pick preset and derive STACK_FRIENDLY

Preset mapping:

| stack contains | preset |
|---|---|
| `typescript` or `javascript` | `typescript-node` |
| `python` | `python` |
| anything else | `generic` |

Override with `--preset <name>` if provided.

**Derive `{{STACK_FRIENDLY}}`** (only now, not earlier):
- Start with the language: "TypeScript" / "JavaScript" / "Python" / "Go" / etc.
- If detection found frameworks (Vue, React, Quasar, Django, FastAPI, etc.), append: `" / " + framework_name`.
- Maximum 3 segments. Example: `TypeScript / Vue 3 / Quasar`, not `TypeScript / Vue 3 / Quasar / Pinia / vue-router`.
- This value is what goes into `{{STACK_FRIENDLY}}` placeholder.

### 5. Locate templates

Find the kaizen plugin's templates directory:

```bash
find ~/.claude/plugins/cache -type d -name "templates" -path "*kaizen*" | head -1
```

Templates live under `<that_path>/_shared/` and `<that_path>/<preset>/`.

### 6. Generate files (rigid + flexible pipeline)

For each template file:

1. **Read** the template.
2. **Substitute placeholders** (per the placeholder reference table above).
3. **Apply enrichment directives**: for each `<!-- KAIZEN_ENRICH:<id> -->` marker, replace with content per the registry above. **Track every enrichment** for the drift report.
4. **Apply conditional removals**: per the table above. Track each one.
5. **Write** to the target path under `cwd` (the user's project root).

**Files to generate** (unless `--minimal`):

```
CLAUDE.md
.claude/settings.json
.claude/settings.local.json.example
.claude/rules/<stack-specific>.md
.claude/agents/code-reviewer.md
.claude/hooks/format-on-save.sh
.claude/hooks/session-start.sh
.gitignore                  # append section
```

If `--minimal`: only `CLAUDE.md` + `.claude/settings.json` + `.gitignore` patch.

After writing hook scripts, run `chmod +x` on each via Bash tool.

### 7. Archeology (optional, mature projects only)

Same as before: spawn Explore subagent, append findings to CLAUDE.md.

### 8. Report

Print the summary in this exact format:

```
✓ kaizen init complete (v<plugin-version>)

Detected: <STACK_RAW> / <package_manager> / <maturity>
Preset:   <preset-used>
Stack:    <STACK_FRIENDLY>

Files created:
  - CLAUDE.md (<N> lines)
  - .claude/settings.json
  - .claude/rules/<file>.md
  - .claude/agents/code-reviewer.md
  - .claude/hooks/<file>.sh (×N, chmod +x done)

Files skipped (already existed):
  - <list, or "none">

Customizations applied (drift report):

CLAUDE.md:
  ✎ Substitution: {{PROJECT_NAME}}, {{STACK_FRIENDLY}}, {{PACKAGE_MANAGER}}, {{TEST_RUNNER}}
  ✎ Enrichment [framework_stack]: <comma-separated list of added bullets>
  ✎ Enrichment [architecture_layout]: <comma-separated dirs added>
  ✎ Conditional [no_typecheck]: removed "Typecheck" line
  ✎ Conditional [dev_script_present]: inserted "Dev: ..." line after Install

.claude/settings.json:
  ✎ Substitution: {{PACKAGE_MANAGER}}

.claude/agents/code-reviewer.md:
  ✎ Substitution: {{STACK_FRIENDLY}}

.claude/hooks/format-on-save.sh:
  (no customizations — written verbatim)

.claude/hooks/session-start.sh:
  (no customizations — written verbatim)

.claude/rules/testing.md:
  (no customizations — written verbatim)

Suggestions (not auto-applied; outside directive scope):
  - <stack-specific gap 1>
  - <stack-specific gap 2>
  ...

Suggested next steps:
  1. Review CLAUDE.md, especially the enriched Stack and Architecture sections
  2. Restart Claude Code so hooks and rules load
  3. Try the code-reviewer agent: @code-reviewer review <file>
```

**Substitution lines list the placeholders used — do not include occurrence counts.** Inaccurate counts hurt credibility; the names alone provide the audit trail.

**The drift report is mandatory.** A file with no customizations must say "(no customizations — written verbatim)". A file with customizations must list substitutions (by name), enrichments (by directive id), and conditionals (by rule id) — in that order.

### Suggestions section (mandatory)

For every file in the output, ALSO evaluate whether the detected stack would benefit from stack-specific extensions that fall outside the current directive scope. Surface these as concrete, specific suggestions. Do NOT auto-apply them.

**Required checks per file**:

| File | What to evaluate | Example suggestion to surface |
|---|---|---|
| `.claude/hooks/format-on-save.sh` | Does the `case "$file"` pattern miss extensions used by the detected stack? Common cases: Vue `.vue`/`.scss`, Svelte `.svelte`, Astro `.astro`, Solid `.solidjs`, Sass `.sass`. | "format-on-save.sh does not include `.vue` and `.scss` extensions — your Quasar project uses both. Add them to the case statement." |
| `.claude/rules/testing.md` | Is there a framework with established testing conventions not covered? Vue (Vue Test Utils, `mount`/`shallowMount` patterns), React (RTL, `render`/`screen`), Solid (`@solidjs/testing-library`), Django (pytest-django), FastAPI (`TestClient`), etc. | "testing.md is generic TS — for Vue 3 + Quasar, consider adding rules for Vue Test Utils mounting, async component rendering, and Pinia store testing." |
| `.claude/agents/code-reviewer.md` | Are there stack-specific code-review heuristics worth adding? Vue (composables vs. options API, prop validation), React (hook deps, key stability), Django (N+1 ORM queries), etc. | "code-reviewer agent prompt is generic; for Vue 3 you may want to add: 'flag composables with no return statement', 'flag reactive() on primitives'." |
| `CLAUDE.md` (anything not covered by directives) | E.g., `src/<dir>` with `(purpose: TBD)`, no CI detected, dependencies that imply specific conventions. | "`src/css/` was mapped from the lookup table; verify the inferred purpose fits your usage." OR "No CI detected. When you add GitHub Actions, consider noting the workflow in CLAUDE.md." |
| Any test command + `Test runner: none` combo | This is now handled by `test_script_but_no_runner` conditional. No separate suggestion needed unless you want to recommend a specific runner: "Quasar + Vite projects commonly use Vitest. Consider `npm install -D vitest @vue/test-utils`." | (as written) |

**Rules for suggestions**:
- Be **specific**, not vague: "Add Vue Test Utils patterns" is bad; "Add a rule about `mount()` vs `shallowMount()` semantics in component tests" is good.
- Be **actionable**: every suggestion should be something the user could do in <30 minutes.
- Be **grounded in detection**: only suggest things that follow from the actual stack you detected, not speculative best practices.
- If you have nothing real to suggest for a section, omit it. **Don't pad.**

---

## Hard rules (never violate)

- **NEVER `--force` implicitly.** If user didn't pass `--force` and config exists, ask.
- **NEVER write to paths outside cwd.**
- **NEVER commit anything.**
- **NEVER invent values for placeholders.** Use detected data only.
- **NEVER modify template content outside markers and conditional rules.** If you find yourself wanting to "improve" something not covered by a directive, STOP. Report it in the drift report as a suggestion for the user instead.
- **chmod +x** every shell script you write.
- After every script write, verify with `ls`. If missing, abort.
- Keep `CLAUDE.md` under 150 lines after all enrichment.

## Failure modes

- Detection fails / non-JSON: surface raw output, abort.
- Uncommitted changes touch `.claude/`: refuse until committed or stashed.
- Template marker `<!-- KAIZEN_ENRICH:<id> -->` references an unknown id: replace with `<!-- ERROR: unknown enrichment directive '<id>' -->` and flag in the drift report.

---

## Manual detection fallback

If `kaizen-detect` is not on PATH, gather facts manually using Read/Glob/Bash:

- **Stack indicators**: try `Read` on `package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`, `pom.xml`, `Gemfile`, etc.
- **Package manager**: try `Read` on `pnpm-lock.yaml`, `yarn.lock`, `package-lock.json`, `uv.lock`, `poetry.lock`.
- **Maturity**: `Glob **/*.{ts,tsx,js,jsx,py,go,rs,java,rb,php,vue}` excluding `node_modules`, `.venv`, `dist`, `build`. Bucket the count.
- **Git**: Bash `git rev-parse --is-inside-work-tree`, `git rev-list --count HEAD`, `git branch --show-current`.
- **Existing config**: Glob `CLAUDE.md`, `.claude/**`.
- **Tests**: Glob `**/*.test.*`, `**/*.spec.*`, `**/test_*.py`, `**/*_test.go`.
- **CI**: Glob `.github/workflows/*.yml`, `.gitlab-ci.yml`, `.circleci/config.yml`, `Jenkinsfile`.

Compose a JSON-equivalent fingerprint and proceed from Step 2.
