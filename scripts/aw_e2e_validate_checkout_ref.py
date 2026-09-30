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

"""Fail-closed checkout-ref guard for manual E2E workflow_dispatch.

``workflow_call`` (CI / promote) is unrestricted: callers pin a trusted SHA.
``workflow_dispatch`` must run from the default branch and may only target that
branch tip or a full SHA that is an ancestor of ``origin/<default>`` — so
harness code run with secrets/write cannot come from an arbitrary feature
branch while keeping the trusted workflow YAML from main.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys

FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def _run_git(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        check=False,
        capture_output=True,
        text=True,
    )


def validate_dispatch_checkout_ref(
    *,
    checkout_ref: str,
    default_branch: str,
    github_ref: str,
) -> None:
    expected_ref = f"refs/heads/{default_branch}"
    if github_ref != expected_ref:
        raise ValueError(
            f"workflow_dispatch must run from {expected_ref}, got {github_ref!r}"
        )
    cleaned = checkout_ref.strip()
    if not cleaned:
        raise ValueError("checkout-ref is empty")
    if cleaned in {default_branch, f"refs/heads/{default_branch}"}:
        return
    sha = cleaned.lower()
    if not FULL_SHA_RE.fullmatch(sha):
        raise ValueError(
            f"workflow_dispatch checkout-ref must be {default_branch!r} or a "
            f"40-char SHA, got {checkout_ref!r}"
        )
    tip = f"origin/{default_branch}"
    fetch = _run_git(["fetch", "--no-tags", "origin", default_branch])
    if fetch.returncode != 0:
        raise ValueError(
            f"failed to fetch {tip}: {fetch.stderr.strip() or fetch.stdout.strip()}"
        )
    ancestor = _run_git(["merge-base", "--is-ancestor", sha, tip])
    if ancestor.returncode != 0:
        raise ValueError(
            f"checkout-ref {sha} is not an ancestor of {tip}; "
            "refusing secrets/write E2E against untrusted history"
        )


def main(argv: list[str] | None = None) -> int:
    _ = argv
    event = (os.environ.get("GITHUB_EVENT_NAME") or "").strip()
    if event != "workflow_dispatch":
        print(f"checkout-ref guard skipped for event={event!r}")
        return 0
    checkout_ref = os.environ.get("CHECKOUT_REF") or "main"
    default_branch = (os.environ.get("DEFAULT_BRANCH") or "main").strip()
    github_ref = (os.environ.get("GITHUB_REF") or "").strip()
    try:
        validate_dispatch_checkout_ref(
            checkout_ref=checkout_ref,
            default_branch=default_branch,
            github_ref=github_ref,
        )
    except ValueError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 1
    print(
        f"workflow_dispatch checkout-ref {checkout_ref!r} accepted "
        f"(default_branch={default_branch!r})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
