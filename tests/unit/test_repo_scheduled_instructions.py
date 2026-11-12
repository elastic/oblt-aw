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
import textwrap

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from repo_scheduled_instructions import (
    E2E_BAIT_AUTOMATION_ID,
    E2E_BAIT_PATH,
    E2E_REPO_SCHEDULED_MODE_TOKEN,
    additional_instructions_enable_e2e,
    build_materialized_instruction_markdown,
    evaluate_for_profile,
    gate_automations_by_capabilities,
    matrix_payload,
    resolve_e2e_bait_only,
)


def _write_file(repo: pathlib.Path, rel: str, content: str) -> pathlib.Path:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _write_apm(
    repo: pathlib.Path,
    automations: list[dict[str, object]],
) -> None:
    doc = {
        "name": "fixture",
        "version": "1.0.0",
        "dependencies": {"apm": [], "mcp": []},
        "x-oblt-aw": {
            "version": 1,
            "obs": {
                "common": {},
                "workflows": {
                    "repo-scheduled": {
                        "automations": automations,
                    }
                },
            },
        },
    }
    _write_file(repo, "apm.yml", yaml.safe_dump(doc, sort_keys=False))


def test_no_apm_means_no_matches(tmp_path: pathlib.Path) -> None:
    result = evaluate_for_profile(tmp_path, "daily", env={})
    assert result.matching == []
    assert result.blocked == []
    assert result.errors == []


def test_profile_filter_and_matrix_from_apm(tmp_path: pathlib.Path) -> None:
    _write_file(
        tmp_path,
        "docs/ai/build-errors.md",
        "---\nschedule-profiles: [daily]\n---\n\nDo the work.\n",
    )
    _write_file(
        tmp_path,
        "prompts/nudge.md",
        "---\nid: merge-nudge\nschedule-profiles: [frequent]\n---\n\nNudge.\n",
    )
    _write_apm(
        tmp_path,
        [
            {"instructions-file": "docs/ai/build-errors.md"},
            {"instructions-file": "prompts/nudge.md"},
        ],
    )
    daily = evaluate_for_profile(tmp_path, "daily", env={})
    assert [a.automation_id for a in daily.matching] == ["build-errors"]
    frequent = evaluate_for_profile(tmp_path, "frequent", env={})
    assert [a.automation_id for a in frequent.matching] == ["merge-nudge"]
    payload = matrix_payload(daily.matching)
    assert payload["include"][0]["path"] == "docs/ai/build-errors.md"


def test_apm_schedule_profiles_and_capabilities_override_frontmatter(
    tmp_path: pathlib.Path,
) -> None:
    _write_file(
        tmp_path,
        "ai/triage.md",
        textwrap.dedent(
            """\
            ---
            id: ignored-id
            schedule-profiles: [daily]
            capabilities: []
            ---

            Triage builds.
            """
        ),
    )
    _write_apm(
        tmp_path,
        [
            {
                "id": "build-error-triage",
                "instructions-file": "ai/triage.md",
                "schedule-profiles": ["weekly"],
                "capabilities": ["buildkite-logs"],
            }
        ],
    )
    blocked = evaluate_for_profile(tmp_path, "weekly", env={})
    assert blocked.matching == []
    assert len(blocked.blocked) == 1
    assert blocked.blocked[0]["id"] == "build-error-triage"

    ok = evaluate_for_profile(tmp_path, "weekly", env={"BUILDKITE_API_TOKEN": "token"})
    assert [a.automation_id for a in ok.matching] == ["build-error-triage"]
    assert ok.matching[0].capabilities == ("buildkite-logs",)
    # APM profiles win — daily frontmatter must not match.
    daily = evaluate_for_profile(
        tmp_path, "daily", env={"BUILDKITE_API_TOKEN": "token"}
    )
    assert daily.matching == []


