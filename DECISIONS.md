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
