# Publishing kaizen to GitHub

> Step-by-step playbook to convert kaizen from a local-path marketplace into a public GitHub-hosted one. After this, anyone can install with `/plugin marketplace add alexruedadev/kaizen` and `/plugin install kaizen@kaizen` — no `--plugin-dir` hacks.

**Run only when `/kaizen:learn` test is validated and you're ready for v0.3.0 to be the first public version.**

---

## Prerequisites

- GitHub account: `alexruedadev` (matches what's already in `marketplace.json` and `plugin.json`).
- `gh` CLI installed and authenticated: `gh auth status` should show you logged in.
- Clean working tree in `/Users/alex/Development/projects/kaizen/` (no uncommitted changes).

## Step 1 — verify the local state is publish-ready

From `/Users/alex/Development/projects/kaizen/`:

```bash
cd /Users/alex/Development/projects/kaizen

# Confirm version is consistent across both files
grep '"version"' .claude-plugin/marketplace.json plugins/kaizen/.claude-plugin/plugin.json
# Both should show: "version": "0.3.0"

# Smoke-test the detection script one more time
./plugins/kaizen/bin/kaizen-detect

# Confirm no extra files that shouldn't be published
ls -la
```

You should see only: `.claude-plugin/`, `plugins/`, `docs/`, `README.md`, `CHANGELOG.md`, `PUBLISHING.md` (this file).

## Step 2 — initialize git and make first commit

```bash
git init
git branch -M main

# Sane defaults for the .gitignore at the repo root
cat > .gitignore <<'EOF'
.DS_Store
*.swp
*.swo
node_modules/
.idea/
.vscode/
EOF

git add .
git status   # review what you're about to commit

git commit -m "$(cat <<'EOF'
chore: initial public release v0.3.0

- /kaizen:init: project bootstrap with hybrid templates + drift report
- /kaizen:learn: git-based config evolution proposals
- Full docs: architecture, runtime-flow, user-manual
- 4 stack templates: generic, typescript-node, python, _shared
EOF
)"
```

## Step 3 — create the GitHub repo and push

```bash
# Create as public repo. If you want private, swap --public for --private.
gh repo create alexruedadev/kaizen \
  --public \
  --description "Bootstrap and continuous improvement for Claude Code projects — scaffolds .claude/, adapts to existing repos, evolves config as the project grows" \
  --homepage "https://github.com/alexruedadev/kaizen" \
  --source=. \
  --remote=origin \
  --push
```

If `gh repo create` complains about an existing remote, use:

```bash
git remote add origin git@github.com:alexruedadev/kaizen.git
git push -u origin main
```

## Step 4 — tag the release

```bash
git tag -a v0.3.0 -m "v0.3.0: /kaizen:init + /kaizen:learn"
git push origin v0.3.0

# Optional: create a GitHub Release with the changelog entry
gh release create v0.3.0 \
  --title "v0.3.0 — /kaizen:learn introduces continuous improvement" \
  --notes "$(awk '/^## \[0\.3\.0\]/,/^---$/' CHANGELOG.md | head -n -1)"
```

## Step 5 — verify install from GitHub works

In a **different** project (not kaizen itself), test the public flow:

```bash
cd /Users/alex/Development/projects/quasar-project
claude
```

Inside Claude Code:

```
/plugin marketplace remove kaizen          # remove old local-path marketplace
/plugin marketplace add alexruedadev/kaizen
/plugin install kaizen@kaizen --scope project
```

Restart Claude Code, then:

```
/kaizen:init
```

If it runs and produces the v0.3.0 drift report → published successfully.

## Step 6 — update your README install instructions

Once published, the local-path install in [README.md](./README.md) is no longer the recommended path. Update it:

```markdown
## Install

\`\`\`
/plugin marketplace add alexruedadev/kaizen
/plugin install kaizen@kaizen
\`\`\`

Then restart Claude Code.
```

Commit + push:

```bash
git add README.md
git commit -m "docs: switch install instructions to public marketplace"
git push
```

---

## Releasing future versions

Pattern for every release after v0.3.0:

1. **Make changes** + update `CHANGELOG.md` with a new `## [X.Y.Z]` section.
2. **Bump versions** in BOTH files:
   - `plugins/kaizen/.claude-plugin/plugin.json`
   - `.claude-plugin/marketplace.json`
3. **Commit**: `git commit -am "release: vX.Y.Z"`.
4. **Tag**: `git tag -a vX.Y.Z -m "vX.Y.Z: <one-line summary>"`.
5. **Push**: `git push && git push origin vX.Y.Z`.
6. **GitHub release**: `gh release create vX.Y.Z --notes "$(awk '/^## \[X\.Y\.Z\]/,/^---$/' CHANGELOG.md | head -n -1)"`.
7. Users update with `/plugin marketplace update kaizen` + restart Claude Code.

---

## Submitting to the official Anthropic marketplace (optional, later)

Once kaizen is stable and you want broader distribution, submit to the official marketplace:

- claude.ai form: https://claude.ai/settings/plugins/submit
- console form: https://platform.claude.com/plugins/submit

Recommended before submitting:
- At least one external user has tested and given feedback.
- CHANGELOG covers ≥3 versions (shows commitment, not a fly-by-night project).
- README has clear screenshots or asciinema of a `/kaizen:init` run.
- Plugin handles the most common stacks (TS, Python, plus at least one of Go/Rust).

This is **v0.5+ territory at earliest**. Don't rush it.

---

## Rollback if something goes wrong

If a published version is broken:

```bash
# Yank from your marketplace by reverting marketplace.json version
git revert HEAD          # or: edit marketplace.json back to previous version
git commit -am "revert: yank vX.Y.Z due to <reason>"
git push

# Users who already installed will keep the broken version until they:
#   /plugin marketplace update kaizen
# This pulls the reverted marketplace.json and downgrades them.
```

For tag/release cleanup:

```bash
git push --delete origin vX.Y.Z          # delete remote tag
git tag -d vX.Y.Z                         # delete local tag
gh release delete vX.Y.Z --yes           # delete the GitHub Release
```

Be cautious — destructive operations on a published artifact erode user trust. Prefer "yank by version bump" (release vX.Y.Z+1 with the fix) over "delete vX.Y.Z" whenever possible.
