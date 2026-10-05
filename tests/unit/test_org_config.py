"""Tests for multi-org helpers in scripts/common.py."""

from __future__ import annotations

import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "scripts"))

import common


class TestDiscoverOrgConfigDirs:
    def test_finds_obs_and_docs(self, tmp_path: pathlib.Path) -> None:
        for org, repos in (
            ("obs", ["elastic/a"]),
            ("docs", []),
        ):
            (tmp_path / org).mkdir(parents=True)
            (tmp_path / org / "workflow-registry.json").write_text(
                json.dumps({"workflows": []}), encoding="utf-8"
            )
            (tmp_path / org / "active-repositories.json").write_text(
                json.dumps({"repositories": repos}), encoding="utf-8"
            )
        (tmp_path / "schema").mkdir()
        keys = common.discover_org_keys_sorted(tmp_path)
        assert keys == ["docs", "obs"]

    def test_skips_reserved_schema(self, tmp_path: pathlib.Path) -> None:
        (tmp_path / "schema").mkdir()
        (tmp_path / "schema" / "workflow-registry.json").write_text(
            "{}", encoding="utf-8"
        )
        (tmp_path / "schema" / "active-repositories.json").write_text(
            '{"repositories":[]}', encoding="utf-8"
        )
        (tmp_path / "obs").mkdir()
        (tmp_path / "obs" / "workflow-registry.json").write_text(
            '{"workflows":[]}', encoding="utf-8"
        )
        (tmp_path / "obs" / "active-repositories.json").write_text(
            '{"repositories":[]}', encoding="utf-8"
        )
        assert common.discover_org_keys_sorted(tmp_path) == ["obs"]


class TestMergeActiveRepositories:
    def test_unions_org_files_only_ignores_root_active_repositories(
        self, tmp_path: pathlib.Path
    ) -> None:
        (tmp_path / "obs").mkdir()
        (tmp_path / "obs" / "workflow-registry.json").write_text(
            '{"workflows":[]}', encoding="utf-8"
        )
        (tmp_path / "obs" / "active-repositories.json").write_text(
            json.dumps({"repositories": ["elastic/from-obs"]}), encoding="utf-8"
        )
        (tmp_path / "active-repositories.json").write_text(
            json.dumps({"repositories": ["elastic/from-legacy"]}), encoding="utf-8"
        )
        merged = common.merge_active_repositories_from_org_trees(tmp_path)
        assert merged == ["elastic/from-obs"]

    def test_merge_token_policies_detects_cross_org_conflict(
        self, tmp_path: pathlib.Path
    ) -> None:
        for org, policy in (
            ("obs", "token-policy-obs"),
            ("docs", "token-policy-docs"),
        ):
            (tmp_path / org).mkdir()
            (tmp_path / org / "workflow-registry.json").write_text(
                json.dumps({"workflows": []}), encoding="utf-8"
            )
            (tmp_path / org / "active-repositories.json").write_text(
                json.dumps(
                    {
                        "repositories": [
                            {
                                "repository": "elastic/shared",
                                "pin-class": "production",
                                "workflow-token-policy": policy,
                                "ai-assets-token-policy": "",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
        with pytest.raises(SystemExit, match="Conflicting workflow-token-policy"):
            common.merge_repository_workflow_token_policies_from_org_trees(tmp_path)


class TestPinClass:
    def test_object_requires_pin_class(self) -> None:
        content = json.dumps({"repositories": [{"repository": "elastic/foo"}]})
        with pytest.raises(SystemExit, match="pin-class"):
            common.parse_active_repository_entries(content)

    def test_oblt_aw_production_fails(self) -> None:
        content = json.dumps(
            {
                "repositories": [
                    {
                        "repository": "elastic/oblt-aw",
                        "pin-class": "production",
                        "workflow-token-policy": "",
                        "ai-assets-token-policy": "",
                    }
                ]
            }
        )
        with pytest.raises(SystemExit, match="must use pin-class"):
            common.parse_active_repository_entries(content)

    def test_oblt_aw_string_entry_fails(self) -> None:
        with pytest.raises(SystemExit, match="object entry"):
            common.parse_active_repository_entries(json.dumps(["elastic/oblt-aw"]))

    def test_missing_oblt_aw_fails_committed_validator(
        self, tmp_path: pathlib.Path
    ) -> None:
        (tmp_path / "obs").mkdir()
        (tmp_path / "obs" / "workflow-registry.json").write_text(
            '{"workflows":[]}', encoding="utf-8"
        )
        (tmp_path / "obs" / "active-repositories.json").write_text(
            json.dumps(
                {
                    "repositories": [
                        {
                            "repository": "elastic/foo",
                            "pin-class": "production",
                            "workflow-token-policy": "",
                            "ai-assets-token-policy": "",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        with pytest.raises(SystemExit, match="must be listed"):
            common.validate_committed_control_plane_pin_class(tmp_path)

    def test_committed_lists_classify_oblt_aw_development(self) -> None:
        config_dir = pathlib.Path(__file__).resolve().parents[2] / "config"
        common.validate_committed_control_plane_pin_class(config_dir)
        classes = common.merge_repository_pin_classes_from_org_trees(config_dir)
        assert classes["elastic/oblt-aw"] == common.PIN_CLASS_DEVELOPMENT
        assert classes["elastic/opentelemetry"] == common.PIN_CLASS_PRODUCTION


class TestEnabledCompoundIdsFromBody:
    def test_three_part_and_legacy(self) -> None:
        body = """
- [x] <!-- oblt-aw:docs:example-workflow --> Ex
- [x] <!-- oblt-aw:automerge --> Am
"""
        assert common.enabled_compound_ids_from_dashboard_body(body) == [
            "docs:example-workflow",
            "obs:automerge",
        ]
