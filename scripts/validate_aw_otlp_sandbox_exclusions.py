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

"""Validate AWF sandbox invocations exclude OTLP credential env (gh-aw#68811).

Compiled locks that run ``awf … --env-all`` must exclude the OTLP env names that
would otherwise dump into sandbox/firewall audit artifacts.
"""

from __future__ import annotations

import pathlib
import sys

# Keep alphabetical — matches gh-aw#68811 aggregated-header sandbox exclusion.
REQUIRED_EXCLUDE_ENV: tuple[str, ...] = (
    "GH_AW_OTLP_ALL_HEADERS",
    "GH_AW_OTLP_ENDPOINTS",
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "OTEL_EXPORTER_OTLP_HEADERS",
)

WORKFLOWS_DIR = pathlib.Path(".github/workflows")


def list_lock_workflows(
    workflows_dir: pathlib.Path | None = None,
) -> list[pathlib.Path]:
    root = workflows_dir if workflows_dir is not None else WORKFLOWS_DIR
    if not root.is_dir():
        return []
    return sorted(root.glob("*.lock.yml")) + sorted(root.glob("*.lock.yaml"))


def validate_lock_text(path: pathlib.Path, text: str) -> list[str]:
    """Return errors for awf --env-all lines missing required --exclude-env."""
    errors: list[str] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        if "awf" not in line or "--env-all" not in line:
            continue
        for name in REQUIRED_EXCLUDE_ENV:
            needle = f"--exclude-env {name}"
            if needle not in line:
                errors.append(
                    f"{path}:{line_no}: awf --env-all missing {needle!r} "
                    "(OTLP sandbox exclusion from gh-aw#68811)"
                )
    return errors


def validate_lock(path: pathlib.Path) -> list[str]:
    return validate_lock_text(path, path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    _ = argv
    locks = list_lock_workflows()
    if not locks:
        print(f"No lock workflows found under {WORKFLOWS_DIR}", file=sys.stderr)
        return 1

    errors: list[str] = []
    scanned = 0
    for path in locks:
        text = path.read_text(encoding="utf-8")
        if "awf" not in text or "--env-all" not in text:
            continue
        scanned += 1
        errors.extend(validate_lock_text(path, text))

    if errors:
        print("OTLP sandbox exclusion validation failed:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print(
        f"Validated {scanned} lock workflow(s) with awf --env-all; "
        f"required excludes present: {', '.join(REQUIRED_EXCLUDE_ENV)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
