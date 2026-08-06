"""Shell script health.

kaizen ships scripts that run inside someone else's session — a syntax error or
a missing exec bit surfaces as a broken Claude Code session, not as a kaizen
error message. `bash -n` is free; shellcheck runs when available.
"""

import os
import subprocess
import sys

import kzparse as P

# Templates are copied into user projects and chmod'ed by /kaizen:init, but
# shipping them already executable means a manual copy works too.
REQUIRE_EXECUTABLE = True


def run(r):
    scripts = P.shell_scripts()
    r.check(len(scripts) > 0, "plugin ships shell scripts")

    has_shellcheck = _which("shellcheck")
    if not has_shellcheck:
        r.warn(
            "shellcheck not installed — static lint of shell scripts skipped",
            "brew install shellcheck / apt-get install shellcheck",
        )

    for path in scripts:
        label = P.rel(path)
        text = P.read(path)

        r.check(
            text.startswith("#!"),
            "%s has a shebang" % label,
        )
        r.check_warn(
            text.startswith("#!/usr/bin/env "),
            "%s uses a portable env shebang" % label,
            text.splitlines()[0] if text else "(empty)",
        )

        # bin/ holds both bash and Python 3 scripts (ADR-0006), so the syntax
        # check follows the shebang rather than assuming one language.
        shebang = text.splitlines()[0] if text else ""
        if "python" in shebang:
            proc = subprocess.run(
                [sys.executable, "-m", "py_compile", path],
                capture_output=True, text=True,
            )
            r.check(
                proc.returncode == 0,
                "%s parses (py_compile)" % label,
                proc.stderr.strip(),
            )
        else:
            proc = subprocess.run(
                ["bash", "-n", path], capture_output=True, text=True
            )
            r.check(
                proc.returncode == 0,
                "%s parses (bash -n)" % label,
                proc.stderr.strip(),
            )

        if REQUIRE_EXECUTABLE:
            r.check(
                os.access(path, os.X_OK),
                "%s is executable" % label,
                "chmod +x %s" % label,
            )

        if "python" not in (text.splitlines()[0] if text else ""):
            r.check_warn(
                "set -euo pipefail" in text,
                "%s sets strict mode" % label,
            )

        if has_shellcheck and "python" not in (text.splitlines()[0] if text else ""):
            proc = subprocess.run(
                ["shellcheck", "--severity=warning", "--format=gcc", path],
                capture_output=True,
                text=True,
            )
            r.check_warn(
                proc.returncode == 0,
                "%s passes shellcheck (warning+)" % label,
                proc.stdout.strip(),
            )

    # --- kaizen-detect is the one script other components parse -----------
    r.check(
        os.access(P.DETECT_BIN, os.X_OK),
        "kaizen-detect is executable (it is put on PATH by Claude Code)",
    )
    r.check(
        os.path.basename(os.path.dirname(P.DETECT_BIN)) == "bin",
        "kaizen-detect lives in bin/ so the plugin puts it on PATH",
    )


def _which(binary):
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        candidate = os.path.join(directory, binary)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return True
    return False
