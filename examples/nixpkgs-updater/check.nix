# Offline check of the nixpkgs-updater demo: generate the SDK, then run the
# unit tests and a stubbed end-to-end run (a local fake LLM endpoint).
{
  runCommand,
  python3,
  baml,
  git,
  cacert,
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
    # BAML's HTTP client loads the system CA roots when it is created, even
    # for the plain-HTTP local stub; the sandbox has none.
    export SSL_CERT_FILE=${cacert}/etc/ssl/certs/ca-bundle.crt
    baml generate
    python -m pytest -q -p no:cacheprovider tests
    touch $out
  ''
