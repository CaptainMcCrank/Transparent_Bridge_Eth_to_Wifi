# Architectural Decision Records

This document captures significant architectural and design decisions made during the project lifecycle.

## Format

Each decision follows this format:

---

### ADR-<number>: <Title>

**Date:** <ISO 8601>
**Status:** <proposed | accepted | deprecated | superseded>
**Deciders:** <agent IDs and/or human names>

#### Context

<What situation or problem prompted this decision?>

#### Decision

<What was decided?>

#### Consequences

<What are the implications of this decision?>

#### Alternatives Considered

<What other options were evaluated?>

---

## Decisions

### ADR-001: Brownfield Adoption Without Restructuring

**Date:** 2026-08-17T12:39:36-07:00
**Status:** accepted
**Deciders:** brownfield-adoption-agent-v1.0

#### Context

This project predates the multi-agent pipeline and has an established directory structure that differs from the greenfield template: the site playbook is `run.yml` (not `site.yml`), there is a single `system` role, there are no inventory files (the target host `ansibledest.local` is named directly in the playbook), and deployed-file mirror trees (`etc/`, `usr/`, `var/`, `pi/`) sit at the repository root.

#### Decision

Adopt the project by adding pipeline metadata around the existing structure. Use `project_layout` in `project.manifest.yaml` to map actual paths instead of restructuring.

#### Consequences

- Downstream agents must read `project_layout` to find artifacts
- No disruption to existing workflows or the Docker/Ansible build process
- File paths in agent outputs may differ from pipeline documentation examples

#### Alternatives Considered

1. **Restructure to match greenfield layout** — Rejected: breaks existing references (`root_playbook_dir` paths inside tasks), the documented build procedure, and developer muscle memory
2. **Symlink compatibility layer** — Rejected: fragile, confusing, adds maintenance burden

---

### ADR-002: L2 Bridging Is the Sole Bridging Mechanism; L3 Relay Artifacts Retired

**Date:** 2026-08-17
**Status:** accepted
**Deciders:** feature-development-agent-v1.0 (resolving bead Transparent_Bridge_Eth_to_Wifi-353, filed at adoption)

#### Context

The original transparent-bridge recipe used an L3 pseudo-bridge: parprouted for proxy-ARP plus dhcp-helper as a DHCP relay. Commit `44c2090` removed the parprouted task as "unneeded" after true L2 bridging landed (`bridge.yml`: `br0` via systemd-networkd with hostapd bound via `bridge=br0`), but three companion artifacts stayed behind unreferenced: `roles/system/tasks/dhcp-helper.yml` (never imported by `main.yml` in any commit), `etc/default/dhcp-helper` (referenced only by that orphaned task), and `usr/lib/systemd/system/parprouted.service` (referenced by nothing). The orphaned task also contained a copy of `Device_Label_WP.service` whose source file no longer exists in the repository, so the task would fail if ever imported.

#### Decision

True L2 bridging is the project's sole bridging mechanism. The three dead L3-relay artifacts are deleted from HEAD.

#### Consequences

- The role's task inventory matches what `main.yml` actually runs; no orphaned tasks remain
- A future L3-relay mode (e.g., for adapters that cannot do bridged AP) must be rebuilt deliberately; the removed files are recoverable from git history (last present at commit `bef555e`)
- `docs/PRD.md` FR-011/OQ-2 are resolved by this decision

#### Alternatives Considered

1. **Document dhcp-helper.yml as an optional mode** — Rejected: it was never wired into the playbook, its Device_Label_WP copy is broken, and no configuration selects it; documenting broken dead code as a feature would mislead downstream agents
2. **Leave the files in place untouched** — Rejected: the adoption audit flagged them precisely because unreferenced task files erode trust in the role inventory

---

### ADR-003: inky-status Replaces the Device_Label Display Path; Per-App venvs over System pip

**Date:** 2026-08-17
**Status:** accepted
**Deciders:** feature-development-agent-v1.0, CaptainMcCrank (approved doc sync 2026-08-17)

#### Context

The Device_Label_WifiAP display path installed Python deps with system-wide pip3, which fails under PEP 668 on Bookworm's externally-managed interpreter, and drove the interactive get.pimoroni.com script via `expect` with `ignore_errors: true`. A replacement was developed and hardware-verified in the FixingSDCard effort (GH issue #2, PR #3).

#### Decision

inky-status (venv with `--system-site-packages` over apt compiled deps, oneshot service + daily timer, stateless date-derived anti-ghosting rotation, AP-aware Wi-Fi band) is the sole e-paper display path. Python dependencies on the target are installed into per-app venvs, never with system-wide pip.

#### Consequences

- Legacy artifacts deleted from HEAD (recoverable at tag `pre-feature-issue-2`); playbook re-runs converge already-deployed devices
- Display no longer lists per-client MACs or build info (user confirmed 2026-08-17 that the AP band's station count suffices; bead Transparent_Bridge_Eth_to_Wifi-gvb closed without implementation)
- Boards without an ID EEPROM need `INKY_BOARD` named explicitly (`inky_board` var / `/etc/default/inky-status`)

#### Alternatives Considered

1. **Fix the legacy path in place** — Rejected: every dependency mechanism it used is broken or deprecated on current Raspberry Pi OS
2. **Run both displays** — Rejected: two timers drawing to one panel overwrite each other
