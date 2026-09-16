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

GH_AW_VERSION_FILE := .aw-compiler-version
GH_AW_VERSION := $(shell tr -d '[:space:]' < $(GH_AW_VERSION_FILE))
GH_AW_BIN := $(HOME)/.local/share/gh/extensions/gh-aw/gh-aw
GH_AW_WORKFLOW ?= gh-aw-estc-pr-buildkite-detective

.PHONY: update-license update-license-check compile-aw compile-aw-check

## Update license headers and NOTICE.txt
update-license:
	python3 scripts/update_license_files.py

## Verify license files; exit 1 if updates needed
update-license-check:
	python3 scripts/update_license_files.py --check

$(GH_AW_BIN):
	@expected="$(GH_AW_VERSION)"; \
	if [ -z "$$expected" ]; then \
		echo "error: $(GH_AW_VERSION_FILE) is empty or missing" >&2; \
		exit 1; \
	fi; \
	install_dir="$$(dirname "$(GH_AW_BIN)")"; \
	mkdir -p "$$install_dir"; \
	tmp_file="$$(mktemp)"; \
	trap 'rm -f "$$tmp_file"' EXIT; \
	curl -fsSL "https://raw.githubusercontent.com/github/gh-aw/refs/tags/$$expected/install-gh-aw.sh" -o "$$tmp_file"; \
	bash "$$tmp_file" "$$expected";

## Install the pinned gh aw compiler binary directly from the upstream release, without gh extension plumbing.
install-aw: $(GH_AW_BIN)

## Compile the selected gh-aw workflow source into its generated .lock.yml.
compile-aw: install-aw
	$(GH_AW_BIN) compile $(GH_AW_WORKFLOW)

## Recompile every gh-aw workflow and fail if the generated lock files drift from the source.
compile-aw-check: install-aw
	$(GH_AW_BIN) compile --purge
	git diff --exit-code -- .github/workflows
