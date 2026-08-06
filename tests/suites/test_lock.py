"""Behaviour of kaizen-lock — the bookkeeping engine behind /kaizen:upgrade.

Unlike everything else kaizen ships, this is deterministic code, so it gets
deterministic tests: real files in a real temp repo, real hashes, real merges.

The promise being guarded is narrow and absolute: **kaizen must never overwrite
something the user changed**. Every check below exists because getting one of
them wrong silently destroys somebody's work.
"""

import json
import os
import shutil
import subprocess
import tempfile

import kzparse as P

LOCK_BIN = os.path.join(P.PLUGIN_ROOT, "bin", "kaizen-lock")

GIT_ID = [
    "-c", "user.email=harness@kaizen.test",
    "-c", "user.name=kaizen harness",
]


def run(r):
    if not r.check(os.path.isfile(LOCK_BIN), "kaizen-lock exists"):
        return
    r.check(os.access(LOCK_BIN, os.X_OK), "kaizen-lock is executable")
    r.check(
        os.path.basename(os.path.dirname(LOCK_BIN)) == "bin",
        "kaizen-lock lives in bin/ so Claude Code puts it on PATH",
    )

    _test_write_and_status(r)
    _test_modification_detection(r)
    _test_clean_merge(r)
    _test_conflicting_merge(r)
    _test_missing_baseline(r)
    _test_incremental_write(r)
    _test_forget(r)
    _test_no_lock(r)
    _test_gitignore_awareness(r)
    _test_placeholder_recording(r)


# --------------------------------------------------------------- scenarios ---


def _test_placeholder_recording(r):
    """The values placeholders resolved to must survive, or upgrade re-renders wrong.

    A project generated with `npm` that later grows a `pnpm-lock.yaml` must not
    have every command line silently rewritten by an upgrade. Recording the
    resolved values is what lets /kaizen:upgrade re-render faithfully and report
    the detection drift as advice instead of acting on it.
    """
    with _project() as project:
        _seed(project, {"CLAUDE.md": "a\n", "B.md": "b\n"})

        out = _lock(r, project, ["write", "--placeholder", "PACKAGE_MANAGER=npm",
                                 "--placeholder", "TEST_RUNNER=vitest", "CLAUDE.md"])
        if out is None:
            return
        lock = _load_lock(r, project)
        if lock is None:
            return
        r.check(
            lock.get("placeholders") == {"PACKAGE_MANAGER": "npm",
                                        "TEST_RUNNER": "vitest"},
            "write records the values placeholders resolved to",
            json.dumps(lock.get("placeholders")),
        )

        # A partial write (what upgrade does) updates what it names and keeps the
        # rest — same contract as files.
        _lock(r, project, ["write", "--placeholder", "PACKAGE_MANAGER=pnpm", "B.md"])
        lock = _load_lock(r, project)
        if lock is None:
            return
        r.check(
            lock.get("placeholders") == {"PACKAGE_MANAGER": "pnpm",
                                        "TEST_RUNNER": "vitest"},
            "a partial write updates one placeholder and keeps the others",
            json.dumps(lock.get("placeholders")),
        )

        _lock(r, project, ["write", "CLAUDE.md"])
        lock = _load_lock(r, project)
        if lock is None:
            return
        r.check(
            lock.get("placeholders") == {"PACKAGE_MANAGER": "pnpm",
                                        "TEST_RUNNER": "vitest"},
            "a write naming no placeholder keeps every recorded value",
            json.dumps(lock.get("placeholders")),
        )

        _lock(r, project, ["forget", "B.md"])
        lock = _load_lock(r, project)
        if lock is None:
            return
        r.check(
            lock.get("placeholders") == {"PACKAGE_MANAGER": "pnpm",
                                        "TEST_RUNNER": "vitest"},
            "forget does not drop the recorded placeholders",
            json.dumps(lock.get("placeholders")),
        )

        status = _lock(r, project, ["status"])
        if status is not None:
            r.check(
                status.get("placeholders", {}).get("PACKAGE_MANAGER") == "pnpm",
                "status surfaces the placeholders so upgrade reads them in one call",
                json.dumps(status.get("placeholders")),
            )


def _load_lock(r, project):
    path = os.path.join(project, ".claude/kaizen/lock.json")
    try:
        with open(path) as fh:
            return json.load(fh)
    except (IOError, ValueError) as exc:
        r.fail("lock.json is readable after the operation", exc)
        return None


