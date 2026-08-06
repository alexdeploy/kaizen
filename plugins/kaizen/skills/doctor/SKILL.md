---
description: Diagnose this project's Claude Code configuration and the environment kaizen runs in. Finds hooks pointing at missing scripts, deprecated settings keys, misspelled hook event names that silently never fire, unsubstituted template markers, a gitignored configuration lock, standards drift, and missing tools. Read-only — reports and proposes fixes, never applies them.
disable-model-invocation: true
argument-hint: "[--fix] [--json]"
allowed-tools: Read, Glob, Grep, Bash(kaizen-doctor), Bash(kaizen-doctor *), Bash(kaizen-detect), Bash(kaizen-standards *), Bash(kaizen-lock status), Bash(claude --version), Bash(git check-ignore *), Bash(git rev-parse *), Bash(test *), Bash(ls *), Bash(cat *), Bash(chmod *), Edit
---

# /kaizen:doctor

Is this setup actually working?

Every other kaizen skill assumes the configuration is valid. This one assumes it
might not be — which makes it the only skill worth running when something is
wrong, and the reason it exists as its own command rather than a flag on
`/kaizen:analyze` (see
`docs/decisions/0010-doctor-diagnoses-the-platform.md`).

Two subjects, neither of which any other skill looks at:

- **The platform.** Claude Code ships new settings keys and hook events
  continuously. A config generated months ago can name a hook event that no
  longer exists — or, worse, one misspelled from the start, which never fires and
  never errors.
- **The environment.** Missing tools, scripts that are not executable, a
  configuration lock that is gitignored and therefore useless to the rest of the
  team.

---

## Arguments

| Arg | Meaning |
|---|---|
| *(none)* | Diagnose and report. **Writes nothing.** |
| `--json` | Print `kaizen-doctor`'s raw JSON instead of prose. For scripting. |
| `--fix` | Apply only the fixes listed as mechanically safe below, one at a time, asking first. Everything else stays a recommendation. |

---

## Protocol

### 1. Run the diagnostic

```
kaizen-doctor
```

All the checking is deterministic and belongs to the script: parsing settings,
resolving hook commands, comparing versions, measuring files. Your job starts
with its output.

**Do not re-check what it checked.** If it says a hook points at a missing file,
that is settled — do not go and Read the file to confirm. Spend your effort on
what the script cannot do: explaining what a finding means for this project, and
ordering the fixes sensibly.

If `kaizen-doctor` is unavailable, say so and fall back to reading
`.claude/settings.json` and `CLAUDE.md` directly. Report only what you can
actually verify, and label the run as degraded.

### 2. Respect the three severities

The script's severities are a contract, not a suggestion:

| Severity | Means | How to present it |
|---|---|---|
| `problem` | kaizen can **prove** this is broken | Fix it. Explain the consequence. |
| `warning` | Probably wrong, or a real cost | Recommend, with the tradeoff. |
| `info` | kaizen does **not recognise** it | Say exactly that. **Never call it invalid.** |

That last row is the one to get right. kaizen's registry cannot list everything
Claude Code accepts, so an unfamiliar settings key means *kaizen has not heard of
it* — which is different from wrong, and a doctor that confuses the two becomes
useless the day the platform ships something new.

### 3. Report

