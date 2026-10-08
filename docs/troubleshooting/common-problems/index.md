---
navigation_title: Common problems
description: Recurring oblt-aw failures and how we solve them — short answers with links to full guides.
applies_to: {}
---

# Common problems

Short answers for problems the team has already diagnosed. Each page links to the full procedure in Troubleshooting, the User guide, or the Admin guide.

| Problem | Start here |
|---------|------------|
| `create-token` / OIDC failures on client runs | [create-token or OIDC failures](create-token-or-oidc-failures.md) |
| No distribute PR or no Control Plane dashboard after registration | [Missing client template or Control Plane dashboard](missing-client-template-or-dashboard.md) |
| Onboard agent never comments or opens PRs | [Onboard agent no comment or PRs](onboard-agent-no-comment-or-prs.md) |
| Registration merged before catalog TokenPolicy was active | [Registration before catalog TokenPolicy](registration-before-catalog-token-policy.md) |
| Unsure whether a long-lived repository secret is required | [Configure a GitHub secret](../configure-a-github-secret.md) |
| Workflow jobs skipped or agents never run | [Workflows skipped or not running](workflows-skipped-or-not-running.md) |

## How to add an entry

1. Confirm the problem and fix are documented in an existing guide or runbook (do not invent).
2. Add a short page under this folder: symptom → cause → fix → links.
3. List it in the table above and in `docs/docset.yml`.
