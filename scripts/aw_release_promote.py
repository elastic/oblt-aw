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

"""Promote a candidate SHA to the production major tag after gating E2E."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from release_pointers import (
    create_immutable_semver_tag,
    load_pointers,
    move_tag,
    plan_promote,
    push_tags,
    resolve_sha,
    save_pointers,
    set_pointer,
    utc_now_iso,
    validate_e2e_gate_summaries,
    validate_full_sha,
)


def _load_summaries(path: Path) -> list[dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and "summaries" in raw:
        raw = raw["summaries"]
    if not isinstance(raw, list):
        raise SystemExit(f"{path} must be a JSON array or {{summaries: [...]}}")
    return raw


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--candidate-sha",
        required=True,
        help="Full 40-char SHA to promote (must match gating E2E candidate_ref)",
    )
    parser.add_argument(
        "--semver",
        required=True,
        help="Immutable semver tag to create (e.g. v1.0.0)",
    )
    parser.add_argument(
        "--e2e-summaries",
        type=Path,
        required=True,
        help="JSON file with all leaf E2E summary objects",
    )
    parser.add_argument(
        "--pointers-path",
        type=Path,
        default=Path("config/release-pointers.json"),
    )
    parser.add_argument(
        "--bootstrap",
        action="store_true",
        help="First promote: allow empty prod pointer",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and print plan without writing tags or pointers",
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="Push moved/created tags to origin (skipped on dry-run)",
    )
    parser.add_argument(
        "--skip-e2e-gate",
        action="store_true",
        help="Dangerous: skip E2E summary validation (tests / emergency only)",
    )
    args = parser.parse_args(argv)

    candidate_sha = validate_full_sha(args.candidate_sha, label="--candidate-sha")
    # Ensure the SHA exists locally.
    resolve_sha(candidate_sha)

    data = load_pointers(args.pointers_path)
    plan = plan_promote(
        data,
        candidate_sha=candidate_sha,
        semver=args.semver,
        bootstrap=args.bootstrap,
    )

    if not args.skip_e2e_gate:
        summaries = _load_summaries(args.e2e_summaries)
        validate_e2e_gate_summaries(summaries, expected_candidate_sha=candidate_sha)

    print(json.dumps({"plan": plan}, indent=2, sort_keys=True))
    if args.dry_run:
        print("Dry-run: no tags or pointers written")
        return 0

    now = utc_now_iso()
    create_immutable_semver_tag(
        plan["semver"],
        candidate_sha,
        message=f"oblt-aw release {plan['semver']}",
    )
    move_tag(
        plan["previous_tag"],
        plan["previous_sha"],
        message=f"previous-prod before {plan['semver']}",
    )
    move_tag(
        plan["prod_tag"],
        candidate_sha,
        message=f"prod {plan['semver']}",
    )
    move_tag(
        plan["candidate_tag"],
        candidate_sha,
        message=f"candidate {plan['semver']}",
    )

    set_pointer(
        data,
        "previous_prod",
        sha=plan["previous_sha"],
        semver=(
            str(data["pointers"]["prod"].get("semver") or plan["semver"])
            if not args.bootstrap
            else plan["semver"]
        ),
        updated_at=now,
    )
    set_pointer(
        data,
        "prod",
        sha=candidate_sha,
        semver=plan["semver"],
        updated_at=now,
    )
    set_pointer(
        data,
        "candidate",
        sha=candidate_sha,
        semver=plan["semver"],
        updated_at=now,
    )
    save_pointers(data, args.pointers_path)

    if args.push:
        push_tags(
            [
                plan["semver"],
                plan["prod_tag"],
                plan["candidate_tag"],
                plan["previous_tag"],
            ]
        )
        print("Pushed release tags to origin")

    print(f"Promoted {candidate_sha} as {plan['semver']} → {plan['prod_tag']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
