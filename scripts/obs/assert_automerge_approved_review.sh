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

# True when reviews_json contains at least one APPROVED review whose user is not
# the PR author and whose commit_id matches head_sha.
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
    '[.[]
      | select((.state // "") | ascii_upcase == "APPROVED")
      | select((.user.login // "") != $author)
      | select((.commit_id // "") == $sha)
     ] | first | .id // empty')"
  [[ -n "${match}" && "${match}" != "null" ]]
}

# Fetch PR reviews and fail closed unless a non-author APPROVED review exists for head_sha.
automerge_assert_pr_has_approved_review() {
  local repo="${1:?repo required}"
  local pr_number="${2:?pr number required}"
  local author_login="${3:?author login required}"
  local head_sha="${4:?head sha required}"
  local reviews_json
  reviews_json="$(gh api "repos/${repo}/pulls/${pr_number}/reviews" --paginate)" || {
    echo "Failed to list reviews for ${repo}#${pr_number}." >&2
    return 1
  }
  if automerge_reviews_have_non_author_approval "${reviews_json}" "${author_login}" "${head_sha}"; then
    echo "Found non-author APPROVED review for ${repo}#${pr_number} at ${head_sha}."
    return 0
  fi
  echo "Missing APPROVE review: expected a non-author GitHub review with state APPROVED for head ${head_sha} on ${repo}#${pr_number} (COMMENT-only or no review does not satisfy MERGE_REQUIRED_APPROVALS)." >&2
  return 1
}
