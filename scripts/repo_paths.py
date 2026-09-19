"""Repository root, resolved without per-module depth arithmetic."""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

__all__ = ["REPO_ROOT"]
