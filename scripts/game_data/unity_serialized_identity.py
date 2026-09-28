"""Read object identities from a no-type-tree Unity serialized file (v22).

This narrow reader covers the installed standalone ``Resources`` files.  It
requires their whole metadata region to close at the declared boundary.  Unity
bundles with type trees or external tables need a separate, fuller reader.
"""

from __future__ import annotations

from dataclasses import dataclass
import struct


class UnitySerializedIdentityError(ValueError):
    pass


@dataclass(frozen=True)
class UnityObjectIdentity:
    path_id: int
    class_id: int
    byte_start: int
    byte_size: int


@dataclass(frozen=True)
class UnitySerializedIdentity:
    unity_version: str
    platform: int
    objects: tuple[UnityObjectIdentity, ...]


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise UnitySerializedIdentityError(reason)


def _read(fmt: str, data: bytes, offset: int, end: int, label: str) -> tuple[int, int]:
    width = struct.calcsize(fmt)
    _require(0 <= offset <= end - width, f"truncated {label} at {offset}")
    return struct.unpack_from(fmt, data, offset)[0], offset + width


def parse_no_type_tree_v22(data: bytes) -> UnitySerializedIdentity:
    """Return exact ``(PathID, classID, source span)`` rows or fail closed."""
    _require(len(data) >= 48, "truncated v22 header")
    version = struct.unpack_from(">I", data, 8)[0]
    endian = data[16]
    metadata_size = struct.unpack_from(">I", data, 20)[0]
    file_size = struct.unpack_from(">Q", data, 24)[0]
    data_offset = struct.unpack_from(">Q", data, 32)[0]
    metadata_end = 48 + metadata_size
    _require(version == 22 and endian == 0, "unsupported Unity version or endian")
    _require(file_size == len(data) and 48 < metadata_end <= data_offset <= len(data),
             "header file or metadata bounds differ")

    cursor = 48
    version_end = data.find(b"\0", cursor, metadata_end)
    _require(version_end >= cursor, "Unity version terminator missing")
    try:
        unity_version = data[cursor:version_end].decode("ascii")
    except UnicodeDecodeError as error:
        raise UnitySerializedIdentityError("Unity version is not ASCII") from error
    _require(bool(unity_version), "Unity version is empty")
    cursor = version_end + 1
    platform, cursor = _read("<i", data, cursor, metadata_end, "platform")
    type_tree, cursor = _read("<B", data, cursor, metadata_end, "type-tree flag")
    _require(type_tree == 0, "type tree enabled")
    type_count, cursor = _read("<i", data, cursor, metadata_end, "type count")
    _require(0 <= type_count <= (metadata_end - cursor) // 23, "type count cannot fit")
    classes: list[int] = []
    for index in range(type_count):
        class_id, cursor = _read("<i", data, cursor, metadata_end, f"type {index} class ID")
        stripped, cursor = _read("<B", data, cursor, metadata_end, f"type {index} stripped")
        script_index, cursor = _read("<h", data, cursor, metadata_end, f"type {index} script index")
        _require(stripped in (0, 1), f"invalid stripped flag for type {index}")
        _require(script_index >= -1, f"invalid script index for type {index}")
        if class_id == 114:
            _require(cursor + 16 <= metadata_end, f"truncated script ID for type {index}")
            cursor += 16
        _require(cursor + 16 <= metadata_end, f"truncated type hash for type {index}")
        cursor += 16
        classes.append(class_id)

    object_count, cursor = _read("<i", data, cursor, metadata_end, "object count")
    _require(0 <= object_count <= (metadata_end - cursor) // 24, "object count cannot fit")
    objects: list[UnityObjectIdentity] = []
    seen: set[int] = set()
    for index in range(object_count):
        cursor = (cursor + 3) & ~3
        path_id, cursor = _read("<q", data, cursor, metadata_end, f"object {index} PathID")
        byte_start, cursor = _read("<q", data, cursor, metadata_end, f"object {index} start")
        byte_size, cursor = _read("<I", data, cursor, metadata_end, f"object {index} length")
        type_id, cursor = _read("<i", data, cursor, metadata_end, f"object {index} type")
        _require(path_id not in seen, f"duplicate PathID {path_id}")
        _require(0 <= type_id < len(classes), f"object {index} type index out of range")
        absolute = data_offset + byte_start
        _require(data_offset <= absolute <= len(data) - byte_size,
                 f"object {index} byte span outside file")
        seen.add(path_id)
        objects.append(UnityObjectIdentity(path_id, classes[type_id], absolute, byte_size))

    script_count, cursor = _read("<i", data, cursor, metadata_end, "script count")
    _require(0 <= script_count <= (metadata_end - cursor) // 12,
             "script identifier count cannot fit")
    for index in range(script_count):
        _, cursor = _read("<i", data, cursor, metadata_end, f"script {index} file index")
        cursor = (cursor + 3) & ~3
        _, cursor = _read("<q", data, cursor, metadata_end, f"script {index} PathID")
    external_count, cursor = _read("<i", data, cursor, metadata_end, "external count")
    _require(external_count == 0, "external table is unsupported")
    ref_type_count, cursor = _read("<i", data, cursor, metadata_end, "reference type count")
    _require(ref_type_count == 0, "reference type table is unsupported")
    _require(cursor + 1 == metadata_end and data[cursor] == 0,
             "user information or trailing metadata is unsupported")
    spans = sorted((item.byte_start, item.byte_start + item.byte_size) for item in objects)
    _require(all(left[1] <= right[0] for left, right in zip(spans, spans[1:])),
             "object byte spans overlap")
    return UnitySerializedIdentity(unity_version, platform, tuple(objects))


def object_name(data: bytes, item: UnityObjectIdentity) -> str:
    """Read the common first length-prefixed ``m_Name`` used by a Mesh."""
    _require(item.byte_size >= 4, f"object {item.path_id} has no name length")
    length = struct.unpack_from("<I", data, item.byte_start)[0]
    _require(0 < length <= min(1024, item.byte_size - 4),
             f"object {item.path_id} name length out of bounds")
    try:
        return data[item.byte_start + 4:item.byte_start + 4 + length].decode("utf-8")
    except UnicodeDecodeError as error:
        raise UnitySerializedIdentityError(f"object {item.path_id} name is not UTF-8") from error
