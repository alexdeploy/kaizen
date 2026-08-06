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

## Open bugs found by the real-project run

1. **`kaizen-detect` only reads the ROOT `package.json`.** In a pnpm workspace
   the dependencies live in `frontend/` and `backend/`, so a TypeScript monorepo
   is detected as `stack: "javascript"` with no `frontend` or `backend-node`
   token. Consequence is concrete: **TS-003 (`No any`) applies only to
   `typescript` and is silently not rendered** — a 132-file TypeScript project
   gets no rule about `any`. Highest-value fix available.
2. **No workspace/monorepo detection at all.** `pnpm-workspace.yaml`,
   `workspaces` in `package.json`, `turbo.json`, `nx.json` are all ignored.
   Monorepo is a *shape*, orthogonal to stack — it changes where config goes,
   not what it says.
3. **`architecture_layout` globs `src/*/` only.** A monorepo has no root `src/`,
   so the literal directive would write "No src/ directory detected", which is
   false. The model worked around it and said so; the directive is still wrong.
4. **`{{PROJECT_NAME}}` is `basename(cwd)`.** Wrong whenever the directory name
   is not the project name. Should prefer `package.json` `name` and fall back to
   the basename.
5. **No `no_format` conditional.** The generated CLAUDE.md advertises
   `Format: pnpm run format` in a repo with no root `format` script — a dead
   command in the first section Claude reads every session.
6. **Live evals need `bypassPermissions`.** `acceptEdits` refuses writes under
   `.claude/**`, so a live run produces `CLAUDE.md` and nothing else and looks
   like a product failure. Fixed in `tests/live/run-live.sh`.

## Not yet verified — pick these up first

1. **`/kaizen:upgrade` as a skill has never run** (the `kaizen-lock` engine
   underneath it now has, on real content). The riskiest part is step 3
   (re-rendering today's templates the way `init` would). Needs a live eval:
   init a fixture, change a template, edit a generated file as a "user", run
   upgrade, assert the user's edit survived. This is the single most important
   missing test in the project.
2. ~~`/kaizen:init` step 7 has never run live.~~ **Done** — verified on a real
   monorepo 2026-08-06; the lock recorded 9 files with baselines.
3. **`.gitignore` repair path is untested.** When an older project ignores all of
   `.claude/kaizen/`, init/upgrade are supposed to rewrite the rule. No test.
4. ~~No live run has ever filled a `KAIZEN_STANDARDS` marker.~~ **Done** —
   8 rules rendered with ids into a real project's `CLAUDE.md`, no leftovers.
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
