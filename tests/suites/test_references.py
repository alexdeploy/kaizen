"""Cross-reference integrity.

Skills name agents, docs name skills, and READMEs link to files. Every one of
those is a string that rots silently when something is renamed. This suite is
the reason a rename cannot ship half-done.
"""

import os
import re

import kzparse as P

DOC_FILES = ["README.md", "TODO.md", "BACKLOG.md", "PUBLISHING.md", "CHANGELOG.md"]

# Named in prose as a design contrast, not dispatched by any skill.
NON_DISPATCHED_AGENTS = set()

# Skills the roadmap names before they exist. Remove an entry when it ships —
# that is what turns "planned" into a checked reference.
PLANNED_SKILLS = {"ci"}

# Both spellings kaizen's skills use to name the agent they dispatch:
#   Task(subagent_type='preflight-security', ...)
#   - `subagent_type`: `preflight-security`
DISPATCH_RE = re.compile(r"subagent_type[`'\"]?\s*[:=]\s*[`'\"]([a-z-]+)[`'\"]")


def run(r):
    plugin_agents = set(name for name, _ in P.agent_files())
    project_agents = set(name for name, _ in P.project_agent_files())
    known_agents = plugin_agents | project_agents
    skill_names = set(name for name, _ in P.skill_files())

    # --- skills dispatch agents that exist -------------------------------
    # Existence is enforced on the machine-readable form only
    # (`subagent_type='x'`); prose mentions are used just to tell a genuinely
    # orphaned agent from one that is dispatched in narrative form.
    dispatched = set()
    for name, path in P.skill_files():
        body = P.read(path)
        explicit = set(DISPATCH_RE.findall(body))
        prose = set(re.findall(r"`([a-z-]+)`\s+agent", body))

        for agent in sorted(explicit):
            r.check(
                agent in known_agents,
                "skills/%s dispatches a real agent (`%s`)" % (name, agent),
                "known agents: %s" % ", ".join(sorted(known_agents)),
            )
        dispatched |= (explicit | prose) & plugin_agents

    # --- every shipped agent is actually used ----------------------------
    for agent in sorted(plugin_agents - dispatched - NON_DISPATCHED_AGENTS):
        r.warn(
            "agent `%s` is shipped but no skill dispatches it" % agent,
            "dead weight in the plugin, or a missing dispatch in a SKILL.md",
        )

    # --- skill names referenced in docs exist ----------------------------
    for doc in DOC_FILES:
        path = os.path.join(P.REPO_ROOT, doc)
        if not os.path.isfile(path):
            continue
        for referenced in sorted(set(re.findall(r"/kaizen:([a-z-]+)", P.read(path)))):
            if referenced in skill_names:
                r.ok("%s references an existing skill (/kaizen:%s)" % (doc, referenced))
            elif referenced in PLANNED_SKILLS:
                r.ok(
                    "%s references /kaizen:%s, declared planned in the harness"
                    % (doc, referenced)
                )
            else:
                r.warn(
                    "%s references /kaizen:%s, which does not exist" % (doc, referenced),
                    "ship it, fix the reference, or add it to PLANNED_SKILLS in "
                    "tests/suites/test_references.py",
                )

    # --- the user manual must know about every shipped skill --------------
    # The failure this prevents: five phases of work landed while user-manual.md
    # still described v0.12.0. Documentation drifting behind the product is the
    # exact criticism this project was started to answer.
    manual = os.path.join(P.REPO_ROOT, "docs", "user-manual.md")
    if os.path.isfile(manual):
        manual_text = P.read(manual)
        for skill in sorted(skill_names):
            r.check(
                "/kaizen:%s" % skill in manual_text,
                "docs/user-manual.md documents /kaizen:%s" % skill,
                "a shipped command absent from the manual does not exist to users",
            )
        for binary in sorted(os.listdir(os.path.join(P.PLUGIN_ROOT, "bin"))):
            r.check_warn(
                binary in manual_text or binary in P.read(
                    os.path.join(P.REPO_ROOT, "docs", "technical-manual.md")),
                "the manuals mention the `%s` executable" % binary,
            )

    # --- the workflow rule kaizen WRITES must know every command ----------
    # This file ships into user projects as their "when to run what" table. A
    # command missing from it does not exist as far as that project is concerned.
    workflow = os.path.join(P.TEMPLATES_DIR, "_shared", ".claude", "rules",
                            "workflow.md")
    if os.path.isfile(workflow):
        text = P.read(workflow)
        for skill in sorted(skill_names):
            r.check(
                "/kaizen:%s" % skill in text,
                "the generated workflow.md mentions /kaizen:%s" % skill,
                "it is the table a user reads to know what to run",
            )

    # --- every ADR is indexed --------------------------------------------
    decisions_dir = os.path.join(P.REPO_ROOT, "docs", "decisions")
    if os.path.isdir(decisions_dir):
        index = P.read(os.path.join(decisions_dir, "README.md"))
        for name in sorted(os.listdir(decisions_dir)):
            if not name.endswith(".md") or name == "README.md":
                continue
            r.check(
                name in index,
                "ADR %s appears in the decisions index" % name,
                "an unindexed decision is one nobody will find",
            )
            body = P.read(os.path.join(decisions_dir, name))
            for heading in ("## Context", "## Decision", "## Consequences"):
                r.check(
                    heading in body,
                    "%s has a `%s` section" % (name, heading),
                )

    # --- relative markdown links resolve ---------------------------------
    md_files = [os.path.join(P.REPO_ROOT, d) for d in DOC_FILES]
    md_files += sorted(P.walk_files(os.path.join(P.REPO_ROOT, "docs"), [".md"]))
    broken = []
    checked = 0
    for md in md_files:
        if not os.path.isfile(md):
            continue
        base = os.path.dirname(md)
        for target in re.findall(r"\]\((?!https?://|#|mailto:)([^)\s]+)\)", P.read(md)):
            target = target.split("#")[0]
            if not target:
                continue
            checked += 1
            if not os.path.exists(os.path.normpath(os.path.join(base, target))):
                broken.append("%s -> %s" % (P.rel(md), target))

    r.check(
        not broken,
        "all %d relative links in docs resolve" % checked,
        "\n".join(broken),
    )
