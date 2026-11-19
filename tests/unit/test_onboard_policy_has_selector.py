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

"""Tests for scripts/onboard_policy_has_selector.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

MODULE_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "scripts"
    / "onboard_policy_has_selector.py"
)
SPEC = importlib.util.spec_from_file_location(
    "onboard_policy_has_selector", MODULE_PATH
)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)

POLICY_WITH_HYPHEN = """
spec:
  implementation:
    kind: TokenPolicy
    spec:
      permissionset:
        selector:
          - kind: Resource
            spec.implementation.spec.repository: elastic/example-repo
            spec.type: github-repository
"""


def test_exact_hyphen_name_matches() -> None:
    assert mod.has_repository_selector(POLICY_WITH_HYPHEN, "elastic/example-repo")


def test_dotted_name_does_not_match_hyphen_selector() -> None:
    """Regression: ERE '.' must not treat example.repo as matching example-repo."""
    assert not mod.has_repository_selector(POLICY_WITH_HYPHEN, "elastic/example.repo")


def test_exact_dotted_name_matches_when_present() -> None:
    policy = "            spec.implementation.spec.repository: elastic/example.repo\n"
    assert mod.has_repository_selector(policy, "elastic/example.repo")


def test_empty_repository_never_matches() -> None:
    assert not mod.has_repository_selector(POLICY_WITH_HYPHEN, "")


def test_cli_exit_codes(tmp_path: Path) -> None:
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text(POLICY_WITH_HYPHEN, encoding="utf-8")
    assert (
        mod.main(
            [
                "--policy",
                str(policy_path),
                "--repository",
                "elastic/example-repo",
            ]
        )
        == 0
    )
    assert (
        mod.main(
            [
                "--policy",
                str(policy_path),
                "--repository",
                "elastic/example.repo",
            ]
        )
        == 1
    )
    missing = tmp_path / "missing.yaml"
    assert (
        mod.main(["--policy", str(missing), "--repository", "elastic/example-repo"])
        == 1
    )


@pytest.mark.parametrize(
    ("line", "repo", "expected"),
    [
        (
            "spec.implementation.spec.repository: elastic/foo",
            "elastic/foo",
            True,
        ),
        (
            "spec.implementation.spec.repository: elastic/foo\r",
            "elastic/foo",
            True,
        ),
        ("# spec.implementation.spec.repository: elastic/foo", "elastic/foo", False),
        (
            "spec.implementation.spec.repository: elastic/foo-bar",
            "elastic/foo.bar",
            False,
        ),
        ("repository: elastic/foo", "elastic/foo", True),
    ],
)
def test_line_shapes(line: str, repo: str, expected: bool) -> None:
    assert mod.has_repository_selector(f"{line}\n", repo) is expected
