# kaizen — documentation

Welcome. This folder documents how the kaizen plugin behaves **once it's installed and a user invokes it**. It is not a development guide for the plugin's own source code (for that, see the [repo README](../README.md)).

## Pick a doc

| You want to... | Read |
|---|---|
| Install kaizen and run `/kaizen:init` | **[user-manual.md](./user-manual.md)** |
| Understand the decision tree (what kaizen asks, when, why) | **[runtime-flow.md](./runtime-flow.md)** |
| Know what each runtime component does and how data flows | **[architecture.md](./architecture.md)** |
| Know how kaizen proves it still works before shipping | **[validation.md](./validation.md)** |

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

- **End users** (people who install the plugin to set up a project): start with [user-manual.md](./user-manual.md).
- **Reviewers / curious developers** (people who want to understand what the plugin does before installing): read [runtime-flow.md](./runtime-flow.md) for the decision flow, then [architecture.md](./architecture.md) for component detail.
- **Contributors** (people who want to extend kaizen): read everything here, then see the [repo README](../README.md) for development workflow.

## Conventions used in these docs

- File paths are clickable links relative to the repo root.
- Diagrams use [Mermaid](https://mermaid.js.org/) — they render in GitHub, VS Code (with the *Markdown Preview Mermaid Support* extension), Obsidian, and most modern markdown viewers.
- Code blocks tagged `bash` are commands you run in your shell.
- Code blocks tagged with nothing or `text` are Claude Code chat input (run inside Claude Code's prompt).

## What's documented vs what isn't

| Documented here | Not documented here |
|---|---|
| `/kaizen:init` runtime behavior | How to write your own kaizen-style plugin |
| Why the validation harness exists ([validation.md](./validation.md)) | How to run it check-by-check (see [tests/README.md](../tests/README.md)) |
| The decision tree and its branches | The plugin manifest schema (see Claude Code docs) |
| What files get generated and why | Roadmap detail (see repo [TODO](../README.md#whats-coming-next)) |
| Installation and troubleshooting | Marketplace publishing flow (see repo README) |

## Version

This documentation tracks kaizen **v0.12.0** — the "Project Ecosystem" release. `--profile=advanced` now scaffolds 6 project-level agents + 2 new hooks for Claude to auto-orchestrate during general conversation in any project. 8 skills + 6 plugin-level agents + 7 project-level agents (advanced) + profile system + visibility surface. Currently shipped commands:

- `/kaizen:init` — bootstrap (covered in detail throughout these docs)
- `/kaizen:learn` — propose CLAUDE.md updates from git activity (see [user-manual.md](./user-manual.md#kaizenlearn-arguments))
- `/kaizen:analyze` — read-only audit (best-practices / coverage / architecture). See [user-manual.md](./user-manual.md#kaizenanalyze-arguments).
- `/kaizen:preflight` — pre-merge gate (tests + typecheck + lint + security review + commit msg) with SHIP/HOLD/BLOCK verdict. See [user-manual.md](./user-manual.md#kaizenpreflight-arguments).
- `/kaizen:plan` — auto-planner from a spec doc, with multi-agent decomposition. See [user-manual.md](./user-manual.md#kaizenplan-arguments).

Plugin-level agents shipped:
- `preflight-security`, `commit-suggester` — invoked by `/kaizen:preflight`
- `plan-context`, `plan-decomposer` — invoked by `/kaizen:plan`

After v0.6.0, focus shifts to polish + new flags rather than new top-level skills.
