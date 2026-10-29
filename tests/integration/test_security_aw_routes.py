"""
Integration checks for the Security org routes.

Covers security:estc-pr-buildkite-detective and security:dependency-review.
Proves registry ↔ wrapper ↔ orchestrator ↔ client template ↔ lock input wiring
and aw-resolve-agentic-assets against frozen consumer fixtures. Does not invoke
a live model or mint tokens.
"""

from __future__ import annotations

import json
import pathlib
import sys
from dataclasses import dataclass

import pytest
import yaml

_root = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_root / "scripts"))

import agentic_assets_resolver as resolver

ORG_KEY = "security"
RESOLVE_JOB = "resolve-apm-assets"
WORKFLOWS_DIR = _root / ".github" / "workflows"
TEMPLATE_DIR = (
    _root
    / ".github"
    / "remote-workflow-template"
    / "security"
    / ".github"
    / "workflows"
)
FIXTURES = _root / "testdata" / "agentic" / "security-aw"


@dataclass(frozen=True)
class Route:
    workflow_id: str
    wrapper: str
    lock: str
    orchestrator: str
    client_template: str
    marker: str
    platform_marker: str


ROUTES = (
    Route(
        workflow_id="estc-pr-buildkite-detective",
        wrapper="security-aw-estc-pr-buildkite-detective.yml",
        lock="gh-aw-estc-pr-buildkite-detective.lock.yml",
        orchestrator="security-aw-event-status.yml",
        client_template="trigger-security-aw-status.yml",
        marker="ESTC_CONSUMER_FRAGMENT_MARKER",
        platform_marker="flaky-test",
    ),
    Route(
        workflow_id="dependency-review",
        wrapper="security-aw-dependency-review.yml",
        lock="gh-aw-dependency-review.lock.yml",
        orchestrator="security-aw-event-pull-request.yml",
        client_template="trigger-security-aw-pull-request.yml",
        marker="DR_CONSUMER_FRAGMENT_MARKER",
        platform_marker="",
    ),
)

route_param = pytest.mark.parametrize("route", ROUTES, ids=lambda r: r.workflow_id)


def _load_yaml(path: pathlib.Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), f"{path}: expected mapping root"
    return data


def _on_block(workflow: dict) -> dict:
    """Return the ``on`` mapping; PyYAML 1.1 may parse the key ``on`` as ``True``."""
    on_block = workflow.get("on")
    if on_block is None:
        on_block = workflow.get(True)
    assert isinstance(on_block, dict), "workflow missing on: mapping"
    return on_block


def _needs(job: dict) -> list[str]:
    needs = job.get("needs") or []
    return [needs] if isinstance(needs, str) else list(needs)


def _platform_instructions(route: Route) -> str:
    wrapper = _load_yaml(WORKFLOWS_DIR / route.wrapper)
    with_block = wrapper["jobs"][RESOLVE_JOB].get("with") or {}
    return with_block.get("platform-additional-instructions") or ""


class TestRegistry:
    @route_param
    def test_registry_entry_points_at_existing_files(self, route: Route) -> None:
        registry = json.loads(
            (_root / "config" / ORG_KEY / "workflow-registry.json").read_text(
                encoding="utf-8"
            )
        )
        entries = {w["id"]: w for w in registry["workflows"]}
        entry = entries[route.workflow_id]
        assert entry["default_enabled"] is False
        assert entry["inner_workflows"] == [route.wrapper]
        assert (_root / entry["docs"]).is_file()
        assert (WORKFLOWS_DIR / route.wrapper).is_file()


