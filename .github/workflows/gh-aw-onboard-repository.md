---
inlined-imports: true
name: "Onboard Repository"
description: "Read an onboard-repository issue and open the required registration PRs"
imports:
  - gh-aw-fragments/elastic-tools.md
  - gh-aw-fragments/ephemeral-github-token.md
  - gh-aw-fragments/formatting.md
  - gh-aw-fragments/messages-footer.md
  - gh-aw-fragments/obs-defaults.md
  - gh-aw-fragments/rigor.md
  - gh-aw-fragments/runtime-setup.md
engine:
  id: copilot
  # Required on gh-aw >= v0.91.x: BYOK Copilot disables native web-fetch unless SDK mode is on.
  copilot-sdk: true
on:
  stale-check: false
  # labeled: issue-form applies the onboard label after create (Phase 1).
  # edited: Phase 2 checkbox (human or catalog-info merge bridge); agent is idempotent.
  # No workflow_dispatch: this agent requires the triggering issue for parse/comment.
  issues:
    types: [labeled, edited]
    names: [oblt-aw/onboard/repository]
  # catalog-info Phase 2 bridge: issue edit alone is not enough for App actors
  # (collaborator check). Bridge checks Phase 2 then repository_dispatch.
  repository_dispatch:
    types: [oblt-aw-onboard-phase2]
  # Immediate 👀 on the issue so the requester sees the agent picked it up.
  reaction: eyes
  roles: [admin, maintainer, write]
  bots:
    - "elastic-vault-github-plugin-prod[bot]"
    - "github-actions[bot]"
concurrency:
  # issue events use github.event.issue.number; bridge dispatch uses client_payload.
  group: ${{ github.workflow }}-onboard-repository-${{ github.event.issue.number || github.event.client_payload.issue_number }}
  # false: host Phase 2 abort uncheck emits edited; do not cancel the abort run.
  cancel-in-progress: false
# Policy id lives in config/onboard-repository.json (same pattern as config/e2e.json).
# Resolved by gh-aw-fragments/ephemeral-github-token.md before create-token.
env:
  WORKFLOW_TOKEN_POLICY_CONFIG: config/onboard-repository.json
permissions:
  copilot-requests: write
  actions: read
  contents: read
  issues: read
  pull-requests: read
  id-token: write
checkout:
  - fetch-depth: 0
  - repository: elastic/catalog-info
    path: repos/catalog-info
    github-token: ${{ steps.create-token.outputs.token || secrets.GH_AW_GITHUB_TOKEN || secrets.GITHUB_TOKEN }}
  - repository: elastic/observability-github-settings
    path: repos/observability-github-settings
    github-token: ${{ steps.create-token.outputs.token || secrets.GH_AW_GITHUB_TOKEN || secrets.GITHUB_TOKEN }}
  - repository: elastic/observability-github-secrets
    path: repos/observability-github-secrets
    github-token: ${{ steps.create-token.outputs.token || secrets.GH_AW_GITHUB_TOKEN || secrets.GITHUB_TOKEN }}
