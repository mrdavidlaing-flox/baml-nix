# macOS (Apple Silicon) verification checklist

This has been verified on x86_64-linux only. Run these steps on an
aarch64-darwin Mac with Nix (flakes enabled) and Flox installed. Each step
lists what success looks like.

## 1. Get the repo onto the Mac

From the Linux machine:

```sh
rsync -a --exclude result --exclude .superpowers ~/Work/baml-nix/ <mac>:Work/baml-nix/
```

Or bundle it and copy the file over:

```sh
git -C ~/Work/baml-nix bundle create /tmp/baml-nix.bundle --all
# on the Mac:
git clone -b baml-v0 baml-nix.bundle ~/Work/baml-nix
```

## 2. Run the flake checks

```sh
cd ~/Work/baml-nix
nix flake check -L
```

Expected: `all checks passed!` This builds `baml-cli` and `baml-py` from
source. Allow time for two Rust builds. The log shows:

- `baml-cli-version-test> baml-cli --version: baml-cli 0.226.3`
- `baml-py-abi3-test>` imports under both python3-3.13 and python3-3.14
- `baml-py-generate-test> ok 0.226.3`

## 3. Check the binary links only system libraries and the Nix store

```sh
nix build .#baml-cli
otool -L result/bin/baml-cli
```

Expected: every line is `/usr/lib/...`, `/System/Library/...` or
`/nix/store/...`. No `/usr/local` or `/opt/homebrew` paths.

## 4. Run the Flox demo

```sh
cd examples/flox-python
flox activate -- ./smoke-test.sh
```

Expected: the last line is `ok baml_py 0.226.3`. The first activation locks
the environment, which writes `.flox/env/manifest.lock`; that file is
git-ignored.

## If something fails

Send back:

- The failing command and the last ~50 lines of its output.
- For a build failure, the full log: `nix log <the .drv path from the error>`.

Likely suspects on macOS:

- A missing framework or `libiconv`. `buildInputs` already includes
  `libiconv` on Darwin; it may turn out to be unnecessary.
- A linker flag from upstream's `engine/.cargo/config.toml`.

Once all four steps pass, update the testing line in
[nixpkgs-pr.md](nixpkgs-pr.md) and the PR is ready to submit.
