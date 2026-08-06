# ADR-0006: Runtime scripts may be Python 3 when the job is structured data

- **Status**: accepted
- **Date**: 2026-08-05
- **Phase**: phase 2 / `next`

## Context

Until now every executable kaizen ships is bash: `kaizen-detect`, `kaizen-lock`,
the hooks, the statusline. That was never a stated policy, just what each job
needed — string matching and file tests, which bash does fine.

The standards catalog ([ADR-0005](./0005-standards-as-versioned-data.md))
changes the shape of the work: filtering nested JSON by stack, maturity, surface
and status, then rendering ordered markdown. Doing that in bash means either
parsing JSON with `awk` (fragile in a way that fails silently on the first
unusual value) or taking a hard dependency on `jq` (common, not universal).

## Decision

`bin/kaizen-standards` is Python 3, stdlib only. Runtime scripts pick the
language that fits the job:

- **bash** — file tests, git plumbing, hashing, invoking other tools.
- **Python 3, stdlib only** — anything that parses or emits structured data.

Every script must still: emit JSON on stdout, degrade with a clear message
rather than crashing, and be usable standalone from a terminal.

The skills that call `kaizen-standards` must handle its absence by reading the
catalog JSON directly. Graceful enhancement, not hard dependency — the same
pattern kaizen already applies to MCP servers.

## Consequences

**Easier:** correct handling of the catalog, and any future component that
queries structured data. The harness already requires Python 3, so contributors
need nothing new.

**Harder:** two languages in `bin/`. Anyone extending kaizen now has to know
which one a given script is, and the harness had to become language-aware
(dispatching `bash -n` or `py_compile` on the shebang).

**Costs:** a runtime dependency on Python 3 for one script. Judged near-zero in
practice: macOS ships `/usr/bin/python3`, Linux distributions ship python3, and
on Windows the bash scripts would need WSL or git-bash anyway — so this is not
worse than the existing floor.

**Explicitly not decided:** rewriting `kaizen-detect` or `kaizen-lock`. They do
bash-shaped work, they are tested, and churn without benefit is not a virtue.

## Alternatives

- **`jq`** — rejected: not installed by default on macOS or on many Linux
  images, and a missing `jq` would break `init` rather than degrade it.
- **Parse JSON in awk** — rejected: works until a value contains a brace, then
  fails silently. Silent failure is the one category of bug this project can
  least afford.
- **Keep the catalog in a bash-friendly format (TSV, delimited lines)** —
  rejected: rules have multi-line rationales, nested applicability and source
  lists. Flattening them into a line format trades a real dependency for a fake
  one and makes the data hostile to read.
- **Do the filtering in the model instead of a script** — rejected: filtering is
  deterministic work, and every deterministic job the model does is tokens spent
  to get a less reliable answer.
