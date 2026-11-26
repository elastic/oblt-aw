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

"""Tests for platform catalog-info Phase 2 bridge helpers."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_PATH = ROOT / "scripts" / "onboard_phase2_bridge.py"
PLATFORM_PATH = (
    ROOT
    / "platform"
    / "catalog-info"
    / ".github"
    / "scripts"
    / "oblt-aw-onboard-phase2-bridge"
    / "check_phase2.py"
)
SPEC = importlib.util.spec_from_file_location("onboard_phase2_bridge", SCRIPTS_PATH)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def test_platform_mirror_matches_scripts_copy() -> None:
    """catalog-info ships a byte-identical copy under platform/catalog-info/."""
    assert PLATFORM_PATH.read_bytes() == SCRIPTS_PATH.read_bytes()


def test_parse_related_issue_url() -> None:
    body = "Summary\n\nRelated issue: https://github.com/elastic/oblt-aw/issues/2584\n"
    assert mod.parse_related_issue_number(body) == 2584


def test_parse_related_issue_shorthand() -> None:
    body = "Related issue: elastic/oblt-aw#99\n"
    assert mod.parse_related_issue_number(body) == 99


def test_parse_related_issue_hash_only() -> None:
    body = "Related issue: #42\n"
    assert mod.parse_related_issue_number(body) == 42


def test_parse_related_issue_missing() -> None:
    assert mod.parse_related_issue_number("no link here") is None


def test_issue_repository_field() -> None:
    body = "### Repository\n\nelastic/example.repo\n\n### Organization key\n\nobs\n"
    assert mod.issue_repository_field(body) == "elastic/example.repo"


def test_extract_consumer_repo_from_title() -> None:
    title = "[oblt-aw][onboard] Add token policy for elastic/example.repo"
    assert mod.extract_consumer_repo(title) == "elastic/example.repo"


def test_check_phase2_box_checks_unchecked() -> None:
    body = "- [x] **Phase 1 — Catalog** — …\n- [ ] **Phase 2 — Remaining PRs** — …\n"
    new_body, changed = mod.check_phase2_box(body)
    assert changed is True
    assert "- [x] **Phase 2 — Remaining PRs**" in new_body


def test_check_phase2_box_idempotent_when_checked() -> None:
    body = "- [x] **Phase 2 — Remaining PRs** — …\n"
    new_body, changed = mod.check_phase2_box(body)
    assert changed is False
    assert new_body == body


def test_check_phase2_box_missing_raises() -> None:
    with pytest.raises(ValueError, match="Phase 2 checkbox"):
        mod.check_phase2_box("no phase triggers here")


def test_check_phase2_box_crlf() -> None:
    body = "- [ ] **Phase 2 — Remaining PRs** — …\r\n"
    new_body, changed = mod.check_phase2_box(body)
    assert changed is True
    assert "- [x] **Phase 2" in new_body
