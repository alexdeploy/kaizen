# Using MCP servers with kaizen

This doc covers the MCP servers kaizen recommends, what each adds, how to enable them, and where they integrate with kaizen skills.

**Official MCP docs**: https://code.claude.com/docs/en/mcp

## What MCP is, briefly

The **Model Context Protocol** lets Claude Code talk to external services (GitHub, browsers, databases, monitoring tools, etc.) through a standardized interface. An **MCP server** runs as a subprocess; Claude Code starts it on session begin and routes tool calls to it.

You enable an MCP server by listing it in either:

| File | Scope |
|---|---|
| `<project-root>/.mcp.json` | Project-scoped — shared with the team via git |
| `~/.claude.json` (under `mcpServers`) | Personal — applies across all your projects |

The kaizen plugin ships **no active MCP servers** in v0.10 (see `plugins/kaizen/.mcp.json` — intentionally empty). Recommendations live in `plugins/kaizen/.mcp.json.example`. You opt in per project.

---

## The recommended MCPs

### `github` — read/write GitHub (high priority)

**What it provides**: tools to list/read/create GitHub issues, PRs, comments, files, search across repos.

**Why kaizen recommends it**:
- `/kaizen:plan --from-issue=<N>` already needs GitHub access. v0.10 uses the `gh` CLI; with this MCP the integration becomes richer (read comments, related issues, labels).
- v0.11+ may add a `/kaizen:finish --open-pr` flag that opens a PR with the suggested commit message + plan reference. That needs MCP.
- `/kaizen:analyze --dependencies` (planned) could use this MCP to check `npm audit` advisories against the project's repo's security tab.

**Enable**:
```json
"github": {
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-github"],
  "env": { "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}" }
}
```

**Setup**:
1. Create a GitHub Personal Access Token at https://github.com/settings/tokens (scopes: `repo`, `read:org`).
2. Export `GITHUB_TOKEN` in your shell (`~/.zshrc` etc.). The MCP server reads it from env at startup.
3. Restart Claude Code.

**Verify**: `/mcp` should list `github` as connected. Ask Claude to "list open issues" — it should use the MCP tool.

---

### `playwright` — browser automation (high for web projects)

**What it provides**: tools to open URLs, click, type, screenshot, evaluate JS in a real browser.

**Why kaizen recommends it**: paired with `/kaizen:preflight` in projects with browser-testable features (Vue / React / Svelte / Astro), this enables real E2E checks beyond unit tests. v0.11+ may add a `browser-test` deterministic check to `/preflight` when this MCP is detected (auto-runs `playwright test` if a config exists).

**Enable**:
```json
"playwright": {
  "command": "npx",
  "args": ["-y", "@playwright/mcp"]
}
```

**Setup**:
1. Install Playwright browsers: `npx playwright install` (one-time per machine).
2. Restart Claude Code.

**Verify**: ask Claude to "take a screenshot of localhost:3000" while a dev server runs.

---

### `filesystem` — advanced file operations (medium priority)

**What it provides**: more granular file ops than Read/Write/Glob (recursive listings with metadata, watch/poll capabilities, chunked I/O for huge files).

**Why kaizen recommends it**: useful in large repos where the basic Read/Glob tools start to feel limited. Especially when running cross-cutting refactors — the MCP can stream-process files that don't fit in context.

**Enable**:
```json
"filesystem": {
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-filesystem", "${CLAUDE_PROJECT_DIR}"]
}
```

**Setup**: none — the server is sandboxed to `CLAUDE_PROJECT_DIR`. No auth.

**Verify**: ask Claude to "list all .ts files modified in the last week" — should use the MCP for the recursive walk.

---

### `memory` — persistent cross-session knowledge graph (medium priority)

**What it provides**: a structured graph (nodes + edges + observations) Claude can read and write across sessions. Distinct from Claude Code's built-in auto-memory (which is per-project markdown notes).

**Why kaizen recommends it**: useful for project facts that should survive `/clear` AND be queryable as structured data — e.g., "who owns module X", "what's the on-call rotation", "known flaky tests and their workarounds". The auto-memory feature is good at narrative; the memory MCP is good at structured lookup.

**Enable**:
```json
"memory": {
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-memory"]
}
```

**Setup**: none. The memory graph persists to disk in the MCP server's default location.

**Verify**: tell Claude "remember that the staging API key is rotated every 90 days". In a new session, ask "when does staging API key rotate?".

---

### `sequential-thinking` — structured multi-step reasoning (low priority)

**What it provides**: a tool that lets Claude break down a problem into explicit sequential steps with revision capability.

**Why kaizen might use it**: `/kaizen:plan` for very large specs could benefit from structured deep reasoning. v0.11+ may add `/plan --deep` that uses this MCP when present.

**Enable**:
```json
"sequential-thinking": {
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"]
}
```

**Setup**: none.

**Verify**: ask Claude to "think step by step about <hard problem>" — it should use the sequential-thinking tool.

---

## Other MCPs worth considering (not yet integrated with kaizen)

Per-project; not (yet) referenced from any kaizen skill but commonly useful:

| MCP | Use case |
|---|---|
| **sentry** | Read crash reports / issue triage |
| **linear** / **jira** | Sync tasks between TodoWrite/plan and your tracker |
| **slack** | Notify channels from hooks (e.g., `Stop` hook posts to #engineering) |
| **notion** | Read/write docs (could integrate with `/kaizen:docs` in future) |
| **postgres** / **sqlite** / **mysql** | DB-aware projects — schema lookups, query analysis |
| **brave-search** / **fetch** | Web research for `/kaizen:analyze --dependencies` (CVE lookup, etc.) |

Official list: https://github.com/modelcontextprotocol/servers

---

## How kaizen will use these (roadmap)

| Skill | MCP | Planned use |
|---|---|---|
| `/kaizen:plan` | `github` | `--from-issue=<N>` with richer issue context (labels, comments, related) |
| `/kaizen:plan` | `sequential-thinking` | Optional `--deep` mode for complex specs |
| `/kaizen:preflight` | `playwright` | New `browser-test` deterministic check when MCP + playwright config detected |
| `/kaizen:finish` | `github` | New `--open-pr` flag to create PR with suggested commit + plan link |
| `/kaizen:analyze` | `github` + web fetch | `--dependencies` mode looks up CVEs and project's security advisories |
| (any) | `memory` | Optional structured project facts beyond CLAUDE.md |

These integrations are TODO; tracked in repo-root `TODO.md` "MCP Integration" section.

---

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `/mcp` shows server as "disconnected" | Server crashed at startup — check stderr; usually missing env var or auth |
| GitHub MCP says "rate limited" | Token has too few scopes or the token is the issue's per-hour limit; use a fine-grained token |
| Playwright MCP can't open browser | `npx playwright install` hasn't run on this machine |
| Memory MCP "loses" facts | The memory file path is per-MCP-install — multiple installs don't share state |
| Tool call slow | First MCP invocation per session can be slow (subprocess startup); subsequent calls are fast |

For MCP debugging: `claude --mcp-debug` (Claude Code flag) shows server stderr in your terminal.
