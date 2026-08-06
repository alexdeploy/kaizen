# kaizen — technical manual

How the whole thing works, as one system.

[architecture.md](./architecture.md) documents each skill in depth, section by
section, in the order they were built. This document is the view that one
cannot give: what the components are, what data flows between them, which
invariants hold everywhere, and where to make a change.

Audience: anyone extending kaizen, reviewing it, or picking it up after a gap.
Read [decisions/](./decisions/README.md) before changing anything structural —
several restrictions that look arbitrary are load-bearing.

---

## 1. What kaizen is made of

```
plugins/kaizen/
├── bin/                    deterministic executables — facts, never judgement
│   ├── kaizen-detect       bash   · project fingerprint → JSON
│   ├── kaizen-lock         bash   · what was generated; hashing and 3-way merge
│   └── kaizen-standards    py3    · query and render the rule catalog
├── standards/              the rule catalog — versioned data with provenance
│   ├── index.json          version, surfaces, severities, check types
│   ├── universal.json      UNI-*
│   ├── typescript.json     TS-*
│   └── python.json         PY-*
├── skills/<name>/SKILL.md  the prompts — judgement, never arithmetic
│   └── init/templates/     what gets written into user projects
├── agents/*.md             subagent definitions used by preflight/plan/finish
└── hooks/scripts/*.sh      29 stubs, all no-ops, none wired
```

Roughly: **~3.000 lines of prompt, ~800 lines of deterministic script, ~1.100
lines of rule data.** The prompts do the reasoning; the scripts do everything a
model would get wrong.

### The dividing line

The single most important design rule in the project:

| Work | Owner | Why |
|---|---|---|
| Traversing files, hashing, globbing | script | a model burns tokens and can hallucinate a file list |
| Merging two versions of a file | `git merge-file` | a model merging by hand produces **plausible-looking corruption** |
| Filtering and ordering rules | script | deterministic output, or every upgrade shows phantom changes |
| Which preset, what a rule means, is this finding real | model | genuinely requires judgement |
| Resolving a merge conflict | **the user** | kaizen has no standing to overrule a deliberate change |

Every time this line has been crossed, it produced a bug. See
[ADR-0003](./decisions/0003-delegate-merging-to-git.md) and
[ADR-0006](./decisions/0006-python-for-structured-runtime-scripts.md).

---

## 2. The three artifacts

Everything kaizen knows about a project lives in three places.

### The fingerprint — `kaizen-detect`, transient

Recomputed on every invocation, never stored.

```json
{
  "project_name": "slabiq",
  "stack": "backend-node,frontend,typescript",
  "package_manager": "pnpm",
  "maturity": "mature",
  "workspaces": { "type": "pnpm", "packages": ["backend", "frontend"], "count": 2 },
  "git": { "is_repo": true, "commits": 8, "branch": "main" },
  "existing_claude_config": "CLAUDE.md,settings.json,rules/",
  "tests_found": 2,
  "ci": "github-actions",
  "cwd": "/…"
}
```

`stack` is scanned from the root manifest **and every workspace member** — a
monorepo keeps its dependencies in the members, so root-only scanning reports
the wrong stack ([ADR-0007](./decisions/0007-monorepo-is-a-shape.md)). A
monorepo is a *shape*: it changes **where** config goes, never **what** it says.

### The catalog — `standards/`, versioned independently

```json
{
  "id": "TS-003",
  "statement": "**No `any`.** Use `unknown` and narrow.",
  "rationale": "…",
  "sources": [{ "label": "…", "url": "…" }],
  "added": "2026-08-05",
  "severity": "convention",
  "status": "active",
  "refines": null,
  "applies_to": { "stack": ["typescript"], "maturity": ["scaffold","small","mature"] },
  "surface": "claude_md.conventions",
  "check": { "type": "grep", "pattern": ": any\\b|\\bas any\\b",
             "include": ["*.ts"], "exclude": ["**/node_modules/**", "*.d.ts"] }
}
```

The `check` living **inside the rule** is the point: before v0.14 the statement
was in a template and the check was in `analyze/SKILL.md`, joined by substring
matching, so rewording a rule silently disabled its verification
([ADR-0008](./decisions/0008-analyze-reports-by-rule-id.md)).

Calendar versioning (`2026.08`) because the value being claimed is *freshness*
([ADR-0005](./decisions/0005-standards-as-versioned-data.md)).

### The lock — `.claude/kaizen/`, committed

```
lock.json          hashes + plugin/standards version + profile + preset + placeholders
baseline/<path>    a verbatim copy of every generated file
```

