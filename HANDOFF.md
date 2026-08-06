# Handoff — current state of work

> Written for whoever picks this up next, including a future session that has
> lost its context. **Update this file at the end of every working session.**
> If it disagrees with reality, reality wins — verify before trusting a line.

**Last updated**: 2026-08-05
**Working branch**: `next`
**Comparison point**: tag `baseline-v0.12.1` (the project as it was before the
new direction, harness included)

## Where things are

```
main                    the plugin as shipped (v0.12.1) + the validation harness
  └─ baseline-v0.12.1   tag: safe point to compare against or return to
       └─ next          the new direction — everything below lives here
```

- Compare everything: `git diff baseline-v0.12.1..next`
- Return: `git checkout main`
- Undo one phase: `git revert <commit>`

## The direction

[ROADMAP.md](./ROADMAP.md) — the argument, in full. In one line: kaizen is
moving from **scaffolder** (generate files once) to **configuration package
manager** (keep a project's setup current, safely, forever).

Decisions and their reasoning: [docs/decisions/](./docs/decisions/README.md).
**Read those before changing anything structural** — several restrictions that
look arbitrary are deliberate.

## Done and verified

| Phase | What | Verified how |
|---|---|---|
| v0.13 | Validation harness: 8 deterministic suites, live evals | `tests/run.sh` green; caught a real README/version mismatch on its first run |
| Phase 1 | `bin/kaizen-lock` — write / status / merge / forget | 37 harness checks over real temp repos, including a clean 3-way merge that preserves a user's own rule and a same-line conflict that is reported rather than merged away |
| Phase 1 | `/kaizen:init` step 7 records what it wrote | Harness (skills suite); **not yet exercised in a live run** |
| Phase 1 | `/kaizen:upgrade` skill | Written and structurally checked; **never executed end to end** |
| Phase 2 | Standards catalog — 31 rules, `universal` / `typescript` / `python` | 873 harness checks: schema, provenance, ripgrep-compatible patterns, template↔index surface agreement |
| Phase 2 | `bin/kaizen-standards` (version/list/show/render/checks) | Exercised directly; render verified deterministic and refinement suppression working |
| Phase 2 | Templates converted to renderers (10 markers across 5 files) | Harness (both directions); **never rendered by a live `/kaizen:init`** |

## Not yet verified — pick these up first

1. **`/kaizen:upgrade` has never actually run.** The riskiest part is step 3
   (re-rendering today's templates the way `init` would). Needs a live eval:
   init a fixture, change a template, edit a generated file as a "user", run
   upgrade, assert the user's edit survived. This is the single most important
   missing test in the project.
2. **`/kaizen:init` step 7 has never run live.** The first live eval attempt hit
   the account's usage limit at 145s, before `init` reached the lock step.
   Rerun: `KZ_LIVE_ONLY=init-standard-ts tests/live/run-live.sh`
3. **`.gitignore` repair path is untested.** When an older project ignores all of
   `.claude/kaizen/`, init/upgrade are supposed to rewrite the rule. No test.
4. **No live run has ever filled a `KAIZEN_STANDARDS` marker.** The whole
   templates-as-renderers change is verified statically only. The live eval
   should assert that a generated `CLAUDE.md` contains rule ids and no leftover
   marker — `tests/live/assert_init.py` already fails on a surviving marker, so
   this mostly needs the live run to actually complete.
5. **17 of 31 rules have no source.** Surfaced by the harness on every run.
   Either find the source or accept them explicitly as kaizen's own opinions —
   but they should not stay ambiguous.

## Known gaps the harness reports on every run

These are warnings, not failures — deliberate, and visible on purpose:

- Six stacks (`go`, `rust`, `java`, `ruby`, `php`, `elixir`) are detected but
  fall back to the `generic` preset.
- `{{HAS_CI}}` and `{{STACK_RAW}}` are documented placeholders no template uses.
- `detect_maturity` counts only source extensions, so a prose/shell repo reports
  `maturity: "empty"` — kaizen's own repo included. Encoded in the `docs-only`
  fixture with a `_note`.

## Next phases (from ROADMAP.md)

| Next | Phase | Note |
|---|---|---|
| ✓ done | Standards catalog with provenance | Templates are renderers over versioned rule data |
| ← now | `/kaizen:analyze` reads the catalog | Replace the hardcoded pattern library with `kaizen-standards checks`; report rule ids and deprecations instead of fuzzy substring matches |
| | Three hooks + asserted security baseline | Delete the other 26 stubs |
| | `/kaizen:doctor` | Claude Code version compatibility |
| | Monorepo shape, `kaizen.config.json`, go/rust presets | |

## Working agreements for this project

- **No new verbs.** `/kaizen:upgrade` was the one deliberate exception
  ([ADR-0004](./docs/decisions/0004-upgrade-replaces-force.md)).
- **The fix and the check that would have caught it go in the same commit.**
- **Every structural decision gets an ADR** before or with the code.
- **Do not bump versions for unreleased work.** It lives under `[Unreleased]`
  in the CHANGELOG until it ships.
- `tests/run.sh` must be green before any commit.
