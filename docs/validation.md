# Validation — how kaizen proves it still works

> Operational reference (how to run it, how to add a fixture, every suite in a
> table) lives in [`tests/README.md`](../tests/README.md). This document is the
> *why*: what problem the harness solves, what it can and cannot prove, and
> where it sits in the release process.

## The problem

kaizen is made almost entirely of prompts. `SKILL.md` files, agent definitions
and markdown templates — plus one bash script and a statusline. There is no
compiler, no type checker, no stack trace.

That has a specific consequence: **a regression in kaizen does not look like a
crash. It looks like slightly worse output, in somebody else's project, weeks
later.** A renamed agent that no skill dispatches. A template placeholder with
no directive telling Claude how to fill it, shipping a literal `{{TEST_RUNNER}}`
into a user's `CLAUDE.md`. A hook stub that stops being silent and starts
injecting text into every turn. None of these fail loudly. All of them are
mechanically detectable.

Before v0.13 the only defence was a maintainer re-reading the diff. The
CHANGELOG entry for v0.12.1 says the bug was found by a "deterministic test
suite run post-release" — that suite was a one-off, run by hand, never
committed, and by definition could not run again. The harness is that idea made
permanent.

## What it does and does not prove

|  | Deterministic suites | Live evals |
|---|---|---|
| **Question answered** | Is the plugin internally consistent? | Does Claude, given these prompts, do what they promise? |
| **Method** | Parse and cross-check every shipped file; run `kaizen-detect` against fixture repos | Run real headless sessions in throwaway copies of fixtures; assert on the files that land |
| **Cost** | ~0.5s, no dependencies, no tokens | Minutes and tokens per scenario |
| **Runs** | Every push (CI) and before every commit | Opt-in, before a release |
| **Cannot prove** | That the prompts produce good output | That output is good in *every* repo — it samples, it does not verify |

Being explicit about that second row matters. The harness raises the floor; it
does not certify the ceiling. A green run means *nothing known-broken ships* —
not that a skill gives excellent advice.

## Design decisions worth keeping

**1. Parse the source of truth; never copy it.**
The placeholder registry and the enrichment-directive registry are read out of
[`init/SKILL.md`](../plugins/kaizen/skills/init/SKILL.md) itself. The harness
then checks templates against them in *both* directions. The result: docs and
templates cannot silently drift apart, and they cannot both be updated to the
same wrong value by a copy-paste. If a check ever needs a hardcoded list, that
list belongs in `tests/config/` as data with a comment explaining who owns it.

**2. `warn` is not a weaker `fail`; it is a different statement.**
- `fail` — a broken invariant. Exits 1, breaks CI.
- `warn` — known drift, deliberately tolerated. Never fails the build.

Warnings carry the project's known gaps out of the maintainer's head and into
every single run. The current ten are all real: six stacks that `kaizen-detect`
identifies but that fall back to the `generic` preset, two placeholders that are
documented but unused, one encoded limitation in `detect_maturity`, and
shellcheck being absent locally. **A warning that cannot be fixed or silenced by
a specific edit is a bug in the harness** — it trains people to ignore the list.

**3. Encoded limitations, not hidden ones.**
The `docs-only` fixture asserts that a repo made of prose and shell scripts
reports `maturity: "empty"`, because `detect_maturity` counts only source
extensions. That is wrong behaviour — kaizen's own repo detects as empty. It is
recorded as a passing golden plus a `_note` that surfaces as a warning, so the
limitation is *visible on every run* instead of living in someone's memory. When
`detect_maturity` is fixed, the golden and the note change in the same commit.

**4. Infrastructure failure is not product failure.**
If a live session cannot complete — quota, auth, network — the run exits **3
(INCONCLUSIVE)**, not 1. Nothing was proven broken and nothing was proven
correct. Conflating the two is how teams learn to ignore a red build.

**5. Fixtures are copied before use.**
Every fixture is copied to a temp directory and given its own git history before
`kaizen-detect` runs, so the surrounding kaizen repo's state can never leak into
a golden result. This is why `tests/fixtures/*/` can safely contain a
`CLAUDE.md` and a `.claude/` tree.

## Where it sits in the release process

```
edit a SKILL.md / template / agent
          │
          ▼
    tests/run.sh                    ← seconds, free. Must be green.
          │
          ▼
    commit + push  ──▶  GitHub Actions runs the same command
          │
          ▼
  before tagging a release:
    tests/run.sh --live             ← real sessions, real files, real cost
          │
          ▼
    bump plugin.json + marketplace.json + README + CHANGELOG
          │
          ▼
    tests/run.sh                    ← the manifests suite catches the one you forgot
```

That last step is not hypothetical: the first run of the harness found that
`README.md` announced v0.12.0 while the plugin shipped 0.12.1.

## What the live layer asserts

Behaviour that no amount of static analysis can reach:

- `CLAUDE.md` and `.claude/settings.json` exist, and the settings parse.
- **No `{{PLACEHOLDER}}` and no `KAIZEN_ENRICH:` marker survived into the user's
  project.** The single highest-value assertion in the whole harness: it is the
  most likely visible failure, and it is invisible statically because a marker
  is an HTML comment.
- `CLAUDE.md` respects the ~200-line budget the template itself states.
- Every generated hook is executable — `/kaizen:init` promises to `chmod +x`.
- The profile produced the right shape (`advanced` → 7 agents + a workflow rule).
- Nothing unexpected appeared at the project root, per the boundary contract in
  [architecture.md](./architecture.md#boundaries).
- The run printed the drift report that `init/SKILL.md` makes mandatory.

## Extending it

Adding a check is three lines of Python and should be the default reflex when
fixing a bug: **the fix and the check that would have caught it belong in the
same commit.** See [`tests/README.md`](../tests/README.md#extending-the-deterministic-layer).

Two rules of thumb:

- If a bug could have been caught by reading files, it belongs in a
  deterministic suite — never in a live eval. Live evals are for behaviour only.
- If a check needs a list of "things we know about" (planned skills, active
  hooks, allowed model ids), that list goes in one named place with a comment,
  so updating it is an explicit decision rather than a silent edit.
