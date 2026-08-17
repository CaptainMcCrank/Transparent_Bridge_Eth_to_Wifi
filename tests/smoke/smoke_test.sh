#!/usr/bin/env bash
# Device-side smoke tests for the Transparent_Bridge_Eth_to_Wifi build.
#
# Runs ON the bridge device (locally, or streamed over SSH by run-tests.sh:
#   ssh pi@<device> bash < tests/smoke/smoke_test.sh
# ). No test data setup — exercises what is already deployed.
#
# Exit 0 = all checks pass, non-zero otherwise.
# Last line of output: RESULT pass=<n> fail=<n> skip=<n>

set -uo pipefail

PASS=0; FAIL=0; SKIP=0

check() {  # check <label> <command...>
  local label="$1"; shift
  if "$@" >/dev/null 2>&1; then
    echo "  ✓ $label"; PASS=$((PASS+1))
  else
    echo "  ✗ $label"; FAIL=$((FAIL+1))
  fi
}

# TC-S-001: core services
check "hostapd.service active"          systemctl is-active --quiet hostapd
check "systemd-networkd active"         systemctl is-active --quiet systemd-networkd
check "avahi-daemon active"             systemctl is-active --quiet avahi-daemon
check "lighttpd active"                 systemctl is-active --quiet lighttpd

# TC-S-002: bridge topology
check "br0 bridge interface exists"     test -d /sys/class/net/br0
check "eth0 enslaved to br0"            test -e /sys/class/net/br0/brif/eth0
check "hostapd bound to br0"            grep -q '^bridge=br0' /etc/hostapd/WifiRepeaterHostAPD.conf

# TC-S-003: access point actually radiating
check "a wifi interface is in AP mode"  bash -c 'iw dev | grep -q "type AP"'
check "wifi passphrase is not the ChangeMe placeholder" \
  bash -c '! grep -q "^wpa_passphrase=ChangeMe" /etc/hostapd/WifiRepeaterHostAPD.conf'

# TC-S-004: web surface
check "web server responds on localhost" \
  bash -c 'curl -fs --max-time 5 -o /dev/null http://localhost/ || curl -fsk --max-time 5 -o /dev/null https://localhost/'

# TC-S-005: status display timer installed (enabled even without inky hardware attached)
check "inky-status.timer enabled"        systemctl is-enabled --quiet inky-status.timer
check "legacy Device_Label_WifiAP.timer gone" \
  bash -c '! systemctl is-enabled --quiet Device_Label_WifiAP.timer'

# TC-S-007: status display runtime intact (venv imports resolve, fonts present)
check "inky-status venv imports resolve" \
  /opt/inky-status/venv/bin/python -c "import inky, PIL, numpy, spidev, gpiod"
check "a truetype font is installed" \
  test -f /usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf
check "inky-status renders headlessly" \
  /opt/inky-status/venv/bin/python /opt/inky-status/inky_status.py --out /tmp/inky_smoke.png

echo "RESULT pass=$PASS fail=$FAIL skip=$SKIP"
[[ "$FAIL" -eq 0 ]]
