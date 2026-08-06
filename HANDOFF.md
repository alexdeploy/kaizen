# Handoff — current state of work

> Written for whoever picks this up next, including a future session that has
> lost its context. **Update this file at the end of every working session.**
> If it disagrees with reality, reality wins — verify before trusting a line.

**Last updated**: 2026-08-06
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
| Phase 1 | `/kaizen:init` step 7 records what it wrote | Harness + **a live run on a real monorepo (9 files recorded)** |
| Phase 1 | `/kaizen:upgrade` skill | Written and structurally checked; **never executed end to end** |
| Phase 2 | Standards catalog — 31 rules, `universal` / `typescript` / `python` | 873 harness checks: schema, provenance, ripgrep-compatible patterns, template↔index surface agreement |
| Phase 2 | `bin/kaizen-standards` (version/list/show/render/checks) | Exercised directly; render verified deterministic and refinement suppression working |
| Phase 2 | Templates converted to renderers (10 markers across 5 files) | Harness (both directions) + **a live run: 8 rules rendered with ids, no leftover markers** |
| Phase 3 | Workspace detection + `project_name` | Real project reports `backend-node,frontend,typescript`; 2 monorepo fixtures |
| Phase 4 | `/kaizen:analyze` verifies from the catalog | 963 standards checks incl. "no catalog pattern inlined in the skill"; checks run by hand against real code |
| Phase 4 | Depth-agnostic check globs | 38 globs fixed; TS-004 went from 36 false violations to 0 on a real monorepo |

## Verified against a real project (2026-08-06)

Run on a copy of a real 132-file pnpm monorepo (Vue 3 + Quasar + Capacitor
frontend, Express + Mongoose backend, 8 commits, GitHub Actions). Never on the
original — always `rsync` to a temp dir first.

**What held up:**

- **Existing config is respected.** `/kaizen:init` on a repo with a hand-written
  187-line `CLAUDE.md` and a full `.claude/` tree refused, explained the options
  and recommended merge-only. **554 files hashed before and after: zero bytes
  changed.**
- **Standards rendering works end to end.** Generated `CLAUDE.md` carried 8
  catalog rules with their ids, no placeholder or marker leaked.
- **The lock records correctly** — 9 files with hashes and baselines.
- **The partial-lock judgement worked.** In a run where `.claude/**` writes were
  blocked, the model refused to write a lock naming only `CLAUDE.md`, reasoning
  that a lock claiming a one-file config is worse than no lock. That is the
  behaviour the SKILL.md asks for, and it was not obvious.
- **The 3-way merge works on real content.** A user-added multi-tenant rule and
  a new kaizen `## Security` section merged clean, zero conflicts, catalog ids
  intact.

**Bugs found — see "Not yet verified / open bugs" below.**

## Bugs found by the real-project run — all six fixed (phase 3)

Fixed in the workspace-detection commit; see
[ADR-0007](./docs/decisions/0007-monorepo-is-a-shape.md).

| # | Bug | Fix | Verified |
|---|---|---|---|
| 1 | `kaizen-detect` read only the ROOT `package.json`, so a TypeScript monorepo detected as `javascript` and silently lost `TS-003` | Scans every workspace member; a member with TypeScript makes the project TypeScript | Real project now reports `backend-node,frontend,typescript`; `TS-003` renders |
| 2 | No workspace detection at all | `workspaces: {type, packages, count}` in the fingerprint | 2 new fixtures with goldens |
| 3 | `architecture_layout` globbed `src/*/` only | Walks `<package>/src/*/` per member when a workspace is detected | **Static only — needs a live run** |
| 4 | `{{PROJECT_NAME}}` was `basename(cwd)` | Comes from `detect.project_name` (manifest name) | Fixture goldens |
| 5 | No `no_format` conditional → dead `Format:` command | `no_format` + `workspace_scripts` conditionals added | **Static only — needs a live run** |
| 6 | Live evals used `acceptEdits`, which refuses writes under `.claude/**` | Default is now `bypassPermissions` | Was the harness that was wrong, not the plugin |

## Not yet verified — pick these up first

0. **The phase-3 fixes have no live run.** `kaizen-detect` is verified
   deterministically (the real project, 2 new fixtures, 41 detect checks), but
   the three changes that live in `init/SKILL.md` — per-package
   `architecture_layout`, `no_format`, `workspace_scripts` — depend on the model
   following new instructions and have only been checked statically. The live
   re-run hit the account's session limit (resets 13:20). Rerun:
   `rsync -a --exclude node_modules <real-project>/ /tmp/x/ && cd /tmp/x && rm -rf .claude CLAUDE.md`
   then `claude -p "/kaizen:init --profile=standard" --plugin-dir <plugin> --permission-mode bypassPermissions`
   and check: no leftover markers, `Project: **<manifest name>**`, per-package
   architecture bullets, no `Format:` line.

1. **`/kaizen:analyze` has never run as a skill.** Its checks were verified by
   running the catalog's patterns by hand against real code (TS-004: 36 hits
   without excludes, 0 with; TS-003: 1 hit, a comment false positive). What is
   unverified is the model following the three-population classification and
   producing the report shape. Needs a live eval on a project with a generated
   `CLAUDE.md` plus one hand-written convention.
2. **`/kaizen:upgrade` as a skill has never run** (the `kaizen-lock` engine
   underneath it now has, on real content). The riskiest part is step 3
   (re-rendering today's templates the way `init` would). Needs a live eval:
   init a fixture, change a template, edit a generated file as a "user", run
   upgrade, assert the user's edit survived. This is the single most important
   missing test in the project.
3. ~~`/kaizen:init` step 7 has never run live.~~ **Done** — verified on a real
   monorepo 2026-08-06; the lock recorded 9 files with baselines.
4. **`.gitignore` repair path is untested.** When an older project ignores all of
   `.claude/kaizen/`, init/upgrade are supposed to rewrite the rule. No test.
5. ~~No live run has ever filled a `KAIZEN_STANDARDS` marker.~~ **Done** —
   8 rules rendered with ids into a real project's `CLAUDE.md`, no leftovers.
6. **17 of 31 rules have no source.** Surfaced by the harness on every run.
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
| ✓ done | `/kaizen:analyze` reads the catalog | Reports by rule id over three populations, with provenance and a standards-status section |
| ← now | Three hooks + asserted security baseline | `Stop`, `PreToolUse`, `SessionStart`; delete the other 26 stubs |
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
