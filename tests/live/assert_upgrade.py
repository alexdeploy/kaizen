"""Assertions for a /kaizen:upgrade run.

The promise being tested is the whole reason the lock exists: **an upgrade must
not destroy what the user changed.** Everything here is a line from
upgrade/SKILL.md's hard rules, turned into a check.

Usage:
  assert_upgrade.py <project> plan  --stdout F --before-hashes F [--user-marker S]
  assert_upgrade.py <project> apply --stdout F --before-hashes F --user-marker S
                                    [--deleted PATH] [--foreign PATH]
"""

import argparse
import hashlib
import json
import os
import sys


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


def hash_tree(root):
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in (".git", "node_modules")]
        for name in filenames:
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, root)
            try:
                with open(path, "rb") as fh:
                    out[rel] = hashlib.sha256(fh.read()).hexdigest()
            except IOError:
                pass
    return out


def read(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except (IOError, UnicodeDecodeError):
        return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("mode", choices=["plan", "apply"])
    ap.add_argument("--stdout", required=True)
    ap.add_argument("--before-hashes", required=True)
    ap.add_argument("--user-marker", help="text the user added that must survive")
    ap.add_argument("--deleted", help="path the user deleted; must stay deleted")
    ap.add_argument("--foreign", help="path kaizen never wrote; must be untouched")
    args = ap.parse_args()

    project = os.path.abspath(args.project)
    transcript = read(args.stdout)
    with open(args.before_hashes) as fh:
        before = json.load(fh)
    after = hash_tree(project)
    r = Result()

    changed = sorted(
        p for p in set(before) | set(after) if before.get(p) != after.get(p)
    )

    if args.mode == "plan":
        # The default invocation is read-only. No exceptions, no flags.
        r.check(
            not changed,
            "plan wrote nothing at all",
            "changed: %s" % ", ".join(changed[:10]),
        )
        r.check(
            "apply" in transcript.lower(),
            "plan tells the user how to apply it",
        )
        # It must have actually read the lock, not guessed.
        r.check(
            "lock" in transcript.lower() or "0.12" in transcript,
            "plan shows it consulted the lock / versions",
        )
        classified = sum(
            1 for word in ("replace", "merge", "conflict", "left alone", "unchanged")
            if word in transcript.lower()
        )
        r.check(
            classified >= 2,
            "plan classifies files rather than listing them flatly",
            "found %d of the classification words" % classified,
        )
    else:
        # THE assertion. If this fails the feature is worse than useless.
        if args.user_marker:
            surviving = [
                p for p in after
                if args.user_marker in read(os.path.join(project, p))
            ]
            r.check(
                bool(surviving),
                "the user's own edit survived the upgrade",
                "marker %r is gone from every file — THE PROMISE OF THE FEATURE"
                % args.user_marker,
            )

        if args.deleted:
            r.check(
                not os.path.exists(os.path.join(project, args.deleted)),
                "a file the user deleted was not resurrected (%s)" % args.deleted,
            )

        if args.foreign:
            rel = args.foreign
            r.check(
                before.get(rel) == after.get(rel),
                "a file kaizen never wrote was left untouched (%s)" % rel,
            )

        lock_path = os.path.join(project, ".claude/kaizen/lock.json")
        if r.check(os.path.isfile(lock_path), "the lock still exists after apply"):
            try:
                lock = json.load(open(lock_path))
                r.check(True, "the lock is still valid JSON")
                r.check(
                    len(lock.get("files", [])) > 0,
                    "the lock still records files",
                )
                plugin = json.load(open(os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    "..", "..", "plugins", "kaizen", ".claude-plugin", "plugin.json")))
                r.check(
                    lock.get("plugin_version") == plugin["version"],
                    "the lock was re-recorded at the new plugin version",
                    "lock says %s, plugin is %s"
                    % (lock.get("plugin_version"), plugin["version"]),
                )
            except ValueError as exc:
                r.check(False, "the lock is still valid JSON", exc)

        r.check(
            not os.path.isdir(os.path.join(project, ".claude/kaizen/upgrade-tmp")),
            "the scratch directory was cleaned up",
        )
        # Merge markers left in a file are a silent corruption.
        leaked = [
            p for p in after
            if p.endswith((".md", ".json", ".sh"))
            and "<<<<<<<" in read(os.path.join(project, p))
        ]
        r.check(
            not leaked,
            "no unresolved conflict markers were written into the project",
            ", ".join(leaked),
        )

    print()
    return 1 if r.failures else 0


if __name__ == "__main__":
    sys.exit(main())
