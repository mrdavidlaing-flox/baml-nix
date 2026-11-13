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
- **Commands:** only these exact shapes run, and no other flags:
  - `nix build [--no-link] [-L] --file . ATTR`
  - `nix-update [--version=V] ATTR`
  - `nix-prefetch-url [--unpack] https://URL`
  - `nix-prefetch-git [--rev REV] [--fetch-submodules] https://URL [REV]`
  - `git diff [--stat] [-- PATH...]`, which always runs with
    `--no-ext-diff --no-textconv`
  - `git status [--short]`

  Anything else returns exit 126 to the plan, and the attempt fails. Flags
  such as `git diff --output`, `nix-update --run`/`--commit` and
  `nix build --expr`/`--impure` are refused by design.
- **Git's own files:** reading or writing anything under `.git` is refused.
- **Edits:** each edit's `find` text must occur exactly once, or the step
  fails and nothing is written.
- **Retries:** before each retry, the workflow, not the model, restores the
  files the last attempt touched.
- **What's still trusted:** the workflow's own check runs
  `nix build --file <worktree> ATTR` on files the model edited. That
  evaluates Nix code the model wrote. Builds are sandboxed, but evaluation
  can read local files. Review the diff before reusing anything, and run
  the demo on a machine where that's acceptable.

## Tests

`pytest -q tests` runs without a key or network:

- the tools' path jail and command allowlist;
- `ApplyUpdate` against a tiny git repo;
- the retry loop, with a fake planner;
- a full end-to-end run through BAML against `tests/stub_llm.py`, a local
  stand-in for OpenRouter.

The same suite is the flake check `nixpkgs-updater` (`check.nix`).

## Notes

- **BAML version.** `baml.toml` pins `[toolchain] version = "0.25.2"`. The
  Nix `baml` refuses to run this project with any other version.
- **Running inside a coding agent.** `baml-cli` notices agent environments
  (`CLAUDECODE`, `AI_AGENT`, …), and `baml generate` then demands BAML's
  agent skill. Run `baml agent install`, or pass `--agent-skill-check off`.
- **Where BAML comes from.** The manifest installs `baml` and `baml-bridge`
  from `github:mrdavidlaing-flox/baml-nix`, and the committed
  `.flox/env/manifest.lock` pins one commit of it. So the demo uses the
  *pushed* packages, not your working tree. After pushing package changes,
  run `flox upgrade` here and commit the new lock. See
  [flox-python-packages.md](../../docs/decisions/flox-python-packages.md).
- **Python version.** Keep `python314` in the manifest in step with the
  flake's `python3`.
- **Once BAML is in nixpkgs.** Replace the two `flake` lines with
  `baml.pkg-path = "baml"` and
  `baml-bridge.pkg-path = "python314Packages.baml-bridge"`.
