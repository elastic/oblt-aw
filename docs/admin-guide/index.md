---
navigation_title: Admin guide
description: Maintain the oblt-aw framework — add workflows, change maturity, configure secrets, and use ephemeral tokens.
applies_to: {}
---

# Admin guide

Procedures for maintainers who change `elastic/oblt-aw` or related agentic assets. Repo owners who only enable existing workflows should use the [User guide](../user-guide/index.md).

## Maintain the framework

| Goal | Guide |
|------|--------|
| Ship a new routed workflow in the framework | [Add a new agentic workflow](add-a-new-agentic-workflow.md) |
| Change maturity or Control Plane dashboard sync behavior | [Change maturity level](change-maturity-level.md) |
| Decide if a repository secret is required vs ephemeral tokens | [Configure a GitHub secret](configure-a-github-secret.md) |
| Use ephemeral tokens and token policies | [Use GitHub ephemeral tokens](use-gh-ephemeral-tokens.md) |
| Contribute to `elastic/oblt-aw` (local setup, pre-commit) | [Contributing](../development/contributing.md) |

## Related

- Long-form adoption checklist: [Adopting a new remote agentic workflow](../onboarding/adopting-agentic-workflows.md)
- Technical registration contract: [Registering resources](../onboarding/registering-a-repository.md)
- [Knowledge base](../knowledge-base/index.md) — architecture and reference
