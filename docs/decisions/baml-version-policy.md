# Decision: how `baml` enforces the Nix version policy

Date: 2026-11-05 (spike, Task 2). BAML language 0.24.0, upstream launcher
built offline with `wrapper/build --no-self-update`.

## What the upstream launcher does (measured, offline)

| Project `[toolchain]` | `BAML_TOOLCHAIN=<nix baml-cli>` | No `BAML_TOOLCHAIN` |
| --- | --- | --- |
| none | runs | **network**: fetches `pkg.boundaryml.com/manifest/v1/canary.json` |
| `version = "0.24.0"` | runs | **network**: `…/version/0.24.0.json` |
| `version = "0.23.0"` | **runs (mismatch hidden)** | **network**: `…/version/0.23.0.json` |
| `channel = "stable"` | runs | error: invalid toolchain.channel |
| `path = <baml-cli>` | runs | runs |

The launcher builds offline (`baml-cli pack`, about 1 s). But under Nix it can
only download toolchains, or let `BAML_TOOLCHAIN` override the project.
Either way it breaks the policy.

## Decision: option (b), `baml-cli` as `baml` behind a checking script

`pkgs/baml` installs `bin/baml`, a POSIX `sh` script (coreutils, grep, sed
only) that does the following:

1. If `BAML_TOOLCHAIN` is set **by the user**: if it is a path to an
   executable, exec it with the original arguments (an explicit local
   override, as upstream). If it is anything else (a channel or a version),
   fail with exit 1, unless it is exactly the packaged version.
2. Otherwise, find the project manifest: the `baml.toml` named by
   `--project PATH`/`--project=PATH`, or else the nearest `baml.toml` walking
   up from the cwd. Read its toolchain selector in any of three forms: a
   `[toolchain]` table, `toolchain.<key> = …` dotted keys, or the inline
   `toolchain = { … }`.
   - no selector → run the packaged toolchain
   - `version` equal to the packaged version → run
   - any other `version` → exit 1:
     `error: <manifest>: [toolchain] version is "<asked>", but this BAML is <packaged> (provided by Nix). Change the version in baml.toml, or install BAML <asked> through Nix.`
   - `channel` → exit 1:
     `error: <manifest>: [toolchain] channel = "<value>" is not supported: this BAML is <packaged> (provided by Nix). Use version = "<packaged>", or remove the [toolchain] table.`
   - `path` → resolve relative to the manifest directory and exec it.
   - a `toolchain` key the script can't parse → exit 1 (fail safe):
     `error: <manifest>: could not read the [toolchain] selector; this BAML is <packaged> (provided by Nix).`
3. `baml toolchain …`: `status` prints the packaged version and path and
   exits 0. Every other `toolchain` subcommand, plus `update` and
   `upgrade`, exits 1 with `error: BAML is managed by Nix; change the
   version through your Nix/Flox environment.`
4. Exec `baml-cli` with `BAML_CLI_ALLOW_DIRECT=1` (the variable upstream's
   build sets, which silences the "use `baml` instead" warning) and the
   original arguments.

Why: it's the smallest option, it can't download anything, it's easy to
review for nixpkgs, and every policy case becomes testable offline. Options
(a) (upstream launcher plus a check) and (c) (patching `selectors.baml`)
would ship a 45 MB packed binary whose only extra features are downloads
and self-management.

## Also learned

- `baml-cli` notices coding-agent environments (`CLAUDECODE` and the other
  markers in `ENV_VARS.md`). Some commands then demand an agent skill
  (`pack` failed with "the BAML agent skill is required"). Nix builds have a
  clean environment, so this doesn't happen there. Interactive users inside
  agents may see it; `--agent-skill-check off` bypasses it.
- `baml check` on any project prints warnings from the standard library
  (`csv.baml` unreachable code) and "no baml skill is installed". These are
  harmless and come from upstream.
