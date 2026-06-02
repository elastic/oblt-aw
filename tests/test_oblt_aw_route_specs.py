"""Tests for scripts/oblt_aw_route_specs.py."""

from __future__ import annotations

import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts"))

from oblt_aw_route_specs import (  # noqa: E402
    default_workflow_file,
    load_ingress_route_job_ids,
    load_ingress_route_specs,
    max_job_permissions,
    parse_route_job_permissions,
    validate_all_org_registries,
    validate_docs_ingress_registry,
    validate_ingress_route_job_permissions,
    validate_obs_ingress_registry,
)


def _write_registry(
    tmp_path: pathlib.Path,
    workflows: list[dict],
    *,
    org_key: str = "obs",
    legacy_top_level: list[dict] | None = None,
) -> pathlib.Path:
    payload: dict = {"workflows": workflows}
    if legacy_top_level is not None:
        payload["ingress_routes"] = legacy_top_level
    org_dir = tmp_path / org_key
    org_dir.mkdir(parents=True, exist_ok=True)
    path = org_dir / "workflow-registry.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


class TestDefaultWorkflowFile:
    def test_obs_naming_contract(self) -> None:
        assert default_workflow_file("automerge", "obs") == "oblt-aw-automerge.yml"

    def test_docs_naming_contract(self) -> None:
        assert default_workflow_file("ai-menu", "docs") == "docs-aw-ai-menu.yml"


class TestLoadIngressRouteSpecs:
    def test_loads_nested_ingress_routes(self, tmp_path: pathlib.Path) -> None:
        path = _write_registry(
            tmp_path,
            [
                {
                    "id": "automerge",
                    "ingress_routes": [
                        {
                            "id": "automerge",
                            "allowed_bot_users_from": "allowed-pr",
                        }
                    ],
                },
                {
                    "id": "issue-triage",
                    "ingress_routes": [{"id": "issue-triage"}],
                },
            ],
        )
        specs = load_ingress_route_specs(path)
        assert specs["automerge"].allowed_bot_users_from == "allowed-pr"
        assert specs["automerge"].registry_workflow_id == "automerge"
        assert specs["issue-triage"].workflow_file == "oblt-aw-issue-triage.yml"

    def test_flattens_multiple_routes_under_one_registry_workflow(
        self, tmp_path: pathlib.Path
    ) -> None:
        path = _write_registry(
            tmp_path,
            [
                {
                    "id": "security",
                    "ingress_routes": [
                        {"id": "security-detector"},
                        {
                            "id": "security-triage",
                            "allowed_bot_users_from": "allowed-issue",
                        },
                    ],
                }
            ],
        )
        specs = load_ingress_route_specs(path)
        assert specs["security-detector"].registry_workflow_id == "security"
        assert specs["security-triage"].allowed_bot_users_from == "allowed-issue"

    def test_defaults_route_id_from_explicit_object(
        self, tmp_path: pathlib.Path
    ) -> None:
        path = _write_registry(
            tmp_path,
            [{"id": "autodoc", "ingress_routes": [{"id": "autodoc"}]}],
        )
        specs = load_ingress_route_specs(path)
        assert specs["autodoc"].workflow_file == "oblt-aw-autodoc.yml"
        assert specs["autodoc"].registry_workflow_id == "autodoc"

    def test_rejects_string_ingress_route_entries(self, tmp_path: pathlib.Path) -> None:
        path = _write_registry(
            tmp_path,
            [{"id": "autodoc", "ingress_routes": ["autodoc"]}],
        )
        with pytest.raises(SystemExit, match="must be an object"):
            load_ingress_route_specs(path)

    def test_rejects_missing_ingress_routes(self, tmp_path: pathlib.Path) -> None:
        path = _write_registry(tmp_path, [{"id": "autodoc"}])
        with pytest.raises(SystemExit, match="missing required 'ingress_routes'"):
            load_ingress_route_specs(path)

    def test_rejects_legacy_config_key(self, tmp_path: pathlib.Path) -> None:
        path = _write_registry(
            tmp_path,
            [{"id": "autodoc", "config": [{}]}],
        )
        with pytest.raises(
            SystemExit, match="rename deprecated 'config' to 'ingress_routes'"
        ):
            load_ingress_route_specs(path)

    def test_rejects_legacy_control_plane_workflows(
        self, tmp_path: pathlib.Path
    ) -> None:
        path = _write_registry(
            tmp_path,
            [
                {
                    "id": "autodoc",
                    "control_plane_workflows": ["oblt-aw-autodoc.yml"],
                }
            ],
        )
        with pytest.raises(SystemExit, match="control_plane_workflows"):
            load_ingress_route_specs(path)

    def test_rejects_top_level_ingress_routes(self, tmp_path: pathlib.Path) -> None:
        path = _write_registry(
            tmp_path,
            [{"id": "autodoc", "ingress_routes": [{"id": "autodoc"}]}],
            legacy_top_level=[{"id": "autodoc"}],
        )
        with pytest.raises(SystemExit, match="deprecated"):
            load_ingress_route_specs(path)

    def test_rejects_empty_ingress_routes_on_workflow(
        self, tmp_path: pathlib.Path
    ) -> None:
        path = _write_registry(tmp_path, [{"id": "autodoc", "ingress_routes": []}])
        with pytest.raises(SystemExit, match="non-empty array"):
            load_ingress_route_specs(path)


