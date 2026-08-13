"""Focused MemoryPack decoder implementation extracted from the retired Data-page builder."""

from __future__ import annotations

import math
import re
import struct
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .core import (
    MEMORYPACK_NULL_COUNT,
    MEMORYPACK_SCHEMA_SOURCE_NOTE,
    STRING_SAMPLE_MAX_CHARS,
    format_offset,
    read_memorypack_f32,
    read_memorypack_i32,
    read_memorypack_u32_count,
    read_memorypack_utf8_string,
    require_memorypack_non_null_string,
    require_memorypack_string,
)
from .schemas import MEMORYPACK_FIELD_SCHEMAS


BAMBOO_RAFT_TASK_TABLE_REL = "Json/NonGeneratedConfigs/BambooRaftTaskTable.json"


BAMBOO_RAFT_TASK_ROOT_MEMBER_COUNT = 1


BAMBOO_RAFT_TASK_VALUE_MEMBER_COUNT = 2


BAMBOO_RAFT_TASK_REF_MEMBER_COUNT = 2


DAMAGE_TEXT_REL = "Json/GPUISystemConfig/damage_text.json"


DAMAGE_TEXT_ROOT_MEMBER_COUNT = 5


DAMAGE_TEXT_ROW_MEMBER_COUNT = 6


DAMAGE_TEXT_ANIMATION_MEMBER_COUNT = 5


DAMAGE_TEXT_NODE_MEMBER_COUNT = 6


DIALOG_ID_TABLE_REL = "Json/GameplayConfig/DialogIdTable.json"


DIALOG_ID_TABLE_ROOT_MEMBER_COUNT = 5


DIALOG_ID_TABLE_BRIEF_MEMBER_COUNT = 7


DIALOG_ID_TABLE_KEY_RE = re.compile(r"^(?:dlg|radio)_[A-Za-z0-9_]{2,140}$")


DIALOG_ID_TABLE_RAW_ID_RE = re.compile(rb"(dlg_[A-Za-z0-9_]{2,80}|radio_[A-Za-z0-9_]{2,80})")


DIALOG_ID_TABLE_LINE_RE = re.compile(r"^(?P<scene>dlg_[A-Za-z0-9_]+?)_(?P<trunk>[1-9]\d*)_(?P<line>\d{3,5})$")


DIALOG_ID_TABLE_OPTION_RAW_RE = re.compile(rb"(option_dlg_[A-Za-z0-9_]+?_[1-9]\d*_\d{3})")


DIALOG_ID_TABLE_OPTION_RE = re.compile(r"^option_(?P<scene>dlg_[A-Za-z0-9_]+?)_(?P<group>[1-9]\d*)_(?P<option>\d{3})$")


MODEL_VIEW_STATE_CONTROLLER_MEMBER_COUNT = 7


def scan_length_prefixed_utf8_string_hits(
    data: bytes,
    *,
    start: int = 0,
    max_scan_bytes: int | None = None,
    max_samples: int = 128,
    min_length: int = 2,
    max_length: int = 160,
) -> list[dict[str, Any]]:
    end = len(data) if max_scan_bytes is None else min(len(data), start + max_scan_bytes)
    hits: list[dict[str, Any]] = []
    seen: set[tuple[int, str]] = set()
    for pos in range(max(start, 0), max(start, end - 4)):
        length = struct.unpack_from("<I", data, pos)[0]
        if length < min_length or length > max_length or pos + 4 + length > end:
            continue
        raw = data[pos + 4:pos + 4 + length]
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        if any(ord(ch) < 32 for ch in text):
            continue
        if not any(ch.isalnum() for ch in text):
            continue
        key = (pos, text)
        if key in seen:
            continue
        seen.add(key)
        hits.append({"offset": format_offset(pos), "length": length, "value": text})
        if len(hits) >= max_samples:
            break
    return hits


def unique_strings(values: list[str], limit: int) -> list[str]:
    out: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in out:
            out.append(text)
            if len(out) >= limit:
                break
    return out


def find_length_prefixed_utf8_tail_value(data: bytes, value: str, *, trailing_bytes: int = 1) -> tuple[int, int] | None:
    raw = value.encode("utf-8")
    marker = struct.pack("<I", len(raw)) + raw
    pos = data.rfind(marker)
    if pos < 0:
        return None
    end = pos + len(marker)
    if end + trailing_bytes != len(data):
        return None
    return pos, end


