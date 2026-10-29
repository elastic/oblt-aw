#!/usr/bin/env python3
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

import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from evaluate_workflow_gates import evaluate_gates


@pytest.fixture
def config_dir(tmp_path: pathlib.Path) -> pathlib.Path:
    obs = tmp_path / "config" / "obs"
    obs.mkdir(parents=True)
    registry = {
        "workflows": [
            {
                "id": "automerge",
                "inner_workflows": ["obs-aw-automerge.yml"],
            },
            {
                "id": "dependency-review",
                "inner_workflows": ["obs-aw-dependency-review.yml"],
            },
        ]
    }
    (obs / "workflow-registry.json").write_text(json.dumps(registry), encoding="utf-8")
    (obs / "active-repositories.json").write_text(
        json.dumps({"repositories": []}), encoding="utf-8"
    )
    return tmp_path / "config"


def test_no_workflows_when_no_dashboard(config_dir: pathlib.Path) -> None:
    result = evaluate_gates(
        config_dir,
        ["obs-aw-automerge.yml", "obs-aw-dependency-review.yml"],
        effective_raw="",
        enabled_workflows_json="[]",
        org_key="obs",
    )
    assert result == {
        "obs-aw-automerge.yml": "false",
        "obs-aw-dependency-review.yml": "false",
    }


def test_selective_enablement(config_dir: pathlib.Path) -> None:
    enabled = json.dumps(["obs:automerge"])
    result = evaluate_gates(
        config_dir,
        ["obs-aw-automerge.yml", "obs-aw-dependency-review.yml"],
        effective_raw="checked",
        enabled_workflows_json=enabled,
        org_key="obs",
    )
    assert result["obs-aw-automerge.yml"] == "true"
    assert result["obs-aw-dependency-review.yml"] == "false"


def test_unknown_workflow_raises(config_dir: pathlib.Path) -> None:
    with pytest.raises(ValueError, match="not listed"):
        evaluate_gates(
            config_dir,
            ["obs-aw-unknown.yml"],
            effective_raw="",
            enabled_workflows_json="[]",
            org_key="obs",
        )


def test_shared_basename_scoped_to_invoking_org(
    tmp_path: pathlib.Path,
) -> None:
    config = tmp_path / "config"
    common = config / "common"
    common.mkdir(parents=True)
    (common / "services.json").write_text(
        json.dumps(
            {
                "services": [
                    {
                        "id": "dependency-review",
                        "inner_workflows": ["obs-aw-dependency-review.yml"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    for org in ("docs", "obs"):
        org_dir = config / org
        org_dir.mkdir()
        (org_dir / "workflow-registry.json").write_text(
            json.dumps({"include_common": ["dependency-review"], "workflows": []}),
            encoding="utf-8",
        )
        (org_dir / "active-repositories.json").write_text(
            json.dumps({"repositories": []}), encoding="utf-8"
        )

    # Docs checkbox must not enable the Obs orchestrator for the shared basename.
    result_obs = evaluate_gates(
        config,
        ["obs-aw-dependency-review.yml"],
        effective_raw="checked",
        enabled_workflows_json=json.dumps(["docs:dependency-review"]),
        org_key="obs",
    )
    assert result_obs["obs-aw-dependency-review.yml"] == "false"

    result_docs = evaluate_gates(
        config,
        ["obs-aw-dependency-review.yml"],
        effective_raw="checked",
        enabled_workflows_json=json.dumps(["docs:dependency-review"]),
        org_key="docs",
    )
    assert result_docs["obs-aw-dependency-review.yml"] == "true"

    result_obs_enabled = evaluate_gates(
        config,
        ["obs-aw-dependency-review.yml"],
        effective_raw="checked",
        enabled_workflows_json=json.dumps(["obs:dependency-review"]),
        org_key="obs",
    )
    assert result_obs_enabled["obs-aw-dependency-review.yml"] == "true"


def test_sub_feature_workflow_requires_parent_and_child(
    config_dir: pathlib.Path,
) -> None:
    registry = {
        "workflows": [
            {
                "id": "security",
                "inner_workflows": ["obs-aw-security-triage.yml"],
                "sub_features": [
                    {
                        "id": "injection",
                        "inner_workflows": ["obs-aw-security-injection-detector.yml"],
                    }
                ],
            }
        ]
    }
    obs = config_dir / "obs"
    (obs / "workflow-registry.json").write_text(json.dumps(registry), encoding="utf-8")

    enabled = json.dumps(
        ["obs:security:injection", "obs:security:injection", "obs:security"]
    )
    result = evaluate_gates(
        config_dir,
        ["obs-aw-security-injection-detector.yml"],
        effective_raw="checked",
        enabled_workflows_json=enabled,
        org_key="obs",
    )
    assert result["obs-aw-security-injection-detector.yml"] == "true"

    child_only = json.dumps(["obs:security:injection"])
    result_child_only = evaluate_gates(
        config_dir,
        ["obs-aw-security-injection-detector.yml"],
        effective_raw="checked",
        enabled_workflows_json=child_only,
        org_key="obs",
    )
    assert result_child_only["obs-aw-security-injection-detector.yml"] == "false"
