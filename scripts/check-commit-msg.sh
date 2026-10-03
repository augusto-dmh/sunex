#!/usr/bin/env sh
# Rejects a commit message that breaks the convention in CONTRIBUTING.md:
#   <type>(<scope>): <lowercase imperative summary>   header at most 72 characters
# The only AI trailer allowed is "Assisted-by: <tool>"; Co-Authored-By, Signed-off-by
# and "Generated with" lines are rejected.
# Usage: scripts/check-commit-msg.sh <file with the message>
#        git log -1 --format=%B <sha> | scripts/check-commit-msg.sh -
set -eu

types='build|chore|ci|docs|feat|fix|perf|refactor|revert|style|test'
scopes='people|org|movements|absence|agents|shared|auth|db|arch|ui|i18n|design|docs|adr|tdd|specs|skills|ci|deps|tooling'

if [ "${1:-}" = "-" ]; then msg=$(cat); else msg=$(cat "$1"); fi
header=$(printf '%s\n' "$msg" | sed -n '1p')

case "$header" in
  Merge\ *|Revert\ \"*) exit 0 ;;
esac

# Count characters, not bytes, so accented words (férias) are measured fairly.
length=$(printf '%s' "$header" | LC_ALL=C.UTF-8 wc -m | tr -d ' ')
if [ "$length" -gt 72 ]; then
  echo "commit header is $length characters, the limit is 72: $header" >&2; exit 1
fi
# LC_ALL=C pins [a-z] to ASCII; in some locales the range also matches accented letters.
if ! printf '%s' "$header" | LC_ALL=C grep -Eq "^($types)(\(($scopes)\))?!?: [a-z0-9]"; then
  echo "commit header must be '<type>(<scope>): <lowercase summary>': $header" >&2
  echo "  types:  $types" >&2
  echo "  scopes: $scopes (optional)" >&2
  exit 1
fi
if printf '%s\n' "$msg" | LC_ALL=C grep -Eiq '^(Co-Authored-By|Signed-off-by):|(^|[^a-z])Generated with'; then
  echo "forbidden trailer: disclose AI assistance only with 'Assisted-by: <tool>'" >&2; exit 1
fi
