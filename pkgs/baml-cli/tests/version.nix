{ runCommand, baml-cli }:

runCommand "baml-cli-version-test" { nativeBuildInputs = [ baml-cli ]; } ''
  out_text=$(baml-cli --version 2>&1)
  echo "baml-cli --version: $out_text"
  case "$out_text" in
    *0.226.3*) touch $out ;;
    *) echo "expected 0.226.3 in version output" >&2; exit 1 ;;
  esac
''