def test_body_without_frontmatter_ok_when_apm_has_profiles(
    tmp_path: pathlib.Path,
) -> None:
    _write_file(tmp_path, "notes/plain.md", "Just do the scheduled work.\n")
    _write_apm(
        tmp_path,
        [
            {
                "id": "plain-job",
                "instructions-file": "notes/plain.md",
                "schedule-profiles": ["daily"],
            }
        ],
    )
    result = evaluate_for_profile(tmp_path, "daily", env={})
    assert [a.automation_id for a in result.matching] == ["plain-job"]
    assert result.errors == []


def test_missing_schedule_profiles_everywhere_fails(tmp_path: pathlib.Path) -> None:
    _write_file(tmp_path, "notes/plain.md", "Body only.\n")
    _write_apm(
        tmp_path,
        [{"instructions-file": "notes/plain.md"}],
    )
    result = evaluate_for_profile(tmp_path, "daily", env={})
    assert result.errors
    assert "schedule-profiles is required" in result.errors[0]


def test_unknown_profile_in_apm(tmp_path: pathlib.Path) -> None:
    _write_file(tmp_path, "x.md", "Body.\n")
    _write_apm(
        tmp_path,
        [
            {
                "instructions-file": "x.md",
                "schedule-profiles": ["monthly"],
            }
        ],
    )
    result = evaluate_for_profile(tmp_path, "daily", env={})
    assert result.errors
    assert "unknown schedule-profiles" in result.errors[0]


def test_unknown_capability_in_apm(tmp_path: pathlib.Path) -> None:
    _write_file(tmp_path, "x.md", "Body.\n")
    _write_apm(
        tmp_path,
        [
            {
                "instructions-file": "x.md",
                "schedule-profiles": ["daily"],
                "capabilities": ["not-a-real-cap"],
            }
        ],
    )
    result = evaluate_for_profile(tmp_path, "daily", env={})
    assert result.errors
    assert "unknown capabilities" in result.errors[0]


def test_empty_body_rejected(tmp_path: pathlib.Path) -> None:
    _write_file(tmp_path, "empty.md", "---\nschedule-profiles: [daily]\n---\n\n")
    _write_apm(tmp_path, [{"instructions-file": "empty.md"}])
    result = evaluate_for_profile(tmp_path, "daily", env={})
    assert result.errors
    assert "empty" in result.errors[0]


def test_missing_instructions_file_fails(tmp_path: pathlib.Path) -> None:
    _write_apm(
        tmp_path,
        [
            {
                "instructions-file": "missing.md",
                "schedule-profiles": ["daily"],
            }
        ],
    )
    result = evaluate_for_profile(tmp_path, "daily", env={})
    assert result.errors
    assert "not found" in result.errors[0]


def test_path_escape_rejected(tmp_path: pathlib.Path) -> None:
    _write_apm(
        tmp_path,
        [
            {
                "instructions-file": "../outside.md",
                "schedule-profiles": ["daily"],
            }
        ],
    )
    result = evaluate_for_profile(tmp_path, "daily", env={})
    assert result.errors
    assert ".." in result.errors[0]


