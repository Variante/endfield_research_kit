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
import io
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

DEFAULT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_INPUT  = DEFAULT_ROOT / "export_full/structured/StreamingAssets/Data/Json/GameplayConfig/DialogIdTable.json"
DEFAULT_OUTPUT = DEFAULT_ROOT / "export_full/recovered/dialog_id_table_index.json"

# Identifier extractor. Match standalone dlg_* / radio_* tokens, up to 80
# chars. `option_dlg_*` contains a syntactically valid `dlg_*` substring; the
# fixed-width negative lookbehind prevents those option-only rows from being
# misclassified as dialog roots or per-line runtime registrations.
_ID_RE = re.compile(rb'(?<!option_)(dlg_[A-Za-z0-9_]{2,80}|radio_[A-Za-z0-9_]{2,80})')

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
def _read_i32(raw: bytes, offset: int) -> tuple[int, int] | None:
    if offset < 0 or offset + 4 > len(raw):
        return None
    return int.from_bytes(raw[offset : offset + 4], "little", signed=True), offset + 4


def _read_memorypack_string(raw: bytes, offset: int) -> tuple[str | None, int] | None:
    decoded = _read_i32(raw, offset)
    if decoded is None:
        return None
    length, offset = decoded
    if length == -1:
        return None, offset
    if length < 0 or offset + length > len(raw):
        return None
    try:
        text = raw[offset : offset + length].decode("utf-8")
    except UnicodeDecodeError:
        return None
    return text, offset + length


def _read_string_list(raw: bytes, offset: int) -> tuple[list[str] | None, int] | None:
    decoded = _read_i32(raw, offset)
    if decoded is None:
        return None
    count, offset = decoded
    if count == -1:
        return None, offset
    if count < 0 or count > 100_000:
        return None
    values: list[str] = []
    for _ in range(count):
        item = _read_memorypack_string(raw, offset)
        if item is None:
            return None
        text, offset = item
        if text is None:
            return None
        values.append(text)
    return values, offset


def _skip_animation_curve(raw: bytes, offset: int) -> int | None:
    if offset >= len(raw):
        return None
    header = raw[offset]
    offset += 1
    if header == 0xFF:
        return offset
    if header != 0x03 or offset + 8 > len(raw):
        return None
    offset += 8  # preWrapMode, postWrapMode
    count_decoded = _read_i32(raw, offset)
    if count_decoded is None:
        return None
    keyframe_count, offset = count_decoded
    if keyframe_count < 0 or keyframe_count > 100_000:
        return None
    byte_count = keyframe_count * 28
    if offset + byte_count > len(raw):
        return None
    return offset + byte_count


def _skip_common_mask(raw: bytes, offset: int) -> int | None:
    if offset >= len(raw):
        return None
    header = raw[offset]
    offset += 1
    if header == 0xFF:
        return offset
    if header != 0x06 or offset + 16 > len(raw):
        return None
    offset += 16  # AudioBlackScreenBehaviour unmanaged payload
    offset = _skip_animation_curve(raw, offset)
    if offset is None or offset + 13 > len(raw):
        return None
    offset += 12  # fadeIn, fadeOut, CommonMaskType
    if raw[offset] not in (0, 1):
        return None
    return offset + 1


def _read_dialog_brief_info(
    raw: bytes,
    offset: int,
    expected_dialog_id: str,
) -> tuple[list[str], int] | None:
    if offset >= len(raw) or raw[offset] != 0x09:
        return None
    offset += 1
    offset = _skip_common_mask(raw, offset)
    if offset is None:
        return None
    offset = _skip_common_mask(raw, offset)
    if offset is None:
        return None

    dialog_id_decoded = _read_memorypack_string(raw, offset)
    if dialog_id_decoded is None:
        return None
    dialog_id, offset = dialog_id_decoded
    if dialog_id != expected_dialog_id:
        return None

    dialog_type_decoded = _read_i32(raw, offset)
    if dialog_type_decoded is None:
        return None
    _dialog_type, offset = dialog_type_decoded
    if offset >= len(raw) or raw[offset] not in (0, 1):
        return None
    offset += 1  # enableSeamlessStartInSameFrame

    if offset >= len(raw) or raw[offset] != 0x01:
        return None
    offset += 1  # LangKey object header
    interact_key_decoded = _read_memorypack_string(raw, offset)
    if interact_key_decoded is None:
        return None
    _interact_key, offset = interact_key_decoded

    npc_ids_decoded = _read_string_list(raw, offset)
    if npc_ids_decoded is None:
        return None
    _npc_ids, offset = npc_ids_decoded
    if offset >= len(raw) or raw[offset] not in (0, 1):
        return None
    offset += 1  # useBlackScreen

    timeline_ids_decoded = _read_string_list(raw, offset)
    if timeline_ids_decoded is None:
        return None
    timeline_ids, offset = timeline_ids_decoded
    return list(timeline_ids or []), offset


def extract_dialog_brief_info_records(raw: bytes) -> dict[str, list[str]]:
    """Decode the first complete DialogBriefInfo map by exact record boundary.

    Every returned key is an authoritative runtime registration.  Values are
    member-9 timeline ids and may be empty.
    """
    if len(raw) < 5 or raw[0] != 0x05:
        return {}
    count_decoded = _read_i32(raw, 1)
    if count_decoded is None:
        return {}
    declared_count, offset = count_decoded
    if declared_count <= 0:
        return {}
    out: dict[str, list[str]] = {}
    seen_dialog_ids: set[str] = set()
    for _ in range(declared_count):
        key_decoded = _read_memorypack_string(raw, offset)
        if key_decoded is None:
            return {}
        dialog_id, offset = key_decoded
        if not dialog_id or dialog_id in seen_dialog_ids:
            return {}
        seen_dialog_ids.add(dialog_id)
        brief_decoded = _read_dialog_brief_info(raw, offset, dialog_id)
        if brief_decoded is None:
            return {}
        timeline_ids, offset = brief_decoded
        out[dialog_id] = timeline_ids
    # The next top-level member is another 2,633-entry map in this build.  This
    # equality proves the first dictionary ended on its exact field boundary.
    next_count = _read_i32(raw, offset)
    if next_count is None or next_count[0] != declared_count:
        return {}
    return out


def extract_used_dialog_timeline_ids(raw: bytes) -> dict[str, list[str]]:
    """Return non-empty timeline membership from exact DialogBriefInfo rows."""
    return {
        dialog_id: timeline_ids
        for dialog_id, timeline_ids in extract_dialog_brief_info_records(raw).items()
        if timeline_ids
    }


def build_index(raw: bytes) -> dict:
    all_ids = sorted({m.group().decode("ascii") for m in _ID_RE.finditer(raw)})
    option_ids = sorted({m.group().decode("ascii") for m in _OPTION_RE.finditer(raw)})
    dialog_brief_records = extract_dialog_brief_info_records(raw)
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