def _test_write_and_status(r):
    with _project() as project:
        _seed(project, {"CLAUDE.md": "a\nb\n", ".claude/settings.json": "{}\n"})
        out = _lock(r, project, ["write", "--plugin-version", "0.13.0",
                                 "--profile", "standard", "--preset", "generic",
                                 "CLAUDE.md", ".claude/settings.json"])
        if out is None:
            return

        r.check(out.get("recorded") == 2, "write records every file it is given")
        r.check(
            os.path.isfile(os.path.join(project, ".claude/kaizen/lock.json")),
            "write creates .claude/kaizen/lock.json",
        )
        for path in ("CLAUDE.md", ".claude/settings.json"):
            r.check(
                os.path.isfile(os.path.join(project, ".claude/kaizen/baseline", path)),
                "write snapshots %s into baseline/" % path,
                "without the snapshot a 3-way merge is impossible",
            )

        try:
            with open(os.path.join(project, ".claude/kaizen/lock.json")) as fh:
                lock = json.load(fh)
            r.ok("lock.json is valid JSON")
        except ValueError as exc:
            r.fail("lock.json is not valid JSON", exc)
            return

        r.check(lock.get("lock_version") == 1, "lock.json declares its schema version")
        r.check(lock.get("plugin_version") == "0.13.0", "lock.json records the plugin version")
        r.check(lock.get("profile") == "standard", "lock.json records the profile")
        r.check(lock.get("preset") == "generic", "lock.json records the preset")
        r.check(len(lock.get("files", [])) == 2, "lock.json lists both files")

        status = _lock(r, project, ["status"])
        if status is None:
            return
        r.check(status.get("lock_present") is True, "status finds the lock")
        r.check(
            status["summary"] == {"unchanged": 2, "modified": 0, "deleted": 0,
                                  "missing_baseline": 0},
            "status reports untouched files as unchanged",
            json.dumps(status.get("summary")),
        )


def _test_modification_detection(r):
    with _project() as project:
        _seed(project, {
            "CLAUDE.md": "a\nb\n",
            ".claude/rules/testing.md": "rule\n",
            ".claude/settings.json": "{}\n",
        })
        _lock(r, project, ["write", "CLAUDE.md", ".claude/rules/testing.md",
                           ".claude/settings.json"])

        # The user edits one file and deletes another.
        _seed(project, {"CLAUDE.md": "a\nb\nmy own rule\n"})
        os.remove(os.path.join(project, ".claude/rules/testing.md"))

        status = _lock(r, project, ["status"])
        if status is None:
            return
        states = {f["path"]: f["state"] for f in status["files"]}

        r.check(
            states.get("CLAUDE.md") == "modified",
            "an edited file is reported as modified",
            json.dumps(states),
        )
        r.check(
            states.get(".claude/rules/testing.md") == "deleted",
            "a deleted file is reported as deleted, not missing",
            json.dumps(states),
        )
        r.check(
            states.get(".claude/settings.json") == "unchanged",
            "an untouched file stays unchanged",
            json.dumps(states),
        )
        r.check(
            status["summary"] == {"unchanged": 1, "modified": 1, "deleted": 1,
                                  "missing_baseline": 0},
            "status summary counts each state once",
            json.dumps(status["summary"]),
        )


def _test_clean_merge(r):
    """The scenario the whole feature exists for: both sides changed, no overlap."""
    with _project() as project:
        _seed(project, {"CLAUDE.md": "# Title\n\n- Test: npm test\n\n- Named exports only.\n"})
        _lock(r, project, ["write", "CLAUDE.md"])

        # User adds their own convention.
        _seed(project, {
            "CLAUDE.md": "# Title\n\n- Test: npm test\n\n- Named exports only.\n- No moment.js.\n"
        })
        # New kaizen template adds a command line.
        incoming = os.path.join(project, "incoming.md")
        with open(incoming, "w") as fh:
            fh.write("# Title\n\n- Test: npm test\n- Lint: npm run lint\n\n- Named exports only.\n")

        out = _lock(r, project, ["merge", "CLAUDE.md", incoming])
        if out is None:
            return

        if not r.check(
            out.get("result") == "clean" and out.get("conflicts") == 0,
            "non-overlapping edits merge cleanly",
            json.dumps(out),
        ):
            return

        merged = _read(out["merged_file"])
        r.check(
            "No moment.js." in merged,
            "the user's own edit survives the merge",
            "THIS IS THE PROMISE OF THE WHOLE FEATURE",
        )
        r.check(
            "Lint: npm run lint" in merged,
            "the new template's addition arrives in the merge",
        )
        r.check(
            _read(os.path.join(project, "CLAUDE.md")) != merged,
            "merge does not write into the project (planning stays read-only)",
        )


def _test_conflicting_merge(r):
    with _project() as project:
        _seed(project, {"CLAUDE.md": "a\nTest: npm test\nc\n"})
        _lock(r, project, ["write", "CLAUDE.md"])
        _seed(project, {"CLAUDE.md": "a\nTest: pnpm test\nc\n"})

        incoming = os.path.join(project, "incoming.md")
        with open(incoming, "w") as fh:
            fh.write("a\nTest: yarn test\nc\n")

        out = _lock(r, project, ["merge", "CLAUDE.md", incoming])
        if out is None:
            return

        r.check(
            out.get("result") == "conflicts" and out.get("conflicts") == 1,
            "edits to the same line are reported as a conflict, never merged away",
            json.dumps(out),
        )
        merged = _read(out["merged_file"])
        for marker in ("<<<<<<<", "|||||||", ">>>>>>>"):
            r.check(
                marker in merged,
                "conflict output carries the %s marker" % marker,
            )
        r.check(
            "pnpm test" in merged and "yarn test" in merged and "npm test" in merged,
            "conflict output shows all three sides (yours, base, theirs)",
        )


