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

"""Literal TokenPolicy repository selector match for onboard Phase 2.

Catalog-info onboard policies use nested keys such as
``spec.implementation.spec.repository: owner/name``. Match that value
literally — do not use ``grep -E`` with an unescaped repo name, because dots
in GitHub repository names are valid and must not become ERE wildcards.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_KEY = "repository:"


def has_repository_selector(policy_text: str, repository: str) -> bool:
    """Return True when *repository* is an exact selector value on a policy line."""
    if not repository:
        return False
    for raw_line in policy_text.splitlines():
        line = raw_line.strip().rstrip("\r")
        if not line or line.startswith("#"):
            continue
        key_at = line.find(_REPO_KEY)
        if key_at < 0:
            continue
        if key_at > 0 and line[key_at - 1] not in ". \t":
            continue
        value = line[key_at + len(_REPO_KEY) :].strip()
        if value == repository:
            return True
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Exit 0 when the TokenPolicy YAML contains an exact "
            "repository: <owner/name> selector value."
        )
    )
    parser.add_argument(
        "--policy",
        type=Path,
        required=True,
        help="Path to token-policy YAML (catalog-info onboard policy)",
    )
    parser.add_argument(
        "--repository",
        required=True,
        help="Repository in owner/name form to match literally",
    )
    args = parser.parse_args(argv)
    if not args.policy.is_file():
        return 1
    text = args.policy.read_text(encoding="utf-8")
    return 0 if has_repository_selector(text, args.repository.strip()) else 1


if __name__ == "__main__":
    sys.exit(main())
