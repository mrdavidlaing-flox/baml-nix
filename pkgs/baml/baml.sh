#!/bin/sh
# `baml` for Nix: runs the packaged BAML toolchain, never downloads one, and
# refuses projects whose baml.toml asks for a different toolchain.
# Upstream's launcher (baml_language/wrapper) manages toolchains itself;
# under Nix the version is chosen by the Nix/Flox environment instead.
set -u

version='@version@'
cli='@cli@'

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

run_packaged() {
  BAML_CLI_ALLOW_DIRECT=1 exec "$cli" "$@"
}

run_path() { # executable, args...
  exe=$1
  shift
  [ -x "$exe" ] || die "toolchain path $exe is not an executable baml-cli"
  BAML_CLI_ALLOW_DIRECT=1 exec "$exe" "$@"
}

# --- Command words: toolchain management belongs to Nix -------------------

project_arg=''
command_word=''
sub_word=''
expect_project=0
for arg in "$@"; do
  if [ "$expect_project" = 1 ]; then
    project_arg=$arg
    expect_project=0
    continue
  fi
  if [ -z "$command_word" ]; then
    case $arg in
      --) break ;;
      --project) expect_project=1 ;;
      --project=*) project_arg=${arg#--project=} ;;
      -*) ;;
      *) command_word=$arg ;;
    esac
  elif [ -z "$sub_word" ]; then
    case $arg in
      -*) ;;
      *) sub_word=$arg ;;
    esac
  fi
done

case $command_word in
  toolchain)
    if [ "$sub_word" = status ]; then
      printf 'BAML %s (provided by Nix)\n%s\n' "$version" "$cli"
      exit 0
    fi
    die "BAML is managed by Nix; change the version through your Nix/Flox environment."
    ;;
  update | upgrade)
    die "BAML is managed by Nix; change the version through your Nix/Flox environment."
    ;;
esac

# --- An explicit BAML_TOOLCHAIN from the user wins, as upstream ------------

if [ -n "${BAML_TOOLCHAIN:-}" ]; then
  case $BAML_TOOLCHAIN in
    "$version") run_packaged "$@" ;;
    */*) run_path "$BAML_TOOLCHAIN" "$@" ;;
    *) die "BAML_TOOLCHAIN=$BAML_TOOLCHAIN is not available: this BAML is $version (provided by Nix). Set BAML_TOOLCHAIN to a path to a baml-cli, or unset it." ;;
  esac
fi

# --- Find the project manifest ----------------------------------------------

find_manifest() { # start
  dir=$1
  [ -f "$dir" ] && { printf '%s\n' "$dir"; return 0; }
  dir=$(cd "$dir" 2>/dev/null && pwd -P) || return 1
  while :; do
    if [ -f "$dir/baml.toml" ]; then
      printf '%s\n' "$dir/baml.toml"
      return 0
    fi
    [ "$dir" = / ] && return 1
    dir=$(dirname "$dir")
  done
}

manifest=$(find_manifest "${project_arg:-.}") || run_packaged "$@"

# --- Read its toolchain selector (fail safe on anything unexpected) ---------

unreadable() {
  die "$manifest: could not read the [toolchain] selector; this BAML is $version (provided by Nix)."
}

sel_kind=''
sel_value=''
record() { # kind, value
  [ -z "$sel_kind" ] || unreadable
  sel_kind=$1
  sel_value=$2
}

ws='[[:space:]]*'
str='"\([^"\\]*\)"'
tail_ok="$ws\(#.*\)\{0,1\}"

# Lines before the first table header.
top=$(sed "/^$ws\[/,\$d" "$manifest")

# [toolchain] table, and refuse any [toolchain.*] sub-table.
if grep -q "^$ws\[$ws\(toolchain\|\"toolchain\"\)$ws[].]" "$manifest"; then
  if grep "^$ws\[" "$manifest" | grep -q "toolchain$ws\." ; then unreadable; fi
  body=$(sed -n "/^$ws\[${ws}toolchain$ws\]$tail_ok\$/,/^$ws\[/p" "$manifest" | sed '1d' | sed "/^$ws\[/d")
  [ -n "$(grep "^$ws\[${ws}toolchain$ws\]$tail_ok\$" "$manifest")" ] || unreadable
  while IFS= read -r line; do
    stripped=$(printf '%s' "$line" | sed "s/^$ws//")
    case $stripped in '' | '#'*) continue ;; esac
    kv=$(printf '%s\n' "$line" | sed -n "s/^$ws\(version\|channel\|path\)$ws=$ws$str$tail_ok\$/\1 \2/p")
    [ -n "$kv" ] || unreadable
    record "${kv%% *}" "${kv#* }"
  done <<EOF
$body
EOF
fi

# Dotted keys at top level: toolchain.version = "..."
if printf '%s\n' "$top" | grep -q "^${ws}toolchain$ws\."; then
  while IFS= read -r line; do
    kv=$(printf '%s\n' "$line" | sed -n "s/^${ws}toolchain$ws\.$ws\(version\|channel\|path\)$ws=$ws$str$tail_ok\$/\1 \2/p")
    [ -n "$kv" ] || unreadable
    record "${kv%% *}" "${kv#* }"
  done <<EOF
$(printf '%s\n' "$top" | grep "^${ws}toolchain$ws\.")
EOF
fi

# Inline table at top level: toolchain = { version = "..." }
if printf '%s\n' "$top" | grep -q "^${ws}toolchain$ws="; then
  inner=$(printf '%s\n' "$top" | sed -n "s/^${ws}toolchain$ws=$ws{\(.*\)}$tail_ok\$/\1/p")
  [ -n "$inner" ] || unreadable
  case $inner in *,*) unreadable ;; esac
  kv=$(printf '%s\n' "$inner" | sed -n "s/^$ws\(version\|channel\|path\)$ws=$ws$str$ws\$/\1 \2/p")
  [ -n "$kv" ] || unreadable
  record "${kv%% *}" "${kv#* }"
fi

# --- Apply the policy -------------------------------------------------------

case $sel_kind in
  '') run_packaged "$@" ;;
  version)
    [ "$sel_value" = "$version" ] && run_packaged "$@"
    die "$manifest: [toolchain] version is \"$sel_value\", but this BAML is $version (provided by Nix). Change the version in baml.toml, or install BAML $sel_value through Nix."
    ;;
  channel)
    die "$manifest: [toolchain] channel = \"$sel_value\" is not supported: this BAML is $version (provided by Nix). Use version = \"$version\", or remove the [toolchain] table."
    ;;
  path)
    case $sel_value in
      /*) run_path "$sel_value" "$@" ;;
      *) run_path "$(dirname "$manifest")/$sel_value" "$@" ;;
    esac
    ;;
esac
unreadable
