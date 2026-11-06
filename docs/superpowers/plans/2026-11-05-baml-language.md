# New BAML language for Nix and Flox: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Package the new BAML language (`baml-cli` toolchain, `baml` launcher, `python3Packages.baml-bridge`) from source in nixpkgs style. Demonstrate it with a Flox-based Python workflow that uses two BAML functions to bump nixpkgs packages. Prepare a nixpkgs branch David can submit.

**Architecture:**
- **Packages.** Plain `callPackage` files under `pkgs/`, wired into the flake through an overlay (the v0 pattern; nixos-unstable is the only input). The three packages build from one `fetchFromGitHub` of tag `baml-language-0.24.0`, with one shared `cargoDeps` (the workspace has one `Cargo.lock`).
- **Launcher.** `baml` wraps the packaged toolchain and enforces the version policy. A spike (Task 2) settles the mechanism.
- **Demo.** `examples/nixpkgs-updater/`: a BAML project with two functions (`PlanUpdate` calls the LLM; `ApplyUpdate` is plain BAML code), a Python orchestrator, and Python callbacks jailed to a throwaway nixpkgs worktree.

**Tech Stack:** Nix flakes, nixpkgs `rustPlatform` / `buildPythonPackage` + `maturinBuildHook`, Flox 1.19.1, BAML language 0.24.0, Python 3.14 (3.13 fallback), pytest, OpenRouter (OpenAI-compatible).

**Spec:** `docs/superpowers/specs/2026-11-05-baml-language-design.md`

## Global Constraints

**Source and build**
- Source: `fetchFromGitHub { owner = "BoundaryML"; repo = "baml"; tag = "baml-language-${version}"; }` with version `0.24.0`, commit `dec4713a0e7c9699442bf5855b4f327063f769c5`. The Cargo workspace root is `baml_language/`.
- Set `env.BAML_GIT_SHA = "dec4713a0e7c9699442bf5855b4f327063f769c5"`. `baml_artifact/build.rs` requires it when there's no `.git`.
- Build from source only. Never download a toolchain, runtime or pack host, at build time or run time.
- Package files: no fenix, crane, flake inputs or `self`. They must be `callPackage`-able unchanged from nixpkgs. Repo copies keep `maintainers = [ ]`.
- Don't strip the packed `baml` launcher (`dontStrip = true` on that derivation). Stripping destroys its payload.
- Never pass `--embed-telemetry`.

**Platforms**
- `meta.platforms = lib.platforms.linux ++ lib.platforms.darwin`.
- The flake covers `x86_64-linux`, `aarch64-linux` and `aarch64-darwin`.

**Versioning**
- Tests take versions from the package (`${pkg.version}`), never literals.
- `updateScript` regex: `^baml-language-([0-9]+\.[0-9]+\.[0-9]+)$`.

**Version policy**
- A project `[toolchain]` with no table runs.
- `version` equal to the packaged version runs.
- A different `version` fails, naming both versions.
- Any `channel` fails.
- A `path` is honoured.
- A user-set `BAML_TOOLCHAIN` is honoured.

**Demo**
- LLM: client `OpenRouterLuna`, an OpenAI-compatible endpoint at `https://openrouter.ai/api/v1`, model `gpt-6-luna` (or the exact id OpenRouter lists, found in Task 2), key from env `OPENROUTER_API_KEY`.
- `ApplyUpdate` makes **no** LLM call. Only `PlanUpdate` does.
- Edits happen only inside a `git worktree` of the nixpkgs checkout (default `~/Work/nixpkgs`), on branch `baml-updater/<run-id>`. Never commit to existing branches, and never push.
- The `run_command` allowlist (exact argv prefixes): `nix build`, `nix-prefetch-url`, `nix-prefetch-git`, `nix-update`, `git diff`, `git status`.
- Maximum 3 plan attempts per package.

**Process**
- Never push anything anywhere. David submits the nixpkgs PR.

## Review Focus

