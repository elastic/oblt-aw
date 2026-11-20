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

"""Parse and apply Buildkite log tail depth for estc-pr-buildkite-detective.

The GH-AW prefetch step keeps a self-contained copy of this logic (consumer
checkouts do not ship control-plane scripts). Unit tests cover this module;
integration wiring asserts the lock env binding and wrapper null-only default.
"""

from __future__ import annotations

LOG_TAIL_DEFAULT = 150
LOG_TAIL_MAX = 2000


class BuildkiteLogTailError(ValueError):
    """Invalid ``buildkite-log-tail-lines`` value."""


def parse_buildkite_log_tail_lines(
    raw: str | None,
    *,
    default: int = LOG_TAIL_DEFAULT,
    max_lines: int = LOG_TAIL_MAX,
) -> int:
    """Parse a tail-depth string from env / workflow input.

    Empty or missing ``raw`` returns ``default``. Non-integers and values
    outside ``1..max_lines`` raise :class:`BuildkiteLogTailError` (including
    ``0``) so callers fail closed before any Buildkite fetch.
    """
    text = (raw or "").strip()
    if not text:
        return default
    try:
        value = int(text)
    except ValueError as exc:
        raise BuildkiteLogTailError(
            f"buildkite-log-tail-lines must be an integer (got {text!r})"
        ) from exc
    if value < 1 or value > max_lines:
        raise BuildkiteLogTailError(
            f"buildkite-log-tail-lines must be between 1 and {max_lines} (got {value})"
        )
    return value


def take_log_tail(lines: list[str], tail_lines: int) -> list[str]:
    """Return the last ``tail_lines`` entries from ``lines``."""
    if tail_lines < 1:
        raise BuildkiteLogTailError(
            f"buildkite-log-tail-lines must be between 1 and {LOG_TAIL_MAX} "
            f"(got {tail_lines})"
        )
    return lines[-tail_lines:]
