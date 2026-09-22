"""Current structural framing for binary GPU UI configuration payloads."""

from __future__ import annotations

import struct
import math
from typing import Any
from pathlib import Path

from scripts.game_data.gpu_ui_damage_text_native import load_damage_text_schema


class GpuUiFramingError(ValueError):
    pass


EXTENDED_PREFAB_GROUP_FIELDS = (
    "dynamicPrefabBufferCapacity",
    "dynamicSpriteAtlasH",
    "dynamicSpriteAtlasW",
    "dynamicSpriteAtlasX",
    "dynamicSpriteAtlasY",
    "enableDynamicSpriteAtlas",
    "fontPrefabBufferSize",
    "hasTextNodes",
    "importantChars",
    "layoutType",
    "prefabBufferSize",
    "prefabs",
    "simpleInstanceBuffer",
    "spriteTexturePath",
    "textIds",
    "vatTexturePath",
)

PREFAB_GROUP_FIELDS = (
    "importantChars",
    "layoutType",
    "prefabs",
    "spriteTexturePath",
    "textIds",
    "vatTexturePath",
)

PREFAB_FIELDS = (
    "animationOnly",
    "animations",
    "nodeCount",
    "nodeMetas",
    "prefabName",
    "renderNodes",
)

ANIMATION_FIELDS = (
    "animationName",
    "animationTime",
    "renderNodesOffset",
    "totalFrames",
    "wrapMode",
)


def frame_gpu_ui_root16_prefix(data: bytes) -> dict[str, Any]:
    """Validate the named ExtendedPrefabGroup prefix and first prefab boundary."""
    if not data or data[0] != 16:
        raise GpuUiFramingError("root member count is not 16")
    offset = 1
    if offset + 20 > len(data):
        raise GpuUiFramingError("truncated five-word prefix")
    words = list(struct.unpack_from("<iiiii", data, offset))
    offset += 20
    if offset >= len(data) or data[offset] not in (0, 1):
        raise GpuUiFramingError("invalid prefix boolean 1")
    boolean1 = bool(data[offset])
    offset += 1
    if offset + 4 > len(data):
        raise GpuUiFramingError("truncated prefix word 6")
    word6 = struct.unpack_from("<i", data, offset)[0]
    offset += 4
    if offset >= len(data) or data[offset] not in (0, 1):
        raise GpuUiFramingError("invalid prefix boolean 2")
    boolean2 = bool(data[offset])
    offset += 1
    if offset + 4 > len(data):
        raise GpuUiFramingError("truncated charset length")
    length = struct.unpack_from("<I", data, offset)[0]
    offset += 4
    if length > 128 or offset + length + 5 > len(data):
        raise GpuUiFramingError(f"invalid charset length {length}")
    try:
        charset = data[offset:offset + length].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise GpuUiFramingError("invalid charset UTF-8") from exc
    offset += length
    layout_type = struct.unpack_from("<i", data, offset)[0]
    offset += 4
    if offset + 9 > len(data):
        raise GpuUiFramingError("truncated prefabBufferSize/prefabs prefix")
    prefab_buffer_size = struct.unpack_from("<i", data, offset)[0]
    offset += 4
    prefab_count = struct.unpack_from("<I", data, offset)[0]
    offset += 4
    if not 1 <= prefab_count <= 4096:
        raise GpuUiFramingError(f"invalid prefabs count {prefab_count}")
    if data[offset] != 7:
        raise GpuUiFramingError(
            f"first ExtendedPrefabSerializeData member count is {data[offset]}, expected 7"
        )
    return {
        "status": "bounded_prefix",
        "schemaStatus": "named_prefix_opaque_remainder",
        "bytesConsumed": offset,
        "rootMemberCount": 16,
        "fieldOrder": list(EXTENDED_PREFAB_GROUP_FIELDS),
        "fields": {
            "dynamicPrefabBufferCapacity": words[0],
            "dynamicSpriteAtlasH": words[1],
            "dynamicSpriteAtlasW": words[2],
            "dynamicSpriteAtlasX": words[3],
            "dynamicSpriteAtlasY": words[4],
            "enableDynamicSpriteAtlas": boolean1,
            "fontPrefabBufferSize": word6,
            "hasTextNodes": boolean2,
            "importantChars": charset,
            "layoutType": layout_type,
            "prefabBufferSize": prefab_buffer_size,
            "prefabsCount": prefab_count,
        },
        "firstPrefabMemberCount": data[offset],
        "opaqueRemainderOffset": offset,
        "opaqueRemainderLength": len(data) - offset,
        "evidenceBoundary": (
            "The first eleven generated wrapper fields and prefabs collection count "
            "are named and bounded. The first seven-member prefab starts at the "
            "opaque remainder; prefab contents and the final four root fields are not closed."
        ),
    }


