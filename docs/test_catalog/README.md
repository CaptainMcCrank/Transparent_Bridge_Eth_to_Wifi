# Project Test Catalog

This directory is the **project-specific specification** for what gets tested. It is kept in the project repository, not in the prompt library.

The library prompts (`Standards/Agents/04_Test_Agent.md` and `Standards/Agents/04_WebDev_Test_Agent.md`) contain only the *category definitions* (what a unit test is, what an e2e test is, what frameworks to use). The *concrete test cases* — the user journeys, domain rules, edge cases that matter for this particular project — live here.

## Why this split exists

If concrete test cases live in the prompt library, the library accumulates one project's domain knowledge (music-theory engines, hostapd configs, GPIO timings) and becomes useless for the next project. Splitting them keeps the library generic and the project specifications durable.

## How agents use this directory

The Test Agent reads `project_layout.test_catalog` from `project.manifest.yaml` (defaults to `docs/test_catalog/`) and processes every file in it:

1. **Greenfield project**: the directory is seeded with the templates from `Standards/Templates/test_catalog/` plus placeholders. The Test Agent generates an initial draft of each category file from the PRD, working solution, and design-review feedback, then asks the human to refine it.
2. **Established project**: the catalog files are already populated. The Test Agent treats them as the spec — it implements the test cases described in each file using the framework chosen in `docs/techstack_decision.md`.

Other agents read this directory too:
- **PRD agent (01)** — writes user journeys discovered in interviews into `user_journeys.md`.
- **Experiment agent (03 / 03_WebDev)** — writes domain risks discovered during prototyping into `domain_risks.md`.
- **Design Review agent (03B)** — writes design-driven correctness rules and cross-device requirements into the matching files after a review session.
- **Feature Development (09) / Feature Evolution (10)** — append new test cases to the relevant category file when scope changes; never delete existing entries without an ADR.

## File index

| File | Applicable to | Purpose |
|---|---|---|
| `user_journeys.md` | both | Critical paths a user takes through the system. Source for E2E and integration tests. |
| `domain_risks.md` | both | Domain-specific failure modes. "What would silently break the user's workflow?" |
| `domain_correctness_matrix.md` | both, optional | Project-specific correctness rules (e.g., music theory, financial math, taxonomy). Drives unit-test coverage requirements. |
| `unit_tests.md` | both | Per-function correctness. Concrete entries for the deepest-leverage logic. |
| `component_tests.md` | webapp | Frontend component rendering and interaction tests. |
| `api_tests.md` | both (if HTTP surface) | Endpoint contract tests. Schema, status codes, auth, error paths. |
| `smoke_tests.md` | both | Quick post-deploy sanity checks. |
| `integration_tests.md` | both | Tests that exercise multiple services together. |
| `e2e_tests.md` | both | Full user journeys against a deployed environment. |
| `performance_tests.md` | both | Latency / throughput / resource-budget checks. |
| `security_tests.md` | both | Auth bypass, input validation, secret exposure. |
| `chaos_tests.md` | both | Failure injection — what survives a partial outage? |
| `cross_device_tests.md` | webapp (or multi-target IoT) | Browser × viewport matrix; or Pi-model matrix. |
| `health_tests.md` | iot primary; webapp optional | Runtime monitoring of a deployed system. |

A project does not need every file. Delete or leave empty the categories that don't apply. The Test Agent skips files that don't exist or contain only the template placeholder.

## Entry shape

Every category file holds a list of test-case entries. The canonical shape:

```markdown
### TC-XXX: <Short title>

- **What it covers:** <user journey ID / FR ID / domain rule referenced>
- **Setup:** <fixtures, services, data needed>
- **Action:** <what the test does>
- **Expected:** <observable outcome>
- **Negative cases:** <edge cases that should fail or be rejected>
```

The Test Agent translates each TC entry into one or more test files in `tests/<category>/`, named after the TC ID where practical.

## Editing rules

- Project owners and humans **may** edit any file here directly.
- Agents **may** add entries; they **may not** delete or substantively rewrite existing entries without an ADR.
- TC IDs are stable. Once `TC-014` exists, do not renumber it; if it's deprecated, mark it `**Status:** deprecated` and explain why.
- Domain content (chord progressions, GPIO pin maps, financial rules) belongs here. Framework choice and test-runner config belong in `docs/techstack_decision.md` and the agent prompt — not here.
