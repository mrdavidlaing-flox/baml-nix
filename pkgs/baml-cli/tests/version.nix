{ runCommand, baml-cli }:

runCommand "baml-cli-version-test" { nativeBuildInputs = [ baml-cli ]; } ''
  out_text=$(baml-cli --version 2>&1)
  echo "baml-cli --version: $out_text"
  case "$out_text" in
    *${baml-cli.version}*) ;;
    *) echo "expected ${baml-cli.version} in version output" >&2; exit 1 ;;
  esac
  test -x ${baml-cli}/bin/baml-pack-host
  touch $out
''
