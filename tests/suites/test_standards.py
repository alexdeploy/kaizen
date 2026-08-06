"""The standards catalog: schema, provenance, and the tool that renders it.

A rule in this catalog ends up verbatim in someone's CLAUDE.md, loaded into
every session they run. It has to be well-formed, traceable, and — when it
claims to be checkable — actually checkable by the tool that will check it.

The provenance checks are deliberately noisy: a rule with no source is a rule
nobody can argue with, which is the failure mode ADR-0005 exists to prevent.
"""

import json
import os
import re
import subprocess
import sys

import kzparse as P

STANDARDS_DIR = os.path.join(P.PLUGIN_ROOT, "standards")
INDEX_PATH = os.path.join(STANDARDS_DIR, "index.json")
STANDARDS_BIN = os.path.join(P.PLUGIN_ROOT, "bin", "kaizen-standards")

REQUIRED_RULE_KEYS = [
    "id", "title", "statement", "rationale", "sources",
    "added", "severity", "status", "applies_to", "surface", "check",
]

VALID_MATURITY = {"empty", "scaffold", "small", "mature"}

# The Grep tool is ripgrep (Rust regex): no lookaround, no backreferences.
# A pattern using them compiles in Python and fails where it will actually run.
RIPGREP_UNSUPPORTED = [
    (r"\(\?=", "lookahead (?=…)"),
    (r"\(\?!", "negative lookahead (?!…)"),
    (r"\(\?<=", "lookbehind (?<=…)"),
    (r"\(\?<!", "negative lookbehind (?<!…)"),
    (r"\\[1-9]", "backreference"),
]

MIN_RATIONALE_CHARS = 80


def run(r):
    if not r.check(os.path.isdir(STANDARDS_DIR), "standards/ catalog exists"):
        return
    if not r.check(os.path.isfile(INDEX_PATH), "standards/index.json exists"):
        return

    try:
        index = P.read_json(INDEX_PATH)
        r.ok("index.json is valid JSON")
    except ValueError as exc:
        r.fail("index.json is not valid JSON", exc)
        return

    _check_index(r, index)
    rules = _load_rules(r, index)
    if rules is None:
        return
    _check_rules(r, index, rules)
    _check_templates_against_surfaces(r, index, rules)
    _check_binary(r, rules)


# ------------------------------------------------------------------ index ---


def _check_index(r, index):
    version = index.get("standards_version", "")
    r.check(
        re.match(r"^\d{4}\.\d{2}$", version) is not None,
        "standards_version uses calendar versioning (%s)" % version,
        "ADR-0005: freshness is the point; 1.4.2 communicates nothing about currency",
    )
    r.check(isinstance(index.get("catalog_schema"), int), "index declares catalog_schema")
    for key in ("domains", "surfaces", "severity_levels", "status_values", "check_types"):
        r.check(key in index, "index declares `%s`" % key)


def _load_rules(r, index):
    rules = []
    for domain in index.get("domains", []):
        path = os.path.join(STANDARDS_DIR, domain["file"])
        if not r.check(
            os.path.isfile(path),
            "declared domain file exists (%s)" % domain["file"],
        ):
            return None
        try:
            data = P.read_json(path)
            r.ok("%s is valid JSON" % domain["file"])
        except ValueError as exc:
            r.fail("%s is not valid JSON" % domain["file"], exc)
            return None
        for rule in data.get("rules", []):
            rule["_file"] = domain["file"]
            rule["_prefix"] = domain.get("id_prefix", "")
            rules.append(rule)

    r.check(len(rules) > 0, "the catalog contains rules")
    return rules


# ------------------------------------------------------------------ rules ---


