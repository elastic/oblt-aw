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

"""Shared ``gh`` JSON helpers for live E2E harnesses.

Keep cross-cutting CLI helpers here so individual harness modules (ESTC,
automerge, repo-scheduled, …) do not own shared infrastructure.
"""

from __future__ import annotations

import json
import re
import subprocess
import time
from typing import Any

# Transient GitHub API failures observed during live E2E polls (promote flake).
_GH_TRANSIENT_HTTP_RE = re.compile(r"\bHTTP\s+50[0-4]\b", re.IGNORECASE)
_GH_JSON_DEFAULT_RETRIES = 4
_GH_JSON_DEFAULT_RETRY_SLEEP_SECONDS = 2.0


def gh_json_error_is_transient(stderr: str) -> bool:
    """True when ``gh`` failed due to a retryable GitHub HTTP 5xx response."""
    return bool(_GH_TRANSIENT_HTTP_RE.search(stderr or ""))


def gh_json(
    args: list[str],
    *,
    check: bool = True,
    retries: int = _GH_JSON_DEFAULT_RETRIES,
    retry_sleep_seconds: float = _GH_JSON_DEFAULT_RETRY_SLEEP_SECONDS,
) -> Any:
    """Run ``gh`` and parse JSON stdout.

    Retries a bounded number of times on transient GitHub HTTP 500–504 errors
    (documented mitigation for Actions API flakes during E2E polls). Non-5xx
    failures still raise immediately when ``check`` is true.
    """
    attempts = max(1, int(retries) + 1)
    last_proc: subprocess.CompletedProcess[str] | None = None
    for attempt in range(1, attempts + 1):
        proc = subprocess.run(
            ["gh", *args],
            capture_output=True,
            text=True,
            check=False,
        )
        last_proc = proc
        if proc.returncode == 0:
            if not proc.stdout.strip():
                return None
            return json.loads(proc.stdout)
        stderr = (proc.stderr or "").strip()
        if check and attempt < attempts and gh_json_error_is_transient(stderr):
            time.sleep(max(0.0, float(retry_sleep_seconds)))
            continue
        break
    assert last_proc is not None
    if check:
        raise RuntimeError(
            f"gh {' '.join(args)} failed ({last_proc.returncode}): "
            f"{(last_proc.stderr or '').strip()}"
        )
    if not last_proc.stdout.strip():
        return None
    return json.loads(last_proc.stdout)
