# Roadmap — from scaffolder to configuration package manager

> **Status: proposal.** Written 2026-08-05 against v0.12.1. This is an
> architectural argument, not a decided plan. Accept, reject or amend it; the
> committed plans live in [TODO.md](./TODO.md) and [BACKLOG.md](./BACKLOG.md).

## The ambition, stated plainly

> A user installs kaizen and can be confident that their Claude Code setup is
> current, follows the best known practices, is secure by default, and keeps
> improving itself without ever breaking what they have.

Every word of that is a technical requirement. This document takes each one
seriously and asks what the architecture must look like to deliver it.

## The gap

kaizen today is a **scaffolder**: it generates a good `.claude/` tree and offers
rituals you invoke by hand. The ambition above describes a different product —
a **package manager for Claude Code configuration**. The verbs are similar; the
architecture is not.

Three claims in the pitch that the current architecture cannot support:

### "Everything is up to date"

Best practices live as prose inside markdown templates, inside the plugin.
Updating a practice means editing a template, which means releasing a plugin
version. A user who installed v0.12 in May still holds May's opinions today,
with no signal that anything moved — because kaizen has no notion of *when* a
practice was established, *why*, or *what replaced it*.

**Standards move faster than software releases.** As long as the two are the
same artifact, "up to date" is a claim about the maintainer's free time.

### "It updates itself without breaking anything"

The only update mechanism is `--force`, which overwrites. The
`kaizen-managed: true` marker is a binary, per-file flag: it cannot distinguish
"the user changed two lines of a file kaizen wrote" from "the user rewrote it".

So the user's real choice is: lose your customizations, or freeze forever. Both
lose. This is the number one reason scaffolders get run once and abandoned.

### "The most secure practices"

The strongest security a config plugin can offer is a **safe permission
baseline**: deny rules for destructive commands, secret scanning before writes,
a considered allow list. In v0.12 that exists as an unimplemented hook stub
(`PreToolUse`, priority "high") and a short `permissions.allow` array. The claim
is currently unverifiable — and an unverifiable security claim is worse than no
claim.

## What is already right

This is not a rewrite argument. The foundations are good and should be kept:

- **The verbs.** `init / learn / analyze / preflight / plan / docs / bump /
  finish` are the right decomposition of the problem. No new ones are needed.
- **Deterministic facts, LLM reasoning.** `kaizen-detect` in bash, judgement in
  the model. Correct, and cheap.
- **The read-only contract** and the single `--auto-fix` escape hatch.
- **Proposals over mutations** — `pending.md` and its state machine are exactly
  how a tool earns permission to touch someone's config.
- **The mandatory drift report.** No silent customization.
- **The validation harness** (v0.13) — the first piece of a *proof surface*.

The problem is proportion, not direction: roughly 80% of the effort went into
*generating files* and 20% into *keeping them right*. The ambition inverts that
ratio. Generation is the commodity — Claude Code ships its own `/init`, and
every competitor scaffolds. **Maintenance over time is the moat.**

---

## P0 — without these, the pitch is false advertising

### 1. A lockfile and a real upgrade path (`/kaizen:upgrade`)

`.claude/kaizen/lock.json` records, for every file kaizen writes: the path, the
template id it came from, the standards version, the plugin version, and the
SHA-256 of exactly what kaizen produced.

On upgrade, per file:

| Situation | Detection | Behaviour |
|---|---|---|
| User never touched it | current hash == recorded hash | Replace silently, log it |
| User customized it | hashes differ | **3-way merge**: recorded output as base, new template as theirs, current file as mine. Show the conflict. Never auto-resolve |
| User deleted it | file missing | Respect the deletion. Do not resurrect |
| kaizen no longer ships it | template gone | Offer removal, never force it |

This is `package-lock.json` + `create-next-app` codemods + Terraform state,
applied to Claude Code configuration. **No plugin in this space has it.** It is
the literal technical meaning of "updates without breaking anything", and it is
the single most defensible thing kaizen could own.

It also retires `--force`, which is a destructive verb that should never have
been the answer.

### 2. Standards as versioned data, not prose in templates

Extract every convention into a catalog entry:

```yaml
id: TS-004
title: No default exports
rationale: >
  Named exports keep rename-refactors mechanical and make re-export barrels
  diffable. Default exports rename silently at the import site.
source: https://...            # docs, benchmark, or an in-repo ADR
added: 2026-03-11
severity: convention           # convention | safety | security
applies_to:
  stack: [typescript, javascript]
  maturity: [small, mature]
supersedes: TS-001
```

Templates stop being the source of truth and become **renderers over the
catalog**. Four consequences, each of which unlocks part of the ambition:

- The catalog gets **its own version** (`standards@2026.08`), released
  independently of the engine. That is how "up to date" becomes something you
  can ship weekly without touching the plugin — and how a user can pin,
  audit and upgrade their standards deliberately.
