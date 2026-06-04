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
Resolve a control-plane workflow filename to its compound dashboard id.

Reads config/<org>/workflow-registry.json and writes compound-workflow-id to
GITHUB_OUTPUT when set, otherwise prints to stdout.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from common import write_outputs
from workflow_registry import resolve_compound_id


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Resolve control-plane workflow file to org:workflow-id"
    )
    parser.add_argument(
        "control_plane_workflow",
        help="Workflow basename under .github/workflows/ (for example oblt-aw-automerge.yml)",
    )
    parser.add_argument(
        "--config-dir",
        type=Path,
        default=Path("config"),
        help="Config root containing per-org workflow-registry.json trees",
    )
    args = parser.parse_args()

    try:
        compound_id = resolve_compound_id(args.config_dir, args.control_plane_workflow)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if os.getenv("GITHUB_OUTPUT"):
        write_outputs({"compound-workflow-id": compound_id})
    else:
        print(compound_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
