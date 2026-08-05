"""Manifest integrity: the two version numbers users see must agree.

kaizen ships its version in three independent places (plugin.json,
marketplace.json, README). A release that bumps one and forgets another is
invisible until a user installs the wrong thing.
"""

import os
import re

import kzparse as P

REQUIRED_PLUGIN_KEYS = ["name", "description", "version", "author", "homepage", "license"]


def run(r):
    # --- both manifests parse -------------------------------------------
    try:
        plugin = P.read_json(P.PLUGIN_MANIFEST)
        r.ok("plugin.json is valid JSON")
    except ValueError as exc:
        r.fail("plugin.json is not valid JSON", exc)
        return

    try:
        market = P.read_json(P.MARKETPLACE_MANIFEST)
        r.ok("marketplace.json is valid JSON")
    except ValueError as exc:
        r.fail("marketplace.json is not valid JSON", exc)
        return

    # --- required keys ---------------------------------------------------
    for key in REQUIRED_PLUGIN_KEYS:
        r.check(key in plugin, "plugin.json has `%s`" % key)

    version = plugin.get("version", "")
    r.check(
        re.match(r"^\d+\.\d+\.\d+$", version) is not None,
        "plugin.json version is semver (%s)" % version,
    )

    # --- marketplace entry ------------------------------------------------
    entries = market.get("plugins", [])
    r.check(len(entries) >= 1, "marketplace.json lists at least one plugin")
    entry = next((e for e in entries if e.get("name") == plugin.get("name")), None)
    if not r.check(
        entry is not None,
        "marketplace.json has an entry named `%s`" % plugin.get("name"),
    ):
        return

    r.check(
        entry.get("version") == version,
        "marketplace.json version matches plugin.json",
        "marketplace.json=%s  plugin.json=%s" % (entry.get("version"), version),
    )
    r.check(
        entry.get("description") == plugin.get("description"),
        "marketplace.json description matches plugin.json",
    )

    source = entry.get("source", "")
    source_path = os.path.normpath(os.path.join(P.REPO_ROOT, source))
    r.check(
        os.path.isdir(source_path),
        "marketplace source path exists (%s)" % source,
    )
    r.check(
        os.path.isfile(os.path.join(source_path, ".claude-plugin", "plugin.json")),
        "marketplace source points at a directory containing plugin.json",
    )

    # --- README + CHANGELOG agree with the shipped version ----------------
    readme = P.read(os.path.join(P.REPO_ROOT, "README.md"))
    claimed = re.search(r"What it does today \(v([\d.]+)\)", readme)
    if claimed:
        r.check(
            claimed.group(1) == version,
            "README 'What it does today' version matches plugin.json",
            "README claims v%s, plugin.json is %s" % (claimed.group(1), version),
        )
    else:
        r.warn("README has no 'What it does today (vX.Y.Z)' heading to check")

    changelog = P.read(os.path.join(P.REPO_ROOT, "CHANGELOG.md"))
    r.check(
        ("## [%s]" % version) in changelog or ("## %s" % version) in changelog,
        "CHANGELOG has an entry for v%s" % version,
    )

    # --- plugin-level settings/mcp are valid and point at real files ------
    settings_path = os.path.join(P.PLUGIN_ROOT, "settings.json")
    if os.path.isfile(settings_path):
        try:
            settings = P.read_json(settings_path)
            r.ok("plugin settings.json is valid JSON")
        except ValueError as exc:
            r.fail("plugin settings.json is not valid JSON", exc)
            settings = {}
        command = (settings.get("subagentStatusLine") or {}).get("command", "")
        if command:
            script = command.replace("${CLAUDE_PLUGIN_ROOT}", P.PLUGIN_ROOT)
            r.check(
                os.path.isfile(script),
                "subagentStatusLine command exists",
                script,
            )
            r.check(
                os.access(script, os.X_OK),
                "subagentStatusLine command is executable",
                script,
            )

    mcp_path = os.path.join(P.PLUGIN_ROOT, ".mcp.json")
    if os.path.isfile(mcp_path):
        try:
            mcp = P.read_json(mcp_path)
            r.ok(".mcp.json is valid JSON")
            # Documented invariant: kaizen activates no MCP server for users.
            r.check_warn(
                not mcp.get("mcpServers"),
                ".mcp.json ships no active MCP servers (documented invariant)",
                "found: %s" % ", ".join(sorted(mcp.get("mcpServers", {}))),
            )
        except ValueError as exc:
            r.fail(".mcp.json is not valid JSON", exc)
