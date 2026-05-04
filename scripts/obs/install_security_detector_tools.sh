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
# Installer script pinned to commit (v1.7.11 tag); bump SHA when upgrading actionlint.
ACTIONLINT_DOWNLOAD_SCRIPT_SHA=393031adb9afb225ee52ae2ccd7a5af5525e03e8
ACTIONLINT_VERSION=1.7.11
bash <(curl -fsSL "https://raw.githubusercontent.com/rhysd/actionlint/${ACTIONLINT_DOWNLOAD_SCRIPT_SHA}/scripts/download-actionlint.bash") "${ACTIONLINT_VERSION}"
echo "$HOME/bin/actionlint" >> "$GITHUB_PATH"