1. **Bad find text.** The plan's `find` text occurs 0 or ≥2 times in the file. Expect the step to fail with a message saying which, nothing written, and the error fed into the next `PlanUpdate`. Test: `test_edit_find_must_match_exactly_once` (Task 5).
2. **Path outside the worktree.** The model proposes a path outside the worktree (`../x`, `/etc/x`, a symlink escape). Expect the callback to refuse and the attempt to fail cleanly. Test: `test_paths_outside_worktree_refused` (Task 5).
3. **Retry starts from a dirty tree.** A retry must not start from the previous attempt's half-applied edits. Expect the workflow to restore the package's files (`git checkout -- <files>` run by Python, not the model) before each attempt. Test: `test_retry_starts_from_clean_tree` (Task 5).
4. **Missing API key.** `OPENROUTER_API_KEY` is unset. Expect a clear error before any worktree is created. Test: `test_missing_api_key_fails_before_worktree` (Task 6).
5. **Unknown attribute.** An unknown or typo'd attribute is reported as `failed` with the reason, and the loop goes on to the next package. Test: `test_unknown_attr_reported_and_loop_continues` (Task 5).

---

### Task 1: Flake skeleton and the `baml-cli` toolchain package

**Files:**
- Create: `flake.nix`, `flake.lock`, `.gitignore` (`result`, `result-*`)
- Create: `pkgs/baml-cli/package.nix`
- Create: `pkgs/baml-cli/tests/version.nix`

**Interfaces:**
- Produces: `pkgs.baml-cli`, with `bin/baml-cli` and `bin/baml-pack-host`. It exposes `src`, `version` and `cargoDeps` for reuse.
- Produces: the flake's `overlays.default` (adds `baml-cli`; later tasks add `baml` and the `pythonPackagesExtensions` entry `baml-bridge`), `packages.<system>.baml-cli`, and `checks.<system>.baml-cli-version`.

- [ ] **Step 1: Write the failing check.** `tests/version.nix` (a `runCommand`) runs `baml-cli --version` and requires `${baml-cli.version}` in the output. It also requires `${baml-cli}/bin/baml-pack-host` to exist and be executable. Wire it in as `checks.<system>.baml-cli-version`.
- [ ] **Step 2: Run it to verify it fails.** Run `nix flake check -L`. Expected: FAIL, because `pkgs/baml-cli/package.nix` is missing.
- [ ] **Step 3: Implement `pkgs/baml-cli/package.nix`.**
  - `rustPlatform.buildRustPackage (finalAttrs: …)`, with `cargoRoot = buildAndTestSubdir = "baml_language"`.
  - `cargoBuildFlags = [ "--bin" "baml-cli" "--bin" "baml-pack-host" ]`, plus `env.BAML_GIT_SHA`.
  - Copy any `rustflags` from `baml_language/.cargo/config.toml` that apply to native targets into `env.RUSTFLAGS`.
  - Add native inputs only as the build demands (start with none; v0 needed none).
  - `doCheck = false` with a comment naming why; check whether the `baml_cli` crate has tests.
  - `versionCheckHook`, and `passthru.updateScript = nix-update-script { extraArgs = [ "--version-regex" "^baml-language-([0-9]+\\.[0-9]+\\.[0-9]+)$" ]; }`.
  - Start the hashes at `lib.fakeHash` and fill them in from the build errors.
- [ ] **Step 4: Run it to verify it passes.** Run `nix flake check -L && nix flake check --all-systems --no-build`. Expected: the check passes, and all three systems evaluate.
- [ ] **Step 5: Commit.** `feat: package baml-cli (BAML language toolchain) 0.24.0`

### Task 2: Spikes: version-policy mechanism, OpenRouter model id

Throwaway code. This task produces decisions.

**Files:**
- Create: `docs/decisions/baml-version-policy.md`
- Create: `docs/decisions/openrouter-model.md`

**Interfaces:**
- Consumes: Task 1's `baml-cli`.
- Produces: the chosen **launcher mechanism**, recorded with the exact error text for a mismatch, and the exact **OpenRouter model id**. Task 3 and Task 5 use them verbatim.

- [ ] **Step 1: Find out what upstream does.** With Task 1's build, run `python3 baml_language/wrapper/build --cli <baml-cli> --pack-host <baml-pack-host> --version 0.24.0 --no-self-update --output $TMPDIR/baml`. Do this from an unpacked copy of the source, in a scratch dir, with network off (`unshare -n` or the Nix sandbox). Record whether it builds offline.
- [ ] **Step 2: Try the five policy cases.** Create five scratch projects:
  - no `[toolchain]`
  - `version = "0.24.0"`
  - `version = "0.23.0"`
  - `channel = "stable"`
  - `path = "<baml-cli>"`

  Run `BAML_TOOLCHAIN=<baml-cli> $TMPDIR/baml check` in each, without network. Record which cases already behave as the policy requires, and whether any case tries the network.
