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
| Something in the setup seems broken, or you inherited this project | `/kaizen:doctor` | The only skill that assumes the config may be invalid: hooks pointing at missing scripts, misspelled hook events, stale settings keys, a gitignored lock |
| kaizen or its standards catalog released a new version | `/kaizen:upgrade` | Adopts the new templates **without overwriting your edits** — plans first, writes nothing until you say `apply` |

## The four workflows

### Quick iteration (small fix, no PR yet)

```
edit code → /kaizen:preflight → fix HOLD/BLOCK → commit
```

### Standard task close (feature, before PR)

```
edit code → /kaizen:finish → review report → fix issues → commit + push + PR
```

### Keeping the config current (when kaizen releases)

```
/kaizen:doctor       # is anything broken or stale?
/kaizen:upgrade      # what would change? nothing is written
/kaizen:upgrade apply
git diff -- CLAUDE.md .claude/     # review what it did
```

Your edits survive: files you never touched are replaced, files you customised
are 3-way merged, files you deleted stay deleted, and genuine collisions are
shown rather than resolved for you.

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
- **Commit `.claude/kaizen/lock.json` and `.claude/kaizen/baseline/`**, like `package-lock.json`. They are how `/kaizen:upgrade` knows what it generated versus what you changed — for you and for everyone else on the repo. The reports and plans beside them are transient and stay ignored.
- **A convention with no `<!-- ID -->` comment is yours**, not kaizen's. `/kaizen:analyze` never judges it against the catalog, and `/kaizen:upgrade` never merges it away.
