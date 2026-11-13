# nixpkgs PR: baml, baml-cli, python3Packages.baml-bridge

**Status: not ready to submit until [macos-checklist.md](macos-checklist.md)
passes and you have confirmed your GitHub id.**

The branch is `baml-language-init` in `~/Work/nixpkgs`, cut from
NixOS/nixpkgs master `7fc3d159e524` (2026-11-06). It has four commits and
has not been pushed. The older `baml-init` branch (shelved BAML v0) is
unrelated: don't submit it.

Before submitting:

1. **Confirm the maintainer id.** `gh api users/mrdavidlaing --jq .id`
   should print `227505`, the value in the `maintainers: add mrdavidlaing`
   commit.
2. **Review it yourself.** nixpkgs' Automation/AI policy (`CONTRIBUTING.md`)
   requires the submitter to have reviewed and understood the change, and
   to answer reviewers themselves. The commits carry the required
   `Assisted-by: Claude Code (Claude Opus 5.5)` trailer, and the body below
   has the separate PR-level disclosure.

To submit:

```sh
cd ~/Work/nixpkgs
git fetch origin master && git rebase FETCH_HEAD   # if master has moved on
git push mrdavidlaing baml-language-init
gh pr create --repo NixOS/nixpkgs --base master --head mrdavidlaing:baml-language-init \
  --title "baml, baml-cli, python3Packages.baml-bridge: init at 0.25.2" --body-file <the Body section below>
```

---

## Title

baml, baml-cli, python3Packages.baml-bridge: init at 0.25.2

## Body

[BAML](https://github.com/BoundaryML/baml) is a programming language for
building agents: typed LLM functions plus ordinary code, with generated
SDKs for host languages. This packages the current BAML language
(`baml_language/`, tag `baml-language-0.25.2`) from source:

- **`baml-cli`**: the toolchain (`baml-cli`, `baml-pack-host`), built with
  `rustPlatform.buildRustPackage`.
- **`baml`**: the `baml` command, a small POSIX `sh` script around
  `baml-cli`.
- **`python3Packages.baml-bridge`**: the Python runtime that SDKs from
  `baml generate` import. Built with maturin as an abi3 (≥ 3.10) extension
  from the same source and vendored crates. It depends on `protobuf`,
  `pydantic` and `typing-extensions`.

The older BAML v0 (`engine/`, PyPI `baml-py`) is not part of this PR.

0.25.2 has the same source as 0.25.0 and 0.25.1. Those two releases differ
only in version strings, and were re-cut because upstream's publishing of
0.25.0 failed partway.

### Why `baml` is a script, not upstream's launcher

Upstream's `baml` launcher manages toolchains. It reads `[toolchain]` from
the project's `baml.toml`, downloads the requested version from
`pkg.boundaryml.com`, and can update itself. Built offline it works, but
under Nix it either goes to the network for every project, or, with
`BAML_TOOLCHAIN` pointed at the store, silently runs projects that asked
for a different version. So the `baml` here:

- runs the packaged `baml-cli` and never downloads anything;
- **refuses** (exit 1, naming both versions) a project whose `baml.toml`
  asks for another `version` or any `channel`, and fails safe on a
  `toolchain` selector it can't read;
- honours `[toolchain] path` and a user-set `BAML_TOOLCHAIN=<path>`, as
  upstream does;
- answers `baml toolchain status`, and refuses `baml update`,
  `baml upgrade` and other `toolchain` subcommands ("managed by Nix").

`baml.tests.policy` covers all of this, offline, in 31 cases.

### Notes for reviewers

- **The source tarball has no `.git`.** `env.BAML_GIT_SHA` carries the
  tag's commit, which upstream's `baml_artifact/build.rs` requires.
- **`baml-cli` has `doCheck = false`.** The crate's suite is large and
  mostly end-to-end (network, telemetry, agent installs). Coverage comes
  from `versionCheckHook` and the passthru tests:
  - `baml.tests.policy`: the version policy above.
  - `python3Packages.baml-bridge.tests.generate`: `baml generate` on a
    small project in the sandbox, then importing the SDK and **calling** a
    BAML function through the bridge.
- **Shared sources.** `baml-bridge` inherits `version`/`src`/`cargoDeps`
  from `baml-cli` (one Cargo workspace, one `Cargo.lock`), so a bump only
  touches `pkgs/by-name/ba/baml-cli`. `updateScript` is limited to
  `baml-language-X.Y.Z` tags, because the repo also tags nightlies,
  `baml-language-source-*` and `baml-wrapper-*`.
- **Python.** The committed protobuf stubs are 6.31.1 gencode, and they
  work with nixpkgs' protobuf 7.36: the generate test imports and calls
  through them. Python 3.14 builds and imports fine.
- **Telemetry.** No telemetry key is embedded (upstream release builds of
  the launcher embed one). `baml-cli` itself prints a one-time notice and
  collects anonymous CLI usage analytics. Users opt out with
  `DO_NOT_TRACK=1` or `baml telemetry disable`. This PR doesn't change
  that default; reviewers may want an opinion.
- **CA certificates.** BAML's HTTP client loads the system CA roots when it
  is created, even for plain-HTTP endpoints. Without CA roots, LLM calls
  fail with "HTTP client initialization failed". This only matters in
  sandboxes and minimal containers (`SSL_CERT_FILE` fixes it); normal
  systems have roots.
- **Coding-agent environments.** `baml-cli` recognises coding-agent
  environments (`CLAUDECODE`, `AI_AGENT`, …), and some commands then ask
  for BAML's agent skill (`--agent-skill-check off` bypasses it). This is
  upstream behaviour, unchanged here.

### AI assistance

This was written with Claude Code (Claude Opus 5.5): the packaging, the
`baml` script, the tests and this description. Each commit carries an
`Assisted-by:` trailer. I reviewed the changes, and I built and tested them
as described above.

## Things done

- Built on platform:
  - [x] x86_64-linux
  - [ ] aarch64-linux
  - [ ] x86_64-darwin (unsupported on unstable)
  - [ ] aarch64-darwin ← tick after macos-checklist.md passes
- Tested, as applicable:
  - [x] `passthru.tests` (`baml.tests.policy`, `python3Packages.baml-bridge.tests.generate`)
  - [x] `versionCheckHook` (`baml-cli`)
- [x] Ran `nixpkgs-review` on this PR (x86_64-linux).
- [x] Tested basic functionality of all binary files (`baml`, `baml-cli`, `baml-pack-host`).
- [x] Fits CONTRIBUTING.md (by-name for `baml` and `baml-cli`, python-modules for the library, nixfmt).
- [x] New maintainer: mrdavidlaing (separate commit).
