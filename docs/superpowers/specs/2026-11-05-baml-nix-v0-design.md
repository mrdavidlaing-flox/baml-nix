# baml-nix: packaging BAML v0 for Nix and Flox

Date: 2026-11-05
Status: draft, awaiting approval (David's questions answered)

## Intent

David wants a Flox environment for a BAML + Python project in which both
Python and BAML come from nixpkgs unstable, named in the manifest the same
way. BAML is not in nixpkgs today (checked: no `baml`, `baml-cli`, or
`python3Packages.baml-py` on nixos-unstable; `flox search baml` finds
nothing).

So: package BAML locally first, in exactly the shape nixpkgs expects, use it
from Flox via a flake reference, and once the shape is proven upstream it to
nixpkgs. After it lands, the Flox manifest switches from the flake reference
to the plain catalog/nixpkgs package and nothing else changes.

## Scope

**This document: BAML v0** — the `engine/` Rust workspace in
`github.com/BoundaryML/baml`, currently version 0.226.3 (tag `v0.226.3`),
published to PyPI as `baml-py`. This is what `baml-cli generate` +
`import baml_py` means today.

**Later, separate design: the new BAML language** (`baml_language/`,
`0.0.0-beta`, `baml-language-*` / `baml-wrapper-*` tags). It ships through a
toolchain-manager wrapper, which needs a different packaging approach
(nixpkgs forbids runtime toolchain downloads). Out of scope here; it gets
its own brainstorm after v0 is done.

## Goals

1. A nixpkgs-style `python3Packages.baml-py` derivation, built from source.
2. A nixpkgs-style top-level `baml-cli` derivation (the standalone binary,
   `pkgs/by-name/ba/baml-cli/package.nix` shape), so people who don't use
   Python still get the CLI.
3. A flake in this repo exposing both on top of nixpkgs unstable, for
   x86_64-linux and aarch64-darwin (others listed, untested — see Platforms).
4. A Flox demo project (`examples/flox-python/`) whose manifest installs
   Python from the Flox catalog/nixpkgs unstable and `baml-py` from this
   flake, referenced **locally** (a `path:`/`git+file:` reference relative
   to the repo; no GitHub repo for now, David copies or clones the repo onto
   his Mac), containing a minimal BAML function, proving:
   - `baml-cli generate` produces `baml_client/`
   - `python -c "import baml_client"` works and the generated client can be
     constructed (no live LLM call needed for the check).
5. A written macOS verification checklist (exact commands, starting from
   getting the repo onto the Mac) for David to run on his Apple Silicon Mac
   in a few days.
6. A ready-to-submit nixpkgs branch in David's checkout at `~/Work/nixpkgs`
   adding both packages, plus drafted PR text. **David pushes and opens the
   PR himself.** Done = branch ready, builds with `nix-build -A baml-cli
   -A python3Packages.baml-py` from that checkout, passes `nixpkgs-review`
   locally on x86_64-linux. Nothing is pushed anywhere by the builder.

Ordering: Linux work (goals 1–4, 6) proceeds without waiting for the Mac.
The branch is marked ready for David to submit only once the macOS
checklist passes.

## Non-goals

- The new BAML language / `baml` wrapper (later design, see Scope).
- The TypeScript, Ruby, Go, VS Code, or WASM artifacts the upstream flake
  also builds.
- Upstream's dev shell.
- Contributing changes to BoundaryML's own `flake.nix`.

## Anti-goals (would count as failure even if it builds)

- Repackaging prebuilt PyPI wheels or GitHub release binaries. Must build
  from source, or it can't go to nixpkgs.
- Using fenix, crane, or other non-nixpkgs flake inputs inside the package
  definitions. The package files must use only `rustPlatform`,
  `buildPythonPackage`, `maturinBuildHook`, etc., so upstreaming is copying
  files, not rewriting them.
- Package files that only work through this repo's flake wiring (e.g.
  reaching for flake inputs or `self`). They must be `callPackage`-able from
  a nixpkgs checkout unchanged.

## What we know about the source (recon, 2026-11-05)