```
kaizen doctor · WARNINGS

  Claude Code 2.1.222 · compat registry 2026.08 · standards 2026.08

  Problems (2)

    ✗ `SessionStart` hook points at a file that does not exist
      .claude/hooks/session-start.sh
      Claude Code reports an error on every session start until this is fixed.
      → restore the script (`/kaizen:init` writes it), or remove the hook block

    ✗ the configuration lock is gitignored
      .gitignore ignores all of `.claude/kaizen/`
      A teammate cloning this repo cannot upgrade the config safely, because the
      record of what kaizen generated never reaches them.
      → ignore `.claude/kaizen/*`, then un-ignore `!.claude/kaizen/lock.json`
        and `!.claude/kaizen/baseline/`

  Worth knowing (1)

    ! CLAUDE.md is 340 lines
      Read into every session, so its length is a recurring cost, not a one-off.
      → move path-specific guidance into `.claude/rules/`, which loads only when
        those paths are touched

  Not recognised (1)

    · `someFutureKey` in .claude/settings.json
      Not in kaizen's registry for Claude Code 2.1.x. That is not an error — it
      may be newer than the registry, or specific to your setup.

  2 problems · 1 warning · 1 unrecognised
  Fix the two problems with: /kaizen:doctor --fix
```

Rules for the report:

- **Order by consequence, not by check.** A hook erroring on every session start
  matters more than a long `CLAUDE.md`.
- **Say what each problem costs**, in one line. "Deprecated" is not a
  consequence; "Claude Code errors on every session start" is.
- **Omit empty sections.** A healthy project gets `✓ HEALTHY`, the versions, and
  nothing else.
- **Never invent a finding** the script did not report, and never soften one it
  did.

### 4. `--fix` mode

Only these are safe to apply mechanically. Ask before each, apply one at a time,
and show what changed:

| Finding | Fix |
|---|---|
| A hook or statusLine script is not executable | `chmod +x` it |
| The lock is gitignored | Edit `.gitignore`: `.claude/kaizen/*` plus the two negations |
| A rule file has no `paths:` frontmatter | Offer to add a `paths:` block — **ask for the globs**, never guess them |
| An agent's declared `name` differs from its filename | Align the frontmatter to the filename |

Everything else is a recommendation, including:

- **A hook pointing at a missing script.** Restoring it means deciding whether
  you want that hook at all. Offer both directions, pick neither.
- **An oversized `CLAUDE.md`.** Splitting it is an editorial decision about your
  own conventions.
- **An unsubstituted template marker.** That is `/kaizen:init --force` or
  `/kaizen:upgrade` territory, not a patch.
- **Anything in the `info` tier.** There is nothing to fix.

---

## Hard rules (never violate)

- **NEVER write anything without `--fix`**, and never outside the table above.
- **NEVER present an `info` finding as a problem.** kaizen not recognising a key
  is a statement about kaizen.
- **NEVER guess a `paths:` glob** for a rule file. A wrong glob silently loads a
  rule everywhere, or nowhere.
- **NEVER re-run the deterministic checks by hand** to "verify" the script.
- **NEVER fix a missing hook script by writing a new one from memory.** That is
  `/kaizen:init`'s job, with its templates.
- **NEVER commit.**

---

## Failure modes

| Failure | Behaviour |
|---|---|
| `kaizen-doctor` not found | Degraded run: read settings and CLAUDE.md directly, report only what is verifiable, label it degraded. |
| The compat registry is missing or invalid | Stop. Without it, "unrecognised" cannot be told from "deprecated", and guessing would produce false alarms. |
| `settings.json` is unparseable | That is the headline finding — nothing else in the file can be checked, and Claude Code is loading none of it. Report it alone. |
| Not a git repo | Skip the lock-is-gitignored check; everything else still runs. |
| No `.claude/` at all | Not a failure. Report that kaizen has not been set up here and suggest `/kaizen:init`. |

---

## Why this design

1. **The only skill that assumes the config is broken.** Everything else in
   kaizen reads `CLAUDE.md` and trusts it. Doctor is the diagnostic of last
   resort, which is why it is a command a user can reach for by name rather than
   a flag they would have to remember.
2. **Three severities, and the third one is load-bearing.** Reporting an
   unfamiliar key as invalid would make kaizen wrong the day Claude Code adds
   one. `info` is how the tool stays honest about the limits of its own registry.
3. **The registry is data, versioned separately** — same reasoning as the
   standards catalog. The platform moves faster than kaizen releases.
4. **Near-miss detection on hook events.** A misspelled event name is the worst
   configuration bug available: it never fires and never complains, so the setup
   looks correct forever. An edit distance of 2 turns that silent failure into a
   named one.
5. **`--fix` is deliberately narrow.** It applies only changes with exactly one
   correct outcome. Anything requiring a decision about your project stays your
   decision — which is the same line every other kaizen skill draws.
