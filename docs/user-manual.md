# kaizen — user manual

Everything kaizen does, what each command writes, and how to recover when
something goes wrong.

For *why* things are built the way they are, see
[decisions/](./decisions/README.md). For internals, see the
[technical manual](./technical-manual.md).

**This manual tracks the `next` branch** (plugin 0.12.1 + unreleased phases,
standards catalog `2026.08`). Features marked **(unreleased)** exist on `next`
but have not shipped to the marketplace yet.

---

## What kaizen is

A Claude Code plugin that sets up your project's `.claude/` configuration, keeps
it current, and audits your code against it.

The distinction that matters: kaizen is not a one-shot scaffolder. It **records
what it wrote**, so months later it can update your config without destroying
the changes you made to it. That record is what everything else is built on.

```
  /kaizen:init        generate the config, and record what was generated
        │
        ▼
  you work, you edit CLAUDE.md, you delete a rule you disliked
        │
        ▼
  /kaizen:upgrade     adopt new templates and standards — your edits survive
  /kaizen:analyze     audit the code against the rules, by rule id
```

---

## Install

```
/plugin marketplace add alexdeploy/kaizen
/plugin install kaizen@kaizen
```

Restart Claude Code so the skills and agents load.

To run from a local checkout instead:

```bash
cd /path/to/your/project
claude --plugin-dir /path/to/kaizen/plugins/kaizen
```

### Requirements

| Needed for | Requirement |
|---|---|
| Everything | `bash`, `git` |
| The standards catalog | `python3` (macOS and most Linux ship it) |
| `/kaizen:upgrade` | `git merge-file` — part of git, nothing extra |

If `python3` is missing, kaizen degrades: it reads the catalog directly instead
of querying it. It never guesses.

---

## The commands

