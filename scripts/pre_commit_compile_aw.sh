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

# Regenerates gh-aw lock files when sources are staged. Exit 1 when locks change
# so pre-commit re-stages them and re-runs (same pattern as format fixers).

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}"

make compile-aw

lock_status="$(
  git status --porcelain --untracked-files=all -- \
    ':(glob).github/workflows/*.lock.yml' \
    ':(glob).github/workflows/**/*.lock.yml' || true
)"

if [[ -n "${lock_status}" ]]; then
  echo "gh-aw lock files were regenerated from Markdown sources."
  echo "pre-commit will re-stage them; re-run the commit if needed."
  echo "${lock_status}"
  exit 1
fi
