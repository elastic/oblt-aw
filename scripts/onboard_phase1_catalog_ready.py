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

"""Phase 1 catalog-ready check for onboard Phase 2 gate.

Onboard selector alone is not enough: an earlier org registration or a
separate allowlist PR can list the consumer on the onboard TokenPolicy while
sync/distribute/settings selectors are still missing. Require every mapped
org-scoped policy from registering-a-repository step 2e before Phase 2.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from onboard_policy_has_selector import has_repository_selector

# Registration org-key → control-plane / settings policy suffix (docs→obs).
_ORG_SUFFIX: dict[str, str] = {
    "docs": "obs",
    "obs": "obs",
    "security": "security",
}

_POLICY_DIR = Path("resources/github-token-policies")


def policy_suffix_for_org(org_key: str) -> str | None:
    """Return the TokenPolicy file suffix for a registration org-key."""
    return _ORG_SUFFIX.get(org_key.strip())


def required_policy_paths(catalog_root: Path, suffix: str) -> list[Path]:
    """Return policy files that must list the consumer for Phase 1."""
    base = catalog_root / _POLICY_DIR
    return [
        base / "token-policy-oblt-aw-onboard-repository.yaml",
        base / f"token-policy-oblt-aw-sync-control-plane-dashboard-{suffix}.yaml",
        base / f"token-policy-oblt-aw-distribute-client-workflow-{suffix}.yaml",
        base / f"token-policy-observability-github-settings-{suffix}.yaml",
    ]


def missing_phase1_selectors(
    catalog_root: Path, org_key: str, repository: str
) -> list[str]:
    """Return policy basenames missing an exact *repository* selector."""
    suffix = policy_suffix_for_org(org_key)
    if not suffix:
        return [f"unknown org-key: {org_key!r}"]
    missing: list[str] = []
    for path in required_policy_paths(catalog_root, suffix):
        if not path.is_file():
            missing.append(f"{path.name} (file missing)")
            continue
        text = path.read_text(encoding="utf-8")
        if not has_repository_selector(text, repository):
            missing.append(path.name)
    return missing


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Exit 0 when catalog-info lists the consumer on all Phase 1 "
            "TokenPolicy allowlists for the mapped org."
        )
    )
    parser.add_argument(
        "--catalog-root",
        type=Path,
        required=True,
        help="Path to checked-out elastic/catalog-info (e.g. repos/catalog-info)",
    )
    parser.add_argument(
        "--org-key",
        required=True,
        help="Registration org key from the issue (docs, obs, or security)",
    )
    parser.add_argument(
        "--repository",
        required=True,
        help="Repository in owner/name form to match literally",
    )
    args = parser.parse_args(argv)
    repo = args.repository.strip()
    missing = missing_phase1_selectors(args.catalog_root, args.org_key, repo)
    if missing:
        print(
            "Phase 1 catalog incomplete for "
            f"{repo} (org-key={args.org_key}): missing selectors in "
            + ", ".join(missing),
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
