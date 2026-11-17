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

"""Require the onboard label on ``issues`` ``edited`` for gh-aw-onboard-repository.

github/gh-aw ``on.issues.names`` only constrains the ``labeled`` action
(``github.event.label.name``). With ``types: [labeled, edited]``, every issue
edit would otherwise activate pre_activation/agent. This post-compile step
rewrites job ``if:`` conditions so ``edited`` also requires the issue to
already carry ``oblt-aw/onboard/repository``.

Run from Makefile ``compile-aw`` after ``wire_ephemeral_token``. Idempotent.
"""

from __future__ import annotations

import sys
from pathlib import Path

TARGET_LOCK = "gh-aw-onboard-repository.lock.yml"
ONBOARD_LABEL = "oblt-aw/onboard/repository"

# Compiler-emitted filter (labeled-only). Matches single-line and folded forms.
OLD_SNIPPETS: tuple[str, ...] = (
    (
        "github.event_name != 'issues' || github.event.action != 'labeled' || "
        f"github.event.label.name == '{ONBOARD_LABEL}'"
    ),
    (
        "github.event_name != 'issues' || github.event.action != 'labeled' ||\n"
        f"      github.event.label.name == '{ONBOARD_LABEL}'"
    ),
)

NEW_SNIPPET = (
    "github.event_name != 'issues' || "
    f"(github.event.action == 'labeled' && github.event.label.name == '{ONBOARD_LABEL}') || "
    "(github.event.action == 'edited' && "
    f"contains(join(github.event.issue.labels.*.name, ','), '{ONBOARD_LABEL}'))"
)


def patch_lock(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    if NEW_SNIPPET in text and all(old not in text for old in OLD_SNIPPETS):
        return False
    updated = text
    replacements = 0
    for old in OLD_SNIPPETS:
        count = updated.count(old)
        if count:
            updated = updated.replace(old, NEW_SNIPPET)
            replacements += count
    if replacements == 0:
        if NEW_SNIPPET in updated:
            return False
        raise SystemExit(
            f"{path.name}: onboard label filter snippet not found; "
            "gh-aw compiler output may have changed — update "
            "scripts/patch_aw_onboard_edited_label.py"
        )
    path.write_text(updated, encoding="utf-8")
    print(f"  patched {path.name} ({replacements} job if condition(s))")
    return True


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    lock = root / ".github" / "workflows" / TARGET_LOCK
    if not lock.is_file():
        print(f"skip: {TARGET_LOCK} missing", file=sys.stderr)
        return 0
    changed = patch_lock(lock)
    if changed:
        print(f"Patched edited-label gate in {TARGET_LOCK}")
    else:
        print(f"Already patched or unchanged: {TARGET_LOCK}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