The hash answers *did the user change this?*. The baseline answers the harder
question — *changed from what?* — without which there is no merge base and
therefore no merge ([ADR-0002](./decisions/0002-configuration-lock.md)).

`placeholders` records the values `{{PACKAGE_MANAGER}}` and friends resolved to,
so an upgrade re-renders with **those** rather than with fresh detection. A
project generated with `npm` that later grows a `pnpm-lock.yaml` must not have
every command line rewritten as a side effect of a template change.

---

## 3. Data flow

```
                        ┌──────────────────┐
                        │  kaizen-detect   │ fingerprint
                        └────────┬─────────┘
                                 │ stack, maturity, workspaces, project_name
        ┌────────────────────────┼────────────────────────┐
        ▼                        ▼                        ▼
┌───────────────┐      ┌──────────────────┐     ┌──────────────────┐
│  templates/   │◀─────│ kaizen-standards │────▶│  /kaizen:analyze │
│  + markers    │ render  render / checks       │  checks by id    │
└───────┬───────┘      └──────────────────┘     └────────┬─────────┘
        │ /kaizen:init                                    │
        ▼                                                 ▼
┌────────────────────────────┐                  ┌────────────────────┐
│  the user's project        │                  │ analyze-report.md  │
│  CLAUDE.md, .claude/…      │                  └────────────────────┘
└───────┬────────────────────┘
        │ kaizen-lock write  (hashes + baselines + placeholders)
        ▼
┌────────────────────────────┐
│  .claude/kaizen/lock.json  │──┐
│  .claude/kaizen/baseline/  │  │ kaizen-lock status → unchanged|modified|deleted
└────────────────────────────┘  │
                                ▼
                    ┌───────────────────────┐
                    │   /kaizen:upgrade     │
                    │   git merge-file      │
                    └───────────────────────┘
```

The loop closes: `init` records what it wrote, `upgrade` reads that record to
update safely, `analyze` reads the same record to say whether the config is
current.

---

## 4. How a template becomes a file

Three mechanisms, deliberately different in how much freedom they give the model.

| Mechanism | Looks like | Model's freedom |
|---|---|---|
| **Placeholder** | `{{PACKAGE_MANAGER}}` | none — substitute the detected value |
| **Standards marker** | `<!-- KAIZEN_STANDARDS:claude_md.conventions -->` | none — paste `kaizen-standards render` verbatim |
| **Enrichment directive** | `<!-- KAIZEN_ENRICH:framework_stack -->` | bounded — generate per a registry entry, max N bullets |
| **Conditional removal** | (no marker) | none — a named rule in a table, each logged |

Everything outside those four is **rigid**: verbatim template text. If the model
wants to improve something not covered, the rule is to report it as a suggestion,
never to write it.

Both registries — placeholders and enrichment directives — are **parsed out of
`init/SKILL.md` by the harness** and checked against the templates in both
directions. Documentation and templates cannot drift apart silently; they can
only fail a check.

### Rendering a surface

```
kaizen-standards render --surface claude_md.conventions \
                        --stack backend-node,frontend,typescript \
                        --maturity mature
```

```markdown
- **Named exports only.** No default exports. <!-- TS-001 -->
- **No `any`.** Use `unknown` and narrow. <!-- TS-003 -->
```

Deterministic ordering: domain order from `index.json`, then by id. An unstable
order would make every upgrade show phantom changes for files nobody touched.

**Refinement**: a stack-specific rule may `refine` a general one, which is then
suppressed. A TypeScript project is told "throw `Error` subclasses" once, not
that plus the vaguer universal version.

**Exit 1 means no rule applies** — an unknown stack, or a project too young for
a rule's `maturity`. The caller falls back to the template's placeholder rather
than shipping an empty section.

---

## 5. Upgrade mechanics

```
kaizen-lock status
        │
        ├── unchanged  → render today's template → differs? replace silently
        ├── modified   → kaizen-lock merge <path> <newly rendered>
        │                     └── git merge-file --diff3
        │                            exit 0  → clean       → apply
        │                            exit >0 → conflicts   → ask the user
        │                            exit 3  → no baseline → show a plain diff
        ├── deleted    → leave deleted
        └── not in the lock → never touched
```

`kaizen-lock merge` writes the result to a **temp file outside the project** and
reports the conflict count as JSON. Planning never writes.

The plan must show substance, not filenames:

```
Auto-merge (your edits + new template, no overlap)    1
  CLAUDE.md
    + your "NEVER call the billing API…" rule kept
    + new "Stack" section added
```

A plan the user cannot evaluate is a plan they approve blindly, which defeats
the purpose.

---

## 6. Invariants

