#!/usr/bin/env bash
# run-tests.sh — the project's single test entrypoint.
#
# Contract (Standards/Contracts/Project_Contract.md §Tests entrypoint):
#   ./run-tests.sh                     run the default suite (smoke + unit)
#   ./run-tests.sh --list              enumerate available categories
#   ./run-tests.sh --category <name>   run one catalog category
#   exit 0 = pass, non-zero = fail
#   last line of output: RESULT pass=<n> fail=<n> skip=<n>
#
# Smoke tests run on a deployed bridge device over SSH. Set SMOKE_TARGET
# (e.g. pi@ansibledest.local) to point at it. When SMOKE_TARGET is unset and
# the default target is unreachable, smoke is skipped rather than failed so
# the suite stays useful on a build workstation with no device attached;
# when SMOKE_TARGET is set explicitly, an unreachable device is a failure.

set -uo pipefail
cd "$(dirname "$0")"

PASS=0; FAIL=0; SKIP=0

CATEGORIES=(
  smoke_tests
  unit_tests
)
DEFAULT_SUITE=(smoke_tests unit_tests)

record() {  # record <pass|fail|skip> <label>
  case "$1" in
    pass) PASS=$((PASS+1)); echo "  ✓ $2" ;;
    fail) FAIL=$((FAIL+1)); echo "  ✗ $2" ;;
    skip) SKIP=$((SKIP+1)); echo "  - $2 (skipped)" ;;
  esac
}

run_cmd() {  # run_cmd <label> <command...> — one test = one command's exit code
  if "${@:2}"; then record pass "$1"; else record fail "$1"; fi
}

absorb_result() {  # absorb_result <output> — fold a sub-runner's RESULT line into our counters
  local line
  line=$(printf '%s\n' "$1" | grep -E '^RESULT ' | tail -1)
  PASS=$((PASS + $(sed -E 's/.*pass=([0-9]+).*/\1/' <<<"$line")))
  FAIL=$((FAIL + $(sed -E 's/.*fail=([0-9]+).*/\1/' <<<"$line")))
  SKIP=$((SKIP + $(sed -E 's/.*skip=([0-9]+).*/\1/' <<<"$line")))
  printf '%s\n' "$1" | grep -vE '^RESULT '
}

run_smoke_tests() {
  local target="${SMOKE_TARGET:-pi@ansibledest.local}"
  local out
  if ! ssh -o ConnectTimeout=5 -o BatchMode=yes "$target" true 2>/dev/null; then
    if [[ -n "${SMOKE_TARGET:-}" ]]; then
      record fail "smoke: device $target unreachable over SSH"
    else
      record skip "smoke: no device reachable at $target (set SMOKE_TARGET to point at one)"
    fi
    return
  fi
  out=$(ssh -o BatchMode=yes "$target" bash < tests/smoke/smoke_test.sh 2>&1)
  absorb_result "$out"
}

run_unit_tests() {
  run_cmd "playbook syntax check" env ANSIBLE_STDOUT_CALLBACK=oneline ansible-playbook run.yml --syntax-check
  local out
  out=$(tests/unit/credential_checks_test.sh 2>&1)
  absorb_result "$out"
  out=$(tests/unit/inky_status_test.sh 2>&1)
  absorb_result "$out"
}

# ── plumbing ────────────────────────────────────────────────────────────────
finish() {
  echo "RESULT pass=$PASS fail=$FAIL skip=$SKIP"
  [[ "$FAIL" -eq 0 ]]
}

run_category() {
  local cat="$1"
  local fn="run_${cat}"
  if ! declare -F "$fn" >/dev/null; then
    echo "✗ Unknown or unimplemented category: $cat (try --list)" >&2
    exit 2
  fi
  echo "── $cat ──"
  "$fn"
}

case "${1:-}" in
  --list)
    printf '%s\n' "${CATEGORIES[@]}"
    exit 0 ;;
  --category)
    [[ -n "${2:-}" ]] || { echo "✗ --category needs a name (try --list)" >&2; exit 2; }
    run_category "$2"; finish ;;
  -h|--help)
    sed -n '2,15p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
  "")
    for c in "${DEFAULT_SUITE[@]}"; do run_category "$c"; done; finish ;;
  *)
    echo "✗ Unknown arg: $1 (try --help)" >&2; exit 2 ;;
esac
