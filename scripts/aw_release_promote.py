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

"""Promote tip of main to the production major tag after E2E jobs succeed."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from release_pointers import (
    RELEASE_TYPES,
    apply_promote_pointer_updates,
    create_immutable_semver_tag,
    load_pointers,
    move_tag,
    plan_promote,
    push_tags,
    resolve_sha,
    save_pointers,
    utc_now_iso,
    validate_full_sha,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sha",
        required=True,
        help="Full 40-char SHA to promote (tip of default branch)",
    )
    parser.add_argument(
        "--release-type",
        required=True,
        choices=RELEASE_TYPES,
        help="Semver bump relative to current prod (ignored on first promote)",
    )
    parser.add_argument(
        "--pointers-path",
        type=Path,
        default=Path("config/release-pointers.json"),
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
    args = parser.parse_args(argv)

    sha = validate_full_sha(args.sha, label="--sha")
    resolve_sha(sha)

    data = load_pointers(args.pointers_path)
    plan = plan_promote(data, sha=sha, release_type=args.release_type)

    print(json.dumps({"plan": plan}, indent=2, sort_keys=True))
    if args.dry_run:
        print("Dry-run: no tags or pointers written")
        return 0

    now = utc_now_iso()
    create_immutable_semver_tag(
        plan["semver"],
        sha,
        message=f"oblt-aw release {plan['semver']}",
    )
    move_tag(
        plan["previous_tag"],
        plan["previous_sha"],
        message=f"previous-prod before {plan['semver']}",
    )
    move_tag(
        plan["prod_tag"],
        sha,
        message=f"prod {plan['semver']}",
    )
    move_tag(
        plan["candidate_tag"],
        sha,
        message=f"candidate {plan['semver']}",
    )

    apply_promote_pointer_updates(data, plan, updated_at=now)
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

    print(f"Promoted {sha} as {plan['semver']} → {plan['prod_tag']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
