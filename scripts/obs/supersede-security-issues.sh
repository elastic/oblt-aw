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
#   ALLOWED_BOT_AUTHORS (optional, comma-separated logins; default: github-actions[bot])
#   DRY_RUN (optional, set to 1 to log actions without mutating GitHub)
set -euo pipefail

readonly DETECTOR_LABEL="oblt-aw/detector/security"
readonly TITLE_PREFIX="[oblt-aw][security]"
readonly BLOCK_LABELS=(
  "oblt-aw/ai/fix-ready"
  "oblt-aw/triage/security-injection"
  "oblt-aw/triage/security-secrets"
  "oblt-aw/triage/security-supply-chain"
  "oblt-aw/triage/security-least-privilege"
  "oblt-aw/triage/other"
  "oblt-aw/triage/needs-info"
)

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

issue_has_block_label() {
  local labels_json="$1"
  local label
  for label in "${BLOCK_LABELS[@]}"; do
    if issue_has_label "$labels_json" "$label"; then
      printf '%s\n' "$label"
      return 0
    fi
  done
  return 1
}

author_is_allowed_bot() {
  local author="$1"
  local csv="$2"
  local item normalized item_normalized
  normalized="$(printf '%s' "$author" | tr '[:upper:]' '[:lower:]')"
  IFS=',' read -ra items <<< "$csv"
  for item in "${items[@]}"; do
    item="${item#"${item%%[![:space:]]*}"}"
    item="${item%"${item##*[![:space:]]}"}"
    [[ -z "$item" ]] && continue
    item_normalized="$(printf '%s' "$item" | tr '[:upper:]' '[:lower:]')"
    if [[ "$item_normalized" == "$normalized" ]]; then
      return 0
    fi
  done
  return 1
}

find_open_linked_prs() {
  local issue_number="$1"
  local repo="$2"
  local search_query="repo:${repo} is:pr is:open \"#${issue_number}\""
  gh search prs "$search_query" \
    --json number,author,isDraft,title,body \
    --limit 20
}

linked_pr_references_issue() {
  local issue_number="$1"
  local pr_json="$2"
  local haystack
  haystack="$(jq -r '[.title // "", .body // ""] | join("\n")' <<< "$pr_json" | tr '[:upper:]' '[:lower:]')"
  [[ "$haystack" == *"fixes #${issue_number}"* ]] \
    || [[ "$haystack" == *"closes #${issue_number}"* ]] \
    || [[ "$haystack" == *"resolves #${issue_number}"* ]]
}

supersession_comment() {
  local canonical="$1"
  local sec_id="$2"
  cat <<EOF
Superseded by #${canonical} — a newer security detector issue replaces this report for the same rule (**${sec_id}**).

This issue is closed automatically. See #${canonical} for the latest findings and analysis date.
EOF
}

pr_supersession_comment() {
  local canonical="$1"
  local issue_number="$2"
  cat <<EOF
Closing as superseded: issue #${issue_number} was replaced by #${canonical} from a newer security detector scan.
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

close_superseded_pr() {
  local pr_number="$1"
  local canonical="$2"
  local issue_number="$3"
  local repo="$4"
  local comment
  comment="$(pr_supersession_comment "$canonical" "$issue_number")"

  if is_dry_run; then
    log "[dry-run] would close PR #${pr_number} (linked to superseded issue #${issue_number})"
    return 0
  fi

  gh pr close "$pr_number" --repo "$repo" --comment "$comment"
}

process_superseded_issue() {
  local issue_number="$1"
  local canonical="$2"
  local sec_id="$3"
  local repo="$4"
  local allowed_bot_authors="$5"
  local issue_json block_label linked_prs pr_json pr_number pr_author

  issue_json="$(gh issue view "$issue_number" --repo "$repo" --json number,title,state,labels)"
  if [[ "$(jq -r '.state' <<< "$issue_json")" != "OPEN" ]]; then
    log "Skipping #${issue_number}: not open"
    return 0
  fi

  if block_label="$(issue_has_block_label "$issue_json")"; then
    log "Skipping #${issue_number}: block label ${block_label}"
    return 0
  fi

  linked_prs="$(find_open_linked_prs "$issue_number" "$repo")"
  while IFS= read -r pr_json; do
    [[ -z "$pr_json" ]] && continue
    if ! linked_pr_references_issue "$issue_number" "$pr_json"; then
      continue
    fi
    pr_author="$(jq -r '.author.login // empty' <<< "$pr_json")"
    if [[ -n "$pr_author" ]] && ! author_is_allowed_bot "$pr_author" "$allowed_bot_authors"; then
      log "Skipping #${issue_number}: open non-bot PR by ${pr_author}"
      return 0
    fi
  done < <(jq -c '.[]' <<< "$linked_prs")

  close_superseded_issue "$issue_number" "$canonical" "$sec_id" "$repo"

  while IFS= read -r pr_json; do
    [[ -z "$pr_json" ]] && continue
    if ! linked_pr_references_issue "$issue_number" "$pr_json"; then
      continue
    fi
    pr_number="$(jq -r '.number' <<< "$pr_json")"
    pr_author="$(jq -r '.author.login // empty' <<< "$pr_json")"
    if [[ -n "$pr_author" ]] && author_is_allowed_bot "$pr_author" "$allowed_bot_authors"; then
      close_superseded_pr "$pr_number" "$canonical" "$issue_number" "$repo"
    fi
  done < <(jq -c '.[]' <<< "$linked_prs")
}

main() {
  local canonical_issue="${1:?canonical issue number required}"
  local repo="${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}"
  local allowed_bot_authors="${ALLOWED_BOT_AUTHORS:-github-actions[bot]}"
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
    process_superseded_issue "$issue_number" "$canonical_issue" "$sec_id" "$repo" "$allowed_bot_authors"
  done <<< "$candidates"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
