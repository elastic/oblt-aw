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

"""Resolve and rewrite control-plane ``uses:`` pins on distributed client YAML."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from common import PIN_CLASS_DEVELOPMENT, PIN_CLASS_PRODUCTION
from release_pointers import (
    DEFAULT_POINTERS_PATH,
    load_pointers,
    pointer_sha,
    validate_moving_tag_name,
)

DEVELOPMENT_PIN_REF = "main"

CONTROL_PLANE_USES_RE = re.compile(
    r"(?m)^([ \t]*uses:\s+elastic/oblt-aw/\.github/workflows/[A-Za-z0-9._-]+\.yml)"
    r"@[^\s#]+"
)


def published_moving_tag_exists(tag: str) -> bool:
    """True when ``refs/tags/<tag>`` exists locally or on ``origin``."""
    for args in (
        ["git", "rev-parse", "--verify", "--quiet", f"refs/tags/{tag}"],
        ["git", "ls-remote", "--exit-code", "origin", f"refs/tags/{tag}"],
    ):
        try:
            completed = subprocess.run(
                args,
                check=False,
                capture_output=True,
                text=True,
            )
        except OSError:
            continue
        if completed.returncode == 0:
            return True
    return False


def production_pin_ref(pointers: dict[str, Any]) -> str:
    """Return ``tags.current`` when the current SHA is set and the tag is published."""
    tags = pointers.get("tags")
    if not isinstance(tags, dict):
        raise SystemExit("release-pointers.json tags must be an object")
    raw_tag = tags.get("current")
    if not isinstance(raw_tag, str) or not raw_tag.strip():
        raise SystemExit("release-pointers.json tags.current is required")
    try:
        tag = validate_moving_tag_name(raw_tag, role="current")
        sha = pointer_sha(pointers, "current")
    except (TypeError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    if not sha:
        return DEVELOPMENT_PIN_REF
    if not published_moving_tag_exists(tag):
        raise SystemExit(
            f"production pin {tag!r} is not published; refuse retarget until "
            "tags.current exists on origin"
        )
    return tag


def resolve_control_plane_pin(pin_class: str, pointers: dict[str, Any]) -> str:
    """Map pin-class to a git ref used in consumer ``uses:`` lines."""
    if pin_class == PIN_CLASS_DEVELOPMENT:
        return DEVELOPMENT_PIN_REF
    if pin_class == PIN_CLASS_PRODUCTION:
        return production_pin_ref(pointers)
    raise SystemExit(f"Unknown pin-class {pin_class!r}")


def rewrite_control_plane_uses_pin(text: str, pin_ref: str) -> str:
    """Replace ``uses: elastic/oblt-aw/.github/workflows/*.yml@<ref>`` pins."""
    cleaned = pin_ref.strip()
    if not cleaned:
        raise SystemExit("control-plane pin ref must be non-empty")
    if any(ch.isspace() for ch in cleaned) or "#" in cleaned:
        raise SystemExit(f"control-plane pin ref is invalid: {pin_ref!r}")
    return CONTROL_PLANE_USES_RE.sub(rf"\1@{cleaned}", text)


def rewrite_files(target_root: Path, files: list[dict[str, str]], pin_ref: str) -> None:
    """Rewrite YAML client files copied into ``target_root``."""
    for entry in files:
        dst_name = entry.get("dst", "")
        if not dst_name:
            raise SystemExit("install file entry missing dst")
        path = target_root / dst_name
        if path.suffix not in {".yml", ".yaml"}:
            continue
        original = path.read_text(encoding="utf-8")
        updated = rewrite_control_plane_uses_pin(original, pin_ref)
        if updated != original:
            path.write_text(updated, encoding="utf-8")


def load_release_pointers(path: Path = DEFAULT_POINTERS_PATH) -> dict[str, Any]:
    try:
        return load_pointers(path)
    except FileNotFoundError as exc:
        raise SystemExit(f"missing release pointers file: {path}") from exc
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(f"invalid release pointers file {path}: {exc}") from exc


def main() -> int:
    pin = os.environ.get("CONTROL_PLANE_PIN", "").strip()
    if not pin:
        raise SystemExit("CONTROL_PLANE_PIN is required")
    target_root_raw = os.environ.get("TARGET_ROOT", "").strip()
    if not target_root_raw:
        raise SystemExit("TARGET_ROOT is required")
    files_json = os.environ.get("FILES_JSON")
    if files_json is None:
        raise SystemExit("FILES_JSON is required")
    try:
        files = json.loads(files_json)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"FILES_JSON is not valid JSON: {exc}") from exc
    if not isinstance(files, list):
        raise SystemExit("FILES_JSON must be a JSON array")
    typed_files: list[dict[str, str]] = []
    for item in files:
        if not isinstance(item, dict):
            raise SystemExit("FILES_JSON entries must be objects")
        dst = item.get("dst")
        if not isinstance(dst, str):
            raise SystemExit("FILES_JSON entries require string dst")
        typed_files.append({"dst": dst})
    rewrite_files(Path(target_root_raw), typed_files, pin)
    return 0


if __name__ == "__main__":
    sys.exit(main())
