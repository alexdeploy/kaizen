# kaizen — documentation

Welcome. This folder documents how the kaizen plugin behaves **once it's installed and a user invokes it**. It is not a development guide for the plugin's own source code (for that, see the [repo README](../README.md)).

## Pick a doc

| You want to... | Read |
|---|---|
| Use kaizen: every command, flag, file and recovery path | **[user-manual.md](./user-manual.md)** |
| Understand the system as a whole: components, data flow, invariants | **[technical-manual.md](./technical-manual.md)** |
| Know *why* a decision was made, and what it cost | **[decisions/](./decisions/README.md)** |
| Go deep on one skill's runtime | **[architecture.md](./architecture.md)** |
| Know how kaizen proves it still works before shipping | **[validation.md](./validation.md)** |
| See the current state, including what is **not** verified | **[../HANDOFF.md](../HANDOFF.md)** |
| Understand where the project is heading | **[../ROADMAP.md](../ROADMAP.md)** |
| Understand the decision tree as of v0.12 (**stale**) | [runtime-flow.md](./runtime-flow.md) |

## At a glance

```
                User types /kaizen:init
                          │
                          ▼
       ┌──────────────────────────────────┐
       │  SKILL.md loaded into context    │
       │  detect.sh runs (bash injection) │
       └──────────────┬───────────────────┘
                      │ JSON fingerprint
                      ▼
       ┌──────────────────────────────────┐
       │  Claude branches on:             │
       │   • existing Claude config?      │
       │   • project maturity?            │
       │   • detected stack → preset      │
       └──────────────┬───────────────────┘
                      │
                      ▼
       ┌──────────────────────────────────┐
       │  Reads templates/_shared/        │
       │       + templates/<preset>/      │
       │  Substitutes {{PLACEHOLDERS}}    │
       └──────────────┬───────────────────┘
                      │
                      ▼
       ┌──────────────────────────────────┐
       │  Writes to user's project:       │
       │   CLAUDE.md                      │
       │   .claude/settings.json          │
       │   .claude/rules/*.md             │
       │   .claude/agents/*.md            │
       │   .claude/hooks/*.sh (chmod +x)  │
       │   .gitignore (appended)          │
       └──────────────┬───────────────────┘
                      │
                      ▼
                 ✓ summary report
```

## Audience guide

- **Using kaizen on a project** → [user-manual.md](./user-manual.md). Everything
  it does, everything it writes, and how to undo any of it.
- **Reviewing or extending it** → [technical-manual.md](./technical-manual.md)
  for the system view, then [decisions/](./decisions/README.md) for why, then
  [architecture.md](./architecture.md) for per-skill depth.
- **Picking the project up after a gap** → [../HANDOFF.md](../HANDOFF.md) first.
  It lists what is built but **not yet verified**, which no other document does.

## Conventions used in these docs

- File paths are clickable links relative to the repo root.
- Code blocks tagged `bash` are commands you run in your shell.
- Code blocks tagged with nothing or `text` are input to Claude Code's prompt.
- **(unreleased)** marks a feature that exists on the `next` branch but has not
  shipped to the marketplace.

## Version

These docs track kaizen **0.12.1 plus the unreleased `next` branch**, with the
standards catalog at **2026.08**.

| Document | State |
|---|---|
| user-manual.md · technical-manual.md · architecture.md · validation.md · decisions/ | current |
| [runtime-flow.md](./runtime-flow.md) · [mcp-usage.md](./mcp-usage.md) | **stale — describe v0.12.0.** Rewrite or delete; do not extend |

The harness enforces part of this: every shipped `/kaizen:*` command must appear
in the user manual, and every ADR must be indexed with its Context / Decision /
Consequences sections. Documentation drifting behind the product is the exact
failure this project set out to fix, so it is a build failure here.
