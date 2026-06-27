#!/usr/bin/env python3
"""Build the OCR-derived per-mission Story order reference for the WebUI.

The gameplay-video OCR pipeline (`build_gameplay_video_story_order.py`) writes a
full proposed order to
`reports/gameplay_video_ocr/story_order_ocr_proposed_story_order.json`. The WebUI
can only fetch files under `webui/`, so this script distills that proposal into a
small, standalone, read-only reference the WebUI loads in debug mode to compare
OCR order against static recovery and the editable override.

Usage:
    python scripts/story_recovery/build_webui_ocr_order.py
    python scripts/story_recovery/build_webui_ocr_order.py --proposed <path> --out <path>
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROPOSED_STORY_ORDER_PATH = (
    ROOT / "reports" / "gameplay_video_ocr" / "story_order_ocr_proposed_story_order.json"
)
WEBUI_OCR_ORDER_PATH = ROOT / "webui" / "data" / "story_order_ocr.json"

SCHEMA = "webuiStoryOrderOcr.v1"
NOTE = (
    "OCR-derived per-mission Story order, distilled from "
    "story_order_ocr_proposed_story_order.json. Read-only reference used by the "
    "WebUI debug mode to compare OCR order against static recovery and the "
    "editable override (overrides/story_order.json)."
)


def distill(proposed: dict) -> dict:
    """Trim a full proposed-order payload down to per-mission order lists."""
    missions_in = proposed.get("missions")
    if not isinstance(missions_in, dict):
        raise ValueError("proposed order payload has no 'missions' object")
    missions_out: dict[str, dict] = {}
    for mission_id, mission in sorted(missions_in.items()):
        if not isinstance(mission, dict):
            continue
        order = mission.get("order")
        if not isinstance(order, list):
            continue
        clean = [str(key) for key in order if isinstance(key, str) and key.strip()]
        if not clean:
            continue
        entry: dict[str, object] = {"order": clean}
        if mission.get("locked") is True:
            entry["locked"] = True
        missions_out[str(mission_id)] = entry
    return {
        "_schema": SCHEMA,
        "_note": NOTE,
        "_generatedAt": datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "_source": str(PROPOSED_STORY_ORDER_PATH.relative_to(ROOT)).replace("\\", "/"),
        "missions": missions_out,
    }


def build_webui_ocr_order(
    proposed_path: Path = PROPOSED_STORY_ORDER_PATH,
    out_path: Path = WEBUI_OCR_ORDER_PATH,
) -> Path:
    """Read the proposed order and write the trimmed WebUI reference file."""
    proposed = json.loads(proposed_path.read_text(encoding="utf-8"))
    distilled = distill(proposed)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(distilled, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proposed", type=Path, default=PROPOSED_STORY_ORDER_PATH)
    parser.add_argument("--out", type=Path, default=WEBUI_OCR_ORDER_PATH)
    args = parser.parse_args(argv)
    if not args.proposed.is_file():
        print(f"error: proposed order not found: {args.proposed}", file=sys.stderr)
        print("Run build_gameplay_video_story_order.py first.", file=sys.stderr)
        return 1
    out = build_webui_ocr_order(args.proposed, args.out)
    payload = json.loads(out.read_text(encoding="utf-8"))
    print(
        f"Wrote {out.relative_to(ROOT)} "
        f"({len(payload.get('missions', {}))} mission order list(s))"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
