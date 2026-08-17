#!/usr/bin/env bash
# Build-side unit tests for the credential gate (credential_checks.yml).
# Runs on the build workstation / container; needs ansible-playbook, no device.
#
# Exit 0 = all scenarios behave as specified, non-zero otherwise.

set -uo pipefail
cd "$(dirname "$0")"

HARNESS=cred_check_harness.yml
PASS=0; FAIL=0

expect() {  # expect <pass|fail> <label> — reads playbook exit code from $?
  local want="$1" label="$2" rc="$3"
  if { [[ "$want" == pass && "$rc" -eq 0 ]] || [[ "$want" == fail && "$rc" -ne 0 ]]; }; then
    echo "  ✓ $label"; PASS=$((PASS+1))
  else
    echo "  ✗ $label (expected $want, playbook rc=$rc)"; FAIL=$((FAIL+1))
  fi
}

run() { ansible-playbook "$HARNESS" >/dev/null 2>&1; }

env -u BRIDGE_PI_PASSWORD -u BRIDGE_WIFI_PASSWORD bash -c "ansible-playbook $HARNESS >/dev/null 2>&1"
expect fail "unset credentials are rejected" $?

BRIDGE_PI_PASSWORD=x BRIDGE_WIFI_PASSWORD=validpassphrase run
expect pass "pi password of any nonzero length is accepted" $?

BRIDGE_PI_PASSWORD=localtest BRIDGE_WIFI_PASSWORD=short run
expect fail "wifi passphrase under 8 chars is rejected" $?

BRIDGE_PI_PASSWORD=localtest BRIDGE_WIFI_PASSWORD=$(printf 'x%.0s' {1..64}) run
expect fail "wifi passphrase over 63 chars is rejected" $?

BRIDGE_PI_PASSWORD=localtest BRIDGE_WIFI_PASSWORD=validpassphrase run
expect pass "valid credentials are accepted" $?

echo "RESULT pass=$PASS fail=$FAIL skip=0"
[[ "$FAIL" -eq 0 ]]
