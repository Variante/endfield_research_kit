#!/usr/bin/env python3
"""
In-place rewrite of `warnings` arrays in webui conv JSON files to match the
current scene_order_gap_shared logic. Useful after tightening the criteria
for `sceneOrderDisorder` warnings without re-running build_story.py.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from scene_order_gap_shared import (  # noqa: E402
    build_scene_order_disorder_warning,
    load_dialog_id_registry,
)


_DIALOG_REGISTRY: dict | None = None


def rewrite_conv(path: Path) -> str | None:
    """Return one of: 'added', 'removed', 'replaced', None (unchanged)."""
    try:
        conv = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    new_warning = build_scene_order_disorder_warning(
        conv, dialog_id_registry=_DIALOG_REGISTRY
    )
    existing_warnings = conv.get("warnings") or []
    existing_index = None
    for i, w in enumerate(existing_warnings):
        if isinstance(w, dict) and w.get("code") == "sceneOrderDisorder":
            existing_index = i
            break

    if new_warning is None:
        if existing_index is None:
            return None
        del existing_warnings[existing_index]
        conv["warnings"] = existing_warnings
        outcome = "removed"
    else:
        if existing_index is None:
            conv["warnings"] = [new_warning, *existing_warnings]
            outcome = "added"
        else:
            if existing_warnings[existing_index] == new_warning:
                return None
            existing_warnings[existing_index] = new_warning
            conv["warnings"] = existing_warnings
            outcome = "replaced"

    path.write_text(json.dumps(conv, ensure_ascii=False), encoding="utf-8")
    return outcome


def main():
    global _DIALOG_REGISTRY
    _DIALOG_REGISTRY = load_dialog_id_registry()
    print(f"Loaded DialogIdTable registry: {len(_DIALOG_REGISTRY)} entries")

    conv_dirs = list((ROOT / "webui" / "data" / "lang").glob("*/conv"))
    if not conv_dirs:
        print("No conv directories found.")
        return

    totals = {"added": 0, "removed": 0, "replaced": 0, "unchanged": 0}
    for conv_dir in conv_dirs:
        lang = conv_dir.parent.name
        # All conv types: dlg_*, radio_*, env_*, nar_*, sns_*, misc_*,
        # wiki_*, etc. The authored-source-table recovery applies to all of
        # them now that we credit RadioTable, EnvTalkTable, SNSDialogTable,
        # RichContentTable, WikiTutorialPageTable, etc. (see
        # AUTHORED_SOURCE_TABLES in scene_order_gap_shared.py).
        for path in sorted(conv_dir.glob("*.json")):
            outcome = rewrite_conv(path)
            if outcome is None:
                totals["unchanged"] += 1
            else:
                totals[outcome] += 1
                if totals[outcome] <= 5:
                    print(f"  [{lang}] {outcome:>8}  {path.name}")
        print(f"-- lang={lang} done --")

    print()
    print("Totals across all langs:")
    for k, v in totals.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
