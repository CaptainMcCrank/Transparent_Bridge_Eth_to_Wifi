# Diagnostic Playbook

Seeded at adoption. Expanded by downstream troubleshooting agents as failures are resolved.

## General Diagnostic Steps

1. Check `project.manifest.yaml` → `status.health`
2. Review open GitHub issues
3. Check `.troubleshooting/common-failures.yaml` for signature matches (seeded from adoption; see `source:` field on each entry)
4. Search `.AgentLessonsLearned/` for component-specific history (directory does not exist yet; created by the first agent that records a lesson)

## Component-Specific Diagnostics

<!-- Populated by downstream agents (06B, 11). -->
<!-- Pre-existing component-specific sources discovered at adoption (Step 2f): -->

### hostapd / onboard WiFi radio
- Source: GitHub issue #1 ("Wifi not working. Hardware failure condition")
- Notes: hostapd start failure accompanied by brcmfmac SDIO errors indicates radio hardware failure, not misconfiguration. See `common-failures.yaml` entry `hostapd-brcmfmac-sdio-001`.

### Attached-client visibility
- Source: `Readme.md` Build Overview
- Notes: `arp -a | grep wlan0` on the device lists hostnames and IPs of clients attached to the WiFi interface.

## Escalation Procedures

Follow `self_correction` configuration in `project.manifest.yaml` (max 3 attempts, 60 s cooldown, escalate to `needs-human` after 3 failures).
