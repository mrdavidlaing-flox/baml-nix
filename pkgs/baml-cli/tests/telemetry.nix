# The wrapper turns baml-cli's PostHog analytics off by default, and
# DO_NOT_TRACK=0 still turns them back on (--set-default, not --set).
{ runCommand, baml-cli }:

runCommand "baml-cli-telemetry-test" { nativeBuildInputs = [ baml-cli ]; } ''
  export HOME=$TMPDIR
  status() {
    "$@" baml-cli telemetry 2>&1 | sed -n 's/^Status: //p'
  }

  default=$(status env)
  echo "default: $default"
  [ "$default" = Disabled ] || { echo "expected analytics off by default" >&2; exit 1; }

  opted_in=$(status env DO_NOT_TRACK=0)
  echo "DO_NOT_TRACK=0: $opted_in"
  [ "$opted_in" = Enabled ] || { echo "expected DO_NOT_TRACK=0 to opt back in" >&2; exit 1; }

  touch $out
''
