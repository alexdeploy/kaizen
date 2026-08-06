"""Template integrity — the highest-value deterministic checks in the harness.

Two failure modes this catches that nothing else does:

1. A template uses `{{FOO}}` that no directive in init/SKILL.md tells Claude how
   to fill. The user gets a literal `{{FOO}}` in their CLAUDE.md.
2. A `KAIZEN_ENRICH:<id>` marker exists with no matching directive (or a
   directive exists with no marker). Same symptom, worse: the marker is an HTML
   comment, so it looks fine until you read the generated file.

Both are invisible in review and only surface in a user's project.
"""

import json
import os
import re

import kzparse as P

REQUIRED_PRESET_FILES = ["CLAUDE.md", os.path.join(".claude", "settings.json")]

TEMPLATE_TEXT_SUFFIXES = (".md", ".json", ".sh", ".append", ".example")


def run(r):
    declared_placeholders = P.declared_placeholders()
    declared_directives = P.declared_enrich_directives()

    r.check(
        len(declared_placeholders) > 0,
        "init/SKILL.md declares a placeholder registry",
    )
    r.check(
        len(declared_directives) > 0,
        "init/SKILL.md declares an enrichment directive registry",
    )

    used_placeholders = set()
    used_directives = set()

    for path in P.walk_files(P.TEMPLATES_DIR):
        if not path.endswith(TEMPLATE_TEXT_SUFFIXES):
            continue
        text = P.read(path)
        found_p = P.placeholders_in(text)
        found_d = P.enrich_markers_in(text)
        used_placeholders |= found_p
        used_directives |= found_d

        unknown_p = sorted(found_p - declared_placeholders)
        r.check(
            not unknown_p,
            "%s uses only registered placeholders" % P.rel(path),
            "unregistered: %s" % ", ".join("{{%s}}" % p for p in unknown_p),
        )

        unknown_d = sorted(found_d - declared_directives)
        r.check(
            not unknown_d,
            "%s uses only registered enrichment directives" % P.rel(path),
            "unregistered: %s" % ", ".join(unknown_d),
        )

    # --- the other direction: registered but never used -------------------
    for placeholder in sorted(declared_placeholders - used_placeholders):
        r.warn(
            "placeholder {{%s}} is documented but no template uses it" % placeholder,
            "either wire it into a template or drop it from init/SKILL.md",
        )

    for directive in sorted(declared_directives - used_directives):
        r.fail(
            "enrichment directive `%s` has no marker in any template" % directive,
            "Claude is told how to fill a marker that will never appear",
        )

    # --- presets are complete and parseable -------------------------------
    presets = P.preset_dirs()
    r.check(len(presets) > 0, "at least one stack preset exists")

    for preset in presets:
        for required in REQUIRED_PRESET_FILES:
            path = os.path.join(P.TEMPLATES_DIR, preset, required)
            r.check(
                os.path.isfile(path),
                "preset `%s` ships %s" % (preset, required),
            )

    for path in P.walk_files(P.TEMPLATES_DIR, [".json"]):
        if path.endswith(".example"):
            continue
        try:
            json.loads(P.read(path))
            r.ok("%s is valid JSON" % P.rel(path))
        except ValueError as exc:
            r.fail("%s is not valid JSON" % P.rel(path), exc)

    # --- prose the skill appends must come from a file --------------------
    # A run that composes this section itself produces different output every
    # time, so /kaizen:upgrade cannot tell a template change from an invention.
    init_skill = P.read(os.path.join(P.SKILLS_DIR, "init", "SKILL.md"))
    for referenced in re.findall(r"templates/(_shared/[A-Za-z0-9_.\-]+\.md)", init_skill):
        r.check(
            os.path.isfile(os.path.join(P.TEMPLATES_DIR, referenced)),
            "init/SKILL.md references a template that exists (%s)" % referenced,
        )

    # --- every stack the detector emits maps to a real preset -------------
    mapping = P.config("stack-presets.json")["stack_to_preset"]
    emitted = P.detect_stack_tokens()

    for stack in sorted(emitted):
        if not r.check(
            stack in mapping,
            "detected stack `%s` has a documented preset mapping" % stack,
            "add it to tests/config/stack-presets.json (and ideally a preset dir)",
        ):
            continue
        target = mapping[stack]
        r.check(
            target in presets,
            "stack `%s` maps to an existing preset (`%s`)" % (stack, target),
        )
        if target == "generic" and stack not in ("generic", "frontend", "backend-node"):
            r.warn(
                "stack `%s` is detected but falls back to the generic preset" % stack,
                "detection promises more adaptation than the templates deliver",
            )

    for stack in sorted(set(mapping) - emitted - {"generic"}):
        r.warn(
            "stack-presets.json maps `%s`, which kaizen-detect never emits" % stack,
        )


