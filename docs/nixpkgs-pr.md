# nixpkgs PR: baml-cli and python3Packages.baml-py

**Status: not ready to submit until [macos-checklist.md](macos-checklist.md) passes.**

The branch is `baml-init` in `~/Work/nixpkgs`, cut from NixOS/nixpkgs master
`af0af9a3d262` (2026-11-06). It has three commits and has not been pushed.

To submit:

```sh
cd ~/Work/nixpkgs
git rebase <fresh master>                # if master has moved on
git push mrdavidlaing baml-init
gh pr create --repo NixOS/nixpkgs --base master --head mrdavidlaing:baml-init \
  --title "baml-cli, python3Packages.baml-py: init at 0.226.3" --body-file <this section below>
```

---

## Title

baml-cli, python3Packages.baml-py: init at 0.226.3

## Body

[BAML](https://github.com/BoundaryML/baml) is a domain-specific language for
writing typed LLM functions. `baml-cli generate` turns `.baml` files into a
typed client library, e.g. a Pydantic-based Python package.

This adds BAML v0 (the `engine/` Rust workspace, as published on PyPI as
`baml-py`):

- `baml-cli`: the standalone CLI (`init`, `generate`, `check`, `test`, `dev`,
  `lsp`, …), built with `rustPlatform.buildRustPackage`.
- `python3Packages.baml-py`: the Python runtime that generated clients import.
  It's built with maturin from the same source and vendored crates, as an
  abi3 (≥ 3.8) extension, and it also installs `baml-cli` and `baml` entry
  points, like the PyPI wheel. It has no Python dependencies; the generated
  `python/pydantic` client needs `pydantic`.

Notes for reviewers:

- Both packages are built from source. TLS uses rustls/ring, so there's no
  OpenSSL. RUSTFLAGS gets `--cfg tracing_unstable`, as upstream's
  `engine/.cargo/config.toml` sets.
- `baml-py` inherits `version`/`src`/`cargoDeps` from `baml-cli`, so a bump
  only touches `pkgs/by-name/ba/baml-cli`.
- `baml-cli` has `doCheck = false` because the crate has no unit tests.
  Coverage comes from `versionCheckHook` and `python3Packages.baml-py.tests`:
  - `generate` runs `baml-cli generate` on a small project in the sandbox
    (no network) and imports the resulting client.
  - `abi3` imports the single build under python313 and python314.
- `baml-cli dev`/`serve` (the playground) fetches its web UI release
  metadata from GitHub at runtime. That happens only when you run those
  subcommands; nothing is fetched at build time.
- The newer BAML language (`baml_language/`, beta, shipped through a
  toolchain-manager wrapper) is a separate project and isn't packaged here.

## Things done

- Built on platform:
  - [x] x86_64-linux
  - [ ] aarch64-linux
  - [ ] x86_64-darwin (unsupported on unstable)
  - [ ] aarch64-darwin ← tick after macos-checklist.md passes
- Tested, as applicable:
  - [x] `passthru.tests` (`python3Packages.baml-py.tests.{generate,abi3}`)
  - [x] `versionCheckHook` (baml-cli)
- [x] Ran `nixpkgs-review` on this PR (x86_64-linux).
- [x] Tested basic functionality of all binary files (`baml-cli`, `baml`).
- [x] Fits CONTRIBUTING.md (by-name for the CLI, python-modules for the library, nixfmt).
- [x] New maintainer: mrdavidlaing (separate commit).
