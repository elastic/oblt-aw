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

The live autodoc E2E harness copies this file onto the default branch so
docs-patrol has a concrete undocumented public entrypoint within the
lookback window. The harness deletes the remote copy after the run.

Marker (must appear in E2E audit issue bodies for correlation):
E2E_AUTODOC_BAIT_MARKER
"""


def e2e_autodoc_public_entrypoint(config_path: str) -> dict[str, str]:
    """Public entrypoint with no repository documentation (intentional E2E bait)."""
    return {"config_path": config_path, "status": "ok"}
