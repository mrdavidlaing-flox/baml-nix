# Offline check of the nixpkgs-updater demo: generate the SDK, then run the
# unit tests and an end-to-end run against a fake `claude` (tests/fake_claude.py).
{
  runCommand,
  python3,
  baml,
  git,
}:

let
  env = python3.withPackages (ps: [
    ps.baml-bridge
    ps.pytest
  ]);
in
runCommand "nixpkgs-updater-check"
  {
    nativeBuildInputs = [
      env
      baml
      git
    ];
  }
  ''
    cp -r ${./.} demo
    chmod -R u+w demo
    cd demo
    export HOME=$TMPDIR
    baml generate
    python -m pytest -q -p no:cacheprovider tests
    touch $out
  ''
