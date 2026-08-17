# Working Solution: Integrate inky-status network/configuration status display

**Issue:** #2
**Branch:** feature/issue-2-inky-status-display
**Date:** 2026-08-17

## Summary

The bridge device's e-paper display is now driven by `inky-status`, the
hardware-verified implementation from the FixingSDCard effort: a oneshot
systemd service on a daily timer rendering three bands (hostname + IPv4 +
interface, Wi-Fi/AP state, uptime + timestamp) with date-derived band rotation
to spread e-ink ghosting. Its `install.sh` was ported to an idempotent Ansible
task file. The legacy `Device_Label_WifiAP` path — system-pip installs that
fail on Bookworm's externally-managed Python, and an `expect`-driven
`get.pimoroni.com` curl-pipe — is retired from both the repo and (via
convergence tasks) already-deployed devices.

Two deliberate divergences from the verified source, both exercised by
hardware-free renders:

1. **AP-aware Wi-Fi band.** The bridge's wlan is a hostapd AP with no
   NetworkManager, so the client-mode probes would render a permanent
   "no wi-fi". When `iw dev` reports an interface with `type AP`, the band
   shows "AP <ssid>" and the associated station count from
   `iw dev <iface> station dump` instead. Client-mode behavior is unchanged.
2. **`what` board option.** The deployed panel is an Inky wHAT and the legacy
   code hardcoded `InkyWHAT("red")`, suggesting the board may predate the ID
   EEPROM that `inky.auto()` needs. `INKY_BOARD=what` names it explicitly;
   the default remains `auto`, settable via the `inky_board` / `inky_colour`
   Ansible vars without clobbering a per-host `/etc/default/inky-status`.

## Changes Made

| File | Change |
|------|--------|
| `opt/inky-status/inky_status.py` | New — adapted from verified source (+AP band, +`what`, +`--simulate-ap`) |
| `etc/systemd/system/inky-status.service` | New — verbatim from source |
| `etc/systemd/system/inky-status.timer` | New — verbatim from source (daily + 2min-after-boot + Persistent) |
| `roles/system/tasks/inky_status.yml` | New — idempotent port of install.sh: boot-config lines (anchored regex incl. commented stock forms), i2c-dev module, apt deps, venv `--system-site-packages` + pip `inky`, file installs, no-clobber board defaults, timer enable, legacy-unit retirement |
| `roles/system/tasks/main.yml` | Imports `inky_status.yml` in place of `inkywhatAP.yml` |
| `roles/system/defaults/main.yml` | `inky_board: "auto"`, `inky_colour: "red"` |
| `roles/system/tasks/inkywhatAP.yml` | Deleted (replaced) |
| `etc/systemd/system/Device_Label_WifiAP.{service,timer}` | Deleted (replaced) |
| `usr/local/bin/Device_Label_WifiAP.py` | Deleted (replaced) |
| `usr/local/bin/Device_Label_WP.py` | Deleted (dead since ADR-002) |
| `tests/unit/inky_status_test.sh` | New — TC-U-003 hardware-free compile + renders |
| `tests/smoke/smoke_test.sh` | TC-S-005 tracks `inky-status.timer` + legacy-gone check; TC-S-007 venv imports / fonts / headless render |
| `run-tests.sh` | Runs the new unit test |
| `docs/test_catalog/{smoke,unit}_tests.md` | TC-S-005 updated in place; TC-S-007 and TC-U-003 added (no TC deleted) |
| `project.manifest.yaml` | `system_files` += `opt/`; agent registered |
| `.agent-ownership.yaml` | Entries for new artifacts |

`ClearLogs.sh` deployment is unaffected: it is installed by `essential.yml:265`,
independently of the legacy bulk `usr/local/bin/` sync that was removed.

## Regression Verification

**Verification completed at:** 2026-08-17 (post-implementation)

### Results
- Tests before changes: 6 PASS, 0 FAIL, 1 SKIP
- Tests after changes: 11 PASS, 0 FAIL, 1 SKIP
- Regressions detected: **No**

### Test-by-Test Comparison

| Test | Before | After | Notes |
|------|--------|-------|-------|
| smoke suite | SKIP | SKIP | no device reachable (unset SMOKE_TARGET → skip by design) |
| playbook syntax check | PASS | PASS | validates the new task file parses and the import swap |
| unset credentials are rejected | PASS | PASS | |
| pi password of any nonzero length is accepted | PASS | PASS | |
| wifi passphrase under 8 chars is rejected | PASS | PASS | |
| wifi passphrase over 63 chars is rejected | PASS | PASS | |
| inky_status.py compiles | N/A | PASS | New |
| client-mode simulate render | N/A | PASS | New |
| AP-mode simulate render | N/A | PASS | New |
| wHAT-resolution render (400x300) | N/A | PASS | New; output visually inspected: "AP workshop / 3 clients (wlan0)" band renders correctly |
| all six band orderings render (--day 0..5) | N/A | PASS | New |

**Regression gate: PASSED**

## Verification

Build-side (already run, all green):

```bash
./run-tests.sh
```

On a deployed device after re-running the playbook and rebooting (the three
boot-config lines take effect at boot):

```bash
ls /dev/spidev0.0 /dev/i2c-1                            # both must exist
systemctl list-timers inky-status.timer --no-pager      # next run scheduled
systemctl start inky-status.service
systemctl show -p Result --value inky-status.service    # expect: success
# If it fails with "No EEPROM detected": set INKY_BOARD=what in
# /etc/default/inky-status (or inky_board: "what" in role defaults) and retry.
```

Then **confirm visually** — SPI is write-only, so a successful draw proves
nothing about the panel (source Agent_README, Gotcha 6).
