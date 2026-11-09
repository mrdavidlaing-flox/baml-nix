# Decision: how Flox consumes Python packages from this flake

Date: 2026-11-05 (spike, Task 1). Flox 1.19.1, nixos-unstable 1d060086 (Python 3.14.8).

## Decision: Mechanism A — install catalog Python and the flake package separately

```toml
[install]
python314.pkg-path = "python314"
baml-py.flake = "path:../..#baml-py"
```

Verified with a stand-in (`python3Packages.pyyaml` from a local flake):
`flox activate -- python -c "import yaml"` imports it from
`$FLOX_ENV/lib/python3.14/site-packages`. Flox's Python setup puts exactly
that directory on `PYTHONPATH`. No `python3.withPackages` wrapper is needed.

## Constraints this imposes

1. **The flake must expose every system the manifest lists.** By default Flox
   locks for x86_64-linux, aarch64-linux and aarch64-darwin (not x86_64-darwin), and locking fails if
   `packages.aarch64-darwin.<name>` is missing, even when you only run on
   Linux. Package evaluation must therefore succeed on all three.
2. **Python minor versions must match.** Flox's `PYTHONPATH` is
   `lib/python3.<minor>/site-packages` for the catalog Python's minor
   version. A `baml-py` built for 3.14 is invisible to a `python313` env,
   even though its extension is abi3. So the catalog Python must be the same
   minor version as the flake's `python3` (3.14 today). Pin `python314`
   explicitly in the demo.
3. **Relative `path:` refs resolve against the env's project directory,**
   but the lock records the **absolute** path plus the `narHash` of the
   whole flake directory. Consequences:
   - A lock made on Linux (`/home/...`) is wrong on macOS (`/Users/...`).
   - When the env lives inside the flake directory (`examples/flox-python`
     in this repo), any edit to the repo, the lock itself included, changes
     the narHash.
   Hence, while the reference was local, the demo did **not** commit
   `.flox/env/manifest.lock`, and each machine locked on first activation.

## Update (2026-11-09): GitHub reference, committed lock

Once the repo had a public origin, the demo switched to
`baml.flake = "github:mrdavidlaing-flox/baml-nix#baml"` (likewise
`baml-bridge`). The lock now records `github:…/<commit>?narHash=…`, with no
local paths, so it is committed and works on any machine. The catch: the
demo now uses the *pushed* packages at the locked commit, not the working
tree. After pushing package changes, run `flox upgrade` in the demo and
commit the new lock (see `docs/updating.md`).

## What failed

- With a single-system flake (x86_64-linux only), all three ref forms
  (relative `path:`, `git+file:...?dir=`, absolute `path:`) failed with
  "does not provide attribute packages.aarch64-darwin...". Once the flake
  exposed every system, all three locked. Relative `path:` was chosen: it
  needs no commit and survives moving the repo, apart from the lock caveat
  above.

## After nixpkgs

Once `python314Packages.baml-py` reaches the Flox catalog, replace the
`flake` line with `baml-py.pkg-path = "python314Packages.baml-py"`, and all
three constraints go away.
