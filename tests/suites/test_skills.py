"""Skill contracts.

Every SKILL.md is a prompt loaded into a user's context. The frontmatter is the
only part Claude Code parses mechanically, so it has to be right; the body
conventions checked here are the ones kaizen's own docs promise.
"""

import os
import re

import kzparse as P

REQUIRED_KEYS = ["description", "disable-model-invocation", "argument-hint", "allowed-tools"]

# Description is loaded into context for every session; keep it a summary.
MAX_DESCRIPTION_CHARS = 600

# Skills documented as read-only must not carry an editing tool. Write is
# allowed everywhere because every skill writes its own report artifact.
READ_ONLY_SKILLS = {"analyze", "preflight", "plan", "docs", "bump", "finish"}
EDITING_TOOLS = {"Edit", "MultiEdit", "NotebookEdit"}


def run(r):
    skills = P.skill_files()
    r.check(len(skills) > 0, "at least one skill exists")

    documented = _skills_documented_in_readme()

    for name, path in skills:
        fm, body = P.parse_frontmatter(path)
        label = "skills/%s" % name

        if not r.check(bool(fm), "%s has parseable frontmatter" % label, P.rel(path)):
            continue

        for key in REQUIRED_KEYS:
            r.check(key in fm, "%s frontmatter has `%s`" % (label, key))

        r.check(
            fm.get("disable-model-invocation") == "true",
            "%s is user-triggered only (disable-model-invocation: true)" % label,
            "found: %s" % fm.get("disable-model-invocation"),
        )

        description = fm.get("description", "")
        r.check(
            0 < len(description) <= MAX_DESCRIPTION_CHARS,
            "%s description is present and <= %d chars" % (label, MAX_DESCRIPTION_CHARS),
            "length: %d" % len(description),
        )

        tools = P.tool_names(fm.get("allowed-tools", ""))
        r.check(len(tools) > 0, "%s declares allowed-tools" % label)

        # A skill that tells Claude to spawn agents must be allowed to.
        spawns_agents = "Task(" in body or "Task tool" in body or "subagent_type" in body
        if spawns_agents:
            r.check(
                "Task" in tools,
                "%s dispatches agents and declares the Task tool" % label,
            )

        if name in READ_ONLY_SKILLS:
            offenders = sorted(EDITING_TOOLS.intersection(tools))
            r.check(
                not offenders,
                "%s is read-only and declares no editing tool" % label,
                "declares: %s" % ", ".join(offenders),
            )

        # Behavioural guardrails live in a 'Hard rules' section by convention.
        r.check_warn(
            re.search(r"^##+\s+Hard rules", body, re.MULTILINE) is not None,
            "%s has a 'Hard rules' section" % label,
        )

        # Anything the skill promises to WRITE must stay under .claude/kaizen/.
        # Only lines phrased as a write are scanned — every skill also reads
        # .claude/rules/*, and flagging those would be noise.
        if name not in ("init", "learn"):  # these two legitimately write config
            stray = set()
            for line in body.splitlines():
                if not re.search(r"\b(write|writes|written to|always at)\b", line, re.I):
                    continue
                for artifact in re.findall(r"`(\.claude/[^`]+\.md)`", line):
                    if not artifact.startswith(".claude/kaizen/"):
                        stray.add(artifact)
            r.check(
                not stray,
                "%s only writes artifacts under .claude/kaizen/" % label,
                ", ".join(sorted(stray)),
            )

        r.check_warn(
            name in documented,
            "%s is documented in README.md" % label,
        )


def _skills_documented_in_readme():
    readme = P.read(os.path.join(P.REPO_ROOT, "README.md"))
    return set(re.findall(r"/kaizen:([a-z-]+)", readme))
