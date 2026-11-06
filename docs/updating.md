# Updating to a new BAML v0 release

`baml-py` inherits `version`, `src` and `cargoDeps` from `baml-cli`, so only
`baml-cli` needs bumping.

1. Bump the version and both hashes (`hash` and `cargoHash`):

   ```sh
   nix run nixpkgs#nix-update -- --flake baml-cli --version-regex '^v(0\.[0-9.]+)$'
   ```

   GitHub's release/tag feeds only list the latest few entries, and
   upstream's new-language tags (`baml-language-source-*`) often crowd out
   the v0 releases. If you see `No version matched the regex`, name the
   release explicitly: `... -- --flake baml-cli --version X.Y.Z`.

   To do it by hand instead: set `version`, set both hashes to
   `lib.fakeHash`, then copy the `got:` values from `nix build .#baml-cli`.

2. Update the demo's generator pin, which must equal the package version:
   `examples/flox-python/baml_src/generators.baml`. The package tests take
   the version from the package, so they need no edits.

3. Verify:

   ```sh
   nix flake update            # optional: move to a newer nixos-unstable
   nix flake check -L
   (cd examples/flox-python && flox activate -- ./smoke-test.sh)
   ```

## When nixpkgs bumps python3 to a new minor version

`examples/flox-python/.flox/env/manifest.toml` pins `python314` and
`python314Packages.pydantic`. After a `nix flake update` moves `python3` to
3.15, change both to `python315`. Flox only puts the env Python's
`site-packages` on `PYTHONPATH`, so a mismatch shows up as
`ModuleNotFoundError: baml_client`/`baml_py`.