def decode_model_view_state_controller_memorypack(path: Path, data: bytes, size: int) -> dict[str, Any] | None:
    schema = MEMORYPACK_FIELD_SCHEMAS.get("ModelViewStateControllerData")
    if not schema or not data or data[0] != MODEL_VIEW_STATE_CONTROLLER_MEMBER_COUNT:
        return None

    def read_u32_count(offset: int, field: str, *, max_count: int = 4096) -> tuple[int | None, int, str | None]:
        if offset + 4 > len(data):
            return None, offset, f"{field}:truncated-count"
        count = struct.unpack_from("<I", data, offset)[0]
        offset += 4
        if count == MEMORYPACK_NULL_COUNT:
            return None, offset, None
        if count > max_count:
            return count, offset, f"{field}:large-count={count}"
        return count, offset, None

    stem = path.stem
    tail = find_length_prefixed_utf8_tail_value(data, stem, trailing_bytes=1)
    if not tail:
        return None
    model_id_offset, model_id_end = tail
    pre_tick_raw = data[model_id_end]
    if pre_tick_raw not in (0, 1):
        return None
    pre_tick_animator = bool(pre_tick_raw)

    offset = 1
    camera_count, offset, err = read_u32_count(offset, "cameraSignalSourceAssetHashes")
    if err or camera_count is None:
        return None
    if offset + camera_count * 8 > len(data):
        return None
    camera_hashes = [f"0x{struct.unpack_from('<Q', data, offset + index * 8)[0]:016x}" for index in range(camera_count)]
    offset += camera_count * 8

    clip_count, offset, err = read_u32_count(offset, "clipAssetInfos")
    if err or clip_count is None:
        return None
    clip_infos: list[dict[str, Any]] = []
    for index in range(clip_count):
        if offset + 13 > len(data) or data[offset] != 2:
            return None
        member_count = data[offset]
        hash_value = struct.unpack_from("<Q", data, offset + 1)[0]
        clip_name, next_offset, err = read_memorypack_utf8_string(data, offset + 9, max_length=512)
        if err or clip_name is None:
            return None
        clip_infos.append({
            "index": index,
            "memberCount": member_count,
            "hash": f"0x{hash_value:016x}",
            "name": clip_name,
        })
        offset = next_offset

    effect_count, offset, err = read_u32_count(offset, "effectIds")
    if err or effect_count is None:
        return None
    effect_ids: list[str] = []
    for _ in range(effect_count):
        effect_id, offset, err = read_memorypack_utf8_string(data, offset, max_length=512)
        if err or effect_id is None:
            return None
        effect_ids.append(effect_id)

    emissive_count, offset, err = read_u32_count(offset, "emissiveConfigHashes")
    if err or emissive_count is None:
        return None
    if offset + emissive_count * 8 > len(data):
        return None
    emissive_hashes = [
        f"0x{struct.unpack_from('<Q', data, offset + index * 8)[0]:016x}"
        for index in range(emissive_count)
    ]
    offset += emissive_count * 8

    model_animator_count, model_animator_body_offset, err = read_u32_count(offset, "modelAnimatorDatas")
    if err or model_animator_count is None:
        return None
    if model_animator_body_offset > model_id_offset:
        return None
    body_size = model_id_offset - model_animator_body_offset
    body_hits = scan_length_prefixed_utf8_string_hits(
        data,
        start=model_animator_body_offset,
        max_scan_bytes=body_size,
        max_samples=128,
        min_length=2,
        max_length=260,
    )
    body_strings = unique_strings([str(hit.get("value") or "") for hit in body_hits], 64)
    body_clip_refs = unique_strings([value for value in body_strings if value.startswith("A_")], 12)
    body_effect_refs = unique_strings([value for value in body_strings if value.startswith("P_")], 12)
    animator_names = unique_strings(
        [
            value
            for value in body_strings
            if value not in body_clip_refs
            and value not in body_effect_refs
            and value != stem
            and not value.startswith("A_")
            and not value.startswith("P_")
        ],
        16,
    )

    details = [
        f"modelId={stem}",
        f"clipInfos={clip_count}",
        f"effects={effect_count}",
        f"emissiveHashes={emissive_count}",
        f"modelAnimatorDatas={model_animator_count}",
        f"preTickAnimator={str(pre_tick_animator).lower()}",
    ]
    if clip_infos:
        details.append("clips=" + ",".join(str(item["name"]) for item in clip_infos[:3]))
    if effect_ids:
        details.append("effects=" + ",".join(effect_ids[:3]))
    if animator_names:
        details.append("animatorStrings=" + ",".join(animator_names[:4]))
    sample = "; ".join(details)
    while len(sample) > STRING_SAMPLE_MAX_CHARS and len(details) > 6:
        details.pop()
        sample = "; ".join(details)

    return {
        "kind": "memorypack-json",
        "subtype": "ModelViewStateControllerData",
        "summary": (
            "MemoryPack ModelViewStateControllerData; object member count 7; "
            f"clips {clip_count}; effects {effect_count}; modelAnimatorDatas {model_animator_count}; "
            "modelId/preTick tail verified"
        ),
        "rows": None,
        "keys": schema,
        "sample": sample,
        "decoded": {
            "memberCount": MODEL_VIEW_STATE_CONTROLLER_MEMBER_COUNT,
            "format": "memorypack",
            "schemaSource": MEMORYPACK_SCHEMA_SOURCE_NOTE,
            "decodedPreviewFields": [
                "cameraSignalSourceAssetHashes",
                "clipAssetInfos",
                "effectIds",
                "emissiveConfigHashes",
                "modelAnimatorDatasCount",
                "modelId",
                "preTickAnimator",
                "modelAnimatorDataStringSamples",
            ],
            "cameraSignalSourceAssetHashCount": camera_count,
            "cameraSignalSourceAssetHashes": camera_hashes[:16],
            "clipAssetInfoCount": clip_count,
            "clipAssetInfos": clip_infos[:16],
            "effectIdCount": effect_count,
            "effectIds": effect_ids[:16],
            "emissiveConfigHashCount": emissive_count,
            "emissiveConfigHashes": emissive_hashes[:16],
            "modelAnimatorDatasCount": model_animator_count,
            "modelAnimatorDatasOffset": format_offset(offset),
            "modelAnimatorDatasBodyBytes": body_size,
            "modelAnimatorDataStringSamples": body_strings[:24],
            "modelAnimatorDataClipRefs": body_clip_refs,
            "modelAnimatorDataEffectRefs": body_effect_refs,
            "animatorNames": animator_names,
            "modelId": stem,
            "modelIdOffset": format_offset(model_id_offset),
            "preTickAnimator": pre_tick_animator,
            "exactPrefixFields": [
                "cameraSignalSourceAssetHashes",
                "clipAssetInfos",
                "effectIds",
                "emissiveConfigHashes",
                "modelAnimatorDatasCount",
            ],
            "exactTailFields": ["modelId", "preTickAnimator"],
            "exactLength": False,
        },
    }


def read_memorypack_nullable_string(
    data: bytes,
    offset: int,
    field_name: str,
    *,
    max_length: int = 512,
) -> tuple[str | None, int]:
    value, offset, error = read_memorypack_utf8_string(data, offset, max_length=max_length)
    if error:
        raise ValueError(f"{field_name}:{error}")
    return value, offset


