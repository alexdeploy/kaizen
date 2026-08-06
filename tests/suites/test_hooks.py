"""Hook wiring.

kaizen's documented invariant today is "29 stubs, zero active hooks". That is a
choice, not an accident, and the harness holds it: a stub must stay a no-op, a
wired hook must point at a real executable script, and hooks.json.example must
stay in sync with the scripts directory.

When hooks start getting implemented, the ACTIVE_HOOKS list below is the one
place to declare it — which forces the implementer to also wire hooks.json.
"""

import json
import os
import subprocess

import kzparse as P

# Scripts that are intentionally not stubs.
NON_STUB_SCRIPTS = {"subagent-statusline.sh"}

# Hook scripts that are implemented and wired in hooks.json. Adding one here is
# the deliberate act that lets it ship: the suite refuses to run stub checks
# against it, and demands hooks.json reference nothing outside this set.
ACTIVE_HOOKS = {"pre-tool-use.sh", "session-start.sh", "stop.sh"}

STUB_MARKERS = ("hook stub", "no-op stub")


def run(r):
    example_path = os.path.join(P.HOOKS_DIR, "hooks.json.example")
    live_path = os.path.join(P.HOOKS_DIR, "hooks.json")

    r.check(os.path.isfile(example_path), "hooks.json.example exists")

    try:
        example = P.read_json(example_path)
        r.ok("hooks.json.example is valid JSON")
    except ValueError as exc:
        r.fail("hooks.json.example is not valid JSON", exc)
        return

    referenced = _commands(example)
    r.check(len(referenced) > 0, "hooks.json.example wires at least one script")

    scripts_on_disk = set(
        name for name in os.listdir(P.HOOK_SCRIPTS_DIR) if name.endswith(".sh")
    )

    # --- every referenced command resolves to a real script ---------------
    referenced_names = set()
    for command in sorted(referenced):
        path = command.replace("${CLAUDE_PLUGIN_ROOT}", P.PLUGIN_ROOT)
        referenced_names.add(os.path.basename(path))
        r.check(
            os.path.isfile(path),
            "hooks.json.example command exists (%s)" % os.path.basename(path),
            command,
        )

    # --- and every script is either wired in the example or excluded ------
    orphans = sorted(scripts_on_disk - referenced_names - NON_STUB_SCRIPTS)
    r.check(
        not orphans,
        "every hook script appears in hooks.json.example",
        "not wired anywhere: %s" % ", ".join(orphans),
    )

    # --- stubs stay no-ops ------------------------------------------------
    for name in sorted(scripts_on_disk - NON_STUB_SCRIPTS):
        path = os.path.join(P.HOOK_SCRIPTS_DIR, name)
        text = P.read(path)
        label = "hooks/scripts/%s" % name

        if name in ACTIVE_HOOKS:
            r.ok("%s is declared active — stub checks skipped" % label)
            continue

        r.check(
            any(marker in text.lower() for marker in STUB_MARKERS),
            "%s identifies itself as a stub" % label,
        )
        r.check(
            "exit 0" in text,
            "%s exits 0 (a stub must never block a session)" % label,
        )
        # A hook that ignores stdin can break the pipe for the caller.
        r.check(
            "$(cat)" in text or "cat >" in text or "read " in text,
            "%s consumes its stdin payload" % label,
        )

        # Stubs must actually run clean, not just parse.
        proc = subprocess.run(
            [path],
            input='{"hook_event_name":"harness-smoke"}',
            capture_output=True,
            text=True,
            timeout=15,
        )
        r.check(
            proc.returncode == 0,
            "%s exits 0 when executed with a JSON payload" % label,
            (proc.stderr or "").strip(),
        )
        r.check(
            proc.stdout.strip() == "",
            "%s is silent (a stub must not inject context)" % label,
            proc.stdout.strip()[:200],
        )

    # --- a real hooks.json, if present, must be sound ---------------------
    if os.path.isfile(live_path):
        try:
            live = P.read_json(live_path)
            r.ok("hooks.json is valid JSON")
        except ValueError as exc:
            r.fail("hooks.json is not valid JSON", exc)
            return
        for command in sorted(_commands(live)):
            path = command.replace("${CLAUDE_PLUGIN_ROOT}", P.PLUGIN_ROOT)
            r.check(os.path.isfile(path), "hooks.json command exists (%s)" % command)
            r.check(
                os.access(path, os.X_OK),
                "hooks.json command is executable (%s)" % command,
            )
            r.check(
                os.path.basename(path) in ACTIVE_HOOKS,
                "hooks.json only wires scripts declared in ACTIVE_HOOKS (%s)"
                % os.path.basename(path),
                "implemented a hook? add it to ACTIVE_HOOKS in tests/suites/test_hooks.py",
            )
    else:
        r.fail(
            "hooks.json is missing but ACTIVE_HOOKS declares implemented hooks",
            "declared active: %s" % ", ".join(sorted(ACTIVE_HOOKS)),
        ) if ACTIVE_HOOKS else r.ok(
            "no hooks.json — kaizen activates zero hooks by default")


def _commands(config):
    """All `command` strings in a hooks config, at any nesting depth."""
    found = set()

    def walk(node):
        if isinstance(node, dict):
            if isinstance(node.get("command"), str):
                found.add(node["command"])
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(config)
    return found
