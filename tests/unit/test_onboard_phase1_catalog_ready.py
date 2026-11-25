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

"""Tests for scripts/onboard_phase1_catalog_ready.py."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

MODULE_PATH = SCRIPTS / "onboard_phase1_catalog_ready.py"
SPEC = importlib.util.spec_from_file_location(
    "onboard_phase1_catalog_ready", MODULE_PATH
)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)

_SELECTOR = "            spec.implementation.spec.repository: elastic/example-repo\n"


def _write_policy(path: Path, *, with_repo: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "spec:\n  implementation:\n    kind: TokenPolicy\n"
    if with_repo:
        body += _SELECTOR
    path.write_text(body, encoding="utf-8")


def test_docs_maps_to_obs_suffix() -> None:
    assert mod.policy_suffix_for_org("docs") == "obs"
    assert mod.policy_suffix_for_org("security") == "security"


def test_ready_when_all_selectors_present(tmp_path: Path) -> None:
    suffix = "obs"
    for name in (
        "token-policy-oblt-aw-onboard-repository.yaml",
        f"token-policy-oblt-aw-sync-control-plane-dashboard-{suffix}.yaml",
        f"token-policy-oblt-aw-distribute-client-workflow-{suffix}.yaml",
        f"token-policy-observability-github-settings-{suffix}.yaml",
    ):
        _write_policy(
            tmp_path / "resources/github-token-policies" / name, with_repo=True
        )
    assert mod.missing_phase1_selectors(tmp_path, "obs", "elastic/example-repo") == []
    assert (
        mod.main(
            [
                "--catalog-root",
                str(tmp_path),
                "--org-key",
                "obs",
                "--repository",
                "elastic/example-repo",
            ]
        )
        == 0
    )


def test_onboard_alone_is_not_ready(tmp_path: Path) -> None:
    """Regression: onboard selector present but sync/distribute/settings missing."""
    policies = tmp_path / "resources/github-token-policies"
    _write_policy(
        policies / "token-policy-oblt-aw-onboard-repository.yaml", with_repo=True
    )
    for name in (
        "token-policy-oblt-aw-sync-control-plane-dashboard-obs.yaml",
        "token-policy-oblt-aw-distribute-client-workflow-obs.yaml",
        "token-policy-observability-github-settings-obs.yaml",
    ):
        _write_policy(policies / name, with_repo=False)
    missing = mod.missing_phase1_selectors(tmp_path, "docs", "elastic/example-repo")
    assert "token-policy-oblt-aw-onboard-repository.yaml" not in missing
    assert any("sync-control-plane-dashboard" in m for m in missing)
    assert any("distribute-client-workflow" in m for m in missing)
    assert any("observability-github-settings" in m for m in missing)
    assert (
        mod.main(
            [
                "--catalog-root",
                str(tmp_path),
                "--org-key",
                "docs",
                "--repository",
                "elastic/example-repo",
            ]
        )
        == 1
    )
