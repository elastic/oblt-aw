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

"""Rollback current major tag to previous (quick recovery)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from release_pointers import (
    apply_rollback_pointer_updates,
    load_pointers,
    load_release_plan,
    move_tag,
    plan_rollback,
    push_rollback_tags,
    require_remote_current_allows_in_flight,
    save_pointers,
    utc_now_iso,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pointers-path",
        type=Path,
        default=Path("config/release-pointers.json"),
    )
    parser.add_argument(
        "--plan-output",
        type=Path,
        default=None,
        help="Write {plan: ...} JSON for a later tag-push step",
    )
    parser.add_argument(
        "--push-from-plan",
        type=Path,
        default=None,
        help=(
            "Push tags from a prior --plan-output JSON and exit "
            "(no pointer or local tag writes)"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and print plan without writing tags or pointers",
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help=(
            "Push moving tags to origin after local writes. Prefer committing "
            "release-pointers.json first, then --push-from-plan."
        ),
    )
    args = parser.parse_args(argv)

    if args.push_from_plan is not None:
        plan = load_release_plan(args.push_from_plan)
        push_rollback_tags(plan)
        print("Pushed rollback tags to origin")
        return 0

    data = load_pointers(args.pointers_path)
    plan = plan_rollback(data)
    require_remote_current_allows_in_flight(
        data, in_flight_sha=str(plan["rollback_sha"])
    )
    payload = {"plan": plan}
    print(json.dumps(payload, indent=2, sort_keys=True))
    if args.plan_output is not None:
        args.plan_output.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    if args.dry_run:
        print("Dry-run: no tags or pointers written")
        return 0

    now = utc_now_iso()
    move_tag(
        plan["current_tag"],
        plan["rollback_sha"],
        message=f"rollback to {plan['rollback_semver']}",
    )
    move_tag(
        plan["next_tag"],
        plan["rollback_sha"],
        message=f"next after rollback to {plan['rollback_semver']}",
    )
    move_tag(
        plan["previous_tag"],
        plan["displaced_current_sha"],
        message=(f"previous after rollback (was {plan['displaced_current_semver']})"),
    )
    apply_rollback_pointer_updates(data, plan, updated_at=now)
    save_pointers(data, args.pointers_path)

    if args.push:
        push_rollback_tags(plan)
        print("Pushed rollback tags to origin")

    print(
        f"Rolled back {plan['current_tag']} → {plan['rollback_sha']} "
        f"({plan['rollback_semver']})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
