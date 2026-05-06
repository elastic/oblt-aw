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
ACTIONLINT_BASE_URL="https://github.com/rhysd/actionlint/releases/download/v${ACTIONLINT_VERSION}"
case "$(uname -m)" in
  x86_64 | amd64) ACTIONLINT_ARCH="amd64" ;;
  aarch64 | arm64) ACTIONLINT_ARCH="arm64" ;;
  *)
    echo "Unsupported architecture: $(uname -m)" >&2
    exit 1
    ;;
esac
ACTIONLINT_ARCHIVE="actionlint_${ACTIONLINT_VERSION}_linux_${ACTIONLINT_ARCH}.tar.gz"
curl -fsSLO "${ACTIONLINT_BASE_URL}/${ACTIONLINT_ARCHIVE}"
curl -fsSLO "${ACTIONLINT_BASE_URL}/checksums.txt"
grep " ${ACTIONLINT_ARCHIVE}\$" checksums.txt | sha256sum -c -
tar -xzf "${ACTIONLINT_ARCHIVE}"
rm -f "${ACTIONLINT_ARCHIVE}" checksums.txt
echo "$HOME/bin/actionlint" >> "$GITHUB_PATH"
