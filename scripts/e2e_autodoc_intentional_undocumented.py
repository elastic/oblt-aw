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

"""E2E bait: intentional undocumented public API for autodoc audit.

Checked-in live E2E fixture for obs:autodoc. Docs-patrol skips this path unless
E2E additional-instructions explicitly request evaluation. See
docs/testing/autodoc-e2e-bait.md.

Fixture marker (issue correlation also uses the per-run token from E2E
instructions):
E2E_AUTODOC_BAIT_MARKER
"""


def e2e_autodoc_public_entrypoint(config_path: str) -> dict[str, str]:
    """Public entrypoint with no repository documentation (intentional E2E bait)."""
    return {"config_path": config_path, "status": "ok"}
