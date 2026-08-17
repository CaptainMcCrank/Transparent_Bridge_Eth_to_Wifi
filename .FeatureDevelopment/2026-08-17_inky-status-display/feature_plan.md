# Feature Plan: Integrate inky-status network/configuration status display

**Issue:** #2
**Classification:** feature
**Agent:** feature-dev-agent-v1.0
**Beads:** Transparent_Bridge_Eth_to_Wifi-6fh
**Date:** 2026-08-17

---

## Problem Statement

The bridge device should display network/configuration status (hostname, IPv4 +
interface, Wi-Fi/AP state, uptime) on its Inky e-paper panel. The existing
display path (`roles/system/tasks/inkywhatAP.yml` + `Device_Label_WifiAP.py`)
is broken on modern Raspberry Pi OS: it installs Python deps with system-wide
`pip3` (fails under PEP 668 externally-managed Python on Bookworm), drives the
interactive `get.pimoroni.com/inky` script via `expect` with
`ignore_errors: true`, and hardcodes `InkyWHAT("red")`.

A replacement was developed and hardware-verified in the FixingSDCard effort
(`~/Development/FixingSDCard/inky-status/`): venv with `--system-site-packages`
over apt-provided compiled deps, oneshot service + daily timer, stateless
date-derived band rotation to spread e-ink ghosting. Its `Agent_README.md`
documents the install procedure and six verified gotchas, and instructs
porting `install.sh` to idempotent Ansible tasks.

## Acceptance Criteria

- [ ] `inky_status.py` + service + timer deployed by an idempotent Ansible task file
- [ ] Boot config (`dtparam=spi=on`, `dtparam=i2c_arm=on`, `dtoverlay=spi0-0cs`) and `i2c-dev` module handled with anchored-regex idempotence
- [ ] Board selection exposed as Ansible variables; existing per-host `/etc/default/inky-status` never clobbered
- [ ] AP-aware: on the bridge (wlan in AP mode, no NetworkManager) the Wi-Fi band shows AP SSID + station count instead of "no wi-fi"
- [ ] Legacy Device_Label artifacts retired; `ClearLogs.sh` deployment unaffected
- [ ] Hardware-free tests pass; TC-S-005 tracks the new timer
- [ ] No regressions (baseline: 6 pass / 0 fail / 1 skip)

## Knowledge Base Findings

