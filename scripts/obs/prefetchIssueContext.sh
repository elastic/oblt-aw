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

# Prefetch issue title, body, labels, and comments for GH-AW issue fixer prompts.
# Public-repo MCP guard policies (min-integrity: approved) can hide triage bot comments
# (e.g. github-actions with CONTRIBUTOR association). This script uses GITHUB_TOKEN
# directly so the agent still receives the full thread.
set -euo pipefail

issue_number="${ISSUE_NUMBER:?ISSUE_NUMBER is required}"
repository="${REPOSITORY:?REPOSITORY is required}"

issue_json=$(gh issue view "$issue_number" --repo "$repository" --json number,title,body,labels,author,state,url)
issue_title=$(jq -r '.title' <<<"$issue_json")
issue_body=$(jq -r '.body // ""' <<<"$issue_json")
issue_author=$(jq -r '.author.login' <<<"$issue_json")
issue_state=$(jq -r '.state' <<<"$issue_json")
issue_url=$(jq -r '.url' <<<"$issue_json")
issue_labels=$(jq -r '[.labels[].name] | join(", ")' <<<"$issue_json")

comments_json=$(gh api "repos/${repository}/issues/${issue_number}/comments" --paginate)
comment_count=$(jq 'length' <<<"$comments_json")

{
  echo "Issue #${issue_number}: ${issue_title}"
  echo "URL: ${issue_url}"
  echo "State: ${issue_state}"
  echo "Author: ${issue_author}"
  echo "Labels: ${issue_labels:-<none>}"
  echo
  echo "## Issue body"
  echo "$issue_body"
  echo
  echo "## Comments (${comment_count})"
  if [ "$comment_count" -eq 0 ]; then
    echo "<no comments>"
  else
    jq -r '.[] | "### Comment by \(.user.login) (\(.created_at))\n\n\(.body)\n"' <<<"$comments_json"
  fi
} >"${RUNNER_TEMP}/prefetched-issue-context.md"

{
  echo 'context<<EOF'
  cat "${RUNNER_TEMP}/prefetched-issue-context.md"
  echo 'EOF'
} >>"${GITHUB_OUTPUT:?GITHUB_OUTPUT is required}"
