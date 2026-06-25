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

# Closes older open security detector issues superseded by a newer issue for the same SEC rule.
# Usage: supersede-security-issues.sh <canonical_issue_number>
#
# Environment:
#   GITHUB_REPOSITORY (required)
#   GH_TOKEN (required unless DRY_RUN=1)
#   DRY_RUN (optional, set to 1 to log actions without mutating GitHub)
set -euo pipefail

readonly DETECTOR_LABEL="oblt-aw/detector/security"
readonly TITLE_PREFIX="[oblt-aw][security]"
readonly KEEP_OPEN_LABEL="oblt-aw/keep-open"

log() {
  printf '%s\n' "$*" >&2
}

is_dry_run() {
  [[ "${DRY_RUN:-0}" == "1" ]]
}

parse_sec_id_from_title() {
  local title="$1"
  if [[ "$title" =~ ^\[oblt-aw\]\[security\]\ (SEC-[0-9]+)[[:space:]] ]]; then
    printf '%s\n' "${BASH_REMATCH[1]}"
    return 0
  fi
  return 1
}

issue_has_label() {
  local labels_json="$1"
  local wanted="$2"
  jq -e --arg label "$wanted" '[.labels[].name] | index($label) != null' <<< "$labels_json" >/dev/null
}

find_open_linked_prs() {
  local issue_number="$1"
  local repo="$2"
  local pr_number pr_json results="[]"

  # Use issue cross-references (Issues/PRs API) instead of gh search prs, which
  # requires the Search API scope that ephemeral workflow tokens often lack.
  while IFS= read -r pr_number; do
    [[ -z "$pr_number" ]] && continue
    pr_json="$(gh pr view "$pr_number" --repo "$repo" --json number,state)"
    if [[ "$(jq -r '.state' <<< "$pr_json")" != "OPEN" ]]; then
      continue
    fi
    results="$(jq -c --argjson pr "$pr_json" '. + [$pr]' <<< "$results")"
  done < <(
    gh issue view "$issue_number" --repo "$repo" \
      --json closedByPullRequestsReferences \
      | jq -r '.closedByPullRequestsReferences[]?.number // empty'
  )

  printf '%s\n' "$results"
}

issue_has_open_linked_pr() {
  local issue_number="$1"
  local repo="$2"
  local linked_prs

  linked_prs="$(find_open_linked_prs "$issue_number" "$repo")"
  [[ "$(jq 'length' <<< "$linked_prs")" -gt 0 ]]
}

issue_should_stay_open() {
  local issue_number="$1"
  local repo="$2"
  local issue_json="$3"

  if issue_has_label "$issue_json" "$KEEP_OPEN_LABEL"; then
    printf '%s\n' "$KEEP_OPEN_LABEL"
    return 0
  fi

  if issue_has_open_linked_pr "$issue_number" "$repo"; then
    printf 'open linked PR\n'
    return 0
  fi

  return 1
}

supersession_comment() {
  local canonical="$1"
  local sec_id="$2"
  cat <<EOF
Superseded by #${canonical} — a newer security detector issue replaces this report for the same rule (**${sec_id}**).

This issue is closed automatically. See #${canonical} for the latest findings and analysis date.
EOF
}

close_superseded_issue() {
  local issue_number="$1"
  local canonical="$2"
  local sec_id="$3"
  local repo="$4"
  local comment
  comment="$(supersession_comment "$canonical" "$sec_id")"

  if is_dry_run; then
    log "[dry-run] would comment and close issue #${issue_number} (superseded by #${canonical})"
    return 0
  fi

  gh issue comment "$issue_number" --repo "$repo" --body "$comment"
  gh issue close "$issue_number" --repo "$repo" --reason "not planned"
}

process_superseded_issue() {
  local issue_number="$1"
  local canonical="$2"
  local sec_id="$3"
  local repo="$4"
  local issue_json stay_open_reason

  issue_json="$(gh issue view "$issue_number" --repo "$repo" --json number,title,state,labels)"
  if [[ "$(jq -r '.state' <<< "$issue_json")" != "OPEN" ]]; then
    log "Skipping #${issue_number}: not open"
    return 0
  fi

  if stay_open_reason="$(issue_should_stay_open "$issue_number" "$repo" "$issue_json")"; then
    log "Skipping #${issue_number}: ${stay_open_reason}"
    return 0
  fi

  close_superseded_issue "$issue_number" "$canonical" "$sec_id" "$repo"
}

main() {
  local canonical_issue="${1:?canonical issue number required}"
  local repo="${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}"
  local canonical_json canonical_title sec_id candidates issue_number row

  export DRY_RUN="${DRY_RUN:-0}"

  if ! command -v gh >/dev/null 2>&1; then
    log "gh CLI is required"
    exit 1
  fi
  if ! command -v jq >/dev/null 2>&1; then
    log "jq is required"
    exit 1
  fi

  if is_dry_run; then
    log "[dry-run] supersede-security-issues for canonical issue #${canonical_issue}"
  fi

  canonical_json="$(gh issue view "$canonical_issue" --repo "$repo" --json number,title,state,labels)"
  if [[ "$(jq -r '.state' <<< "$canonical_json")" != "OPEN" ]]; then
    log "Canonical issue #${canonical_issue} is not open; nothing to do"
    exit 0
  fi

  if ! issue_has_label "$canonical_json" "$DETECTOR_LABEL"; then
    log "Canonical issue #${canonical_issue} lacks ${DETECTOR_LABEL}; skipping"
    exit 0
  fi

  canonical_title="$(jq -r '.title' <<< "$canonical_json")"
  if ! sec_id="$(parse_sec_id_from_title "$canonical_title")"; then
    log "Canonical issue #${canonical_issue} title is not a security detector issue; skipping"
    exit 0
  fi

  candidates="$(gh issue list \
    --repo "$repo" \
    --label "$DETECTOR_LABEL" \
    --state open \
    --limit 500 \
    --json number,title \
    | jq -c --argjson canonical "$canonical_issue" --arg sec "$sec_id" --arg prefix "$TITLE_PREFIX" '
        .[]
        | select(.number < $canonical)
        | select(.title | startswith($prefix + " " + $sec))
      ')"

  if [[ -z "$candidates" ]]; then
    log "No older open issues to supersede for ${sec_id}"
    exit 0
  fi

  while IFS= read -r row; do
    [[ -z "$row" ]] && continue
    issue_number="$(jq -r '.number' <<< "$row")"
    process_superseded_issue "$issue_number" "$canonical_issue" "$sec_id" "$repo"
  done <<< "$candidates"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
