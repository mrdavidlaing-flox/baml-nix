# nixpkgs-updater: a BAML + Python demo

A Python workflow that bumps nixpkgs packages to their latest upstream
release. It uses two BAML functions:

- **`PlanUpdate`** (`baml_src/plan.baml`) asks GPT-6 Luna, through
  OpenRouter, for an exact update plan: the edits, the hash refetches and
  the risks.
- **`ApplyUpdate`** (`baml_src/apply.baml`) is plain BAML code with no LLM.
  It carries out the plan through Python callbacks (`updater/tools.py`) that
  can only touch one throwaway nixpkgs worktree and run a short list of
  commands.

`updater/workflow.py` runs plan → apply → `nix build` for each package. If
the build fails, it feeds the error into a fresh plan, up to 3 attempts per
package.

## Run it

```sh
cd examples/nixpkgs-updater
flox activate                      # Python 3.14, baml, baml-bridge
baml generate                      # writes baml_sdk/ (not committed)
export OPENROUTER_API_KEY=sk-or-…
python -m updater --nixpkgs ~/Work/nixpkgs jq ripgrep
```

It prints one line per package (`updated`, `failed` or `current`) and the
`git diff --stat`. All changes land in a new worktree,
`$TMPDIR/baml-updater-<timestamp>`, on branch `baml-updater/<timestamp>`.
**Nothing is committed or pushed.** Review the diff, then keep or drop the
branch:

```sh
git -C ~/Work/nixpkgs worktree remove /tmp/baml-updater-<timestamp>
git -C ~/Work/nixpkgs branch -D baml-updater/<timestamp>
```

Each package costs up to three `PlanUpdate` calls; GPT-6 Luna is cheap
($0.10 / $0.50 per million input/output tokens when checked).

## Safety limits

- **Files:** paths that resolve outside the worktree, including through
  symlinks, are refused.
- **Commands:** only `nix build`, `nix-prefetch-url`, `nix-prefetch-git`,
  `nix-update`, `git diff` and `git status` run. Anything else returns exit
  126 to the plan, and the attempt fails.
- **Edits:** each edit's `find` text must occur exactly once, or the step
  fails and nothing is written.
- **Retries:** before each retry, the workflow, not the model, restores the
  files the last attempt touched.

## Tests

`pytest -q tests` runs without a key or network:

- the tools' path jail and command allowlist;
- `ApplyUpdate` against a tiny git repo;
- the retry loop, with a fake planner;
- a full end-to-end run through BAML against `tests/stub_llm.py`, a local
  stand-in for OpenRouter.

The same suite is the flake check `nixpkgs-updater` (`check.nix`).

## Notes

- **BAML version.** `baml.toml` pins `[toolchain] version = "0.24.0"`. The
  Nix `baml` refuses to run this project with any other version.
- **Running inside a coding agent.** `baml-cli` notices agent environments
  (`CLAUDECODE`, `AI_AGENT`, …), and `baml generate` then demands BAML's
  agent skill. Run `baml agent install`, or pass `--agent-skill-check off`.
- **Flox lock file.** `.flox/env/manifest.lock` isn't committed: it records
  the flake's absolute path and content hash. See
  [flox-python-packages.md](../../docs/decisions/flox-python-packages.md).
- **Python version.** Keep `python314` in the manifest in step with the
  flake's `python3`.
- **Once BAML is in nixpkgs.** Replace the two `flake` lines with
  `baml.pkg-path = "baml"` and
  `baml-bridge.pkg-path = "python314Packages.baml-bridge"`.