steps:
  - name: Require onboard label for edited events
    if: github.event.action == 'edited'
    env:
      ISSUE_LABELS: ${{ join(github.event.issue.labels.*.name, ',') }}
    run: |
      set -euo pipefail
      # Defense in depth: gh-aw names-filter is labeled-only; Makefile also patches job if.
      if [[ ",${ISSUE_LABELS}," != *",oblt-aw/onboard/repository,"* ]]; then
        echo "::error::edited event without label oblt-aw/onboard/repository; refusing to run"
        exit 1
      fi
  - name: Parse onboard issue phase and repository
    id: onboard-phase
    env:
      GH_TOKEN: ${{ steps.create-token.outputs.token || secrets.GH_AW_GITHUB_TOKEN || secrets.GITHUB_TOKEN }}
      ISSUE_NUMBER: ${{ github.event.issue.number || github.event.client_payload.issue_number }}
    run: |
      set -euo pipefail
      if [[ -z "${ISSUE_NUMBER}" ]]; then
        echo "::error::No issue number on event (issue or client_payload.issue_number required)"
        exit 1
      fi
      # CRLF-safe field parse (blank lines after ### headings must not yield empty repo).
      body="$(gh api "repos/${GITHUB_REPOSITORY}/issues/${ISSUE_NUMBER}" --jq '.body // ""')"
      eval "$(printf '%s\n' "$body" | python3 scripts/onboard_parse_issue_fields.py)"
      repo="${repository:-}"
      org_key="${org_key:-}"
      phase="${phase:-1}"
      phase2="${phase2_checked:-0}"
      if [[ -z "$repo" ]]; then
        echo "::warning::Could not parse elastic/<repo> from issue body"
      fi
      if [[ -z "$org_key" ]]; then
        echo "::warning::Could not parse Organization key (docs|obs|security) from issue body"
      fi
      # Platform repos always; append this issue's validated consumer only (never elastic/*).
      allowed_repos="elastic/catalog-info,elastic/oblt-aw,elastic/observability-github-secrets,elastic/observability-github-settings"
      if [[ -n "$repo" ]]; then
        allowed_repos="${allowed_repos},${repo}"
      fi
      # Exact private: tags for write-sink.accept (same repos; no wildcard).
      allowed_repos_json="["
      allowed_sinks_json="["
      first=1
      IFS=',' read -ra _allowed_repos <<< "${allowed_repos}"
      for r in "${_allowed_repos[@]}"; do
        if [[ "${first}" -eq 1 ]]; then
          first=0
        else
          allowed_repos_json+=","
          allowed_sinks_json+=","
        fi
        allowed_repos_json+="\"${r}\""
        allowed_sinks_json+="\"private:${r}\""
      done
      allowed_repos_json+="]"
      allowed_sinks_json+="]"
      {
        echo "repository=${repo}"
        echo "org_key=${org_key}"
        echo "phase=${phase}"
        echo "phase2_checked=${phase2}"
        echo "allowed_repos=${allowed_repos}"
        echo "allowed_repos_json=${allowed_repos_json}"
        echo "allowed_sinks_json=${allowed_sinks_json}"
      } >> "$GITHUB_OUTPUT"
      echo "Parsed repository='${repo}' org_key='${org_key}' phase=${phase} phase2_checked=${phase2} allowed_repos=${allowed_repos}"
  # Host owns Phase 2 abort uncheck (fresh issue body) so the agent never queues a
  # whole-body update-issue that can race with maintainer edits in safe_outputs.
  - name: Enforce Phase 2 catalog-merge gate
    id: phase2-gate
    if: >-
      steps.onboard-phase.outputs.phase2_checked == '1' &&
      steps.onboard-phase.outputs.repository != '' &&
      steps.onboard-phase.outputs.org_key != ''
    env:
      GH_TOKEN: ${{ steps.create-token.outputs.token || secrets.GH_AW_GITHUB_TOKEN || secrets.GITHUB_TOKEN }}
      ISSUE_NUMBER: ${{ github.event.issue.number || github.event.client_payload.issue_number }}
      CONSUMER_REPO: ${{ steps.onboard-phase.outputs.repository }}
      ORG_KEY: ${{ steps.onboard-phase.outputs.org_key }}
      CATALOG_ROOT: repos/catalog-info
    run: |
      set -euo pipefail
      # Trusted host writes must hit api.github.com directly. After Start DIFC Proxy,
      # GITHUB_API_URL points at localhost and REST writes return github_api_write_denied.
      gh_host_write() {
        env -u HTTPS_PROXY -u HTTP_PROXY -u ALL_PROXY \
          -u https_proxy -u http_proxy -u all_proxy \
          GITHUB_API_URL="https://api.github.com" \
          GITHUB_GRAPHQL_URL="https://api.github.com/graphql" \
          GH_HOST="github.com" \
          "$@"
      }
      ready=0
      reason=""
      open_pr_url=""
      # Full Phase 1: onboard + sync + distribute + settings selectors (not onboard alone).
      if python3 scripts/onboard_phase1_catalog_ready.py \
        --catalog-root "${CATALOG_ROOT}" \
        --org-key "${ORG_KEY}" \
        --repository "${CONSUMER_REPO}"; then
        ready=1
      else
        reason="Phase 1 catalog incomplete for ${CONSUMER_REPO} (org-key=${ORG_KEY}) on catalog-info default branch"
      fi
      if [[ "${ready}" -eq 0 ]]; then
        printf 'aborted\n' > .onboard-phase2-host-aborted
        open_pr_url="$(gh pr list --repo elastic/catalog-info --state open --limit 20 \
          --json number,title,url 2>/dev/null \
          | jq -r --arg repo "${CONSUMER_REPO}" \
            '[.[] | select(.title | startswith("[oblt-aw][onboard]")) | select(.title | contains($repo))] | .[0].url // empty' \
          || true)"
        body="$(gh api "repos/${GITHUB_REPOSITORY}/issues/${ISSUE_NUMBER}" --jq '.body // ""')"
        if printf '%s\n' "${body}" | grep -Eq -- '^[[:space:]]*-[[:space:]]*\[[xX]\][[:space:]]*\*\*Phase 2'; then
          updated="$(printf '%s\n' "${body}" | awk '
            {
              line=$0
              if (line ~ /^[[:space:]]*-[[:space:]]*\[[xX]\][[:space:]]*\*\*Phase 2/) {
                sub(/\[[xX]\]/, "[ ]", line)
              }
              print line
            }
          ')"
          jq -n --arg body "${updated}" '{body:$body}' \
            | gh_host_write gh api "repos/${GITHUB_REPOSITORY}/issues/${ISSUE_NUMBER}" -X PATCH --input -
          comment="Phase 2 was aborted on the host: ${reason}."
          if [[ -n "${open_pr_url}" ]]; then
            comment+=" Open catalog PR: ${open_pr_url}."
          fi
          comment+=" Merge the Phase 1 catalog-info PR (onboard + org-scoped sync/distribute/settings TokenPolicy selectors), wait for it to be active, then check Phase 2 again."
          jq -n --arg body "${comment}" '{body:$body}' \
            | gh_host_write gh api "repos/${GITHUB_REPOSITORY}/issues/${ISSUE_NUMBER}/comments" -X POST --input -
        else
          echo "Phase 2 already unchecked; skipping issue rewrite"
        fi
        echo "aborted=true" >> "${GITHUB_OUTPUT}"
        echo "::notice::Phase 2 aborted on host (${reason})"
      else
        rm -f .onboard-phase2-host-aborted
        echo "aborted=false" >> "${GITHUB_OUTPUT}"
        echo "Phase 2 gate passed for ${CONSUMER_REPO} (org-key=${ORG_KEY})"
      fi
  # Do not use actions/checkout here: it suppresses gh-aw's default workflow-repo checkout.
  # Authenticated host clone keeps persist-credentials out of the agent sandbox.
  - name: Checkout consumer repository for Phase 2
    id: checkout-consumer
    if: >-
      steps.onboard-phase.outputs.phase == '2'
      && steps.onboard-phase.outputs.repository != ''
      && steps.phase2-gate.outputs.aborted != 'true'
    continue-on-error: true
    env:
      CONSUMER_REPO: ${{ steps.onboard-phase.outputs.repository }}
      GH_TOKEN: ${{ steps.create-token.outputs.token || secrets.GH_AW_GITHUB_TOKEN || secrets.GITHUB_TOKEN }}
    run: |
      set -euo pipefail
      rm -rf repos/consumer
      mkdir -p repos
      # Transient Authorization header only (never embed the token in the remote URL).
      # On any failure, remove a partial checkout so the agent never sees credentials.
      cleanup() {
        local ec=$?
        if [[ "${ec}" -ne 0 && -e repos/consumer ]]; then
          rm -rf repos/consumer
        fi
      }
      trap cleanup EXIT
      auth_header="AUTHORIZATION: basic $(printf 'x-access-token:%s' "${GH_TOKEN}" | base64 | tr -d '\n')"
      git -c "http.https://github.com/.extraheader=${auth_header}" \
        clone --depth 1 "https://github.com/${CONSUMER_REPO}.git" repos/consumer
      # Defense in depth: ensure origin has no embedded credentials.
      git -C repos/consumer remote set-url origin "https://github.com/${CONSUMER_REPO}.git"
      git -C repos/consumer config --unset-all "http.https://github.com/.extraheader" 2>/dev/null || true
      echo "Checked out ${CONSUMER_REPO} into repos/consumer (no credentials in remote URL)"
