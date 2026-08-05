"""Minimal check runner: pass / warn / fail, with a readable summary.

Deliberately not pytest — the harness must run with zero installs on a clean
machine and inside CI, and the checks are assertions about files, not unit
tests of functions.

Severity contract:
  ok()   — invariant holds
  warn() — drift worth knowing about, does NOT fail the build (exit 0)
  fail() — broken invariant, fails the build (exit 1)
"""

import os
import sys
import time

_COLOR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def _c(code, text):
    return "\033[%sm%s\033[0m" % (code, text) if _COLOR else text


GREEN = lambda t: _c("32", t)
RED = lambda t: _c("31", t)
YELLOW = lambda t: _c("33", t)
DIM = lambda t: _c("2", t)
BOLD = lambda t: _c("1", t)


class Reporter(object):
    """Collects results for one suite."""

    def __init__(self, suite, verbose=False):
        self.suite = suite
        self.verbose = verbose
        self.passed = 0
        self.warnings = []
        self.failures = []

    def ok(self, message):
        self.passed += 1
        if self.verbose:
            print("  %s %s" % (GREEN("✓"), message))

    def warn(self, message, detail=None):
        self.warnings.append((message, detail))

    def fail(self, message, detail=None):
        self.failures.append((message, detail))

    def check(self, condition, message, detail=None):
        """ok/fail in one call. Returns the condition for chaining."""
        if condition:
            self.ok(message)
        else:
            self.fail(message, detail)
        return bool(condition)

    def check_warn(self, condition, message, detail=None):
        if condition:
            self.ok(message)
        else:
            self.warn(message, detail)
        return bool(condition)


def run_suites(suites, verbose=False, only=None):
    """suites: [(name, callable(reporter))]. Returns process exit code."""
    print(BOLD("\nkaizen :: validation harness"))
    print(DIM("  %s\n" % time.strftime("%Y-%m-%d %H:%M:%S")))

    total_pass = 0
    all_warnings = []
    all_failures = []
    started = time.time()

    for name, fn in suites:
        if only and name not in only:
            continue
        reporter = Reporter(name, verbose=verbose)
        try:
            fn(reporter)
        except Exception as exc:  # a broken suite must not look like a pass
            reporter.fail(
                "suite raised %s" % type(exc).__name__, "%s" % exc
            )

        total_pass += reporter.passed
        all_warnings += [(name, m, d) for m, d in reporter.warnings]
        all_failures += [(name, m, d) for m, d in reporter.failures]

        if reporter.failures:
            mark, label = RED("✗"), RED("FAIL")
        elif reporter.warnings:
            mark, label = YELLOW("!"), YELLOW("WARN")
        else:
            mark, label = GREEN("✓"), GREEN("ok")
        print(
            "  %s %-14s %s %s"
            % (
                mark,
                name,
                label,
                DIM(
                    "%d passed, %d warn, %d failed"
                    % (reporter.passed, len(reporter.warnings), len(reporter.failures))
                ),
            )
        )

    if all_warnings:
        print(YELLOW("\n  warnings"))
        for suite, message, detail in all_warnings:
            print("    %s %s :: %s" % (YELLOW("!"), suite, message))
            if detail:
                for line in str(detail).splitlines():
                    print(DIM("        %s" % line))

    if all_failures:
        print(RED("\n  failures"))
        for suite, message, detail in all_failures:
            print("    %s %s :: %s" % (RED("✗"), suite, message))
            if detail:
                for line in str(detail).splitlines():
                    print(DIM("        %s" % line))

    elapsed = time.time() - started
    print(
        "\n  %s  %s  %s   %s\n"
        % (
            GREEN("%d passed" % total_pass),
            YELLOW("%d warnings" % len(all_warnings)),
            RED("%d failed" % len(all_failures)),
            DIM("in %.2fs" % elapsed),
        )
    )
    return 1 if all_failures else 0
