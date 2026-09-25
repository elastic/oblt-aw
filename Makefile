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

GH_AW_VERSION := $(shell tr -d '[:space:]' < .aw-compiler-version)
GH_AW_BIN := $(HOME)/.local/share/gh/extensions/gh-aw/gh-aw

.PHONY: update-license update-license-check compile-aw compile-aw-check install-aw

## Update license headers and NOTICE.txt
update-license:
	python3 scripts/update_license_files.py

## Verify license files; exit 1 if updates needed
update-license-check:
	python3 scripts/update_license_files.py --check

## Install the pinned gh aw compiler binary directly from the upstream release, without gh extension plumbing.
install-aw:
	curl -fsSL "https://raw.githubusercontent.com/github/gh-aw/refs/tags/$(GH_AW_VERSION)/install-gh-aw.sh" | bash -s -- "$(GH_AW_VERSION)";

## Compile the gh-aw workflows source into its generated .lock.yml.
compile-aw: install-aw
	$(GH_AW_BIN) compile --purge
	python3 scripts/wire_ephemeral_token.py

## Recompile every gh-aw workflow and fail if the generated lock files drift from the source.
compile-aw-check: install-aw compile-aw
	test -z "$$(git status --porcelain --untracked-files=all -- ':(glob).github/workflows/*.lock.yml' ':(glob).github/workflows/**/*.lock.yml')"
