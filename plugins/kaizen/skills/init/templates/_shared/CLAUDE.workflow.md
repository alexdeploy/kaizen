## Workflow

This project has kaizen installed. Every skill below is read-only by default.

- `/kaizen:plan <spec>` — before starting: turn a spec into an annotated task tree.
- `/kaizen:learn` — after a chunk of work: propose CLAUDE.md / rules updates from recent commits.
- `/kaizen:analyze` — audit the code against the conventions stated here, by rule id.
- `/kaizen:preflight` — before commit/PR: tests + typecheck + lint + security + commit message.
- `/kaizen:docs` — surface documentation recent changes may have made stale.
- `/kaizen:bump` — decide whether this work warrants a semver bump.
- `/kaizen:finish` — the end-of-task ritual: all of the above, one verdict.
- `/kaizen:upgrade` — adopt newer kaizen templates and standards without losing your edits.

See [.claude/rules/workflow.md](./.claude/rules/workflow.md) for the full guide.
