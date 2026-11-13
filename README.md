# baml-nix

The [BAML](https://github.com/BoundaryML/baml) language, packaged for Nix
from source in nixpkgs style, ready to upstream to nixpkgs.

| Package | Provides |
| --- | --- |
| `baml` | The `baml` command. It runs the packaged toolchain, never downloads one, and refuses projects whose `baml.toml` asks for another version. |
| `baml-cli` | The toolchain itself (`baml-cli`, `baml-pack-host`). |
| `python3Packages.baml-bridge` | The Python runtime that SDKs from `baml generate` import. |

```sh
nix build .#baml .#baml-bridge
nix flake check -L   # version, policy, generate+call, and the demo's offline tests
```

Use `overlays.default` to get `pkgs.baml`, `pkgs.baml-cli` and
`python3Packages.baml-bridge` in your own nixpkgs.

Supported systems: x86_64-linux and aarch64-linux (tested); aarch64-darwin
(pending [docs/macos-checklist.md](docs/macos-checklist.md)). nixos-unstable
no longer supports x86_64-darwin.

- [examples/nixpkgs-updater](examples/nixpkgs-updater): a Flox demo in
  which a Python workflow drives two BAML functions to bump nixpkgs
  packages.
- [docs/decisions/baml-version-policy.md](docs/decisions/baml-version-policy.md):
  why `baml` is a checking script, not upstream's launcher.
- [docs/decisions/flox-python-packages.md](docs/decisions/flox-python-packages.md):
  how Flox uses this flake's Python packages.
- [docs/updating.md](docs/updating.md): bumping to a new release.
- [docs/nixpkgs-pr.md](docs/nixpkgs-pr.md): the drafted nixpkgs PR.

BAML v0 (`engine/`, PyPI `baml-py`) was packaged first, then shelved. It
lives on the `baml-v0` branch for reference only.
