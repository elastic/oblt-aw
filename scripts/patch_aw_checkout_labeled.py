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

"""Inject a runtime patch so same-repo bot ``labeled`` events pass PR checkout.

github/gh-aw Checkout PR branch trusts same-repository Bot senders only for
``opened``, ``synchronize``, ``ready_for_review``, and ``reopened``. Automerge
autoapprove wakes on App-applied ``oblt-aw/ai/merge-ready`` (``labeled``), so
Vault App actors fail with collaborator permission ``none`` (github/gh-aw#71151).
Upstream #72074 documented that gap as intentional; we cannot land the runtime
fix in gh-aw from Elastic.

This post-compile step (Makefile ``compile-aw``, after ``wire_ephemeral_token``)
inserts a step into ``gh-aw-autoapprove.lock.yml`` that rewrites the downloaded
``checkout_pr_branch.cjs`` allowlist to include ``labeled`` before Checkout PR
branch runs. Fail closed if the expected marker is missing so compiler bumps
cannot silently ship an unpatched lock. Idempotent. Remove when upstream covers
``labeled`` (or drop this workflow from TARGET_LOCK_NAMES).
"""

from __future__ import annotations

import sys
from pathlib import Path

STEP_MARKER = "oblt-aw:patch-aw-checkout-labeled"
STEP_NAME = "Patch checkout trust for labeled bot PRs"
CHECKOUT_STEP = "      - name: Checkout PR branch\n"

# Exact allowlist string from github/gh-aw setup action (v0.92.x pins).
EXPECTED_TRUSTED_BOT_LINE = (
    "const TRUSTED_BOT_PR_ACTIONS = "
    '["opened", "synchronize", "ready_for_review", "reopened"];'
)
PATCHED_TRUSTED_BOT_LINE = (
    "const TRUSTED_BOT_PR_ACTIONS = "
    '["opened", "synchronize", "ready_for_review", "reopened", "labeled"];'
)

TARGET_LOCK_NAMES: tuple[str, ...] = ("gh-aw-autoapprove.lock.yml",)

# YAML step inserted immediately before each Checkout PR branch step.
# Indentation matches compiler-emitted agent job steps (6-space list item).
# Runtime rewrite uses a quoted heredoc so lock YAML does not fight nested quotes.
INJECTED_STEP = f"""\
      - name: {STEP_NAME}
        # {STEP_MARKER} — temporary until github/gh-aw#71151 covers labeled
        run: |
          set -euo pipefail
          file="${{RUNNER_TEMP}}/gh-aw/actions/checkout_pr_branch.cjs"
          if [[ ! -f "$file" ]]; then
            echo "::error::checkout_pr_branch.cjs missing at $file (setup action destination changed?)"
            exit 1
          fi
          export OBLT_AW_CHECKOUT_PR_BRANCH_CJS="$file"
          python3 <<'PY'
          from pathlib import Path
          import os
          import re
          import sys

          path = Path(os.environ["OBLT_AW_CHECKOUT_PR_BRANCH_CJS"])
          text = path.read_text(encoding="utf-8")
          old = {EXPECTED_TRUSTED_BOT_LINE!r}
          new = {PATCHED_TRUSTED_BOT_LINE!r}
          if old in text:
              path.write_text(text.replace(old, new, 1), encoding="utf-8")
              print("Patched TRUSTED_BOT_PR_ACTIONS to include labeled")
              sys.exit(0)
          # Upstream already trusts labeled (or a prior patch ran).
          if re.search(
              r"TRUSTED_BOT_PR_ACTIONS\\s*=\\s*\\[[^\\]]*\\blabeled\\b",
              text,
          ):
              print("labeled already in TRUSTED_BOT_PR_ACTIONS; skipping patch")
              sys.exit(0)
          print(
              "::error::TRUSTED_BOT_PR_ACTIONS marker not found or changed in "
              f"{{path}}",
              file=sys.stderr,
          )
          print(
              "::error::Update scripts/patch_aw_checkout_labeled.py for the "
              "new gh-aw setup action shape",
              file=sys.stderr,
          )
          sys.exit(1)
          PY
"""


def inject_patch_steps(text: str) -> str:
    """Insert the labeled-trust patch step before each Checkout PR branch step.

    Raises ValueError when Checkout PR branch is present but the expected
    surrounding shape cannot be patched safely.
    """
    if STEP_MARKER in text:
        return text
    if CHECKOUT_STEP not in text:
        raise ValueError(
            "Checkout PR branch step not found; refuse to leave autoapprove "
            "without a labeled checkout patch"
        )

    parts = text.split(CHECKOUT_STEP)
    if len(parts) < 2:
        raise ValueError("failed to split on Checkout PR branch step")

    rebuilt = [parts[0]]
    for chunk in parts[1:]:
        rebuilt.append(INJECTED_STEP)
        if not INJECTED_STEP.endswith("\n"):
            rebuilt.append("\n")
        rebuilt.append(CHECKOUT_STEP)
        rebuilt.append(chunk)
    return "".join(rebuilt)


def process_lock_file(path: Path) -> bool:
    """Rewrite one lock file. Return True when the file changed."""
    original = path.read_text(encoding="utf-8")
    updated = inject_patch_steps(original)
    if updated == original:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    workflows = repo_root / ".github" / "workflows"
    changed = 0
    for name in TARGET_LOCK_NAMES:
        lock_file = workflows / name
        if not lock_file.is_file():
            print(f"error: missing target lock {lock_file}", file=sys.stderr)
            return 1
        try:
            if process_lock_file(lock_file):
                print(f"  patched {lock_file.name}")
                changed += 1
            else:
                print(f"  unchanged {lock_file.name}")
        except ValueError as exc:
            print(f"error: {lock_file.name}: {exc}", file=sys.stderr)
            return 1
    print(f"Patched labeled checkout trust in {changed} lock file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
