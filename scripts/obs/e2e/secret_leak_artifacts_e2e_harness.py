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

"""Live E2E harness: agent-like audit artifacts must not contain OTLP canaries.

Mirrors the H1 / golang-crossbuild failure mode: sandbox/firewall audit files
are uploaded as an ``agent`` artifact after GH-AW mask + redact_secrets. This
harness scans the downloaded artifact tree (not job log masking alone).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_E2E_DIR = Path(__file__).resolve().parent
_SCRIPTS_DIR = Path(__file__).resolve().parents[2]
for _path in (_E2E_DIR, _SCRIPTS_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from e2e_secret_scan import (
    directory_contains_marker,
    leak_fields_from_scan,
    missing_required_canary_env_names,
    present_comparable_secret_env_names,
    run_gitleaks_dir,
    scan_directory,
)

WORKFLOW_ID = "obs:secret-leak-artifacts"
DEFAULT_CASE_ID = "otel-headers-absent-from-agent-artifact-live"
DEFAULT_ARTIFACT_NAME = "e2e-secret-leak-agent"
DEFAULT_AUDIT_MARKER = "OBLT_AW_E2E_SECRET_LEAK_AUDIT_PLANTED"
DEFAULT_TESTDATA_ROOT = Path("testdata/agentic/secret-leak-artifacts")
DEFAULT_GITLEAKS_CONFIG = DEFAULT_TESTDATA_ROOT / "gitleaks.toml"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def require_case_mode(case: dict[str, Any], expected: str, *, case_id: str) -> None:
    mode = str(case.get("mode") or "")
    if mode != expected:
        raise RuntimeError(
            f"Case {case_id!r} mode={mode!r}; this harness only supports {expected!r}"
        )


def run_live_case(
    case_dir: Path,
    *,
    artifact_dir: Path,
    run_url: str | None = None,
    gitleaks_bin: str | None = None,
    gitleaks_config: Path | None = None,
    gitleaks_report_path: Path | None = None,
) -> dict[str, Any]:
    case = _load_json(case_dir / "case.json")
    case_id = str(case.get("id") or case_dir.name)
    require_case_mode(case, "live", case_id=case_id)
    trigger = case.get("trigger") if isinstance(case.get("trigger"), dict) else {}
    expectations = (
        case.get("expectations") if isinstance(case.get("expectations"), dict) else {}
    )
    marker = str(
        trigger.get("audit_marker")
        or expectations.get("audit_marker")
        or DEFAULT_AUDIT_MARKER
    ).strip()
    artifact_name = str(trigger.get("artifact_name") or DEFAULT_ARTIFACT_NAME).strip()
    require_gitleaks = expectations.get("gitleaks_clean") is True

    missing_canary = missing_required_canary_env_names()
    comparable = present_comparable_secret_env_names()
    base: dict[str, Any] = {
        "workflow_id": str(case.get("workflow_id") or WORKFLOW_ID),
        "case_id": case_id,
        "layer": "e2e",
        "mode": "live",
        "trigger": trigger,
        "expectations": expectations,
        "run_url": run_url,
        "fixture": {
            "artifact_name": artifact_name,
            "artifact_dir": str(artifact_dir),
            "marker": marker,
            "comparable_secret_env_names": comparable,
        },
    }

    if missing_canary:
        return {
            **base,
            "blocked": True,
            "block_reason": (
                "Missing required OTLP canary env values for leak comparison "
                f"(names only): {', '.join(missing_canary)}. The scan job must "
                "inherit the full E2E_OTLP_CANARY_* set from the workflow."
            ),
            "secret_leak_detected": None,
            "secret_leak_detail": None,
            "artifact_downloaded": False,
            "audit_marker_verified": None,
        }

    if not artifact_dir.is_dir():
        return {
            **base,
            "blocked": True,
            "block_reason": (
                f"Downloaded agent artifact directory missing: {artifact_dir}"
            ),
            "secret_leak_detected": None,
            "secret_leak_detail": None,
            "artifact_downloaded": False,
            "audit_marker_verified": False,
            "audit_marker_detail": "artifact directory absent",
        }

    entries = list(artifact_dir.rglob("*"))
    if not any(path.is_file() for path in entries):
        return {
            **base,
            "blocked": True,
            "block_reason": (
                f"Downloaded agent artifact {artifact_name!r} has no files under "
                f"{artifact_dir}"
            ),
            "secret_leak_detected": None,
            "secret_leak_detail": None,
            "artifact_downloaded": False,
            "audit_marker_verified": False,
            "audit_marker_detail": "artifact empty",
        }

    marker_ok = directory_contains_marker(artifact_dir, marker)
    marker_detail = (
        f"Found audit marker {marker!r} in downloaded artifact"
        if marker_ok
        else f"Audit marker {marker!r} not found in downloaded artifact"
    )
    if not marker_ok:
        return {
            **base,
            "blocked": True,
            "block_reason": marker_detail,
            "artifact_downloaded": True,
            "audit_marker_verified": False,
            "audit_marker_detail": marker_detail,
            "secret_leak_detected": None,
            "secret_leak_detail": None,
        }

    leak = leak_fields_from_scan(scan_directory(artifact_dir))
    if leak.get("secret_leak_detected") is True:
        return {
            **base,
            "blocked": True,
            "block_reason": (
                f"Agent artifact contains {leak.get('secret_leak_detail')}"
            ),
            "artifact_downloaded": True,
            "audit_marker_verified": True,
            "audit_marker_detail": marker_detail,
            "gitleaks_clean": None,
            "gitleaks_detail": None,
            **leak,
        }

    if require_gitleaks:
        if not gitleaks_bin:
            return {
                **base,
                "blocked": True,
                "block_reason": (
                    "Case expects gitleaks_clean but --gitleaks-bin was not provided"
                ),
                "artifact_downloaded": True,
                "audit_marker_verified": True,
                "audit_marker_detail": marker_detail,
                "gitleaks_clean": False,
                "gitleaks_detail": "gitleaks binary path missing",
                **leak,
            }
        config_path = gitleaks_config or DEFAULT_GITLEAKS_CONFIG
        if not config_path.is_file():
            return {
                **base,
                "blocked": True,
                "block_reason": f"gitleaks config missing: {config_path}",
                "artifact_downloaded": True,
                "audit_marker_verified": True,
                "audit_marker_detail": marker_detail,
                "gitleaks_clean": False,
                "gitleaks_detail": f"missing config {config_path}",
                **leak,
            }
        report_path = gitleaks_report_path or (artifact_dir / "gitleaks-report.json")
        gitleaks = run_gitleaks_dir(
            artifact_dir,
            config=config_path,
            report_path=report_path,
            binary=gitleaks_bin,
        )
        if gitleaks.get("gitleaks_clean") is not True:
            return {
                **base,
                "blocked": True,
                "block_reason": (
                    f"gitleaks reported secret findings: {gitleaks.get('gitleaks_detail')}"
                ),
                "artifact_downloaded": True,
                "audit_marker_verified": True,
                "audit_marker_detail": marker_detail,
                **leak,
                **gitleaks,
            }
        return {
            **base,
            "blocked": False,
            "artifact_downloaded": True,
            "audit_marker_verified": True,
            "audit_marker_detail": marker_detail,
            **leak,
            **gitleaks,
        }

    return {
        **base,
        "blocked": False,
        "artifact_downloaded": True,
        "audit_marker_verified": True,
        "audit_marker_detail": marker_detail,
        "gitleaks_clean": None,
        "gitleaks_detail": "gitleaks not required by case expectations",
        **leak,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run dedicated secret-leak agent-artifact E2E harness."
    )
    parser.add_argument("--case-id", default=DEFAULT_CASE_ID)
    parser.add_argument("--testdata-root", type=Path, default=DEFAULT_TESTDATA_ROOT)
    parser.add_argument("--outcome-path", type=Path, required=True)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--run-url", default="")
    parser.add_argument("--gitleaks-bin", default="")
    parser.add_argument(
        "--gitleaks-config",
        type=Path,
        default=None,
        help="Defaults to testdata/.../gitleaks.toml when omitted",
    )
    parser.add_argument("--gitleaks-report-path", type=Path, default=None)
    args = parser.parse_args(argv)

    case_dir = args.testdata_root / "cases" / args.case_id
    if not case_dir.is_dir():
        raise SystemExit(f"Missing case directory: {case_dir}")

    gitleaks_config = args.gitleaks_config
    if gitleaks_config is None:
        gitleaks_config = args.testdata_root / "gitleaks.toml"

    outcome = run_live_case(
        case_dir,
        artifact_dir=args.artifact_dir,
        run_url=args.run_url or None,
        gitleaks_bin=args.gitleaks_bin or None,
        gitleaks_config=gitleaks_config,
        gitleaks_report_path=args.gitleaks_report_path,
    )
    args.outcome_path.parent.mkdir(parents=True, exist_ok=True)
    args.outcome_path.write_text(
        json.dumps(outcome, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"outcome_path": str(args.outcome_path), **outcome}, indent=2))
    return 0 if not outcome.get("blocked") else 1


if __name__ == "__main__":
    raise SystemExit(main())
