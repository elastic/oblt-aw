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

"""Promote a default-branch SHA to the production major tag after E2E succeeds."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from release_pointers import (
    RELEASE_TYPES,
    apply_promote_pointer_updates,
    create_github_release,
    create_immutable_semver_tag,
    load_pointers,
    load_release_plan,
    move_tag,
    plan_promote,
    push_promote_tags,
    require_ancestor_of,
    require_remote_tip,
    resolve_sha,
    save_pointers,
    utc_now_iso,
    validate_full_sha,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sha",
        default=None,
        help="Full 40-char SHA to promote (must be on default-branch history)",
    )
    parser.add_argument(
        "--release-type",
        default=None,
        choices=RELEASE_TYPES,
        help="Semver bump relative to current prod (ignored on first promote)",
    )
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
        "--create-release-from-plan",
        type=Path,
        default=None,
        help=(
            "Create a GitHub Release with auto-generated notes from a prior "
            "--plan-output JSON and exit"
        ),
    )
    parser.add_argument(
        "--expect-tip-of",
        default="",
        help="Strict CAS: fail unless this ref still resolves to --sha",
    )
    parser.add_argument(
        "--require-ancestor-of",
        default="",
        help=(
            "Fail unless --sha is this ref or an ancestor of it "
            "(e.g. origin/main); allows main to advance during E2E"
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
            "Push tags to origin after local writes. Prefer committing "
            "release-pointers.json first, then --push-from-plan."
        ),
    )
    args = parser.parse_args(argv)

    if args.push_from_plan is not None:
        plan = load_release_plan(args.push_from_plan)
        push_promote_tags(plan)
        print("Pushed release tags to origin")
        return 0

    if args.create_release_from_plan is not None:
        plan = load_release_plan(args.create_release_from_plan)
        create_github_release(
            semver=str(plan["semver"]),
            sha=str(plan["sha"]),
            previous_semver=str(plan.get("previous_semver") or ""),
            bootstrap=bool(plan.get("bootstrap")),
        )
        print(f"Created GitHub Release {plan['semver']} with generated notes")
        return 0

    if args.sha is None or args.release_type is None:
        parser.error(
            "--sha and --release-type are required unless "
            "--push-from-plan or --create-release-from-plan"
        )

    sha = validate_full_sha(args.sha, label="--sha")
    resolve_sha(sha)
    if args.expect_tip_of.strip():
        require_remote_tip(sha, tip_ref=args.expect_tip_of.strip())
    if args.require_ancestor_of.strip():
        require_ancestor_of(sha, tip_ref=args.require_ancestor_of.strip())

    data = load_pointers(args.pointers_path)
    plan = plan_promote(data, sha=sha, release_type=args.release_type)
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
    create_immutable_semver_tag(
        plan["semver"],
        sha,
        message=f"oblt-aw release {plan['semver']}",
    )
    move_tag(
        plan["previous_tag"],
        plan["previous_sha"],
        message=f"previous before {plan['semver']}",
    )
    move_tag(
        plan["current_tag"],
        sha,
        message=f"current {plan['semver']}",
    )
    move_tag(
        plan["next_tag"],
        sha,
        message=f"next {plan['semver']}",
    )

    apply_promote_pointer_updates(data, plan, updated_at=now)
    save_pointers(data, args.pointers_path)

    if args.push:
        push_promote_tags(plan)
        print("Pushed release tags to origin")

    print(f"Promoted {sha} as {plan['semver']} → {plan['current_tag']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
