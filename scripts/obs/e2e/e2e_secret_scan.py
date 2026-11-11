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

"""Shared E2E helpers: scan text or artifact trees for secret leakage.

Fail-closed gates must report pattern / env / canary *names* only — never echo
matched secret values into outcome JSON, summaries, or exception messages.

The golang-crossbuild / H1 failure mode was cleartext OTLP headers in uploaded
agent sandbox/firewall audit artifacts, not GitHub log masking alone.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

# Skip short values to avoid noisy substring hits on empty/placeholder tokens.
_ENV_VALUE_MIN_LEN = 12

# Env names aligned with GH-AW redact_secrets / OTEL lock env surfaces.
# E2E_OTLP_CANARY_* cover gh-aw#68811 extraction shapes (ApiKey, Basic-auth
# decoded password, multi-endpoint ALL_HEADERS, percent-encoded headers).
# Keep alphabetical.
_ENV_SECRET_NAMES: tuple[str, ...] = (
    "BUILDKITE_API_TOKEN",
    "BUILDKITE_TOKEN",
    "E2E_OTLP_CANARY_ALL_HEADERS",
    "E2E_OTLP_CANARY_BASIC_CREDENTIAL",
    "E2E_OTLP_CANARY_BASIC_DECODED",
    "E2E_OTLP_CANARY_BASIC_HEADERS",
    "E2E_OTLP_CANARY_BASIC_PASSWORD",
    "E2E_OTLP_CANARY_ENDPOINT",
    "E2E_OTLP_CANARY_HEADERS",
    "E2E_OTLP_CANARY_PERCENT_HEADERS",
    "GH_AW_DEFAULT_OTLP_ENDPOINT",
    "GH_AW_DEFAULT_OTLP_HEADERS",
    "GH_AW_GITHUB_MCP_SERVER_TOKEN",
    "GH_AW_GITHUB_TOKEN",
    "GH_AW_OTLP_ALL_HEADERS",
    "GH_AW_OTLP_ENDPOINTS",
    "GH_TOKEN",
    "GITHUB_TOKEN",
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "OTEL_EXPORTER_OTLP_HEADERS",
)

REQUIRED_CANARY_ENV_NAMES: tuple[str, ...] = (
    "E2E_OTLP_CANARY_ALL_HEADERS",
    "E2E_OTLP_CANARY_BASIC_CREDENTIAL",
    "E2E_OTLP_CANARY_BASIC_DECODED",
    "E2E_OTLP_CANARY_BASIC_HEADERS",
    "E2E_OTLP_CANARY_BASIC_PASSWORD",
    "E2E_OTLP_CANARY_ENDPOINT",
    "E2E_OTLP_CANARY_HEADERS",
    "E2E_OTLP_CANARY_PERCENT_HEADERS",
)

# High-signal denylist (pattern id → regex). Match ids only appear in details.
_PATTERN_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "aws_access_key_id",
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    ),
    (
        "github_fine_grained_pat",
        re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    ),
    (
        "github_token",
        re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{20,}\b"),
    ),
    (
        "private_key_header",
        re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----"),
    ),
    (
        "slack_token",
        re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{10,}\b"),
    ),
)

_AUTH_HEADER_VALUE = re.compile(
    r"(?i)(?:authorization|api[_-]?key)\s*[:=]\s*"
    r"(?:(?:Bearer|Basic|Api[_-]?Key)\s+)?([^\s,;]+)"
)

# Header-like canary env names whose values may embed Authorization= fragments.
_HEADER_LIKE_CANARY_NAMES: frozenset[str] = frozenset(
    {
        "E2E_OTLP_CANARY_ALL_HEADERS",
        "E2E_OTLP_CANARY_BASIC_HEADERS",
        "E2E_OTLP_CANARY_HEADERS",
        "E2E_OTLP_CANARY_PERCENT_HEADERS",
    }
)

# Text-ish extensions typically present in GH-AW agent / firewall audit uploads.
_SCAN_EXTENSIONS: frozenset[str] = frozenset(
    {
        "",
        ".json",
        ".jsonl",
        ".log",
        ".md",
        ".mdx",
        ".txt",
        ".xml",
        ".yaml",
        ".yml",
    }
)


def env_secret_names() -> tuple[str, ...]:
    """Return the env names considered for value-based leak scanning."""
    return _ENV_SECRET_NAMES


def present_comparable_secret_env_names(
    env: Mapping[str, str] | None = None,
) -> list[str]:
    """Env secret names present with values long enough to compare (names only)."""
    source_env = env if env is not None else os.environ
    names: list[str] = []
    for name in _ENV_SECRET_NAMES:
        value = str(source_env.get(name) or "")
        if len(value) >= _ENV_VALUE_MIN_LEN:
            names.append(name)
    return names


def missing_required_canary_env_names(
    env: Mapping[str, str] | None = None,
) -> list[str]:
    """Required E2E canary env names missing or too short for a meaningful scan."""
    source_env = env if env is not None else os.environ
    missing: list[str] = []
    for name in REQUIRED_CANARY_ENV_NAMES:
        value = str(source_env.get(name) or "")
        if len(value) < _ENV_VALUE_MIN_LEN:
            missing.append(name)
    return missing


def _header_fragment_values(headers_blob: str) -> list[str]:
    """Extract authorization / api-key values from an OTLP headers string."""
    values: list[str] = []
    for match in _AUTH_HEADER_VALUE.finditer(headers_blob):
        fragment = match.group(1).strip().strip("\"'")
        if len(fragment) >= _ENV_VALUE_MIN_LEN:
            values.append(fragment)
    return values


def scan_text(
    text: str,
    *,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Scan text for high-signal secret patterns and known env secret values.

    Returns a dict with:
    - ``secret_leak_detected`` (bool)
    - ``secret_leak_detail`` (str) — pattern/env names only
    - ``secret_leak_match_ids`` (list[str]) — stable ids for tests/oracles
    """
    source_env = env if env is not None else os.environ
    match_ids: list[str] = []

    for pattern_id, pattern in _PATTERN_RULES:
        if pattern.search(text):
            match_ids.append(f"pattern:{pattern_id}")

    for name in _ENV_SECRET_NAMES:
        value = str(source_env.get(name) or "")
        if len(value) < _ENV_VALUE_MIN_LEN:
            continue
        if value in text:
            match_ids.append(f"env:{name}")
        if (
            name.endswith(("_HEADERS", "_ALL_HEADERS"))
            or name in _HEADER_LIKE_CANARY_NAMES
        ):
            for fragment in _header_fragment_values(value):
                if fragment in text:
                    match_ids.append(f"env:{name}:auth_fragment")

    ordered = sorted(dict.fromkeys(match_ids))
    detected = bool(ordered)
    if detected:
        detail = "secret leak match(es): " + ", ".join(ordered)
    else:
        detail = "no secret leak patterns or known env secret values detected"
    return {
        "secret_leak_detected": detected,
        "secret_leak_detail": detail,
        "secret_leak_match_ids": ordered,
    }


