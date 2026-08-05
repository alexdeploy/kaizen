# kaizen :: validation harness

kaizen is made almost entirely of prompts. A prompt has no compiler, no type
checker and no stack trace — a regression in a `SKILL.md` shows up as *slightly
worse output in someone else's project*, weeks later. This harness exists to
close that gap.

```bash
tests/run.sh              # every deterministic suite — seconds, free, no deps
tests/run.sh -v           # show each passing check
tests/run.sh --only detect
tests/run.sh --list
tests/run.sh --live       # + the LLM behaviour evals (spawns real sessions)
```

Exit code `0` = every invariant holds. `1` = something broke. Requires Python 3
(stdlib only) and `bash`. `shellcheck` is used when present and skipped when not.

---

## The two layers

| Layer | What it proves | Cost | Runs in CI |
|---|---|---|---|
| **Deterministic suites** (`tests/suites/`) | The plugin is internally consistent: manifests agree, references resolve, every template placeholder has a directive, every script parses, `kaizen-detect` still returns exactly what it used to | ~0.5s, free | yes, on every push |
| **Live evals** (`tests/live/`) | Claude, given a `SKILL.md`, actually produces what the skill promises | minutes, tokens | no — opt-in, run before a release |

The split matters: the first layer catches the failures that are *mechanically
detectable*, which is most of them, and it must stay fast enough that nobody
skips it. The second catches the ones only a real run can reveal, and is priced
accordingly.

---

## Deterministic suites

| Suite | Guards |
|---|---|
| `manifests` | `plugin.json` / `marketplace.json` / README / CHANGELOG agree on the version; the marketplace source path resolves; plugin-level `settings.json` and `.mcp.json` are valid and point at real files |
| `skills` | Frontmatter completeness; `disable-model-invocation: true`; a skill that dispatches agents declares `Task`; read-only skills declare no editing tool; skills only write artifacts under `.claude/kaizen/` |
| `agents` | Frontmatter completeness; `name` matches the filename; model ids are in the allowlist; **an agent documented read-only holds no writing tool**; project-level agents carry the `kaizen-managed` marker |
| `references` | Every dispatched `subagent_type` exists; no orphan agents; every `/kaizen:*` named in the docs exists (or is declared planned); every relative markdown link resolves |
| `templates` | Every `{{PLACEHOLDER}}` and `KAIZEN_ENRICH:<id>` in a template is registered in `init/SKILL.md` **and vice versa**; presets are complete; template JSON parses; every stack `kaizen-detect` can emit maps to a real preset |
| `scripts` | Shebang, `bash -n`, exec bit, strict mode, shellcheck when available |
| `hooks` | Stubs are still no-ops (exit 0, silent, consume stdin) and actually execute; `hooks.json.example` and `scripts/` stay in sync; a real `hooks.json` may only wire scripts declared in `ACTIVE_HOOKS` |
| `detect` | Golden output for every fixture repo |

### Severity

- **fail** — a broken invariant. Exits 1, breaks CI.
- **warn** — drift worth seeing, not breakage. Never fails the build.

Warnings are the harness's other job: they carry the known gaps out of the
maintainer's head and into every run. Today's warnings are all real findings —
stacks that are detected but fall back to the `generic` preset, placeholders
documented but never used, and the `docs-only` fixture below.

---

## Fixtures

`tests/fixtures/<name>/` is a miniature repo plus:

- `expected.json` — the exact `kaizen-detect` output, minus `cwd`. An optional
  `_note` field documents an *encoded limitation* and is surfaced as a warning.
- `fixture.json` — optional. `git.init` / `git.commits` / `git.branch`, and a
  `_comment` explaining what the fixture is for.

Fixtures are copied to a temp dir before running, so the surrounding kaizen repo's
git state can never leak into a result.

| Fixture | Covers |
|---|---|
| `empty` | The empty-repo branch of `/kaizen:init` |
| `typescript-node` | The happy path: TS + React + pnpm + vitest + CI + git history |
| `python-uv` | Python preset selection, `uv` lockfile |
| `go-module` | A stack that is **detected but has no preset** — the generic-fallback warning made concrete |
| `docs-only` | Encodes a known limitation: `maturity` counts only code extensions, so a docs/shell repo reads as `empty` (kaizen's own repo does too) |
| `existing-config` | The refuse-without-`--force` branch, and the CSV *ordering* of `existing_claude_config`, which `/init` parses |

### Adding one

```bash
mkdir -p tests/fixtures/my-case
# ...put the minimum files that trigger the behaviour...
tests/run.sh --only detect     # see what detect returns
# write tests/fixtures/my-case/expected.json with the output you INTEND
```

Write the expectation you intend, not the output you got. If they differ you
have either found a bug or learned something — both worth a commit message.

---

## Live evals

```bash
tests/live/run-live.sh
KZ_LIVE_ONLY=init-standard-ts KZ_LIVE_KEEP=1 tests/live/run-live.sh
```

Each scenario copies a fixture to a temp dir, `git init`s it, runs
`claude -p "<prompt>" --plugin-dir plugins/kaizen --permission-mode acceptEdits`
inside it, then asserts on what landed on disk:

- `CLAUDE.md` and `.claude/settings.json` exist, and the settings parse
- **no `{{PLACEHOLDER}}` or `KAIZEN_ENRICH:` marker survived** into the project
  — the single highest-value behavioural assertion, and invisible statically
- `CLAUDE.md` respects its own ~200-line budget
- every generated hook is executable, as `/kaizen:init` promises
- the profile produced the right shape (`advanced` → 7 agents + a workflow rule)
- nothing unexpected appeared at the project root (the boundary contract)
- the run printed the drift report `init/SKILL.md` makes mandatory

| Env | Effect |
|---|---|
| `KZ_CLAUDE_BIN` | Claude Code binary (default: `claude`) |
| `KZ_LIVE_MODEL` | Passed to `--model` |
| `KZ_LIVE_ONLY` | Run one scenario by name |
| `KZ_LIVE_KEEP=1` | Keep the temp project for inspection |
| `KZ_LIVE_TIMEOUT` | Per-scenario seconds (default 600) |

Scenarios are the `SCENARIOS` array at the top of `run-live.sh`. Adding one is a
line there plus, if it is not an `/init` run, an assertion script beside
`assert_init.py`.

---

## Extending the deterministic layer

1. Add `tests/suites/test_<name>.py` exposing `run(reporter)`.
2. Register `<name>` in `SUITES` in `tests/lib/runner.py`.
3. Use `r.check(...)` for invariants and `r.warn(...)` for drift.

Two rules that keep this harness honest:

- **Parse the source of truth, don't copy it.** The placeholder and enrichment
  registries are read out of `init/SKILL.md` itself, so documentation and
  templates can only drift apart by failing a check — never by both being
  updated to the same wrong value.
- **A warning must be actionable.** If a warning cannot be fixed or silenced by
  a specific edit, it trains people to ignore the whole list.
