---
navigation_title: Frequent Asked Problems
description: Recurring oblt-aw failures and how we solve them — short answers with links to full guides.
applies_to: {}
---

# Frequent Asked Problems

Short answers for problems the team has already diagnosed. Each page links to the full procedure in Troubleshooting, the User guide, or the Admin guide.

| Problem | Start here |
|---------|------------|
| Workflow jobs skipped or agents never run | [Workflows skipped or not running](workflows-skipped-or-not-running.md) |
| Registration merged before catalog TokenPolicy was active | [Registration before catalog TokenPolicy](registration-before-catalog-token-policy.md) |
| `create-token` / OIDC failures on client runs | [create-token or OIDC failures](create-token-or-oidc-failures.md) |
| No distribute PR or no Control Plane Dashboard after registration | [Missing client template or dashboard](missing-client-template-or-dashboard.md) |
| Unsure whether a long-lived repository secret is required | [Configure a GitHub secret](../../troubleshooting/configure-a-github-secret.md) |

## How to add an entry

1. Confirm the problem and fix are documented in an existing guide or runbook (do not invent).
2. Add a short page under this folder: symptom → cause → fix → links.
3. List it in the table above and in `docs/docset.yml`.
