"""The orchestration: plan, apply, check, and retry with the errors."""

from __future__ import annotations

import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal, Protocol

import baml_sdk

from .tools import ToolRefused, Tools, tail


@dataclass(frozen=True)
class Outcome:
    attr: str
    from_version: str
    to_version: str | None
    status: Literal["updated", "failed", "current"]
    detail: str


class Client(Protocol):
    def plan_update(
        self, attr: str, current_version: str, package_nix: str, package_path: str, previous_errors: list[str]
    ) -> baml_sdk.UpdatePlan: ...

    def apply_update(self, plan: baml_sdk.UpdatePlan, tools: Tools) -> baml_sdk.ApplyResult: ...


class BamlClient:
    """The real thing: PlanUpdate asks the LLM, ApplyUpdate is plain BAML."""

    def plan_update(self, attr, current_version, package_nix, package_path, previous_errors):
        return baml_sdk.plan_update_sync(attr, current_version, package_nix, package_path, previous_errors)

    def apply_update(self, plan, tools):
        return baml_sdk.apply_update_sync(plan, tools.read_file, tools.write_file, tools.run_command)


Check = Callable[[str], baml_sdk.CommandResult]
Locate = Callable[[str], tuple[str, str]]


def restore(worktree: Path, tools: Tools, paths: set[str]) -> None:
    """Undo edits from a failed attempt (Python does this, not the model)."""
    for path in sorted(paths):
        try:
            tools.resolve(path)
        except ToolRefused:
            continue
        subprocess.run(
            ["git", "-C", str(worktree), "checkout", "--", path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def run(
    packages: list[str],
    worktree: Path,
    client: Client,
    check: Check,
    locate: Locate,
    max_attempts: int = 3,
) -> list[Outcome]:
    tools = Tools(worktree)
    outcomes: list[Outcome] = []
    for attr in packages:
        try:
            path, version = locate(attr)
        except LookupError as e:
            outcomes.append(Outcome(attr, "?", None, "failed", str(e)))
            continue

        errors: list[str] = []
        touched = {path}
        outcome = None
        for attempt in range(1, max_attempts + 1):
            if attempt > 1:
                restore(worktree, tools, touched)
            try:
                plan = client.plan_update(attr, version, tools.read_file(path), path, errors)
            except Exception as e:  # LLM, network or parse failure: count it as an attempt
                errors.append(f"attempt {attempt}: planning failed: {e}")
                continue
            if not plan.needs_update:
                outcome = Outcome(attr, version, version, "current", plan.reasoning)
                break
            touched |= {edit.path for edit in plan.edits}
            try:
                result = client.apply_update(plan, tools)
            except Exception as e:
                errors.append(f"attempt {attempt}: applying the plan failed: {e}")
                continue
            if not result.ok:
                errors.append(f"attempt {attempt}: step '{result.failed_step}' failed:\n{result.failed_output}")
                continue
            built = check(attr)
            if built.exit_code == 0:
                outcome = Outcome(attr, version, plan.target_version, "updated", "; ".join(result.steps_done))
                break
            errors.append(f"attempt {attempt}: nix build of {attr} failed:\n{built.output}")

        if outcome is None:
            restore(worktree, tools, touched)
            outcome = Outcome(attr, version, None, "failed", errors[-1] if errors else "no attempts made")
        outcomes.append(outcome)
    return outcomes


# --- Real nixpkgs plumbing ----------------------------------------------------


def create_worktree(nixpkgs: Path, run_id: str) -> Path:
    path = Path(tempfile.gettempdir()) / f"baml-updater-{run_id}"
    subprocess.run(
        ["git", "-C", str(nixpkgs), "worktree", "add", "-q", "-b", f"baml-updater/{run_id}", str(path), "HEAD"],
        check=True,
    )
    return path


def nix_locate(worktree: Path) -> Locate:
    def locate(attr: str) -> tuple[str, str]:
        def nix_eval(expr: str) -> str:
            done = subprocess.run(
                ["nix", "eval", "--raw", "--file", str(worktree), expr],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if done.returncode != 0:
                raise LookupError(f"{attr}: {done.stderr.strip().splitlines()[-1] if done.stderr.strip() else 'not found'}")
            return done.stdout

        position = nix_eval(f"{attr}.meta.position")
        file = Path(position.rsplit(":", 1)[0]).resolve()
        if not file.is_relative_to(worktree.resolve()):
            raise LookupError(f"{attr}: defined outside the worktree ({file})")
        return str(file.relative_to(worktree.resolve())), nix_eval(f"{attr}.version")

    return locate


def nix_check(worktree: Path) -> Check:
    def check(attr: str) -> baml_sdk.CommandResult:
        done = subprocess.run(
            ["nix", "build", "--file", str(worktree), attr, "--no-link"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        return baml_sdk.CommandResult(exit_code=done.returncode, output=tail(done.stdout))

    return check
