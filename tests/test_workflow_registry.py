"""Tests for scripts/workflow_registry.py."""

from __future__ import annotations

import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts"))

import workflow_registry as wr  # noqa: E402


def _write_org(
    config_dir: pathlib.Path,
    org_key: str,
    workflows: list[dict],
    repos: list[str] | None = None,
) -> None:
    org_dir = config_dir / org_key
    org_dir.mkdir(parents=True)
    (org_dir / "workflow-registry.json").write_text(
        json.dumps({"workflows": workflows}),
        encoding="utf-8",
    )
    (org_dir / "active-repositories.json").write_text(
        json.dumps({"repositories": repos or []}),
        encoding="utf-8",
    )


class TestResolveCompoundId:
    def test_single_file_entry(self, tmp_path: pathlib.Path) -> None:
        _write_org(
            tmp_path,
            "obs",
            [
                {
                    "id": "automerge",
                    "control_plane_workflows": ["oblt-aw-automerge.yml"],
                }
            ],
        )
        assert (
            wr.resolve_compound_id(tmp_path, "oblt-aw-automerge.yml") == "obs:automerge"
        )

    def test_multi_file_entry(self, tmp_path: pathlib.Path) -> None:
        _write_org(
            tmp_path,
            "obs",
            [
                {
                    "id": "security",
                    "control_plane_workflows": [
                        "oblt-aw-security-detector.yml",
                        "oblt-aw-security-fixer.yml",
                    ],
                }
            ],
        )
        assert (
            wr.resolve_compound_id(tmp_path, "oblt-aw-security-fixer.yml")
            == "obs:security"
        )

    def test_unknown_file_raises(self, tmp_path: pathlib.Path) -> None:
        _write_org(
            tmp_path,
            "obs",
            [{"id": "automerge", "control_plane_workflows": ["oblt-aw-automerge.yml"]}],
        )
        with pytest.raises(ValueError, match="not listed"):
            wr.resolve_compound_id(tmp_path, "oblt-aw-missing.yml")


class TestValidateRegistryAgainstWorkflows:
    def test_flags_missing_registry_entry(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_org(
            tmp_path,
            "obs",
            [{"id": "automerge", "control_plane_workflows": ["oblt-aw-automerge.yml"]}],
        )
        workflows = tmp_path / "workflows"
        workflows.mkdir()
        (workflows / "oblt-aw-agent-suggestions.yml").write_text("", encoding="utf-8")
        errors = wr.validate_registry_against_workflows(
            tmp_path, workflows, {"oblt-aw-agent-suggestions.yml"}
        )
        assert any("not listed" in err for err in errors)
