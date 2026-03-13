# Implementation Plan: Control Plane Dashboard (Issue #3732)

**Related issue:** https://github.com/elastic/observability-robots/issues/3732

---

## Summary

**Goal:** Create an agentic workflow acting as a Control Plane that enables repository users to self-service opt-in/opt-out of each agentic workflow via a GitHub Issue dashboard (Renovate Dependency Dashboard–style UX), with automatic updates of the workflow list and maturity classification.

**In scope:**
- GitHub Issue as UI for per-workflow opt-in/opt-out per repository
- Dashboard-style UX similar to Renovate Dependency Dashboard
- Automatic updates of the available workflow list in each repository's dashboard issue
- Maturity classification (stable, early adoption, experimental)

**Out of scope:**
- Changes to individual workflow implementations (unless required for conditional execution)
- Modifications to `elastic/ai-github-actions` or external workflow sources
- Central cross-repo dashboard (issue explicitly targets per-repo dashboards)

---

## Facts Gathered

### From the Issue

- **Request:** Create an agentic workflow working as a Control Plane for remote management of agent workflows as self-service.
- **Requirements:**
  1. Use a GitHub Issue as UI to opt-in/opt-out each agentic workflow per repository
  2. Renovate Dependency Dashboard–style UX (reference: elastic/cloud#131145)
  3. Automatically update the list of all available agentic workflows in every repository's issue
  4. Classify workflows by maturity: stable, early adoption, experimental
- **Labels:** area:ci, Team:Automation
- **Impact:** High
- **Target:** ASAP

### From Repository Investigation

**Current architecture (`oblt-aw` / control-plane):**

- **Ingress:** `.github/workflows/oblt-aw-ingress.yml` routes events to specialized workflows:
  - `agent-suggestions`, `autodoc`, `automerge` (schedule)
  - `dependency-review` (pull_request from bots)
  - `resource-not-accessible-by-integration-detector` (schedule)
  - `resource-not-accessible-by-integration-triage` (issues opened)
  - `resource-not-accessible-by-integration-fixer` (issues labeled)
- **Distribution:** `distribute-client-workflow.yml` installs `.github/remote-workflow-template/oblt-aw.yml` as `oblt-aw.yml` in all repos listed in `active-repositories.json`.
- **Client template:** `.github/remote-workflow-template/oblt-aw.yml` triggers on `schedule`, `workflow_dispatch`, `issues` (opened, labeled), `pull_request`, `pull_request_review`.
- **No per-workflow opt-in:** All workflows run for all admitted repositories.

**Renovate Dependency Dashboard pattern (from docs):**

- Single issue per repo with dynamic Markdown checkboxes
- Checkboxes trigger actions (e.g., approval, retry)
- GitHub fires `issues` with `edited` when task list items are checked/unchecked
- Collapsible sections, tables for warnings, links to PRs/docs

**Assumptions:**

- Dashboard issue is created and maintained by the control-plane (oblt-aw), not by each repo manually.
- Config derived from the dashboard (checkboxes) must be consumable by the ingress at runtime.
- Default opt-in behavior: workflows are enabled by default for backward compatibility until a repo explicitly opts out.

---

## Creating a Pinnable Dashboard Issue

This section details how to create a dashboard issue that can be pinned at the top of the repository's Issues list.

### GitHub Pinning Behavior

- **Limit:** Up to **3 issues** can be pinned per repository.
- **Placement:** Pinned issues appear **above** the regular issues list.
- **Manual pinning:** Users can pin via the "Pin issue" button in the right sidebar.
- **Programmatic pinning:** Supported via GitHub GraphQL API (`pinIssue` mutation) or `gh issue pin <number> --repo owner/repo`.

### Making the Dashboard Discoverable and Pinnable

**1. Deterministic title and label**

Use a stable, recognizable title and label so the sync workflow can find and update the same issue every time:

| Attribute | Recommended value | Rationale |
|-----------|-------------------|-----------|
| **Title** | `[OBLT AW] Control Plane Dashboard` | Unique, sortable; users can filter by `in:title` |
| **Label** | `oblt-aw/dashboard` | Single canonical label for identification; enables `label:oblt-aw/dashboard` search |

**2. Finding the existing dashboard issue**

Before creating, search for an existing issue:

```graphql
query FindDashboard($query: String!) {
  search(query: $query, type: ISSUE, first: 5) {
    nodes {
      ... on Issue {
        id
        number
        title
        body
      }
    }
  }
}
# query: "repo:owner/repo label:oblt-aw/dashboard is:open"
```

Or via REST: `GET /repos/{owner}/{repo}/issues?labels=oblt-aw/dashboard&state=open`.

**3. Create or update**

- **If no match:** Create via `POST /repos/{owner}/{repo}/issues` with `title`, `body`, `labels: ["oblt-aw/dashboard"]`.
- **If match:** Update via `PATCH /repos/{owner}/{repo}/issues/{number}` with new `body` (and optionally `title` if it changed).

**4. Programmatic pinning**

After creating or updating, pin the issue so it appears at the top:

**GraphQL mutation (requires `issueId` as global node ID):**

```graphql
mutation PinDashboard($input: PinIssueInput!) {
  pinIssue(input: $input) {
    issue { number title }
  }
}
# input: { issueId: "I_kwDO..." }
```

To get the global node ID: `issue.id` from the create/update response, or use `node(id: $id) { ... on Issue { id } }`.

**Alternative: `gh` CLI**

```bash
gh issue pin <number> --repo owner/repo
```

**5. Handling the 3-pin limit**

- If the repo already has 3 pinned issues, `pinIssue` will fail.
- **Options:**
  - **A. Fail gracefully:** Log a warning and skip pinning; the dashboard is still usable, just not pinned.
  - **B. Unpin others:** Use `unpinIssue` on an older issue (risky; may unpin something important).
  - **C. Document:** Recommend in repo docs that maintainers keep a slot for the dashboard.
- **Recommended:** Option A. Document that users can manually pin the dashboard if they want it at the top.

**6. Renovate-style patterns to adopt**

| Pattern | Renovate config | OBLT AW equivalent |
|---------|------------------|---------------------|
| Custom title | `dependencyDashboardTitle` | Fixed: `[OBLT AW] Control Plane Dashboard` |
| Labels | `dependencyDashboardLabels` | `oblt-aw/dashboard` (required); optional: `oblt-aw/attention` when action needed |
| Header | `dependencyDashboardHeader` | Configurable intro in workflow body template |
| Footer | `dependencyDashboardFooter` | Optional: link to docs, last update timestamp |

**7. Sync workflow sequence**

```text
For each repo in active-repositories.json:
  1. Search for open issue with label oblt-aw/dashboard
  2. Build body from workflow-registry.json (maturity, checkboxes, descriptions)
  3. If found: PATCH issue; if not: POST create issue
  4. Call pinIssue mutation (or gh issue pin)
  5. If pin fails (e.g. 3 already pinned): log and continue
```

**8. Token permissions**

- `issues: write` (create, update, add labels)
- `repo` scope for cross-repo access when syncing from control-plane
- GraphQL `pinIssue` requires the same permissions as manual pinning (typically `repo` or `admin:repo_hook`)

---

## Implementation Plan

### Phase 1: Workflow Registry and Metadata

**1.1 Create workflow registry** (`./workflow-registry.json` or `./.github/workflow-registry.json`):

- Add a JSON file listing all available workflows with:
  - `id` (e.g., `dependency-review`, `agent-suggestions`)
  - `name` (human-readable)
  - `description` (short)
  - `maturity` (`stable` | `early-adoption` | `experimental`)
  - `default_enabled` (boolean; for backward compatibility, `true` for existing workflows)
- Populate with current workflows: agent-suggestions, autodoc, automerge, dependency-review, resource-not-accessible-by-integration-detector, resource-not-accessible-by-integration-triage, resource-not-accessible-by-integration-fixer.
- New workflows default to `default_enabled: true` for existing repos.
- **Why:** Single source of truth for dashboard content and maturity; enables automatic list updates.

**1.2 Document maturity criteria** (`./docs/operations/workflow-maturity.md`):

- Define when a workflow is stable vs early-adoption vs experimental.
- **Assignment:** Maturity is set centrally in oblt-aw (`workflow-registry.json`) by maintainers. Future enhancement: derive automatically from metrics (e.g. successful execution ratio, proposed actions taken).
- **Why:** Ensures consistent classification and user trust.

---

### Phase 2: Dashboard Issue Management

**2.1 Create dashboard sync workflow** (`./.github/workflows/sync-control-plane-dashboard.yml`):

- **Triggers:** `push` to `main` (paths: `workflow-registry.json`, `active-repositories.json`, the sync workflow itself), `schedule` (e.g., daily), `workflow_dispatch`.
- **Behavior:**
  - Read `workflow-registry.json` and `active-repositories.json`.
  - For each repository in `active-repositories.json`:
    1. Search for existing open issue with label `oblt-aw/dashboard` (REST or GraphQL search).
    2. Create or update the issue with title `[OBLT AW] Control Plane Dashboard`, label `oblt-aw/dashboard`, and body from registry (header, maturity badges, checkboxes, descriptions).
    3. Pin the issue via GraphQL `pinIssue` mutation (or `gh issue pin`) so it appears at the top of the Issues list. If pinning fails (e.g. repo already has 3 pinned issues), log and continue.
  - Use REST `issues.create`/`issues.update` or a script calling GitHub API.
- **Permissions:** `contents: read`, ephemeral token via `elastic/oblt-actions/github/create-token` with `token-policy-63405ab45244` (same as `distribute-client-workflow`).
- **Why:** Keeps the list of workflows and maturity in sync across all repos; pinning ensures the dashboard is visible at the top of the Issues tab.

**2.2 Define dashboard issue format** (`./docs/operations/control-plane-dashboard-format.md`):

- Markdown structure: intro, workflow table with columns (Workflow | Maturity | Opt-in | Description), instructions for users.
- Checkbox format: `- [ ]` / `- [x]` with workflow id in a parseable pattern (e.g., `<!-- oblt-aw:workflow-id -->`).
- **Why:** Enables reliable parsing when users edit checkboxes.

---

### Phase 3: Config Persistence and Ingress Integration

**3.1 Add dashboard config handler to client and ingress**:

- **Client template** (`.github/remote-workflow-template/oblt-aw.yml`): Add `issues` type `edited` to triggers.
- **Ingress** (`.github/workflows/oblt-aw-ingress.yml`): Add routing for `issues` + `edited` + label `oblt-aw/dashboard` → new job `dashboard-config-sync`.
- **New job `dashboard-config-sync`:**
  - Parse the dashboard issue body for checkbox state per workflow id.
  - Write `.github/oblt-aw-config.json` in the caller repo (e.g., `{"enabled_workflows": ["dependency-review", ...]}`).
  - Use `peter-evans/create-pull-request` or direct commit (with appropriate token).
- **Why:** Checkbox edits must persist to a machine-readable config so the ingress can gate workflow execution.

**3.2 Ingress conditional execution**:

- Add an initial job (e.g., `resolve-config`) that:
  - Checks out the caller repository (or uses API to read `.github/oblt-aw-config.json`).
  - Outputs `enabled_workflows` as a JSON array or comma-separated string.
- Update each specialized job's `if` condition to also require the workflow id in `enabled_workflows` (or absence of config = all enabled for backward compatibility).
- **Why:** Per-workflow opt-in/opt-out requires the ingress to respect repo-level config.

**3.3 Backward compatibility**:

- If `.github/oblt-aw-config.json` does not exist, treat all workflows as enabled.
- **Why:** Existing repos continue to work without any change.

---

### Phase 4: Distribution and Documentation

**4.1 Extend distribute-client-workflow** (`./.github/workflows/distribute-client-workflow.yml`):

- Ensure the dashboard sync workflow is triggered when `workflow-registry.json` or `active-repositories.json` changes (already covered if sync workflow watches those paths).
- Optionally: trigger `sync-control-plane-dashboard` after successful distribution.
- **Why:** New repos get the dashboard issue shortly after client workflow installation.

**4.2 Create dashboard on first install**:

- In `sync-control-plane-dashboard`, create the dashboard issue when a repo is in `active-repositories.json` and has no existing dashboard issue.
- **Why:** New adopters see the dashboard immediately.

**4.3 Update documentation**:

- `docs/architecture/overview.md`: Add Control Plane Dashboard and config flow.
- `docs/workflows/README.md`: Add `sync-control-plane-dashboard` and `dashboard-config-sync` (or equivalent).
- `docs/operations/`: Add `control-plane-dashboard.md` with user instructions.
- `docs/routing/README.md`: Document `issues.edited` + `oblt-aw/dashboard` routing.
- **Why:** Aligns with existing documentation standards.

---

### Phase 5: Validation and Rollout

**5.1 Unit tests**:

- Script or test to parse dashboard issue body and produce `oblt-aw-config.json`.
- Script to read `workflow-registry.json` and validate schema.
- **Why:** Reduces regression risk.

**5.2 Rollout**:

- Deploy to all repositories in `active-repositories.json` (no separate pilot phase).
- Validate checkbox → config → ingress gating across the target set.

---

## Validation

| Step | Verification |
|------|--------------|
| Workflow registry | `jq . workflow-registry.json` succeeds; all current workflows present with maturity |
| Dashboard sync | Run `sync-control-plane-dashboard` manually; verify issue created/updated in a test repo |
| Config handler | Edit dashboard issue checkbox → run workflow → verify `.github/oblt-aw-config.json` updated |
| Ingress gating | Disable a workflow via dashboard → trigger that workflow's event → verify it does not run |
| Backward compat | Repo without `oblt-aw-config.json` → all workflows run as today |

**Commands (when applicable):**

- `python -c "import json; json.load(open('workflow-registry.json'))"`
- `gh issue list --repo <owner>/<repo> --label "oblt-aw/dashboard"`
- `gh run list --workflow sync-control-plane-dashboard.yml`

---

## Resolved Decisions

1. **Maturity assignment:** Maturity is assigned centrally in oblt-aw (`workflow-registry.json`), manually by maintainers. Future enhancement: derive automatically from metrics (e.g. successful execution ratio, proposed actions taken).
2. **Token:** Same token as `distribute-client-workflow`, from `elastic/oblt-actions/github/create-token` with `token-policy-63405ab45244`.
3. **Pilot repositories:** The repositories in `active-repositories.json` (no separate pilot phase).
4. **Default for new workflows:** New workflows default to `enabled` for existing repos.
5. **Renovate reference:** No specific UX elements from elastic/cloud#131145 to replicate.

---

## Execution Order Summary

1. Create `workflow-registry.json` and maturity docs
2. Implement `sync-control-plane-dashboard.yml` and dashboard format spec
3. Add `issues.edited` to client template and `dashboard-config-sync` job to ingress
4. Implement `resolve-config` and conditional `if` in ingress jobs
5. Update distribute workflow and documentation
6. Add tests and rollout to all repos in `active-repositories.json`
