---
# Elastic-specific: mint an OIDC ephemeral GitHub token in each token-consuming job.
# Requires Elastic TokenPolicy / ephemeral-token infrastructure (create-token).
#
# Resolve the policy id from (first match wins):
# 1. Job/workflow env WORKFLOW_TOKEN_POLICY (explicit id)
# 2. Job/workflow env WORKFLOW_TOKEN_POLICY_CONFIG (JSON path with
#    "workflow-token-policy", e.g. config/onboard-repository.json or config/e2e.json)
#
# When WORKFLOW_TOKEN_POLICY_CONFIG is set but the file is not on disk yet
# (create-token often runs before checkout), the resolve step loads the file
# via the GitHub Contents API at github.sha.
#
# Importing workflows must set one of those env vars (workflow- or job-level)
# and grant permissions.id-token: write.
#
# The compiler only accepts a single secrets.* chain or a single steps.*.outputs.*
# expression for github-token, so scripts/wire_ephemeral_token.py rewrites compiled
# lock files to prefer the minted step outputs before GH_AW_GITHUB_TOKEN / GITHUB_TOKEN.
jobs:
  activation:
    pre-steps:
      - name: Resolve ephemeral token policy
        id: resolve-token-policy
        env:
          WORKFLOW_TOKEN_POLICY: ${{ env.WORKFLOW_TOKEN_POLICY }}
          WORKFLOW_TOKEN_POLICY_CONFIG: ${{ env.WORKFLOW_TOKEN_POLICY_CONFIG }}
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          set -euo pipefail
          POLICY="${WORKFLOW_TOKEN_POLICY:-}"
          if [[ -z "${POLICY}" && -n "${WORKFLOW_TOKEN_POLICY_CONFIG:-}" ]]; then
            if [[ -f "${WORKFLOW_TOKEN_POLICY_CONFIG}" ]]; then
              POLICY="$(jq -r '."workflow-token-policy" // empty' "${WORKFLOW_TOKEN_POLICY_CONFIG}")"
            else
              POLICY="$(gh api "repos/${GITHUB_REPOSITORY}/contents/${WORKFLOW_TOKEN_POLICY_CONFIG}?ref=${GITHUB_SHA}" \
                --jq '.content' | base64 -d | jq -r '."workflow-token-policy" // empty')"
            fi
          fi
          if [[ -z "${POLICY}" ]]; then
            echo "::notice::No workflow-token-policy resolved; create-token will be skipped"
          fi
          echo "token-policy=${POLICY}" >> "${GITHUB_OUTPUT}"
      - name: Create ephemeral GitHub token
        id: create-token
        if: ${{ steps.resolve-token-policy.outputs.token-policy != '' }}
        uses: elastic/oblt-actions/github/create-token@v1
        with:
          token-policy: ${{ steps.resolve-token-policy.outputs.token-policy }}
  agent:
    pre-steps:
      - name: Resolve ephemeral token policy
        id: resolve-token-policy
        env:
          WORKFLOW_TOKEN_POLICY: ${{ env.WORKFLOW_TOKEN_POLICY }}
          WORKFLOW_TOKEN_POLICY_CONFIG: ${{ env.WORKFLOW_TOKEN_POLICY_CONFIG }}
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          set -euo pipefail
          POLICY="${WORKFLOW_TOKEN_POLICY:-}"
          if [[ -z "${POLICY}" && -n "${WORKFLOW_TOKEN_POLICY_CONFIG:-}" ]]; then
            if [[ -f "${WORKFLOW_TOKEN_POLICY_CONFIG}" ]]; then
              POLICY="$(jq -r '."workflow-token-policy" // empty' "${WORKFLOW_TOKEN_POLICY_CONFIG}")"
            else
              POLICY="$(gh api "repos/${GITHUB_REPOSITORY}/contents/${WORKFLOW_TOKEN_POLICY_CONFIG}?ref=${GITHUB_SHA}" \
                --jq '.content' | base64 -d | jq -r '."workflow-token-policy" // empty')"
            fi
          fi
          if [[ -z "${POLICY}" ]]; then
            echo "::notice::No workflow-token-policy resolved; create-token will be skipped"
          fi
          echo "token-policy=${POLICY}" >> "${GITHUB_OUTPUT}"
      - name: Create ephemeral GitHub token
        id: create-token
        if: ${{ steps.resolve-token-policy.outputs.token-policy != '' }}
        uses: elastic/oblt-actions/github/create-token@v1
        with:
          token-policy: ${{ steps.resolve-token-policy.outputs.token-policy }}
  safe_outputs:
    pre-steps:
      - name: Resolve ephemeral token policy
        id: resolve-token-policy
        env:
          WORKFLOW_TOKEN_POLICY: ${{ env.WORKFLOW_TOKEN_POLICY }}
          WORKFLOW_TOKEN_POLICY_CONFIG: ${{ env.WORKFLOW_TOKEN_POLICY_CONFIG }}
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          set -euo pipefail
          POLICY="${WORKFLOW_TOKEN_POLICY:-}"
          if [[ -z "${POLICY}" && -n "${WORKFLOW_TOKEN_POLICY_CONFIG:-}" ]]; then
            if [[ -f "${WORKFLOW_TOKEN_POLICY_CONFIG}" ]]; then
              POLICY="$(jq -r '."workflow-token-policy" // empty' "${WORKFLOW_TOKEN_POLICY_CONFIG}")"
            else
              POLICY="$(gh api "repos/${GITHUB_REPOSITORY}/contents/${WORKFLOW_TOKEN_POLICY_CONFIG}?ref=${GITHUB_SHA}" \
                --jq '.content' | base64 -d | jq -r '."workflow-token-policy" // empty')"
            fi
          fi
          if [[ -z "${POLICY}" ]]; then
            echo "::notice::No workflow-token-policy resolved; create-token will be skipped"
          fi
          echo "token-policy=${POLICY}" >> "${GITHUB_OUTPUT}"
      - name: Create ephemeral GitHub token
        id: create-token
        if: ${{ steps.resolve-token-policy.outputs.token-policy != '' }}
        uses: elastic/oblt-actions/github/create-token@v1
        with:
          token-policy: ${{ steps.resolve-token-policy.outputs.token-policy }}
  conclusion:
    pre-steps:
      - name: Resolve ephemeral token policy
        id: resolve-token-policy
        env:
          WORKFLOW_TOKEN_POLICY: ${{ env.WORKFLOW_TOKEN_POLICY }}
          WORKFLOW_TOKEN_POLICY_CONFIG: ${{ env.WORKFLOW_TOKEN_POLICY_CONFIG }}
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          set -euo pipefail
          POLICY="${WORKFLOW_TOKEN_POLICY:-}"
          if [[ -z "${POLICY}" && -n "${WORKFLOW_TOKEN_POLICY_CONFIG:-}" ]]; then
            if [[ -f "${WORKFLOW_TOKEN_POLICY_CONFIG}" ]]; then
              POLICY="$(jq -r '."workflow-token-policy" // empty' "${WORKFLOW_TOKEN_POLICY_CONFIG}")"
            else
              POLICY="$(gh api "repos/${GITHUB_REPOSITORY}/contents/${WORKFLOW_TOKEN_POLICY_CONFIG}?ref=${GITHUB_SHA}" \
                --jq '.content' | base64 -d | jq -r '."workflow-token-policy" // empty')"
            fi
          fi
          if [[ -z "${POLICY}" ]]; then
            echo "::notice::No workflow-token-policy resolved; create-token will be skipped"
          fi
          echo "token-policy=${POLICY}" >> "${GITHUB_OUTPUT}"
      - name: Create ephemeral GitHub token
        id: create-token
        if: ${{ steps.resolve-token-policy.outputs.token-policy != '' }}
        uses: elastic/oblt-actions/github/create-token@v1
        with:
          token-policy: ${{ steps.resolve-token-policy.outputs.token-policy }}
---