- `/kaizen:analyze` stops saying "you violated a rule" and starts saying
  "TS-004 was superseded in `standards@2026.09`; here is the replacement and
  why it changed".
- **Every rule becomes citable.** That is what turns "best practices" from a
  marketing adjective into something a team can audit — and it is the
  difference between a plugin people try and one teams adopt.
- It fixes a real defect in today's templates: they assert opinions
  ("named exports only", "no `any`") as if they were detected facts. A rule
  with a rationale and a source can be argued with. A hardcoded line cannot.

---

## P1 — what makes it feel alive, and trustworthy

### 3. The passive layer: three hooks, not twenty-nine

`PreToolUse` (block destructive bash), `Stop` (suggest `/kaizen:finish` when
files changed and it has not run), `SessionStart` (inject repo state and the
last verdict). All three are already specified in [TODO.md](./TODO.md) at
priority *high*.

Today kaizen acts only when invoked. "Continuous improvement" requires it to
watch. This is what makes the difference between a set of commands and a system.

**Ship three working hooks and delete the other twenty-six stubs.** Shipping
no-ops to users as if they were features is the fastest way to lose the trust
this project is trying to build.

### 4. `/kaizen:doctor` — compatibility with the platform

Claude Code ships new hook events, settings keys and capabilities continuously.
A config generated in May can reference a key deprecated in August. `doctor`
detects the installed Claude Code version, flags configuration that is stale or
no longer valid, and proposes the migration.

This is the *other half* of "breaks nothing": not breaking against kaizen's own
updates (the lockfile) **and** not breaking against the platform's evolution.
Nobody does this either, and for a plugin whose entire job is configuration, it
is arguably table stakes.

### 5. A security baseline that the harness asserts

A default deny list (`rm -rf` against `~` or `/`, `git push --force` to
protected branches, `curl … | sh`, `chmod -R 777`), secret scanning before
writes, and a considered allow list — **plus a test in `tests/` that asserts the
generated `settings.json` denies each pattern**.

That pairing is the whole point. A security claim backed by an executable check
is a guarantee; the same claim in a README is a wish.

---

## P2 — after the above, and cheaper because of it

- **More presets** (`go`, `rust`), now that the harness guards preset/detection
  parity and warns on every stack that falls back to `generic`.
- **Monorepo support.** Not as a preset — monorepo is a *shape*, orthogonal to
  stack. It changes *where* configuration goes (root `CLAUDE.md` plus
  per-package rules with `paths:` scoping), not what it says. Detect
  `workspaces`, `pnpm-workspace.yaml`, `turbo.json`, `nx.json` and treat it as a
  dimension of the fingerprint.
- **Configurable install.** Yes — but **not an interactive wizard**. A wizard
  does not survive a re-run, cannot be committed, and cannot run in CI. Instead:
  a `kaizen.config.json` in the project declaring which modules are wanted
  (`versioning: off`, `commit-suggester: on`). Re-runs and upgrades read it —
  which is also precisely what the lockfile needs in order to work.

---

## What to stop doing

- **Stop adding skills.** Eight verbs is already more surface than the value
  delivered. `/kaizen:ci`, `--deep`, `--dependencies` all dilute. The next
  release should add **zero** new verbs.
- **Stop the version inflation.** v0.3 → v0.12 in three days reads as churn to
  anyone evaluating adoption. Now that there is a harness behind them, make
  version numbers mean something.
- **Stop documenting intentions as capabilities.** The 29 stubs and the MCP
  integration table are shipped to users today as if they were features. One
  user checking one of them costs more trust than the table ever bought.

## The proof surface

"The most advanced plugin on the market" is not established by adjectives in a
README. It is established by things a sceptical developer can check in ninety
seconds:

1. A green CI badge, backed by a real harness. *(started — v0.13)*
2. A standards catalog where every rule carries a source and a date.
3. A public changelog with migration notes per version, and an `upgrade` command
   that honours them.
4. A `doctor` command that tells you the truth about your own setup.

Trust is manufactured by visible verification. Everything in P0 and P1 above is
chosen because it produces evidence a user can inspect, not because it adds
capability.

## Suggested sequencing

| Release | Contents |
|---|---|
| **v0.13** | Validation harness *(done)*. No new verbs. |
| **v0.14** | Lockfile + `/kaizen:upgrade` with 3-way merge. Retire `--force`. |
| **v0.15** | Standards catalog with provenance; templates become renderers. `/kaizen:analyze` reports rule deprecations. |
| **v0.16** | The three hooks + the asserted security baseline. Delete the 26 remaining stubs. |
| **v0.17** | `/kaizen:doctor`. |
| **v1.0** | Monorepo shape, `kaizen.config.json`, go/rust presets. Semver commitment starts here — which is only credible with everything above in place. |
