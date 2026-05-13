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
ACTIONLINT_ARCH="$(uname -m)"
case "$ACTIONLINT_ARCH" in
  x86_64) ACTIONLINT_PLATFORM=linux_amd64 ;;
  aarch64|arm64) ACTIONLINT_PLATFORM=linux_arm64 ;;
  *)
    echo "Unsupported architecture for actionlint: ${ACTIONLINT_ARCH}" >&2
    exit 1
    ;;
esac

ACTIONLINT_TARBALL="actionlint_${ACTIONLINT_VERSION}_${ACTIONLINT_PLATFORM}.tar.gz"
ACTIONLINT_URL="https://github.com/rhysd/actionlint/releases/download/v${ACTIONLINT_VERSION}/${ACTIONLINT_TARBALL}"
case "$ACTIONLINT_PLATFORM" in
  linux_amd64) ACTIONLINT_SHA256="900919a84f2229bac68ca9cd4103ea297abc35e9689ebb842c6e34a3d1b01b0a" ;;
  linux_arm64) ACTIONLINT_SHA256="21bc0dfb57a913fe175298c2a9e906ee630f747cb66d0a934d0d4b69f4ee1235" ;;
esac

curl -fsSLo "${ACTIONLINT_TARBALL}" "${ACTIONLINT_URL}"
echo "${ACTIONLINT_SHA256}  ${ACTIONLINT_TARBALL}" | sha256sum -c -
tar -xzf "${ACTIONLINT_TARBALL}" actionlint
install -m 0755 actionlint "$HOME/bin/actionlint/actionlint"
rm -f "${ACTIONLINT_TARBALL}" actionlint
echo "$HOME/bin/actionlint" >> "$GITHUB_PATH"
