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

.PHONY: update-license update-license-check install-aw compile-aw

## Update license headers and NOTICE.txt
update-license:
	python3 scripts/update_license_files.py

## Verify license files; exit 1 if updates needed
update-license-check:
	python3 scripts/update_license_files.py --check

## Install or verify the pinned gh aw compiler version
install-aw:
	@expected="$(GH_AW_VERSION)"; \
	if [ -z "$$expected" ]; then \
		echo "error: $(GH_AW_VERSION_FILE) is empty or missing" >&2; \
		exit 1; \
	fi; \
	current="$$(gh aw version 2>&1 | grep -oE 'v[0-9]+\.[0-9]+\.[0-9]+([.-][0-9A-Za-z.-]+)?' | head -1 || true)"; \
	if [ "$$current" = "$$expected" ]; then \
		echo "gh aw $$expected already installed"; \
	else \
		echo "Installing gh aw $$expected (current: $${current:-none})..."; \
		gh extension remove gh-aw >/dev/null 2>&1 || true; \
		gh extension install github/gh-aw --pin "$$expected"; \
		installed="$$(gh aw version 2>&1 | awk '{print $$NF}' || true)"; \
		if [ "$$installed" != "$$expected" ]; then \
			echo "error: expected gh aw $$expected, got $${installed:-none}" >&2; \
			exit 1; \
		fi; \
		echo "gh aw $$expected installed"; \
	fi

## Compile agentic workflow Markdown into .lock.yml
compile-aw: install-aw
	gh aw compile
