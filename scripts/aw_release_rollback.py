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

"""Rollback production major tag to previous-prod (quick recovery)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from release_pointers import (
    load_pointers,
    move_tag,
    plan_rollback,
    push_tags,
    save_pointers,
    set_pointer,
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
        "--dry-run",
        action="store_true",
        help="Validate and print plan without writing tags or pointers",
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="Push moved tags to origin (skipped on dry-run)",
    )
    args = parser.parse_args(argv)

    data = load_pointers(args.pointers_path)
    plan = plan_rollback(data)
    print(json.dumps({"plan": plan}, indent=2, sort_keys=True))
    if args.dry_run:
        print("Dry-run: no tags or pointers written")
        return 0

    now = utc_now_iso()
    move_tag(
        plan["prod_tag"],
        plan["rollback_sha"],
        message=f"rollback to {plan['rollback_semver']}",
    )
    move_tag(
        plan["candidate_tag"],
        plan["rollback_sha"],
        message=f"candidate after rollback to {plan['rollback_semver']}",
    )
    # Keep previous-prod pointing at the displaced prod so a second rollback
    # can undo the undo (swap).
    data["tags"]["prod"] = plan["prod_tag"]
    data["major"] = int(str(plan["prod_tag"]).removeprefix("v"))
    set_pointer(
        data,
        "previous_prod",
        sha=plan["displaced_prod_sha"],
        semver=plan["displaced_prod_semver"] or plan["rollback_semver"],
        updated_at=now,
    )
    set_pointer(
        data,
        "prod",
        sha=plan["rollback_sha"],
        semver=plan["rollback_semver"],
        updated_at=now,
    )
    set_pointer(
        data,
        "candidate",
        sha=plan["rollback_sha"],
        semver=plan["rollback_semver"],
        updated_at=now,
    )
    move_tag(
        plan["previous_tag"],
        plan["displaced_prod_sha"],
        message=f"previous-prod after rollback (was {plan['displaced_prod_semver']})",
    )
    save_pointers(data, args.pointers_path)

    if args.push:
        push_tags([plan["prod_tag"], plan["candidate_tag"], plan["previous_tag"]])
        print("Pushed rollback tags to origin")

    print(
        f"Rolled back {plan['prod_tag']} → {plan['rollback_sha']} "
        f"({plan['rollback_semver']})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