- [ ] **Step 3: Choose the smallest mechanism that meets the policy.** One of:
  - (a) the upstream launcher behind a `makeWrapper` shim that reads the nearest `baml.toml` `[toolchain]` and exits 1 on a mismatch;
  - (b) `baml-cli` exposed as `baml` behind that same shim, with no launcher build;
  - (c) a patch to `wrapper/baml_src/selectors.baml`.

  Prefer (b) if the launcher adds nothing a Nix user needs. Write `docs/decisions/baml-version-policy.md` with the choice, why, the exact mismatch error text, and what the user-set `BAML_TOOLCHAIN` case does.
- [ ] **Step 4: Find the model id.** Run `curl -s https://openrouter.ai/api/v1/models | jq -r '.data[].id' | grep -i luna`. Write `docs/decisions/openrouter-model.md` with the exact id, or with "not listed" and the closest ids. If it isn't listed, stop and ask David which model to use before Task 5 Step 3 (this is the plan's only planned stop).
- [ ] **Step 5: Commit the decisions.** Delete the scratch files, then commit with `docs: decide BAML version-policy mechanism and OpenRouter model`.

### Task 3: The `baml` launcher package with the version policy

**Files:**
- Create: `pkgs/baml/package.nix`
- Create: `pkgs/baml/tests/policy.nix` (plus fixture projects under `pkgs/baml/tests/projects/{none,match,mismatch,channel,path}/baml.toml`)
- Modify: `flake.nix` (add `baml` to the overlay, packages and checks)

**Interfaces:**
- Consumes: Task 1's `baml-cli` (`src`, `version`, `cargoDeps`, bins), and Task 2's mechanism and error text.
- Produces: `pkgs.baml`, with `bin/baml` (`meta.mainProgram = "baml"`) and `passthru.tests.policy`.

- [ ] **Step 1: Write the failing policy test.** `tests/policy.nix` runs `baml --version`, then `baml check` (or the cheapest command Task 2 found that triggers toolchain selection) in each fixture, offline, with these assertions:
  - `none` → exit 0
  - `match` (`version = "${baml.version}"`) → exit 0
  - `mismatch` (`version = "0.0.1"`) → exit ≠ 0, and stderr contains both `0.0.1` and `${baml.version}`
  - `channel` → exit ≠ 0
  - `path` (points at `${baml-cli}/bin/baml-cli`) → exit 0
  - `BAML_TOOLCHAIN=${baml-cli}/bin/baml-cli` with the `mismatch` fixture → behaves as `docs/decisions/baml-version-policy.md` says, asserted exactly
- [ ] **Step 2: Run it to verify it fails.** Run `nix build .#checks.x86_64-linux.baml-policy -L`. Expected: FAIL, because `baml` is undefined.
- [ ] **Step 3: Implement `pkgs/baml/package.nix`** using Task 2's mechanism. Include `dontStrip = true` if it packs the launcher. If the mechanism is a shim, make it a small POSIX shell script installed with `makeWrapper`, with no runtime dependencies beyond coreutils/grep/sed. It reads the nearest `baml.toml`'s `[toolchain]` table, walking up from the cwd or `--project`.
- [ ] **Step 4: Run it to verify it passes.** Run `nix flake check -L`. Expected: all policy assertions pass.
- [ ] **Step 5: Commit.** `feat: package baml launcher with Nix version policy`

### Task 4: `python3Packages.baml-bridge`

**Files:**
- Create: `pkgs/python-modules/baml-bridge/default.nix`
- Create: `pkgs/python-modules/baml-bridge/tests/generate.nix`, `tests/fixture/` (a minimal project: `baml.toml` with a `[generator.python]` `output_type = "python/pydantic"`, plus `baml_src/main.baml` with one function and one class)
- Modify: `flake.nix` (add the `pythonPackagesExtensions` entry, `packages.<system>.baml-bridge`, and checks)

**Interfaces:**
- Consumes: Task 1's `src`, `version` and `cargoDeps`, and Task 3's `baml`.
- Produces: `python3Packages.baml-bridge` (import `baml_bridge`) and `passthru.tests.generate`. It also produces the generated-SDK import name used in Task 5, `baml_sdk` by default; record it if the fixture sets `package_name`.

- [ ] **Step 1: Write the failing check.** `tests/generate.nix` uses `python.withPackages (ps: [ ps.baml-bridge ])` plus `baml`. Offline, it runs the generate command (`baml generate`, or what Task 2/3 established) on the fixture, then runs Python that asserts:
  - `import baml_sdk` succeeds;
  - the fixture's function is an attribute of the SDK's sync client;
  - `importlib.metadata.version("baml_bridge") == "${baml-bridge.version}"`.
