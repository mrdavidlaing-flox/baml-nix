# baml-nix

[BAML](https://github.com/BoundaryML/baml) v0, packaged for Nix from source
in nixpkgs style, ready to upstream to nixpkgs.

| Package | Provides |
| --- | --- |
| `baml-cli` | The standalone `baml-cli` binary |
| `python3Packages.baml-py` | The `baml_py` runtime, plus the `baml-cli` and `baml` commands |

```sh
nix build .#baml-cli .#baml-py
nix flake check -L          # version check, offline generate+import, abi3 import
```

Use the `overlays.default` overlay to get `pkgs.baml-cli` and
`python3Packages.baml-py` in your own nixpkgs.

Supported systems: x86_64-linux and aarch64-darwin (tested), plus
aarch64-linux (evaluates; untested). nixos-unstable no longer supports
x86_64-darwin.

- [examples/flox-python](examples/flox-python): a Flox environment using these packages
- [docs/macos-checklist.md](docs/macos-checklist.md): verifying on Apple Silicon
- [docs/updating.md](docs/updating.md): bumping to a new BAML release
- [docs/decisions/flox-python-packages.md](docs/decisions/flox-python-packages.md): how Flox consumes the flake
- [docs/superpowers/specs/](docs/superpowers/specs/): design
