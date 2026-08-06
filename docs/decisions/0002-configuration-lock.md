# ADR-0002: Record what kaizen writes, and commit that record

- **Status**: accepted
- **Date**: 2026-08-05
- **Phase**: phase 1 / `next`

## Context

kaizen generated files and then forgot them. That single gap made everything
downstream impossible.

Asked "the templates improved — what about existing projects?", kaizen had two
answers: `--force` (overwrite, destroying customisations) or nothing (leave the
project frozen on whatever it got the day it was initialised). Both are wrong,
and the second is why scaffolders get run once and abandoned.

The `kaizen-managed: true` marker was the right instinct with the wrong
resolution: a binary per-file flag cannot distinguish "the user changed two
lines" from "the user rewrote this".

The missing capability was never merging. It was **knowing**.

## Decision

`/kaizen:init` records what it produced, in two artifacts under
`.claude/kaizen/`:

- **`lock.json`** — per file: path and SHA-256, plus the plugin version,
  profile and preset that produced them.
- **`baseline/<path>`** — a verbatim copy of each generated file.

Both are **committed**, like `package-lock.json`. The `.gitignore` template
ignores `.claude/kaizen/*` and negates these two.

The hash answers "did the user change this?". The baseline answers the harder
question — "changed *from what?*" — without which there is no merge base and
therefore no merge.

## Consequences

**Easier:** everything in the roadmap. Safe upgrades, a versioned standards
catalog (projects must be able to move between versions), a `doctor` that can
offer to fix what it finds. Each of those degrades to "overwrite and hope"
without this record.

**Harder:** `/kaizen:init` gains a mandatory step, and every future skill that
writes into a project must remember to re-record. The harness guards the
mechanism, not the discipline.

**Costs:**
- A copy of every generated file lives in the repo. Small (tens of KB) but not
  zero, and it is duplication — the baseline of an untouched file is identical
  to the file.
- Committing the lock means merge conflicts *on the lock* when two people run
  kaizen on separate branches. Acceptable: the conflict is legible, and a wrong
  lock is recoverable by re-recording.
- Projects initialised before this exist without a lock. They get an explicit
  adoption path, never a silent overwrite.

**Accepted limitation:** the lock records what kaizen wrote, not why. Rule-level
provenance is [ADR-0005](./0005-standards-as-versioned-data.md)'s job.

## Alternatives

- **Hash only, no baseline copy** — rejected: detects modification but cannot
  merge, which reduces the feature to a warning.
- **Re-render the old version from the old plugin to get the merge base** —
  rejected: requires keeping every historical plugin version reachable, and
  breaks entirely if the user's detection results changed in between.
- **Store the lock outside the repo (`~/.claude/`)** — rejected: configuration
  provenance is a property of the project, not of the machine. A teammate
  cloning the repo must be able to upgrade it.
- **Keep `kaizen-managed: true`** — kept as a *hint* for authorship, superseded
  as an *upgrade mechanism*.
