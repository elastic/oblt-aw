---
# Hardcoded OIDC mint for gh-aw-onboard-repository (standalone issues trigger).
# Role token-policy-995e89faa204 is sha256 of
# elastic/oblt-aw/.github/workflows/gh-aw-onboard-repository.lock.yml (first 12 hex).
# Requires permissions.id-token: write on the importing workflow.
#
# The compiler only accepts a single secrets.* chain or a single steps.*.outputs.*
# expression for github-token, so scripts/wire-ephemeral-token.py rewrites compiled
# lock files to prefer the minted step outputs before GH_AW_GITHUB_TOKEN / GITHUB_TOKEN.
jobs:
  activation:
    pre-steps:
      - name: Create ephemeral GitHub token
        id: create-token
        uses: elastic/oblt-actions/github/create-token@v1
        with:
          token-policy: token-policy-995e89faa204
  agent:
    pre-steps:
      - name: Create ephemeral GitHub token
        id: create-token
        uses: elastic/oblt-actions/github/create-token@v1
        with:
          token-policy: token-policy-995e89faa204
  safe_outputs:
    pre-steps:
      - name: Create ephemeral GitHub token
        id: create-token
        uses: elastic/oblt-actions/github/create-token@v1
        with:
          token-policy: token-policy-995e89faa204
  conclusion:
    pre-steps:
      - name: Create ephemeral GitHub token
        id: create-token
        uses: elastic/oblt-actions/github/create-token@v1
        with:
          token-policy: token-policy-995e89faa204
---
