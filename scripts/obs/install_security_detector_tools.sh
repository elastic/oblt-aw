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
ACTIONLINT_CHECKSUMS_SHA256=7d588eeb1ceb1e926b5618162a082453e1618b7772597e4ef8270e08777a8114
ACTIONLINT_RELEASE_BASE="https://github.com/rhysd/actionlint/releases/download/v${ACTIONLINT_VERSION}"
ACTIONLINT_TMP_DIR="$(mktemp -d "${RUNNER_TEMP:-$PWD}/actionlint.XXXXXXXXXX")"
cleanup_actionlint_tmp() {
  rm -rf "$ACTIONLINT_TMP_DIR"
}
trap cleanup_actionlint_tmp EXIT

curl -fsSL -o "$ACTIONLINT_TMP_DIR/$ACTIONLINT_CHECKSUMS" "$ACTIONLINT_RELEASE_BASE/$ACTIONLINT_CHECKSUMS"
printf '%s  %s\n' "$ACTIONLINT_CHECKSUMS_SHA256" "$ACTIONLINT_TMP_DIR/$ACTIONLINT_CHECKSUMS" | sha256sum -c -

curl -fsSL -o "$ACTIONLINT_TMP_DIR/$ACTIONLINT_ARCHIVE" "$ACTIONLINT_RELEASE_BASE/$ACTIONLINT_ARCHIVE"
if ! actionlint_checksum_line="$(grep -E "  ${ACTIONLINT_ARCHIVE}$" "$ACTIONLINT_TMP_DIR/$ACTIONLINT_CHECKSUMS")"; then
  echo "Checksum for $ACTIONLINT_ARCHIVE not found in $ACTIONLINT_CHECKSUMS" >&2
  exit 1
fi
printf '%s\n' "$actionlint_checksum_line" | (cd "$ACTIONLINT_TMP_DIR" && sha256sum -c -)
tar -xzf "$ACTIONLINT_TMP_DIR/$ACTIONLINT_ARCHIVE" -C "$HOME/bin/actionlint" actionlint
echo "$HOME/bin/actionlint" >> "$GITHUB_PATH"
