# macOS (Apple Silicon) verification checklist

This has been verified on x86_64-linux only. Run these steps on an
aarch64-darwin Mac with Nix (flakes enabled) and Flox installed. Each step
lists what success looks like.

## 1. Get the repo onto the Mac

```sh
# on the Linux machine
git -C ~/Work/baml-nix bundle create /tmp/baml-nix.bundle --all
# copy /tmp/baml-nix.bundle over, then on the Mac
git clone -b main baml-nix.bundle ~/Work/baml-nix
```

Or use `rsync -a --exclude result --exclude .superpowers --exclude .baml ~/Work/baml-nix/ <mac>:Work/baml-nix/`.

## 2. Run the flake checks

```sh
cd ~/Work/baml-nix
nix flake check -L
```

Expected: `all checks passed!` This runs two Rust builds (the toolchain and
the Python bridge), so allow time. The log should show:

- `baml-cli-version-test> baml-cli 0.24.0`
- `baml-policy-test>` with 31 `ok` lines
- `baml-bridge-generate-test> ok 0.24.0`
- `nixpkgs-updater-check> 21 passed`

## 3. Check the binaries link only system libraries and the Nix store

```sh
nix build .#baml-cli .#baml-bridge
otool -L result/bin/baml-cli result/bin/baml-pack-host
otool -L result-1/lib/python3.14/site-packages/baml_bridge/baml_py.abi3.so
```

Expected: every line is `/usr/lib/…`, `/System/Library/…` or
`/nix/store/…`. No `/usr/local` or `/opt/homebrew` paths.

## 4. Run the Flox demo offline

```sh
cd examples/nixpkgs-updater
flox activate -- bash -c 'baml generate && python -m pytest -q tests'
flox activate -- python -m updater hello   # with OPENROUTER_API_KEY unset
```

Expected: `21 passed`, then `error: OPENROUTER_API_KEY is not set` (exit 2).
The first activation locks the environment, writing the git-ignored
`.flox/env/manifest.lock`.

## 5. Optional: one real run

```sh
export OPENROUTER_API_KEY=sk-or-…
flox activate -- python -m updater --nixpkgs ~/Work/nixpkgs jq
```

Expected: one line for `jq` (`updated`, `failed` or `current`) and a
`git diff --stat` of a fresh worktree.

## If something fails

Send back:

- The failing command and the last ~50 lines of its output.
- For a build failure, the full log: `nix log <the .drv path from the error>`.

Likely suspects on macOS:

- A missing Apple SDK framework. nixpkgs' default SDK should cover it.
- `baml_pack_host/build.rs` has a macOS-only branch.

Once steps 1–4 pass, tick aarch64-darwin in
[nixpkgs-pr.md](nixpkgs-pr.md).
