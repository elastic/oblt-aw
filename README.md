# OBLT Agentic Workflows (`oblt-aw`)

This repository is the **central catalog of reusable agentic workflows** for Observability automation.

Its main objective is to provide a **single reusable entry point** for consuming repositories, while keeping each automation capability isolated in specialized reusable workflows.

---

## Why this repository exists

In consumer repositories, wiring multiple automation workflows directly creates drift and duplication:

- each repository must know which reusable workflow to call
- trigger/event wiring can diverge across repositories
- onboarding new workflows requires repetitive updates everywhere

`oblt-aw` solves this by exposing one reusable orchestrator:

- `.github/workflows/oblt-aw.yml`

That orchestrator routes execution to a specific specialized workflow based on GitHub event context.

---

## Core design principles

- **Single entry point** for target repositories.
- **Event-driven routing** in one place.
- **Capability isolation** (detector / triage / fixer are independent reusable workflows).
- **Least surprise for consumers**: caller workflows do not need to understand internal implementation details.
- **Future extensibility**: new capabilities can be added behind the same entrypoint contract.

---

## Current capabilities

This repository currently manages the **Resource not accessible by integration** automation chain:

1. **Detector**
   - scans recent workflow runs
   - identifies occurrences of `Resource not accessible by integration`
   - creates structured issue(s)

2. **Triage**
   - reacts to new issues
   - classifies whether issue belongs to this problem space
   - produces a resolution plan and labels for downstream automation

3. **Fixer**
   - reacts when issue is ready to be fixed
   - implements the triage plan
   - opens/updates PR with required changes and review assignment

---

## Repository organization

```text
.
├── .github/
│   ├── workflows/
│   │   ├── oblt-aw.yml
│   │   ├── resource-not-accessible-by-integration-detector.yml
│   │   ├── resource-not-accessible-by-integration-triage.yml
│   │   └── resource-not-accessible-by-integration-fixer.yml
│   └── workflow-routing/
│       └── resource-not-accessible-by-integration/
│           └── README.md
├── catalog-info.yaml
└── renovate.json
```

### Folder responsibilities

- `.github/workflows/`
  - executable reusable workflows
  - includes both orchestrator and capability workflows

- `.github/workflow-routing/`
  - domain-level routing and operational notes
  - intended for documentation and conventions by workflow family

- `catalog-info.yaml`
  - service/component metadata for cataloging

- `renovate.json`
  - dependency/automation maintenance policies

---

## Entrypoint routing behavior

`oblt-aw.yml` is invoked via `workflow_call` and routes internally:

- `schedule` or `workflow_dispatch` → detector workflow
- `issues` + `opened` → triage workflow
- `issues` + `labeled` + labels (`ai:fix-ready` and `triage/resource-not-accessible-by-integration`) → fixer workflow
- unsupported event/action combinations fail fast in `unsupported-trigger`

This design ensures consumers integrate once and keep trigger-based behavior centralized.

---

## Agentic workflow structure (diagram)

```mermaid
flowchart TD
  A[Target Repository Workflow] --> B[Reusable Entrypoint<br/>oblt-aw.yml]

  B -->|schedule / workflow_dispatch| C[Detector Reusable Workflow]
  B -->|issues.opened| D[Triage Reusable Workflow]
  B -->|issues.labeled + required labels| E[Fixer Reusable Workflow]
  B -->|unsupported trigger| X[Fail Fast Job]

  C --> C1[Analyze recent workflow runs]
  C1 --> C2[Create issue with findings]

  D --> D1[Classify issue relevance]
  D1 --> D2[Generate resolution plan]
  D2 --> D3[Apply labels: triage/* and ai:fix-ready]

  E --> E1[Read triage plan]
  E1 --> E2[Implement fix in code/workflows]
  E2 --> E3[Create Draft PR]
  E3 --> E4[Open for review when validated]

  C2 -.issues.opened.-> D
  D3 -.issues.labeled.-> E
```

---

## Consumption model for target repositories

Target repositories should reference only:

- `elastic/oblt-aw/.github/workflows/oblt-aw.yml@main`

This keeps consumers decoupled from specialized workflow file names and internal orchestration logic.

---

## Operational notes

- The specialized workflows (`detector`, `triage`, `fixer`) define optional `target-repositories` filters for direct invocation scenarios.
- The main entrypoint currently routes by trigger/action and does not expose those filter inputs.
- Permissions are explicitly declared per workflow to align with least-privilege operation.

---

## How to extend this repository

When adding a new agentic capability:

1. Create a new reusable workflow under `.github/workflows/` for that capability.
2. Add routing condition(s) in `oblt-aw.yml` to dispatch to it.
3. Add/update documentation under `.github/workflow-routing/<domain>/`.
4. Keep consumer repositories unchanged whenever possible (single-entrypoint contract).

This approach preserves consistency across all target repositories while allowing internal evolution.
