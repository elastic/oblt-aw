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
Automate license headers, NOTICE, and LICENSE consistency.

Usage:
  python scripts/update_license_files.py           # Add/update headers, sync NOTICE
  python scripts/update_license_files.py --check  # Verify only, exit 1 if changes needed
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Apache 2.0 header content (each line prefixed with comment char when building)
_APACHE2_HEADER_LINES = [
    "Copyright 2026-2027 Elasticsearch B.V.",
    "",
    'Licensed under the Apache License, Version 2.0 (the "License");',
    "you may not use this file except in compliance with the License.",
    "You may obtain a copy of the License at",
    "",
    "    http://www.apache.org/licenses/LICENSE-2.0",
    "",
    "Unless required by applicable law or agreed to in writing,",
    "software distributed under the License is distributed on an",
    '"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY',
    "KIND, either express or implied.  See the License for the",
    "specific language governing permissions and limitations",
    "under the License.",
]


def _build_header(comment_prefix: str) -> str:
    """Build Apache 2.0 header with the given comment prefix (# or //)."""
    return "\n".join(
        (comment_prefix + " " + line).rstrip() if line else comment_prefix
        for line in _APACHE2_HEADER_LINES
    )


# Exposed for tests
APACHE2_HEADER_HASH = _build_header("#")

# Files/patterns that must have the Apache 2.0 header
# Note: YAML workflow and config files are excluded; GitHub Actions YAML does not
# carry per-file Apache headers in this repository.
HEADER_GLOBS = [
    "scripts/*.py",
    "scripts/*.sh",
    "scripts/*.ts",
    "tests/**/*.ts",
]

# Exclude empty files and generated/vendor
# Match .git only as path segment (e.g. /.git/) to avoid excluding paths like "repo.git"
HEADER_EXCLUDE = re.compile(r"(\.mypy_cache|node_modules|__pycache__|/\.git/|/\.git$)")

NOTICE_CONTENT = """Agentic Workflows for Elastic Observability projects
Copyright 2026-2027 Elasticsearch B.V.

This project is licensed under the Apache License, Version 2.0 - https://www.apache.org/licenses/LICENSE-2.0
A copy of the Apache License, Version 2.0 is provided in the 'LICENSE' file.
"""


def repo_root() -> Path:
    """Return repository root (directory containing .git or LICENSE)."""
    root = Path(__file__).resolve().parent.parent
    if not (root / "LICENSE").exists():
        raise SystemExit("LICENSE not found; run from repository root")
    return root


def collect_header_files(root: Path) -> list[Path]:
    """Collect files that should have license headers."""
    files: list[Path] = []
    for pattern in HEADER_GLOBS:
        for p in root.glob(pattern):
            if p.is_file() and not HEADER_EXCLUDE.search(str(p)):
                files.append(p)
    return sorted(set(files))


# Regex to match a single Apache 2.0 header block (# or // style).
# Closing line is either "# under the License." (canonical here) or a wrapped
# variant ending with "# limitations under the License." (still Apache 2.0 boilerplate).
_HEADER_BLOCK_RE = re.compile(
    r"^\s*(?:#|//) Copyright 20\d{2}(?:-20\d{2})? Elasticsearch B\.V\.\s*\n"
    r"(?:\s*(?:#|//).*\n)*?"
    r"\s*(?:#|//) (?:limitations )?under the License\.\s*\n"
    r"(?:\s*(?:#|//)\s*\n)*"
    r"\s*",
    re.MULTILINE,
)


def _strip_existing_headers(text: str) -> tuple[str, str]:
    """
    Remove all leading Apache 2.0 header blocks. Returns (prefix, body).
    prefix: shebang if present, else empty string.
    body: content after all header blocks.
    """
    prefix = ""

    # Repeatedly extract shebang and strip headers (handles header+shebang+header)
    while True:
        if text.lstrip().startswith("#!"):
            first_line = text.split("\n", 1)[0]
            prefix = first_line + "\n"
            text = text[len(prefix) :]
        # Remove all consecutive header blocks from the start
        if _HEADER_BLOCK_RE.match(text):
            text = _HEADER_BLOCK_RE.sub("", text, count=1)
        else:
            break

    return prefix, text.lstrip("\n")


def _header_for_path(path: Path) -> str:
    """Return the appropriate header for the file extension."""
    suffix = path.suffix.lower()
    prefix = "//" if suffix in (".ts", ".tsx", ".js", ".mjs", ".cjs") else "#"
    return _build_header(prefix)


def add_or_update_header(path: Path) -> str | None:
    """
    Add or update the license header. Returns new content if changed, else None.
    Strips any existing header blocks first to avoid duplicates.
    """
    if path.stat().st_size == 0:
        return None

    text = path.read_text(encoding="utf-8")
    header = _header_for_path(path)
    prefix, body = _strip_existing_headers(text)

    # Check if body already has our exact header
    expected = header.rstrip() + "\n\n"
    if body.startswith(expected) or body == header.rstrip():
        return None

    # Insert header
    new_body = header.rstrip() + "\n\n" + body

    result = prefix + new_body
    if result != text:
        return result
    return None


def sync_notice(root: Path) -> bool:
    """Sync NOTICE.txt from NOTICE_CONTENT. Returns True if changed."""
    notice_txt = root / "NOTICE.txt"
    current = notice_txt.read_text(encoding="utf-8") if notice_txt.exists() else ""
    if current.strip() != NOTICE_CONTENT.strip():
        notice_txt.write_text(NOTICE_CONTENT, encoding="utf-8")
        return True
    return False


def verify_license(root: Path) -> bool:
    """Verify LICENSE exists and contains Apache 2.0."""
    license_path = root / "LICENSE"
    if not license_path.exists():
        return False
    text = license_path.read_text(encoding="utf-8")
    return "Apache License" in text and "Version 2.0" in text


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Update license headers, NOTICE, and verify LICENSE."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify only; exit 1 if updates would be needed",
    )
    args = parser.parse_args()
    root = repo_root()

    changed = False

    # 1. Headers
    for path in collect_header_files(root):
        new_content = add_or_update_header(path)
        if new_content is not None:
            if args.check:
                print(f"Would update: {path.relative_to(root)}")
                changed = True
            else:
                path.write_text(new_content, encoding="utf-8")
                print(f"Updated: {path.relative_to(root)}")
                changed = True

    # 2. NOTICE sync
    if sync_notice(root):
        if args.check:
            print("Would update: NOTICE.txt")
            changed = True
        else:
            print("Updated: NOTICE.txt")
            changed = True

    # 3. LICENSE verification
    if not verify_license(root):
        print(
            "Error: LICENSE missing or invalid (expected Apache 2.0)", file=sys.stderr
        )
        return 2

    if args.check and changed:
        print("Run: python3 scripts/update_license_files.py")
        return 1
    if changed:
        print("License files updated. Stage changes and commit again.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
