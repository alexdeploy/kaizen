# User manual

> Install kaizen, run `/kaizen:init`, get a Claude Code config tailored to your project. This manual covers v0.1.0.

For internal architecture, see [architecture.md](./architecture.md). For decision flow, see [runtime-flow.md](./runtime-flow.md).

## Requirements

- [Claude Code](https://claude.com/code) v2.1.0 or later.
- `bash`, `jq`, `find`, `git` (all standard on macOS/Linux).
- A terminal in the project you want to configure.

## Install

### Option A — local development (today)

Clone or pull the kaizen repo, then load it directly with `--plugin-dir`:

```bash
git clone https://github.com/alexruedadev/kaizen.git ~/kaizen
cd /path/to/your/project
claude --plugin-dir ~/kaizen/plugins/kaizen
```

Inside Claude Code, the skill is now available:

```
/kaizen:init
```

### Option B — marketplace (when published)

```bash
# Inside Claude Code, once:
/plugin marketplace add alexruedadev/kaizen
/plugin install kaizen@kaizen
```

Then **restart Claude Code** so the new skills load. (Some versions support `/reload-plugins` for hot reload; if your install message says "Restart Claude Code to load new plugins", do that.)

From then on, `/kaizen:init` is available in any project.

To update later:

```
/plugin marketplace update kaizen
```
Then restart Claude Code.

## Quickstart

```bash
cd /your/project
claude --plugin-dir ~/kaizen/plugins/kaizen
```

```
/kaizen:init
```

You'll see Claude run `detect.sh`, report what it found, and either generate files or ask you a question. Approve the file writes when prompted.

## Command reference

Commands shipped in v0.3.0:
- [`/kaizen:init`](#kaizeninit-arguments) — bootstrap project config
- [`/kaizen:learn`](#kaizenlearn-arguments) — propose config updates from git activity

### `/kaizen:init [arguments]` {#kaizeninit-arguments}

Bootstrap a Claude Code configuration tailored to the current project. Detects stack, package manager, project maturity, and existing config, then generates `CLAUDE.md`, `.claude/settings.json`, path-scoped rules, a code-reviewer agent, and hooks.

#### Arguments

| Argument | Meaning |
|---|---|
| *(no args)* | Auto-detect everything. Recommended for first runs. |
| `--preset <name>` | Skip auto-detection, use a named preset. Values: `generic`, `typescript-node`, `python`. |
| `--force` | Overwrite existing Claude config files. **Use only after committing or backing up.** Without this flag, kaizen will refuse to overwrite. |
| `--minimal` | Only generate `CLAUDE.md` + `.claude/settings.json` + `.gitignore` patch. Skip rules, agents, hooks. |

Combine freely: `/kaizen:init --preset python --minimal`, `/kaizen:init --force --preset typescript-node`.

#### What gets written

| File | Created by default | `--minimal` |
|---|---|---|
| `CLAUDE.md` | ✓ | ✓ |
| `.claude/settings.json` | ✓ | ✓ |
| `.claude/settings.local.json.example` | ✓ | ✗ |
| `.claude/rules/<topic>.md` (path-scoped) | ✓ (preset-dependent) | ✗ |
| `.claude/agents/code-reviewer.md` | ✓ | ✗ |
| `.claude/hooks/session-start.sh` | ✓ | ✗ |
| `.claude/hooks/format-on-save.sh` | ✓ (preset-dependent) | ✗ |
| `.gitignore` (appends a section) | ✓ | ✓ |

#### What kaizen never touches

- Anything outside your project directory (`$CLAUDE_PROJECT_DIR`).
- Your source code.
- Your `package.json`, `pyproject.toml`, or any dependency manifest.
- Your git history (no commits, no branches).
- Existing config files **without `--force`**.

## Common scenarios

### Scenario 1 — Brand new empty project

```
mkdir my-new-app && cd my-new-app
git init
claude --plugin-dir ~/kaizen/plugins/kaizen
```

```
/kaizen:init
```

kaizen sees no code and asks: "What kind of project? (typescript / python / go / other)". You pick one. It generates a minimal scaffolding plus a `CLAUDE.md` with placeholders to fill in once you have `package.json`/`pyproject.toml`.

### Scenario 2 — Adopting kaizen in an existing project

```bash
cd /existing/repo
claude --plugin-dir ~/kaizen/plugins/kaizen
```

```
/kaizen:init
```

kaizen detects your stack and maturity. If the project is **mature** (50+ source files), it offers to run **archeology mode**: an Explore subagent reads your git history and produces a `.claude/rules/lessons.md` with recurring patterns. Say `yes` to enable, `no` to skip.

### Scenario 3 — You already have `CLAUDE.md` from before

```
/kaizen:init
```

kaizen sees existing config and stops. It asks:

> I found existing Claude config: `CLAUDE.md, settings.json`. Options:
> (a) abort, (b) re-run with `--force` (overwrites), (c) merge only missing pieces

Pick `(c)` to add what's missing without touching what you already wrote. Pick `(b)` only if you want a clean reset (commit first!).

### Scenario 4 — Starting over

```bash
git add . && git commit -m "Pre-kaizen reset"
```

```
/kaizen:init --force
```

Overwrites everything. The commit is your safety net.

### Scenario 5 — You only want CLAUDE.md, nothing else

```
/kaizen:init --minimal
```

Generates just `CLAUDE.md` + `settings.json` + a `.gitignore` patch. No rules, agents, or hooks.

### Scenario 6 — Force a specific preset

```
/kaizen:init --preset typescript-node
```

Useful if detection is wrong (e.g., a polyglot monorepo where the TypeScript piece is what you want config for).

## After `/kaizen:init` finishes

You'll see a summary like:

```
✓ kaizen init complete

Detected: typescript,frontend / pnpm / small
Preset:   typescript-node

Files created:
  - CLAUDE.md (52 lines)
  - .claude/settings.json
  - .claude/rules/testing.md
  - .claude/agents/code-reviewer.md
  - .claude/hooks/session-start.sh (chmod +x done)
  - .claude/hooks/format-on-save.sh (chmod +x done)
  - .gitignore (appended 3 lines)

Suggested next steps:
  1. Review CLAUDE.md and adjust the "Commands" section
  2. Run `claude` and try the code-reviewer agent
  3. When you start writing tests, /kaizen:learn will tune rules/testing.md
```

**What to do immediately:**

1. **Review `CLAUDE.md`**. Adjust the `## Commands` section to match what your project actually runs. Delete lines for commands you don't have.
2. **Restart Claude Code** or run `/reload-plugins` so it loads the new config.
3. **Try the code-reviewer agent**: `@code-reviewer review src/`.

**Optional:**

- Copy `.claude/settings.local.json.example` → `.claude/settings.local.json` and add personal overrides (extra permissions, different model).
- Commit `CLAUDE.md` and `.claude/` (minus `settings.local.json`, which is auto-gitignored).

### `/kaizen:learn [subcommand] [flags]` {#kaizenlearn-arguments}

Analyzes recent git activity and proposes updates to `CLAUDE.md` / `.claude/rules/`. **Never modifies your config silently** — proposals are written to `.claude/kaizen/pending.md` for review.

#### Subcommands

| Subcommand | Action |
|---|---|
| *(none)* | Analyze and write up to 3 proposals to `pending.md`. Refuses if `pending.md` already exists (use `apply` or `discard` first). |
| `show` | Print the contents of `pending.md`. |
| `apply` | Apply every proposal in `pending.md` to its target file, then delete `pending.md`. |
| `discard` | Delete `pending.md` without applying. |

#### Flags

| Flag | Meaning |
|---|---|
| `--since=<git-ref>` | Analyze commits since this ref. Default: `HEAD~10`. Examples: `--since=HEAD~25`, `--since=v1.0.0`, `--since=2 weeks ago`. |

#### Typical workflow

```
# After a few days of work, see what kaizen suggests:
/kaizen:learn

# Review the proposals:
/kaizen:learn show

# Either apply them all:
/kaizen:learn apply

# ...or throw them away if not useful:
/kaizen:learn discard

# You can also EDIT pending.md by hand to refine before applying.
```

#### What gets proposed

`/kaizen:learn` looks for **patterns in recent commits not yet documented**:

- Recurring file structures (e.g., 5 new `src/services/*.ts` files but Architecture section doesn't mention `services/`).
- Recurring fix patterns (e.g., 3 commits with `fix:` for the same kind of bug → candidate for `## Never do`).
- New libraries introduced and used across files.
- Conventions emerging in new code (e.g., new files all use factory pattern).
- `CLAUDE.md` exceeding ~150 lines → proposes moving a section to `.claude/rules/`.
- Path-specific patterns → proposes new path-scoped rule file.

Maximum **3 proposals per analysis**. Each cites concrete evidence (commit SHAs, file paths, counts).

#### Where proposals live

`.claude/kaizen/pending.md`. The directory is **auto-added to `.gitignore`** the first time `/kaizen:learn` runs — pending proposals are WIP and shouldn't pollute team commits.

You can edit `pending.md` by hand before applying: tweak wording, delete a proposal, change the target section, etc.

#### Signal sources

- **v0.3 (today)**: git only — `git log` and `git diff` from the last N commits.
- **v0.4 (planned)**: optional `--include-session` flag to also analyze the current conversation for user corrections.
- **v0.5 (planned)**: optional `--include-memory` flag to read Claude's auto-memory.

See the [SKILL.md source](../plugins/kaizen/skills/learn/SKILL.md) for the full roadmap with tradeoffs.

#### Limits and safety

- **Never modifies files outside `apply`** — even in analyze mode, nothing in `CLAUDE.md` or `.claude/rules/` is touched until you explicitly `/kaizen:learn apply`.
- **Never proposes deletions** of user-written content. Only append, insert, move, or create new files.
- **Validates before applying**: if a proposal's target section no longer exists, the whole apply stops with a clear error.
- **Never auto-commits**. Changes land in your working tree; you commit when ready.

## Troubleshooting

### "Skill `/kaizen:init` not found"

The plugin isn't loaded. Either:
- You forgot `--plugin-dir <path>` when launching Claude Code.
- The path you passed doesn't contain `.claude-plugin/plugin.json`. The correct path ends in `plugins/kaizen/`, not just `kaizen/`.
- You installed the plugin from a marketplace but didn't restart Claude Code afterwards. The install message will say "Restart Claude Code to load new plugins" when restart is needed.

### `detect.sh: jq: command not found`

Install `jq`:

```bash
brew install jq          # macOS
sudo apt install jq      # Debian/Ubuntu
```

### "Permission denied" when kaizen tries to write

You're running kaizen from a directory you don't own (e.g., a system path). Run from a project you own.

### `detect.sh` output looks wrong

Run it manually to see what's happening:

```bash
bash ~/kaizen/plugins/kaizen/skills/init/scripts/detect.sh
```

If `stack` says `generic` for what should be a TypeScript project, check:
- Is there a `package.json` at the repo root? (If it's nested under `apps/`, detection misses it in v0.1.0.)
- Did you `cd` into the right directory?

Workaround until v0.2: use `--preset` to override.

### kaizen overwrote my `CLAUDE.md` even though I didn't pass `--force`

This should never happen. If it did:
1. Recover from git: `git restore CLAUDE.md`.
2. File an issue with the exact command and Claude Code version.

### The hooks don't run

Two possible causes:
- The scripts aren't executable. Check: `ls -l .claude/hooks/`. They should show `rwxr-xr-x`. Fix: `chmod +x .claude/hooks/*.sh`.
- Claude Code session started before the hooks existed. Restart Claude Code (or `/reload-plugins`).

### Hooks fire but do nothing

Check the script directly:

```bash
echo '{"tool_input":{"file_path":"./test.ts"}}' | bash .claude/hooks/format-on-save.sh
```

You should see `prettier` or `ruff` run. If not, the formatter binary isn't on `PATH`. Install it.

## FAQ

**Q: Will kaizen change my source code?**
No. It only writes to `CLAUDE.md`, `.claude/`, and appends to `.gitignore`.

**Q: Can I undo a `/kaizen:init` run?**
With `git restore` if you had a clean working tree. Without git, no — make a backup before running `--force`.

**Q: Does kaizen send my code anywhere?**
No. `detect.sh` runs locally and returns a small JSON. Claude reads template files locally. Nothing in this skill makes network calls.

**Q: What happens if my project mixes stacks?**
`detect.sh` reports a CSV like `typescript,python`. The preset picker uses the first match in priority order (`typescript-node` > `python` > `generic`). Use `--preset python` to override if the priority is wrong.

**Q: Can I customize the templates?**
Yes — clone kaizen, edit files in `plugins/kaizen/skills/init/templates/<preset>/`, point `--plugin-dir` at your fork. For permanent customization, fork and publish your own marketplace.

**Q: Does kaizen work with Windows?**
Not officially in v0. The hooks use bash scripts (`.sh`) and `jq`. WSL works. Native Windows support is planned for v0.2.

**Q: Will future kaizen commands be available?**
v0.1.0 ships only `/kaizen:init`. Planned for v0.2+:
- `/kaizen:learn` — auto-update `CLAUDE.md` with diff-review after tasks.
- `/kaizen:analyze` — deep audit (best-practices, deps, upgrades).
- `/kaizen:plan` — turn a spec doc into a task tree.
- `/kaizen:preflight` — pre-PR chain.

**Q: Should I commit the generated files?**
Yes. Commit `CLAUDE.md` and the whole `.claude/` directory **except** `settings.local.json` (auto-gitignored). Your team should share the same Claude config.

**Q: I want different config than the template provides.**
Edit the generated files directly. They're yours now. kaizen won't touch them again unless you re-run with `--force`.

## Getting help

- Architecture detail: [architecture.md](./architecture.md)
- Decision flow with diagrams: [runtime-flow.md](./runtime-flow.md)
- Issue tracker: https://github.com/alexruedadev/kaizen/issues
