# Updating to a new BAML language release

All three packages share `baml-cli`'s `version`, `src` and `cargoDeps`, so a
bump starts in `pkgs/baml-cli/package.nix`.

1. Bump the version and both hashes:

   ```sh
   nix run nixpkgs#nix-update -- --flake baml-cli \
     --version-regex '^baml-language-([0-9]+\.[0-9]+\.[0-9]+)$'
   ```

   The repo also tags `baml-language-source-*`, nightlies and
   `baml-wrapper-*`, and those often crowd the release feed. If you see
   `No version matched the regex`, name the release explicitly:
   `… -- --flake baml-cli --version X.Y.Z`.

2. Point `env.BAML_GIT_SHA` in `pkgs/baml-cli/package.nix` at the new
   tag's commit:

   ```sh
   git ls-remote https://github.com/BoundaryML/baml refs/tags/baml-language-X.Y.Z
   ```

3. Update the demo's pin, `[toolchain] version` in
   `examples/nixpkgs-updater/baml.toml`. The package tests take the version
   from the package, so they need no edits.

4. Verify:

   ```sh
   nix flake update            # optional: move to a newer nixos-unstable
   nix flake check -L
   ```

5. Push, then move the demo onto the pushed packages. Its lock pins a
   commit of `github:mrdavidlaing-flox/baml-nix`:

   ```sh
   git push
   cd examples/nixpkgs-updater
   flox upgrade
   flox activate -- bash -c 'baml generate && python -m pytest -q tests'
   git commit -m "demo: lock to new BAML" .flox/env/manifest.lock && git push
   ```

## When nixpkgs bumps python3 to a new minor version

The demo's Flox manifest pins `python314` and `python314Packages.pytest`.
After a `nix flake update` moves `python3` to 3.15, change both. Flox only
puts the env Python's `site-packages` on `PYTHONPATH`, so a mismatch shows
up as `ModuleNotFoundError: baml_bridge`.
