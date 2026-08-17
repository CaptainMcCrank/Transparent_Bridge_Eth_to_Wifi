# Smoke Tests

**Applicable to:** iot (this project)
**Frameworks:** bash + systemctl / sysfs / iw / curl, streamed to the device over SSH
**Output directory:** `tests/smoke/` (implementation: `tests/smoke/smoke_test.sh`, invoked by `./run-tests.sh --category smoke_tests`)

---

## Purpose

The fastest possible "is this bridge device alive and actually bridging?" check after a build or deployment. Runs in seconds. If smoke fails, do not proceed to deeper testing — investigate first (start with `.troubleshooting/common-failures.yaml`).

The Validation Agent (06) runs these immediately after deployment. The Deployment Troubleshooting Agent (06B) runs them as the first step of any post-incident triage.

## Project Conventions

- Smoke tests require no test data setup — they exercise the deployed device as-is.
- The runner exits non-zero on any failure; agents read exit codes, not log prose.
- Target selection: `SMOKE_TARGET` env var (default `pi@ansibledest.local`). Unreachable device = skip when the default is used (build workstation without hardware), failure when `SMOKE_TARGET` was set explicitly.
- SSH key auth must already be in place (the build procedure's `ssh-copy-id` step); the runner uses `BatchMode=yes` and never prompts.

---

## Test Cases

### TC-S-001: Core services active

- **What it covers:** hostapd, systemd-networkd, avahi-daemon, lighttpd
- **Setup:** none; deployed device reachable over SSH
- **Action:** `systemctl is-active --quiet <unit>` for each
- **Expected:** all four units report active
- **Negative cases:** hostapd inactive with brcmfmac SDIO errors in journal matches `.troubleshooting/common-failures.yaml` pattern `hostapd-brcmfmac-sdio-001` (radio hardware failure)

### TC-S-002: Bridge topology correct

- **What it covers:** the transparent L2 bridge that is this device's entire purpose
- **Setup:** none
- **Action:** check `/sys/class/net/br0` exists, `/sys/class/net/br0/brif/eth0` shows eth0 enslaved, and `/etc/hostapd/WifiRepeaterHostAPD.conf` contains `bridge=br0`
- **Expected:** all three present
- **Negative cases:** br0 exists but eth0 not enslaved usually means `bridge.yml`'s systemd-networkd files were not applied or eth0 has no link

### TC-S-003: Access point radiating with real credentials

- **What it covers:** the WiFi radio is in AP mode and the build's credential injection worked
- **Setup:** none
- **Action:** `iw dev` shows an interface with `type AP`; hostapd conf does not still contain the `wpa_passphrase=ChangeMe` placeholder
- **Expected:** AP mode present, placeholder absent
- **Negative cases:** placeholder still present means the playbook ran without `BRIDGE_WIFI_PASSWORD` before the credential gate existed, or the lineinfile regexp missed

### TC-S-004: Web surface responds

- **What it covers:** lighttpd serving the status content from `var/www/html/`
- **Setup:** none
- **Action:** `curl -fs http://localhost/` falling back to `curl -fsk https://localhost/` (self-signed cert)
- **Expected:** one of the two returns success within 5 s
- **Negative cases:** none (pass/fail)

### TC-S-005: Device label timer installed

- **What it covers:** the Inky wHAT display refresh unit from `inkywhatAP.yml`
- **Setup:** none; passes with or without the display hardware attached
- **Action:** `systemctl is-enabled --quiet Device_Label_WifiAP.timer`
- **Expected:** timer enabled
- **Negative cases:** none (pass/fail)

### TC-S-006: Client DHCP passthrough (manual)

- **What it covers:** the end-to-end promise — a WiFi client gets a lease from the wired LAN's DHCP server, same subnet, no NAT
- **Setup:** a test client (phone/laptop) and knowledge of the LAN subnet
- **Action:** join the SSID with the build passphrase; compare the client's address and gateway with a wired host's; on the device, `arp -a | grep wlan` should list the client
- **Expected:** client address is in the wired LAN's subnet
- **Negative cases:** client gets a 169.254.x.x address = DHCP broadcasts not crossing the bridge
- **Note:** not automated (needs a second radio); run by a human after first deployment of a new image
