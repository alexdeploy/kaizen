# ADR-0003: Delegate merging to `git merge-file`; the model never merges

- **Status**: accepted
- **Date**: 2026-08-05
- **Phase**: phase 1 / `next`

## Context

With a lock and a baseline ([ADR-0002](./0002-configuration-lock.md)), kaizen
has the three versions a merge needs: what it wrote (base), what the project has
now (yours), and what today's template produces (theirs). Something has to
combine them.

The obvious move in an LLM-centric tool is to let the model do it — it has all
three files in context and merging is "just" careful reading.

## Decision

The model never merges. `git merge-file --diff3` does, invoked by
`kaizen-lock merge`, which reports the conflict count and writes the result to a
temp file **outside the project**.

The division of labour:

| Job | Owner |
|---|---|
| Hashing, snapshotting, classifying | `kaizen-lock` |
| The merge itself | `git merge-file` |
| What to do about a conflict | The user, prompted by the skill |
| Rendering today's template output | The model |

## Consequences

**Easier:** correctness. Merge semantics are decades old, implemented on every
machine that already has git — which kaizen requires anyway. Conflict markers
are a format developers already know how to resolve.

**Harder:** kaizen cannot do "smart" merges a model could attempt — for example
recognising that a user's reworded rule means the same thing as the new
template's wording, and keeping one. That would be nice. It is also exactly the
kind of judgement that goes wrong silently.

**Costs:** a hard dependency on git for the upgrade path. Acceptable: every
kaizen skill that matters already requires a git repo.

**Why this is not negotiable:** a model that merges by hand produces
*plausible-looking corruption*. Not a crash, not an obvious mangling — a file
that reads fine and quietly lost a line. For a tool whose entire promise is
"does not break anything", that is the worst available failure mode, and it is
undetectable by the user until it matters.

## Alternatives

- **Model-driven merge** — rejected above.
- **Model-driven merge with the model verifying its own output** — rejected: the
  verification has the same failure mode as the merge.
- **Refuse to merge; always ask the user to resolve manually** — rejected as the
  default: most upgrades touch lines nobody customised, and asking about all of
  them trains users to approve blindly. It remains the behaviour when no
  baseline is available.
- **Bundle a merge implementation** — rejected: reimplementing diff3 to avoid a
  dependency that is already present is unjustifiable.