def decode_damage_text_memorypack(rel: str, data: bytes, size: int) -> dict[str, Any] | None:
    if rel != DAMAGE_TEXT_REL:
        return None
    if not data or data[0] != DAMAGE_TEXT_ROOT_MEMBER_COUNT:
        return None

    def parse_animation_ref(offset: int, row_index: int, anim_index: int) -> tuple[dict[str, Any], int]:
        if offset >= len(data) or data[offset] != DAMAGE_TEXT_ANIMATION_MEMBER_COUNT:
            raise ValueError(f"damageText[{row_index}].animation[{anim_index}].memberCount")
        offset += 1
        name, offset = require_memorypack_non_null_string(
            data,
            offset,
            f"damageText[{row_index}].animation[{anim_index}].name",
            max_length=128,
        )
        duration = round(read_memorypack_f32(data, offset)[0], 6)
        offset += 4
        int0 = struct.unpack_from("<i", data, offset)[0]
        offset += 4
        int1 = struct.unpack_from("<i", data, offset)[0]
        offset += 4
        int2 = struct.unpack_from("<i", data, offset)[0]
        offset += 4
        if not math.isfinite(duration) or abs(duration) > 10_000:
            raise ValueError(f"damageText[{row_index}].animation[{anim_index}].duration")
        if any(abs(value) > 1_000_000 for value in (int0, int1, int2)):
            raise ValueError(f"damageText[{row_index}].animation[{anim_index}].ints")
        return {
            "name": name,
            "durationOrScale": duration,
            "int0": int0,
            "int1": int1,
            "int2": int2,
        }, offset

    def parse_node_meta(offset: int, row_index: int, node_index: int) -> tuple[dict[str, Any], int]:
        if offset >= len(data) or data[offset] != DAMAGE_TEXT_NODE_MEMBER_COUNT:
            raise ValueError(f"damageText[{row_index}].node[{node_index}].memberCount")
        offset += 1
        name, offset = require_memorypack_non_null_string(
            data,
            offset,
            f"damageText[{row_index}].node[{node_index}].name",
            max_length=128,
        )
        text_or_value, offset = read_memorypack_nullable_string(
            data,
            offset,
            f"damageText[{row_index}].node[{node_index}].textOrValue",
            max_length=256,
        )
        resource_or_path, offset = read_memorypack_nullable_string(
            data,
            offset,
            f"damageText[{row_index}].node[{node_index}].resourceOrPath",
            max_length=256,
        )
        scalar = round(read_memorypack_f32(data, offset)[0], 6)
        offset += 4
        int0 = struct.unpack_from("<i", data, offset)[0]
        offset += 4
        int1 = struct.unpack_from("<i", data, offset)[0]
        offset += 4
        if not math.isfinite(scalar) or abs(scalar) > 10_000:
            raise ValueError(f"damageText[{row_index}].node[{node_index}].scalar")
        if any(abs(value) > 1_000_000 for value in (int0, int1)):
            raise ValueError(f"damageText[{row_index}].node[{node_index}].ints")
        return {
            "name": name,
            "textOrValue": text_or_value,
            "resourceOrPath": resource_or_path,
            "scalar": scalar,
            "int0": int0,
            "int1": int1,
        }, offset

    def parse_row_prefix(offset: int, row_index: int) -> tuple[dict[str, Any], int]:
        start = offset
        if offset >= len(data) or data[offset] != DAMAGE_TEXT_ROW_MEMBER_COUNT:
            raise ValueError(f"damageText[{row_index}].memberCount")
        offset += 1
        row_flag = data[offset]
        offset += 1
        if row_flag not in {0, 1}:
            raise ValueError(f"damageText[{row_index}].rowFlag={row_flag}")
        animation_count, offset = read_memorypack_u32_count(
            data,
            offset,
            f"damageText[{row_index}].animationCount",
            max_count=16,
        )
        if animation_count <= 0:
            raise ValueError(f"damageText[{row_index}].animationCount=0")
        animations: list[dict[str, Any]] = []
        for anim_index in range(animation_count):
            animation, offset = parse_animation_ref(offset, row_index, anim_index)
            animations.append(animation)

        node_count, offset = read_memorypack_u32_count(
            data,
            offset,
            f"damageText[{row_index}].nodeMetaCount",
            max_count=256,
        )
        layout_count, offset = read_memorypack_u32_count(
            data,
            offset,
            f"damageText[{row_index}].layoutCount",
            max_count=256,
        )
        if node_count != layout_count:
            raise ValueError(f"damageText[{row_index}].layoutCountMismatch={node_count}/{layout_count}")
        nodes: list[dict[str, Any]] = []
        for node_index in range(node_count):
            node, offset = parse_node_meta(offset, row_index, node_index)
            nodes.append(node)
        return {
            "startOffset": start,
            "rowFlag": row_flag,
            "animationCount": animation_count,
            "animations": animations,
            "nodeMetaCount": node_count,
            "layoutCount": layout_count,
            "nodes": nodes,
        }, offset

    def is_row_start(offset: int) -> bool:
        try:
            parse_row_prefix(offset, -1)
        except (ValueError, struct.error, UnicodeDecodeError):
            return False
        return True

    try:
        offset = 1
        charset, offset = require_memorypack_non_null_string(
            data,
            offset,
            "damageText.charset",
            max_length=128,
        )
        declared_rows, offset = read_memorypack_u32_count(
            data,
            offset,
            "damageText.rows",
            max_count=1_000,
        )
        if declared_rows <= 0:
            return None

        row_member_counts: Counter[int] = Counter()
        animation_member_counts: Counter[int] = Counter()
        node_member_counts: Counter[int] = Counter()
        animation_count_by_row: Counter[int] = Counter()
        node_count_pairs: Counter[str] = Counter()
        tail_length_counts: Counter[int] = Counter()
        row_flags: Counter[int] = Counter()
        animation_names: list[str] = []
        node_names: list[str] = []
        node_resource_refs: list[str] = []
        sample_rows: list[dict[str, Any]] = []

        for row_index in range(declared_rows):
            row, after_nodes = parse_row_prefix(offset, row_index)
            row_member_counts[DAMAGE_TEXT_ROW_MEMBER_COUNT] += 1
            row_flags[row["rowFlag"]] += 1
            animation_count_by_row[row["animationCount"]] += 1
            node_count_pairs[f"{row['nodeMetaCount']}/{row['layoutCount']}"] += 1
            animation_member_counts[DAMAGE_TEXT_ANIMATION_MEMBER_COUNT] += len(row["animations"])
            node_member_counts[DAMAGE_TEXT_NODE_MEMBER_COUNT] += len(row["nodes"])

            if row_index + 1 < declared_rows:
                next_offset = None
                for candidate in range(after_nodes, len(data)):
                    if is_row_start(candidate):
                        next_offset = candidate
                        break
                if next_offset is None:
                    return None
            else:
                next_offset = len(data)
            tail = data[after_nodes:next_offset]
            tail_length_counts[len(tail)] += 1
            tail_hits = scan_length_prefixed_utf8_string_hits(
                tail,
                max_samples=6,
                min_length=2,
                max_length=96,
            )

            for animation in row["animations"]:
                name = animation["name"]
                if name not in animation_names and len(animation_names) < 64:
                    animation_names.append(name)
            for node in row["nodes"]:
                name = node["name"]
                if name not in node_names and len(node_names) < 96:
                    node_names.append(name)
                for key in ("textOrValue", "resourceOrPath"):
                    value = node.get(key)
                    if value and value not in node_resource_refs and len(node_resource_refs) < 96:
                        node_resource_refs.append(value)

            if len(sample_rows) < 20:
                sample_rows.append({
                    "index": row_index,
                    "startOffset": format_offset(row["startOffset"]),
                    "rowFlag": row["rowFlag"],
                    "animationRefs": row["animations"],
                    "nodeMetaCount": row["nodeMetaCount"],
                    "layoutCount": row["layoutCount"],
                    "nodeNames": [node["name"] for node in row["nodes"]],
                    "nodeResourceRefs": [
                        value
                        for node in row["nodes"]
                        for value in (node.get("textOrValue"), node.get("resourceOrPath"))
                        if value
                    ][:12],
                    "layoutTailLength": len(tail),
                    "layoutTailStringSamples": tail_hits,
                })
            offset = next_offset

        if offset != len(data):
            return None
        if row_member_counts != Counter({DAMAGE_TEXT_ROW_MEMBER_COUNT: declared_rows}):
            return None
    except (ValueError, struct.error, UnicodeDecodeError):
        return None

    anim_summary = ",".join(f"{key}:{count}" for key, count in animation_count_by_row.most_common(6))
    node_summary = ",".join(f"{key}:{count}" for key, count in node_count_pairs.most_common(6))
    tail_summary = ",".join(f"{key}:{count}" for key, count in tail_length_counts.most_common(6))
    details = [
        f"rows={declared_rows}",
        f"charset={charset}",
        f"animationCounts={anim_summary}",
        f"nodeCounts={node_summary}",
    ]
    if tail_summary:
        details.append("tailLengths=" + tail_summary)
    if animation_names:
        details.append("sampleAnimations=" + ",".join(animation_names[:5]))
    sample = "; ".join(details)
    while len(sample) > STRING_SAMPLE_MAX_CHARS and len(details) > 4:
        details.pop()
        sample = "; ".join(details)

    return {
        "kind": "memorypack-json",
        "subtype": "GPUISystemConfigDamageText",
        "summary": (
            "MemoryPack GPUISystemConfig damage_text; object member count 5; "
            f"{declared_rows} damage-text rows with exact animation/node metadata; exact length"
        ),
        "rows": declared_rows,
        "keys": [
            "charset",
            "animationRefs",
            "nodeNames",
            "nodeResourceRefs",
            "layoutTailLength",
        ],
        "sample": sample,
        "decoded": {
            "memberCount": DAMAGE_TEXT_ROOT_MEMBER_COUNT,
            "format": "memorypack",
            "decodedPreviewFields": [
                "charset",
                "animationRefs",
                "nodeNames",
                "nodeResourceRefs",
                "layoutTailLength",
            ],
            "charset": charset,
            "declaredRowCount": declared_rows,
            "rowMemberCountMarkers": dict(sorted(row_member_counts.items())),
            "animationMemberCountMarkers": dict(sorted(animation_member_counts.items())),
            "nodeMemberCountMarkers": dict(sorted(node_member_counts.items())),
            "rowFlagCounts": dict(sorted(row_flags.items())),
            "animationCountByRow": dict(sorted(animation_count_by_row.items())),
            "nodeCountPairs": dict(node_count_pairs.most_common(32)),
            "tailLengthCounts": dict(tail_length_counts.most_common(32)),
            "animationRefs": animation_names,
            "nodeNames": node_names,
            "nodeResourceRefs": node_resource_refs,
            "sampleRows": sample_rows,
            "exactLength": True,
            "fileSize": size,
        },
    }


