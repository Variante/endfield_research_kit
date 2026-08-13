#!/usr/bin/env python3
"""Write the envTalk attachment recovery report using the stable Story builder."""
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from story_builder.envtalk_attachment import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