- [ ] **Step 2: Run it to verify it fails.** Run `nix flake check -L`. Expected: FAIL, because `baml-bridge` is undefined.
- [ ] **Step 3: Implement `default.nix`.**
  - `buildPythonPackage`, `pyproject = true`, `inherit (baml-cli) version src cargoDeps;`.
  - `sourceRoot = "${src.name}/baml_language"`, and `buildAndTestSubdir = "sdks/python"`. Maturin reads `manifest-path` from that `pyproject.toml`; if the hook needs the crate path instead, use `rust/bridge_python` and record a ruling.
  - `dependencies = [ protobuf pydantic typing-extensions ]`, `pythonImportsCheck = [ "baml_bridge" ]`, and `env.BAML_GIT_SHA`.
  - **Python 3.14:** build the default `python3Packages` first. If the build or import fails on 3.14 because of the bridge itself (not our packaging), set `disabled = pythonAtLeast "3.14";`, build `python313Packages.baml-bridge`, and record a ruling. Task 6 then pins `python313`.
- [ ] **Step 4: Run it to verify it passes.** Run `nix flake check -L`. Expected: the generate test prints the SDK import and passes.
- [ ] **Step 5: Commit.** `feat: package python3Packages.baml-bridge 0.24.0`

### Task 5: The demo's BAML functions and Python workflow, with an offline check

**Files (all under `examples/nixpkgs-updater/`):**
- Create: `baml.toml` (generator `python/pydantic`, `output_dir = "."`, and `[toolchain] version = "0.24.0"`)
- Create: `baml_src/clients.baml` (`OpenRouterLuna`)
- Create: `baml_src/plan.baml` (types and `PlanUpdate`)
- Create: `baml_src/apply.baml` (`ApplyUpdate`)
- Create: `updater/tools.py`, `updater/workflow.py`, `updater/__main__.py`
- Create: `tests/test_tools.py`, `tests/test_workflow.py`, `tests/stub_llm.py`
- Create: `check.nix`, wired into the flake as `checks.<system>.nixpkgs-updater`

**Interfaces:**
- Consumes: Task 4's SDK import name, Task 2's model id, and Task 3/4's `baml` and `baml-bridge`.
- Produces these BAML types and functions (exact names; field types in BAML syntax):
  - `class Edit { path string  find string  replace string }`, where `path` is relative to the worktree.
  - `class UpdatePlan { attr string  current_version string  target_version string  needs_update bool  edits Edit[]  commands string[][]  risks string[]  reasoning string }`
  - `class CommandResult { exit_code int  output string }`
  - `class ApplyResult { ok bool  steps_done string[]  failed_step string?  failed_output string? }`
  - `function PlanUpdate(attr: string, current_version: string, package_nix: string, previous_errors: string[]) -> UpdatePlan`, using client `OpenRouterLuna`.
  - `function ApplyUpdate(plan: UpdatePlan, read_file: <(path: string) -> string>, write_file: <(path: string, contents: string) -> null>, run_command: <(argv: string[]) -> CommandResult>) -> ApplyResult`. It's plain BAML code with no `client`. Use BAML's function-type syntax for the three callbacks, per `baml_language/sdks/python/README.md` § Python callback execution and the sdk_tests fixtures.
- Produces these Python names:
  - `updater.tools.Tools(worktree: Path)`, with methods `read_file(path: str) -> str`, `write_file(path: str, contents: str) -> None` and `run_command(argv: list[str]) -> CommandResult`. Each raises `ToolRefused(str)` on a jail or allowlist violation; `run_command` returns the refusal as `CommandResult(exit_code=126, output=…)` so `ApplyUpdate` fails that step.
  - `updater.workflow.Outcome(attr: str, from_version: str, to_version: str | None, status: Literal["updated", "failed", "current"], detail: str)`
  - `updater.workflow.run(packages: list[str], worktree: Path, client, check, max_attempts: int = 3) -> list[Outcome]`. `client` exposes `PlanUpdate`/`ApplyUpdate` (the generated `b`, or a fake). `check(attr) -> CommandResult` runs `nix build --file <worktree> <attr> --no-link`.
  - `updater.workflow.create_worktree(nixpkgs: Path, run_id: str) -> Path` creates branch `baml-updater/<run_id>` under `$TMPDIR`.

