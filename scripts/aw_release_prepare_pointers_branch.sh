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

# Prepare a branch from default-branch tip that lands a planned
# config/release-pointers.json without silently overwriting newer tip state.
#
# Fail closed when tip's pointer file differs from the plan-base SHA (the
# revision the promote/rollback plan was computed from). Re-dispatch on
# current tip instead of clobbering a concurrent promote/rollback landing.
#
# Required env:
#   BRANCH_PREFIX    Branch name prefix (e.g. release/pointers)
#   DEFAULT_BRANCH   Repository default branch
#   PLAN_BASE_SHA    Full SHA used as plan input (usually github.sha)
#   RUN_ID           Unique suffix (usually github.run_id)
# Actions env (when not sourced for unit tests):
#   GITHUB_OUTPUT    Job output file
#   RUNNER_TEMP      Scratch directory for the planned file
# Optional env:
#   POINTERS_PATH    default config/release-pointers.json

set -euo pipefail

POINTERS_PATH="${POINTERS_PATH:-config/release-pointers.json}"

aw_release_blob_at_ref() {
  local ref="${1:?}"
  local path="${2:?}"
  if git cat-file -e "${ref}:${path}" 2>/dev/null; then
    git show "${ref}:${path}"
    return 0
  fi
  return 1
}

# Fail unless tip and plan-base agree on the pointer file contents.
# Args: plan_base_sha tip_ref [pointers_path]
aw_release_require_pointers_base_matches_tip() {
  local plan_base_sha="${1:?}"
  local tip_ref="${2:?}"
  local path="${3:-${POINTERS_PATH}}"
  local base_blob tip_blob
  local base_rc=0 tip_rc=0

  base_blob="$(aw_release_blob_at_ref "${plan_base_sha}" "${path}")" || base_rc=$?
  tip_blob="$(aw_release_blob_at_ref "${tip_ref}" "${path}")" || tip_rc=$?

  if ((base_rc != 0 && tip_rc != 0)); then
    echo "Pointer file absent on both ${plan_base_sha:0:12} and ${tip_ref}; ok"
    return 0
  fi

  if ((base_rc != tip_rc)); then
    echo "::error::${path} presence differs between plan base ${plan_base_sha:0:12} and ${tip_ref}."
    echo "::error::Re-dispatch on the current default-branch tip; refuse to overwrite tip state."
    return 1
  fi

  if [[ "${base_blob}" != "${tip_blob}" ]]; then
    echo "::error::${path} at ${tip_ref} differs from plan base ${plan_base_sha:0:12}."
    echo "::error::Another promote/rollback (or manual edit) landed while this run used a stale plan."
    echo "::error::Re-dispatch on the current default-branch tip; refuse to overwrite tip state."
    return 1
  fi

  echo "Pointer file at ${tip_ref} matches plan base ${plan_base_sha:0:12}"
  return 0
}

aw_release_prepare_pointers_branch() {
  local default_branch="${1:?}"
  local plan_base_sha="${2:?}"
  local branch_prefix="${3:?}"
  local run_id="${4:?}"
  local pointers_path="${5:-${POINTERS_PATH}}"
  local github_output="${6:-${GITHUB_OUTPUT:-}}"
  local runner_temp="${7:-${RUNNER_TEMP:-}}"
  local planned tip_ref branch

  if [[ -z "${github_output}" || -z "${runner_temp}" ]]; then
    echo "GITHUB_OUTPUT and RUNNER_TEMP are required" >&2
    return 1
  fi

  if git diff --quiet -- "${pointers_path}"; then
    echo "No pointer file changes to land"
    echo "has_changes=false" >>"${github_output}"
    return 0
  fi

  planned="${runner_temp}/release-pointers.json"
  cp "${pointers_path}" "${planned}"

  git fetch origin "${default_branch}"
  tip_ref="origin/${default_branch}"
  aw_release_require_pointers_base_matches_tip \
    "${plan_base_sha}" \
    "${tip_ref}" \
    "${pointers_path}"

  # Keep local tags from promote/rollback; only move the working tree.
  branch="${branch_prefix}-${run_id}"
  git checkout -B "${branch}" "${tip_ref}"
  cp "${planned}" "${pointers_path}"
  echo "has_changes=true" >>"${github_output}"
  echo "Prepared branch ${branch} from ${tip_ref}"
}

# When sourced (unit tests), skip main.
if [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
  return 0
fi

: "${DEFAULT_BRANCH:?DEFAULT_BRANCH is required}"
: "${PLAN_BASE_SHA:?PLAN_BASE_SHA is required}"
: "${BRANCH_PREFIX:?BRANCH_PREFIX is required}"
: "${RUN_ID:?RUN_ID is required}"
: "${GITHUB_OUTPUT:?GITHUB_OUTPUT is required}"
: "${RUNNER_TEMP:?RUNNER_TEMP is required}"

aw_release_prepare_pointers_branch \
  "${DEFAULT_BRANCH}" \
  "${PLAN_BASE_SHA}" \
  "${BRANCH_PREFIX}" \
  "${RUN_ID}" \
  "${POINTERS_PATH}" \
  "${GITHUB_OUTPUT}" \
  "${RUNNER_TEMP}"
