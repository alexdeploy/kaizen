# ADR-0005: Standards are versioned data with provenance, not prose in templates

- **Status**: accepted
- **Date**: 2026-08-05
- **Phase**: phase 2 / `next`

## Context

kaizen's pitch is that a user's setup follows current best practice. Today those
practices are prose lines inside markdown templates:

```markdown
## Conventions
- **Named exports only.** No default exports.
- **No `any`.** Use `unknown` and narrow.
```

Three problems follow from that representation, and none of them are fixable by
editing the templates more often.

**1. Updating a practice requires releasing the plugin.** Standards move faster
than software. As long as they are the same artifact, "up to date" is a claim
about the maintainer's free time.

**2. A rule cannot be argued with.** The template asserts opinions as if they
were detected facts. There is no rationale, no source, no date — so a team that
disagrees has no material to disagree *with*, and a user cannot tell a
considered rule from an arbitrary one.

**3. The rule and its check are separate objects, joined by fuzzy matching.**
The statement lives in a template; the check that verifies it lives in
`analyze/SKILL.md`'s pattern library, matched by case-insensitive substring
against the convention text. Reword a convention and it silently becomes
unchecked, with no error anywhere.

## Decision

Extract every convention into a **catalog of rules as data**, under
`plugins/kaizen/standards/`, versioned independently of the plugin using
calendar versioning (`2026.08`).

Each rule carries what a rule needs to be trustworthy:

```json
{
  "id": "TS-004",
  "title": "No default exports",
  "statement": "**Named exports only.** No default exports.",
  "rationale": "Named exports keep rename refactors mechanical…",
  "sources": [{ "label": "…", "url": "…" }],
  "added": "2026-08-05",
  "severity": "convention",
  "status": "active",
  "applies_to": { "stack": ["typescript"], "maturity": ["scaffold", "small", "mature"] },
  "surface": "claude_md.conventions",
  "check": { "type": "grep", "pattern": "^export default", "include": [".ts"], "exclude": ["*.test.*"] }
}
```

Templates keep their shape and gain `<!-- KAIZEN_STANDARDS:<surface> -->`
markers — the same idiom as the existing `KAIZEN_ENRICH` directives — which
`/kaizen:init` fills by rendering the rules that apply to the detected stack and
maturity. **Templates become renderers; the catalog is the source of truth.**

Rendered rules carry their id as an HTML comment (`<!-- TS-004 -->`) so any
line in a user's `CLAUDE.md` can be traced back to the rule that produced it.

## Consequences

**Easier:**
- Shipping standards updates without a plugin release.
- `/kaizen:analyze` reporting "TS-004 was superseded in `2026.09`" instead of
  just "you violated a rule".
- Adding a stack: write rules, not prose in another template.
- Disagreeing productively — a rule with a rationale and a source can be
  discussed, disabled, or replaced.
- Keeping statement and check in one object with a stable id, so rewording a
  rule can no longer silently disable its verification.

**Harder:**
- Two sources of truth to keep in sync — the catalog and the templates that
  reference its surfaces. The harness checks both directions, which is the only
  reason this is acceptable.
- Rules now need *maintenance*: a source link that rots, a date that ages, a
  rationale that stops being true. That work is real and did not exist before.

**Costs:**
- ~5 tokens per rendered rule for the id comment in `CLAUDE.md`, which is loaded
  every session. Roughly 50 tokens for a typical config. Paid deliberately in
  exchange for traceability.
- The catalog is a new artifact users can read but not yet edit. Project-level
  overrides are not designed yet and must not be improvised.

**Accepted limitation:** a versioned catalog does not make the rules *correct*.
It makes them *auditable*, dated and attributable — which is what turns "best
practices" from an adjective into something a team can evaluate.

## Alternatives

- **Keep prose, edit templates faster** — rejected: does not address provenance,
  the check-linkage gap, or release coupling.
- **Fetch standards from a remote URL at runtime** — rejected for now: turns
  every `init` into a network call, makes behaviour non-reproducible, and
  introduces a supply-chain surface for content that gets written into a user's
  repository. Revisit only with signing and an offline cache.
- **Markdown-with-frontmatter per rule** (matching the skills/agents idiom) —
  rejected: rules are queried and filtered programmatically and diffed across
  versions; JSON is the better fit. Consistency of idiom lost to fitness for
  purpose.
- **Semver for the catalog** — rejected: `2026.08` communicates freshness, which
  is the entire value proposition. `1.4.2` communicates nothing about currency.
