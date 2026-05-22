"""Pytest hooks: make ``scripts/`` importable without installation."""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
_scripts_str = str(_SCRIPTS)
if _scripts_str not in sys.path:
    sys.path.insert(0, _scripts_str)
