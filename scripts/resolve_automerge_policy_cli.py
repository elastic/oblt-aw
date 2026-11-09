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
Resolve consumer automerge policy from ``apm.yml`` for GitHub Actions.

Environment:
  REPO_ROOT  Consumer repository root (default: cwd)
  ORG_KEY    Consuming org key (default: obs)

Writes ``automerge-policy-json`` to ``GITHUB_OUTPUT`` (single-line JSON).
Also prints the JSON object to stdout for local debugging.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from apm_agentic_assets import resolve_automerge_policy
from common import append_multiline_github_output


def main() -> int:
    repo_root = Path(os.environ.get("REPO_ROOT", ".")).resolve()
    org_key = os.environ.get("ORG_KEY", "obs").strip() or "obs"
    policy = resolve_automerge_policy(repo_root=repo_root, org_key=org_key)
    payload = json.dumps(policy, separators=(",", ":"), sort_keys=True)
    append_multiline_github_output("automerge-policy-json", payload)
    print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
