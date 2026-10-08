---
navigation_title: Catalog by outcome
description: OBLT Agentic Workflows grouped by developer outcome — what each does, maturity, and how to enable.
applies_to: {}
---

# Agentic workflow catalog by outcome

Consumer agentic workflows registered for Observability (`config/obs/workflow-registry.json`) and Docs (`config/docs/workflow-registry.json`). Each row links to enablement and the framework doc. For upstream agent encyclopedias, use [AI GitHub Actions](https://elastic.github.io/ai-github-actions/).

How to turn a row on or off: [Enable or disable an agentic workflow](../user-guide/enable-a-new-workflow.md). Maturity meanings: [Workflow maturity](../operations/workflow-maturity.md).

## Issues

| Agentic workflow | Maturity | What it does | Docs |
|----------|----------|--------------|------|
| Issue Triage | early-adoption | Triages newly opened issues | [obs-aw-issue-triage](obs-aw-issue-triage.md) |
| Mention in Issue | early-adoption | `/ai` assistant on issues (questions, debug, PRs) | [obs-aw-mention-in-issue](obs-aw-mention-in-issue.md) |
| Duplicate Issue Detector | experimental | Flags likely duplicate issues | [obs-aw-duplicate-issue-detector](obs-aw-duplicate-issue-detector.md) |
| Issue Fixer | experimental | Generic `/ai implement` fixes (non-security paths) | [obs-aw-issue-fixer](obs-aw-issue-fixer.md) |
| Agent Suggestions | experimental | Suggests agentic workflows for the repository | [obs-aw-agent-suggestions](obs-aw-agent-suggestions.md) |

## Pull requests

| Agentic workflow | Maturity | What it does | Docs |
|----------|----------|--------------|------|
| Automated Documentation | stable | Finds doc gaps and opens issues/PRs | [obs-aw-autodoc](obs-aw-autodoc.md) |
| Dependency Review | stable | Labels bot dependency PRs when merge-ready | [obs-aw-dependency-review](obs-aw-dependency-review.md) |
| PR Actions Detective | early-adoption | Diagnoses failed GitHub Actions runs on a PR | [obs-aw-pr-actions-detective](obs-aw-pr-actions-detective.md) |
| PR Buildkite Detective | stable | Diagnoses Buildkite failures on a PR | [obs-aw-estc-pr-buildkite-detective](obs-aw-estc-pr-buildkite-detective.md) |
| Resource Not Accessible by Integration | early-adoption | Detects, triages, and fixes that Actions error | [obs-aw-resource-not-accessible-by-integration-detector](obs-aw-resource-not-accessible-by-integration-detector.md) |

## Security

| Agentic workflow | Maturity | What it does | Docs |
|----------|----------|--------------|------|
| Security | early-adoption | Static checks on workflows, scripts, and manifests; opens issues | [obs-aw-security-detector](obs-aw-security-detector.md) |

Related: [Security triage](obs-aw-security-triage.md), [Security fixer](obs-aw-security-fixer.md), [Security issue superseder](obs-aw-security-issue-superseder.md), [Security scanning ruleset](security-scanning-ruleset.md), [Security routing](../routing/security-routing.md).

## Dependency updates / Automerge

| Agentic workflow | Maturity | What it does | Docs |
|----------|----------|--------------|------|
| Automerge | stable | Arms and squash-merges allowed bot PRs when checks are green | [Choose Automerge services](../user-guide/automerge-services.md), [obs-aw-automerge](obs-aw-automerge.md) |

## Docs organization

| Agentic workflow | Maturity | What it does | Docs |
|----------|----------|--------------|------|
| Docs Issue AI Menu | experimental | Issue AI menu for the Docs org | [docs-aw-ai-menu](docs-aw-ai-menu.md) |
| Docs PR AI Menu | experimental | PR AI menu for the Docs org | [docs-aw-pr-ai-menu](docs-aw-pr-ai-menu.md) |

## Filename index

Maintainer-oriented list of every workflow source file: [Workflow catalog (filename index)](index.md).
