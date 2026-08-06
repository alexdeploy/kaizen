# Runtime flow — from a prompt to a commit

What actually happens, in order, from the moment you type something to the moment
you commit. Who runs, what they read, what they write, and who talks to whom.

The other documents cut this differently: [user-manual.md](./user-manual.md) is
per command, [architecture.md](./architecture.md) is per skill in depth,
[technical-manual.md](./technical-manual.md) is components and invariants. This
one is the timeline.

---

## 1. The whole loop

```
                        ┌──────────────────────────────┐
                        │  a project with no config    │
                        └───────────────┬──────────────┘
                                        │  /kaizen:init
                                        ▼
   ┌─────────────────────────────────────────────────────────────────────┐
   │  CLAUDE.md · .claude/{settings,rules,agents,hooks} · lock + baseline │
   └───────────────┬─────────────────────────────────────┬───────────────┘
                   │                                     │
      every session│                        every turn   │
                   ▼                                     ▼
        ┌──────────────────────┐            ┌────────────────────────┐
        │ SessionStart hook    │            │ PreToolUse hook        │
        │ branch · verdict ·   │            │ blocks the catastrophic│
        │ drift · pending      │            │ warns on the risky     │
        └──────────────────────┘            └────────────────────────┘
                   │
                   │  you and Claude do the work
                   ▼
   ┌─────────────────────────────────────────────────────────────────────┐
   │                        the work itself                              │
   │  /kaizen:plan  →  a task tree, before you start                     │
   │  project agents (test-writer, refactor-helper, …) auto-invoke        │
   └───────────────┬─────────────────────────────────────────────────────┘
                   │
                   ▼  source files changed
        ┌──────────────────────┐
        │ Stop hook            │  "…no pre-merge check has run since"
        └──────────┬───────────┘   once per session, then silent
                   │
                   ▼
   ┌─────────────────────────────────────────────────────────────────────┐
   │  closing the task                                                   │
   │  /kaizen:preflight   tests+typecheck+lint  +2 agents  → verdict      │
   │  /kaizen:finish      the same, +4 agents, one report                 │
   │  /kaizen:analyze     code vs the rules, by rule id                  │
   │  /kaizen:learn       what the commits taught → proposals             │
   └───────────────┬─────────────────────────────────────────────────────┘
                   │
                   ▼  YOU commit. kaizen never does.
   ┌─────────────────────────────────────────────────────────────────────┐
   │  time passes · kaizen releases · the catalog moves · Claude Code moves│
   └───────────────┬─────────────────────────────────┬───────────────────┘
                   │ /kaizen:upgrade                 │ /kaizen:doctor
                   ▼                                 ▼
      your edits survive a merge          is any of this still valid?
```

Everything above the `/kaizen:upgrade` line happens in a week. Everything below
it is why the lock exists.

---

## 2. What runs without you asking

Only three things. Everything else in kaizen requires a command.

| When | Hook | Decides |
|---|---|---|
| Session begins | `SessionStart` | Is there anything worth injecting? Branch, dirty count, a stale verdict, pending proposals, standards drift. **Silent if not.** |
| Before every Bash call | `PreToolUse` | Is this command catastrophic (block), risky (warn), or ordinary (silence)? |
| End of a turn | `Stop` | Did source change with no check since, and have I already said so this session? |

```
   turn ends
      │
      ▼
   source files changed?  ──no──▶ silent
      │ yes
      ▼
   already nudged this session?  ──yes──▶ silent
      │ no
      ▼
   a verdict newer than the changes?  ──yes──▶ silent
      │ no
      ▼
   "N source file(s) changed and no pre-merge check has run since."
```

Three chances to stay quiet before it says anything. That is deliberate: a hook
that speaks every turn is a hook people disable.

---

## 3. `/kaizen:init` — the decision tree

```
kaizen-detect  ──▶  { project_name, stack, package_manager, maturity,
                      workspaces, git, existing_claude_config, tests, ci }
      │
      ▼
existing_claude_config is not empty?
      │
      ├── yes, and no --force  ─────▶ STOP. Show what is there. Offer:
      │                                abort · --force (destructive) · merge-only
      │
      └── no, or --force
              │
              ▼
        maturity?
              ├── empty     ──▶ ask what this project will be
              ├── scaffold  ──▶ minimal scaffolding
              ├── small     ──▶ full scaffolding
              └── mature    ──▶ full scaffolding + offer archeology
              │
              ▼
        stack ──▶ preset          (typescript-node · python · generic)
              │
              ▼
        for each template file:
              ├── {{PLACEHOLDER}}            ──▶ substitute detected value
              ├── <!-- KAIZEN_STANDARDS:x --> ──▶ paste `kaizen-standards render` verbatim
              ├── <!-- KAIZEN_ENRICH:x -->    ──▶ generate per the registry entry
              ├── conditional rule matched    ──▶ remove/insert the named line
              └── everything else             ──▶ verbatim
              │
              ▼
        chmod +x every hook
              │
              ▼
        kaizen-lock write  ── hashes + baselines + the placeholder values used
              │
              ▼
        drift report — every adaptation, named
```

The lock write is not bookkeeping for its own sake: without it, `/kaizen:upgrade`
has nothing to compare against and the only update path is overwriting.