def decode_bamboo_raft_task_table_memorypack(rel: str, data: bytes, size: int) -> dict[str, Any] | None:
    if rel != BAMBOO_RAFT_TASK_TABLE_REL:
        return None
    if not data or data[0] != BAMBOO_RAFT_TASK_ROOT_MEMBER_COUNT:
        return None

    try:
        offset = 1
        entry_count, offset = read_memorypack_u32_count(
            data,
            offset,
            "BambooRaftTaskTable.entries",
            max_count=512,
        )
        value_member_counts: Counter[int] = Counter()
        task_member_counts: Counter[int] = Counter()
        field0_counts: Counter[int] = Counter()
        task_count_counts: Counter[int] = Counter()
        task_tail_counts: Counter[int] = Counter()
        tail_u64_counts: Counter[int] = Counter()
        duplicate_matches = 0
        total_task_refs = 0
        rows: list[dict[str, Any]] = []

        for row_index in range(entry_count):
            if offset + 8 > len(data):
                raise ValueError(f"BambooRaftTaskTable[{row_index}].header:truncated")
            hash_u32 = struct.unpack_from("<I", data, offset)[0]
            offset += 4
            field0_u32 = struct.unpack_from("<I", data, offset)[0]
            offset += 4
            if offset >= len(data):
                raise ValueError(f"BambooRaftTaskTable[{row_index}].memberCount:truncated")
            value_member_count = data[offset]
            offset += 1
            value_member_counts[value_member_count] += 1
            task_count, offset = read_memorypack_u32_count(
                data,
                offset,
                f"BambooRaftTaskTable[{row_index}].tasks",
                max_count=128,
            )
            tasks: list[dict[str, Any]] = []
            for task_index in range(task_count):
                task_id, offset = require_memorypack_non_null_string(
                    data,
                    offset,
                    f"BambooRaftTaskTable[{row_index}].tasks[{task_index}].taskId",
                    max_length=96,
                )
                if offset >= len(data):
                    raise ValueError(f"BambooRaftTaskTable[{row_index}].tasks[{task_index}].memberCount:truncated")
                task_member_count = data[offset]
                offset += 1
                task_member_counts[task_member_count] += 1
                duplicate_id, offset = require_memorypack_non_null_string(
                    data,
                    offset,
                    f"BambooRaftTaskTable[{row_index}].tasks[{task_index}].duplicateId",
                    max_length=96,
                )
                if offset + 4 > len(data):
                    raise ValueError(f"BambooRaftTaskTable[{row_index}].tasks[{task_index}].tail:truncated")
                task_tail = struct.unpack_from("<I", data, offset)[0]
                offset += 4
                if duplicate_id == task_id:
                    duplicate_matches += 1
                task_tail_counts[task_tail] += 1
                if len(tasks) < 8:
                    tasks.append(
                        {
                            "taskId": task_id,
                            "memberCount": task_member_count,
                            "duplicateId": duplicate_id,
                            "tailU32": task_tail,
                        }
                    )
            if offset + 8 > len(data):
                raise ValueError(f"BambooRaftTaskTable[{row_index}].tail:truncated")
            tail_u64 = struct.unpack_from("<Q", data, offset)[0]
            offset += 8
            field0_counts[field0_u32] += 1
            task_count_counts[task_count] += 1
            tail_u64_counts[tail_u64] += 1
            total_task_refs += task_count
            if len(rows) < 16:
                rows.append(
                    {
                        "hashU32": hash_u32,
                        "field0U32": field0_u32,
                        "valueMemberCount": value_member_count,
                        "taskCount": task_count,
                        "taskRefs": tasks,
                        "tailU64": tail_u64,
                    }
                )

        if offset != len(data):
            return None
        if set(value_member_counts) != {BAMBOO_RAFT_TASK_VALUE_MEMBER_COUNT}:
            return None
        if set(task_member_counts) != {BAMBOO_RAFT_TASK_REF_MEMBER_COUNT}:
            return None
    except (ValueError, struct.error):
        return None

    field0_summary = ",".join(f"{key}:{count}" for key, count in field0_counts.most_common(6))
    task_summary = ",".join(f"{key}:{count}" for key, count in task_count_counts.most_common(6))
    details = [f"rows={entry_count}", f"taskRefs={total_task_refs}"]
    if field0_summary:
        details.append("field0=" + field0_summary)
    if task_summary:
        details.append("taskCounts=" + task_summary)
    sample = "; ".join(details)
    while len(sample) > STRING_SAMPLE_MAX_CHARS and len(details) > 3:
        details.pop()
        sample = "; ".join(details)

    return {
        "kind": "memorypack-json",
        "subtype": "BambooRaftTaskTable",
        "summary": (
            "MemoryPack BambooRaftTaskTable; object member count 1; "
            f"{entry_count} rows, {total_task_refs} duplicated task refs; exact length"
        ),
        "rows": entry_count,
        "keys": ["hashU32", "field0U32", "taskRefs", "tailU64"],
        "sample": sample,
        "decoded": {
            "memberCount": BAMBOO_RAFT_TASK_ROOT_MEMBER_COUNT,
            "format": "memorypack",
            "decodedPreviewFields": ["hashU32", "field0U32", "taskRefs", "tailU64"],
            "entryCount": entry_count,
            "totalTaskRefs": total_task_refs,
            "duplicateIdMatches": duplicate_matches,
            "valueMemberCountMarkers": dict(sorted(value_member_counts.items())),
            "taskMemberCountMarkers": dict(sorted(task_member_counts.items())),
            "field0Counts": dict(field0_counts.most_common(16)),
            "taskCountCounts": dict(task_count_counts.most_common(16)),
            "taskTailCounts": dict(task_tail_counts.most_common(16)),
            "tailU64Counts": dict(tail_u64_counts.most_common(16)),
            "sampleRows": rows,
            "exactLength": True,
            "fileSize": size,
        },
    }


