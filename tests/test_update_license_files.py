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

"""Unit tests for scripts/update_license_files.py."""

from __future__ import annotations

import pathlib
import sys


sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts"))

import update_license_files as ulf  # noqa: E402


class TestStripExistingHeaders:
    def test_strips_single_header(self) -> None:
        content = ulf.APACHE2_HEADER_HASH.rstrip() + "\n\nimport os"
        prefix, body = ulf._strip_existing_headers(content)
        assert prefix == ""
        assert body.startswith("import os")

    def test_strips_multiple_headers(self) -> None:
        header = ulf.APACHE2_HEADER_HASH.rstrip() + "\n\n"
        content = (
            header.replace("2026-2027", "2024")
            + header.replace("2026-2027", "2025")
            + "import os"
        )
        prefix, body = ulf._strip_existing_headers(content)
        assert "Copyright" not in body
        assert body.strip() == "import os"

    def test_preserves_shebang(self) -> None:
        content = (
            "#!/usr/bin/env bash\n" + ulf.APACHE2_HEADER_HASH.rstrip() + "\n\nset -e"
        )
        prefix, body = ulf._strip_existing_headers(content)
        assert prefix == "#!/usr/bin/env bash\n"
        assert "set -e" in body


class TestVerifyLicense:
    def test_verify_license_ok(self, tmp_path: pathlib.Path) -> None:
        (tmp_path / "LICENSE").write_text(
            "Apache License\nVersion 2.0\n\nTERMS AND CONDITIONS..."
        )
        assert ulf.verify_license(tmp_path) is True

    def test_verify_license_missing(self, tmp_path: pathlib.Path) -> None:
        assert ulf.verify_license(tmp_path) is False

    def test_verify_license_invalid(self, tmp_path: pathlib.Path) -> None:
        (tmp_path / "LICENSE").write_text("Not a license")
        assert ulf.verify_license(tmp_path) is False
