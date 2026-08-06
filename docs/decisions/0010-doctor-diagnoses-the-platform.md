# ADR-0010: `/kaizen:doctor` diagnoses the platform, and gets to be a verb

- **Status**: accepted
- **Date**: 2026-08-06
- **Phase**: phase 6 / `next`

## Context

[ADR-0002](./0002-configuration-lock.md) solved one half of "updates without
breaking anything": kaizen's own changes can no longer destroy a user's edits.

The other half was untouched. **Claude Code moves independently of kaizen.**
Settings keys and hook events are added; a configuration generated months ago can
reference something that no longer exists, or — worse — something misspelled from
the start, because a misspelled hook event never fires and never errors. The setup
looks configured forever and does nothing.

Nothing in kaizen looked at that. Every skill reads `CLAUDE.md` and trusts it.

There was also a rule in the way. [ADR-0004](./0004-upgrade-replaces-force.md)
made `/kaizen:upgrade` "the one deliberate exception" to a moratorium on new
verbs. This is the second exception, which means either the rule was wrong or it
needs a stated bar.

## Decision

**`/kaizen:doctor` is its own verb**, and the bar for a new one is now explicit:

> A new verb needs a distinct **subject**, not a distinct report section. If it
> reads the same things the existing verbs read, it is a flag.

`doctor`'s subject is the *platform and the environment* — the Claude Code
version, the validity of settings against it, whether scripts referenced actually
exist, whether required tools are installed. No other skill looks at any of that.
And there is a second, sharper reason: **every other skill assumes the
configuration is valid.** `doctor` assumes it might not be, which makes it the
only skill worth running when something is broken — and a user whose setup is
broken cannot be expected to remember a flag.

Three severities, and the third is the load-bearing one:

| Severity | Means |
|---|---|
| `problem` | kaizen can **prove** it is broken — a hook pointing at a missing file |
| `warning` | probably wrong, or a real recurring cost |
| `info` | kaizen does **not recognise** it, which is not the same as invalid |

The registry of known settings keys and hook events lives in
`compat/claude-code.json`, versioned separately (`2026.08`), for the same reason
the standards catalog is: the platform outruns plugin releases.

Deterministic checking lives in `bin/kaizen-doctor` (Python 3, JSON out). The
skill explains, orders by consequence, and proposes fixes. `--fix` applies only
changes with exactly one correct outcome — `chmod +x`, the `.gitignore` negation,
an agent name mismatch — and never guesses a `paths:` glob.

## Consequences

**Easier:** finding out why a hook silently does nothing. Discovering that four
agents in a real project have no frontmatter and therefore never loaded — which
is precisely what happened the first time this ran against one.

**Harder:** the compat registry is now a thing to maintain. A stale registry does
not break doctor — unfamiliar keys degrade to `info` — but it does make it less
useful over time, and nothing reminds anyone to update it except the version
number looking old.

**Costs:**
- A tenth verb. The bar above exists so the eleventh needs a real argument.
- kaizen now asserts things about Claude Code's configuration format, which is
  not kaizen's format. Every such assertion is a chance to be wrong, which is
  exactly why only two things are ever called problems: an entry on the curated
  deprecation list, and a fault kaizen can prove by looking at the filesystem.

**Accepted limitation:** the registry cannot be exhaustive. kaizen does not know
every valid settings key and never will. `info` is the honest representation of
that gap, and reporting an unrecognised key as invalid would make the tool wrong
the day the platform ships a new one.

## Alternatives

- **A `--compat` mode on `/kaizen:analyze`** — rejected on discoverability.
  `analyze`'s subject is your code against your rules; this is your setup against
  the platform. And a broken setup is the worst moment to require remembering a
  flag. (`brew doctor`, `flutter doctor`, `npm doctor` — the idiom is universal.)
- **Fold it into `/kaizen:upgrade status`** — rejected: `upgrade` requires a lock,
  and a project with no lock is one of the things doctor needs to report on.
- **Validate settings against a JSON schema fetched at runtime** — rejected: a
  network call on every run, non-reproducible behaviour, and a supply-chain
  surface for content that decides what kaizen tells you is wrong.
- **Treat an unrecognised key as an error** — rejected, and this is the one that
  matters most. It would make doctor confidently wrong on a schedule set by
  someone else's release cadence.
- **Let `--fix` repair everything it finds** — rejected: restoring a missing hook
  script means deciding whether you want that hook, and splitting an oversized
  `CLAUDE.md` is an editorial judgement about your own conventions.
