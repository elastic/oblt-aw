# Workflow Maturity Criteria

This document defines the maturity levels used to classify agentic workflows in the Control Plane Dashboard. Maturity is assigned centrally in [workflow-registry.json](../../config/workflow-registry.json) by maintainers.

## Maturity Levels

### Stable

**Criteria:**

- Production-ready and widely used across repositories
- Well-tested behavior with predictable outcomes
- Documentation and support are established
- Suitable for general adoption without special considerations

**Use when:** The workflow has a proven track record and is recommended for all applicable repositories.

---

### Early Adoption

**Criteria:**

- Available for testing and use
- May have rough edges or limitations
- Feedback from adopters is welcome to improve the workflow
- Generally functional but not yet broadly validated

**Use when:** The workflow is ready for teams willing to try it and provide feedback, with the understanding that behavior may evolve.

---

### Experimental

**Criteria:**

- In active development
- Behavior and interface may change without notice
- Intended for internal testing or limited pilot use
- Not recommended for production-critical workflows

**Use when:** The workflow is being developed or validated; adopters should expect changes and potential instability.

---

## Assignment

Maturity is set in [workflow-registry.json](../../config/workflow-registry.json) (`config/`). Each workflow entry includes:

- `maturity`: one of `stable`, `early-adoption`, or `experimental`
- `default_enabled`: default checkbox state used by dashboard sync when a workflow is not yet present in an existing dashboard issue body

`default_enabled` does not override user-edited dashboard checkbox state. It defines the initial state for newly introduced workflow IDs until users change them in the dashboard issue.

Future enhancement: maturity could be derived automatically from metrics (e.g., successful execution ratio, proposed actions taken).