| Command | Writes? | What it is |
|---|---|---|
| [`/kaizen:init`](#kaizeninit) | **yes** | Generate the config for this project |
| [`/kaizen:upgrade`](#kaizenupgrade) **(unreleased)** | **yes**, only with `apply` | Adopt newer templates without losing your edits |
| [`/kaizen:learn`](#kaizenlearn) | proposes, applies on request | Propose config updates from recent commits |
| [`/kaizen:analyze`](#kaizenanalyze) | report only | Audit code against your rules, by rule id |
| [`/kaizen:plan`](#kaizenplan) | plan file only | Turn a spec into an annotated task tree |
| [`/kaizen:preflight`](#kaizenpreflight) | report only | Pre-merge gate with a SHIP/HOLD/BLOCK verdict |
| [`/kaizen:docs`](#kaizendocs) | report only | Which docs recent changes made stale |
| [`/kaizen:bump`](#kaizenbump) | report only | Suggest a semver bump |
| [`/kaizen:finish`](#kaizenfinish) | report only | The end-of-task ritual, all of the above |
| [`/kaizen:doctor`](#kaizendoctor) **(unreleased)** | report only, or `--fix` | Is this setup actually working? |

Two rules hold across all of them:

- **Nothing is written without you asking.** `init` asks before overwriting;
  `upgrade` plans before applying; everything else only writes its own report.
- **kaizen never commits.** Not after a clean upgrade, not after a SHIP verdict.

---

## `/kaizen:init`

Generates `CLAUDE.md`, `.claude/settings.json`, rules, agents and hooks, adapted
to what your project actually is.

```
/kaizen:init
/kaizen:init --profile=advanced
/kaizen:init --preset python
/kaizen:init --force
```

| Flag | Meaning |
|---|---|
| `--profile=<minimal\|standard\|advanced>` | How much workflow scaffolding. Default `standard`. |
| `--preset <name>` | Skip stack detection: `typescript-node`, `python`, `generic`. |
| `--force` | Overwrite existing config. **Prefer `/kaizen:upgrade`.** |
| `--minimal` | Only `CLAUDE.md` + settings + `.gitignore`. |

### Profiles

| Profile | Adds |
|---|---|
| `minimal` | Nothing beyond the base config |
| `standard` | A `## Workflow` section and `.claude/rules/workflow.md` |
| `advanced` | Standard + 6 more project agents, a secret-detector hook, an end-of-task ritual rule |

### If config already exists

kaizen **stops** and shows you what is there. It does not overwrite by default.
You get three options: abort, `--force` (destructive), or merge-only — write
just the files that do not exist yet. On a project with a hand-written
`CLAUDE.md`, merge-only is usually right.

### What it writes

```
CLAUDE.md
.claude/settings.json
.claude/settings.local.json.example
.claude/rules/*.md
.claude/agents/*.md
.claude/hooks/*.sh          (always chmod +x)
.claude/kaizen/lock.json    ← the record of what was generated
.claude/kaizen/baseline/    ← a copy of each generated file
.gitignore                  (appended, never replaced)
```

It never touches your source code, your `package.json`, or `.git/`.

### The drift report

Every run ends with a list of every adaptation made and why:

```
CLAUDE.md:
  ✎ Substitution: {{PROJECT_NAME}}, {{STACK_FRIENDLY}}, {{PACKAGE_MANAGER}}
  ✎ Standards [claude_md.conventions]: 5 rules from standards@2026.08 (TS-001, …)
  ✎ Enrichment [framework_stack]: Vue 3.5.22, Quasar 2.16.0, Express 5.2.1
  ✎ Conditional [no_typecheck]: removed "Typecheck" line
```

If kaizen adapted something, it says so. Read this — it is where you find out
that a command it wrote does not exist in your `package.json`.

---

## `/kaizen:upgrade` **(unreleased)**

Adopt newer kaizen templates and standards **without overwriting what you
changed**. This is what `--force` should have been.

```
/kaizen:upgrade            # plan — writes nothing
/kaizen:upgrade status     # just the lock state
/kaizen:upgrade apply      # the only mode that writes
```

### How it decides

kaizen recorded a hash of every file it generated. For each one:

| Your file | kaizen concludes | What happens |
|---|---|---|
| Identical to what it wrote | you never touched it | replaced silently |
| Different | you customised it | **3-way merged** — your edits kept |
| Missing | you deleted it | left deleted |
| Never recorded | not kaizen's | never touched |

The merge is done by `git merge-file`, not by the model. When both you and the
new template changed the *same lines*, you get asked — never overruled:

```
Conflicts (both sides changed the same lines)     1
  .claude/settings.json
    yours:   "defaultMode": "acceptEdits"
    theirs:  "defaultMode": "plan"
```

Three options per conflict: keep yours · take the new template · write the file
with conflict markers so you resolve it yourself.

### Before applying

`apply` refuses on a dirty git tree, on purpose: an upgrade you cannot
`git diff` afterwards is an upgrade you cannot review. Commit first.

Afterwards:

```
Review with:  git diff -- CLAUDE.md .claude/
Undo with:    git checkout -- CLAUDE.md .claude/
```

### If your project has no lock

Projects set up before lock tracking have nothing to compare against. kaizen
tells you so and offers two safe paths — regenerate with `--force` (last time
that is ever needed), or adopt the current files as the baseline:

```bash
kaizen-lock write --plugin-version <current> CLAUDE.md .claude/settings.json ...
```

It will never silently overwrite instead.

---

## `/kaizen:analyze`

Audits your code against the rules in your config, and tells you whether your
config itself is current.

```
/kaizen:analyze                    # all three modes
/kaizen:analyze --best-practices
/kaizen:analyze --coverage
/kaizen:analyze --architecture
/kaizen:analyze show               # re-print the last report
```

Writes only `.claude/kaizen/analyze-report.md`.

### What `--best-practices` reports

Every rule kaizen wrote carries its catalog id (`<!-- TS-003 -->`), so findings
are traceable:

```
#### [convention] TS-003 — No `any`
`src/features/parse.ts:1` (matched `export const parse = (raw: any) => raw;`)
> `any` disables checking for every expression it touches, and it spreads.
Source: TypeScript Handbook — unknown · https://www.typescriptlang.org/…
```

**Your own conventions are never judged.** A bullet with no catalog id is yours;
it is listed under "Unchecked", not measured against kaizen's rules.

**A rule you never adopted is never a violation.** Rules that apply to your
stack but are not in your config appear under "Available but not adopted".

And a `Standards status` section answers *is my config current?*:

```
| Config generated against | standards@2026.08 |
| Catalog installed        | standards@2026.09 |

- 2 rules added since your config was generated — run /kaizen:upgrade
- 1 rule in your config is deprecated
```

### Known limits, stated in the report

Checks are regular expressions, so they have no idea whether a match sits inside
a comment. Rules with known false positives carry a note, and the report prints
it. If a rule cannot be checked mechanically at all, it is listed under
"Unchecked" with the reason — never silently skipped.

---

## `/kaizen:learn`

Reads recent git activity and **proposes** updates to `CLAUDE.md` and your
rules. It never edits directly.

```
/kaizen:learn                  # analyse → write proposals
/kaizen:learn --limit=20       # how many commits to look at
/kaizen:learn --since=v1.2.0
/kaizen:learn show             # read the proposals
/kaizen:learn apply            # accept them
/kaizen:learn discard          # throw them away
```

Proposals land in `.claude/kaizen/pending.md`, which you can **edit by hand**
before applying — change the wording, delete a proposal you disagree with.

While proposals are pending, kaizen refuses to generate new ones. That is
deliberate: accumulating drafts is how config files become incoherent.

---

## `/kaizen:plan`

Turns a specification into an ordered task tree with dependencies and risks.

```
/kaizen:plan docs/spec.md
/kaizen:plan --from-prompt="add OAuth login with refresh tokens"
/kaizen:plan --from-issue=42
/kaizen:plan docs/spec.md --seed-todos    # push tasks into the todo list
/kaizen:plan list
/kaizen:plan show <plan-id>
```

Plans **accumulate** at `.claude/kaizen/plans/<slug>-<timestamp>.md` — unlike
reports, they are not overwritten, so you can compare a re-plan against the
original. PDF and DOCX specs are converted automatically when `pdftotext` or
`pandoc` is available.

---

## `/kaizen:preflight`

The pre-merge gate: deterministic checks plus two agents in parallel.

```
/kaizen:preflight
/kaizen:preflight --base=develop
/kaizen:preflight --skip=lint
/kaizen:preflight --auto-fix     # the only mode that touches your code
```

| Verdict | When |
|---|---|
| **BLOCK** | tests failed, typecheck failed, or a `critical` security finding |
| **HOLD** | lint errors or a `high` security finding |
| **SHIP** | everything else |

Checks that are skipped because the tooling is not installed **never** change
the verdict. `--auto-fix` only runs your configured formatter and linter —
kaizen itself never edits your code.

---

## `/kaizen:docs`, `/kaizen:bump`

```
/kaizen:docs         # which docs recent changes may have made stale
/kaizen:bump         # major / minor / patch, with justification
```

Both are read-only and take `--since` / `--base` / `--limit`. `bump` detects
changesets and supports JS/TS, Python and Rust manifests. Neither applies
anything: `bump` suggests, you decide.

---

## `/kaizen:finish`

The end-of-task ritual in one command: the deterministic checks, plus **four
agents in parallel** — security review, commit message, version bump, docs gaps
— into a single verdict.

```
/kaizen:finish
/kaizen:finish --skip=docs,bump
/kaizen:finish --auto-fix
```

```
╔══════════════════════════════════════════════╗
║  FINISH — HOLD                               ║
╚══════════════════════════════════════════════╝
✓ Tests          (47 passed)
✓ Typecheck      (0 errors)
⚠ Lint           (2e, 5w)
✓ Security       (No findings)
ℹ Commit msg     (feat(api): add zod validation)
ℹ Version bump   (minor: 1.2.3 → 1.3.0)
⚠ Docs           (2 medium findings — README.md, docs/api.md)
```

Bump and docs findings are **advisory** — they never block. Missing docs is your
call, not a merge blocker.

---

## `/kaizen:doctor` **(unreleased)**

Every other command assumes your configuration is valid. This one assumes it
might not be — so it is the one to run when something is wrong, or when you
inherit a project someone else set up.

```
/kaizen:doctor            # diagnose and report
/kaizen:doctor --fix      # apply only the unambiguous fixes, asking first
/kaizen:doctor --json     # raw findings, for scripting
```

### What it checks

| Area | Examples |
|---|---|
| **The platform** | settings keys that are deprecated · hook event names that are **misspelled** — the worst config bug there is, because it never fires and never errors |
| **References** | hooks and status lines pointing at scripts that do not exist, or that are not executable |
| **Your config** | unparseable `settings.json`, an unsubstituted `{{PLACEHOLDER}}` still in `CLAUDE.md`, rules with no `paths:`, agents with no frontmatter |
| **The lock** | missing, gitignored (so useless to your team), or missing baseline snapshots |
| **Standards** | your config was generated against an older catalog than the one installed |
| **Environment** | `git`, `python3`, `jq`, and what degrades without each |

### Three severities, and the third one matters

```
kaizen doctor · WARNINGS

  Problems (1)
    ✗ `SessionStart` hook points at a file that does not exist
      Claude Code reports an error on every session start until this is fixed.
      → restore the script, or remove the hook block

  Worth knowing (1)
    ! CLAUDE.md is 340 lines
      → move path-specific guidance into .claude/rules/

  Not recognised (1)
    · `someFutureKey` in .claude/settings.json
      Not in kaizen's registry. That is not an error — it may be newer than
      kaizen, or specific to your setup.
```

kaizen's registry of valid settings keys **cannot be complete**, so a key it does
not know is reported as *unfamiliar*, never as invalid. A doctor that cries wolf
the day Claude Code adds a key would be worse than no doctor.

### `--fix` is deliberately narrow

It applies only changes with exactly one correct outcome, one at a time, asking
first: `chmod +x` a hook, repair the `.gitignore` so the lock is committed, align
an agent's declared name to its filename, add a `paths:` block (**asking you for
the globs** — it never guesses).

Everything else stays a recommendation. Restoring a missing hook script means
deciding whether you want that hook; splitting a long `CLAUDE.md` is an editorial
call about your own conventions.

## What kaizen does without being asked

Three hooks run automatically once the plugin is enabled. Everything else kaizen
does requires you to type a command.

### A safety net on Bash commands

Before any shell command runs, kaizen checks it against a very short list of
things that are catastrophic and never legitimate, and **blocks** those:

```
kaizen safety: refusing to run this command.

  rm -rf /

This deletes the filesystem root or your entire home directory.
```

The bar for that list is deliberately extreme: a pattern is only there if no
real task could match it. `rm -rf node_modules`, `rm -rf dist`,
`rm -rf ~/projects/app/build`, `git clean -fd`, `chmod -R 755 ./bin` all run
normally. What gets blocked:

| Blocked | Why |
|---|---|
| `rm -rf /`, `rm -rf ~`, `rm -rf $HOME` | deletes the filesystem root or your home directory |
| `curl … \| sh`, `wget … \| bash` | runs an unreviewed remote script that can change between runs |
| `chmod -R 777 /` or `~` | makes root or home world-writable |
| `git clean -x…` | deletes ignored files too, including `.env` and local credentials |

A second, softer tier **warns without blocking**: force-push without
`--force-with-lease`, `git reset --hard`, `npm publish`.

Turn it off for a session with `KAIZEN_SAFETY=off`. It is a safety net, not a
sandbox — a sufficiently indirect command will get through, and kaizen does not
pretend otherwise.

### An oriented session start

At session start kaizen injects a few lines so Claude does not spend tool calls
rediscovering them — and stays completely silent when there is nothing to say:

```
kaizen:
- branch `feature/oauth`, 4 uncommitted file(s)
- last SHIP verdict is stale — source changed since it ran
- config was generated against standards@2026.07, catalog is now 2026.08 — `/kaizen:upgrade` to see what changed
```

### One nudge, once

When source files have changed and no pre-merge check has run since, kaizen
suggests `/kaizen:finish` — **once per session**, never repeatedly, and never
when a fresh verdict already exists. Turn it off with `KAIZEN_NUDGE=off`.

It writes nothing into your project to track this.

### The permission baseline

`/kaizen:init` writes a `deny` list into `.claude/settings.json` — secrets stay
unreadable (`.env`, `secrets/`, `*.pem`, `id_rsa*`, `.ssh/`, `.aws/`), `sudo` and
the catastrophic deletes are refused — plus an `ask` list for `git push`,
`git reset --hard` and `git rebase`.

This overlaps the hook on purpose. The hook protects any project with kaizen
enabled; the deny list protects *this* project even with the plugin disabled.

Notably absent: `Bash(rm -rf *)`. It was there, and it blocked
`rm -rf node_modules` — a deny rule that stops real work gets the whole list
deleted by the first person it annoys.

### The hooks written into your project

`/kaizen:init` also writes hooks that are yours to edit:

| Hook | Does |
|---|---|
| `format-on-save.sh` | runs your formatter on files Claude edits |
| `secret-detector.sh` | **blocks** a write containing a likely secret (AWS key, GitHub PAT, JWT, PEM private key, credential assignment) |
| `session-start.sh` | project-level session context |
| `statusline.sh` | the status line at the bottom of the TUI |
| `dependency-changed.sh` | notices when a manifest changes |

To dismiss a secret-detector false positive, add `# noqa: secret` on the same
line, or name the file `*.env.example`.

## Files kaizen creates

```
.claude/kaizen/
├── lock.json              what was generated  ← COMMIT THIS
├── baseline/              a copy of each generated file  ← COMMIT THIS
├── pending.md             /learn proposals
├── analyze-report.md      /analyze
├── preflight-report.md    /preflight
├── finish-report.md       /finish
├── docs-report.md         /docs
├── bump-report.md         /bump
└── plans/                 /plan (accumulates)
```

**Commit `lock.json` and `baseline/`**, like `package-lock.json`. They are how
`/kaizen:upgrade` works, for you and for everyone on your team. The generated
`.gitignore` section does this for you: it ignores `.claude/kaizen/*` and then
un-ignores those two.

The reports are transient. Delete them freely.

---

## The standards catalog

The rules kaizen writes into your config are versioned data, not prose baked
into a template. Every rule carries its reasoning:

```bash
kaizen-standards show TS-003
kaizen-standards list --stack typescript --maturity mature
kaizen-standards version
```

```json
{
  "id": "TS-003",
  "statement": "**No `any`.** Use `unknown` and narrow.",
  "rationale": "`any` disables checking for every expression it touches…",
  "sources": [{ "label": "TypeScript Handbook — unknown", "url": "…" }],
  "added": "2026-08-05",
  "severity": "convention"
}
```

The catalog is versioned separately from the plugin (`2026.08` — calendar
versioning, because freshness is the point), so practices can update without
waiting for a plugin release.

**If you disagree with a rule**, that is a feature: read its rationale and its
source, then delete the line from your `CLAUDE.md`. `/kaizen:upgrade` will not
put it back — a deletion is a decision.

---

## Troubleshooting

**"kaizen detected the wrong stack."** Run `kaizen-detect` to see the raw
fingerprint. In a monorepo it scans every workspace member, not just the root.
Override with `--preset <name>`.

**"A generated command does not exist in my project."** Read the drift report —
kaizen removes commands it can detect are missing (`no_lint`, `no_format`,
`no_typecheck`), but only from the root manifest. In a workspace, per-package
scripts get annotated rather than invented.

**"`/kaizen:upgrade` says there is no lock."** Your config predates lock
tracking. Adopt it with `kaizen-lock write` (see above) rather than regenerating.

**"analyze reports a violation inside a comment."** A known limit of regex
checks; the rule's note says so. Report it as a finding about the catalog, not
about your code.

**"I want to see what kaizen would do without it doing anything."**
`/kaizen:upgrade` with no argument, and every read-only skill, write nothing but
their own report.

**"Undo everything the last command did."**

```bash
git diff -- CLAUDE.md .claude/       # see it
git checkout -- CLAUDE.md .claude/   # undo it
```

kaizen never commits, so `git checkout` is always available.

---

## What kaizen will never do

- Write outside your project directory.
- Modify your source code (except your own formatter, via `--auto-fix`).
- Touch `package.json` or any dependency manifest.
- Commit, push, or create branches.
- Overwrite a file you edited without merging.
- Resurrect a file you deleted.
- Resolve a merge conflict on your behalf.
