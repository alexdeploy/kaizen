"""Agent contracts, for both plugin-level and project-level (template) agents.

The invariant that matters most: an agent documented as read-only must not be
handed a tool that can write. That promise appears in kaizen's docs, the
skills' reports, and the agent bodies themselves — here it is enforced.
"""

import os
import re

import kzparse as P

REQUIRED_KEYS = ["name", "description", "tools"]
WRITING_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}

READ_ONLY_MARKERS = (
    "read-only",
    "never edits",
    "never modifies",
    "never writes",
    "do not edit",
)

# Project-level agents /kaizen:init writes are re-writable by `--force`, which
# is only safe while they carry the ownership marker.
MANAGED_MARKER = "kaizen-managed:"


def run(r):
    models = set(P.config("allowed-models.json")["models"])
    plugin_agents = P.agent_files()
    r.check(len(plugin_agents) > 0, "plugin ships at least one agent")

    for name, path in plugin_agents:
        _check_agent(r, "agents/%s" % name, name, path, models, require_model=True)

    project_agents = P.project_agent_files()
    r.check(len(project_agents) > 0, "init templates ship project-level agents")

    for name, path in project_agents:
        label = "templates/_shared/agents/%s" % name
        _check_agent(r, label, name, path, models, require_model=False)

        body = P.read(path)
        r.check(
            MANAGED_MARKER in body,
            "%s carries the kaizen-managed ownership marker" % label,
        )


def _check_agent(r, label, filename, path, models, require_model):
    fm, body = P.parse_frontmatter(path)

    if not r.check(bool(fm), "%s has parseable frontmatter" % label, P.rel(path)):
        return

    for key in REQUIRED_KEYS:
        r.check(key in fm, "%s frontmatter has `%s`" % (label, key))

    r.check(
        fm.get("name") == filename,
        "%s frontmatter name matches its filename" % label,
        "name=%s file=%s.md" % (fm.get("name"), filename),
    )

    description = fm.get("description", "")
    r.check(len(description) > 0, "%s has a description" % label)
    # Descriptions drive auto-invocation; a bare name teaches Claude nothing.
    r.check_warn(
        len(description) > 40 or "KAIZEN_ENRICH" in description,
        "%s description is specific enough to route on" % label,
        description,
    )

    tools = set(P.tool_names(fm.get("tools", "")))
    r.check(len(tools) > 0, "%s declares tools" % label)

    if require_model:
        model = fm.get("model", "")
        r.check(len(model) > 0, "%s declares a model" % label)
        r.check_warn(
            model in models,
            "%s model is in the current allowlist" % label,
            "declares %s; allowlist: %s"
            % (model, ", ".join(sorted(models))),
        )

    haystack = (description + "\n" + body).lower()
    if any(marker in haystack for marker in READ_ONLY_MARKERS):
        offenders = sorted(WRITING_TOOLS.intersection(tools))
        r.check(
            not offenders,
            "%s is documented read-only and holds no writing tool" % label,
            "declares: %s" % ", ".join(offenders),
        )

    # Unbounded Bash defeats the point of a scoped tool list — but only for the
    # plugin's own analyst agents. Project-level agents (test-writer,
    # refactor-helper...) legitimately need to run whatever the project uses.
    raw_tools = P.csv_list(fm.get("tools", ""))
    if require_model and "Bash" in raw_tools and not any(
        t.startswith("Bash(") for t in raw_tools
    ):
        r.warn(
            "%s declares unscoped Bash" % label,
            "prefer Bash(<cmd> *) entries so the agent cannot run arbitrary commands",
        )
