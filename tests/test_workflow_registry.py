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


class TestBuildControlPlaneWorkflowIndex:
    def test_maps_files_to_compound_ids(self, tmp_path: pathlib.Path) -> None:
        _write_org(
            tmp_path,
            "obs",
            [
                {
                    "id": "automerge",
                    "ingress_routes": [{"id": "automerge"}],
                },
                {
                    "id": "security",
                    "ingress_routes": [
                        {"id": "security-detector"},
                        {"id": "security-fixer"},
                    ],
                },
            ],
        )
        index = wr.build_control_plane_workflow_index(tmp_path)
        assert index["oblt-aw-automerge.yml"].compound_id == "obs:automerge"
        assert index["oblt-aw-security-fixer.yml"].compound_id == "obs:security"


class TestValidateRegistryAgainstWorkflows:
    def test_flags_missing_registry_entry(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_org(
            tmp_path,
            "obs",
            [{"id": "automerge", "ingress_routes": [{"id": "automerge"}]}],
        )
        workflows = tmp_path / "workflows"
        workflows.mkdir()
        (workflows / "oblt-aw-agent-suggestions.yml").write_text("", encoding="utf-8")
        errors = wr.validate_registry_against_workflows(
            tmp_path, workflows, {"oblt-aw-agent-suggestions.yml"}
        )
        assert any("not listed" in err for err in errors)