tools:
  github:
    # Prefer OIDC create-token output, then MCP/secret fallbacks (gh-aw >= v0.89.21).
    github-token: ${{ steps.create-token.outputs.token || secrets.GH_AW_GITHUB_MCP_SERVER_TOKEN || secrets.GH_AW_GITHUB_TOKEN || secrets.GITHUB_TOKEN }}
    toolsets: [repos, issues, pull_requests, search, actions]
    # Temporary override of obs-defaults `approved`: DIFC tags human-authored
    # onboard issues as `none:public`, so issue_read under min-integrity: approved
    # filters the body the agent must parse. Same workaround as
    # gh-aw-create-pr-from-issue. Remove once DIFC integrity tags allow approved
    # reads for write-gated issue authors.
    min-integrity: none
    # Compile-time floor: platform only (DIFC starts before parse). MCP gateway is
    # patched at runtime to platform + this issue's consumer (never elastic/*).
    allowed-repos:
      - "elastic/catalog-info"
      - "elastic/oblt-aw"
      - "elastic/observability-github-secrets"
      - "elastic/observability-github-settings"
  bash: true
  web-fetch:
network:
  allowed:
    - github
    - local
    - "docs.elastic.dev"
safe-outputs:
  activation-comments: false
  # Secrets only: conclusion consumes this expression and cannot mint create-token (gh-aw >= v1.3.x).
  # safe_outputs still prefers the minted token via wire_ephemeral_token.py after compile.
  github-token: ${{ secrets.GH_AW_GITHUB_TOKEN || secrets.GITHUB_TOKEN }}
  add-comment:
    max: 2
    issues: true
    pull-requests: false
    discussions: false
    # triggering for issue events; "*" so repository_dispatch can pass item_number.
    target: "*"
  create-pull-request:
    draft: false
    # Phase 1: catalog (+ optional allowlist gap-fill).
    # Phase 2: registration, settings, secrets, CODEOWNERS, Renovate (+ optional catalog gap-fill).
    max: 7
    auto-close-issue: false
    title-prefix: "[oblt-aw][onboard] "
    # Platform repos + this issue's consumer only (from parse step); not elastic/*.
    allowed-repos: ${{ steps.onboard-phase.outputs.allowed_repos }}