def _check_rules(r, index, rules):
    ids = [rule.get("id") for rule in rules]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    r.check(not duplicates, "every rule id is unique", ", ".join(duplicates))

    known_ids = set(ids)
    surfaces = set(index.get("surfaces", {}))
    severities = set(index.get("severity_levels", {}))
    statuses = set(index.get("status_values", []))
    check_types = set(index.get("check_types", {}))
    known_stacks = P.detect_stack_tokens()

    used_surfaces = set()
    sourceless = []

    for rule in rules:
        rid = rule.get("id", "<no id>")

        for key in REQUIRED_RULE_KEYS:
            r.check(key in rule, "%s has `%s`" % (rid, key))

        r.check(
            rid.startswith(rule["_prefix"] + "-"),
            "%s uses its domain's id prefix (%s)" % (rid, rule["_prefix"]),
        )
        r.check(
            re.match(r"^[A-Z]+-\d{3}$", rid) is not None,
            "%s id is well-formed (PREFIX-NNN)" % rid,
        )
        r.check(
            re.match(r"^\d{4}-\d{2}-\d{2}$", str(rule.get("added", ""))) is not None,
            "%s has an ISO date in `added`" % rid,
            str(rule.get("added")),
        )
        r.check(
            rule.get("severity") in severities,
            "%s severity is one the index declares" % rid,
            str(rule.get("severity")),
        )
        r.check(
            rule.get("status") in statuses,
            "%s status is one the index declares" % rid,
            str(rule.get("status")),
        )
        r.check(
            rule.get("surface") in surfaces,
            "%s renders into a declared surface" % rid,
            str(rule.get("surface")),
        )
        used_surfaces.add(rule.get("surface"))

        r.check(
            bool(str(rule.get("statement", "")).strip()),
            "%s has a non-empty statement" % rid,
        )
        r.check_warn(
            len(str(rule.get("rationale", ""))) >= MIN_RATIONALE_CHARS,
            "%s explains itself (rationale >= %d chars)" % (rid, MIN_RATIONALE_CHARS),
            "a rule nobody can evaluate is a rule nobody will keep",
        )

        # Provenance. Deliberately a warning, not a failure: the gap is real and
        # should be visible on every run rather than blocking work.
        if not rule.get("sources"):
            sourceless.append(rid)
        for source in rule.get("sources", []):
            r.check(
                "label" in source,
                "%s source entries are labelled" % rid,
            )
            if "url" in source:
                r.check(
                    source["url"].startswith("http"),
                    "%s source url is absolute" % rid,
                    source["url"],
                )

        applies = rule.get("applies_to", {})
        for stack in applies.get("stack", []):
            r.check(
                stack == "*" or stack in known_stacks,
                "%s applies to a stack kaizen-detect can emit (%s)" % (rid, stack),
                "known: %s" % ", ".join(sorted(known_stacks)),
            )
        for maturity in applies.get("maturity", []):
            r.check(
                maturity in VALID_MATURITY,
                "%s applies to a valid maturity (%s)" % (rid, maturity),
            )

        if "refines" in rule:
            r.check(
                rule["refines"] in known_ids,
                "%s refines a rule that exists (%s)" % (rid, rule["refines"]),
            )
        if rule.get("status") == "deprecated":
            r.check(
                rule.get("deprecated_by") in known_ids,
                "%s is deprecated and names its replacement" % rid,
                "a deprecated rule with no successor leaves users nowhere to go",
            )

        _check_rule_check(r, rid, rule.get("check", {}), check_types)

    if sourceless:
        r.warn(
            "%d rule(s) have no source" % len(sourceless),
            "%s\nADR-0005: a rule with a source can be argued with; one without "
            "is indistinguishable from an arbitrary opinion." % ", ".join(sourceless),
        )

    for surface in sorted(surfaces - used_surfaces):
        r.warn("surface `%s` is declared but no rule renders into it" % surface)


def _check_rule_check(r, rid, check, check_types):
    ctype = check.get("type")
    r.check(ctype in check_types, "%s check.type is declared in the index" % rid, str(ctype))

    if ctype == "none":
        r.check(
            bool(check.get("reason")),
            "%s says why it cannot be checked mechanically" % rid,
            "unverifiable rules are surfaced as 'unchecked', never skipped silently",
        )
        return

    pattern = check.get("pattern")
    r.check(bool(pattern), "%s declares a pattern" % rid)
    if not pattern:
        return

    try:
        re.compile(pattern)
        r.ok("%s pattern is a valid regex" % rid)
    except re.error as exc:
        r.fail("%s pattern is not a valid regex" % rid, "%s — %s" % (pattern, exc))
        return

    # The pattern will be handed to the Grep tool, which is ripgrep.
    for probe, label in RIPGREP_UNSUPPORTED:
        if re.search(probe, pattern):
            r.fail(
                "%s pattern uses %s, unsupported by the Grep tool" % (rid, label),
                "%s\nripgrep's regex engine has no lookaround or backreferences; "
                "this compiles in Python and fails where it actually runs." % pattern,
            )

    if ctype == "grep":
        r.check(bool(check.get("include")), "%s declares include globs" % rid)


