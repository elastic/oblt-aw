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

"""Parse onboard issue body fields (CRLF-safe).

GitHub issue bodies may use CRLF. A blank line after a ``###`` heading then
has nonzero ``NF`` in awk until ``\\r`` is stripped, which used to print an
empty repository and exit early. Normalize newlines before section parsing.
"""

from __future__ import annotations

import argparse
import re
import sys

_REPO_RE = re.compile(r"^elastic/[A-Za-z0-9._-]+$")
_ORG_KEYS = frozenset({"docs", "obs", "security"})
_PHASE2_PY = re.compile(
    r"^\s*-\s*\[[xX]\]\s*\*\*Phase 2",
    re.MULTILINE | re.IGNORECASE,
)


def normalize_newlines(text: str) -> str:
    """Normalize CRLF / CR to LF before field parsing."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def section_first_nonempty(body: str, heading: str) -> str:
    """Return the first non-empty line under ``### <heading>`` (CRLF-safe)."""
    normalized = normalize_newlines(body)
    marker = f"### {heading}"
    grab = False
    for line in normalized.split("\n"):
        if line.strip() == marker:
            grab = True
            continue
        if grab:
            if line.startswith("### "):
                break
            value = line.strip()
            if value:
                return value
    return ""


def parse_onboard_fields(body: str) -> dict[str, str | int]:
    """Parse repository, org_key, and phase2_checked from an issue body."""
    repo = section_first_nonempty(body, "Repository")
    if not _REPO_RE.match(repo):
        repo = ""
    org_key = section_first_nonempty(body, "Organization key")
    if org_key not in _ORG_KEYS:
        org_key = ""
    phase2 = 1 if _PHASE2_PY.search(normalize_newlines(body)) else 0
    phase = 2 if phase2 else 1
    return {
        "repository": repo,
        "org_key": org_key,
        "phase": phase,
        "phase2_checked": phase2,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Parse onboard issue fields; print key=value lines for GITHUB_OUTPUT."
    )
    parser.add_argument(
        "--body-file",
        type=argparse.FileType("r", encoding="utf-8"),
        default=sys.stdin,
        help="Issue body file (default: stdin)",
    )
    args = parser.parse_args(argv)
    body = args.body_file.read()
    fields = parse_onboard_fields(body)
    for key, value in fields.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