def dialog_id_table_row_start(data: bytes, offset: int) -> str | None:
    if offset + 5 > len(data):
        return None
    length = struct.unpack_from("<I", data, offset)[0]
    if length < 5 or length > 140 or offset + 4 + length >= len(data):
        return None
    try:
        key = data[offset + 4:offset + 4 + length].decode("utf-8")
    except UnicodeDecodeError:
        return None
    if not DIALOG_ID_TABLE_KEY_RE.match(key):
        return None
    if data[offset + 4 + length] != DIALOG_ID_TABLE_BRIEF_MEMBER_COUNT:
        return None
    return key


def parse_dialog_id_table_int_string_map(data: bytes, offset: int, field_name: str, *, max_count: int = 20_000) -> tuple[dict[str, Any], int]:
    count, offset = read_memorypack_u32_count(data, offset, field_name, max_count=max_count)
    rows: list[dict[str, Any]] = []
    key_min: int | None = None
    key_max: int | None = None
    for row_index in range(count):
        row_offset = offset
        value, offset = read_memorypack_i32(data, offset)
        text, offset = require_memorypack_non_null_string(
            data,
            offset,
            f"{field_name}[{row_index}].value",
            max_length=220,
        )
        if key_min is None or value < key_min:
            key_min = value
        if key_max is None or value > key_max:
            key_max = value
        if len(rows) < 8 or row_index >= count - 3:
            rows.append({"index": row_index, "offset": format_offset(row_offset), "key": value, "value": text})
    return {
        "count": count,
        "keyMin": key_min,
        "keyMax": key_max,
        "sampleRows": rows[:16],
    }, offset


def parse_dialog_id_table_string_int_map(data: bytes, offset: int, field_name: str, *, max_count: int = 20_000) -> tuple[dict[str, Any], int]:
    count, offset = read_memorypack_u32_count(data, offset, field_name, max_count=max_count)
    rows: list[dict[str, Any]] = []
    value_counts: Counter[int] = Counter()
    key_prefix_counts: Counter[str] = Counter()
    for row_index in range(count):
        row_offset = offset
        key, offset = require_memorypack_non_null_string(
            data,
            offset,
            f"{field_name}[{row_index}].key",
            max_length=220,
        )
        value, offset = read_memorypack_i32(data, offset)
        value_counts[value] += 1
        prefix = "option" if key.startswith("option_dlg_") else key.split("_", 1)[0]
        key_prefix_counts[prefix] += 1
        if len(rows) < 8 or row_index >= count - 3:
            rows.append({"index": row_index, "offset": format_offset(row_offset), "key": key, "value": value})
    return {
        "count": count,
        "valueMin": min(value_counts) if value_counts else None,
        "valueMax": max(value_counts) if value_counts else None,
        "keyPrefixCounts": dict(key_prefix_counts.most_common(12)),
        "sampleRows": rows[:16],
    }, offset


def dialog_id_table_counter_to_json(counter: Counter[Any], limit: int = 24) -> dict[str, int]:
    out: dict[str, int] = {}
    for key, count in counter.most_common(limit):
        if key is None or key == MEMORYPACK_NULL_COUNT:
            out_key = "null"
        elif isinstance(key, bool):
            out_key = "true" if key else "false"
        else:
            out_key = str(key)
        out[out_key] = count
    return out


def parse_dialog_id_table_lang_key(data: bytes, offset: int, field_name: str) -> tuple[dict[str, Any], int]:
    if offset >= len(data):
        raise ValueError(f"{field_name}:truncated-member-count")
    member_count = data[offset]
    offset += 1
    if member_count == (MEMORYPACK_NULL_COUNT & 0xFF):
        return {"memberCount": None, "value": None}, offset
    if member_count != 1:
        raise ValueError(f"{field_name}:unexpected-member-count={member_count}")
    value, offset = require_memorypack_string(data, offset, f"{field_name}.value")
    return {"memberCount": member_count, "value": value}, offset