- Upstream `flake.nix` (repo root, branch `canary`) builds `baml-cli`
  (`packages.default`) and `baml-py` (wheel via `maturin build`, wrapped in
  `buildPythonPackage`) using crane + a fenix toolchain pinned to Rust
  1.98.0 (`engine/rust-toolchain.toml`). Useful reference for env vars and
  native inputs; not reusable as-is.
- nixos-unstable has rustc 1.99.0 (≥ 1.98, expected fine) and Python 3.14.8.
- `engine/Cargo.lock` has **no git dependencies** — `fetchCargoVendor` /
  `cargoHash` should be straightforward.
- `baml-py` crate (`engine/language_client_python`) uses pyo3 0.23 with
  `abi3-py38`: one compiled extension works with any Python ≥ 3.8. This
  matters for Flox, where the env's Python may not be the exact interpreter
  the package was built against.
- `pyproject.toml` declares console scripts `baml-cli` and `baml`, so the
  Python package also provides the CLI. Its runtime `dependencies` list is
  deliberately empty; the *generated* `baml_client` imports `pydantic` (and
  `typing_extensions`), so the demo project must include those.
- Upstream sets `--cfg tracing_unstable` in RUSTFLAGS, uses
  libclang/bindgen, and adds `libiconv` on Darwin. TLS is now rustls (the
  `static-ssl` feature is a no-op alias), so system OpenSSL may not be
  needed at all; confirm during the build. Upstream's static-linking flags
  (`crt-static`, `OPENSSL_STATIC`) are for their release artifacts and are
  not carried over.
- No JavaScript build is needed: `engine/` crates embed no web assets. The
  playground server fetches its UI release metadata at runtime
  (`playground-server/src/server.rs:134`). That is a runtime network
  feature, not a build input. Note it for nixpkgs reviewers; don't patch it
  out unless review asks.
- `baml-cli` defaults to the `bedrock` feature (AWS Bedrock provider);
  `baml-py` builds the CLI with `default-features = false`. Our
  `baml-cli` keeps upstream defaults (feature parity with upstream's
  release binary).
- Upstream's release platform list covers Linux and macOS on x86_64 and
  aarch64 (plus Windows).

## Platforms

- `meta.platforms`: Linux and Darwin, x86_64 and aarch64 (what upstream
  supports and Nix can target).
- Tested and promised now: **x86_64-linux** (built here) and
  **aarch64-darwin** (David tests on his Mac within days; Darwin-specific
  inputs are included from the start so there is something real to test).
- Other platforms: best effort; Hydra will report on them after
  upstreaming.

## Repo layout (decided)

`~/Work/baml-nix`, a new git repo:

- `pkgs/baml-cli/package.nix` — nixpkgs `by-name` shape.
- `pkgs/python-modules/baml-py/default.nix` — nixpkgs `python-modules`
  shape.
- `flake.nix` — inputs: nixpkgs (nixos-unstable) only. Exposes
  `packages.<system>.{baml-cli, baml-py}` plus an overlay that adds
  `baml-cli` and `python3Packages.baml-py` (via `pythonPackagesExtensions`).
- `examples/flox-python/` — the Flox demo project (`.flox/` manifest, a
  `baml_src/` with one function, a smoke-test script).
- `docs/` — this design, the macOS checklist, upstreaming notes.

## Versioning (decided)

Track BAML v0 releases (`v0.226.3` now). Bumps are manual: change `version`,
update `hash` and `cargoHash`. An `updateScript` (nix-update) is nice to
have because nixpkgs reviewers expect it.

## Left to the builder

- Whether `baml-cli` and `baml-py` share source/vendor hashes or are fully
  independent derivations (nixpkgs convention favours independent and
  simple).
- Which tests to run in `checkPhase` / `pythonImportsCheck`; skipping tests
  that need network or API keys is expected.
- Exact Flox manifest mechanics for installing a Python package from a
  flake alongside catalog Python, and making it importable. **This is the
  main unknown**: prove it with a quick spike early, before polishing the
  packages. Fallback if Flox can't merge them cleanly: expose a
  `python3.withPackages (ps: [ ps.baml-py ps.pydantic ])` from the flake and
  install that single thing into Flox.
- Maintainer metadata for nixpkgs (David as maintainer; check whether his
  GitHub handle is already in `maintainers/maintainer-list.nix`).