---

## 4. `/kaizen:upgrade` — the decision tree

```
kaizen-lock status
      │
      ├── no lock ────────▶ STOP. Offer adoption or regeneration. Never overwrite.
      │
      └── lock present
              │
              ▼
        lock version vs installed plugin
              ├── newer than installed  ──▶ STOP (you downgraded)
              ├── equal, files modified ──▶ a DRIFT report, not an upgrade
              ├── equal, nothing changed──▶ "already up to date"
              └── older ────────────────▶ continue
              │
              ▼
        render today's templates, using profile · preset · placeholders
        FROM THE LOCK (never fresh detection)
              │
              ▼
        per tracked file:
              ├── deleted    ──▶ leave deleted
              ├── unchanged  ──▶ identical? nothing.  different? safe replace
              └── modified   ──▶ kaizen-lock merge  →  git merge-file --diff3
                                       ├── clean      ──▶ apply
                                       ├── conflicts  ──▶ ASK: yours · theirs · markers
                                       └── no baseline──▶ show a plain diff, never merge
              │
              ▼
        PLAN — writes nothing at all
              │
              ▼  only on `apply`, only on a clean git tree
        write · chmod · re-record the lock · print the git diff/checkout commands
```

---

## 5. Who talks to whom

kaizen has three kinds of agent, and they never mix.

```
┌───────────────────────────────────────────────────────────────────┐
│  PLUGIN AGENTS — kaizen's own, dispatched by a skill              │
│                                                                   │
│  /kaizen:preflight ──┬──▶ preflight-security   (changed files)    │
│                      └──▶ commit-suggester     (diff range)       │
│                                                                   │
│  /kaizen:plan ───────┬──▶ plan-context         (project state)    │
│                      └──▶ plan-decomposer      (the spec only)    │
│                                                                   │
│  /kaizen:finish ─────┬──▶ preflight-security                      │
│                      ├──▶ commit-suggester      4 in parallel,    │
│                      ├──▶ versioner             one message        │
│                      └──▶ docs-keeper                             │
│                                                                   │
│  /kaizen:docs ───────────▶ docs-keeper                            │
│  /kaizen:bump ───────────▶ versioner                              │
└───────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────┐
│  PROJECT AGENTS — written into YOUR .claude/agents/, yours to edit│
│  Claude auto-invokes these in ordinary conversation, not by a     │
│  kaizen command:                                                  │
│    code-reviewer · test-writer · refactor-helper                  │
│    documentation-writer · dependency-auditor                      │
│    security-auditor · architecture-advisor                        │
└───────────────────────────────────────────────────────────────────┘
```

Three properties of that dispatch worth knowing:

- **Agents never talk to each other.** Each gets a fresh context and a prompt
  from the orchestrating skill, and returns text to it. `/kaizen:finish` is four
  independent opinions merged by the skill, not a conversation.
- **Parallel means one message with several Task calls.** Four agents cost about
  what four sequential ones cost in tokens, and about a quarter in wall-clock.
- **Synthesis happens in the skill, not in a fifth agent.** The orchestrator is
  the only thing holding every result, so merging them is its job.

---

## 6. Where the deterministic scripts fit

```
kaizen-detect      /init · /upgrade · /analyze · /doctor · SessionStart
kaizen-standards   /init (render) · /analyze (checks) · SessionStart (drift)
kaizen-lock        /init (write) · /upgrade (status, merge, write) · /doctor
kaizen-doctor      /doctor
```

Each emits JSON on stdout and decides nothing. The rule they exist to enforce:
**the model never hashes, never merges, never orders a rule list.** Every time
that line was crossed during development it produced a bug — see
[ADR-0003](./decisions/0003-delegate-merging-to-git.md).

---

## 7. Failure paths

What each stage does when things are wrong, because this is the half that decides
whether a tool is trustworthy.

| Situation | What happens |
|---|---|
| Config already exists, no `--force` | `/init` stops and offers three options. Zero bytes written — verified on a real 554-file project. |
| No lock | `/upgrade` stops with adoption instructions. **Never falls back to overwriting.** |
| No baseline for a modified file | Merge refused; a plain diff is shown instead. |
| Both sides changed the same lines | The user picks. kaizen never arbitrates. |
| `kaizen-standards` unavailable | Read the catalog JSON directly; never improvise rules from memory. |
| `python3` unavailable | Catalog and workspace parsing degrade to grep; the answer is narrower, never wrong. |
| `jq` unavailable in a generated hook | Falls back to python3, then sed. A hook that errors on every edit is worse than no hook. |
| A check pattern cannot be verified | Reported under "unchecked" with the reason. Never silently skipped. |
| Dirty tree on `/upgrade apply` | Refused: an upgrade you cannot `git diff` is one you cannot review. |
| A live session hits a quota | The eval harness exits **3, inconclusive** — never 1. Infrastructure failure is not product failure. |

---

## 8. The one thing kaizen never does

It never commits. Not after a clean upgrade, not after a SHIP verdict, not after
`--fix`. Every change it makes is sitting in your working tree, and

```bash
git diff -- CLAUDE.md .claude/
git checkout -- CLAUDE.md .claude/
```

always works.
