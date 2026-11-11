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

from __future__ import annotations

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from repo_scheduled_instructions import (
    SCHEDULED_INSTRUCTIONS_DIR,
    evaluate_for_profile,
    matrix_payload,
)


def _write_instruction(
    repo: pathlib.Path,
    name: str,
    frontmatter: str,
    body: str = "Do the work and prefer noop when nothing is actionable.\n",
) -> None:
    path = repo / SCHEDULED_INSTRUCTIONS_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{frontmatter}\n---\n\n{body}", encoding="utf-8")


def test_no_directory_means_no_matches(tmp_path: pathlib.Path) -> None:
    result = evaluate_for_profile(tmp_path, "daily", env={})
    assert result.matching == []
    assert result.blocked == []
    assert result.errors == []


def test_profile_filter_and_matrix(tmp_path: pathlib.Path) -> None:
    _write_instruction(
        tmp_path,
        "build-errors.md",
        "schedule-profiles: [daily]\ncapabilities: []",
    )
    _write_instruction(
        tmp_path,
        "nudge.md",
        "id: merge-nudge\nschedule-profiles: [frequent]",
    )
    daily = evaluate_for_profile(tmp_path, "daily", env={})
    assert [a.automation_id for a in daily.matching] == ["build-errors"]
    frequent = evaluate_for_profile(tmp_path, "frequent", env={})
    assert [a.automation_id for a in frequent.matching] == ["merge-nudge"]
    payload = matrix_payload(daily.matching)
    assert payload["include"][0]["path"].endswith(
        ".github/ai/scheduled/build-errors.md"
    )


def test_weekly_profile(tmp_path: pathlib.Path) -> None:
    _write_instruction(
        tmp_path,
        "build-error-triage.md",
        "schedule-profiles: [weekly]\ncapabilities: [buildkite-logs]",
    )
    blocked = evaluate_for_profile(tmp_path, "weekly", env={})
    assert blocked.matching == []
    assert len(blocked.blocked) == 1
    assert "BUILDKITE_API_TOKEN" in blocked.blocked[0]["reason"]

    ok = evaluate_for_profile(tmp_path, "weekly", env={"BUILDKITE_API_TOKEN": "token"})
    assert [a.automation_id for a in ok.matching] == ["build-error-triage"]
    assert ok.blocked == []


def test_unknown_profile_in_frontmatter(tmp_path: pathlib.Path) -> None:
    _write_instruction(
        tmp_path,
        "bad.md",
        "schedule-profiles: [monthly]",
    )
    result = evaluate_for_profile(tmp_path, "daily", env={})
    assert result.matching == []
    assert result.errors
    assert "unknown schedule-profiles" in result.errors[0]


def test_unknown_capability(tmp_path: pathlib.Path) -> None:
    _write_instruction(
        tmp_path,
        "bad-cap.md",
        "schedule-profiles: [daily]\ncapabilities: [not-a-real-cap]",
    )
    result = evaluate_for_profile(tmp_path, "daily", env={})
    assert result.errors
    assert "unknown capabilities" in result.errors[0]


def test_empty_body_rejected(tmp_path: pathlib.Path) -> None:
    path = tmp_path / SCHEDULED_INSTRUCTIONS_DIR / "empty.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("---\nschedule-profiles: [daily]\n---\n\n", encoding="utf-8")
    result = evaluate_for_profile(tmp_path, "daily", env={})
    assert result.errors
    assert "empty" in result.errors[0]


def test_missing_frontmatter_rejected(tmp_path: pathlib.Path) -> None:
    path = tmp_path / SCHEDULED_INSTRUCTIONS_DIR / "plain.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("just text\n", encoding="utf-8")
    result = evaluate_for_profile(tmp_path, "daily", env={})
    assert result.errors
    assert "frontmatter" in result.errors[0]


def test_duplicate_ids(tmp_path: pathlib.Path) -> None:
    _write_instruction(
        tmp_path,
        "one.md",
        "id: shared\nschedule-profiles: [daily]",
    )
    _write_instruction(
        tmp_path,
        "two.md",
        "id: shared\nschedule-profiles: [daily]",
    )
    result = evaluate_for_profile(tmp_path, "daily", env={})
    assert any("duplicate automation id" in e for e in result.errors)


def test_unknown_wake_profile_raises(tmp_path: pathlib.Path) -> None:
    with pytest.raises(ValueError, match="unknown schedule-profile"):
        evaluate_for_profile(tmp_path, "hourly", env={})
