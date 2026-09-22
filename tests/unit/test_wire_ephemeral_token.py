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

"""Tests for scripts/wire_ephemeral_token.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path

MODULE_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "scripts"
    / "wire_ephemeral_token.py"
)
SPEC = importlib.util.spec_from_file_location("wire_ephemeral_token", MODULE_PATH)
assert SPEC and SPEC.loader
wire = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(wire)


SAMPLE_LOCK = """on:
  issues:
    types: [labeled]
jobs:
  safe_outputs:
    permissions:
      issues: write
    steps:
      - id: create-token
        uses: elastic/oblt-actions/github/create-token@v1
        with:
          token-policy: token-policy-995e89faa204
      - name: Process Safe Outputs
        with:
          github-token: ${{ secrets.GH_AW_GITHUB_TOKEN || secrets.GITHUB_TOKEN }}
  detection:
    permissions:
      contents: read
    steps:
      - name: Scan
        with:
          github-token: ${{ secrets.GH_AW_GITHUB_TOKEN || secrets.GITHUB_TOKEN }}
"""


def test_wire_token_expressions_is_idempotent() -> None:
    once = wire.wire_token_expressions(SAMPLE_LOCK)
    twice = wire.wire_token_expressions(once)
    assert once == twice
    assert "steps.create-token.outputs.token" in once


def test_wire_token_expressions_only_on_minting_jobs() -> None:
    updated = wire.wire_token_expressions(SAMPLE_LOCK)
    safe_block, detection_block = updated.split("  detection:")
    assert (
        "steps.create-token.outputs.token || secrets.GH_AW_GITHUB_TOKEN" in safe_block
    )
    assert "steps.create-token.outputs.token" not in detection_block
    assert (
        "github-token: ${{ secrets.GH_AW_GITHUB_TOKEN || secrets.GITHUB_TOKEN }}"
        in detection_block
    )


def test_ensure_id_token_write_only_on_minting_jobs() -> None:
    updated = wire.ensure_id_token_write(SAMPLE_LOCK)
    safe_block, detection_block = updated.split("  detection:")
    assert "id-token: write" in safe_block
    assert "id-token: write" not in detection_block


def test_process_lock_file_wires_create_token_step(tmp_path: Path) -> None:
    lock = tmp_path / "gh-aw-onboard-repository.lock.yml"
    lock.write_text(SAMPLE_LOCK, encoding="utf-8")
    assert wire.process_lock_file(lock) is True
    text = lock.read_text(encoding="utf-8")
    safe_block, detection_block = text.split("  detection:")
    assert (
        "steps.create-token.outputs.token || secrets.GH_AW_GITHUB_TOKEN" in safe_block
    )
    assert "id-token: write" in safe_block
    assert "steps.create-token.outputs.token" not in detection_block
    assert "id-token: write" not in detection_block


def test_process_lock_file_skips_without_create_token(tmp_path: Path) -> None:
    lock = tmp_path / "gh-aw-other.lock.yml"
    lock.write_text("jobs:\n  run:\n    steps: []\n", encoding="utf-8")
    assert wire.process_lock_file(lock) is False
