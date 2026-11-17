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

"""Tests for scripts/patch_aw_onboard_edited_label.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

MODULE_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "scripts"
    / "patch_aw_onboard_edited_label.py"
)
SPEC = importlib.util.spec_from_file_location(
    "patch_aw_onboard_edited_label", MODULE_PATH
)
assert SPEC and SPEC.loader
patch_mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(patch_mod)

SAMPLE_LOCK = """jobs:
  activation:
    if: >
      needs.pre_activation.outputs.activated == 'true' && (github.event_name != 'issues' || github.event.action != 'labeled' ||
      github.event.label.name == 'oblt-aw/onboard/repository')
  pre_activation:
    if: >
      github.event_name != 'issues' || github.event.action != 'labeled' || github.event.label.name == 'oblt-aw/onboard/repository'
"""


def test_patch_lock_rewrites_labeled_only_filters(tmp_path: Path) -> None:
    lock = tmp_path / "gh-aw-onboard-repository.lock.yml"
    lock.write_text(SAMPLE_LOCK, encoding="utf-8")
    assert patch_mod.patch_lock(lock) is True
    text = lock.read_text(encoding="utf-8")
    assert patch_mod.NEW_SNIPPET in text
    assert "github.event.action != 'labeled'" not in text
    assert patch_mod.patch_lock(lock) is False


def test_patch_lock_fails_closed_when_snippet_missing(tmp_path: Path) -> None:
    lock = tmp_path / "gh-aw-onboard-repository.lock.yml"
    lock.write_text("jobs: {}\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="snippet not found"):
        patch_mod.patch_lock(lock)
