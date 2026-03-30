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

# Reads all pr-result-*.txt files from the pr-results/ directory,
# emits a single ::notice:: workflow annotation, and appends a
# markdown table to $GITHUB_STEP_SUMMARY.
set -euo pipefail

mapfile -t lines < <(sort pr-results/*.txt)

# Single workflow annotation: compact list of repo (operation)
parts=()
for line in "${lines[@]}"; do
  IFS='|' read -r repo op url <<< "$line"
  parts+=("${repo} (${op})")
done
annotation=$(IFS=', '; echo "${parts[*]}")
echo "::notice title=PR Distribution Results::${annotation}"

# Detailed table in step summary
{
  echo "## PR Distribution Results"
  echo
  echo "| Repository | Operation | Pull Request |"
  echo "| --- | --- | --- |"
  for line in "${lines[@]}"; do
    IFS='|' read -r repo op url <<< "$line"
    if [[ "$url" == http* ]]; then
      echo "| \`${repo}\` | ${op} | [${url}](${url}) |"
    else
      echo "| \`${repo}\` | ${op} | — |"
    fi
  done
} >> "$GITHUB_STEP_SUMMARY"