class _GpuUiCursor:
    """Strict cursor for generated GPUI wrapper field layouts."""

    def __init__(self, data: bytes, offset: int):
        self.data = data
        self.offset = offset

    def scalar(self, fmt: str, field: str) -> Any:
        size = struct.calcsize("<" + fmt)
        if self.offset + size > len(self.data):
            raise GpuUiFramingError(f"{field}: truncated at {self.offset}")
        values = struct.unpack_from("<" + fmt, self.data, self.offset)
        self.offset += size
        if "f" in fmt and any(not math.isfinite(value) for value in values):
            raise GpuUiFramingError(f"{field}: non-finite float")
        return values[0] if len(values) == 1 else list(values)

    def boolean(self, field: str) -> bool:
        value = self.scalar("B", field)
        if value not in (0, 1):
            raise GpuUiFramingError(f"{field}: invalid boolean {value}")
        return bool(value)

    def string(self, field: str) -> str | None:
        size = self.scalar("I", field)
        if size == 0xFFFFFFFF:
            return None
        if size > 16_384 or self.offset + size > len(self.data):
            raise GpuUiFramingError(f"{field}: invalid UTF-8 length {size}")
        try:
            value = self.data[self.offset:self.offset + size].decode("utf-8")
        except UnicodeDecodeError as exc:
            raise GpuUiFramingError(f"{field}: invalid UTF-8") from exc
        self.offset += size
        return value

    def collection(self, field: str, read: Any) -> list[Any] | None:
        count = self.scalar("I", field)
        if count == 0xFFFFFFFF:
            return None
        if count > 100_000 or count > len(self.data) - self.offset:
            raise GpuUiFramingError(f"{field}: invalid count {count}")
        return [read(f"{field}[{index}]") for index in range(count)]

    def record(self, layout: tuple[tuple[str, str], ...], field: str) -> dict[str, Any]:
        marker = self.scalar("B", field)
        if marker != len(layout):
            raise GpuUiFramingError(
                f"{field}: member count {marker}, expected {len(layout)}"
            )
        result = {}
        for name, kind in layout:
            label = f"{field}.{name}"
            if kind == "string":
                value = self.string(label)
            elif kind == "bool":
                value = self.boolean(label)
            elif kind == "ints":
                value = self.collection(label, lambda item: self.scalar("i", item))
            else:
                value = self.scalar(kind, label)
            result[name] = value
        return result


# Generated wrapper setter order; scalar types come from the matching original
# UI.Beyond types. Unity Vector2/Vector4 values are contiguous float components.
_EXTENDED_ANIMATION_LAYOUT = (
    ("affectedNodeIndices", "ints"), ("animationName", "string"),
    ("animationTime", "f"), ("renderNodesOffset", "i"),
    ("subrootIndex", "i"), ("subrootName", "string"),
    ("totalFrames", "i"), ("wrapMode", "i"),
)
_NODE_METADATA_LAYOUT = (
    ("nodeName", "string"), ("nodeText", "string"),
    ("nodeTextBold", "bool"), ("nodeTextId", "string"),
    ("nodeTextSize", "f"), ("nodeType", "i"), ("subrootIndex", "i"),
    ("subrootName", "string"), ("textAlignment", "i"),
    ("textAutoSizeMaxGlyphCount", "i"), ("textAutoSizeMinScale", "f"),
    ("textAutoSizeWidth", "f"),
)
_EXTENDED_NODE_LAYOUT = (
    ("aniColorV", "f"), ("aniDurationInv", "f"), ("aniFillV", "f"),
    ("aniPosAddMinMax", "4f"), ("aniPosAddV", "f"),
    ("aniPosScaleMinMax", "4f"), ("aniPosScaleV", "f"),
    ("aniURange", "2f"), ("fillClockwise", "bool"),
    ("fillOrigin", "i"), ("fillType", "i"), ("materialParam1", "I"),
    ("materialType", "i"), ("uv", "4f"), ("wrapMode", "i"),
)
_SUBROOT_LAYOUT = (("anchorNodeIndex", "i"), ("subrootName", "string"))