- [ ] **Step 1: Write the failing unit tests.**
  - `tests/test_tools.py`:
    - `test_paths_outside_worktree_refused`: `../x`, `/etc/passwd`, and a symlink pointing outside are refused.
    - `test_allowlist`: `["nix","build",…]` runs; `["sh","-c","x"]`, `["nix","eval",…]` and `["git","push"]` are refused with exit 126.
    - `test_edit_find_must_match_exactly_once`: drives the generated `ApplyUpdate` with a plan whose `find` occurs 0 times, then 2 times. Asserts `ok is False`, that `failed_step` names the edit, and that the file is unchanged.
  - `tests/test_workflow.py`, with a fake client and a fake `check`:
    - `test_success_first_try`
    - `test_retry_feeds_errors_back`: the second `PlanUpdate` call receives the first check's output in `previous_errors`.
    - `test_gives_up_after_3`: status `failed`, 3 plan calls.
    - `test_already_current`: `needs_update=False` → `current`, with no apply and no check.
    - `test_retry_starts_from_clean_tree`: the files a failed attempt touched are restored before attempt 2.
    - `test_unknown_attr_reported_and_loop_continues`: the attribute's file can't be found → `failed`, and the next package is still processed.
- [ ] **Step 2: Run them to verify they fail.** Run `nix develop`-free: `nix build .#checks.x86_64-linux.nixpkgs-updater -L` (see Step 5 for its shape). Expected: FAIL, because the modules don't exist.
- [ ] **Step 3: Implement the BAML files and `updater/`.**
  - `PlanUpdate`'s prompt asks for exact, unique `find` strings, whole-line replacements, and the refetch commands from the allowlist. It must state the allowlist.
  - `ApplyUpdate` applies the edits in order, then the commands, and stops at the first failure.
  - `run` restores the package's touched files with `git -C <worktree> checkout -- <files>` before each attempt after the first.
  - `__main__.py`:
    - CLI: `python -m updater [--nixpkgs PATH] ATTR...`.
    - If `OPENROUTER_API_KEY` is unset, exit 2 with `error: OPENROUTER_API_KEY is not set` before doing anything else.
    - Otherwise create the worktree, call `run`, and print the outcome table.
    - Finally, print the worktree path and `git -C <worktree> diff --stat`.
- [ ] **Step 4: Write `tests/stub_llm.py` and an end-to-end test.**
  - `tests/stub_llm.py` is a localhost HTTP server that answers OpenAI chat-completions requests with canned `UpdatePlan` JSON.
  - `test_end_to_end_stubbed` points the `OpenRouterLuna` client's base URL at the stub. That is done with an env var the client reads, `OPENROUTER_BASE_URL`, defaulting to `https://openrouter.ai/api/v1`. The test runs `run()` against a tiny git repo fixture containing one fake `package.nix`, with a fake `check` that passes on the second attempt. Assert outcome `updated` and the expected file content.
- [ ] **Step 5: Wire up `check.nix`.** It's a `runCommand` with `python.withPackages (ps: [ ps.baml-bridge ps.pytest ])`, plus `baml` and `git`. It copies the example, runs `baml generate`, then `pytest -q`. Wire it as `checks.<system>.nixpkgs-updater`. Run `nix flake check -L`. Expected: all tests pass, offline.
- [ ] **Step 6: Commit.** `feat: nixpkgs-updater demo (PlanUpdate/ApplyUpdate + Python workflow)`

### Task 6: The demo's Flox environment and the real-run instructions

**Files:**
- Create: `examples/nixpkgs-updater/.flox/` (via `flox init`), `.gitignore` (`.flox/env/manifest.lock`, `baml_sdk/`)
- Create: `examples/nixpkgs-updater/README.md`
- Modify: `tests/test_workflow.py` (add `test_missing_api_key_fails_before_worktree`)

**Interfaces:**
- Consumes: the Flox rules in `docs/decisions/flox-python-packages.md` (on `baml-v0`; copy the file onto this branch), plus Tasks 3 to 5.