def test_symlink_escape_rejected(tmp_path: pathlib.Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    outside = tmp_path / "outside.md"
    outside.write_text(
        "---\nschedule-profiles: [daily]\n---\n\nLeaked body.\n",
        encoding="utf-8",
    )
    link = repo / "link.md"
    link.symlink_to(outside)
    _write_apm(
        repo,
        [
            {
                "instructions-file": "link.md",
                "schedule-profiles": ["daily"],
            }
        ],
    )
    result = evaluate_for_profile(repo, "daily", env={})
    assert result.errors
    assert "escapes repository root" in result.errors[0]


def test_inline_instructions_from_apm(tmp_path: pathlib.Path) -> None:
    inline = "Nudge idle pull requests.\n"
    _write_apm(
        tmp_path,
        [
            {
                "id": "weekly-nudge",
                "schedule-profiles": ["weekly"],
                "instructions": inline,
            }
        ],
    )
    result = evaluate_for_profile(tmp_path, "weekly", env={})
    assert [a.automation_id for a in result.matching] == ["weekly-nudge"]
    assert result.matching[0].path == ""
    assert result.matching[0].instructions == inline
    payload = matrix_payload(result.matching)
    assert payload["include"][0]["instructions"] == inline
    assert payload["include"][0]["path"] == ""


def test_inline_preserves_body_thematic_breaks_after_frontmatter(
    tmp_path: pathlib.Path,
) -> None:
    inline = textwrap.dedent(
        """\
        ---
        schedule-profiles: [daily]
        ---

        ---
        keep-this-constraint: true
        ---

        Do the scheduled work.
        """
    )
    _write_apm(
        tmp_path,
        [
            {
                "id": "thematic-break-body",
                "instructions": inline,
            }
        ],
    )
    result = evaluate_for_profile(tmp_path, "daily", env={})
    assert [a.automation_id for a in result.matching] == ["thematic-break-body"]
    assert result.matching[0].instructions == inline
    assert "keep-this-constraint: true" in result.matching[0].instructions


def test_inline_requires_id(tmp_path: pathlib.Path) -> None:
    _write_apm(
        tmp_path,
        [
            {
                "schedule-profiles": ["daily"],
                "instructions": "Do the work.\n",
            }
        ],
    )
    result = evaluate_for_profile(tmp_path, "daily", env={})
    assert result.errors
    assert "id is required for inline" in result.errors[0]


def test_instructions_file_and_inline_both_rejected(tmp_path: pathlib.Path) -> None:
    _write_file(tmp_path, ".github/oblt-aw/scheduled/x.md", "Body.\n")
    _write_apm(
        tmp_path,
        [
            {
                "id": "both",
                "instructions-file": ".github/oblt-aw/scheduled/x.md",
                "instructions": "Also inline.\n",
                "schedule-profiles": ["daily"],
            }
        ],
    )
    result = evaluate_for_profile(tmp_path, "daily", env={})
    assert result.errors
    assert "not both" in result.errors[0]


def test_apm_yaml_only_discovers_automations(tmp_path: pathlib.Path) -> None:
    _write_file(
        tmp_path,
        "jobs/daily.md",
        "---\nschedule-profiles: [daily]\n---\n\nDo work.\n",
    )
    doc = {
        "name": "fixture",
        "version": "1.0.0",
        "dependencies": {"apm": [], "mcp": []},
        "x-oblt-aw": {
            "version": 1,
            "obs": {
                "common": {},
                "workflows": {
                    "repo-scheduled": {
                        "automations": [
                            {"instructions-file": "jobs/daily.md"},
                        ],
                    }
                },
            },
        },
    }
    _write_file(tmp_path, "apm.yaml", yaml.safe_dump(doc, sort_keys=False))
    result = evaluate_for_profile(tmp_path, "daily", env={})
    assert [a.automation_id for a in result.matching] == ["daily"]
    assert result.errors == []


def test_duplicate_ids(tmp_path: pathlib.Path) -> None:
    _write_file(tmp_path, "one.md", "Body one.\n")
    _write_file(tmp_path, "two.md", "Body two.\n")
    _write_apm(
        tmp_path,
        [
            {
                "id": "shared",
                "instructions-file": "one.md",
                "schedule-profiles": ["daily"],
            },
            {
                "id": "shared",
                "instructions-file": "two.md",
                "schedule-profiles": ["daily"],
            },
        ],
    )
    result = evaluate_for_profile(tmp_path, "daily", env={})
    assert any("duplicate automation id" in e for e in result.errors)


def test_unknown_wake_profile_raises(tmp_path: pathlib.Path) -> None:
    with pytest.raises(ValueError, match="unknown schedule-profile"):
        evaluate_for_profile(tmp_path, "hourly", env={})


def test_resolve_e2e_bait_injects_without_apm(tmp_path: pathlib.Path) -> None:
    _write_file(
        tmp_path,
        E2E_BAIT_PATH,
        textwrap.dedent(
            f"""\
            ---
            id: {E2E_BAIT_AUTOMATION_ID}
            schedule-profiles: [daily]
            ---

            <!-- E2E_REPO_SCHEDULED_BAIT_MARKER -->

            E2E bait body.
            """
        ),
    )
    resolved = resolve_e2e_bait_only(tmp_path, [], schedule_profile="daily")
    assert len(resolved) == 1
    assert resolved[0].automation_id == E2E_BAIT_AUTOMATION_ID
    assert resolved[0].path == E2E_BAIT_PATH


def test_resolve_e2e_bait_requires_profile_match(tmp_path: pathlib.Path) -> None:
    _write_file(
        tmp_path,
        E2E_BAIT_PATH,
        textwrap.dedent(
            f"""\
            ---
            id: {E2E_BAIT_AUTOMATION_ID}
            schedule-profiles: [daily]
            ---

            <!-- E2E_REPO_SCHEDULED_BAIT_MARKER -->

            E2E bait body.
            """
        ),
    )
    with pytest.raises(ValueError, match="does not include schedule-profile"):
        resolve_e2e_bait_only(tmp_path, [], schedule_profile="weekly")


def test_injected_bait_blocked_without_capability_secret(
    tmp_path: pathlib.Path,
) -> None:
    _write_file(
        tmp_path,
        E2E_BAIT_PATH,
        textwrap.dedent(
            f"""\
            ---
            id: {E2E_BAIT_AUTOMATION_ID}
            schedule-profiles: [daily]
            capabilities: [buildkite-logs]
            ---

            <!-- E2E_REPO_SCHEDULED_BAIT_MARKER -->

            E2E bait body.
            """
        ),
    )
    resolved = resolve_e2e_bait_only(tmp_path, [], schedule_profile="daily")
    matching, blocked = gate_automations_by_capabilities(resolved, env={})
    assert matching == []
    assert len(blocked) == 1
    assert blocked[0]["id"] == E2E_BAIT_AUTOMATION_ID
    assert "buildkite-logs" in blocked[0]["missing-capabilities"]


def test_additional_instructions_enable_e2e() -> None:
    assert additional_instructions_enable_e2e(
        f"{E2E_REPO_SCHEDULED_MODE_TOKEN}. Create issue."
    )
    assert not additional_instructions_enable_e2e(
        "Prefer noop when nothing is actionable."
    )


def test_build_materialized_instruction_markdown_prepends_e2e_block() -> None:
    text = build_materialized_instruction_markdown(
        automation_id=E2E_BAIT_AUTOMATION_ID,
        source_label=E2E_BAIT_PATH,
        body="## E2E wakes\n\nCreate one issue.\n",
        additional_instructions=(
            f"{E2E_REPO_SCHEDULED_MODE_TOKEN}. "
            "Create exactly one GitHub issue. Do not noop."
        ),
    )
    assert "## Platform E2E wake (authoritative)" in text
    assert E2E_REPO_SCHEDULED_MODE_TOKEN in text
    assert "Do not call `noop`" in text
    assert "## E2E wakes" in text
    # Flag appears before consumer body so source-of-truth cannot miss it.
    assert text.index(E2E_REPO_SCHEDULED_MODE_TOKEN) < text.index("## E2E wakes")


def test_build_materialized_instruction_markdown_skips_e2e_without_flag() -> None:
    text = build_materialized_instruction_markdown(
        automation_id="docs-patrol",
        source_label="apm.yml#instructions",
        body="Prefer noop.\n",
        additional_instructions="Prefer noop when nothing is actionable.",
    )
    assert "## Platform E2E wake" not in text
    assert E2E_REPO_SCHEDULED_MODE_TOKEN not in text
    assert "Prefer noop." in text
