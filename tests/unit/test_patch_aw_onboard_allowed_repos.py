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

"""Tests for scripts/patch_aw_onboard_allowed_repos.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

MODULE_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "scripts"
    / "patch_aw_onboard_allowed_repos.py"
)
SPEC = importlib.util.spec_from_file_location(
    "patch_aw_onboard_allowed_repos", MODULE_PATH
)
assert SPEC and SPEC.loader
patch_mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(patch_mod)

SAMPLE_LOCK = """jobs:
  agent:
    outputs:
      agentic_engine_timeout: ${{ steps.detect-agent-errors.outputs.agentic_engine_timeout || 'false' }}
    steps:
      - name: Start DIFC Proxy
        env:
          DIFC_PROXY_POLICY: '{"allow-only":{"min-integrity":"none","repos":["elastic/catalog-info","elastic/oblt-aw","elastic/observability-github-secrets","elastic/observability-github-settings"]}}'
      - name: Determine automatic lockdown mode for GitHub MCP Server
        env:
          GH_AW_GITHUB_REPOS: '["elastic/catalog-info","elastic/oblt-aw","elastic/observability-github-secrets","elastic/observability-github-settings"]'
      - name: Generate Safe Outputs Config
        env:
          GH_AW_SAFE_OUTPUTS_CONFIG: '{"create_pull_request":{"allowed_repos":"${{ steps.onboard-phase.outputs.allowed_repos }}"}}'
      - name: Start MCP Gateway
        id: start-mcp-gateway
        env:
          DEBUG: 'false'
        run: |
          cat << GH_AW_MCP_CONFIG_EOF
          {
            "servers": {
              "github": {
                "guard-policies": {
                  "allow-only": {
                    "repos": [
                      "elastic/catalog-info",
                      "elastic/oblt-aw",
                      "elastic/observability-github-secrets",
                      "elastic/observability-github-settings"
                    ]
                  }
                }
              },
              "public-code-search": {
                "guard-policies": {
                  "write-sink": {
                    "accept": [
                      "private:elastic/catalog-info",
                      "private:elastic/oblt-aw",
                      "private:elastic/observability-github-secrets",
                      "private:elastic/observability-github-settings"
                    ],
                    "sink-visibility": "${GH_AW_SINK_VISIBILITY}"
                  }
                }
              },
              "safeoutputs": {
                "guard-policies": {
                  "write-sink": {
                    "accept": [
                      "private:elastic/catalog-info",
                      "private:elastic/oblt-aw",
                      "private:elastic/observability-github-secrets",
                      "private:elastic/observability-github-settings"
                    ],
                    "sink-visibility": "${GH_AW_SINK_VISIBILITY}"
                  }
                }
              }
            }
          }
          GH_AW_MCP_CONFIG_EOF
  safe_outputs:
    steps:
      - name: Process Safe Outputs
        env:
          GH_AW_SAFE_OUTPUTS_HANDLER_CONFIG: '{"create_pull_request":{"allowed_repos":"${{ steps.onboard-phase.outputs.allowed_repos }}"}}'
"""


def test_patch_lock_wires_agent_output_handler_and_mcp(tmp_path: Path) -> None:
    lock = tmp_path / "gh-aw-onboard-repository.lock.yml"
    lock.write_text(SAMPLE_LOCK, encoding="utf-8")
    assert patch_mod.patch_lock(lock) is True
    text = lock.read_text(encoding="utf-8")
    assert patch_mod.AGENT_OUTPUT_LINE.strip() in text
    assert (
        'GH_AW_SAFE_OUTPUTS_HANDLER_CONFIG: \'{"create_pull_request":'
        '{"allowed_repos":"${{ needs.agent.outputs.allowed_repos }}"}}\'' in text
    )
    assert (
        "GH_AW_GITHUB_REPOS: "
        "'${{ steps.onboard-phase.outputs.allowed_repos_json }}'" in text
    )
    assert '"repos": ${GH_AW_GITHUB_REPOS}' in text
    assert (
        'DIFC_PROXY_POLICY: \'{"allow-only":{"min-integrity":"none",'
        '"repos":["elastic/catalog-info","elastic/oblt-aw",'
        '"elastic/observability-github-secrets",'
        '"elastic/observability-github-settings"]}}\'' in text
    )
    assert (
        "GH_AW_GITHUB_REPOS: ${{ steps.onboard-phase.outputs.allowed_repos_json }}"
        in text
    )
    assert (
        "GH_AW_GITHUB_SINKS: ${{ steps.onboard-phase.outputs.allowed_sinks_json }}"
        in text
    )
    assert text.count('"accept": ${GH_AW_GITHUB_SINKS}') == 2
    assert '"sink-visibility": "${GH_AW_SINK_VISIBILITY}"' in text
    assert "private:elastic/*" not in text
    assert '"accept": ["*"]' not in text
    assert patch_mod.patch_lock(lock) is False


def test_patch_lock_fails_closed_when_write_sink_missing(tmp_path: Path) -> None:
    lock = tmp_path / "gh-aw-onboard-repository.lock.yml"
    # Valid anchors but no write-sink.accept lists.
    lock.write_text(
        SAMPLE_LOCK.replace('"write-sink": {', '"write-sink-disabled": {').replace(
            '"accept": [', '"accept_disabled": ['
        ),
        encoding="utf-8",
    )
    with pytest.raises(SystemExit, match="write-sink.accept"):
        patch_mod.patch_lock(lock)


def test_patch_lock_fails_closed_when_anchor_missing(tmp_path: Path) -> None:
    lock = tmp_path / "gh-aw-onboard-repository.lock.yml"
    lock.write_text("jobs: {}\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="anchor not found"):
        patch_mod.patch_lock(lock)
