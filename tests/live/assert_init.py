"""Assertions over what /kaizen:init actually wrote into a project.

This is the half of the harness that cannot be done statically: whether the
model followed the SKILL.md. Everything checked here is a promise kaizen's own
docs make, phrased so a failure names the broken promise.

Usage: assert_init.py <project-dir> <profile> [--stdout <file>]
"""

import argparse
import json
import os
import re
import sys

# Paths /kaizen:init is allowed to create at the project root.
# From docs/architecture.md, "Boundaries — kaizen writes".
ALLOWED_NEW_ROOT_ENTRIES = {"CLAUDE.md", ".claude", ".gitignore"}

# The template tells the user to keep CLAUDE.md under ~200 lines; a generated
# file that already blows the budget makes the instruction meaningless.
MAX_CLAUDE_MD_LINES = 200

PROFILE_EXPECTATIONS = {
    "minimal": {"agents": 1, "workflow_rule": False},
    "standard": {"agents": 1, "workflow_rule": True},
    "advanced": {"agents": 7, "workflow_rule": True},
}

PLACEHOLDER_RE = re.compile(r"\{\{[A-Z_]+\}\}")
ENRICH_RE = re.compile(r"KAIZEN_ENRICH:[a-z_]+")


class Result(object):
    def __init__(self):
        self.failures = []
        self.passed = 0

    def check(self, condition, message, detail=None):
        if condition:
            self.passed += 1
            print("  \033[32m✓\033[0m %s" % message)
        else:
            self.failures.append((message, detail))
            print("  \033[31m✗\033[0m %s" % message)
            if detail:
                for line in str(detail).splitlines()[:12]:
                    print("      %s" % line)
        return bool(condition)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("project")
    parser.add_argument("profile", choices=sorted(PROFILE_EXPECTATIONS))
    parser.add_argument("--stdout", help="file with the session transcript")
    parser.add_argument(
        "--baseline",
        help="file listing root entries that existed before the run",
    )
    args = parser.parse_args()

    project = os.path.abspath(args.project)
    expect = PROFILE_EXPECTATIONS[args.profile]
    r = Result()

    # --- the files that must exist ---------------------------------------
    claude_md = os.path.join(project, "CLAUDE.md")
    settings = os.path.join(project, ".claude", "settings.json")

    r.check(os.path.isfile(claude_md), "CLAUDE.md was created")
    r.check(os.path.isfile(settings), ".claude/settings.json was created")

    if os.path.isfile(settings):
        try:
            json.load(open(settings, encoding="utf-8"))
            r.check(True, ".claude/settings.json is valid JSON")
        except ValueError as exc:
            r.check(False, ".claude/settings.json is valid JSON", exc)

    # --- nothing unsubstituted leaked into the user's project -------------
    leaked_placeholders = []
    leaked_markers = []
    for path in _generated_files(project):
        text = _read(path)
        if text is None:
            continue
        rel = os.path.relpath(path, project)
        for hit in PLACEHOLDER_RE.findall(text):
            leaked_placeholders.append("%s: %s" % (rel, hit))
        for hit in ENRICH_RE.findall(text):
            leaked_markers.append("%s: %s" % (rel, hit))

    r.check(
        not leaked_placeholders,
        "no {{PLACEHOLDER}} survived into the generated files",
        "\n".join(sorted(set(leaked_placeholders))),
    )
    r.check(
        not leaked_markers,
        "no KAIZEN_ENRICH marker survived into the generated files",
        "\n".join(sorted(set(leaked_markers))),
    )

    # --- size budget ------------------------------------------------------
    if os.path.isfile(claude_md):
        lines = len(_read(claude_md).splitlines())
        r.check(
            lines <= MAX_CLAUDE_MD_LINES,
            "CLAUDE.md is within its %d-line budget (%d)"
            % (MAX_CLAUDE_MD_LINES, lines),
        )

    # --- hooks are runnable ----------------------------------------------
    hooks_dir = os.path.join(project, ".claude", "hooks")
    if os.path.isdir(hooks_dir):
        for name in sorted(os.listdir(hooks_dir)):
            if not name.endswith(".sh"):
                continue
            path = os.path.join(hooks_dir, name)
            r.check(
                os.access(path, os.X_OK),
                "hook .claude/hooks/%s is executable" % name,
                "/kaizen:init promises to chmod +x every hook it writes",
            )

    # --- profile shape ----------------------------------------------------
    agents_dir = os.path.join(project, ".claude", "agents")
    agents = (
        sorted(n for n in os.listdir(agents_dir) if n.endswith(".md"))
        if os.path.isdir(agents_dir)
        else []
    )
    r.check(
        len(agents) >= expect["agents"],
        "profile %s produced at least %d agent(s) (got %d)"
        % (args.profile, expect["agents"], len(agents)),
        ", ".join(agents),
    )

    if expect["workflow_rule"]:
        rules_dir = os.path.join(project, ".claude", "rules")
        rules = os.listdir(rules_dir) if os.path.isdir(rules_dir) else []
        r.check(
            any(name.startswith("workflow") for name in rules),
            "profile %s documented the workflow in .claude/rules/" % args.profile,
            "rules present: %s" % ", ".join(sorted(rules)),
        )

    # --- boundaries: nothing unexpected at the project root ---------------
    if args.baseline and os.path.isfile(args.baseline):
        before = set(_read(args.baseline).split())
        after = set(os.listdir(project))
        unexpected = sorted(after - before - ALLOWED_NEW_ROOT_ENTRIES)
        r.check(
            not unexpected,
            "no unexpected files created at the project root",
            "created: %s" % ", ".join(unexpected),
        )

    # --- the drift report is mandatory per init/SKILL.md ------------------
    if args.stdout and os.path.isfile(args.stdout):
        transcript = _read(args.stdout) or ""
        r.check(
            "drift" in transcript.lower(),
            "the run printed a drift report (mandatory in init/SKILL.md)",
        )

    print()
    return 1 if r.failures else 0


def _generated_files(project):
    for dirpath, dirnames, filenames in os.walk(project):
        dirnames[:] = [d for d in dirnames if d not in (".git", "node_modules")]
        for name in filenames:
            if name.endswith((".md", ".json", ".sh", ".yml", ".yaml")):
                yield os.path.join(dirpath, name)


def _read(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except (IOError, UnicodeDecodeError):
        return None


if __name__ == "__main__":
    sys.exit(main())