- `.AgentLessonsLearned/`, `.ContextAcquisition/`: directories absent (brownfield, first feature). No relevant entries.
- `.AgentDiaries/2026-08-17_123936_orient_brownfield-adoption.md`: adoption diary; flags OQ-1 (since fixed — `main.yml` imports `inkywhatAP.yml` correctly at HEAD).
- `DECISIONS.md` ADR-002: L3-relay artifacts retired; established the precedent that orphaned task files are deleted, and already removed the broken `Device_Label_WP.service` copy. `Device_Label_WP.py` remains in `usr/local/bin/` referenced by nothing.
- `.troubleshooting/common-failures.yaml`: no display-related signatures.
- Source knowledge: `FixingSDCard/inky-status/Agent_README.md` — six verified gotchas (spidev has no aarch64 wheel → use apt; i2c_arm=on doesn't create /dev/i2c-* without i2c-dev module; inky needs `dtoverlay=spi0-0cs` to free GPIO8; minimal images ship zero fonts; iw lives in /usr/sbin off non-login PATH; a successful draw proves nothing — SPI is write-only).

## Canonical Spec Anchoring

- **PRD FR-004:** "E-paper device label: Inky wHAT display service and timer showing build info and up to 14 attached client MACs." This change replaces that implementation; new display shows hostname/IP/AP-SSID/station-count/uptime, not the 14 MAC list → **PRD impact, Phase 6d**.
- **PRD NFR-005:** "device state (build version, attached clients) readable from the physical e-paper display" — station *count* preserved; build version and per-client MACs are not → follow-up beads issue for a MAC-list band if wanted.
- **ADR-001:** brownfield layout preserved; mirror trees at repo root. New `opt/` mirror tree follows the same convention (manifest `system_files` updated).
- **ADR-002:** precedent for deleting orphaned artifacts.

## Approach

Port `install.sh` to `roles/system/tasks/inky_status.yml`, replacing the
`inkywhatAP.yml` import in `main.yml`. Ship the display files via mirror
trees per ADR-001. Adapt `inky_status.py` minimally for this project's
hardware and role:

1. **`what` board option** — target hardware is an Inky wHAT (legacy code
   hardcoded `InkyWHAT("red")`, suggesting the board may predate the ID
   EEPROM, in which case `auto` would fail). Default stays `auto`;
   `inky_board`/`inky_colour` Ansible vars feed `/etc/default/inky-status`.
2. **AP-aware Wi-Fi band** — the bridge's wlan is an AP under hostapd with no
   NetworkManager, so the verified client-mode collection (`iw dev link`,
   `nmcli`) would render a permanent, misleading "no wi-fi". When an
   interface is in AP mode, collect SSID from `iw dev <iface> info` and
   station count from `iw dev <iface> station dump`, and render
   "AP <ssid>" + "N clients". Client-mode behavior is unchanged for other
   deployments. This is the one deliberate divergence from the verified
   source; it is exercised hardware-free via `--simulate-ap` preview renders.

### Changes Required

| File/Role | Change | Risk |
|-----------|--------|------|
| `opt/inky-status/inky_status.py` | New (adapted from verified source: + `what` board, + AP band, + `--simulate-ap`) | Medium |
| `etc/systemd/system/inky-status.service` | New (verbatim from source) | Low |
| `etc/systemd/system/inky-status.timer` | New (verbatim from source) | Low |
| `roles/system/tasks/inky_status.yml` | New — idempotent port of `install.sh` | Medium |
| `roles/system/tasks/main.yml` | Import `inky_status.yml` instead of `inkywhatAP.yml` | Low |
| `roles/system/defaults/main.yml` | Add `inky_board`, `inky_colour` vars | Low |
| `roles/system/tasks/inkywhatAP.yml` | Delete (replaced) | Low |
| `etc/systemd/system/Device_Label_WifiAP.{service,timer}` | Delete (replaced) | Low |
| `usr/local/bin/Device_Label_WifiAP.py` | Delete (replaced) | Low |
| `usr/local/bin/Device_Label_WP.py` | Delete (dead since ADR-002) | Low |
| `tests/smoke/smoke_test.sh` | TC-S-005 checks `inky-status.timer`; add TC-S-012 venv import check | Low |
| `tests/unit/inky_status_test.sh` | New hardware-free render/compile tests | Low |
| `docs/test_catalog/{smoke,unit}_tests.md` | Update TC-S-005, add new TCs (additions + in-place update; no deletions) | Low |
| `project.manifest.yaml` | `system_files` += `opt/`; agents entry | Low |

Legacy service/timer on already-deployed devices: `inky_status.yml` disables
`Device_Label_WifiAP.timer`/`.service` and removes the unit files and scripts
on the target, so a re-run of the playbook converges live devices too.

## Test Strategy

- **Pre-change baseline:** `./run-tests.sh` → 6 pass / 0 fail / 1 skip (smoke skipped: no device reachable). Recorded below.
- **New tests (hardware-free):**
  - `tests/unit/inky_status_test.sh`: `py_compile` of `inky_status.py`; `--simulate --out` PNG render; `--simulate-ap --out` render showing AP band; render across `--day 0..5` (exercises all band orderings). PIL-dependent steps skip cleanly when PIL is absent.
  - Smoke additions (device-side): timer enabled, venv imports resolve, fonts present (`fc-list | wc -l > 0` — Gotcha 4).
- **Post-change:** full suite; compare with baseline. No regressions allowed.
- **Not verifiable here:** an actual panel draw (Gotcha 6: SPI is write-only; only visual confirmation proves it). Flagged in PR verification steps.

## Risks

- **Board without ID EEPROM →** `auto` fails at draw time with "No EEPROM detected". Mitigation: `INKY_BOARD` override via Ansible var / `/etc/default/inky-status`, `what` option added; PR verification steps include checking `systemctl show -p Result inky-status.service` after first boot.
- **AP-band code is the untested-on-hardware delta.** Mitigation: pure additions gated behind AP detection; falls back to verified client-mode path; preview renders exercised in unit tests.
- **apt package availability on Bookworm** (`python3-smbus2`, `python3-libgpiod`): both exist in Debian 12; verified names against source README (tested on trixie). Low residual risk.
- **Live devices keep running legacy timer** if playbook not re-run — convergence tasks included; rollback is `git revert` + re-run.

## Documentation Impact

| Doc | Impact | Planned update |
|---|---|---|
| `docs/PRD.md` | FR-004 behavior replaced; NFR-005 partially re-scoped | Rewrite FR-004 row to describe inky-status; note MAC-list loss + follow-up bead |
| `docs/feature_list.md` | absent | none (gap noted; do not create) |
| `docs/techstack_decision.md` | New dep pattern: per-app venv + apt compiled deps; `inky` pinned via pip in venv | Add entry with rationale |
| `domain_knowledge/service_dependencies.yml` | absent | none (gap noted; do not create) |
| `domain_knowledge/compatibility_matrix.yml` | absent | none |
| `DECISIONS.md` | New ADR required (replace legacy display path; venv-over-system-pip pattern) | ADR-003 drafted in `proposed_doc_updates.md` |
| `.troubleshooting/common-failures.yaml` | Novel signatures from source gotchas | Add EEPROM/GPIO8/spidev signatures |

All rows requiring edits go through the Phase 6d confirmation gate. This
session runs non-interactively, so canonical-doc edits are **deferred**: diffs
are staged in `proposed_doc_updates.md`, presented to the user at session end,
and filed as beads issues. See "Deferred doc updates" below.

## Impact Analysis

### Affected Features

| Feature | Dependency Type | Risk Level |
|---------|-----------------|------------|
| Device label display (FR-004) | Replaced outright | Medium |
| ClearLogs.sh deployment | Was co-deployed by legacy bulk `usr/local/bin/` sync; independently deployed by `essential.yml:265` | None |
| hostapd / bridge / web / avahi | Untouched; new tasks only add packages, /opt files, units, boot-config lines | Low |
| Boot config | Three appended `config.txt` lines (SPI/I2C/spi0-0cs); anchored-regex guarded | Low |

### Baseline Smoke Tests

**Run at:** 2026-08-17 (session start, pre-branch)
**Command:** `./run-tests.sh`
**Results:** 6 PASS, 0 FAIL, 1 SKIP

| Test | Result | Notes |
|------|--------|-------|
| smoke suite | SKIP | no device reachable at pi@ansibledest.local (unset SMOKE_TARGET → skip by design) |
| playbook syntax check | PASS | |
| unset credentials are rejected | PASS | |
| pi password of any nonzero length is accepted | PASS | |
| wifi passphrase under 8 chars is rejected | PASS | |
| wifi passphrase over 63 chars is rejected | PASS | |
| valid credentials are accepted | PASS | |

**Baseline captured for regression detection.**

## Deferred doc updates

Phase 6d ran non-interactively, so all canonical-doc edits are deferred with
exact diffs staged in `proposed_doc_updates.md`:

1. `docs/PRD.md` FR-004 row — now factually wrong (names deleted files)
2. `docs/PRD.md` NFR-005 — scope of at-a-glance info changed
3. `docs/techstack_decision.md` — per-app venv dependency pattern + `inky`
4. `DECISIONS.md` — proposed ADR-003 (display replacement, venv-over-system-pip)
5. `.troubleshooting/common-failures.yaml` — three verified signatures

Filed as beads issue (doc-sync) at session close; `docs/feature_list.md` and
`domain_knowledge/` files are absent (gap noted, not created per protocol).

## Rollback

```bash
git revert <commit>          # then re-run the playbook to converge devices
# or discard the branch entirely:
git checkout main && git branch -D feature/issue-2-inky-status-display
git tag -d pre-feature-issue-2
```
