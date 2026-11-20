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

"""
Keep agent Python pins aligned with the control-plane ``.python-version`` file.

Agent jobs check out the *consumer* repository, so they cannot use
``python-version-file: .python-version`` (that would read the consumer pin).
The compiled agent setup steps therefore bake an explicit ``python-version``.
Root ``.python-version`` remains the bumpable source of truth for Renovate /
manual bumps; this script copies that value into the GH-AW fragments (and the
``elastic/oblt-actions/pre-commit`` input that cannot use a version file).

Control-plane ``actions/setup-python`` steps should use
``python-version-file: .python-version`` so they follow the file automatically.

Usage:
  python3 scripts/sync_python_version.py          # write
  python3 scripts/sync_python_version.py --check  # exit 1 on drift
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
PYTHON_VERSION_FILE = ROOT / ".python-version"
RUNTIME_SETUP = ROOT / ".github" / "workflows" / "gh-aw-fragments" / "runtime-setup.md"
OBS_DEFAULTS = ROOT / ".github" / "workflows" / "gh-aw-fragments" / "obs-defaults.md"
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
WORKFLOWS_DIR = ROOT / ".github" / "workflows"

# Markers so sync updates stay surgical.
BEGIN_RUNTIME = "  # BEGIN synced-from:.python-version:setup-python"
END_RUNTIME = "  # END synced-from:.python-version:setup-python"
BEGIN_RUNTIMES = "# BEGIN synced-from:.python-version:runtimes"
END_RUNTIMES = "# END synced-from:.python-version:runtimes"

_MARKED_RUNTIME = re.compile(
    re.escape(BEGIN_RUNTIME) + r".*?" + re.escape(END_RUNTIME),
    re.DOTALL,
)
_MARKED_RUNTIMES = re.compile(
    re.escape(BEGIN_RUNTIMES) + r".*?" + re.escape(END_RUNTIMES),
    re.DOTALL,
)
# pre-commit composite action cannot use python-version-file.
_PRECOMMIT_PYTHON = re.compile(
    r"(uses:\s*elastic/oblt-actions/pre-commit@v\d+\s*\n"
    r"\s+with:\s*\n"
    r'\s+python-version:\s*")[^"]+(")',
    re.MULTILINE,
)
_CONSUMER_PYTHON_FILE = re.compile(
    r"python-version-file:\s*['\"]?\.python-version['\"]?",
)
_SETUP_PYTHON_LITERAL = re.compile(
    r"(?m)^(\s+python-version:\s*['\"])([^'\"]+)(['\"])\s*$",
)


def load_python_version(path: pathlib.Path = PYTHON_VERSION_FILE) -> str:
    if not path.is_file():
        raise SystemExit(f"missing Python version file: {path}")
    version = path.read_text(encoding="utf-8").strip()
    if not version:
        raise SystemExit(f"{path}: expected a non-empty Python version")
    if not re.fullmatch(r"\d+\.\d+(?:\.\d+)?", version):
        raise SystemExit(
            f"{path}: expected major.minor or major.minor.patch, got {version!r}"
        )
    return version


def render_runtime_setup_block(version: str) -> str:
    return "\n".join(
        [
            BEGIN_RUNTIME,
            "  - name: Setup Python",
            "    # Control-plane pin (baked at compile time). Do not use",
            "    # python-version-file here — agent jobs check out the consumer",
            "    # repo, so .python-version would be the target's pin.",
            "    uses: actions/setup-python@v7",
            "    with:",
            f"      python-version: '{version}'",
            END_RUNTIME,
        ]
    )


def render_runtimes_block(version: str) -> str:
    return "\n".join(
        [
            BEGIN_RUNTIMES,
            "runtimes:",
            "  python:",
            f'    version: "{version}"',
            END_RUNTIMES,
        ]
    )


def apply_runtime_setup(text: str, version: str) -> str:
    block = render_runtime_setup_block(version)
    if _MARKED_RUNTIME.search(text):
        return _MARKED_RUNTIME.sub(block, text, count=1)
    # First-time upgrade from consumer .python-version delegation.
    # Do not use DOTALL here — nested .* causes catastrophic backtracking.
    legacy = re.compile(
        r"(?m)^  - name: Setup Python\n"
        r"(?:    .+\n)*?"
        r"      python-version-file:\s*['\"]?\.python-version['\"]?\s*\n",
    )
    if legacy.search(text):
        # Preserve a blank line before the next step.
        return legacy.sub(block + "\n\n", text, count=1)
    raise SystemExit(f"{RUNTIME_SETUP}: missing Setup Python block or sync markers")


def apply_obs_defaults(text: str, version: str) -> str:
    block = render_runtimes_block(version)
    if _MARKED_RUNTIMES.search(text):
        return _MARKED_RUNTIMES.sub(block, text, count=1)
    # Insert after frontmatter opening --- line's following keys: place before
    # the closing --- of the YAML frontmatter.
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end == -1:
            raise SystemExit(f"{OBS_DEFAULTS}: could not find frontmatter end")
        insert_at = end + 1  # keep leading newline of \n---
        return text[:insert_at] + block + "\n" + text[insert_at:]
    raise SystemExit(f"{OBS_DEFAULTS}: expected YAML frontmatter")


def apply_ci_precommit(text: str, version: str) -> str:
    if not _PRECOMMIT_PYTHON.search(text):
        raise SystemExit(
            f"{CI_WORKFLOW}: missing elastic/oblt-actions/pre-commit "
            "python-version input"
        )
    return _PRECOMMIT_PYTHON.sub(
        rf"\g<1>{version}\2",
        text,
        count=1,
    )


def validate_control_plane_setup_python(
    workflows_dir: pathlib.Path = WORKFLOWS_DIR,
) -> list[str]:
    """Control-plane setup-python must follow .python-version, not literals."""
    errors: list[str] = []
    if not workflows_dir.is_dir():
        return [f"missing workflows dir: {workflows_dir}"]
    for path in sorted(workflows_dir.glob("*.yml")) + sorted(
        workflows_dir.glob("*.yaml")
    ):
        if path.name.endswith(".lock.yml") or path.name.endswith(".lock.yaml"):
            continue
        if path.name.startswith("gh-aw-"):
            # Sources are markdown; locks checked separately.
            continue
        text = path.read_text(encoding="utf-8")
        if "actions/setup-python@" not in text:
            continue
        # Flag literal python-version next to setup-python (except none expected).
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if "actions/setup-python@" not in line:
                continue
            window = "\n".join(lines[i : i + 12])
            if "python-version-file:" in window and ".python-version" in window:
                continue
            if re.search(r"python-version:\s*['\"]?\d", window):
                try:
                    label = str(path.relative_to(ROOT))
                except ValueError:
                    label = str(path)
                errors.append(
                    f"{label}: setup-python should use "
                    "python-version-file: .python-version so bumps of the "
                    "root pin apply automatically"
                )
    return errors


def validate_locks_use_control_plane_pin(
    version: str,
    workflows_dir: pathlib.Path = WORKFLOWS_DIR,
) -> list[str]:
    """Compiled agent locks must bake the control-plane pin, not consumer file."""
    errors: list[str] = []
    if not workflows_dir.is_dir():
        return [f"missing workflows dir: {workflows_dir}"]
    for path in sorted(workflows_dir.glob("*.lock.yml")) + sorted(
        workflows_dir.glob("*.lock.yaml")
    ):
        text = path.read_text(encoding="utf-8")
        if "actions/setup-python@" not in text:
            continue
        if _CONSUMER_PYTHON_FILE.search(text):
            errors.append(
                f"{path.name}: still delegates via python-version-file: "
                ".python-version (consumer pin); recompile after syncing "
                "runtime-setup.md"
            )
        # Require at least one baked pin matching SSOT when Setup Python exists.
        if ("Setup Python" in text or "setup-python@" in text) and not re.search(
            rf"python-version:\s*['\"]?{re.escape(version)}['\"]?",
            text,
        ):
            errors.append(f"{path.name}: expected baked python-version: {version!r}")
    return errors


def sync(version: str) -> list[pathlib.Path]:
    changed: list[pathlib.Path] = []
    runtime_text = RUNTIME_SETUP.read_text(encoding="utf-8")
    new_runtime = apply_runtime_setup(runtime_text, version)
    if new_runtime != runtime_text:
        RUNTIME_SETUP.write_text(new_runtime, encoding="utf-8")
        changed.append(RUNTIME_SETUP)

    defaults_text = OBS_DEFAULTS.read_text(encoding="utf-8")
    new_defaults = apply_obs_defaults(defaults_text, version)
    if new_defaults != defaults_text:
        OBS_DEFAULTS.write_text(new_defaults, encoding="utf-8")
        changed.append(OBS_DEFAULTS)

    ci_text = CI_WORKFLOW.read_text(encoding="utf-8")
    new_ci = apply_ci_precommit(ci_text, version)
    if new_ci != ci_text:
        CI_WORKFLOW.write_text(new_ci, encoding="utf-8")
        changed.append(CI_WORKFLOW)

    return changed


def check(version: str) -> list[str]:
    errors: list[str] = []
    runtime_text = RUNTIME_SETUP.read_text(encoding="utf-8")
    expected_runtime = apply_runtime_setup(runtime_text, version)
    if expected_runtime != runtime_text:
        errors.append(
            f"{RUNTIME_SETUP.relative_to(ROOT)}: out of sync with "
            f".python-version ({version})"
        )

    defaults_text = OBS_DEFAULTS.read_text(encoding="utf-8")
    expected_defaults = apply_obs_defaults(defaults_text, version)
    if expected_defaults != defaults_text:
        errors.append(
            f"{OBS_DEFAULTS.relative_to(ROOT)}: out of sync with "
            f".python-version ({version})"
        )

    ci_text = CI_WORKFLOW.read_text(encoding="utf-8")
    expected_ci = apply_ci_precommit(ci_text, version)
    if expected_ci != ci_text:
        errors.append(
            f"{CI_WORKFLOW.relative_to(ROOT)}: pre-commit python-version "
            f"out of sync with .python-version ({version})"
        )

    errors.extend(validate_control_plane_setup_python())
    errors.extend(validate_locks_use_control_plane_pin(version))
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit 1 when pins drift from .python-version",
    )
    args = parser.parse_args(argv)
    version = load_python_version()

    if args.check:
        errors = check(version)
        if errors:
            for err in errors:
                print(err, file=sys.stderr)
            print(
                "Run: python3 scripts/sync_python_version.py && make compile-aw-check",
                file=sys.stderr,
            )
            return 1
        print(f"Python version pins match .python-version ({version})")
        return 0

    changed = sync(version)
    if not changed:
        print(f"Already in sync with .python-version ({version})")
        return 0
    for path in changed:
        print(f"Updated {path.relative_to(ROOT)}")
    print(
        "If GH-AW fragments changed, run: make compile-aw-check",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
