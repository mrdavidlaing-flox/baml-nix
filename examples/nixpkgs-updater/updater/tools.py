"""Callbacks handed to the BAML ApplyUpdate function.

Everything is confined to one nixpkgs worktree: paths may not leave it, and
only a short list of commands may run.
"""

from __future__ import annotations

import os
import re
import shlex
import subprocess
from pathlib import Path

import baml_sdk

# Each allowed command, with exactly the flags it may take. Anything else (an
# unknown flag, a path or URL of the wrong kind) is refused: prefix matching is
# not enough, since flags like `git diff --output=…` or `nix-update --run`
# write outside the worktree or run code.
ALLOWED_SHAPES = (
    "nix build [--no-link] [-L] --file . ATTR",
    "nix-update [--version=V | --version V] ATTR",
    "nix-prefetch-url [--unpack] https://URL",
    "nix-prefetch-git [--rev REV] [--fetch-submodules] https://URL [REV]",
    "git diff [--stat] [-- PATH...]",
    "git status [--short]",
)

ATTR = re.compile(r"^[A-Za-z_][A-Za-z0-9_+-]*(\.[A-Za-z0-9_+-]+)*$")
VERSION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]*$")
HTTPS = re.compile(r"^https://[^\s]+$")

MAX_OUTPUT_CHARS = 20_000


def nix_env(base: dict[str, str] | None = None) -> dict[str, str]:
    """The environment for subprocesses, with `nix-command` enabled.

    The workflow runs `nix eval` and `nix build`, and nix-update calls `nix`
    too; many installs leave that feature off. NIX_CONFIG adds to the user's
    configuration rather than replacing it.
    """
    env = dict(os.environ if base is None else base)
    extra = "extra-experimental-features = nix-command"
    env["NIX_CONFIG"] = f"{env['NIX_CONFIG']}\n{extra}" if env.get("NIX_CONFIG") else extra
    return env


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
        if ".git" in target.relative_to(self.root).parts:
            raise ToolRefused(f"{path} is inside git's own files")
        return target

    def refusal(self, argv: list[str]) -> str | None:
        """Why `argv` may not run, or None if it matches an allowed shape."""
        ok = self._allowed(argv)
        if ok:
            return None
        return f"command not allowed: {shlex.join(argv) or '(empty)'}; allowed: " + "; ".join(ALLOWED_SHAPES)

    def _allowed(self, argv: list[str]) -> bool:
        match argv:
            case ["nix", "build", *rest]:
                rest = [a for a in rest if a not in ("--no-link", "-L")]
                return len(rest) == 3 and rest[:2] == ["--file", "."] and bool(ATTR.match(rest[2]))
            case ["nix-update", *rest]:
                if len(rest) >= 2 and rest[0] == "--version":
                    rest = [f"--version={rest[1]}", *rest[2:]]
                if rest and rest[0].startswith("--version="):
                    if not VERSION.match(rest[0].removeprefix("--version=")):
                        return False
                    rest = rest[1:]
                return len(rest) == 1 and bool(ATTR.match(rest[0]))
            case ["nix-prefetch-url", *rest]:
                rest = [a for a in rest if a != "--unpack"]
                return len(rest) == 1 and bool(HTTPS.match(rest[0]))
            case ["nix-prefetch-git", *rest]:
                positional = []
                i = 0
                while i < len(rest):
                    if rest[i] == "--rev" and i + 1 < len(rest) and VERSION.match(rest[i + 1]):
                        i += 2
                    elif rest[i] == "--fetch-submodules":
                        i += 1
                    elif rest[i].startswith("-"):
                        return False
                    else:
                        positional.append(rest[i])
                        i += 1
                return (
                    1 <= len(positional) <= 2
                    and bool(HTTPS.match(positional[0]))
                    and all(VERSION.match(p) for p in positional[1:])
                )
            case ["git", "diff", *rest]:
                rest = [a for a in rest if a != "--stat"]
                if not rest:
                    return True
                if rest[0] != "--":
                    return False
                try:
                    for path in rest[1:]:
                        self.resolve(path)
                except ToolRefused:
                    return False
                return True
            case ["git", "status", *rest]:
                return rest in ([], ["--short"])
        return False

    def read_file(self, path: str) -> str:
        return self.resolve(path).read_text()

    def write_file(self, path: str, contents: str) -> None:
        self.resolve(path).write_text(contents)

    def run_command(self, argv: list[str]) -> baml_sdk.CommandResult:
        refused = self.refusal(argv)
        if refused:
            return baml_sdk.CommandResult(exit_code=126, output=refused)
        if argv[:2] == ["git", "diff"]:
            # Never run diff drivers or textconv filters from the repo's config.
            argv = ["git", "--no-pager", "diff", "--no-ext-diff", "--no-textconv", *argv[2:]]
        try:
            done = subprocess.run(
                argv,
                cwd=self.root,
                env=nix_env(),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=self.timeout_s,
            )
        except (OSError, subprocess.TimeoutExpired) as e:
            return baml_sdk.CommandResult(exit_code=127, output=str(e))
        return baml_sdk.CommandResult(exit_code=done.returncode, output=tail(done.stdout))