def decode_gpu_ui_root16(data: bytes) -> dict[str, Any]:
    """Decode all ExtendedPrefabGroup fields and nested records to exact EOF."""
    prefix = frame_gpu_ui_root16_prefix(data)
    cursor = _GpuUiCursor(data, prefix["bytesConsumed"])
    fields = dict(prefix["fields"])
    count = fields.pop("prefabsCount")
    prefabs = []
    for index in range(count):
        label = f"prefabs[{index}]"
        marker = cursor.scalar("B", label)
        if marker != 7:
            raise GpuUiFramingError(f"{label}: member count {marker}, expected 7")
        prefab = {"animationOnly": cursor.boolean(label + ".animationOnly")}
        prefab["animations"] = cursor.collection(
            label + ".animations", lambda item: cursor.record(_EXTENDED_ANIMATION_LAYOUT, item)
        )
        prefab["nodeCount"] = cursor.scalar("i", label + ".nodeCount")
        prefab["nodeMetas"] = cursor.collection(
            label + ".nodeMetas", lambda item: cursor.record(_NODE_METADATA_LAYOUT, item)
        )
        prefab["prefabName"] = cursor.string(label + ".prefabName")
        prefab["renderNodes"] = cursor.collection(
            label + ".renderNodes", lambda item: cursor.record(_EXTENDED_NODE_LAYOUT, item)
        )
        prefab["subroots"] = cursor.collection(
            label + ".subroots", lambda item: cursor.record(_SUBROOT_LAYOUT, item)
        )
        prefabs.append(prefab)
    fields["prefabs"] = prefabs
    fields["simpleInstanceBuffer"] = cursor.boolean("simpleInstanceBuffer")
    fields["spriteTexturePath"] = cursor.scalar("q", "spriteTexturePath")
    fields["textIds"] = cursor.collection("textIds", cursor.string)
    fields["vatTexturePath"] = cursor.scalar("q", "vatTexturePath")
    if cursor.offset != len(data):
        raise GpuUiFramingError(f"trailing bytes: cursor={cursor.offset}, length={len(data)}")
    return {
        "status": "exact", "schemaStatus": "named_exact",
        "bytesConsumed": cursor.offset, "rootMemberCount": 16,
        "fieldOrder": list(EXTENDED_PREFAB_GROUP_FIELDS), "fields": fields,
        "evidenceBoundary": (
            "All generated ExtendedPrefabGroup wrapper fields and nested ExtendedPrefab, "
            "ExtendedAnimation, NodeMetadata, ExtendedNode and Subroot records close by "
            "a sequential cursor to EOF. Texture hashes identify stored references; "
            "runtime shader consumption and resolved texture identity remain separate joins."
        ),
    }


def _row_prefix(data: bytes, offset: int) -> dict[str, Any] | None:
    try:
        if data[offset] != 6 or data[offset + 1] not in (0, 1):
            return None
        cursor = offset + 2
        animation_count = struct.unpack_from("<I", data, cursor)[0]
        cursor += 4
        if not 1 <= animation_count <= 16:
            return None
        animations: list[dict[str, Any]] = []
        for _ in range(animation_count):
            if data[cursor] != 5:
                return None
            cursor += 1
            length = struct.unpack_from("<I", data, cursor)[0]
            cursor += 4
            if not 1 <= length <= 128 or cursor + length + 16 > len(data):
                return None
            name = data[cursor:cursor + length].decode("utf-8")
            cursor += length
            animation_time, render_nodes_offset, total_frames, wrap_mode = (
                struct.unpack_from("<fiii", data, cursor)
            )
            cursor += 16
            if not (-10_000.0 <= animation_time <= 10_000.0):
                return None
            animations.append({
                "memberCount": 5,
                "fieldOrder": list(ANIMATION_FIELDS),
                "animationName": name,
                "animationTime": animation_time,
                "renderNodesOffset": render_nodes_offset,
                "totalFrames": total_frames,
                "wrapMode": wrap_mode,
            })
        node_count = struct.unpack_from("<I", data, cursor)[0]
        layout_count = struct.unpack_from("<I", data, cursor + 4)[0]
        cursor += 8
        if node_count != layout_count or node_count > 256:
            return None
        return {
            "namedPrefixEndOffset": cursor,
            "animationOnly": bool(data[offset + 1]),
            "animations": animations,
            "nodeCount": node_count,
            "nodeMetasCount": layout_count,
        }
    except (IndexError, struct.error, UnicodeDecodeError):
        return None


