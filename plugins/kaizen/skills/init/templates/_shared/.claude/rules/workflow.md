# Workflow with kaizen skills

> This project has kaizen installed. Use these skills to keep development friction low and quality high. **All are read-only by default** — none modify code without explicit opt-in.

## When to run what

| Situation | Skill | Why |
|---|---|---|
| Project setup / fresh repo | `/kaizen:init` | Bootstrap the config (this file) |
| Before starting a new task | `/kaizen:plan <spec.md>` | Decompose spec into annotated task tree |
| You finished a chunk of work, ready for next | `/kaizen:learn` | Surface CLAUDE.md/rules updates from recent commits |
| Curious if code matches stated rules | `/kaizen:analyze` | Audit code vs conventions/architecture/coverage |
| About to commit/PR | `/kaizen:preflight` | Pre-merge gate: tests + typecheck + lint + security + commit msg |
| Want to know what docs may be stale | `/kaizen:docs` | Surface README/docs gaps from recent changes |
| Decide if this work warrants a version bump | `/kaizen:bump` | Suggests semver bump with justification |
| End-of-task ritual (everything in one go) | `/kaizen:finish` | Runs preflight + bump + docs + commit suggestion, unified verdict |

## The three workflows

### Quick iteration (small fix, no PR yet)

```
edit code → /kaizen:preflight → fix HOLD/BLOCK → commit
```

### Standard task close (feature, before PR)

```
edit code → /kaizen:finish → review report → fix issues → commit + push + PR
```

### Configuration drift maintenance (weekly / per sprint)

```
/kaizen:learn        # propose CLAUDE.md updates from recent activity
/kaizen:learn show   # review
/kaizen:learn apply  # accept (or discard)

/kaizen:analyze      # audit code against current config
                     # → manually update what needs updating
```

## Hard rules around kaizen skills

- **Never use `/kaizen:preflight --auto-fix` or `/kaizen:finish --auto-fix` on a dirty git tree** unless you understand that auto-fixes will mix with your WIP edits.
- **Always review the `pending.md` from `/kaizen:learn` before `apply`** — proposed updates may not match your intent.
- **Plans from `/kaizen:plan` accumulate** at `.claude/kaizen/plans/<slug>-<timestamp>.md` — old ones don't auto-delete; clean up periodically if you don't need them.
- **The `code-reviewer` agent** in `.claude/agents/` is yours to customize. The plugin-level agents (`preflight-security`, `commit-suggester`, `versioner`, `docs-keeper`, `plan-context`, `plan-decomposer`) are NOT — they live in the plugin and update with kaizen releases.
