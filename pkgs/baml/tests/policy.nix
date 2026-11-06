# The Nix version policy: the packaged BAML runs unless a project asks for a
# different toolchain, and nothing is ever downloaded (the sandbox has no
# network, so any download attempt fails the test).
{
  runCommand,
  baml,
  baml-cli,
}:

runCommand "baml-policy-test" { nativeBuildInputs = [ baml ]; } ''
  set -u
  v=${baml.version}
  cli=${baml-cli}/bin/baml-cli

  project() { # name, extra baml.toml text
    mkdir -p "$1/baml_src"
    printf 'function Hello(name: string) -> string {\n  "hi " + name\n}\n' > "$1/baml_src/main.baml"
    # Top-level keys (dotted, inline) must come before any table header.
    printf '%s\n\n[package]\nname = "%s"\n' "$2" "$1" > "$1/baml.toml"
  }
  expect() { # name, want-exit (0 or fail), command...
    name=$1 want=$2; shift 2
    if "$@" >"$name.out" 2>"$name.err"; then got=0; else got=$?; fi
    if [ "$want" = 0 ] && [ "$got" != 0 ]; then
      echo "FAIL $name: expected success, got exit $got"; cat "$name.err"; exit 1
    fi
    if [ "$want" = fail ] && [ "$got" = 0 ]; then
      echo "FAIL $name: expected failure, got exit 0"; exit 1
    fi
    echo "ok   $name (exit $got)"
  }
  stderr_has() { grep -qF -- "$2" "$1.err" || { echo "FAIL $1: stderr lacks: $2"; cat "$1.err"; exit 1; }; }

  project none ""
  project match "[toolchain]
  version = \"$v\""
  project mismatch '[toolchain]
  version = "0.0.1"'
  project channel '[toolchain]
  channel = "stable"'
  project path "[toolchain]
  path = \"$cli\""
  project dotted 'toolchain.version = "0.0.1"'
  project inline 'toolchain = { version = "0.0.1" }'
  project unparseable '[toolchain]
  version = 24'
  mkdir -p none/sub/dir

  expect version 0 baml --version
  grep -qF "$v" version.out || { echo "FAIL version output"; exit 1; }

  (cd none && expect ../none 0 baml check)
  (cd none/sub/dir && expect ../../../nested 0 baml check)
  (cd match && expect ../match 0 baml check)
  (cd mismatch && expect ../mismatch fail baml check)
  stderr_has mismatch '"0.0.1"'; stderr_has mismatch "$v"
  (cd channel && expect ../channel fail baml check)
  stderr_has channel "channel"
  (cd path && expect ../path 0 baml check)
  (cd dotted && expect ../dotted fail baml check)
  stderr_has dotted '"0.0.1"'
  (cd inline && expect ../inline fail baml check)
  stderr_has inline '"0.0.1"'
  (cd unparseable && expect ../unparseable fail baml check)
  stderr_has unparseable "could not read"

  # --project selects the manifest, not the cwd.
  expect project-flag fail baml --project mismatch check
  expect project-flag-eq fail baml --project=mismatch check

  # A user-set BAML_TOOLCHAIN path is an explicit override, as upstream.
  (cd mismatch && BAML_TOOLCHAIN=$cli expect ../env-path 0 baml check)
  (cd none && BAML_TOOLCHAIN=nightly expect ../env-channel fail baml check)
  (cd none && BAML_TOOLCHAIN=$v expect ../env-same-version 0 baml check)

  # Toolchain management belongs to Nix.
  expect toolchain-status 0 baml toolchain status
  grep -qF "$v" toolchain-status.out || { echo "FAIL toolchain status output"; exit 1; }
  expect toolchain-install fail baml toolchain install 0.23.0
  expect update fail baml update
  stderr_has update "managed by Nix"

  touch $out
''
