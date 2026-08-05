"""Golden tests for kaizen-detect.

This is the only part of kaizen with deterministic behaviour, and every skill
branches on its output: preset choice, empty-vs-mature flow, refusals. A
regression here silently changes what /kaizen:init writes into user projects.

Each fixture is a miniature repo under tests/fixtures/<name>/ plus:
  expected.json  — the exact detect output (minus `cwd`)
  fixture.json   — optional: git setup, and a `note` for encoded limitations

Fixtures are copied to a temp dir before running so the surrounding kaizen
repo's own git state can never leak into the result.
"""

import json
import os
import shutil
import subprocess
import tempfile

import kzparse as P

GIT_ENV = {
    "GIT_AUTHOR_NAME": "kaizen harness",
    "GIT_AUTHOR_EMAIL": "harness@kaizen.test",
    "GIT_COMMITTER_NAME": "kaizen harness",
    "GIT_COMMITTER_EMAIL": "harness@kaizen.test",
}


def run(r):
    fixtures = sorted(
        name
        for name in os.listdir(P.FIXTURES_DIR)
        if os.path.isdir(os.path.join(P.FIXTURES_DIR, name))
    )
    if not r.check(len(fixtures) > 0, "detect fixtures exist"):
        return

    for name in fixtures:
        _run_fixture(r, name)


def _run_fixture(r, name):
    source = os.path.join(P.FIXTURES_DIR, name)
    expected_path = os.path.join(source, "expected.json")

    if not r.check(
        os.path.isfile(expected_path), "fixture `%s` has expected.json" % name
    ):
        return

    expected = P.read_json(expected_path)
    config_path = os.path.join(source, "fixture.json")
    config = P.read_json(config_path) if os.path.isfile(config_path) else {}

    workdir = tempfile.mkdtemp(prefix="kaizen-fixture-")
    try:
        target = os.path.join(workdir, name)
        shutil.copytree(source, target)
        for meta in ("expected.json", "fixture.json"):
            path = os.path.join(target, meta)
            if os.path.isfile(path):
                os.remove(path)

        _setup_git(config.get("git"), target)

        env = dict(os.environ)
        env.update(GIT_ENV)
        env["CLAUDE_PROJECT_DIR"] = target
        proc = subprocess.run(
            [P.DETECT_BIN],
            cwd=target,
            capture_output=True,
            text=True,
            env=env,
            timeout=60,
        )

        if not r.check(
            proc.returncode == 0,
            "fixture `%s`: kaizen-detect exits 0" % name,
            (proc.stderr or "").strip(),
        ):
            return

        try:
            actual = json.loads(proc.stdout)
            r.ok("fixture `%s`: kaizen-detect emits valid JSON" % name)
        except ValueError as exc:
            r.fail(
                "fixture `%s`: kaizen-detect emitted invalid JSON" % name,
                "%s\n--- stdout ---\n%s" % (exc, proc.stdout[:400]),
            )
            return

        r.check(
            actual.get("cwd") == os.path.realpath(target)
            or actual.get("cwd") == target,
            "fixture `%s`: cwd points at the project dir" % name,
            "got %s, expected %s" % (actual.get("cwd"), target),
        )

        actual.pop("cwd", None)
        expected.pop("cwd", None)
        note = expected.pop("_note", None)

        diffs = _diff(expected, actual)
        r.check(
            not diffs,
            "fixture `%s`: detect output matches golden" % name,
            "\n".join(diffs),
        )

        if note:
            r.warn(
                "fixture `%s` encodes a known limitation" % name,
                note,
            )
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def _setup_git(git_config, target):
    if not git_config or not git_config.get("init"):
        return
    branch = git_config.get("branch", "main")
    env = dict(os.environ)
    env.update(GIT_ENV)

    def git(*args):
        subprocess.run(
            ["git"] + list(args),
            cwd=target,
            capture_output=True,
            text=True,
            env=env,
            check=True,
        )

    git("init", "-q", "-b", branch)
    git("add", "-A")
    git("commit", "-q", "-m", "fixture: initial")
    for i in range(1, int(git_config.get("commits", 1))):
        git("commit", "-q", "--allow-empty", "-m", "fixture: commit %d" % (i + 1))


def _diff(expected, actual, prefix=""):
    """Readable field-by-field difference between two detect payloads."""
    diffs = []
    for key in sorted(set(expected) | set(actual)):
        path = "%s%s" % (prefix, key)
        want = expected.get(key, "<missing>")
        got = actual.get(key, "<missing>")
        if isinstance(want, dict) and isinstance(got, dict):
            diffs += _diff(want, got, prefix="%s." % path)
        elif want != got:
            diffs.append("%s: expected %r, got %r" % (path, want, got))
    return diffs
