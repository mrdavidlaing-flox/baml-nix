#!/bin/sh
# `baml` for Nix: runs the packaged BAML toolchain, never downloads one, and
# refuses projects whose baml.toml asks for a different toolchain.
# Upstream's launcher (baml_language/wrapper) manages toolchains itself;
# under Nix the version is chosen by the Nix/Flox environment instead.
set -u

version='@version@'
cli='@cli@'
# Fixed GNU tools: the parsing below must not depend on the user's PATH.
SED='@sed@'
GREP='@grep@'
DIRNAME='@dirname@'

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

# --- Arguments, parsed like upstream's wrapper (invocation.baml) ------------
# --project is read in any position except after the `query` command; the
# values of value-taking global flags are skipped.

project_arg=''
command_word=''
sub_word=''
expect_project=0
skip_value=0
for arg in "$@"; do
  if [ "$expect_project" = 1 ]; then
    project_arg=$arg
    expect_project=0
    continue
  fi
  if [ "$skip_value" = 1 ]; then
    skip_value=0
    continue
  fi
  [ "$arg" = -- ] && break
  if [ "$command_word" != query ]; then
    case $arg in
      --project)
        expect_project=1
        continue
        ;;
      --project=*)
        project_arg=${arg#--project=}
        continue
        ;;
    esac
  fi
  if [ -z "$command_word" ]; then
    case $arg in
      --output-preset | --color | --hyperlinks | --diagnostic-format | --agent-skill-check) skip_value=1 ;;
      -*) ;;
      *) command_word=$arg ;;
    esac
    continue
  fi
  if [ -z "$sub_word" ]; then
    case $arg in
      -*) ;;
      *) sub_word=$arg ;;
    esac
  fi
done

# --- Toolchain management belongs to Nix -------------------------------------

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
  [ -f "$dir" ] && {
    printf '%s\n' "$dir"
    return 0
  }
  dir=$(cd "$dir" 2>/dev/null && pwd -P) || return 1
  while :; do
    if [ -f "$dir/baml.toml" ]; then
      printf '%s\n' "$dir/baml.toml"
      return 0
    fi
    [ "$dir" = / ] && return 1
    dir=$("$DIRNAME" "$dir")
  done
}

manifest=$(find_manifest "${project_arg:-.}") || run_packaged "$@"

# --- Read its toolchain selector (fail safe on anything unexpected) ---------

unreadable() {
  die "$manifest: could not read the [toolchain] selector; this BAML is $version (provided by Nix)."
}

# Normalised copy: no UTF-8 BOM, no CR line endings.
content=$("$SED" -e '1s/^\xEF\xBB\xBF//' -e 's/\r$//' "$manifest") || unreadable
lines() { printf '%s\n' "$content"; }

ws='[[:space:]]*'
str='"\([^"\\]*\)"'
tail_ok="$ws\(#.*\)\{0,1\}"
header_re="^$ws\[${ws}toolchain$ws\]$tail_ok\$"
dotted_re="^${ws}toolchain$ws\.$ws\(version\|channel\|path\)$ws=$ws$str$tail_ok\$"
inline_re="^${ws}toolchain$ws=$ws{$ws\(version\|channel\|path\)$ws=$ws$str$ws}$tail_ok\$"
kv_re="^$ws\(version\|channel\|path\)$ws=$ws$str$tail_ok\$"
# Any line naming `toolchain` as a key or table, in any TOML spelling.
mention_re="^$ws\[\{0,2\}$ws[\"']\{0,1\}toolchain[\"']\{0,1\}$ws[].=]"

sel_kind=''
sel_value=''
record() { # "kind value"
  [ -z "$sel_kind" ] || unreadable
  sel_kind=${1%% *}
  sel_value=${1#* }
}

# Top level ends at the first line starting with `[` (a table header, or a
# multi-line array continuation; either way, later lines are not top level).
first_header=$(lines | "$GREP" -n "^$ws\[" | "$SED" -n '1s/:.*//p')
top_end=${first_header:+$((first_header - 1))}

accepted=' '

# The [toolchain] table.
header_lines=$(lines | "$GREP" -n "$header_re" | "$SED" 's/:.*//')
case $header_lines in
  *[!0-9]*) unreadable ;; # more than one [toolchain] header
esac
if [ -n "$header_lines" ]; then
  accepted="$accepted$header_lines "
  body=$(lines | "$SED" -n "$((header_lines + 1)),\$p" | "$SED" "/^$ws\[/,\$d")
  while IFS= read -r line; do
    case $(printf '%s' "$line" | "$SED" "s/^$ws//") in
      '' | '#'*) continue ;;
    esac
    kv=$(printf '%s\n' "$line" | "$SED" -n "s/$kv_re/\1 \2/p")
    [ -n "$kv" ] || unreadable
    record "$kv"
  done <<EOF
$body
EOF
fi

# Dotted keys and inline tables, only at top level.
while IFS=: read -r n line; do
  [ -n "$n" ] || continue
  if [ -n "$top_end" ] && [ "$n" -gt "$top_end" ]; then continue; fi
  kv=$(printf '%s\n' "$line" | "$SED" -n -e "s/$dotted_re/\1 \2/p" -e "s/$inline_re/\1 \2/p")
  [ -n "$kv" ] || continue
  accepted="$accepted$n "
  record "$kv"
done <<EOF
$(lines | "$GREP" -n "$mention_re")
EOF

# Anything else that names `toolchain` is a spelling we don't understand.
while IFS=: read -r n _; do
  [ -n "$n" ] || continue
  case $accepted in
    *" $n "*) ;;
    *) unreadable ;;
  esac
done <<EOF
$(lines | "$GREP" -n "$mention_re")
EOF

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
      *) run_path "$("$DIRNAME" "$manifest")/$sel_value" "$@" ;;
    esac
    ;;
esac
unreadable
