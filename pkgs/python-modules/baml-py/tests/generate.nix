# Generate a Python client from a small BAML project inside the build sandbox
# (no network), then import it.
{
  runCommand,
  python,
  baml-py,
}:

let
  env = python.withPackages (ps: [
    baml-py
    ps.pydantic
  ]);
in
runCommand "baml-py-generate-test" { nativeBuildInputs = [ env ]; } ''
  cp -r ${./fixture} project
  chmod -R u+w project
  cd project
  substituteInPlace baml_src/generators.baml --replace-fail @version@ ${baml-py.version}

  baml-cli generate --from baml_src
  test -f baml_client/__init__.py

  baml-cli --version | tee version.txt
  grep -qF ${baml-py.version} version.txt

  python - <<'PY'
  import baml_py
  import baml_client
  from baml_client import b

  assert hasattr(b, "ExtractResume"), dir(b)
  assert baml_client.__version__ == "${baml-py.version}", baml_client.__version__
  print("ok", baml_client.__version__)
  PY

  touch $out
''
