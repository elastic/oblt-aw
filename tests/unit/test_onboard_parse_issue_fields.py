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

"""Tests for scripts/onboard_parse_issue_fields.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path

MODULE_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "scripts"
    / "onboard_parse_issue_fields.py"
)
SPEC = importlib.util.spec_from_file_location("onboard_parse_issue_fields", MODULE_PATH)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)

LF_BODY = """\
### Phase triggers

- [x] **Phase 1 — Catalog** — …
- [x] **Phase 2 — Remaining PRs** — …

### Repository

elastic/example-repo

### Organization key

obs
"""


def test_lf_body_parses_repo_org_and_phase2() -> None:
    fields = mod.parse_onboard_fields(LF_BODY)
    assert fields["repository"] == "elastic/example-repo"
    assert fields["org_key"] == "obs"
    assert fields["phase2_checked"] == 1
    assert fields["phase"] == 2


def test_crlf_blank_line_after_repository_heading() -> None:
    """Regression: CRLF blank line must not yield an empty repository."""
    body = (
        "### Repository\r\n"
        "\r\n"
        "elastic/example.repo\r\n"
        "\r\n"
        "### Organization key\r\n"
        "\r\n"
        "security\r\n"
        "- [ ] **Phase 2 — Remaining PRs**\r\n"
    )
    fields = mod.parse_onboard_fields(body)
    assert fields["repository"] == "elastic/example.repo"
    assert fields["org_key"] == "security"
    assert fields["phase2_checked"] == 0
    assert fields["phase"] == 1


def test_invalid_repo_cleared() -> None:
    body = "### Repository\n\nnot-a-repo\n\n### Organization key\n\ndocs\n"
    fields = mod.parse_onboard_fields(body)
    assert fields["repository"] == ""
    assert fields["org_key"] == "docs"
