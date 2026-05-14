from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    webui_script_dir = Path(__file__).resolve().parents[1]
    if str(webui_script_dir) not in sys.path:
        sys.path.insert(0, str(webui_script_dir))
    from story_builder.cli import main
else:
    from .cli import main


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)
