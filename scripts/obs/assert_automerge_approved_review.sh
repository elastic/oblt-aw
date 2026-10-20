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

# Fail-closed helpers: require a non-author APPROVED review for the PR head.
# Source this file; do not execute it directly.
#
# Exit codes for automerge_assert_pr_has_approved_review:
#   0 — non-author APPROVED (latest decisive) for head_sha
#   2 — lookup succeeded; no matching approval (missing_approval)
#   1 — could not verify (API error, invalid args, etc.)

# Print the live PR head SHA (40-hex) or return 1.
automerge_fetch_pr_head_sha() {
  local repo="${1:?repo required}"
  local pr_number="${2:?pr number required}"
  local head_sha
  head_sha="$(gh api "repos/${repo}/pulls/${pr_number}" --jq '.head.sha // empty')" || {
    echo "Failed to fetch head SHA for ${repo}#${pr_number}." >&2
    return 1
  }
  if [[ ! "${head_sha}" =~ ^[0-9a-f]{40}$ ]]; then
    echo "automerge_fetch_pr_head_sha: expected 40-hex sha, got: ${head_sha}" >&2
    return 1
  fi
  printf '%s\n' "${head_sha}"
}

# Fail unless expected_sha matches the live PR head (stale workflow re-run / race).
automerge_require_pr_head_sha() {
  local repo="${1:?repo required}"
  local pr_number="${2:?pr number required}"
  local expected_sha="${3:?expected sha required}"
  local live_sha
  if [[ ! "${expected_sha}" =~ ^[0-9a-f]{40}$ ]]; then
    echo "automerge_require_pr_head_sha: expected 40-hex sha, got: ${expected_sha}" >&2
    return 1
  fi
  live_sha="$(automerge_fetch_pr_head_sha "${repo}" "${pr_number}")" || return 1
  if [[ "${live_sha}" != "${expected_sha}" ]]; then
    echo "PR head moved: live=${live_sha} expected=${expected_sha} for ${repo}#${pr_number}." >&2
    return 1
  fi
  return 0
}

# True when reviews_json has a non-author whose latest decisive review on head_sha
# is APPROVED. Decisive states: APPROVED, CHANGES_REQUESTED, DISMISSED.
# Later COMMENTED / PENDING reviews do not clear an earlier approval.
automerge_reviews_have_non_author_approval() {
  local reviews_json="${1:?reviews json required}"
  local author_login="${2:?author login required}"
  local head_sha="${3:?head sha required}"
  local match
  if [[ ! "${head_sha}" =~ ^[0-9a-f]{40}$ ]]; then
    echo "automerge_reviews_have_non_author_approval: expected 40-hex sha, got: ${head_sha}" >&2
    return 1
  fi
  match="$(printf '%s' "${reviews_json}" | jq -r \
    --arg author "${author_login}" \
    --arg sha "${head_sha}" \
    '
    [.[]
      | select((.user.login // "") != $author)
      | select((.commit_id // "") == $sha)
      | . + {state_u: ((.state // "") | ascii_upcase)}
    ]
    | group_by(.user.login)
    | map(
        sort_by(.id)
        | map(select(
            .state_u == "APPROVED"
            or .state_u == "CHANGES_REQUESTED"
            or .state_u == "DISMISSED"
          ))
        | last
      )
    | map(select(. != null and .state_u == "APPROVED"))
    | first
    | .id // empty
    ')"
  [[ -n "${match}" && "${match}" != "null" ]]
}

# Fetch PR reviews and fail closed unless a non-author APPROVED review exists for head_sha.
# Prints ASSERT_REASON=ok|missing_approval|verify_failed on stdout for workflow wiring.
automerge_assert_pr_has_approved_review() {
  local repo="${1:?repo required}"
  local pr_number="${2:?pr number required}"
  local author_login="${3:?author login required}"
  local head_sha="${4:?head sha required}"
  local reviews_json
  if [[ ! "${head_sha}" =~ ^[0-9a-f]{40}$ ]]; then
    echo "ASSERT_REASON=verify_failed"
    echo "automerge_assert_pr_has_approved_review: expected 40-hex sha, got: ${head_sha}" >&2
    return 1
  fi
  reviews_json="$(gh api "repos/${repo}/pulls/${pr_number}/reviews" --paginate)" || {
    echo "ASSERT_REASON=verify_failed"
    echo "Failed to list reviews for ${repo}#${pr_number}." >&2
    return 1
  }
  if automerge_reviews_have_non_author_approval "${reviews_json}" "${author_login}" "${head_sha}"; then
    echo "ASSERT_REASON=ok"
    echo "Found non-author APPROVED review for ${repo}#${pr_number} at ${head_sha}."
    return 0
  fi
  echo "ASSERT_REASON=missing_approval"
  echo "Missing APPROVE review: expected a non-author GitHub review with state APPROVED for head ${head_sha} on ${repo}#${pr_number} (COMMENT-only or no review does not satisfy MERGE_REQUIRED_APPROVALS)." >&2
  return 2
}