These hold across every skill. Breaking one is a bug regardless of what else the
change achieves.

**Ownership**
- A file not in the lock is not kaizen's. Never touched, even at a path kaizen
  would normally generate.
- A file the user deleted stays deleted.
- A convention with no catalog id belongs to the user. Never judged, never
  merged away, never claimed.

**Writing**
- Read-only skills write exactly one file: their own report.
- `init` and `upgrade` write config; `upgrade` only under `apply`.
- Nothing is ever written outside `$CLAUDE_PROJECT_DIR`.
- kaizen never commits, and never touches dependency manifests or source code.

**Honesty**
- Every adaptation appears in the drift report.
- Rules that cannot be checked mechanically are listed as unchecked, with the
  reason — never silently skipped.
- Checks with known false positives carry a note, and the note gets printed.
- A rule the project never adopted is a gap, never a violation.

**Determinism**
- Hashing, merging, filtering and ordering are done by scripts.
- Rendering the same inputs twice produces byte-identical output.
- An upgrade re-renders from recorded values, not fresh detection.

---

## 7. The harness

```bash
tests/run.sh              # ~1.800 checks, ~2s, no dependencies
tests/run.sh --live       # real sessions, real tokens, opt-in
```

Ten deterministic suites — `manifests`, `skills`, `agents`, `references`,
`templates`, `scripts`, `hooks`, `detect`, `lock`, `standards` — plus five live
scenarios. Full detail in [validation.md](./validation.md).

Two properties worth preserving:

- **Parse the source of truth; never copy it.** Registries are read from the
  files that own them. A check needing a hardcoded list puts it in
  `tests/config/` with a comment naming its owner.
- **`warn` is a distinct severity**, never fails the build. It carries known
  gaps out of the maintainer's head into every run. A warning that cannot be
  fixed or silenced by a specific edit is a bug in the harness.

### Live evals

`seed-project.sh` builds the "generated by an older kaizen, then edited by a
human" state deterministically — so a live session is spent only on the skill
under test, never on setting the stage. A session that cannot complete (quota,
auth, network) exits **3, inconclusive** — never 1. Infrastructure failure is not
product failure.

---

## 8. Where to make a change

| You want to… | Touch | Also |
|---|---|---|
| Add or change a rule | `standards/<domain>.json` | bump `standards_version`; the harness checks schema, provenance and ripgrep compatibility |
| Support a new stack | `kaizen-detect` + `tests/config/stack-presets.json` + a preset dir | add a fixture with a golden |
| Change what a template says | `templates/…` | if it is a rule, it belongs in the catalog instead |
| Change how a skill behaves | `skills/<name>/SKILL.md` | add a check; consider a live eval |
| Add a placeholder or directive | `init/SKILL.md` registry **and** a template | the harness checks both directions |
| Change the detect output shape | `kaizen-detect` | **every fixture golden** — deliberately expensive |
| Implement a hook | `hooks/scripts/<event>.sh` + a real `hooks.json` | add it to `ACTIVE_HOOKS` in the hooks suite |

Two working agreements:

- **The fix and the check that would have caught it go in the same commit.**
- **Every structural decision gets an ADR** before or with the code.

---

## 9. Known gaps

Reported by the harness on every run, deliberately visible:

| Gap | Effect |
|---|---|
| Six stacks (`go`, `rust`, `java`, `ruby`, `php`, `elixir`) detected but fall back to the `generic` preset | detection promises more adaptation than the templates deliver |
| 17 of 31 rules have no source | they are opinions, not sourced practice — [ADR-0005](./decisions/0005-standards-as-versioned-data.md) says a rule with a source can be argued with |
| `detect_maturity` counts only source extensions | a prose/shell repo reports `maturity: "empty"` — kaizen's own repo included |
| `{{HAS_CI}}` and `{{STACK_RAW}}` documented but unused | dead registry entries |
| 29 hook stubs, none wired | shipped as templates, do nothing |

Plus, from [HANDOFF.md](../HANDOFF.md), what is built but **not yet verified
live** — that list is the honest one, and it should be read before trusting any
claim here.

---

## 10. Reading order

Coming to this project cold:

1. [ROADMAP.md](../ROADMAP.md) — why kaizen is becoming a configuration package
   manager rather than a scaffolder.
2. [decisions/](./decisions/README.md) — nine ADRs, each with the alternatives
   that lost and the costs accepted.
3. This document.
4. [architecture.md](./architecture.md) — per-skill depth.
5. [validation.md](./validation.md) — what the harness can and cannot prove.
6. [HANDOFF.md](../HANDOFF.md) — the current state, including what is unverified.