class TestWrapperLockWiring:
    @route_param
    def test_resolve_job_targets_wrapper_basename(self, route: Route) -> None:
        wrapper = _load_yaml(WORKFLOWS_DIR / route.wrapper)
        resolve_job = wrapper["jobs"][RESOLVE_JOB]
        assert resolve_job["uses"].endswith("aw-resolve-agentic-assets.yml")
        assert resolve_job["with"]["workflow-basename"] == route.wrapper

    @route_param
    def test_agent_job_passes_resolve_outputs_to_lock_inputs(
        self, route: Route
    ) -> None:
        wrapper = _load_yaml(WORKFLOWS_DIR / route.wrapper)
        lock = _load_yaml(WORKFLOWS_DIR / route.lock)
        agent = wrapper["jobs"][route.workflow_id]
        with_block = agent.get("with") or {}

        assert agent["uses"].startswith(
            ("elastic/oblt-aw/.github/workflows/", "./.github/workflows/")
        ), f"{route.workflow_id} must call the in-repo lock (got {agent['uses']!r})"
        assert route.lock in agent["uses"]
        assert RESOLVE_JOB in _needs(agent)
        assert (
            with_block.get("additional-instructions")
            == "${{ needs.resolve-apm-assets.outputs.resolved-additional-instructions }}"
        )
        assert (
            with_block.get("setup-commands")
            == "${{ join(fromJSON(needs.resolve-apm-assets.outputs."
            "resolved-setup-commands-json), fromJSON('\"\\n\"')) }}"
        )

        lock_inputs = (_on_block(lock).get("workflow_call") or {}).get("inputs") or {}
        for key in with_block:
            assert key in lock_inputs, f"{route.lock} has no input {key!r}"

    @route_param
    def test_wrapper_does_not_invoke_agent_engine_inline(self, route: Route) -> None:
        wrapper = _load_yaml(WORKFLOWS_DIR / route.wrapper)
        agent = wrapper["jobs"][route.workflow_id]
        assert "uses" in agent
        assert "steps" not in agent

    @route_param
    def test_wrapper_does_not_call_prelude(self, route: Route) -> None:
        wrapper = _load_yaml(WORKFLOWS_DIR / route.wrapper)
        for name, job in wrapper["jobs"].items():
            assert "aw-prelude.yml" not in str(job.get("uses", "")), (
                f"{route.wrapper}:{name} must not call aw-prelude directly"
            )
        inputs = (_on_block(wrapper)["workflow_call"] or {}).get("inputs") or {}
        assert inputs["shared-proceed"]["required"] is True

    def test_dependency_review_inputs_are_slim(self) -> None:
        wrapper = _load_yaml(WORKFLOWS_DIR / "security-aw-dependency-review.yml")
        inputs = _on_block(wrapper)["workflow_call"]["inputs"]
        assert set(inputs) == {"shared-proceed", "shared-token-policy"}
        agent = wrapper["jobs"]["dependency-review"]
        assert (
            agent["with"]["github-token-policy"] == "${{ inputs.shared-token-policy }}"
        )

    def test_buildkite_secret_is_required_and_forwarded(self) -> None:
        wrapper = _load_yaml(
            WORKFLOWS_DIR / "security-aw-estc-pr-buildkite-detective.yml"
        )
        secrets = _on_block(wrapper)["workflow_call"]["secrets"]
        assert secrets["BUILDKITE_API_TOKEN"]["required"] is True
        agent = wrapper["jobs"]["estc-pr-buildkite-detective"]
        assert agent["secrets"]["BUILDKITE_API_TOKEN"] == (
            "${{ secrets.BUILDKITE_API_TOKEN }}"
        )


class TestOrchestrator:
    @route_param
    def test_prelude_lists_route_and_route_is_gated(self, route: Route) -> None:
        orch = _load_yaml(WORKFLOWS_DIR / route.orchestrator)
        prelude = orch["jobs"]["run-aw-prelude"]
        assert prelude["uses"] == "./.github/workflows/aw-prelude.yml"
        assert json.loads(prelude["with"]["control-plane-workflows"]) == [route.wrapper]

        job = orch["jobs"][route.workflow_id]
        assert job["uses"] == f"./.github/workflows/{route.wrapper}"
        assert "run-aw-prelude" in _needs(job)
        proceed = (
            f"fromJSON(needs.run-aw-prelude.outputs.proceed-by-workflow)"
            f"['{route.wrapper}']"
        )
        assert f"{proceed} == 'true'" in job["if"]
        assert job["with"]["shared-proceed"] == "${{ " + proceed + " }}"

    @route_param
    def test_caller_permissions_cover_callee(self, route: Route) -> None:
        orch = _load_yaml(WORKFLOWS_DIR / route.orchestrator)
        wrapper = _load_yaml(WORKFLOWS_DIR / route.wrapper)
        granted = orch["jobs"][route.workflow_id]["permissions"]
        for job_name, job in wrapper["jobs"].items():
            if job_name == RESOLVE_JOB:
                continue
            for scope, level in (job.get("permissions") or {}).items():
                if level == "write":
                    assert granted.get(scope) == "write", (
                        f"{route.orchestrator} must grant {scope}: write for "
                        f"{route.wrapper}:{job_name}"
                    )

    def test_pull_request_route_is_limited_to_allowed_authors(self) -> None:
        orch = _load_yaml(WORKFLOWS_DIR / "security-aw-event-pull-request.yml")
        cond = orch["jobs"]["dependency-review"]["if"]
        assert "allowed-pr-authors-json" in cond
        assert "github.event.pull_request.user.login" in cond
        assert "'pull_request'" in cond

    def test_status_route_is_limited_to_buildkite_failures(self) -> None:
        orch = _load_yaml(WORKFLOWS_DIR / "security-aw-event-status.yml")
        cond = orch["jobs"]["estc-pr-buildkite-detective"]["if"]
        assert "github.event.state == 'failure'" in cond
        assert "contains(github.event.context, 'buildkite')" in cond


