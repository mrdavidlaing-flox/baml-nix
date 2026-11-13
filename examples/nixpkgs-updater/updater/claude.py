"""PlanUpdate through the local Claude Code CLI and its login.

BAML has a Claude Code client built in (claude_code.ClaudeCodeClient): it
runs `claude -p` with no tools, sends the rendered prompt as stream-json, and
passes UpdatePlan's schema as --json-schema, so the reply is structured
output rather than parsed prose. The call counts against whatever Claude Code
is logged in with: a Claude Pro/Max subscription or an API key.

This module only builds that client at run time, so the model and the
executable can be chosen, and Claude starts in an empty directory (no
project CLAUDE.md or settings from wherever the workflow runs).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile

import baml_sdk
from baml_sdk.vendor.claude_code import ClaudeCodeClient

DEFAULT_MODEL = "sonnet"


def claude_bin() -> str:
    """The Claude Code executable: $CLAUDE_BIN if set (the tests use a fake), else `claude`."""
    return os.environ.get("CLAUDE_BIN") or "claude"


def preflight() -> str | None:
    """Why Claude Code can't be used, or None if it is installed and logged in."""
    exe = shutil.which(claude_bin())
    if exe is None:
        return f"{claude_bin()} not found on PATH; install Claude Code and run `claude auth login`"
    status = subprocess.run(
        [exe, "auth", "status", "--json"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True
    )
    try:
        logged_in = status.returncode == 0 and json.loads(status.stdout).get("loggedIn") is True
    except ValueError:
        logged_in = False
    if not logged_in:
        return "Claude Code is not logged in; run `claude auth login`"
    return None


def plan_update(
    attr: str,
    current_version: str,
    package_nix: str,
    package_path: str,
    previous_errors: list[str],
    model: str | None = None,
) -> baml_sdk.UpdatePlan:
    spec = baml_sdk.plan_update_spec_sync(attr, current_version, package_nix, package_path, previous_errors)
    with tempfile.TemporaryDirectory(prefix="baml-updater-claude-") as empty:
        client = ClaudeCodeClient.new_sync(model=model or DEFAULT_MODEL, executable=claude_bin(), cwd=empty)
        return spec.call_sync(client=client)