strict: false
timeout-minutes: 90
---

# Onboard a consumer repository

You run **only** in `elastic/oblt-aw` when an issue labeled `oblt-aw/onboard/repository` is **labeled** or **edited**, or on `repository_dispatch` type `oblt-aw-onboard-phase2` (catalog-info merge bridge after Phase 2 is checked).
You are **not** a consumer catalog workflow: do not touch `workflow-registry.json`, client templates, or Control Plane Dashboard checkbox definitions.

## Two phases (mandatory)

The issue body has phase trigger checkboxes (see the issue form). Parse them from the issue body:

| Checkbox text (contains) | Checked means |
|--------------------------|---------------|
| `Phase 1 — Catalog` | Run **Phase 1** |
| `Phase 2 — Remaining PRs` | Run **Phase 2** |

**Phase selection rules:**

1. If **Phase 2** is checked → run **Phase 2** only (subject to the catalog-merge gate below).
2. Else if the event is `labeled`, or **Phase 1** is checked → run **Phase 1**.
3. Else (for example `edited` with Phase 2 unchecked and Phase 1 already done) → call `noop` and stop. Do **not** open PRs.

Do **not** treat Control Plane dashboard checkboxes as phase triggers.

## Inputs (from the issue)

Read the triggering issue via GitHub MCP using the **issue-number** from `<github-context>` (the prompt does not embed the issue body). From that issue body, extract exactly:

1. **Repository** — must match `elastic/<repo>` (slug under the `elastic` org).
2. **Organization key** — must be an existing directory under `config/` in this repository (today: `docs`, `obs`, or `security`).
3. **Phase checkboxes** — as above.

If repository or org-key is missing/invalid, or the repository is already listed in `config/<org-key>/active-repositories.json` when Phase 1 would register it, call `add-comment` with a clear explanation and stop (use `noop` if no further action is possible).

## Phase 2 catalog-merge gate (fail closed)

The **host** step `Enforce Phase 2 catalog-merge gate` already checks that `repos/catalog-info` lists this `elastic/<repo>` on **all** Phase 1 TokenPolicy allowlists for the mapped org (onboard + sync + distribute + settings; see step **2e**). When that fails, the host unchecks Phase 2 on the **latest** issue body and comments via direct GitHub API (outside the DIFC write proxy) — do **not** call any issue-body rewrite tool (avoids racing maintainer edits through delayed safe-outputs).

Before any Phase 2 PR work:

1. If `.onboard-phase2-host-aborted` exists, or a re-fetch shows Phase 2 unchecked, call `noop` and stop (host already commented when it unchecked).
2. Confirm the host gate passed (full Phase 1 selectors present) and `repos/consumer` exists when CODEOWNERS/Renovate work is needed.
3. If Phase 2 is still checked but the selector is missing or `repos/consumer` is absent (checkout soft-failed), call `add-comment` explaining the block and stop — do **not** attempt an agent-side `git clone` and do **not** rewrite the issue body.
4. Prefer the host checkout at `repos/consumer` (authenticated host step; credentials never embedded in the remote URL).

## Retry safety (before opening PRs)

Before calling `create-pull-request`, search for **existing open** pull requests whose titles start with `[oblt-aw][onboard]` and that target the same `elastic/<repo>` (in any of the allowlisted repos). Prefer GitHub search / `gh pr list` filtered by that title prefix.

Map each matching open PR to one inventory concern by repository (and title):

| Concern | Allowlisted repo | Typical title contains | Phase |
|---------|------------------|------------------------|-------|
| catalog | `elastic/catalog-info` | `Add token policy` (consumer TokenPolicy + mapped org-scoped sync/distribute + settings selectors + **onboard agent TokenPolicy selector** + Phase 2 bridge platform files when missing) | 1 |
| catalog-settings-selector | `elastic/catalog-info` | `observability-github-settings token policy` / settings selector / allowlist | 1 (gap-fill) |
| registration | `elastic/oblt-aw` | `Register` / `active repositories` | 2 |
| settings | `elastic/observability-github-settings` | `branch protection` | 2 |
| secrets | `elastic/observability-github-secrets` | `secret` / secrets provision | 2 |
| codeowners | `elastic/<repo>` | `CODEOWNERS` / trigger owners | 2 |
| renovate | `elastic/<repo>` | `Renovate` / `packageRules` / trigger ignore | 2 |

Then:

1. **Never duplicate** — do not open a second PR for a concern that already has an open matching onboard PR. Do not invent `pulls?q=` search links.
2. **Phase 1 scope** — open or gap-fill **catalog** concerns only. Do **not** open registration, settings, secrets, CODEOWNERS, or Renovate in Phase 1.
3. **Phase 2 scope** — gap-fill registration, settings, secrets, CODEOWNERS, Renovate. Open a catalog follow-up (`aw_catalog_settings`) only when step **2e** / onboard-selector coverage is still missing after a merged Phase 1 PR.
4. **Stop only when the active phase is complete** — comment with **exact PR URLs** and what the human should do next (merge catalog, then check Phase 2; or merge remaining PRs in order).
5. Re-applying the `oblt-aw/onboard/repository` label retries the phase implied by the checkboxes; treat prior open onboard PRs as the source of truth until they merge or close.