def _test_missing_baseline(r):
    with _project() as project:
        _seed(project, {"CLAUDE.md": "a\n"})
        _lock(r, project, ["write", "CLAUDE.md"])
        os.remove(os.path.join(project, ".claude/kaizen/baseline/CLAUDE.md"))
        _seed(project, {"CLAUDE.md": "a\nedited\n"})

        incoming = os.path.join(project, "incoming.md")
        with open(incoming, "w") as fh:
            fh.write("a\nnew\n")

        proc = _raw(project, ["merge", "CLAUDE.md", incoming])
        out = _parse(r, proc, "merge without baseline")
        if out is None:
            return
        r.check(
            out.get("result") == "no-baseline",
            "a missing baseline is refused, not guessed at",
            json.dumps(out),
        )
        r.check(
            proc.returncode == 3,
            "merge signals no-baseline with a distinct exit code (3)",
            "got %d" % proc.returncode,
        )


def _test_incremental_write(r):
    """An upgrade re-records only the files it touched; the rest must survive."""
    with _project() as project:
        _seed(project, {"a.md": "1\n", "b.md": "2\n"})
        _lock(r, project, ["write", "a.md", "b.md"])
        _seed(project, {"a.md": "1 updated\n"})
        out = _lock(r, project, ["write", "a.md"])
        if out is None:
            return

        r.check(
            out.get("total_tracked") == 2,
            "a partial write keeps the files it did not touch",
            json.dumps(out),
        )
        status = _lock(r, project, ["status"])
        states = {f["path"]: f["state"] for f in status["files"]}
        r.check(
            states == {"a.md": "unchanged", "b.md": "unchanged"},
            "re-recording a file resets it to unchanged",
            json.dumps(states),
        )


def _test_forget(r):
    with _project() as project:
        _seed(project, {"a.md": "1\n", "b.md": "2\n"})
        _lock(r, project, ["write", "a.md", "b.md"])
        out = _lock(r, project, ["forget", "a.md"])
        if out is None:
            return
        r.check(out.get("total_tracked") == 1, "forget drops the entry")
        r.check(
            not os.path.isfile(os.path.join(project, ".claude/kaizen/baseline/a.md")),
            "forget removes the baseline snapshot too",
        )


def _test_no_lock(r):
    with _project() as project:
        proc = _raw(project, ["status"])
        out = _parse(r, proc, "status without a lock")
        if out is None:
            return
        r.check(
            out.get("lock_present") is False,
            "status on an untracked project reports lock_present: false",
        )
        r.check(
            proc.returncode == 0,
            "status on an untracked project is not an error",
            "upgrade needs to branch on this, not crash on it",
        )


def _test_gitignore_awareness(r):
    """The lock must be committed; ignoring it silently breaks upgrades for a team."""
    with _project() as project:
        _seed(project, {"CLAUDE.md": "a\n", ".gitignore": ".claude/kaizen/\n"})
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=project,
                       capture_output=True)
        out = _lock(r, project, ["write", "CLAUDE.md"])
        if out is None:
            return
        r.check(
            out.get("lock_is_gitignored") is True,
            "write warns when .gitignore would exclude the lock file",
            "the init/upgrade skills branch on this to fix .gitignore",
        )


# ----------------------------------------------------------------- helpers ---


class _project(object):
    """Temp project directory, cleaned up afterwards."""

    def __enter__(self):
        self.path = tempfile.mkdtemp(prefix="kaizen-lock-test-")
        return self.path

    def __exit__(self, *exc):
        shutil.rmtree(self.path, ignore_errors=True)
        return False


def _seed(project, files):
    for rel, content in files.items():
        path = os.path.join(project, rel)
        directory = os.path.dirname(path)
        if directory:
            try:
                os.makedirs(directory)
            except OSError:
                pass
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)


def _raw(project, args):
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = project
    return subprocess.run(
        [LOCK_BIN] + args, cwd=project, capture_output=True, text=True,
        env=env, timeout=60,
    )


def _lock(r, project, args):
    proc = _raw(project, args)
    return _parse(r, proc, " ".join(args[:2]))


def _parse(r, proc, label):
    try:
        return json.loads(proc.stdout)
    except ValueError as exc:
        r.fail(
            "kaizen-lock %s did not emit valid JSON" % label,
            "%s\n--- stdout ---\n%s\n--- stderr ---\n%s"
            % (exc, proc.stdout[:400], proc.stderr[:400]),
        )
        return None


def _read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()
