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

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from generate_planned_dispatch import (  # noqa: E402
    PlannedDispatchTarget,
    commit_message_for_routes,
    gh_aw_workflow_uses,
    load_route_specs,
    parse_routes_json,
    render_planned_dispatch_workflow,
    write_planned_dispatch_workflow,
)


def test_route_specs_loaded_from_workflow_registry() -> None:
    specs = load_route_specs()
    assert specs["automerge"]["workflow"] == "gh-aw-automerge.yml"
    assert specs["automerge"]["with_input"] == "allowed-pr"
    assert specs["security-detector"]["workflow"] == "gh-aw-security-detector.yml"
    assert len(specs) == 15


def test_planned_dispatch_targets_gh_aw_directly() -> None:
    yaml_text = render_planned_dispatch_workflow(["automerge"], "main")
    assert (
        "uses: elastic/oblt-aw/.github/workflows/gh-aw-automerge.yml@main" in yaml_text
    )
    assert "oblt-aw-invoke-" not in yaml_text
    assert "oblt-aw-leg-" not in yaml_text


def test_planned_dispatch_only_includes_planned_jobs() -> None:
    yaml_text = render_planned_dispatch_workflow(
        ["automerge", "dependency-review"], "abc123def"
    )
    assert "  automerge:" in yaml_text
    assert "  dependency-review:" in yaml_text
    assert (
        gh_aw_workflow_uses(
            {
                "workflow": "gh-aw-automerge.yml",
                "secrets": "copilot",
                "with_input": "allowed-pr",
            },
            "abc123def",
            dispatch_repo="elastic/oblt-aw",
        )
        in yaml_text
    )
    assert "  issue-fixer:" not in yaml_text


def test_planned_dispatch_unknown_route() -> None:
    with pytest.raises(KeyError):
        render_planned_dispatch_workflow(["not-a-route"], "main")


def test_planned_dispatch_target_fields() -> None:
    target = PlannedDispatchTarget(
        repo="elastic/oblt-aw",
        workflow_file="oblt-aw-planned-dispatch.yml",
    )
    assert target.workflow_file == "oblt-aw-planned-dispatch.yml"
    assert target.repo == "elastic/oblt-aw"


def test_parse_routes_json_rejects_unknown() -> None:
    with pytest.raises(SystemExit):
        parse_routes_json('["not-a-route"]')


def test_commit_message_for_routes() -> None:
    assert commit_message_for_routes(["automerge", "autodoc"]) == (
        "chore(dispatch): planned routes automerge, autodoc"
    )


def test_write_planned_dispatch_workflow(tmp_path: Path) -> None:
    output = tmp_path / "oblt-aw-planned-dispatch.yml"
    routes = write_planned_dispatch_workflow(
        '["automerge"]',
        "main",
        output,
        dispatch_repo="elastic/oblt-aw",
    )
    assert routes == ["automerge"]
    assert output.is_file()
    assert "gh-aw-automerge.yml@main" in output.read_text(encoding="utf-8")