## Authoritative procedure (read and follow — do not invent)

**Read and follow** these docs in the workspace. They are the technical contract. Do **not** invent parallel steps.

1. `docs/onboarding/registering-a-repository.md` — especially **Pull request inventory**, **Consumer secrets discovery**, **Automation contract**, **Steps** (including step **2e** and onboard TokenPolicy selector), and the TokenPolicy appendix.
2. `docs/user-guide/onboard-a-repository.md` — two-phase UX and post-merge dashboard enablement to cite in the issue comment.

Edit the checked-out trees named in the Automation contract (`repos/catalog-info`, `repos/observability-github-settings`, `repos/observability-github-secrets`, this repository root for `elastic/oblt-aw`, and `repos/consumer` for CODEOWNERS / Renovate in Phase 2). Settings stacks live under `resources/<settings-org>/branch-protections/<repo>/` (`docs`→`obs` until `orgs.json` has docs).

### Org-scoped allowlists (catalog) — Phase 1

Follow registering-resources step **2e** in full, **and** add `elastic/<repo>` to the onboard agent TokenPolicy selector.

In the catalog concern PR: (1) add the consumer TokenPolicy for `trigger-<org>-aw-*.yml@*`. (2) Map the registration org-key to the policy suffix — `obs`→`obs`, `security`→`security`, `docs`→`obs` (temporary). Ensure the consumer’s github-repository RRE lives under `resources/github/engineering/<backstage-org>/`. (3) Ensure these list `elastic/<repo>`:

- `token-policy-oblt-aw-sync-control-plane-dashboard-<suffix>.yaml`
- `token-policy-oblt-aw-distribute-client-workflow-<suffix>.yaml`
- `token-policy-observability-github-settings-<suffix>.yaml`
- `token-policy-oblt-aw-onboard-repository.yaml` (onboard agent; required so Phase 2 can open consumer PRs)

(4) **Phase 2 merge bridge (platform, once)** — If any of these are missing on `repos/catalog-info`, copy them from this repository’s `platform/catalog-info/` tree into the catalog PR (same relative paths):

- `.github/workflows/oblt-aw-onboard-phase2-bridge.yml`
- `.github/scripts/oblt-aw-onboard-phase2-bridge/check_phase2.py`
- `resources/github-token-policies/token-policy-oblt-aw-onboard-phase2-bridge.yaml`

Do **not** edit them when they already match. That bridge checks Phase 2 on this issue when an `[oblt-aw][onboard]` catalog PR merges.

(5) **Related issue (required on every catalog PR body)** — Every `create-pull-request` targeting `elastic/catalog-info` must include a line exactly like:

`Related issue: https://github.com/elastic/oblt-aw/issues/<N>`

where `<N>` is this onboard issue number. The catalog-info merge bridge uses that line to find the issue.

Run `python .github/scripts/update-token-policy-obs-repositories/update_token_policy.py --org <suffix>` (or append sorted selector rows) for the org-scoped policies. For the onboard policy, append a selector row for `elastic/<repo>` when missing (keep existing platform and consumer selectors). Prefer folding into `temporary_id` `aw_catalog`; on retry use `aw_catalog_settings` when the open catalog PR lacks allowlist or onboard-selector coverage. Do **not** invent `-docs` policies or use `ALWAYS_INCLUDE_REPOS`. Never rely on a later weekly job or on `active-repositories.json` alone.

### Consumer secrets — Phase 2

Before deciding whether to open a secrets PR (do **not** hardcode secret names):

1. Read `config/<org-key>/workflow-registry.json`.
2. Build the **effective** workflow list for that org:
   - For each id in top-level `include_common` (when present), look up that service in `config/common/services.json` and take its object (including `docs`).
   - Then append every local `workflows` entry.
   - Do **not** read only the local `workflows` array — shared services such as `estc-pr-buildkite-detective` live under `include_common` and would be skipped.
