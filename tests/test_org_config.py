"""Tests for multi-org helpers in scripts/common.py."""

from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts"))

import common  # noqa: E402


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