- [ ] **Step 1: Write the failing test.** `test_missing_api_key_fails_before_worktree` runs `python -m updater hello` with `OPENROUTER_API_KEY` unset. It asserts exit code 2, the exact error line, and that `create_worktree` was never called (monkeypatched).
- [ ] **Step 2: Run it to verify it fails, then make it pass** (if Task 5's `__main__` already satisfies it, record that it passed first time and why). Run `nix flake check -L`.
- [ ] **Step 3: Write the manifest.**
  - From the catalog: `python314` (or `python313` per Task 4's ruling), plus the matching `pydantic`, `protobuf`, `typing-extensions` and `pytest` packages.
  - From `path:../..`: `baml` and `baml-bridge`.
- [ ] **Step 4: Verify offline in Flox.** Run `flox activate -- bash -c 'baml generate && pytest -q'`. Expected: passes. Then run `flox activate -- python -m updater hello` with no key. Expected: exit 2 and the error line.
- [ ] **Step 5: Write the README.**
  - What the demo does.
  - Real-run steps: `export OPENROUTER_API_KEY=…`, `flox activate -- python -m updater --nixpkgs ~/Work/nixpkgs jq ripgrep`.
  - Where the diff lands, and that the demo never commits or pushes.
  - The Flox caveats (lock not committed; Python minor version pin).
- [ ] **Step 6: Commit.** `feat: Flox environment for nixpkgs-updater demo`

### Task 7: Docs: macOS checklist, update procedure, README

**Files:** create `docs/macos-checklist.md`, `docs/updating.md`, `README.md`, and copy `docs/decisions/flox-python-packages.md` from `baml-v0`, correcting it to 3 locked systems.

- [ ] **Step 1: Write the macOS checklist.** It follows v0's checklist shape: copy the repo (rsync or git bundle), `nix flake check -L`, `otool -L` on `baml-cli`, `baml` and the bridge's `.so`, then Task 6's Flox commands.
- [ ] **Step 2: Write the update procedure.** It uses `nix-update --flake baml-cli --version-regex …`, with the `--version X.Y.Z` fallback. Bump `BAML_GIT_SHA` to the new tag's commit (`git ls-remote`), the demo's `[toolchain] version`, and `pythonAtLeast` if it's in use.
- [ ] **Step 3: Write the README.** It covers what the repo contains, how to build, and links to the docs. It says that v0 is shelved on `baml-v0`.
- [ ] **Step 4: Verify every Linux-applicable command in the docs.** Run each one and correct any whose output differs.
- [ ] **Step 5: Commit.** `docs: README, macOS checklist, update procedure`

### Task 8: nixpkgs branch, ready for David to submit

Work in `~/Work/nixpkgs` and never push. Leave the `baml-init` branch (v0) untouched.

**Files (in nixpkgs):**
- `pkgs/by-name/ba/baml-cli/package.nix`
- `pkgs/by-name/ba/baml/package.nix` (with `tests/` if it has fixtures)
- `pkgs/development/python-modules/baml-bridge/`
- `pkgs/top-level/python-packages.nix` (in alphabetical order)
- `maintainers/maintainer-list.nix`: the `mrdavidlaing` entry from `baml-init`, name/github/githubId 227505

**Files (in this repo):** `docs/nixpkgs-pr.md`

- [ ] **Step 1: Branch and check for collisions.**
  - `git fetch origin master`, then `git switch -c baml-language-init FETCH_HEAD`.
  - `nix eval --raw -f . baml.name` and `… baml-cli.name` must fail with "attribute missing", and `python3Packages.baml-bridge` must be absent too.
  - Any existing attribute: stop and record a ruling on the name.
- [ ] **Step 2: Copy in the files.** Copy the package files, change only `maintainers`, register the Python package, and add the maintainer entry.
- [ ] **Step 3: Build.** Run `nix-build -A baml-cli -A baml -A baml.tests -A python3Packages.baml-bridge -A python3Packages.baml-bridge.tests`. Expected: all build.
- [ ] **Step 4: Review.** Run `nix run nixpkgs#nixfmt -- --check <new files>` and `nix run nixpkgs#nixpkgs-review -- wip --staged --no-shell --print-result`. Expected: formatted, and every attribute built.
- [ ] **Step 5: Commit in four commits.**
  - `maintainers: add mrdavidlaing`
  - `baml-cli: init at 0.24.0`
  - `baml: init at 0.24.0`
  - `python3Packages.baml-bridge: init at 0.24.0`
- [ ] **Step 6: Write `docs/nixpkgs-pr.md`.** It holds the title, the body (the version policy, no downloads, no telemetry key, the 3.14 status, the playground or other run-time network uses found), the template checklist, "aarch64-darwin pending David's Mac run", "confirm githubId 227505", and the submit commands. Commit it in this repo.
