# Unit Tests

**Applicable to:** iot (this project)
**Frameworks:** ansible-playbook (syntax check + localhost harness playbooks), bash
**Output directory:** `tests/unit/` (invoked by `./run-tests.sh --category unit_tests`)

---

## Purpose

Build-side correctness checks that need no target device: does the playbook parse, and do the pieces with real logic behave as specified? For an Ansible project the deepest-leverage logic lives in guard tasks and templated values, so those are what get unit coverage.

## Project Conventions

- Unit tests run on the build workstation or container; they must never touch a real device or require secrets beyond throwaway values injected per-test.
- Harness playbooks target `localhost` with `ansible_python_interpreter: "{{ ansible_playbook_python }}"` so they run anywhere ansible does.

---

## Test Cases

### TC-U-001: Playbook syntax check

- **What it covers:** every task file reachable from `run.yml` parses (this exact check would have caught the `inkywhat.yml` broken import fixed in bead Transparent_Bridge_Eth_to_Wifi-ux0)
- **Setup:** ansible with the `community.crypto` and `ansible.posix` collections installed
- **Action:** `ansible-playbook run.yml --syntax-check`
- **Expected:** exit 0
- **Negative cases:** missing collection on a fresh workstation fails here, not mid-build

### TC-U-002: Credential gate behavior

- **What it covers:** `roles/system/tasks/credential_checks.yml` (the fail-fast guard added for bead Transparent_Bridge_Eth_to_Wifi-9d6)
- **Setup:** `tests/unit/cred_check_harness.yml` mirrors the env lookups from role defaults
- **Action:** `tests/unit/credential_checks_test.sh` runs five scenarios: both vars unset; pi password set with valid passphrase; passphrase under 8 chars; passphrase over 63 chars; both valid
- **Expected:** unset and out-of-range passphrases abort the play with the documented message; valid values pass
- **Negative cases:** are the point of the test

### TC-U-003: inky-status hardware-free renders

- **What it covers:** `opt/inky-status/inky_status.py` (GH #2) — compiles, and renders previews without hardware in both collection modes
- **Setup:** python3; render steps need PIL and skip cleanly without it
- **Action:** `tests/unit/inky_status_test.sh` — `py_compile`; `--simulate --out` (client mode); `--simulate-ap --out` (AP mode, the bridge's real mode); a 400x300 wHAT-resolution render; all six `--day 0..5` band orderings (the anti-ghosting rotation)
- **Expected:** compile passes and every render exits 0 writing a PNG
- **Negative cases:** a band function raising on None data (e.g. no IP, no stations) surfaces here before it can brick the on-device draw
