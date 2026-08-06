"""Assertions for a /kaizen:analyze --best-practices run.

Checks the two things that separate a useful audit from an argument (ADR-0008):
findings are traceable to a catalog rule with its reason, and the three
populations of conventions are not mixed.

Usage: assert_analyze.py <project> --stdout F --user-convention S
                         [--excluded-dir D] [--absent-rule ID]
"""

import argparse
import os
import re
import sys

REPORT = ".claude/kaizen/analyze-report.md"


class Result(object):
    def __init__(self):
        self.failures = []
        self.passed = 0

    def check(self, condition, message, detail=None):
        if condition:
            self.passed += 1
            print("  \033[32m✓\033[0m %s" % message)
        else:
            self.failures.append(message)
            print("  \033[31m✗\033[0m %s" % message)
            if detail:
                for line in str(detail).splitlines()[:10]:
                    print("      %s" % line)
        return bool(condition)


def read(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except (IOError, UnicodeDecodeError):
        return ""


def section(text, heading):
    """Text from a heading to the next heading of the same or higher level."""
    idx = text.find(heading)
    if idx == -1:
        return ""
    level = len(heading) - len(heading.lstrip("#"))
    nxt = re.search(r"^#{1,%d}\s" % max(level, 1), text[idx + len(heading):], re.M)
    return text[idx:idx + len(heading) + (nxt.start() if nxt else len(text))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--stdout", required=True)
    ap.add_argument("--user-convention", required=True,
                    help="distinctive text of a convention the USER wrote")
    ap.add_argument("--excluded-dir",
                    help="path segment a rule excludes; no finding may cite it")
    ap.add_argument("--absent-rule",
                    help="rule id that applies but is NOT in the config")
    args = ap.parse_args()

    project = os.path.abspath(args.project)
    report_path = os.path.join(project, REPORT)
    r = Result()

    if not r.check(os.path.isfile(report_path), "the report was written to %s" % REPORT):
        return 1
    report = read(report_path)
    combined = report + "\n" + read(args.stdout)

    # --- traceability -----------------------------------------------------
    ids = set(re.findall(r"\b([A-Z]{2,4}-\d{3})\b", report))
    r.check(bool(ids), "findings are reported by catalog rule id",
            "no rule id appears anywhere in the report")
    r.check(
        "Standards status" in report,
        "the report has a Standards status section",
        "without it the report cannot answer 'is my config current?'",
    )
    r.check(
        "http" in report,
        "at least one finding carries its source link",
    )

    # --- the three populations must not be mixed --------------------------
    violations = section(report, "### Violations")
    unchecked = section(report, "### Unchecked")
    r.check(
        args.user_convention not in violations,
        "the user's own convention is NOT reported as a catalog violation",
        "found in the Violations section — ADR-0008 population B is not "
        "kaizen's to judge",
    )
    r.check(
        args.user_convention in report,
        "the user's own convention is acknowledged somewhere in the report",
    )
    if unchecked:
        r.check(
            args.user_convention in unchecked,
            "the user's own convention is listed under Unchecked",
        )

    if args.absent_rule:
        adopted = section(report, "### Available but not adopted")
        r.check(
            args.absent_rule not in violations,
            "a rule the project never adopted is NOT reported as a violation "
            "(%s)" % args.absent_rule,
        )
        r.check(
            args.absent_rule in adopted or args.absent_rule in report,
            "the unadopted rule is surfaced as a gap (%s)" % args.absent_rule,
        )

    # --- excludes were honoured -------------------------------------------
    if args.excluded_dir:
        cited = [
            line for line in violations.splitlines()
            if args.excluded_dir in line
        ]
        r.check(
            not cited,
            "no finding cites an excluded path (%s)" % args.excluded_dir,
            "a violation inside an excluded directory destroys trust in the "
            "whole report:\n" + "\n".join(cited[:5]),
        )

    # --- read-only contract -----------------------------------------------
    r.check(
        not os.path.isdir(os.path.join(project, ".claude/kaizen/upgrade-tmp")),
        "analyze left no scratch directory behind",
    )
    claude_md = read(os.path.join(project, "CLAUDE.md"))
    r.check(
        args.user_convention in claude_md,
        "analyze did not modify CLAUDE.md",
    )

    # --- honesty ----------------------------------------------------------
    r.check(
        "unchecked" in combined.lower(),
        "the report states what it could NOT verify",
        "silently skipping unverifiable rules hides kaizen's limits",
    )

    print()
    return 1 if r.failures else 0


if __name__ == "__main__":
    sys.exit(main())
