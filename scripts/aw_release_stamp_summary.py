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

"""Stamp candidate_ref / run_class onto an existing E2E summary.json."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from release_pointers import enrich_summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary-path", type=Path, required=True)
    parser.add_argument(
        "--candidate-ref",
        default="",
        help="Full SHA when this is a gating run; empty for smoke",
    )
    parser.add_argument(
        "--github-sha",
        required=True,
        help="github.sha of the E2E workflow run (must match candidate for gating)",
    )
    args = parser.parse_args(argv)

    summary = json.loads(args.summary_path.read_text(encoding="utf-8"))
    if not isinstance(summary, dict):
        raise SystemExit(f"{args.summary_path} must be a JSON object")
    stamped = enrich_summary(
        summary,
        candidate_ref=args.candidate_ref,
        github_sha=args.github_sha,
    )
    args.summary_path.write_text(
        json.dumps(stamped, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(stamped, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
