#!/usr/bin/env python3
"""Build the OCR-derived per-mission Story order reference for the WebUI.

The gameplay-video OCR matcher (`ocr_story_order.py match`) writes an
OCR-observed proposal to
`reports/gameplay_video_ocr/story_order_ocr_proposed_story_order.json`. The WebUI
can only fetch files under `webui/`, so this script distills that proposal into a
small, standalone, read-only reference the WebUI loads in debug mode to compare
OCR order against static recovery and the editable override.

Usage:
    python scripts/story_recovery/ocr_story_order.py publish
    python scripts/story_recovery/ocr_story_order.py publish --proposed <path> --out <path>
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from scripts.common import safe_key
from scripts.story_builder.mission_recovery import natural_key

ROOT = Path(__file__).resolve().parents[3]
PROPOSED_STORY_ORDER_PATH = (
    ROOT / "reports" / "gameplay_video_ocr" / "story_order_ocr_proposed_story_order.json"
)
WEBUI_OCR_ORDER_PATH = ROOT / "webui" / "data" / "story_order_ocr.json"

SCHEMA = "webuiStoryOrderOcr.v1"
NOTE = (
    "OCR-observed per-mission Story order, distilled from "
    "story_order_ocr_proposed_story_order.json. The source proposal contains "
    "only accepted gameplay-video OCR text matches and is not seeded from "
    "overrides/story_order.json."
)


def build_proposed_story_order(
    *,
    video_summaries: list[dict],
    min_sequence_keys: int,
) -> tuple[dict, list[dict]]:
    """Build a proposal solely from accepted OCR-observed keys."""
    proposal_rows: list[dict] = []
    missions: dict[str, dict] = {}
    by_mission: dict[str, list[dict]] = defaultdict(list)
    for video in video_summaries:
        for mission, sequence in (video.get("observedSequences") or {}).items():
            if sequence:
                by_mission[safe_key(mission)].append(
                    {"video": video.get("video"), "sequence": sequence}
                )

    for mission in sorted((key for key in by_mission if key), key=natural_key):
        rows = by_mission[mission]
        observed_keys: list[str] = []
        linked_entries_by_key: dict[str, dict] = {}
        for row in rows:
            for item in row["sequence"]:
                key = safe_key(item.get("key"))
                if key and (not observed_keys or observed_keys[-1] != key):
                    observed_keys.append(key)
                actual_mission = safe_key(item.get("actualMission"))
                link_reason = safe_key(item.get("linkReason"))
                if key and actual_mission and actual_mission != mission:
                    linked_entries_by_key.setdefault(
                        key,
                        {
                            "key": key,
                            "actualMission": actual_mission,
                            "linkReason": link_reason or "ocr-match",
                            "firstTime": item.get("firstTime"),
                        },
                    )

        deduped = list(dict.fromkeys(observed_keys))
        videos = [row["video"] for row in rows]
        included = len(deduped) >= min_sequence_keys
        if included:
            missions[mission] = {"order": deduped}
        proposal_rows.append(
            {
                "mission": mission,
                "existingActiveOrder": False,
                "locked": False,
                "observedKeys": deduped,
                "detectedKeys": deduped,
                "proposalKeys": deduped if included else [],
                "linkedEntries": (
                    [
                        linked_entries_by_key[key]
                        for key in deduped
                        if key in linked_entries_by_key
                    ]
                    if included
                    else []
                ),
                "videoRefLinks": [],
                "indexedInferences": [],
                "possiblyUnusedKeys": [],
                "changed": False,
                "included": included,
                **({} if included else {"skipReason": "insufficient-ocr-evidence"}),
                "changedKeys": [],
                "insertedKeys": [],
                "orderLength": len(deduped) if included else 0,
                "videos": videos,
            }
        )

    return {
        "_schema": "storyOrder.ocrObserved.v1",
        "_note": (
            "OCR-observed per-mission Story file order. Each missions.<mission>.order "
            "array contains only keys directly accepted from gameplay-video OCR text "
            "matching. This file is not seeded from overrides/story_order.json and "
            "does not include locked/manual/static/inferred order entries."
        ),
        "missions": missions,
    }, proposal_rows


def distill(
    proposed: dict,
    *,
    source_path: Path = PROPOSED_STORY_ORDER_PATH,
) -> dict:
    """Trim an OCR-observed proposal down to per-mission order lists."""
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
        missions_out[str(mission_id)] = {"order": clean}
    try:
        source_label = str(source_path.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        source_label = str(source_path.resolve()).replace("\\", "/")
    return {
        "_schema": SCHEMA,
        "_note": NOTE,
        "_generatedAt": datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "_source": source_label,
        "missions": missions_out,
    }


def build_webui_ocr_order(
    proposed_path: Path = PROPOSED_STORY_ORDER_PATH,
    out_path: Path = WEBUI_OCR_ORDER_PATH,
) -> Path:
    """Read the proposed order and write the trimmed WebUI reference file."""
    proposed_path = proposed_path.resolve()
    out_path = out_path.resolve()
    proposed = json.loads(proposed_path.read_text(encoding="utf-8"))
    distilled = distill(proposed, source_path=proposed_path)
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
        print("Run ocr_story_order.py match first.", file=sys.stderr)
        return 1
    out = build_webui_ocr_order(args.proposed, args.out)
    payload = json.loads(out.read_text(encoding="utf-8"))
    print(
        f"Wrote {out.relative_to(ROOT)} "
        f"({len(payload.get('missions', {}))} mission order list(s))"
    )
    return 0
