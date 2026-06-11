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

"""
Write a configured repository token policy from active-repositories.json to GITHUB_OUTPUT.

Reads per-org ``active-repositories.json`` under ``--config-dir``. When no policy is
configured for the repository, writes an empty value for the selected output key.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from collections.abc import Callable
from typing import TypedDict

from common import (
    lookup_repository_ai_assets_token_policy,
    lookup_repository_workflow_token_policy,
    write_outputs,
)


class PolicyFieldSpec(TypedDict):
    lookup: Callable[[Path, str], str]
    output_key: str


POLICY_FIELD_CHOICES: dict[str, PolicyFieldSpec] = {
    "workflow-token-policy": {
        "lookup": lookup_repository_workflow_token_policy,
        "output_key": "token-policy",
    },
    "ai-assets-token-policy": {
        "lookup": lookup_repository_ai_assets_token_policy,
        "output_key": "ai-assets-token-policy",
    },
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Resolve a repository token policy from active-repositories.json"
    )
    parser.add_argument(
        "--config-dir",
        type=Path,
        default=Path(os.environ.get("CONFIG_DIR", "config")),
        help="Directory containing config/<org-key>/ trees",
    )
    parser.add_argument(
        "--repository",
        default=os.environ.get("TARGET_REPOSITORY", "").strip(),
        help="Repository in owner/repo form (defaults to TARGET_REPOSITORY env)",
    )
    parser.add_argument(
        "--policy-field",
        choices=sorted(POLICY_FIELD_CHOICES),
        default="workflow-token-policy",
        help="Policy field to resolve from active-repositories.json",
    )
    args = parser.parse_args()
    if not args.repository:
        raise SystemExit("--repository or TARGET_REPOSITORY is required")

    spec = POLICY_FIELD_CHOICES[args.policy_field]
    policy = spec["lookup"](args.config_dir, args.repository)
    write_outputs({spec["output_key"]: policy})
    return 0


if __name__ == "__main__":
    sys.exit(main())
