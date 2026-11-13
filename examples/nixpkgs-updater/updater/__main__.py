"""python -m updater [--nixpkgs PATH] [--model MODEL] ATTR..."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

from . import claude, workflow


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m updater", description=__doc__)
    parser.add_argument("--nixpkgs", type=Path, default=Path.home() / "Work" / "nixpkgs")
    parser.add_argument("--model", help="Claude model for PlanUpdate (default: sonnet)")
    parser.add_argument("attrs", nargs="+", metavar="ATTR")
    args = parser.parse_args(argv)

    problem = claude.preflight()
    if problem:
        print(f"error: {problem}", file=sys.stderr)
        return 2

    run_id = time.strftime("%Y%m%d-%H%M%S")
    worktree = workflow.create_worktree(args.nixpkgs, run_id)
    outcomes = workflow.run(
        args.attrs,
        worktree,
        workflow.BamlClient(args.model),
        workflow.nix_check(worktree),
        workflow.nix_locate(worktree),
    )

    width = max(len(o.attr) for o in outcomes)
    for o in outcomes:
        change = f"{o.from_version} -> {o.to_version}" if o.status == "updated" else o.from_version
        print(f"{o.attr:<{width}}  {o.status:<8} {change}")
        if o.status == "failed":
            print("    " + o.detail.strip().replace("\n", "\n    "))
    print(f"\nworktree: {worktree} (branch baml-updater/{run_id}; nothing committed or pushed)")
    subprocess.run(["git", "-C", str(worktree), "diff", "--stat"])
    return 0 if all(o.status != "failed" for o in outcomes) else 1


if __name__ == "__main__":
    sys.exit(main())