# Back-compat alias for callers that still say "log".
scan_log_text = scan_text


def iter_scan_files(root: Path) -> list[Path]:
    """Return regular files under ``root`` that look text-scannable."""
    if not root.is_dir():
        return []
    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in _SCAN_EXTENSIONS:
            continue
        files.append(path)
    return files


def scan_directory(
    root: Path,
    *,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Scan text-like files under ``root``; aggregate match ids (names only)."""
    source_env = env if env is not None else os.environ
    files = iter_scan_files(root)
    if not files:
        return {
            "secret_leak_detected": False,
            "secret_leak_detail": f"no scannable files under {root}",
            "secret_leak_match_ids": [],
            "scanned_file_count": 0,
        }

    match_ids: list[str] = []
    for path in files:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            return {
                "secret_leak_detected": True,
                "secret_leak_detail": (
                    f"could not read artifact file for scan: {path.name} ({exc})"
                ),
                "secret_leak_match_ids": ["error:read_failed"],
                "scanned_file_count": len(files),
            }
        part = scan_text(text, env=source_env)
        match_ids.extend(
            str(item) for item in (part.get("secret_leak_match_ids") or [])
        )

    ordered = sorted(dict.fromkeys(match_ids))
    detected = bool(ordered)
    if detected:
        detail = "secret leak match(es): " + ", ".join(ordered)
    else:
        detail = (
            "no secret leak patterns or known env secret values detected "
            f"in {len(files)} file(s)"
        )
    return {
        "secret_leak_detected": detected,
        "secret_leak_detail": detail,
        "secret_leak_match_ids": ordered,
        "scanned_file_count": len(files),
    }


def directory_contains_marker(root: Path, marker: str) -> bool:
    """True when any scannable file under ``root`` contains ``marker``."""
    if not marker:
        return False
    for path in iter_scan_files(root):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if marker in text:
            return True
    return False


def leak_fields_from_scan(scan: Mapping[str, Any]) -> dict[str, Any]:
    """Project scan result into outcome fields (no match value echo)."""
    detected = bool(scan.get("secret_leak_detected"))
    detail = str(scan.get("secret_leak_detail") or "")
    return {
        "secret_leak_detected": detected,
        "secret_leak_detail": detail,
    }


def gitleaks_fields_from_report(findings: list[Any]) -> dict[str, Any]:
    """Project gitleaks JSON findings into outcome fields (rule ids only)."""
    rule_ids: list[str] = []
    for item in findings:
        if not isinstance(item, dict):
            continue
        rule_id = str(item.get("RuleID") or item.get("rule_id") or "").strip()
        if rule_id:
            rule_ids.append(rule_id)
    ordered = sorted(dict.fromkeys(rule_ids))
    clean = len(ordered) == 0
    if clean:
        detail = "gitleaks reported no findings"
    else:
        detail = "gitleaks finding rule id(s): " + ", ".join(ordered)
    return {
        "gitleaks_clean": clean,
        "gitleaks_finding_count": len(findings),
        "gitleaks_detail": detail,
        "gitleaks_rule_ids": ordered,
    }


def run_gitleaks_dir(
    source: Path,
    *,
    config: Path,
    report_path: Path,
    binary: str = "gitleaks",
) -> dict[str, Any]:
    """Run ``gitleaks dir`` on ``source``; return name-only outcome fields.

    Uses ``--exit-code 0`` so callers interpret the report; a missing binary or
    nonzero tool failure is returned as a blocked-style detail (not clean).
    """
    report_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        binary,
        "dir",
        str(source),
        "--config",
        str(config),
        "--report-path",
        str(report_path),
        "--report-format",
        "json",
        "--redact",
        "--no-banner",
        "--exit-code",
        "0",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()[:400]
        return {
            "gitleaks_clean": False,
            "gitleaks_finding_count": None,
            "gitleaks_detail": (
                f"gitleaks failed (exit {proc.returncode}): {err or 'no output'}"
            ),
            "gitleaks_rule_ids": [],
        }
    if not report_path.is_file():
        return {
            "gitleaks_clean": False,
            "gitleaks_finding_count": None,
            "gitleaks_detail": f"gitleaks report missing: {report_path}",
            "gitleaks_rule_ids": [],
        }
    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {
            "gitleaks_clean": False,
            "gitleaks_finding_count": None,
            "gitleaks_detail": f"gitleaks report is not valid JSON: {exc}",
            "gitleaks_rule_ids": [],
        }
    if payload is None:
        findings: list[Any] = []
    elif isinstance(payload, list):
        findings = payload
    else:
        return {
            "gitleaks_clean": False,
            "gitleaks_finding_count": None,
            "gitleaks_detail": "gitleaks report must be a JSON array",
            "gitleaks_rule_ids": [],
        }
    return gitleaks_fields_from_report(findings)
