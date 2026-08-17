#!/usr/bin/env bash
# Build-side unit tests for the inky-status display (opt/inky-status/inky_status.py).
# Runs on the build workstation; needs python3, no device and no Inky hardware.
# Rendering tests need PIL (python3-pil / Pillow) and skip cleanly without it.
#
# Exit 0 = all checks pass, non-zero otherwise.
# Last line of output: RESULT pass=<n> fail=<n> skip=<n>

set -uo pipefail
cd "$(dirname "$0")/../.."

SCRIPT=opt/inky-status/inky_status.py
OUTDIR=$(mktemp -d)
trap 'rm -rf "$OUTDIR"' EXIT

PASS=0; FAIL=0; SKIP=0

check() {  # check <label> <command...>
  local label="$1"; shift
  if "$@" >/dev/null 2>&1; then
    echo "  ✓ $label"; PASS=$((PASS+1))
  else
    echo "  ✗ $label"; FAIL=$((FAIL+1))
  fi
}

# TC-U-003a: the script must at least compile everywhere
check "inky_status.py compiles" python3 -m py_compile "$SCRIPT"

if python3 -c "import PIL" >/dev/null 2>&1; then
  # TC-U-003b: hardware-free renders in both collection modes
  check "client-mode simulate render" \
    python3 "$SCRIPT" --simulate --out "$OUTDIR/client.png"
  check "AP-mode simulate render" \
    python3 "$SCRIPT" --simulate-ap --out "$OUTDIR/ap.png"
  check "wHAT-resolution render (400x300)" \
    python3 "$SCRIPT" --simulate-ap --size 400x300 --out "$OUTDIR/what.png"

  # TC-U-003c: all six burn-in band orderings render (days 0..5)
  days_ok=true
  for d in 0 1 2 3 4 5; do
    python3 "$SCRIPT" --simulate-ap --day "$d" --out "$OUTDIR/day$d.png" \
      >/dev/null 2>&1 || days_ok=false
  done
  check "all six band orderings render (--day 0..5)" "$days_ok"
else
  echo "  - render tests (PIL not installed) (skipped)"; SKIP=$((SKIP+1))
fi

echo "RESULT pass=$PASS fail=$FAIL skip=$SKIP"
[[ "$FAIL" -eq 0 ]]
