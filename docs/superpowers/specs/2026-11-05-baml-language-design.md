# baml-nix: packaging the new BAML language for Nix and Flox

Date: 2026-11-05
Status: draft, awaiting approval (builder check done; David's answers in)
Branch: `baml-language` (cut from `main`; the shelved v0 work stays on `baml-v0`)

## Intent

David wants to write whole agents in the new BAML language, with Python
interop, inside a Flox environment where Python and BAML both come from
nixpkgs unstable. BAML isn't in nixpkgs. So, as with v0: package it locally
in exactly nixpkgs' shape, use it from Flox through a local flake, then
upstream it.

BAML v0 was packaged first (branch `baml-v0`, plus an unpushed nixpkgs
branch `baml-init`), then **shelved on 2026-11-05**. David doesn't use v0,
and keeping it in nixpkgs would mean maintenance and a clash on the
`baml-cli`/`baml` names. It stays as reference only. **Reuse its lessons;
do not submit it.**

## Scope

The new BAML language is the `baml_language/` Cargo workspace in
`github.com/BoundaryML/baml`. Releases are tagged `baml-language-X.Y.Z`;
`0.24.0` was the latest stable on 2026-11-05. The launcher is tagged
`baml-wrapper-X.Y.Z` on **the same commit** (`baml-wrapper-0.3.0` =
`baml-language-0.24.0` = `dec4713a`). Package stable releases only, no
nightlies.

## Goals

1. **Toolchain package** (`baml-cli`): `baml_language/crates/baml_cli`
   (binary `baml-cli`) plus `baml-pack-host`, built from source with
   nixpkgs' `rustPlatform`.
2. **Launcher package** (`baml`): the `baml` command. It runs the packaged
   toolchain, never downloads one, and **fails with a clear error when a
   project asks for a different version** (see Version policy).
3. **Python runtime** (`python3Packages.baml-bridge`, PyPI/import name
   `baml_bridge`): `baml_language/sdks/python`, built with maturin
   (`rust/bridge_python`, module `baml_bridge.baml_py`). Runtime
   dependencies: `protobuf`, `pydantic`, `typing-extensions`. This is the
   runtime the generated `baml_sdk` imports.
4. **A flake** in this repo exposing all three on nixos-unstable, for
   x86_64-linux, aarch64-linux and aarch64-darwin.
5. **A demo agent**, `examples/nixpkgs-updater/` (described below), in a
   Flox environment. It uses both interop directions: Python calls BAML
   functions, and BAML calls Python callbacks.
6. **A macOS checklist and an update procedure**, like v0's.
7. **A ready-to-submit nixpkgs branch** in `~/Work/nixpkgs` with drafted PR
   text. David pushes and opens the PR himself. Done = branch ready, builds,
   and `nixpkgs-review` passes on x86_64-linux. Nothing is pushed.

## Non-goals

- BAML v0 (shelved).
- The TypeScript, Go, Java, C#, Ruby, Rust, C++ and Swift SDKs, and the
  standalone C library (`bridge_cffi`), except where a Python build needs it.
- Nightly or canary channels.
- Upstream's telemetry key: official launcher builds embed one; ours don't
  (no `--embed-telemetry`).
- The launcher's toolchain management (install, update, channels,
  self-update). Nix owns that.

## Anti-goals

- Anything that downloads a toolchain, runtime or pack host at build time
  **or at run time**.
- Prebuilt binaries or wheels instead of a source build.
- Package files that depend on flake inputs, fenix/crane or `self`. They
  must be `callPackage`-able unchanged from a nixpkgs checkout (as with v0).
- A demo that can modify anything outside its throwaway worktree, commits to
  David's branches, or pushes anywhere.
- Silently using a different BAML version than a project asked for.

## Version policy (decided by David)

Nix and Flox decide the BAML version. If a project's `baml.toml` asks for a
toolchain other than the installed one, `baml` **fails** with an error that
names both versions. It neither downloads the requested version nor warns
and carries on.

Facts the builder has to work with:

- A project selects its toolchain in `baml.toml` under `[toolchain]`, with
  one of `version`, `channel` or `path` (see
  `baml_language/wrapper/baml_src/selectors.baml`).
