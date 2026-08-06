"""Parsing helpers shared by the validation suites.

Stdlib only, Python 3.9+. No YAML dependency: kaizen frontmatter is flat
`key: value` and a hand-rolled parser keeps the harness installable anywhere.
"""

import json
import os
import re

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PLUGIN_ROOT = os.path.join(REPO_ROOT, "plugins", "kaizen")
SKILLS_DIR = os.path.join(PLUGIN_ROOT, "skills")
AGENTS_DIR = os.path.join(PLUGIN_ROOT, "agents")
HOOKS_DIR = os.path.join(PLUGIN_ROOT, "hooks")
HOOK_SCRIPTS_DIR = os.path.join(HOOKS_DIR, "scripts")
TEMPLATES_DIR = os.path.join(SKILLS_DIR, "init", "templates")
TESTS_DIR = os.path.join(REPO_ROOT, "tests")
CONFIG_DIR = os.path.join(TESTS_DIR, "config")
FIXTURES_DIR = os.path.join(TESTS_DIR, "fixtures")
DETECT_BIN = os.path.join(PLUGIN_ROOT, "bin", "kaizen-detect")

PLUGIN_MANIFEST = os.path.join(PLUGIN_ROOT, ".claude-plugin", "plugin.json")
MARKETPLACE_MANIFEST = os.path.join(REPO_ROOT, ".claude-plugin", "marketplace.json")

# Preset directories that are not stack presets.
NON_PRESET_TEMPLATE_DIRS = {"_shared"}


def rel(path):
    """Repo-relative path, for readable check output."""
    return os.path.relpath(path, REPO_ROOT)


def read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def read_json(path):
    """Parse JSON, tolerating the `_comment` / `_docs` keys kaizen uses."""
    return json.loads(read(path))


def parse_frontmatter(path):
    """Return (frontmatter_dict, body). Frontmatter is flat `key: value`.

    Values keep their raw string form minus surrounding quotes. Missing or
    malformed frontmatter yields ({}, full_text) so callers can report it.
    """
    text = read(path)
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    raw = text[3:end]
    body = text[end + 4 :]
    data = {}
    for line in raw.splitlines():
        line = line.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        data[key] = value
    return data, body


def csv_list(value):
    """Split a `Read, Write, Bash(git diff *)` style list, respecting parens."""
    items, depth, current = [], 0, ""
    for ch in value or "":
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        if ch == "," and depth == 0:
            items.append(current.strip())
            current = ""
        else:
            current += ch
    if current.strip():
        items.append(current.strip())
    return [i for i in items if i]


def tool_names(value):
    """Bare tool names from an allowed-tools / tools value (`Bash(x *)` -> `Bash`)."""
    return [re.sub(r"\(.*\)$", "", item).strip() for item in csv_list(value)]


def skill_files():
    """[(skill_name, path)] for every plugin skill, sorted."""
    out = []
    for name in sorted(os.listdir(SKILLS_DIR)):
        path = os.path.join(SKILLS_DIR, name, "SKILL.md")
        if os.path.isfile(path):
            out.append((name, path))
    return out


def agent_files():
    """[(agent_name_from_filename, path)] for plugin-level agents."""
    return [
        (name[:-3], os.path.join(AGENTS_DIR, name))
        for name in sorted(os.listdir(AGENTS_DIR))
        if name.endswith(".md")
    ]


def project_agent_files():
    """Agents that /kaizen:init writes into the *user's* project."""
    d = os.path.join(TEMPLATES_DIR, "_shared", ".claude", "agents")
    if not os.path.isdir(d):
        return []
    return [
        (name[:-3], os.path.join(d, name))
        for name in sorted(os.listdir(d))
        if name.endswith(".md")
    ]


def preset_dirs():
    """Stack preset directories under templates/."""
    return [
        name
        for name in sorted(os.listdir(TEMPLATES_DIR))
        if os.path.isdir(os.path.join(TEMPLATES_DIR, name))
        and name not in NON_PRESET_TEMPLATE_DIRS
    ]


def walk_files(root, suffixes=None):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        for name in sorted(filenames):
            if suffixes and not name.endswith(tuple(suffixes)):
                continue
            yield os.path.join(dirpath, name)


def shell_scripts():
    """Every shell script shipped by the plugin.

    Everything in bin/ (which has no extension by convention, since Claude Code
    puts the directory on PATH) plus every .sh under the plugin, including the
    hooks that templates copy into user projects.
    """
    bin_dir = os.path.join(PLUGIN_ROOT, "bin")
    found = sorted(
        os.path.join(bin_dir, name)
        for name in os.listdir(bin_dir)
        if os.path.isfile(os.path.join(bin_dir, name))
    )
    found += sorted(walk_files(PLUGIN_ROOT, [".sh"]))
    return found


PLACEHOLDER_RE = re.compile(r"\{\{([A-Z_]+)\}\}")
ENRICH_RE = re.compile(r"KAIZEN_ENRICH:([a-z_]+)")


def placeholders_in(text):
    return set(PLACEHOLDER_RE.findall(text))


def enrich_markers_in(text):
    return set(ENRICH_RE.findall(text))


def declared_placeholders():
    """Placeholder registry, parsed from the table in init/SKILL.md.

    The SKILL.md table is the single source of truth — the harness reads it
    rather than duplicating the list, so adding a placeholder to the docs and
    the templates in the same commit keeps the check green.
    """
    text = read(os.path.join(SKILLS_DIR, "init", "SKILL.md"))
    section = _section(text, "## Placeholder reference")
    return set(PLACEHOLDER_RE.findall(section or ""))


def declared_enrich_directives():
    """Enrichment directive ids, parsed from the registry in init/SKILL.md."""
    text = read(os.path.join(SKILLS_DIR, "init", "SKILL.md"))
    section = _section(text, "## Enrichment directive registry")
    return set(re.findall(r"^###\s+`?([a-z_]+)`?", section or "", re.MULTILINE))


def _section(text, heading):
    """Text from `heading` up to the next heading of the same level."""
    start = text.find(heading)
    if start == -1:
        return None
    level = len(heading) - len(heading.lstrip("#"))
    pattern = re.compile(r"^#{1,%d}\s" % level, re.MULTILINE)
    match = pattern.search(text, start + len(heading))
    return text[start : match.start()] if match else text[start:]


def config(name):
    """Load a JSON config file from tests/config/."""
    return read_json(os.path.join(CONFIG_DIR, name))


def detect_stack_tokens():
    """Every stack token kaizen-detect can emit.

    Single source of truth for the suites that check stack coverage (templates,
    standards). Tokens reach the output two ways: appended to the `stacks` array
    for whole-project signals, and echoed by `scan_manifest` for per-manifest
    ones — a workspace scans several manifests, so those cannot use the array.
    """
    text = read(DETECT_BIN)
    tokens = set(re.findall(r'stacks\+=\("([a-z-]+)"\)', text))

    # Only echoes inside scan_manifest are stack tokens; the other helpers echo
    # package managers, maturity levels and CI providers.
    match = re.search(r"^scan_manifest\(\).*?^}", text, re.MULTILINE | re.DOTALL)
    if match:
        tokens |= set(re.findall(r'echo "([a-z][a-z-]*)"', match.group(0)))

    tokens.add("generic")
    return tokens
