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
ACTIONLINT_CHECKSUMS="actionlint_${ACTIONLINT_VERSION}_checksums.txt"
ACTIONLINT_CHECKSUM_ENTRY="${ACTIONLINT_ARCHIVE}.sha256"
ACTIONLINT_CHECKSUMS_SHA256="7d588eeb1ceb1e926b5618162a082453e1618b7772597e4ef8270e08777a8114"
ACTIONLINT_BASE_URL="https://github.com/rhysd/actionlint/releases/download/v${ACTIONLINT_VERSION}"

cleanup_actionlint_downloads() {
  rm -f "$ACTIONLINT_ARCHIVE" "$ACTIONLINT_CHECKSUMS" "$ACTIONLINT_CHECKSUM_ENTRY"
}
trap cleanup_actionlint_downloads EXIT

curl -fsSLO "${ACTIONLINT_BASE_URL}/${ACTIONLINT_ARCHIVE}"
curl -fsSLO "${ACTIONLINT_BASE_URL}/${ACTIONLINT_CHECKSUMS}"
echo "${ACTIONLINT_CHECKSUMS_SHA256}  ${ACTIONLINT_CHECKSUMS}" | sha256sum -c -
grep "  ${ACTIONLINT_ARCHIVE}$" "$ACTIONLINT_CHECKSUMS" > "$ACTIONLINT_CHECKSUM_ENTRY"
sha256sum -c "$ACTIONLINT_CHECKSUM_ENTRY"
tar xzf "$ACTIONLINT_ARCHIVE" actionlint
chmod 0755 actionlint
echo "$HOME/bin/actionlint" >> "$GITHUB_PATH"
