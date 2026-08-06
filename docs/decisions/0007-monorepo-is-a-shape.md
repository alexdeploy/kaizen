# ADR-0007: A monorepo is a shape, not a preset

- **Status**: accepted
- **Date**: 2026-08-06
- **Phase**: phase 3 / `next`

## Context

Running `/kaizen:init` against a real 132-file pnpm workspace exposed a failure
that had been invisible in every fixture: `kaizen-detect` read only the **root**
`package.json`. In a workspace the dependencies live in the members, so a
TypeScript monorepo with Vue on one side and Express on the other reported:

```json
{ "stack": "javascript" }
```

Before the standards catalog this was cosmetic — a slightly wrong label in a
generated file. After it, detection *filters the rules a project receives*:
`TS-003` (`No any`) declares `applies_to.stack: ["typescript"]`, so a 132-file
TypeScript codebase silently got no rule about `any`.

The open question in the project's own notes had been "does kaizen work for
monorepos?". The answer was no, and the reason was one unqualified `grep` of one
file.

## Decision

**A monorepo is a dimension of the fingerprint, orthogonal to stack** — not a
new preset and not a new stack token.

`kaizen-detect` gains:

```json
"project_name": "slabiq",
"workspaces": { "type": "pnpm", "packages": ["backend", "frontend", "…"], "count": 3 }
```

- `type`: `pnpm` | `npm` | `lerna` | `turbo` | `nx` | `cargo` | `go` | `none`,
  from `pnpm-workspace.yaml`, `workspaces` in `package.json`, `lerna.json`, or
  the presence of a task runner.
- `packages`: the globs expanded to directories that actually hold a manifest.
- Stack detection scans the root manifest **and every member**, and a member
  declaring TypeScript makes the project TypeScript.

Consumers use the shape to decide **where** things go, never **what** they say:
`architecture_layout` walks `<package>/src/*/` instead of assuming a root
`src/`; the `workspace_scripts` conditional annotates commands that only exist
in a member.

`project_name` comes from the manifest, because the directory name is whatever
the user cloned into.

## Consequences

**Easier:** correct rules for the most common shape of serious JS/TS project.
Adding per-package rule scoping later, since the package list is already in the
fingerprint. Answering "does this work for monorepos" with a fixture instead of
a guess.

**Harder:** the detect output schema grew, and every golden fixture had to be
updated — which the harness demanded, loudly and correctly. Schema changes are
now visibly expensive, which is the right price.

**Costs:**
- Reading `workspaces` out of `package.json` needs real JSON parsing, so
  `kaizen-detect` now calls `python3` when available and falls back to a `grep`
  that handles only `name`. A missing `python3` degrades to today's behaviour —
  no workspaces detected — never to a wrong answer.
- YAML parsing for `pnpm-workspace.yaml` is a deliberate minimum: the
  `packages:` list of `- 'glob'` entries. Flow-style or nested YAML yields no
  packages rather than wrong ones.
- Negated workspace globs (`!packages/legacy`) are skipped, not honoured. A
  package that should have been excluded is included. Visible in the fingerprint,
  and better than silently dropping a real package.

**Accepted limitation:** kaizen still writes **one** root `CLAUDE.md`. Per-package
rules with `paths:` scoping are the natural follow-up, and the fingerprint now
carries what that needs.

## Alternatives

- **A `monorepo` preset** — rejected: it would have to cross-multiply with every
  stack (`monorepo-typescript`, `monorepo-python`, …). Shape and stack are
  independent, and the template tree should reflect that.
- **A `monorepo` stack token** — rejected for the same reason, plus it would
  break the `applies_to.stack` semantics in the standards catalog, where tokens
  mean "this language/framework".
- **Ask the user whether it is a monorepo** — rejected: `pnpm-workspace.yaml`
  sitting in the root is not ambiguous, and questions with a detectable answer
  are friction.
- **Scan every `package.json` in the tree** — rejected: `node_modules` aside,
  an unrelated fixture or example directory would pollute the stack. The
  workspace definition is the authoritative list of what belongs.
