#!/usr/bin/env python3
"""
Annotate each webui conv JSON with its DialogIdTable registry status.

For each `dlg_*.json` / `misc_dlg_*.json` under `webui/data/lang/<lang>/conv/`,
read the matching entry from `export_full/recovered/dialog_id_table_index.json`
(produced by story_builder/dialog_registry.py) and write a `_debug.runtimeRegistry`
block summarising the runtime-side evidence:

  - registered:    bool, was the sceneKey present in DialogIdTable?
  - trunkCount:    int, number of distinct trunk indices (only when registered)
  - lineCount:     int, total per-line entries in DialogIdTable (only when registered)
  - lineCountWebui: int, number of lines in the webui conv (for cross-check)
  - reason:        short human-readable explanation

This is purely evidence surfacing -- no inference. The registry came directly
from the game's DialogIdTable binary, and this script just attaches it to
each scene that already exists in webui.
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for _path in (ROOT / "scripts",):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from scene_order_gap_shared import (  # noqa: E402
    build_runtime_registry_debug,
    load_dialog_id_registry,
)

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


def rewrite_conv(path: Path, registry: dict) -> bool:
    """Return True if the file was modified."""
    try:
        conv = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False

    scene_key = conv.get("key")
    if not isinstance(scene_key, str) or not scene_key:
        return False

    block = build_runtime_registry_debug(conv, dialog_id_registry=registry)

    debug = conv.get("_debug")
    if not isinstance(debug, dict):
        debug = {}
        conv["_debug"] = debug

    if block is None:
        if "runtimeRegistry" not in debug:
            return False
        del debug["runtimeRegistry"]
        path.write_text(json.dumps(conv, ensure_ascii=False), encoding="utf-8")
        return True

    if debug.get("runtimeRegistry") == block:
        return False
    debug["runtimeRegistry"] = block
    path.write_text(json.dumps(conv, ensure_ascii=False), encoding="utf-8")
    return True


def main():
    registry = load_dialog_id_registry()
    print(f"Loaded DialogIdTable registry: {len(registry)} entries")

    counts = {"registered": 0, "unregistered": 0, "unchanged": 0}
    conv_dirs = list((ROOT / "webui" / "data" / "lang").glob("*/conv"))
    for conv_dir in conv_dirs:
        lang = conv_dir.parent.name
        per_lang_registered = 0
        per_lang_unregistered = 0
        for path in sorted(conv_dir.glob("*.json")):
            if not (path.name.startswith("dlg_") or path.name.startswith("misc_dlg_")):
                continue
            changed = rewrite_conv(path, registry)
            try:
                conv = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            reg = conv.get("_debug", {}).get("runtimeRegistry", {})
            if reg.get("registered"):
                per_lang_registered += 1
                counts["registered"] += 1
            else:
                per_lang_unregistered += 1
                counts["unregistered"] += 1
            if not changed:
                counts["unchanged"] += 1
        print(f"  lang={lang}: registered={per_lang_registered}, unregistered={per_lang_unregistered}")

    print()
    print("Totals across all langs:")
    for k, v in counts.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