3. For **every** effective entry with a `docs:` path, **open that markdown file** and collect consumer-facing secret names from **Prerequisites** first (when the doc says consumers provision/map a name). Fall back to required `Secret:` lines under **API / Interface**.
4. **Union across all effective workflows.** Do **not** filter by `default_enabled`, `enabled_by_default`, “onboarding defaults”, maturity, or whether a workflow is likely to be toggled on later. A secrets PR provisions for the org catalog; dashboard opt-in is separate.
5. In `repos/observability-github-secrets`, resolve each name to a `conf/shared` module (`*.tf` search or README Create Secret table). Fail closed if unresolved — do not invent modules or skip unresolved names.
6. Non-empty set → scaffold or update `conf/resources/<repo>/` (+ `docs/<repo>.md`) and open one secrets PR (`temporary_id` `aw_secrets`). Empty set **only after** the full-union steps above → skip and record “none” in the checklist. Never write “none” because you only inspected default-enabled entries, ignored `include_common`, or did not open the docs files.

Follow `docs/onboarding/registering-a-repository.md` (**Consumer secrets discovery**) in full.

### Consumer CODEOWNERS and Renovate — Phase 2

In `repos/consumer` (or the consumer checkout):

1. **CODEOWNERS (always)** — Append (do not replace other owners) the org trigger rule from registering step **5a**. Open PR `temporary_id` `aw_codeowners` targeting `elastic/<repo>`.
2. **Renovate (when enabled)** — If the consumer has Renovate config (`renovate.json`, `renovate.json5`, or `.github/renovate.json` / `.json5`), append the `packageRules` ignore from registering step **5b**. Open PR `temporary_id` `aw_renovate`. If no Renovate config, skip and record “none” in the checklist.

### Markdown format (comments and PR bodies)

Pass **real newlines** in every safe-output text field that GitHub renders as Markdown:

- `add-comment` `body`
- `create-pull-request` `body` (and titles without embedded `\n`)

Never put the two-character sequence `\` + `n` in those fields; never collapse a multi-line body into one escaped line. Use headings and lists GitHub can render. For links, prefer full `https://github.com/.../pull/<n>` URLs or `#aw_…` ids — not `owner/repo#n` shorthand and not invented `pulls?q=` search links.

### Issue comment

On each `create-pull-request`, set a distinct `temporary_id` (`aw_catalog`, `aw_catalog_settings`, `aw_obltaw`, `aw_settings`, `aw_secrets`, `aw_codeowners`, `aw_renovate` as needed). Link newly opened PRs with those `#aw_…` ids so safe-outputs rewrite them to exact PR URLs. For already-open PRs, use real `https://github.com/<owner>/<repo>/pull/<n>` URLs from search / `gh pr list`.

**Content to include** in the issue comment (wording and heading text may vary):

- Parsed repository, organization key, and which **phase** ran
- Checklist of opened or skipped PRs for that phase
- **Phase 1:** tell the human to merge the catalog-info PR; Phase 2 normally starts automatically on that merge (manual Phase 2 check remains a fallback)
- **Phase 2:** merge order (catalog already merged; then `elastic/oblt-aw`; settings and secrets before relying on automerge / secret-backed workflows; consumer CODEOWNERS and Renovate ignore before or with distribute)
- That merges are **manual**
- Pointer to `docs/user-guide/onboard-a-repository.md` for post-merge dashboard enablement

**Pull request bodies** must also follow [Markdown format](#markdown-format-comments-and-pr-bodies). Keep them short (summary of the concern-specific change); do not paste discovery essays or escaped newline sequences.

## Safe-output constraints

- Open PRs only via `create-pull-request` (`draft: false`). Do not merge. Do not close the onboard issue.
- Do **not** rewrite the issue body (Phase 2 abort uncheck is host-owned). Do not toggle phase checkboxes from the agent.
- Finish with `add-comment` covering the content above, in **valid Markdown** (real newlines; exact PR links), unless the run is a pure `noop`.
- On failure, comment what failed; never invent credentials.
- Call at least one of: `create-pull-request`, `add-comment`, or `noop`. A text-only exit with zero safe outputs is a failure.
