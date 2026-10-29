"""Tests for scripts/workflow_registry.py."""

from __future__ import annotations

import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "scripts"))

import workflow_registry as wr


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
                    "inner_workflows": ["obs-aw-automerge.yml"],
                }
            ],
        )
        assert (
            wr.resolve_compound_id(tmp_path, "obs-aw-automerge.yml") == "obs:automerge"
        )

    def test_multi_file_entry(self, tmp_path: pathlib.Path) -> None:
        _write_org(
            tmp_path,
            "obs",
            [
                {
                    "id": "security",
                    "inner_workflows": [
                        "obs-aw-security-triage.yml",
                        "obs-aw-security-fixer.yml",
                    ],
                    "sub_features": [
                        {
                            "id": "injection",
                            "inner_workflows": [
                                "obs-aw-security-injection-detector.yml"
                            ],
                        }
                    ],
                }
            ],
        )
        assert (
            wr.resolve_compound_id(tmp_path, "obs-aw-security-fixer.yml")
            == "obs:security"
        )
        assert (
            wr.resolve_compound_id(tmp_path, "obs-aw-security-injection-detector.yml")
            == "obs:security:injection"
        )

    def test_unknown_file_raises(self, tmp_path: pathlib.Path) -> None:
        _write_org(
            tmp_path,
            "obs",
            [{"id": "automerge", "inner_workflows": ["obs-aw-automerge.yml"]}],
        )
        with pytest.raises(ValueError, match="not listed"):
            wr.resolve_compound_id(tmp_path, "obs-aw-missing.yml")

    def test_sub_feature_file_resolves_to_three_part_id(
        self, tmp_path: pathlib.Path
    ) -> None:
        _write_org(
            tmp_path,
            "obs",
            [
                {
                    "id": "security",
                    "inner_workflows": ["obs-aw-security-triage.yml"],
                    "sub_features": [
                        {
                            "id": "injection",
                            "inner_workflows": [
                                "obs-aw-security-injection-detector.yml"
                            ],
                        }
                    ],
                }
            ],
        )
        assert (
            wr.resolve_compound_id(tmp_path, "obs-aw-security-injection-detector.yml")
            == "obs:security:injection"
        )

    def test_rejects_duplicate_parent_and_sub_feature_files(
        self, tmp_path: pathlib.Path
    ) -> None:
        _write_org(
            tmp_path,
            "obs",
            [
                {
                    "id": "security",
                    "inner_workflows": ["obs-aw-security-detector.yml"],
                    "sub_features": [
                        {
                            "id": "injection",
                            "inner_workflows": ["obs-aw-security-detector.yml"],
                        }
                    ],
                }
            ],
        )
        with pytest.raises(ValueError, match="also assigned to the parent"):
            wr.build_control_plane_workflow_index(tmp_path)


class TestValidateRegistryAgainstWorkflows:
    def test_flags_missing_registry_entry(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_org(
            tmp_path,
            "obs",
            [{"id": "automerge", "inner_workflows": ["obs-aw-automerge.yml"]}],
        )
        workflows = tmp_path / "workflows"
        workflows.mkdir()
        (workflows / "obs-aw-agent-suggestions.yml").write_text("", encoding="utf-8")
        errors = wr.validate_registry_against_workflows(
            tmp_path, workflows, {"obs-aw-agent-suggestions.yml"}
        )
        assert any("not listed" in err for err in errors)


class TestValidateAutomergeSubFeatures:
    def test_checked_in_obs_automerge_sub_features_match_collections(self) -> None:
        config_dir = pathlib.Path(__file__).parent.parent.parent / "config"
        entries = wr.parse_registry_entries(config_dir / "obs", config_dir)
        wr.validate_automerge_sub_features(config_dir, entries)


class TestCommonServicesInclude:
    def test_shared_basename_allowed_across_orgs(self, tmp_path: pathlib.Path) -> None:
        common = tmp_path / "common"
        common.mkdir()
        (common / "services.json").write_text(
            json.dumps(
                {
                    "services": [
                        {
                            "id": "dependency-review",
                            "name": "Dependency Review",
                            "inner_workflows": ["obs-aw-dependency-review.yml"],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        for org in ("docs", "obs"):
            _write_org(
                tmp_path,
                org,
                [],
            )
            registry = {
                "include_common": ["dependency-review"],
                "workflows": [],
            }
            (tmp_path / org / "workflow-registry.json").write_text(
                json.dumps(registry), encoding="utf-8"
            )

        index = wr.build_control_plane_workflow_index(tmp_path)
        entries = index["obs-aw-dependency-review.yml"]
        assert {e.compound_id for e in entries} == {
            "docs:dependency-review",
            "obs:dependency-review",
        }
        assert (
            wr.resolve_compound_id(tmp_path, "obs-aw-dependency-review.yml")
            == "obs:dependency-review"
        )
        assert (
            wr.resolve_compound_id(
                tmp_path, "obs-aw-dependency-review.yml", org_key="docs"
            )
            == "docs:dependency-review"
        )

    def test_conflicting_workflow_ids_still_fail(self, tmp_path: pathlib.Path) -> None:
        _write_org(
            tmp_path,
            "obs",
            [
                {
                    "id": "dependency-review",
                    "inner_workflows": ["obs-aw-dependency-review.yml"],
                }
            ],
        )
        _write_org(
            tmp_path,
            "docs",
            [
                {
                    "id": "other",
                    "inner_workflows": ["obs-aw-dependency-review.yml"],
                }
            ],
        )
        with pytest.raises(ValueError, match="listed under both"):
            wr.build_control_plane_workflow_index(tmp_path)

    def test_checked_in_common_pilot_services(self) -> None:
        config_dir = pathlib.Path(__file__).parent.parent.parent / "config"
        common = wr.load_common_services(config_dir)
        assert set(common) >= {"automerge", "dependency-review"}
        index = wr.build_control_plane_workflow_index(config_dir)
        dr = index["obs-aw-dependency-review.yml"]
        assert {e.org_key for e in dr} == {"obs"}
        assert wr.resolve_compound_id(config_dir, "obs-aw-dependency-review.yml") == (
            "obs:dependency-review"
        )
        obs_ids = {
            entry.workflow_id
            for entry in wr.parse_registry_entries(config_dir / "obs", config_dir)
        }
        assert "automerge" in obs_ids
        assert "dependency-review" in obs_ids
