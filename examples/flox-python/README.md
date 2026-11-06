# Flox + BAML + Python demo

A Flox environment with Python from the Flox catalog (nixpkgs unstable) and
BAML v0 from this repo's flake.

```sh
flox activate -- ./smoke-test.sh   # → ok baml_py 0.226.3
```

`smoke-test.sh` regenerates `baml_client/` from `baml_src/` and imports it.
It never calls an LLM. The `Fake` client in `main.baml` has a dummy key.

## The manifest

| Entry | From | Why |
| --- | --- | --- |
| `python314` | catalog | The interpreter. Its minor version must match the flake's `python3` (3.14), because Flox only adds `lib/python3.<minor>/site-packages` to `PYTHONPATH`. |
| `pydantic` | catalog | Imported by the generated `python/pydantic` client. `baml-py` itself has no Python dependencies. |
| `baml-py` | `path:../..#baml-py` | The `baml_py` runtime, plus the `baml-cli` and `baml` commands. |
| `baml-cli` | `path:../..#baml-cli` | The standalone CLI. Optional here; `priority = 6` lets `baml-py`'s copy of `bin/baml-cli` win the tie. |

`baml_src/generators.baml` pins `version "0.226.3"`. It must equal the
installed `baml-py` version, or the generated client refuses to import.

## Why `manifest.lock` isn't committed

Flox records the absolute path and a content hash of the whole flake. The
flake is this repo, so the hash changes with every edit (including to the
lock itself), and the path differs between machines. Each checkout locks
itself on first `flox activate`. See
[docs/decisions/flox-python-packages.md](../../docs/decisions/flox-python-packages.md).

## Once BAML is in nixpkgs

Replace the two `flake` entries with catalog packages:

```toml
baml-py.pkg-path = "python314Packages.baml-py"
```

Then drop the `baml-cli` entry, commit `manifest.lock`, and the caveats
above go away.
