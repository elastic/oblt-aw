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

"""Validate a directory of E2E summary.json files for production promote."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from release_pointers import (
    REQUIRED_E2E_WORKFLOW_IDS,
    enrich_summary,
    validate_e2e_gate_summaries,
    validate_full_sha,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--summaries-dir",
        type=Path,
        required=True,
        help="Directory containing summary.json files (searched recursively)",
    )
    parser.add_argument(
        "--candidate-sha",
        required=True,
        help="Expected candidate SHA for gating eligibility",
    )
    parser.add_argument(
        "--aggregate-out",
        type=Path,
        help="Optional path to write {summaries: [...]} aggregate JSON",
    )
    args = parser.parse_args(argv)

    candidate_sha = validate_full_sha(args.candidate_sha, label="--candidate-sha")
    paths = sorted(args.summaries_dir.rglob("summary.json"))
    if not paths:
        raise SystemExit(f"no summary.json under {args.summaries_dir}")

    summaries: list[dict[str, Any]] = []
    for path in paths:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise SystemExit(f"{path} is not a JSON object")
        # Re-stamp eligibility against the promote candidate (fail closed if
        # the leaf run omitted candidate metadata).
        stamped = enrich_summary(
            raw,
            candidate_ref=str(raw.get("candidate_ref") or ""),
            github_sha=str(raw.get("github_sha") or ""),
        )
        # If the leaf already recorded gating fields, keep them; enrich only
        # fills blanks. Always recompute eligible against expected SHA below.
        if stamped.get("candidate_ref") != candidate_sha:
            stamped["eligible_for_promote"] = False
        summaries.append(stamped)

    validate_e2e_gate_summaries(
        summaries,
        expected_candidate_sha=candidate_sha,
        required_workflow_ids=REQUIRED_E2E_WORKFLOW_IDS,
    )

    aggregate = {"summaries": summaries, "candidate_sha": candidate_sha}
    print(json.dumps(aggregate, indent=2, sort_keys=True))
    if args.aggregate_out is not None:
        args.aggregate_out.parent.mkdir(parents=True, exist_ok=True)
        args.aggregate_out.write_text(
            json.dumps(aggregate, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print("E2E gate: all required workflows passed (gating)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
