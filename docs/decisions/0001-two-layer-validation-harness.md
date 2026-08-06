# ADR-0001: Two-layer validation harness

- **Status**: accepted
- **Date**: 2026-08-05
- **Phase**: v0.13 / `main`

## Context

kaizen is made almost entirely of prompts: `SKILL.md` files, agent definitions,
markdown templates, plus one bash script. There is no compiler, no type checker
and no stack trace.

The consequence is specific: a regression does not look like a crash, it looks
like slightly worse output in somebody else's project weeks later. A renamed
agent that no skill dispatches. A template placeholder with no directive telling
Claude how to fill it, shipping a literal `{{TEST_RUNNER}}` into a user's
`CLAUDE.md`. None of these fail loudly, and all of them are mechanically
detectable.

The v0.12.1 CHANGELOG cites a "deterministic test suite run post-release" that
found a real bug. That suite was run by hand once and never committed — by
definition it could not run again.

## Decision

Two layers, split by cost, with different jobs:

1. **Deterministic suites** (`tests/run.sh`) — parse and cross-check every
   shipped file; run `kaizen-detect` against fixture repos. Seconds, free, no
   dependencies beyond Python 3 stdlib and bash. Runs on every push.
2. **Live evals** (`tests/run.sh --live`) — real headless Claude Code sessions
   against throwaway fixture copies, asserting on the files that land. Minutes
   and tokens. Opt-in, before a release, never in CI.

Plus two supporting decisions:

- **`warn` is a distinct severity from `fail`**, and never breaks the build. Its
  job is to carry known gaps out of the maintainer's head into every run.
- **Registries are parsed from the source of truth, never copied.** The
  placeholder and enrichment-directive lists are read out of `init/SKILL.md`
  itself and checked against templates in both directions.

## Consequences

**Easier:** renaming anything, because every cross-reference is checked. Adding
a stack, because preset/detection parity is guarded. Releasing, because the
manifests suite catches the version you forgot — it caught one on its first run.

**Harder:** nothing about the plugin's behaviour, but every new check is a new
thing that can be wrong. A false-positive warning is worse than no warning: it
trains people to ignore the list. Warnings must stay actionable or be deleted.

**Costs:** the live layer costs real tokens, so in practice it runs rarely. That
means most behavioural regressions are still caught by a human noticing. The
harness raises the floor; it does not certify the ceiling, and the docs say so.

**Accepted limitation:** a green run means "nothing known-broken ships", not
"the prompts give good advice". No amount of static checking reaches the second.

## Alternatives

- **pytest** — rejected: needs an install, and these are assertions about files,
  not unit tests of functions. Zero-install matters for a plugin whose users are
  not necessarily Python developers.
- **Only live evals** — rejected: too slow and too expensive to run on every
  change, which means they would not be run on every change.
- **Only static checks** — rejected: the highest-value assertion in the whole
  harness (no unsubstituted placeholder reaches a user's project) is only
  observable by running the thing.
