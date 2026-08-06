# ADR-0004: `/kaizen:upgrade` replaces `--force`

- **Status**: accepted
- **Date**: 2026-08-05
- **Phase**: phase 1 / `next`

## Context

The roadmap's own advice was "the next release should add zero new verbs" —
eight skills is already more surface than the value delivered. Adding a ninth
needs a better reason than "it would be useful".

Meanwhile `--force` is the only path for an existing project to receive template
improvements, and it works by overwriting. It is a destructive verb answering a
non-destructive question.

## Decision

Add one verb, `/kaizen:upgrade`, and treat it as the exception that earns the
rule. It is the operation the product's stated ambition ("keeps improving
without breaking anything") actually names; the moratorium is on *more analysis
verbs*, which dilute.

Its contract:

- Default invocation **plans and writes nothing**. `apply` is a separate word.
- A `modified` file is merged, never overwritten. No flag changes this.
- A file absent from the lock is never touched, even at a path kaizen would
  normally generate.
- A deleted file stays deleted.
- Conflicts go to the user: keep yours / take theirs / write markers. kaizen
  never arbitrates.
- Profile and preset come from the lock. An upgrade changes content, not
  identity.

`--force` survives for the one legitimate case: a project with no lock that
wants a clean regeneration.

## Consequences

**Easier:** staying current. A user can accept template improvements without
auditing every file, because the plan tells them what changes and the merge
preserves what they wrote.

**Harder:** kaizen must now be able to re-render historical output faithfully.
The upgrade renders "what today's templates produce" using the *recorded*
profile and preset — if template rendering ever becomes non-deterministic in a
way the lock does not capture, plans will show phantom changes.

**Costs:** a ninth verb to learn, and a second place (besides `init`) that
writes into user projects. The hard rules are correspondingly strict.

**Risk accepted:** step 3 of the skill — re-rendering today's templates — is the
least mechanical part and depends on the model following `init`'s pipeline
exactly. This is the part most in need of live-eval coverage, and it does not
have it yet.

## Alternatives

- **Make `--force` smarter** — rejected: a flag whose meaning is "destroy my
  changes" cannot be quietly redefined as "merge them". Users who learned the
  destructive meaning would be badly surprised.
- **Fold upgrading into `/kaizen:init`** — rejected: `init` means "start", and
  overloading it hides a genuinely different operation with different risks
  behind a familiar name.
- **Auto-upgrade on session start via a hook** — rejected outright: writing to a
  user's config without them asking is the exact opposite of the trust this
  feature exists to build.
