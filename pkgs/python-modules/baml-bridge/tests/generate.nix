# Generate a Python SDK from a small BAML project in the sandbox (no
# network), import it, and call a plain BAML function through baml_bridge.
{
  runCommand,
  python,
  baml,
  baml-bridge,
}:

let
  env = python.withPackages (_: [ baml-bridge ]);
in
runCommand "baml-bridge-generate-test"
  {
    nativeBuildInputs = [
      env
      baml
    ];
  }
  ''
    cp -r ${./fixture} project
    chmod -R u+w project
    cd project
    export HOME=$TMPDIR

    baml generate
    test -d baml_sdk

    python - <<'PY'
    from importlib.metadata import version

    import baml_sdk

    assert version("baml_bridge") == "${baml-bridge.version}", version("baml_bridge")
    assert baml_sdk.hello_sync("nix") == "hi nix", baml_sdk.hello_sync("nix")
    print("ok", version("baml_bridge"))
    PY

    touch $out
  ''
