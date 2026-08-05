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
