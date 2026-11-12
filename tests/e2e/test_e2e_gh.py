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

"""Unit tests for shared E2E ``gh`` JSON helpers."""

from __future__ import annotations

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "obs" / "e2e"))

import e2e_gh
import estc_pr_buildkite_detective_e2e_harness as estc_harness


class TestE2eGh:
    def test_transient_http_5xx_detection(self) -> None:
        assert e2e_gh.gh_json_error_is_transient(
            "failed to get run: HTTP 500 "
            "(https://api.github.com/repos/elastic/oblt-aw/actions/runs/1)"
        )
        assert e2e_gh.gh_json_error_is_transient("HTTP 502 Bad Gateway")
        assert e2e_gh.gh_json_error_is_transient("HTTP 503")
        assert e2e_gh.gh_json_error_is_transient("HTTP 504")
        assert not e2e_gh.gh_json_error_is_transient("HTTP 404 Not Found")
        assert not e2e_gh.gh_json_error_is_transient("permission denied")

    def test_gh_json_retries_transient_500_then_succeeds(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[int] = []

        class _Proc:
            def __init__(self, code: int, stdout: str = "", stderr: str = "") -> None:
                self.returncode = code
                self.stdout = stdout
                self.stderr = stderr

        def fake_run(cmd: list[str], **_k: object) -> _Proc:
            calls.append(1)
            if len(calls) < 3:
                return _Proc(
                    1,
                    stderr=(
                        "failed to get run: HTTP 500 "
                        "(https://api.github.com/repos/x/actions/runs/1"
                        "?exclude_pull_requests=true)"
                    ),
                )
            return _Proc(0, stdout='{"ok": true}')

        sleeps: list[float] = []
        monkeypatch.setattr(e2e_gh.subprocess, "run", fake_run)
        monkeypatch.setattr(e2e_gh.time, "sleep", lambda s: sleeps.append(float(s)))
        payload = e2e_gh.gh_json(
            ["run", "view", "1", "--json", "databaseId"],
            retries=3,
            retry_sleep_seconds=0.01,
        )
        assert payload == {"ok": True}
        assert len(calls) == 3
        assert sleeps == [0.01, 0.01]

    def test_gh_json_does_not_retry_non_transient(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[int] = []

        class _Proc:
            def __init__(self, code: int, stdout: str = "", stderr: str = "") -> None:
                self.returncode = code
                self.stdout = stdout
                self.stderr = stderr

        def fake_run(cmd: list[str], **_k: object) -> _Proc:
            calls.append(1)
            return _Proc(1, stderr="HTTP 404 Not Found")

        monkeypatch.setattr(e2e_gh.subprocess, "run", fake_run)
        monkeypatch.setattr(e2e_gh.time, "sleep", lambda *_a, **_k: None)
        try:
            e2e_gh.gh_json(["api", "repos/x"], retries=3, retry_sleep_seconds=0.01)
            raise AssertionError("expected RuntimeError")
        except RuntimeError as exc:
            assert "HTTP 404" in str(exc)
        assert len(calls) == 1

    def test_estc_harness_reexports_shared_helpers(self) -> None:
        assert estc_harness.gh_json is e2e_gh.gh_json
        assert (
            estc_harness.gh_json_error_is_transient is e2e_gh.gh_json_error_is_transient
        )
