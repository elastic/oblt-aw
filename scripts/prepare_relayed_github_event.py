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

"""CLI: prepare github.event JSON for workflow_dispatch relay inputs."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from ingress_github_context import prepare_relayed_github_event_json


def main() -> int:
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        print("GITHUB_EVENT_PATH is required", file=sys.stderr)
        return 1

    event = json.loads(Path(event_path).read_text(encoding="utf-8"))
    if not isinstance(event, dict):
        print("github.event payload must be a JSON object", file=sys.stderr)
        return 1

    try:
        payload_json, mode = prepare_relayed_github_event_json(event)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    mode_output = os.environ.get("RELAY_PREPARE_MODE_OUTPUT", "").strip()
    if mode_output:
        Path(mode_output).write_text(mode, encoding="utf-8")

    print(payload_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