class TestClientTemplate:
    @route_param
    def test_template_calls_security_orchestrator(self, route: Route) -> None:
        template = _load_yaml(TEMPLATE_DIR / route.client_template)
        (job,) = template["jobs"].values()
        assert job["uses"] == (
            f"elastic/oblt-aw/.github/workflows/{route.orchestrator}@main"
            " # ratchet:exclude"
        ) or job["uses"] == (
            f"elastic/oblt-aw/.github/workflows/{route.orchestrator}@main"
        )

    def test_status_template_maps_buildkite_secret(self) -> None:
        template = _load_yaml(TEMPLATE_DIR / "trigger-security-aw-status.yml")
        (job,) = template["jobs"].values()
        assert job["secrets"]["BUILDKITE_API_TOKEN"] == (
            "${{ secrets.BUILDKITE_LOGS_API_TOKEN }}"
        )
        assert "buildkite" in job["if"]

    def test_pull_request_template_uses_least_privilege(self) -> None:
        template = _load_yaml(TEMPLATE_DIR / "trigger-security-aw-pull-request.yml")
        assert template["permissions"] == {"contents": "read"}
        (job,) = template["jobs"].values()
        assert job["permissions"]["contents"] == "read"
        assert _on_block(template)["pull_request"]["types"] == [
            "opened",
            "synchronize",
            "reopened",
        ]


class TestResolveFixtures:
    @route_param
    def test_resolve_maps_instructions_setup_and_layers(self, route: Route) -> None:
        fixture = FIXTURES / route.workflow_id
        expected_setup = json.loads(
            (fixture / "expected" / "setup-commands.json").read_text(encoding="utf-8")
        )
        expected_layers = json.loads(
            (fixture / "expected" / "instruction-layers.json").read_text(
                encoding="utf-8"
            )
        )

        resolved = resolver.resolve_agentic_assets(
            repo_root=fixture / "consumer",
            workflow_id=route.workflow_id,
            org_key=ORG_KEY,
            platform_additional_instructions=_platform_instructions(route),
            config_dir=_root / "config",
            workflow_basename=route.wrapper,
        )

        assert resolved["asset_source"] == "workflow"
        assert resolved["setup_commands"] == expected_setup
        text = resolved["additional_instructions"]
        assert route.marker in text
        assert "SHOULD_NOT_APPLY" not in text
        if route.platform_marker:
            assert text.index(route.platform_marker) < text.index(route.marker)

        layers = resolved["instruction_layers"]
        assert layers["org-key"] == ORG_KEY == expected_layers["org-key"]
        assert layers["workflow-id"] == expected_layers["workflow-id"]
        assert layers["workflow-basename"] == route.wrapper
        assert layers["layers"] == expected_layers["layers"]

    @route_param
    def test_resolve_without_apm_keeps_platform_only(
        self, route: Route, tmp_path: pathlib.Path
    ) -> None:
        platform = _platform_instructions(route)
        resolved = resolver.resolve_agentic_assets(
            repo_root=tmp_path,
            workflow_id=route.workflow_id,
            org_key=ORG_KEY,
            platform_additional_instructions=platform,
            config_dir=_root / "config",
            workflow_basename=route.wrapper,
        )

        assert resolved["apm_manifest_present"] is False
        assert resolved["setup_commands"] == []
        assert resolved["additional_instructions"].strip() == platform.strip()

    @route_param
    def test_fixture_tree_is_present(self, route: Route) -> None:
        fixture = FIXTURES / route.workflow_id
        assert (fixture / "consumer" / "apm.yml").is_file()
        assert (fixture / "expected" / "setup-commands.json").is_file()
        assert (fixture / "expected" / "instruction-layers.json").is_file()
