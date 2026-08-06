# ADR-0008: `/kaizen:analyze` reports by rule id, over three populations

- **Status**: accepted
- **Date**: 2026-08-06
- **Phase**: phase 4 / `next`

## Context

Until now `/kaizen:analyze` matched conventions by prose. It read the bullets
under `## Conventions` in a project's `CLAUDE.md` and compared each one, by
case-insensitive substring, against a keyword table hardcoded in
`analyze/SKILL.md`:

| Convention keyword | Check |
|---|---|
| `named exports only`, `no default exports` | grep `^export default` |

Three problems, all structural:

1. **Rewording silently disabled verification.** A user tidying "No default
   exports." into "Avoid default exports." lost the check, with no error
   anywhere. The rule and its verification were separate objects joined by
   string similarity.
2. **A violation carried no reason.** The report could say a rule was broken but
   not why the rule existed, so a developer had nothing to weigh the finding
   against.
3. **kaizen's rules and the user's rules were indistinguishable.** Everything in
   `## Conventions` was treated as kaizen's to judge, including conventions the
   team wrote themselves.

[ADR-0005](./0005-standards-as-versioned-data.md) made a fix possible: rules are
catalog entries with ids, and every generated line carries its id as an HTML
comment.

## Decision

`--best-practices` sorts every convention in the project's config into **three
populations, which are never mixed in the report**:

| Population | Identified by | Treatment |
|---|---|---|
| **A — catalog rule** | line ends with `<!-- RULE-ID -->` | verified with the catalog's own check; reported by id, with rationale and source |
| **B — the user's own** | no id | not kaizen's to judge. One *exact* text match against catalog statements is attempted and reported as such; otherwise unchecked |
| **C — available, not adopted** | in the catalog for this stack/maturity, no line carries its id | reported as a gap, never as a violation |

Plus a **standards status** section: rules deprecated or unknown to the catalog,
and rules added since the `standards_version` recorded in the lock
(`kaizen-standards list --added-after <version>`).

The keyword table is deleted. Checks come from `kaizen-standards checks`, used
verbatim, and a harness check fails the build if any catalog pattern reappears
inside `analyze/SKILL.md`.

## Consequences

**Easier:** trusting the report. A finding names a rule, quotes its reason, links
its source, and can be looked up with `kaizen-standards show <ID>`. Answering
"is my config current?" — previously unanswerable — is now a section.

**Harder:** projects whose config predates ids get less. Population B's exact
text match is deliberately narrow; anything reworded lands in "unchecked". The
remedy is `/kaizen:upgrade`, which is a nudge, not a wall.

**Costs:**
- More output. The report has five sections where it had three, and a report
  nobody reads is worthless. Every section is suppressed when empty.
- The three-population split must be maintained by the model. Getting it wrong
  in either direction — judging a user's own rule, or reporting an unadopted rule
  as a violation — turns an audit into an argument, so both are hard rules.

**Accepted limitation, stated in the report:** grep-based checks have no comment
or string awareness. Running TS-003 against a real project produced exactly one
match, and it was the comment `Crude heuristic: any CJK char`. Rather than
weaken the pattern or hide the match, the rule carries a `note` about the false
positive and the report must print it. A known limitation shown is worth more
than a clean-looking report that cannot be trusted.

## Alternatives

- **Keep substring matching as a fallback for everything without an id** —
  rejected: it reintroduces exactly the silent-drift failure the ids exist to
  fix. An exact match is verifiable; a fuzzy one is a guess presented as a fact.
- **Have the model judge conventions it cannot mechanically check** — rejected:
  unverifiable findings are indistinguishable from confident invention, and the
  "Unchecked (manual review)" list already tells the user where to look.
- **Report unadopted rules as violations** to push adoption — rejected as
  dishonest. A project that never had a rule has not broken it.
- **Strip comments before grepping** — rejected: correct comment stripping is
  per-language parsing, and an approximation would create a second, subtler
  class of wrong answers.
