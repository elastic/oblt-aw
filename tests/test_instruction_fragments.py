"""Unit tests for scripts/instruction_fragments.py and resolver composition."""

from __future__ import annotations

import json
import pathlib
import sys

import pytest

_root = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(_root / "scripts"))

import agentic_assets_resolver as resolver
import instruction_fragments as ifr


@pytest.fixture
def config_dir(tmp_path: pathlib.Path) -> pathlib.Path:
    org = tmp_path / "obs"
    fragments = org / "instruction-fragments"
    fragments.mkdir(parents=True)
    (fragments / "common-a.md").write_text("COMMON_A", encoding="utf-8")
    (fragments / "wf-b.md").write_text("WF_B", encoding="utf-8")
    (fragments / "inner-c.md").write_text("INNER_C", encoding="utf-8")
    (org / "instruction-fragment-map.json").write_text(
        json.dumps(
            {
                "common": ["common-a"],
                "workflows": {
                    "issue-fixer": {
                        "fragments": ["wf-b"],
                    },
                    "security": {
                        "fragments": [],
                        "inner-workflows": {
                            "obs-aw-security-fixer.yml": {
                                "fragments": ["inner-c"],
                            }
                        },
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    (org / "workflow-registry.json").write_text(
        json.dumps(
            {
                "workflows": [
                    {
                        "id": "issue-fixer",
                        "inner_workflows": ["obs-aw-issue-fixer.yml"],
                    },
                    {
                        "id": "security",
                        "inner_workflows": [
                            "obs-aw-security-fixer.yml",
                            "obs-aw-security-triage.yml",
                        ],
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    return tmp_path


class TestInstructionFragments:
    def test_absent_map_is_noop(self, tmp_path: pathlib.Path) -> None:
        text, layers = ifr.compose_control_plane_fragments(
            config_dir=tmp_path,
            org_key="obs",
            workflow_id="issue-fixer",
            control_plane_workflow="obs-aw-issue-fixer.yml",
        )
        assert text == ""
        assert all(layer["ids"] == [] for layer in layers)

    def test_append_common_then_workflow(self, config_dir: pathlib.Path) -> None:
        text, layers = ifr.compose_control_plane_fragments(
            config_dir=config_dir,
            org_key="obs",
            workflow_id="issue-fixer",
            control_plane_workflow="obs-aw-issue-fixer.yml",
        )
        assert text == "COMMON_A\n\nWF_B"
        by_name = {layer["layer"]: layer for layer in layers}
        assert by_name["control-plane-common"]["ids"] == ["common-a"]
        assert by_name["control-plane-workflow"]["ids"] == ["wf-b"]
        assert by_name["control-plane-inner-workflow"]["ids"] == []

    def test_inner_workflow_appended(self, config_dir: pathlib.Path) -> None:
        text, layers = ifr.compose_control_plane_fragments(
            config_dir=config_dir,
            org_key="obs",
            workflow_id="security",
            control_plane_workflow="obs-aw-security-fixer.yml",
        )
        assert text == "COMMON_A\n\nINNER_C"
        by_name = {layer["layer"]: layer for layer in layers}
        assert by_name["control-plane-inner-workflow"]["ids"] == ["inner-c"]

    def test_triage_does_not_get_fixer_inner(self, config_dir: pathlib.Path) -> None:
        text, layers = ifr.compose_control_plane_fragments(
            config_dir=config_dir,
            org_key="obs",
            workflow_id="security",
            control_plane_workflow="obs-aw-security-triage.yml",
        )
        assert text == "COMMON_A"
        by_name = {layer["layer"]: layer for layer in layers}
        assert by_name["control-plane-inner-workflow"]["ids"] == []

    def test_unknown_fragment_id_fails(self, config_dir: pathlib.Path) -> None:
        org = config_dir / "obs"
        (org / "instruction-fragment-map.json").write_text(
            json.dumps({"common": ["missing-frag"], "workflows": {}}),
            encoding="utf-8",
        )
        with pytest.raises(FileNotFoundError, match="missing-frag"):
            ifr.compose_control_plane_fragments(
                config_dir=config_dir,
                org_key="obs",
                workflow_id="issue-fixer",
            )


class TestResolverWithFragments:
    def test_layers_expose_appended_fragments(
        self, tmp_path: pathlib.Path, config_dir: pathlib.Path
    ) -> None:
        resolved = resolver.resolve_agentic_assets(
            repo_root=tmp_path,
            workflow_id="issue-fixer",
            org_key="obs",
            platform_additional_instructions="PLATFORM_INLINE",
            config_dir=config_dir,
            control_plane_workflow="obs-aw-issue-fixer.yml",
        )
        text = resolved["additional_instructions"]
        assert text.index("COMMON_A") < text.index("WF_B")
        assert text.index("WF_B") < text.index("PLATFORM_INLINE")

        meta = resolved["instruction_layers"]
        assert meta["org-key"] == "obs"
        assert meta["workflow-id"] == "issue-fixer"
        assert meta["control-plane-workflow"] == "obs-aw-issue-fixer.yml"
        by_name = {layer["layer"]: layer for layer in meta["layers"]}
        assert by_name["control-plane-common"]["ids"] == ["common-a"]
        assert by_name["control-plane-workflow"]["ids"] == ["wf-b"]
        assert by_name["platform-inline"]["present"] is True

    def test_repo_map_pilot_issue_fixer(self, tmp_path: pathlib.Path) -> None:
        config_dir = _root / "config"
        resolved = resolver.resolve_agentic_assets(
            repo_root=tmp_path,
            workflow_id="issue-fixer",
            org_key="obs",
            config_dir=config_dir,
            control_plane_workflow="obs-aw-issue-fixer.yml",
        )
        text = resolved["additional_instructions"]
        assert "/ai implement" in text
        assert "elastic/observablt-ci" in text
        assert "Do not merge automatically" in text
        ids = []
        for layer in resolved["instruction_layers"]["layers"]:
            if layer.get("kind") == "fragment":
                ids.extend(layer.get("ids") or [])
        assert "issue-fixer-preamble" in ids
        assert "obs-merge-policy" in ids

    def test_repo_map_security_fixer_not_triage(self, tmp_path: pathlib.Path) -> None:
        config_dir = _root / "config"
        fixer = resolver.resolve_agentic_assets(
            repo_root=tmp_path,
            workflow_id="security",
            org_key="obs",
            config_dir=config_dir,
            control_plane_workflow="obs-aw-security-fixer.yml",
        )
        triage = resolver.resolve_agentic_assets(
            repo_root=tmp_path,
            workflow_id="security",
            org_key="obs",
            config_dir=config_dir,
            control_plane_workflow="obs-aw-security-triage.yml",
        )
        assert "Least-privilege (MANDATORY)" in fixer["additional_instructions"]
        assert "Least-privilege (MANDATORY)" not in triage["additional_instructions"]
        assert triage["additional_instructions"] == ""