class TestIngressRoutePermissions:
    def test_max_job_permissions_unions_job_scopes(
        self, tmp_path: pathlib.Path
    ) -> None:
        workflow = tmp_path / "oblt-aw-sample.yml"
        workflow.write_text(
            "permissions:\n  contents: read\n\n"
            "jobs:\n"
            "  one:\n"
            "    permissions:\n"
            "      issues: read\n"
            "  two:\n"
            "    permissions:\n"
            "      issues: write\n"
            "      pull-requests: read\n",
            encoding="utf-8",
        )
        assert max_job_permissions(workflow) == {
            "issues": "write",
            "pull-requests": "read",
        }

    def test_parse_route_job_permissions(self, tmp_path: pathlib.Path) -> None:
        ingress = tmp_path / "ingress.yml"
        ingress.write_text(
            "jobs:\n"
            "  route-sample:\n"
            "    needs: prelude\n"
            "    permissions:\n"
            "      issues: write\n"
            "    uses: ./.github/workflows/oblt-aw-sample.yml\n",
            encoding="utf-8",
        )
        text = ingress.read_text(encoding="utf-8")
        assert parse_route_job_permissions(text, "sample") == {"issues": "write"}

    def test_validate_ingress_route_job_permissions_fails_when_missing(
        self, tmp_path: pathlib.Path
    ) -> None:
        workflows_dir = tmp_path / "workflows"
        workflows_dir.mkdir()
        (workflows_dir / "oblt-aw-sample.yml").write_text(
            "jobs:\n  run:\n    permissions:\n      issues: write\n",
            encoding="utf-8",
        )
        ingress = tmp_path / "oblt-aw-ingress.yml"
        ingress.write_text(
            "jobs:\n"
            "  route-sample:\n"
            "    needs: prelude\n"
            "    uses: ./.github/workflows/oblt-aw-sample.yml\n",
            encoding="utf-8",
        )
        specs = load_ingress_route_specs(
            _write_registry(
                tmp_path,
                [{"id": "sample", "ingress_routes": [{"id": "sample"}]}],
            )
        )
        with pytest.raises(SystemExit, match="missing job permissions"):
            validate_ingress_route_job_permissions(
                ingress,
                specs=specs,
                workflows_dir=workflows_dir,
            )


class TestLoadIngressRouteJobIds:
    def test_extracts_route_job_ids(self, tmp_path: pathlib.Path) -> None:
        ingress = tmp_path / "oblt-aw-ingress.yml"
        ingress.write_text(
            "jobs:\n"
            "  route-automerge:\n    uses: ./.github/workflows/oblt-aw-automerge.yml\n"
            "  route-issue-triage:\n    uses: ./.github/workflows/oblt-aw-issue-triage.yml\n",
            encoding="utf-8",
        )
        assert load_ingress_route_job_ids(ingress) == ["automerge", "issue-triage"]


class TestRepoRegistryValidation:
    def test_obs_registry_in_repo(self) -> None:
        repo_root = pathlib.Path(__file__).parent.parent
        validate_all_org_registries(repo_root / "config")

    def test_obs_registry_matches_ingress_jobs_and_workflow_files(self) -> None:
        repo_root = pathlib.Path(__file__).parent.parent
        validate_obs_ingress_registry(
            config_dir=repo_root / "config",
            workflows_dir=repo_root / ".github" / "workflows",
            ingress_path=repo_root / ".github" / "workflows" / "oblt-aw-ingress.yml",
        )

    def test_docs_registry_matches_ingress_jobs_and_workflow_files(self) -> None:
        repo_root = pathlib.Path(__file__).parent.parent
        validate_docs_ingress_registry(
            config_dir=repo_root / "config",
            workflows_dir=repo_root / ".github" / "workflows",
            ingress_path=repo_root / ".github" / "workflows" / "docs-aw-ingress.yml",
        )