def parse_dialog_id_table_string_list(data: bytes, offset: int, field_name: str, *, max_count: int = 256) -> tuple[dict[str, Any], int]:
    if offset + 4 > len(data):
        raise ValueError(f"{field_name}:truncated-count")
    count = struct.unpack_from("<I", data, offset)[0]
    offset += 4
    if count == MEMORYPACK_NULL_COUNT:
        return {"count": None, "values": []}, offset
    if count > max_count:
        raise ValueError(f"{field_name}:invalid-count={count}")
    values: list[str] = []
    for index in range(count):
        value, offset = require_memorypack_non_null_string(data, offset, f"{field_name}[{index}]", max_length=220)
        values.append(value)
    return {"count": count, "values": values}, offset


def parse_dialog_id_table_mask_segment(segment: bytes, field_name: str) -> dict[str, Any]:
    if segment == bytes([MEMORYPACK_NULL_COUNT & 0xFF]):
        return {"isNull": True, "byteLength": 1}
    if len(segment) < 15 or segment[0] != 6:
        raise ValueError(f"{field_name}:not-common-mask")
    curve = segment[2:-13]
    if not curve:
        raise ValueError(f"{field_name}.curve:empty")
    fade_in = struct.unpack_from("<f", segment, len(segment) - 13)[0]
    fade_out = struct.unpack_from("<f", segment, len(segment) - 9)[0]
    mask_type = struct.unpack_from("<i", segment, len(segment) - 5)[0]
    use_curve_byte = segment[-1]
    if not math.isfinite(fade_in) or not math.isfinite(fade_out):
        raise ValueError(f"{field_name}.fade:non-finite")
    if abs(fade_in) > 120 or abs(fade_out) > 120:
        raise ValueError(f"{field_name}.fade:out-of-range")
    if mask_type < 0 or mask_type > 16:
        raise ValueError(f"{field_name}.maskType:out-of-range={mask_type}")
    if use_curve_byte not in (0, 1):
        raise ValueError(f"{field_name}.useCurve:invalid={use_curve_byte}")
    return {
        "isNull": False,
        "byteLength": len(segment),
        "memberCount": segment[0],
        "audioBlackScreenBehaviour": segment[1],
        "curveByteLength": len(curve),
        "curvePrefixHex": curve[:12].hex(),
        "fadeInDuration": round(fade_in, 4),
        "fadeOutDuration": round(fade_out, 4),
        "maskType": mask_type,
        "useCurve": bool(use_curve_byte),
    }


def split_dialog_id_table_masks(prefix: bytes, field_name: str) -> tuple[dict[str, Any], dict[str, Any]]:
    matches: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for split in range(1, len(prefix)):
        try:
            after_mask = parse_dialog_id_table_mask_segment(prefix[:split], f"{field_name}.afterMaskBlendData")
            before_mask = parse_dialog_id_table_mask_segment(prefix[split:], f"{field_name}.beforeMaskBlendData")
        except (ValueError, struct.error):
            continue
        matches.append((after_mask, before_mask))
    if len(matches) != 1:
        raise ValueError(f"{field_name}.maskPrefix:ambiguous-splits={len(matches)}")
    return matches[0]


def parse_dialog_brief_info_payload(payload: bytes, key: str, field_name: str) -> dict[str, Any]:
    marker = struct.pack("<I", len(key.encode("utf-8"))) + key.encode("utf-8")
    search_from = 0
    last_error = "duplicate-dialogId:not-found"
    while True:
        dialog_id_offset = payload.find(marker, search_from)
        if dialog_id_offset < 0:
            break
        try:
            after_mask, before_mask = split_dialog_id_table_masks(payload[:dialog_id_offset], field_name)
            offset = dialog_id_offset
            dialog_id, offset = require_memorypack_non_null_string(payload, offset, f"{field_name}.dialogId", max_length=220)
            if dialog_id != key:
                raise ValueError(f"{field_name}.dialogId:mismatch")
            dialog_type, offset = read_memorypack_i32(payload, offset)
            if dialog_type < 0 or dialog_type > 32:
                raise ValueError(f"{field_name}.dialogType:out-of-range={dialog_type}")
            interact_text, offset = parse_dialog_id_table_lang_key(payload, offset, f"{field_name}.interactText")
            npc_proxy_ids, offset = parse_dialog_id_table_string_list(payload, offset, f"{field_name}.npcProxyIds")
            if offset >= len(payload):
                raise ValueError(f"{field_name}.useBlackScreen:truncated")
            use_black_screen_byte = payload[offset]
            offset += 1
            if use_black_screen_byte not in (0, 1):
                raise ValueError(f"{field_name}.useBlackScreen:invalid={use_black_screen_byte}")
            if offset != len(payload):
                raise ValueError(f"{field_name}:trailing-bytes={len(payload) - offset}")
            return {
                "maskPrefixLength": dialog_id_offset,
                "afterMaskBlendData": after_mask,
                "beforeMaskBlendData": before_mask,
                "dialogId": dialog_id,
                "dialogType": dialog_type,
                "interactText": interact_text["value"],
                "interactTextMemberCount": interact_text["memberCount"],
                "npcProxyIdCount": npc_proxy_ids["count"],
                "npcProxyIds": npc_proxy_ids["values"],
                "useBlackScreen": bool(use_black_screen_byte),
            }
        except (UnicodeDecodeError, struct.error, ValueError) as exc:
            last_error = str(exc)
            search_from = dialog_id_offset + 1
    raise ValueError(f"{field_name}:{last_error}")


