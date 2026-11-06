"""Callbacks handed to the BAML ApplyUpdate function.

Everything is confined to one nixpkgs worktree: paths may not leave it, and
only a short list of commands may run.
"""

from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

import baml_sdk

ALLOWED_COMMANDS: tuple[tuple[str, ...], ...] = (
    ("nix", "build"),
    ("nix-prefetch-url",),
    ("nix-prefetch-git",),
    ("nix-update",),
    ("git", "diff"),
    ("git", "status"),
)

MAX_OUTPUT_CHARS = 20_000


class ToolRefused(Exception):
    """A callback refused to act (path outside the worktree)."""


def tail(text: str) -> str:
    return text if len(text) <= MAX_OUTPUT_CHARS else "…" + text[-MAX_OUTPUT_CHARS:]


class Tools:
    def __init__(self, worktree: Path, timeout_s: int = 3600):
        self.root = Path(worktree).resolve()
        self.timeout_s = timeout_s

    def resolve(self, path: str) -> Path:
        target = (self.root / path).resolve()
        if not target.is_relative_to(self.root):
            raise ToolRefused(f"{path} is outside the worktree")
        return target

    def read_file(self, path: str) -> str:
        return self.resolve(path).read_text()

    def write_file(self, path: str, contents: str) -> None:
        self.resolve(path).write_text(contents)

    def run_command(self, argv: list[str]) -> baml_sdk.CommandResult:
        if not any(tuple(argv[: len(prefix)]) == prefix for prefix in ALLOWED_COMMANDS):
            allowed = ", ".join(" ".join(p) for p in ALLOWED_COMMANDS)
            return baml_sdk.CommandResult(
                exit_code=126,
                output=f"command not allowed: {shlex.join(argv) or '(empty)'}; allowed: {allowed}",
            )
        try:
            done = subprocess.run(
                argv,
                cwd=self.root,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=self.timeout_s,
            )
        except (OSError, subprocess.TimeoutExpired) as e:
            return baml_sdk.CommandResult(exit_code=127, output=str(e))
        return baml_sdk.CommandResult(exit_code=done.returncode, output=tail(done.stdout))
