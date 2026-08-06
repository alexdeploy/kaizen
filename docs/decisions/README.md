# Architecture Decision Records

One file per decision that would be expensive to reverse or confusing to
encounter without knowing why it was made.

## Why these exist

kaizen's code is prompts and data. A prompt does not carry its reasoning: six
months from now, `"NEVER resolve a conflict on the user's behalf"` reads like an
arbitrary restriction unless something records that it was a deliberate choice
about who has standing to overrule a developer in their own project.

These records exist so a future maintainer — or a future session that has lost
its context — can tell **a decision from an accident**, and can change one
knowing what it costs.

## Format

```markdown
# ADR-NNNN: Short imperative title

- **Status**: proposed | accepted | superseded by ADR-NNNN | reversed
- **Date**: YYYY-MM-DD
- **Phase**: which release / branch this belongs to

## Context      — the forces at play. What made a decision necessary.
## Decision     — what was chosen, stated plainly.
## Consequences — what this makes easy, what it makes hard, what it costs.
## Alternatives — what else was considered and why it lost.
```

## Rules

- **One decision per file.** If a record needs "and also", it is two records.
- **Never edit a decision's substance after it is accepted.** Supersede it with
  a new ADR and mark the old one. The record of having changed your mind is
  worth more than a tidy document.
- **Write the consequences honestly, including the bad ones.** An ADR that
  reads like a sales pitch is useless — the whole point is helping someone judge
  a trade-off you already made.
- Record decisions about *the product*, not about implementation detail. "Which
  JSON key name" is not an ADR. "Runtime scripts may be Python" is.

## Index

| ADR | Title | Status |
|---|---|---|
| [0001](./0001-two-layer-validation-harness.md) | Two-layer validation harness | accepted |
| [0002](./0002-configuration-lock.md) | Record what kaizen writes, and commit that record | accepted |
| [0003](./0003-delegate-merging-to-git.md) | Delegate merging to `git merge-file`; the model never merges | accepted |
| [0004](./0004-upgrade-replaces-force.md) | `/kaizen:upgrade` replaces `--force` | accepted |
| [0005](./0005-standards-as-versioned-data.md) | Standards are versioned data with provenance, not prose in templates | accepted |
| [0006](./0006-python-for-structured-runtime-scripts.md) | Runtime scripts may be Python 3 when the job is structured data | accepted |
