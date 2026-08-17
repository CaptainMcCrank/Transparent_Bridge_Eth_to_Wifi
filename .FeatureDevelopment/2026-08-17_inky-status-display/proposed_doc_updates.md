# Proposed canonical-doc updates (Phase 6d — awaiting user approval)

This session ran non-interactively, so the Phase 6d confirmation gate could not
be exercised live. Nothing below has been applied. Each block is the exact edit
proposed; approve/adjust and apply (tracked as beads issue
Transparent_Bridge_Eth_to_Wifi doc-sync entries filed at session end).

---

## 1. `docs/PRD.md` — FR-004 row (line 29)

The row is factually wrong on HEAD of this branch: the artifacts it names are
deleted and the behavior changed.

```diff
-| FR-004 | E-paper device label: Inky wHAT display service and timer showing build info and up to 14 attached client MACs | `roles/system/tasks/inkywhatAP.yml`, `usr/local/bin/Device_Label_WifiAP.py` | Implemented | ⚠️ Broken import (see OQ-1) |
+| FR-004 | E-paper status display: inky-status service + daily timer showing hostname/IPv4, AP SSID + station count (client SSID + signal when not an AP), and uptime, with daily band rotation against e-ink ghosting | `roles/system/tasks/inky_status.yml`, `opt/inky-status/inky_status.py` | Implemented (GH #2) | ✅ Complete |
```

## 2. `docs/PRD.md` — NFR-005 (line 46)

```diff
-- **NFR-005 — Observability at a glance:** device state (build version, attached clients) is readable from the physical e-paper display without logging in.
+- **NFR-005 — Observability at a glance:** device state (hostname, IP, AP SSID, attached-client count, uptime) is readable from the physical e-paper display without logging in. The pre-GH#2 display also listed per-client MAC addresses and build info; restoring those as an extra band is open as a follow-up beads issue.
```

## 3. `docs/techstack_decision.md` — under "## Package Dependencies"

Add:

```markdown
- **inky (pip, in a dedicated venv at `/opt/inky-status/venv`)** — e-paper
  driver for the status display (GH #2). The venv is created with
  `--system-site-packages` so compiled deps (numpy, Pillow, spidev, smbus2,
  gpiod) come from apt (`python3-spidev` has no aarch64 wheel); only `inky`
  itself comes from pip. This is the project's pattern for Python deps on
  Bookworm's externally-managed interpreter — never system-wide pip.
```

## 4. `DECISIONS.md` — new ADR-003

```markdown
### ADR-003: inky-status Replaces the Device_Label Display Path; Per-App venvs over System pip

**Date:** 2026-08-17
**Status:** proposed (accepted on merge of PR for GH #2)
**Deciders:** feature-development-agent-v1.0, CaptainMcCrank (PR review)

#### Context

The Device_Label_WifiAP display path installed Python deps with system-wide
pip3 (fails under PEP 668 on Bookworm) and drove the interactive
get.pimoroni.com script via expect with ignore_errors: true. A replacement was
developed and hardware-verified in the FixingSDCard effort.

#### Decision

inky-status (venv with --system-site-packages over apt compiled deps, oneshot
service + daily timer, stateless date-derived anti-ghosting rotation,
AP-aware Wi-Fi band) is the sole e-paper display path. Python deps on the
target are installed into per-app venvs, never with system-wide pip.

#### Consequences

- Legacy artifacts deleted from HEAD (recoverable at tag pre-feature-issue-2);
  playbook re-runs converge already-deployed devices
- Display no longer lists per-client MACs or build info (follow-up bead open)
- Boards without an ID EEPROM need INKY_BOARD named explicitly (inky_board var)

#### Alternatives Considered

1. **Fix the legacy path in place** — Rejected: every dependency mechanism it
   uses is broken or deprecated on current Raspberry Pi OS
2. **Run both displays** — Rejected: two timers drawing to one panel overwrite
   each other
```

## 5. `.troubleshooting/common-failures.yaml` — three new patterns

Signatures verified during the FixingSDCard hardware effort (source
Agent_README Gotchas 1–3), reformatted to this file's schema:

- `inky-no-eeprom-001`: `RuntimeError: No EEPROM detected!` → board lacks ID
  EEPROM or i2c-dev module not loaded; check `/dev/i2c-1` exists, then set
  `INKY_BOARD=what` in `/etc/default/inky-status`
- `inky-gpio8-claimed-001`: `Woah there, some pins we need are in use! Chip
  Select: (line 8, GPIO8) currently claimed by spi0 CS0` → `dtoverlay=spi0-0cs`
  missing from boot config; reboot required after adding
- `pip-spidev-build-fail-001`: `fatal error: Python.h: No such file or
  directory` during pip install → compiled dep being built by pip instead of
  taken from apt; install `python3-spidev` and use `--system-site-packages`
