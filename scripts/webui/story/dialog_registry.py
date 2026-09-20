#!/usr/bin/env python3
"""
Extract Endfield's runtime DialogIdTable into a JSON registry for Story builds.

DialogIdTable is the runtime's authoritative dialog registry: every dialog
the runtime can load must appear here. Each entry is a MemoryPack-serialized
DialogBriefInfo record keyed by dialog ID. The decoded record schema does not
contain branch or option-position fields, so this helper extracts only the
printable identifier vocabulary. Per-line/trunk structure below is token-shape
classification, not recovered runtime routing.

The runtime class for this table is `Beyond.Gameplay.DialogIdTable` with
records of type `Beyond.Gameplay.DialogIdTable.DialogBriefInfo` (confirmed by
scanning global-metadata.dat).

Output: a JSON map keyed by sceneKey -> {
    registered:    true,
    trunkCount:    N (number of distinct trunk indices),
    trunkIndices:  [int, ...],
    lineCount:     N (number of per-line entries in the table),
    linesByTrunk:  { trunkIdx: [<id>, ...] },
    optionCount:   N (number of option IDs in the table for this scene),
    optionsByGroup:{ groupIdx: [<option_id>, ...] },
    usedDialogTimelineIds: [<dlgtl_id>, ...] (authoritative runtime field),
}

Used by scene_order_gap_shared.analyze_line_order to provide direct evidence
about runtime registration, independent of Timeline/LevelScript recovery.
"""
from __future__ import annotations

import argparse
import json
import re
import struct
import sys
from collections import defaultdict
from pathlib import Path

from scripts.repo_paths import REPO_ROOT
from scripts.common import EXPORT_LAYOUT, WEBUI_BUILD_DIR
from scripts.game_data.memorypack.tables import (
    DIALOG_ID_TABLE_LINE_RE,
    DIALOG_ID_TABLE_OPTION_RAW_RE,
    DIALOG_ID_TABLE_OPTION_RE,
    parse_dialog_brief_info_records,
)

DEFAULT_ROOT = REPO_ROOT

DEFAULT_INPUT  = EXPORT_LAYOUT.json_dir / "GameplayConfig" / "DialogIdTable.json"
DEFAULT_OUTPUT = WEBUI_BUILD_DIR / "story" / "dialog_id_table_index.json"

_ID_RE = re.compile(
    rb"(?<!option_)(dlg_[A-Za-z0-9_]{2,80}|radio_[A-Za-z0-9_]{2,80})"
)

def _dialog_timeline_ids(raw: bytes) -> dict[str, list[str]]:
    try:
        records, _next_member_offset = parse_dialog_brief_info_records(raw)
    except (UnicodeDecodeError, struct.error, ValueError):
        return {}
    return {
        record["key"]: list(record["value"]["usedDialogTimelineIds"])
        for record in records
    }


def build_index(raw: bytes) -> dict:
    all_ids = sorted({m.group().decode("ascii") for m in _ID_RE.finditer(raw)})
    option_ids = sorted({m.group().decode("ascii") for m in DIALOG_ID_TABLE_OPTION_RAW_RE.finditer(raw)})
    dialog_brief_records = _dialog_timeline_ids(raw)
    used_timeline_ids = {
        dialog_id: timeline_ids
        for dialog_id, timeline_ids in dialog_brief_records.items()
        if timeline_ids
    }

    per_line_by_scene: dict[str, dict[int, list[str]]] = defaultdict(lambda: defaultdict(list))
    options_by_scene: dict[str, dict[int, list[str]]] = defaultdict(lambda: defaultdict(list))
    root_keys: set[str] = set()

    for ident in all_ids:
        if ident.startswith("radio_"):
            root_keys.add(ident)
            continue
        m = DIALOG_ID_TABLE_LINE_RE.match(ident)
        if m:
            scene = m.group("scene")
            trunk = int(m.group("trunk"))
            per_line_by_scene[scene][trunk].append(ident)
        else:
            root_keys.add(ident)

    for ident in option_ids:
        m = DIALOG_ID_TABLE_OPTION_RE.match(ident)
        if not m:
            continue
        scene = m.group("scene")
        group = int(m.group("group"))
        options_by_scene[scene][group].append(ident)

    # Scenes that appear ONLY through per-line entries also count as registered.
    # Option IDs live in the same table blob, but they are not enough by
    # themselves to prove that the scene has a runtime entry point.
    all_scenes = root_keys | set(per_line_by_scene)

    index: dict[str, dict] = {}
    for scene in sorted(all_scenes):
        trunks = per_line_by_scene.get(scene, {})
        trunk_indices = sorted(trunks)
        option_groups = options_by_scene.get(scene, {})
        option_group_indices = sorted(option_groups)
        registration_evidence: list[str] = []
        if scene in dialog_brief_records:
            registration_evidence.append("memorypack_record_key")
        if scene in root_keys:
            registration_evidence.append("printable_root_token")
        if scene in per_line_by_scene:
            registration_evidence.append("printable_line_token")
        index[scene] = {
            "registered": True,
            "memoryPackRecordKey": scene in dialog_brief_records,
            "registrationEvidence": registration_evidence,
            "hasRootKey": scene in root_keys,
            "trunkCount": len(trunk_indices),
            "trunkIndices": trunk_indices,
            "lineCount": sum(len(trunks[t]) for t in trunk_indices),
            "linesByTrunk": {str(t): sorted(trunks[t]) for t in trunk_indices},
            "optionGroupCount": len(option_group_indices),
            "optionCount": sum(len(option_groups[t]) for t in option_group_indices),
            "optionsByGroup": {str(t): sorted(option_groups[t]) for t in option_group_indices},
            "usedDialogTimelineCount": len(used_timeline_ids.get(scene, [])),
            "usedDialogTimelineIds": list(used_timeline_ids.get(scene, [])),
        }
    return index


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    if not args.input.is_file():
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text("{}\n", encoding="utf-8")
        if not args.quiet:
            print(f"Input missing: {args.input}")
            print(f"Output: {args.output}")
            print("DialogIdTable registry skipped; wrote empty registry.")
        return

    raw = args.input.read_bytes()
    index = build_index(raw)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")

    if not args.quiet:
        with_decomp  = sum(1 for v in index.values() if v["trunkCount"] > 0)
        multi_trunk  = sum(1 for v in index.values() if v["trunkCount"] > 1)
        root_only    = sum(1 for v in index.values() if v["trunkCount"] == 0)
        with_options = sum(1 for v in index.values() if v["optionCount"] > 0)
        option_count = sum(v["optionCount"] for v in index.values())
        radio_scenes = sum(1 for k in index if k.startswith("radio_"))
        with_timelines = sum(1 for v in index.values() if v["usedDialogTimelineCount"] > 0)
        timeline_count = sum(v["usedDialogTimelineCount"] for v in index.values())
        print(f"Input:  {args.input}")
        print(f"Output: {args.output}")
        print(f"Total scenes registered:        {len(index)}")
        print(f"  with trunk/line decomposition: {with_decomp}")
        print(f"    of which multi-trunk:        {multi_trunk}")
        print(f"  with option registrations:     {with_options}")
        print(f"    option IDs extracted:        {option_count}")
        print(f"  with authored Timeline IDs:    {with_timelines}")
        print(f"    Timeline IDs extracted:      {timeline_count}")
        print(f"  root-key only (no per-line):   {root_only}")
        print(f"  radio entries:                 {radio_scenes}")


if __name__ == "__main__":
    main()