def frame_damage_text(data: bytes) -> dict[str, Any]:
    """Name the current PrefabGroup/Prefab/Animation outer framing."""
    if not data or data[0] != 6:
        raise GpuUiFramingError("root member count is not 6")
    if len(data) < 13:
        raise GpuUiFramingError("truncated root")
    length = struct.unpack_from("<I", data, 1)[0]
    if length > 128 or 5 + length + 8 > len(data):
        raise GpuUiFramingError("invalid charset")
    try:
        charset = data[5:5 + length].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise GpuUiFramingError("invalid charset UTF-8") from exc
    offset = 5 + length
    style_discriminator = struct.unpack_from("<i", data, offset)[0]
    declared_count = struct.unpack_from("<I", data, offset + 4)[0]
    first_row = offset + 8
    if not 1 <= declared_count <= 1000:
        raise GpuUiFramingError(f"invalid row count {declared_count}")
    starts: list[int] = []
    prefixes: list[dict[str, Any]] = []
    for candidate in range(first_row, len(data)):
        prefix = _row_prefix(data, candidate)
        if prefix is not None:
            starts.append(candidate)
            prefixes.append(prefix)
    if len(starts) != declared_count or starts[0] != first_row:
        raise GpuUiFramingError(
            f"row boundary mismatch: declared={declared_count}, candidates={len(starts)}"
        )
    spans = [
        {
            "startOffset": start,
            "namedPrefixEndOffset": prefixes[index]["namedPrefixEndOffset"],
            "endOffset": starts[index + 1] if index + 1 < len(starts) else len(data),
            "memberCount": 6,
            "fieldOrder": list(PREFAB_FIELDS),
            "animationOnly": prefixes[index]["animationOnly"],
            "animations": prefixes[index]["animations"],
            "nodeCount": prefixes[index]["nodeCount"],
            "nodeMetasCount": prefixes[index]["nodeMetasCount"],
            "opaqueNestedFields": ["nodeMetas", "prefabName", "renderNodes"],
        }
        for index, start in enumerate(starts)
    ]
    return {
        "status": "exact_outer_frame",
        "schemaStatus": "named_exact_frame",
        "bytesConsumed": len(data),
        "rootMemberCount": 6,
        "fieldOrder": list(PREFAB_GROUP_FIELDS),
        "entryCount": declared_count,
        "importantChars": charset,
        "layoutType": style_discriminator,
        "rows": spans,
        "opaqueRootTailFields": ["spriteTexturePath", "textIds", "vatTexturePath"],
        "evidenceBoundary": (
            "Generated wrapper setter order names the six-field PrefabGroup root, "
            "every six-field Prefab row, and every five-field Animation row. Row "
            "starts and physical EOF close exactly; node metadata/render-node bodies "
            "and the three root tail fields remain bounded opaque spans."
        ),
    }


def decode_damage_text(data: bytes, *, game_root: Path | None = None) -> dict[str, Any]:
    """Decode the complete six-member PrefabGroup using authenticated native layouts."""
    contract, native_audit = load_damage_text_schema(game_root=game_root)
    if contract is None:
        raise GpuUiFramingError(
            "DamageText native schema unavailable: " + str(native_audit)
        )
    cursor = _GpuUiCursor(data, 0)
    spans: list[dict[str, Any]] = []
    root_field_ranges: dict[str, dict[str, int]] = {}

    def record(type_name: str, label: str) -> dict[str, Any]:
        layout = contract["records"][type_name]
        start = cursor.offset
        marker = cursor.scalar("B", label)
        if marker != layout["memberCount"]:
            raise GpuUiFramingError(
                f"{label}: member count {marker}, expected {layout['memberCount']} at {start}"
            )
        fields: dict[str, Any] = {}
        for field in layout["fields"]:
            name, encoding = field["name"], field["encoding"]
            child = f"{label}.{name}"
            before = cursor.offset
            if encoding == "string":
                value = cursor.string(child)
            elif encoding == "bool":
                value = cursor.boolean(child)
            elif encoding.startswith("list:"):
                element = encoding.removeprefix("list:")
                read = cursor.string if element == "string" else lambda item: record(element, item)
                value = cursor.collection(child, read)
            else:
                value = cursor.scalar(encoding, child)
            fields[name] = value
            if label == "root":
                root_field_ranges[name] = {"startOffset": before, "endOffset": cursor.offset}
        spans.append({"path": label, "type": type_name,
                      "startOffset": start, "endOffset": cursor.offset})
        return fields

    fields = record(contract["root"], "root")
    if cursor.offset != len(data):
        raise GpuUiFramingError(f"trailing bytes: cursor={cursor.offset}, length={len(data)}")
    prefabs = fields["prefabs"] or []
    return {
        "status": "exact", "schemaStatus": "named_exact", "wholeSchemaExact": True,
        "bytesConsumed": cursor.offset, "rootMemberCount": 6,
        "fieldOrder": list(fields), "fields": fields,
        "rootFieldRanges": root_field_ranges, "recordSpans": spans,
        "entryCount": len(prefabs),
        "animationCount": sum(len(row["animations"] or []) for row in prefabs),
        "nodeMetadataCount": sum(len(row["nodeMetas"] or []) for row in prefabs),
        "renderNodeCount": sum(len(row["renderNodes"] or []) for row in prefabs),
        "nativeAudit": native_audit, "evidenceBoundary": contract["evidenceBoundary"],
    }
