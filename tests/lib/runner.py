"""Harness entrypoint. Invoked by tests/run.sh; usable directly as
`python3 tests/lib/runner.py [--verbose] [--only <suite>]`.
"""

import argparse
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TESTS_DIR = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(TESTS_DIR, "suites"))

import kzharness  # noqa: E402

# Order matters: cheapest and most foundational first, so a broken manifest is
# the first thing you read rather than the last.
SUITES = [
    "manifests",
    "skills",
    "agents",
    "references",
    "templates",
    "scripts",
    "hooks",
    "detect",
    "lock",
    "standards",
    "safety",
    "doctor",
]


def main():
    parser = argparse.ArgumentParser(description="kaizen validation harness")
    parser.add_argument(
        "--only",
        action="append",
        metavar="SUITE",
        help="run only the named suite (repeatable): %s" % ", ".join(SUITES),
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="print every passing check"
    )
    parser.add_argument(
        "--list", action="store_true", help="list suite names and exit"
    )
    args = parser.parse_args()

    if args.list:
        for name in SUITES:
            print(name)
        return 0

    unknown = sorted(set(args.only or []) - set(SUITES))
    if unknown:
        print("unknown suite(s): %s" % ", ".join(unknown), file=sys.stderr)
        print("available: %s" % ", ".join(SUITES), file=sys.stderr)
        return 2

    loaded = []
    for name in SUITES:
        module = importlib.import_module("test_%s" % name)
        loaded.append((name, module.run))

    return kzharness.run_suites(
        loaded, verbose=args.verbose, only=set(args.only) if args.only else None
    )


if __name__ == "__main__":
    sys.exit(main())
