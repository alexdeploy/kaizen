# Backlog

Items deliberadamente diferidos del polish loop reciente, esperando design o validación.

> Tracked here (in-repo, committed) rather than as GitHub issues so the planning context lives next to the code. Promote to GitHub issues if/when external contributors get involved.

---

## `/kaizen:learn` v0.10 — `--include-session` flag

**Goal**: extend `/learn`'s signal sources to include the current Claude Code session's conversation, capturing user corrections that never made it into commits ("don't use X", "prefer Y", "I said no to that").

**Why deferred**: needs research on **how a skill accesses prior conversation transcript inside Claude Code**. Not a trivial tool call — the skill runs in a fresh slot of the same context, but the formal API for reading prior turns is unclear. Possible approaches:
- Bash injection that reads a session log file (if Claude Code exposes one)
- An MCP server that proxies conversation access
- A new built-in tool (would require Anthropic-side support)

**Acceptance criteria**:
- `--include-session` is opt-in (off by default).
- Signal source labeling in `pending.md` header updates accordingly.
- Anti-noise: filter casual remarks from explicit corrections (heuristic or LLM-based).
- Honest degradation: if the access mechanism isn't available in the user's Claude Code version, surface that clearly and continue with git-only.

**Estimated effort**: 2-3 hours after the access mechanism is figured out (the research is the bottleneck).

---

## `/kaizen:analyze` v0.10 — `--dependencies`, `--security`, `--complexity` modes

**Goal**: extend `/analyze` beyond the v0.4 trio (`--best-practices`, `--coverage`, `--architecture`) with three more modes that audit different dimensions.

**Why deferred**: each new mode adds real-world coupling that needs robust handling:
- `--dependencies` runs `npm outdated` / `pip list --outdated` / equivalent — needs error handling for tool-not-installed, output format variance, parsing fragility, and CVE severity surfacing (via `npm audit --json` or `safety check --json`).
- `--security` overlaps with the existing `code-reviewer` agent and `preflight-security`. Need to define WHICH gaps `--security` covers that the others don't (e.g., whole-repo static patterns vs. diff-scoped, dependency CVEs vs. code patterns).
- `--complexity` needs a complexity metric. Options: cyclomatic complexity per function, lines of code per file, nesting depth. Each has tradeoffs — false positives are the enemy.

**Acceptance criteria**:
- Modes combine like the existing trio.
- `--dependencies` gracefully skips if tooling absent (consistent with v0.4 behavior).
- Report's "Suggestions" section actionable per finding.

**Estimated effort**: 2-3 hours per mode (~6-9h total). Could ship incrementally (v0.10 = `--dependencies` only; v0.11 = `--security`; v0.12 = `--complexity`).

---

## `/kaizen:preflight` v0.10 — risk-aware sizing + commit style auto-detection

**Goal**: two related improvements that reduce friction in `/preflight` without changing its contract.

### Risk-aware sizing
For very small diffs (e.g., <10 LOC, single file), reduce the security agent's invocation (skip entirely, or use a faster/cheaper model). A 3-line config tweak doesn't need a full security audit.

**Why deferred**: calibration. What's "small"? <10 LOC could miss a real injection vulnerability in a 5-line auth fix. False negatives are worse than wasted tokens. Needs careful threshold definition and an `--always-review` escape hatch.

### Commit style auto-detection
Currently `commit-suggester` always uses Conventional Commits. v0.10 would read `git log -50`, detect the dominant style (Conventional / gitmoji / plain / custom prefix patterns), and adapt the suggestion accordingly.

**Why deferred**: detection can be wrong on small/young repos (one commit, no signal) or mixed-style repos. Need a confidence threshold and a fallback to Conventional. Also: surface the detected style in the report so the user can override.

**Acceptance criteria** (combined):
- Risk-aware sizing has a clear threshold and override flag.
- Commit style detection has a confidence threshold and fallback.
- Both opt-in via flag if behavior would be surprising.

**Estimated effort**: 1-2 hours each. ~3-4 hours total.

---

## Tracking

Items here are pulled when the corresponding skill gets its next minor version bump. Closed items move to the CHANGELOG under the resolving version.
