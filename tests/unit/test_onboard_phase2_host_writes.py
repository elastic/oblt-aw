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

"""Lock regressions for Phase 2 host abort writes (outside DIFC)."""

from __future__ import annotations

from pathlib import Path

LOCK = (
    Path(__file__).resolve().parent.parent.parent
    / ".github"
    / "workflows"
    / "gh-aw-onboard-repository.lock.yml"
)


def test_phase2_gate_bypasses_difc_for_issue_writes() -> None:
    text = LOCK.read_text(encoding="utf-8")
    assert "gh_host_write()" in text
    assert 'GITHUB_API_URL="https://api.github.com"' in text
    assert "gh_host_write gh api" in text
    assert "onboard_phase1_catalog_ready.py" in text
    assert "onboard_parse_issue_fields.py" in text
