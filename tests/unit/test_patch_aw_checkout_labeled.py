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

"""Tests for scripts/patch_aw_checkout_labeled.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

MODULE_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "scripts"
    / "patch_aw_checkout_labeled.py"
)
SPEC = importlib.util.spec_from_file_location("patch_aw_checkout_labeled", MODULE_PATH)
assert SPEC and SPEC.loader
patch_mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(patch_mod)

SAMPLE_LOCK = """jobs:
  agent:
    steps:
      - name: Configure Git credentials
        run: bash "${RUNNER_TEMP}/gh-aw/actions/configure_git_credentials.sh"
      - name: Checkout PR branch
        id: checkout-pr
        uses: actions/github-script@v9
        with:
          script: |
            await main();
      - name: Install GitHub Copilot CLI
        run: true
"""


def test_inject_patch_steps_inserts_before_checkout() -> None:
    updated = patch_mod.inject_patch_steps(SAMPLE_LOCK)
    assert patch_mod.STEP_MARKER in updated
    assert patch_mod.STEP_NAME in updated
    checkout_idx = updated.index("      - name: Checkout PR branch\n")
    patch_idx = updated.index(f"      - name: {patch_mod.STEP_NAME}\n")
    assert patch_idx < checkout_idx
    assert updated.count("      - name: Checkout PR branch\n") == 1
    assert updated.count(patch_mod.STEP_MARKER) == 1


def test_inject_patch_steps_is_idempotent() -> None:
    once = patch_mod.inject_patch_steps(SAMPLE_LOCK)
    twice = patch_mod.inject_patch_steps(once)
    assert once == twice


def test_inject_patch_steps_requires_checkout_step() -> None:
    with pytest.raises(ValueError, match="Checkout PR branch"):
        patch_mod.inject_patch_steps("jobs:\n  agent:\n    steps: []\n")


def test_process_lock_file_writes_once(tmp_path: Path) -> None:
    lock = tmp_path / "gh-aw-autoapprove.lock.yml"
    lock.write_text(SAMPLE_LOCK, encoding="utf-8")
    assert patch_mod.process_lock_file(lock) is True
    assert patch_mod.STEP_MARKER in lock.read_text(encoding="utf-8")
    assert patch_mod.process_lock_file(lock) is False


def test_injected_step_embeds_expected_allowlist_markers() -> None:
    updated = patch_mod.inject_patch_steps(SAMPLE_LOCK)
    assert patch_mod.EXPECTED_TRUSTED_BOT_LINE in updated
    assert patch_mod.PATCHED_TRUSTED_BOT_LINE in updated
