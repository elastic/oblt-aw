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

"""Unit tests for scripts/render_pr_actions_detective_trigger.py."""

from __future__ import annotations

import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "scripts"))

import render_pr_actions_detective_trigger as render


class TestRenderWorkflowsPlaceholder:
    def test_replaces_placeholder(self) -> None:
        content = (
            "on:\n"
            "  workflow_run:\n"
            '    workflows: ["__OBLT_AW_PR_ACTIONS_DETECTIVE_WORKFLOWS__"]\n'
            "    types: [completed]\n"
        )
        out = render.render_workflows_placeholder(content, ["CI", "Build"])
        assert 'workflows: ["CI", "Build"]' in out
        assert "__OBLT_AW_PR_ACTIONS_DETECTIVE_WORKFLOWS__" not in out

    def test_empty_list_raises(self) -> None:
        with pytest.raises(SystemExit, match="refuse to render empty"):
            render.render_workflows_placeholder(
                'workflows: ["__OBLT_AW_PR_ACTIONS_DETECTIVE_WORKFLOWS__"]\n',
                [],
            )

    def test_missing_placeholder_raises(self) -> None:
        with pytest.raises(SystemExit, match="missing pr-actions-detective"):
            render.render_workflows_placeholder('workflows: ["CI"]\n', ["CI"])


class TestMain:
    def test_writes_rendered_file(self, tmp_path: pathlib.Path) -> None:
        path = tmp_path / "trigger.yml"
        path.write_text(
            'workflows: ["__OBLT_AW_PR_ACTIONS_DETECTIVE_WORKFLOWS__"]\n',
            encoding="utf-8",
        )
        rc = render.main(
            [
                "--path",
                str(path),
                "--workflows-json",
                json.dumps(["Internal: CI"]),
            ]
        )
        assert rc == 0
        assert path.read_text(encoding="utf-8") == 'workflows: ["Internal: CI"]\n'