def _check_templates_against_surfaces(r, index, rules):
    """Markers in templates and surfaces in the index must agree, both ways."""
    surfaces = set(index.get("surfaces", {}))
    marker_re = re.compile(r"KAIZEN_STANDARDS:([a-z_.]+)")

    used_in_templates = set()
    for path in P.walk_files(P.TEMPLATES_DIR, [".md"]):
        found = set(marker_re.findall(P.read(path)))
        used_in_templates |= found
        unknown = sorted(found - surfaces)
        r.check(
            not unknown,
            "%s uses only declared standards surfaces" % P.rel(path),
            "unknown: %s" % ", ".join(unknown),
        )

    rendered_surfaces = {rule.get("surface") for rule in rules}
    for surface in sorted(rendered_surfaces - used_in_templates):
        r.fail(
            "rules render into `%s` but no template has that marker" % surface,
            "those rules would never reach a user's project",
        )

    # The init skill must document how to fill the markers.
    init_skill = P.read(os.path.join(P.SKILLS_DIR, "init", "SKILL.md"))
    r.check(
        "KAIZEN_STANDARDS" in init_skill,
        "init/SKILL.md documents the standards markers",
    )
    r.check(
        "kaizen-standards render" in init_skill,
        "init/SKILL.md tells Claude to render from the catalog, not from memory",
    )
    r.check(
        "Bash(kaizen-standards *)" in init_skill,
        "init/SKILL.md is allowed to run kaizen-standards",
    )


# ----------------------------------------------------------------- binary ---


def _check_binary(r, rules):
    if not r.check(os.path.isfile(STANDARDS_BIN), "kaizen-standards exists"):
        return
    r.check(os.access(STANDARDS_BIN, os.X_OK), "kaizen-standards is executable")

    version = _json_run(r, ["version"])
    if version is not None:
        r.check(
            version.get("rules") == len(rules),
            "kaizen-standards sees every rule in the catalog",
            "reports %s, catalog has %d" % (version.get("rules"), len(rules)),
        )

    # Rendering must be stable: an unstable order would make every /kaizen:upgrade
    # show phantom changes.
    first = _run(["render", "--surface", "claude_md.conventions",
                  "--stack", "frontend,typescript", "--maturity", "small"])
    second = _run(["render", "--surface", "claude_md.conventions",
                   "--stack", "frontend,typescript", "--maturity", "small"])
    r.check(
        first.stdout == second.stdout and first.returncode == 0,
        "render output is deterministic across runs",
        "an unstable order would make every upgrade show phantom changes",
    )
    r.check(
        first.stdout.strip() != "",
        "render produces rules for a typescript project",
    )
    for line in first.stdout.strip().splitlines():
        r.check(
            re.search(r"<!-- [A-Z]+-\d{3} -->$", line) is not None,
            "each rendered line carries its rule id",
            line,
        )

    # A general rule must not render alongside the specific rule that refines it.
    ids = re.findall(r"<!-- ([A-Z]+-\d{3}) -->", first.stdout)
    refined = {rule["refines"] for rule in rules if rule.get("refines")}
    overlap = sorted(set(ids) & refined)
    r.check(
        not overlap,
        "a refined rule is suppressed when its specialisation applies",
        "both rendered: %s" % ", ".join(overlap),
    )

    empty = _run(["render", "--surface", "claude_md.conventions",
                  "--stack", "generic", "--maturity", "empty"])
    r.check(
        empty.returncode == 1,
        "render exits 1 when no rule applies, so init can fall back",
        "exit %d" % empty.returncode,
    )

    missing = _run(["show", "ZZ-999"])
    r.check(missing.returncode != 0, "show fails on an unknown rule id")


def _run(args):
    env = dict(os.environ)
    env["KAIZEN_STANDARDS_DIR"] = STANDARDS_DIR
    return subprocess.run(
        [sys.executable, STANDARDS_BIN] + args,
        capture_output=True, text=True, env=env, timeout=60,
    )


def _json_run(r, args):
    proc = _run(args)
    try:
        return json.loads(proc.stdout)
    except ValueError as exc:
        r.fail(
            "kaizen-standards %s did not emit valid JSON" % " ".join(args),
            "%s\n%s\n%s" % (exc, proc.stdout[:300], proc.stderr[:300]),
        )
        return None


