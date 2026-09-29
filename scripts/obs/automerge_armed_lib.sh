#!/usr/bin/env bash
# Copyright 2026-2027 Elasticsearch B.V.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

# Shared helpers for automerge arm → deferred merge (marker + REST error class).
# Source this file; do not execute it directly.

AUTOMERGE_ARMED_BOT='github-actions[bot]'
# HTML comment marker always includes the approved head SHA, e.g.
# <!-- obs-aw-automerge:armed sha=0123…abcdef -->

automerge_armed_marker_line() {
  local sha="${1:?head sha required}"
  if [[ ! "${sha}" =~ ^[0-9a-f]{40}$ ]]; then
    echo "automerge_armed_marker_line: expected 40-hex sha, got: ${sha}" >&2
    return 1
  fi
  printf '<!-- obs-aw-automerge:armed sha=%s -->' "${sha}"
}

# True when REST merge failed because required checks are still pending (retry later).
automerge_merge_error_is_pending_checks() {
  local msg="${1:-}"
  printf '%s' "${msg}" | grep -qiE \
    'required status check|[[:space:]]pending[[:space:]]|awaiting status|status checks? (are |have )?not|Must be green before merging'
}

# True when REST merge reported the PR was already merged (not merely closed).
automerge_merge_error_is_already_merged_message() {
  local msg="${1:-}"
  printf '%s' "${msg}" | grep -qiE 'already been merged'
}

# List issue comments as JSON (paginated). Fails closed on API errors.
automerge_list_issue_comments() {
  local repo="${1:?}"
  local pr_number="${2:?}"
  gh api "repos/${repo}/issues/${pr_number}/comments" --paginate
}

# True when comments_json contains a bot-authored marker for this exact head SHA.
automerge_comments_armed_for_sha() {
  local comments_json="${1:?}"
  local head_sha="${2:?}"
  local match
  match="$(printf '%s' "${comments_json}" | jq -r \
    --arg bot "${AUTOMERGE_ARMED_BOT}" \
    --arg sha "${head_sha}" \
    '[.[]
      | select(.user.login == $bot)
      | ((.body // "")
          | capture("<!-- obs-aw-automerge:armed sha=(?<s>[0-9a-f]{40}) -->")? // empty
        )
      | .s
      | select(. == $sha)
     ] | first // empty')"
  [[ -n "${match}" ]]
}

# Find the first workflow-authored armed comment id (any head SHA). Empty if none.
automerge_find_bot_armed_comment_id_from_json() {
  local comments_json="${1:?}"
  printf '%s' "${comments_json}" | jq -r \
    --arg bot "${AUTOMERGE_ARMED_BOT}" \
    '[.[]
      | select(.user.login == $bot)
      | select((.body // "") | test("<!-- obs-aw-automerge:armed sha=[0-9a-f]{40} -->"))
      | .id
     ] | first // empty'
}

# Upsert a bot-owned armed comment bound to head_sha. Sets armed=true on GITHUB_OUTPUT when set.
# Optional 5th arg: shared-token-policy (non-empty => Vault-app bypass wording).
automerge_upsert_armed_comment() {
  local repo="${1:?}"
  local pr_number="${2:?}"
  local head_sha="${3:?}"
  local run_url="${4:-}"
  local token_policy="${5:-}"
  local marker
  marker="$(automerge_armed_marker_line "${head_sha}")"
  local retry_blurb
  if [[ -n "${token_policy}" ]]; then
    retry_blurb="This run stays successful. Deferred automerge on the frequent schedule (about every 15 minutes) will retry the squash-merge as the Vault app (CODEOWNERS bypass via classic \`pull_request_bypassers\`) once GitHub reports all required checks green."
  else
    retry_blurb="This run stays successful. Deferred automerge on the frequent schedule (about every 15 minutes) will retry the squash-merge with the workflow token. Configure a non-empty \`shared-token-policy\` when CODEOWNERS bypass via a Vault app is required."
  fi
  local body
  body="$(printf '%s\n\n%s\n\n%s\n\n%s' \
    "${marker}" \
    "Automerge did not merge yet because this pull request is **not ready** (required status checks are still pending)." \
    "${retry_blurb}" \
    "Armed by workflow run: ${run_url} (head \`${head_sha}\`)")"
  local comments_json
  comments_json="$(automerge_list_issue_comments "${repo}" "${pr_number}")" || return 1
  local comment_id
  comment_id="$(automerge_find_bot_armed_comment_id_from_json "${comments_json}")"
  if [[ -n "${comment_id}" ]]; then
    gh api --method PATCH "repos/${repo}/issues/comments/${comment_id}" -f body="${body}" >/dev/null
  else
    gh pr comment "${pr_number}" --repo "${repo}" --body "${body}"
  fi
  if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
    echo "armed=true" >>"${GITHUB_OUTPUT}"
  fi
}
