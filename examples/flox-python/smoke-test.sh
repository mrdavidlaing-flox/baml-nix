#!/usr/bin/env bash
# Run inside the Flox env:  flox activate -- ./smoke-test.sh
set -euo pipefail
cd "$(dirname "$0")"

case "$(command -v baml-cli)" in
  "$FLOX_ENV"/*) ;;
  *) echo "baml-cli is not coming from this Flox env: $(command -v baml-cli || echo missing)" >&2; exit 1 ;;
esac

rm -rf baml_client
baml-cli generate
python main.py
