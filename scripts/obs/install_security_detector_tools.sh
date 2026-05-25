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

# Install apt packages, Python tools, and actionlint for gh-aw-security-detector.
set -euo pipefail

sudo apt-get update -qq
sudo apt-get install -y shellcheck jq curl python3-pip
python3 -m pip install --user 'zizmor==1.23.1' 'semgrep==1.60.0'
echo "$HOME/.local/bin" >> "$GITHUB_PATH"
mkdir -p "$HOME/bin/actionlint"
cd "$HOME/bin/actionlint"
ACTIONLINT_VERSION=1.7.11
ACTIONLINT_ARCHIVE="actionlint_${ACTIONLINT_VERSION}_linux_amd64.tar.gz"
ACTIONLINT_RELEASE_BASE_URL="https://github.com/rhysd/actionlint/releases/download/v${ACTIONLINT_VERSION}"
curl -fsSLO "${ACTIONLINT_RELEASE_BASE_URL}/${ACTIONLINT_ARCHIVE}"
curl -fsSLO "${ACTIONLINT_RELEASE_BASE_URL}/checksums.txt"
if ! grep -E "[[:space:]]${ACTIONLINT_ARCHIVE}$" checksums.txt > checksums.actionlint.txt; then
  echo "Missing checksum entry for ${ACTIONLINT_ARCHIVE} in checksums.txt" >&2
  exit 1
fi
sha256sum -c checksums.actionlint.txt
tar -xzf "${ACTIONLINT_ARCHIVE}"
chmod +x actionlint
echo "$HOME/bin/actionlint" >> "$GITHUB_PATH"