def summarize_dialog_id_table_registry(data: bytes) -> dict[str, Any]:
    all_ids = sorted({match.group().decode("ascii") for match in DIALOG_ID_TABLE_RAW_ID_RE.finditer(data)})
    option_ids = sorted({match.group().decode("ascii") for match in DIALOG_ID_TABLE_OPTION_RAW_RE.finditer(data)})

    per_line_by_scene: dict[str, dict[int, list[str]]] = defaultdict(lambda: defaultdict(list))
    options_by_scene: dict[str, dict[int, list[str]]] = defaultdict(lambda: defaultdict(list))
    root_keys: set[str] = set()
    for ident in all_ids:
        if ident.startswith("radio_"):
            root_keys.add(ident)
            continue
        match = DIALOG_ID_TABLE_LINE_RE.match(ident)
        if match:
            per_line_by_scene[match.group("scene")][int(match.group("trunk"))].append(ident)
        else:
            root_keys.add(ident)
    for ident in option_ids:
        match = DIALOG_ID_TABLE_OPTION_RE.match(ident)
        if match:
            options_by_scene[match.group("scene")][int(match.group("group"))].append(ident)

    all_scenes = root_keys | set(per_line_by_scene)
    with_decomp = 0
    multi_trunk = 0
    root_only = 0
    with_options = 0
    option_count = 0
    line_count = 0
    for scene in all_scenes:
        trunks = per_line_by_scene.get(scene, {})
        trunk_count = len(trunks)
        scene_line_count = sum(len(values) for values in trunks.values())
        option_groups = options_by_scene.get(scene, {})
        scene_option_count = sum(len(values) for values in option_groups.values())
        line_count += scene_line_count
        option_count += scene_option_count
        if trunk_count > 0:
            with_decomp += 1
        else:
            root_only += 1
        if trunk_count > 1:
            multi_trunk += 1
        if scene_option_count > 0:
            with_options += 1
    return {
        "registeredSceneCount": len(all_scenes),
        "rootKeyCount": len(root_keys),
        "lineIdCount": line_count,
        "optionIdCount": option_count,
        "withTrunkLineDecomposition": with_decomp,
        "multiTrunkSceneCount": multi_trunk,
        "rootOnlySceneCount": root_only,
        "withOptionsSceneCount": with_options,
        "radioSceneCount": sum(1 for key in all_scenes if key.startswith("radio_")),
    }


