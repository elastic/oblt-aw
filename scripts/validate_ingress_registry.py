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

"""Validate per-org ingress_routes in workflow-registry.json against ingress route jobs."""

from __future__ import annotations

from pathlib import Path

from oblt_aw_route_specs import (
    validate_all_org_registries,
    validate_all_workflow_local_reusable_job_permissions,
    validate_client_entrypoint_permissions,
    validate_docs_ingress_registry,
    validate_obs_ingress_registry,
)

CONFIG_DIR = Path("config")
WORKFLOWS_DIR = Path(".github/workflows")
TEMPLATE_DIR = Path(".github/remote-workflow-template")


def main() -> int:
    validate_all_org_registries(CONFIG_DIR)
    validate_obs_ingress_registry(
        config_dir=CONFIG_DIR,
        workflows_dir=WORKFLOWS_DIR,
        ingress_path=WORKFLOWS_DIR / "oblt-aw-ingress.yml",
    )
    validate_docs_ingress_registry(
        config_dir=CONFIG_DIR,
        workflows_dir=WORKFLOWS_DIR,
        ingress_path=WORKFLOWS_DIR / "docs-aw-ingress.yml",
    )
    validate_all_workflow_local_reusable_job_permissions(WORKFLOWS_DIR)
    for org_key in ("obs", "docs"):
        validate_client_entrypoint_permissions(
            org_key=org_key,
            config_dir=CONFIG_DIR,
            workflows_dir=WORKFLOWS_DIR,
            template_dir=TEMPLATE_DIR,
        )
    print("Ingress registry validated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