- The upstream launcher gives `BAML_TOOLCHAIN` (a channel, a version or a
  path to a local `baml-cli`) priority over the project. So pointing
  `BAML_TOOLCHAIN` at the store path **on its own would silently override**
  a mismatched project. That breaks the policy.
- A project with no `[toolchain]` section uses the installed version.

How to enforce it is left to the builder (see below). Every one of these
cases must be covered by a test: no `[toolchain]` (runs), a matching
`version` (runs), a different `version` (fails, naming both), a `channel`
(fails: Nix doesn't do channels), and a `path` (honoured as an explicit
local override, matching upstream's meaning).

If the user sets `BAML_TOOLCHAIN` themselves, it is an explicit override,
like `path`. Honour it, and test it (my call). What must never happen is the
*package* setting it on the user's behalf in a way that hides a mismatched
project.

## The demo: `examples/nixpkgs-updater/`

A Python "workflow" program that asks an LLM how to bump nixpkgs packages to
their latest upstream version, then tries it.

**BAML side (`baml_src/`)**, two functions (David's design):

- **`PlanUpdate`** works out what to do. It takes the package attribute
  name, its current `package.nix` contents and its current version, and
  optionally the errors from a previous failed attempt. It returns a typed
  plan: the target version, whether an update is needed, the edits to make,
  which hashes need refetching, any risks noticed, and short reasoning.
- **`ApplyUpdate`** applies the change. It is **plain BAML code, not an
  LLM call** (decided by David). It walks the plan's edits and hash-refetch
  steps in order, calling Python callbacks passed into it:
  `read_file(path)`, `write_file(path, contents)` and `run_command(argv)`.
  It returns what it did, and stops at the first failing step with that
  step and its output. So the plan's type must be concrete enough for code
  to execute: exact file paths, exact text to find and replace (it must
  occur exactly once, otherwise the step fails), and exact commands. Only
  `PlanUpdate` calls the LLM. The tests can therefore stub one LLM response
  per attempt, and the allowlist guards the commands the *plan* contains.

**Python side (`workflow.py`)** orchestrates (David's design):

- It loops over a list of nixpkgs attribute names, kept in the script or a
  small file.
- For each package it runs plan → apply → check. The check is `nix build`
  of that attribute in the worktree. If the check fails, it calls
  `PlanUpdate` again with the error output, at most 3 attempts (my call).
- It prints a final table: package, from-version → to-version, and outcome
  (updated / failed / already current), and leaves the diff for David to
  review.

**Safety (my calls; David can override):**

- All edits happen in a throwaway `git worktree` of `~/Work/nixpkgs` (path
  configurable), on a new branch per run. The demo never commits to existing
  branches and never pushes.
- File callbacks refuse paths outside the worktree.
- `run_command` is an allowlist: `nix build`, `nix-prefetch-url`,
  `nix-prefetch-git`, `nix-update`, `git diff`, `git status`. Anything else
  returns an error to the model.

**LLM (decided by David):** `gpt-6-luna`, through **OpenRouter** with
BAML's OpenAI-compatible client. The base URL is
`https://openrouter.ai/api/v1`, and the key comes from the
`OPENROUTER_API_KEY` environment variable, never stored in the repo or a
package. The model id on OpenRouter is unverified. Check it on the first
real run. If OpenRouter lists it under a vendor prefix, use that exact id.
Claude-plan and ChatGPT-plan subscriptions can't be used: they don't
include API access.

**Testing:** the dry run is a **flake check** (my call; same pattern as
v0's `generate` test). It runs in the sandbox, with a stub LLM endpoint on
localhost inside the build. Nix builds have no network and no key. Automated checks
therefore cover:

- `baml generate` producing the Python SDK.
- Importing that SDK.
- A dry run of the workflow with **stubbed** LLM responses that exercises the
  plan → apply → check → retry loop and the callback plumbing.

A real run with David's key is a manual step, documented in the demo's
README.

## Platforms

- Same as v0: `meta.platforms = lib.platforms.linux ++ lib.platforms.darwin`.
- The flake covers x86_64-linux, aarch64-linux and aarch64-darwin;
  nixos-unstable has dropped x86_64-darwin.
- Tested: x86_64-linux here, and aarch64-darwin on David's Mac (checklist).

## Lessons carried over from v0 (verified there)

- Flox locks flake packages for every system in the manifest, so the flake
  must evaluate on all three.
- Flox's `PYTHONPATH` is per Python minor version. Pin the catalog Python
  to the flake's `python3` minor (3.14 today).
- Don't commit the demo's `.flox/env/manifest.lock`. It records the absolute
  path and the narHash of the whole flake.
- Derive test versions from the package (`${pkg.version}`); never hardcode
  them.
- Restrict the `updateScript` to the right tag family, here
  `^baml-language-([0-9]+\.[0-9]+\.[0-9]+)$`. Upstream tags several
  products in one repo, and the release feed is crowded with
  `baml-language-source-*` and nightly tags. Expect it to fail safe and
  document the `--version` fallback.
- Maintainer `mrdavidlaing` (github id 227505) goes in its own commit,
  included in the branch. David confirms the id before he pushes (my call,
  as with v0). The repo copies keep `maintainers = [ ]`.

## Target commit (my call, from David's "stable releases only")

Build `baml-language-0.24.0` (`dec4713a`), not canary. The recon below was
done on canary `1d9f45c`, so re-check every fact at the tag before relying
on it. The demo must work with what 0.24.0 ships. If it needs a feature
that only exists on canary, change the demo; don't move off stable.

## Recon facts (2026-11-05, canary `1d9f45c`; re-verify at the tag)

- The workspace pins Rust 1.98.0; nixos-unstable has 1.99. `Cargo.lock` has
  no git dependencies. Patched crates live in-tree (`forks/aws-*`,
  `forks/google-cloud-auth`, `vendor/quanta`), so path dependencies work
  with Nix.
- The launcher is written in BAML. The upstream build recipe (from
  `packaging/aur/baml/PKGBUILD`): `cargo build --release --frozen --bin
  baml-cli --bin baml-pack-host`, then `python wrapper/build --cli … --pack-host
  … --version … --no-self-update --output …/baml`. Set `BAML_GIT_SHA` (the
  tarball has no `.git`; "compiler and host must agree"). Don't strip the
  packed launcher (stripping destroys its payload).
- `baml_bridge` is at version 0.24.0. Its `pyproject.toml` lists CPython
  3.10–3.13; whether it works on 3.14 is unknown (see below).
- Python interop runs both ways: Python calls the generated SDK, and BAML
  calls Python callables, sync or async (`sdks/python/README.md` § Python
  callback execution).

## Left to the builder

- **How to enforce the version policy.** Options include building the
  upstream launcher (`--no-self-update`) and wrapping it in a check that
  reads the project's `[toolchain]` before exec'ing with `BAML_TOOLCHAIN`;
  shipping `baml-cli` as `baml` behind a small checking shim; or a patch.
  Prove it with a spike before committing to one. Prefer whatever is
  smallest and easiest to upstream.
- **Python 3.14.** `baml_bridge` lists CPython up to 3.13. Spike a build and
  import on 3.14 early. If it fails, the fallback is building
  `python313Packages.baml-bridge` and pinning the Flox demo to 3.13. Record
  which happened. In that case, the nixpkgs PR ships the Python package with
  `disabled = pythonAtLeast "3.14"` and says so in the PR text (my call);
  reviewers can push back.
- Whether `baml-pack-host` is its own output, its own package, or internal
  to the launcher's build.
- Whether the three packages share one `cargoDeps` (the v0 pattern), or
  whether the Python SDK's Cargo workspace differs. Check which lockfile
  `sdks/python/rust/bridge_python` uses.
- The exact BAML client syntax for an OpenAI-compatible endpoint, and how
  BAML passes Python callables in (follow `sdks/python/README.md` and the
  sdk_tests fixtures).
- How the dry run stubs the LLM: a fake HTTP endpoint on localhost, or
  BAML's test or record facilities.
- Package names in nixpkgs. Proposed: `baml` (launcher), `baml-cli`
  (toolchain, a dependency of the launcher), `python3Packages.baml-bridge`.
  Check for collisions with existing nixpkgs attributes.
