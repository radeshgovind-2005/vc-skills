#!/bin/sh
# vc: one source of truth for local hooks and CI.
# Usage: sh .githooks/run-checks.sh [lint|test|all]
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
[ -f "$here/config" ] && . "$here/config"

run() {
  label="$1"; cmd="$2"
  if [ -z "$cmd" ]; then
    echo "run-checks: no $label command in .githooks/config (skipped)"
    return 0
  fi
  bin=${cmd%% *}
  if ! command -v "$bin" >/dev/null 2>&1; then
    if [ -n "$CI" ]; then
      echo "run-checks: '$bin' not found in CI. Failing so a missing tool cannot give a false green." >&2
      return 1
    fi
    echo "run-checks: '$bin' not found, skipping $label" >&2
    return 0
  fi
  echo "run-checks: $label: $cmd"
  sh -c "$cmd" || { echo "run-checks: $label failed" >&2; return 1; }
}

# Repo-specific gates: every executable *.sh in .githooks/checks.d/ runs, in name order.
# Use it for content checks (README rules, link checks) so hooks and CI share them.
extra() {
  [ -d "$here/checks.d" ] || return 0
  for f in "$here"/checks.d/*.sh; do
    [ -f "$f" ] || continue
    echo "run-checks: extra: ${f##*/}"
    sh "$f" || { echo "run-checks: extra ${f##*/} failed" >&2; return 1; }
  done
}

case "${1:-all}" in
  lint) run lint "$LINT_CMD" ;;
  test) run test "$TEST_CMD" ;;
  all)  run lint "$LINT_CMD" && run test "$TEST_CMD" && extra ;;
  *)    echo "usage: run-checks.sh [lint|test|all]" >&2; exit 2 ;;
esac
