#!/usr/bin/env python3
"""
Extract Endfield's runtime DialogIdTable into a JSON registry.

DialogIdTable is the runtime's authoritative dialog registry: every dialog
the runtime can load must appear here. Each entry is a MemoryPack-serialized
DialogBriefInfo record keyed by dialog ID. We don't fully parse the binary,
but we extract the keys (ASCII tokens) and derive per-scene trunk/line
structure where present.

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
}

Used by scene_order_gap_shared.analyze_line_order to provide direct evidence
about runtime registration, independent of Timeline/LevelScript recovery.
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

DEFAULT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_INPUT  = DEFAULT_ROOT / "export_full/structured/StreamingAssets/Data/Json/GameplayConfig/DialogIdTable.json"
DEFAULT_OUTPUT = DEFAULT_ROOT / "export_full/recovered/dialog_id_table_index.json"

# Identifier extractor. Match dlg_* / radio_* tokens, up to 80 chars.
# Length lower bound 2 chars after the prefix to avoid garbage matches.
_ID_RE = re.compile(rb'(dlg_[A-Za-z0-9_]{2,80}|radio_[A-Za-z0-9_]{2,80})')

# Per-line form: <scene>_<trunkIdx>_<lineDigits>
# Examples: dlg_e10m3_1_1_001, dlg_a1m10_1_3_002.
_PER_LINE_RE = re.compile(r'^(?P<scene>dlg_[A-Za-z0-9_]+?)_(?P<trunk>[1-9]\d*)_(?P<line>\d{3,5})$')

# Dialog option form: option_<scene>_<groupIdx>_<optionDigits>.
# DialogOptionTable option suffixes are three digits; keeping this exact avoids
# accidentally swallowing printable bytes that follow the MemoryPack string.
_OPTION_RE = re.compile(rb'(option_dlg_[A-Za-z0-9_]+?_[1-9]\d*_\d{3})')
_OPTION_ID_RE = re.compile(
    r'^(?P<prefix>option_)(?P<scene>dlg_[A-Za-z0-9_]+?)_(?P<group>[1-9]\d*)_(?P<option>\d{3})$'
)


def build_index(raw: bytes) -> dict:
    all_ids = sorted({m.group().decode("ascii") for m in _ID_RE.finditer(raw)})
    option_ids = sorted({m.group().decode("ascii") for m in _OPTION_RE.finditer(raw)})

    per_line_by_scene: dict[str, dict[int, list[str]]] = defaultdict(lambda: defaultdict(list))
    options_by_scene: dict[str, dict[int, list[str]]] = defaultdict(lambda: defaultdict(list))
    root_keys: set[str] = set()

    for ident in all_ids:
        if ident.startswith("radio_"):
            root_keys.add(ident)
            continue
        m = _PER_LINE_RE.match(ident)
        if m:
            scene = m.group("scene")
            trunk = int(m.group("trunk"))
            per_line_by_scene[scene][trunk].append(ident)
        else:
            root_keys.add(ident)

    for ident in option_ids:
        m = _OPTION_ID_RE.match(ident)
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
        index[scene] = {
            "registered": True,
            "hasRootKey": scene in root_keys,
            "trunkCount": len(trunk_indices),
            "trunkIndices": trunk_indices,
            "lineCount": sum(len(trunks[t]) for t in trunk_indices),
            "linesByTrunk": {str(t): sorted(trunks[t]) for t in trunk_indices},
            "optionGroupCount": len(option_group_indices),
            "optionCount": sum(len(option_groups[t]) for t in option_group_indices),
            "optionsByGroup": {str(t): sorted(option_groups[t]) for t in option_group_indices},
        }
    return index


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

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
        print(f"Input:  {args.input}")
        print(f"Output: {args.output}")
        print(f"Total scenes registered:        {len(index)}")
        print(f"  with trunk/line decomposition: {with_decomp}")
        print(f"    of which multi-trunk:        {multi_trunk}")
        print(f"  with option registrations:     {with_options}")
        print(f"    option IDs extracted:        {option_count}")
        print(f"  root-key only (no per-line):   {root_only}")
        print(f"  radio entries:                 {radio_scenes}")


if __name__ == "__main__":
    main()