def decode_dialog_id_table_memorypack(rel: str, data: bytes, size: int) -> dict[str, Any] | None:
    if rel != DIALOG_ID_TABLE_REL:
        return None
    if not data or data[0] != DIALOG_ID_TABLE_ROOT_MEMBER_COUNT:
        return None

    try:
        offset = 1
        brief_count, offset = read_memorypack_u32_count(
            data,
            offset,
            "dialogBriefInfoDict",
            max_count=20_000,
        )
        starts: list[tuple[int, str]] = []
        for candidate in range(offset, len(data) - 5):
            key = dialog_id_table_row_start(data, candidate)
            if key is not None:
                starts.append((candidate, key))
                if len(starts) >= brief_count + 1:
                    break
        if len(starts) < brief_count or starts[0][0] != offset:
            raise ValueError("dialogBriefInfoDict.rowStarts:not-found")

        last_start = starts[brief_count - 1][0]
        search_end = starts[brief_count][0] if len(starts) > brief_count else len(data)
        field2_offset: int | None = None
        for candidate in range(last_start + 1, search_end):
            if candidate + 4 > len(data):
                break
            if struct.unpack_from("<I", data, candidate)[0] != brief_count:
                continue
            try:
                _field2_probe, probe_offset = parse_dialog_id_table_int_string_map(
                    data,
                    candidate,
                    "dialogIdByIntIdProbe",
                    max_count=20_000,
                )
            except (UnicodeDecodeError, struct.error, ValueError):
                continue
            if probe_offset <= len(data):
                field2_offset = candidate
                break
        if field2_offset is None:
            raise ValueError("dialogBriefInfoDict.end:not-found")

        brief_rows: list[dict[str, Any]] = []
        interesting_brief_rows: list[dict[str, Any]] = []
        payload_length_counts: Counter[int] = Counter()
        duplicate_key_matches = 0
        brief_key_prefix_counts: Counter[str] = Counter()
        brief_mask_prefix_length_counts: Counter[int] = Counter()
        brief_mask_length_counts: Counter[str] = Counter()
        brief_dialog_type_counts: Counter[int] = Counter()
        brief_interact_text_counts: Counter[str | None] = Counter()
        brief_npc_proxy_count_counts: Counter[int | None] = Counter()
        brief_use_black_screen_counts: Counter[bool] = Counter()
        brief_mask_field_counts: dict[str, Counter[Any]] = defaultdict(Counter)
        dialog_brief_info_parsed_count = 0
        for row_index, (row_start, key) in enumerate(starts[:brief_count]):
            row_end = starts[row_index + 1][0] if row_index + 1 < brief_count else field2_offset
            key_length = struct.unpack_from("<I", data, row_start)[0]
            payload_start = row_start + 4 + key_length + 1
            if row_end < payload_start:
                raise ValueError(f"dialogBriefInfoDict[{row_index}].payload:negative")
            payload = data[payload_start:row_end]
            payload_length_counts[len(payload)] += 1
            parsed_brief = parse_dialog_brief_info_payload(payload, key, f"dialogBriefInfoDict[{row_index}]")
            dialog_brief_info_parsed_count += 1
            if parsed_brief["dialogId"] == key:
                duplicate_key_matches += 1
            prefix = "radio" if key.startswith("radio_") else key.split("_", 2)[1] if key.startswith("dlg_") and len(key.split("_", 2)) > 1 else key.split("_", 1)[0]
            brief_key_prefix_counts[prefix] += 1
            brief_mask_prefix_length_counts[parsed_brief["maskPrefixLength"]] += 1
            after_mask = parsed_brief["afterMaskBlendData"]
            before_mask = parsed_brief["beforeMaskBlendData"]
            brief_mask_length_counts[f"after:{after_mask['byteLength']}|before:{before_mask['byteLength']}"] += 1
            brief_dialog_type_counts[parsed_brief["dialogType"]] += 1
            brief_interact_text_counts[parsed_brief["interactText"]] += 1
            brief_npc_proxy_count_counts[parsed_brief["npcProxyIdCount"]] += 1
            brief_use_black_screen_counts[parsed_brief["useBlackScreen"]] += 1
            for side, mask in (("afterMaskBlendData", after_mask), ("beforeMaskBlendData", before_mask)):
                brief_mask_field_counts[f"{side}.isNull"][mask["isNull"]] += 1
                brief_mask_field_counts[f"{side}.byteLength"][mask["byteLength"]] += 1
                if not mask["isNull"]:
                    for field in (
                        "audioBlackScreenBehaviour",
                        "curveByteLength",
                        "fadeInDuration",
                        "fadeOutDuration",
                        "maskType",
                        "useCurve",
                    ):
                        brief_mask_field_counts[f"{side}.{field}"][mask[field]] += 1
            row_preview = {
                "key": key,
                "offset": format_offset(row_start),
                "payloadLength": len(payload),
                "dialogType": parsed_brief["dialogType"],
                "interactText": parsed_brief["interactText"],
                "npcProxyIdCount": parsed_brief["npcProxyIdCount"],
                "npcProxyIds": parsed_brief["npcProxyIds"][:8],
                "useBlackScreen": parsed_brief["useBlackScreen"],
                "afterMaskBlendData": after_mask,
                "beforeMaskBlendData": before_mask,
            }
            if len(brief_rows) < 16:
                string_hits = scan_length_prefixed_utf8_string_hits(
                    payload,
                    max_samples=8,
                    min_length=3,
                    max_length=160,
                )
                row_preview["stringSamples"] = [hit["value"] for hit in string_hits[:6]]
                brief_rows.append(row_preview)
            has_variant_mask = after_mask["byteLength"] not in (1, 31) or before_mask["byteLength"] not in (1, 31)
            has_non_default_text = parsed_brief["interactText"] is not None
            has_null_mask = after_mask["isNull"] or before_mask["isNull"]
            if len(interesting_brief_rows) < 16 and (has_variant_mask or has_non_default_text or has_null_mask):
                interesting_brief_rows.append(row_preview)

        offset = field2_offset
        field2, offset = parse_dialog_id_table_int_string_map(data, offset, "dialogIdByIntId")
        field3, offset = parse_dialog_id_table_int_string_map(data, offset, "optionIdByIntId")
        field4, offset = parse_dialog_id_table_string_int_map(data, offset, "intIdByDialogOrOptionId")
        field5, offset = parse_dialog_id_table_string_int_map(data, offset, "intIdByDialogId")
        if offset != len(data):
            raise ValueError(f"trailing-bytes:{len(data) - offset}")
    except (UnicodeDecodeError, struct.error, ValueError):
        return None

    registry = summarize_dialog_id_table_registry(data)
    payload_summary = ",".join(
        f"{length}:{count}" for length, count in payload_length_counts.most_common(6)
    )
    dialog_type_summary = ",".join(
        f"{dialog_type}:{count}" for dialog_type, count in brief_dialog_type_counts.most_common(4)
    )
    details = [
        f"briefRows={brief_count}",
        f"briefParsed={dialog_brief_info_parsed_count}",
        f"dialogTypes={dialog_type_summary}",
        f"dialogIntMap={field2['count']}",
        f"optionIntMap={field3['count']}",
        f"reverseAll={field4['count']}",
        f"reverseDialog={field5['count']}",
        f"registryScenes={registry['registeredSceneCount']}",
        f"payloads={payload_summary}",
    ]
    if brief_rows:
        details.append("samples=" + ",".join(row["key"] for row in brief_rows[:3]))
    sample = "; ".join(details)
    while len(sample) > STRING_SAMPLE_MAX_CHARS and len(details) > 5:
        details.pop()
        sample = "; ".join(details)

    return {
        "kind": "memorypack-json",
        "subtype": "DialogIdTable",
        "summary": (
            "MemoryPack DialogIdTable; object member count 5; "
            f"{brief_count} DialogBriefInfo rows, {field3['count']} option-id rows; exact length"
        ),
        "rows": brief_count + field2["count"] + field3["count"] + field4["count"] + field5["count"],
        "keys": [
            "dialogId",
            "dialogBriefInfoPayloadLength",
            "dialogType",
            "interactText",
            "npcProxyIds",
            "useBlackScreen",
            "dialogIntId",
            "optionId",
            "optionIntId",
            "registrySceneCount",
            "lineIdCount",
            "optionIdCount",
        ],
        "sample": sample,
        "decoded": {
            "memberCount": DIALOG_ID_TABLE_ROOT_MEMBER_COUNT,
            "format": "memorypack",
            "schemaSource": "DialogIdTable runtime class and registry semantics from scripts/story_builder/dialog_registry.py plus IL2CPP MemoryPack formatter metadata; table and nested DialogBriefInfo fields recovered by exact byte boundaries",
            "decodedPreviewFields": [
                "dialogBriefInfoDict",
                "DialogBriefInfo.afterMaskBlendData",
                "DialogBriefInfo.beforeMaskBlendData",
                "DialogBriefInfo.dialogId",
                "DialogBriefInfo.dialogType",
                "DialogBriefInfo.interactText",
                "DialogBriefInfo.npcProxyIds",
                "DialogBriefInfo.useBlackScreen",
                "dialogIdByIntId",
                "optionIdByIntId",
                "intIdByDialogOrOptionId",
                "intIdByDialogId",
                "registrySummary",
            ],
            "dialogBriefInfoMemberCount": DIALOG_ID_TABLE_BRIEF_MEMBER_COUNT,
            "dialogBriefInfoFieldOrder": [
                "afterMaskBlendData",
                "beforeMaskBlendData",
                "dialogId",
                "dialogType",
                "interactText",
                "npcProxyIds",
                "useBlackScreen",
            ],
            "dialogBriefInfoCount": brief_count,
            "dialogBriefInfoParsedCount": dialog_brief_info_parsed_count,
            "dialogBriefInfoEndOffset": format_offset(field2_offset),
            "dialogBriefInfoDuplicateKeyMatches": duplicate_key_matches,
            "dialogBriefInfoPayloadLengthCounts": {str(key): count for key, count in payload_length_counts.most_common(24)},
            "dialogBriefInfoKeyPrefixCounts": dict(brief_key_prefix_counts.most_common(24)),
            "dialogBriefInfoMaskPrefixLengthCounts": {str(key): count for key, count in brief_mask_prefix_length_counts.most_common(24)},
            "dialogBriefInfoMaskLengthCounts": dict(brief_mask_length_counts.most_common(24)),
            "dialogBriefInfoDialogTypeCounts": dialog_id_table_counter_to_json(brief_dialog_type_counts),
            "dialogBriefInfoInteractTextCounts": dialog_id_table_counter_to_json(brief_interact_text_counts),
            "dialogBriefInfoNpcProxyIdCountCounts": dialog_id_table_counter_to_json(brief_npc_proxy_count_counts),
            "dialogBriefInfoUseBlackScreenCounts": dialog_id_table_counter_to_json(brief_use_black_screen_counts),
            "dialogBriefInfoMaskFieldCounts": {
                key: dialog_id_table_counter_to_json(value)
                for key, value in sorted(brief_mask_field_counts.items())
            },
            "dialogBriefInfoSampleRows": brief_rows,
            "dialogBriefInfoInterestingRows": interesting_brief_rows,
            "dialogIdByIntId": field2,
            "optionIdByIntId": field3,
            "intIdByDialogOrOptionId": field4,
            "intIdByDialogId": field5,
            "registrySummary": registry,
            "exactLength": True,
            "fileSize": size,
        },
    }
