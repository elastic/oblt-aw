#!/usr/bin/env bash
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
