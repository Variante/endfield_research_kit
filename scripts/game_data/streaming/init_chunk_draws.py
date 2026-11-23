"""Static renderer draw references stored in InitChunkData entity columns.

InitChunkData (``raw/Streaming/PC/<level>/Streaming/InitChunkData_*.bytes``)
is an inverted-LZ4 FlatBuffer of ECS column groups. Each group pairs an entity
id vector with ``(u16 id, u16 stride, u32 0)`` descriptors and a
descriptor-major column blob. This reader frames that container exactly
(every group's column sizes must fill its blob) and decodes the static
renderer columns:

* ``18`` instance constants, whose first 64 bytes are the column-major
  object-to-world matrix (Unity, left-handed);
* ``21`` the 64-byte NUL-padded entity name;
* ``8..14`` draw infos, ``4 + 32*2^n`` bytes for ``n = id - 8``:
  ``u32 count``, ``2^n`` 24-byte infos (submesh at +2, flag word at +16),
  then ``2^n`` ``(f32 max^2, f32 min^2)`` LOD bounds;
* ``68..74`` draw refs, ``8 + 40*2^n`` bytes for ``n = id - 68``:
  ``u64 count`` then ``2^n`` ``(u64 material hash, u64 mesh hash, 24 bytes)``;
* ``67`` LOD ranges: ``u8 lodCount`` and, at +16, ``u8[8]`` cumulative draw
  counts per LOD.

Evidence boundary: the framing, strides and count agreement between the info
and ref columns are ``exact`` for every file this reader accepts. The column
*roles* are ``structuralOnly``: they are read from layout and from the fact
that every hash resolves through the installed StringPathHash catalog to one
``.fbx##<sub-asset>``/``.asset`` mesh path and one ``.mat`` path. No native
consumer of these columns is authenticated here. The column ids and layouts
follow the 0BSD-licensed endfield-noclip reader
(``packages/formats/src/endfield/init-chunk-data.ts``), re-derived and
checked against the installed corpus.

``StringPathCatalog`` resolves a 64-bit StringPathHash value to its stored
path (``raw/ExtendData/Main/StringPathHash.bin``). A hash that matches no
bucket entry returns ``None``; a hash that matches more than one entry raises,
since the join would be ambiguous.
"""

from __future__ import annotations

import re
import struct
from dataclasses import dataclass
from typing import Iterator

from scripts.game_data.extend_data_binary import parse_string_path_hash
from scripts.game_data.inverted_lz4 import decompress_inverted_lz4

MATRIX_COMPONENT = 18
NAME_COMPONENT = 21
LOD_RANGES_COMPONENT = 67
DRAW_INFO_FIRST = 8
DRAW_REF_FIRST = 68
DRAW_REF_LAST = 74
SHADOW_ONLY_FLAG = 1 << 10


class InitChunkDrawError(ValueError):
    """Raised when an InitChunkData payload does not match the framed layout."""


@dataclass(frozen=True)
class RendererDraw:
    material_hash: int
    mesh_hash: int
    submesh: int
    flags: int
    lod: int

    @property
    def shadow_only(self) -> bool:
        return bool(self.flags & SHADOW_ONLY_FLAG)


@dataclass(frozen=True)
class EntityDraws:
    group: int
    index: int
    entity_id: int
    name: str | None
    matrix: tuple[float, ...]
    lod_count: int
    draws: tuple[RendererDraw, ...]


def decode_init_chunk(packed: bytes) -> bytes:
    """Undo the inverted-LZ4 wrapper (``u32`` decoded size, then payload)."""
    if len(packed) < 4:
        raise InitChunkDrawError("InitChunkData payload shorter than its size prefix")
    return decompress_inverted_lz4(packed[4:], struct.unpack_from("<I", packed, 0)[0])


def _u16(data: bytes, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def _u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def _field(data: bytes, table: int, index: int) -> int | None:
    vtable = table - struct.unpack_from("<i", data, table)[0]
    size = _u16(data, vtable)
    if 4 + index * 2 >= size:
        return None
    offset = _u16(data, vtable + 4 + index * 2)
    return table + offset if offset else None


def _target(data: bytes, address: int) -> int:
    return address + _u32(data, address)


def _vector(data: bytes, table: int, index: int) -> tuple[int, int]:
    address = _field(data, table, index)
    if address is None:
        return 0, 0
    vector = _target(data, address)
    return vector + 4, _u32(data, vector)


def _element(data: bytes, vector: int, index: int) -> int:
    return _target(data, vector + index * 4)


def iter_entity_draws(data: bytes) -> Iterator[EntityDraws]:
    """Yield every matrix-bearing entity that carries draw-ref columns."""
    root = _u32(data, 0)
    ids_vector, id_groups = _vector(data, root, 6)
    data_vector, data_groups = _vector(data, root, 7)
    if id_groups != data_groups:
        raise InitChunkDrawError(f"parallel group count mismatch {id_groups}/{data_groups}")
    for group_index in range(data_groups):
        ids_data, id_count = _vector(data, _element(data, ids_vector, group_index), 0)
        group = _element(data, data_vector, group_index)
        count_address = _field(data, group, 1)
        if count_address is None or _u32(data, count_address) != id_count:
            raise InitChunkDrawError(f"group {group_index} entity count mismatch")
        descriptors_data, descriptor_count = _vector(data, group, 3)
        wrapper = _field(data, group, 4)
        if wrapper is None:
            raise InitChunkDrawError(f"group {group_index} has no column blob")
        blob, blob_length = _vector(data, _target(data, wrapper), 0)
        columns: dict[int, tuple[int, int]] = {}
        cursor = 0
        for index in range(descriptor_count):
            type_id, stride, reserved = struct.unpack_from("<HHI", data, descriptors_data + index * 8)
            if reserved:
                raise InitChunkDrawError(f"group {group_index} descriptor {type_id} reserved={reserved}")
            columns[type_id] = (blob + cursor, stride)
            cursor += id_count * stride
        if cursor != blob_length:
            raise InitChunkDrawError(f"group {group_index} columns {cursor} != blob {blob_length}")
        ref_ids = [type_id for type_id in columns if DRAW_REF_FIRST <= type_id <= DRAW_REF_LAST]
        if not ref_ids or MATRIX_COMPONENT not in columns:
            continue
        matrix_at, matrix_stride = columns[MATRIX_COMPONENT]
        if matrix_stride < 64:
            raise InitChunkDrawError(f"group {group_index} matrix stride {matrix_stride}")
        for entity_index in range(id_count):
            matrix = struct.unpack_from("<16f", data, matrix_at + entity_index * matrix_stride)
            name = None
            if NAME_COMPONENT in columns:
                at, stride = columns[NAME_COMPONENT]
                raw = data[at + entity_index * stride:at + (entity_index + 1) * stride].split(b"\0", 1)[0]
                name = raw.decode("utf-8", errors="replace") or None
            draws: list[tuple[int, int, int, int]] = []
            for ref_id in sorted(ref_ids):
                capacity = 1 << (ref_id - DRAW_REF_FIRST)
                info_id = ref_id - (DRAW_REF_FIRST - DRAW_INFO_FIRST)
                if info_id not in columns:
                    raise InitChunkDrawError(f"group {group_index} draw refs {ref_id} without infos {info_id}")
                ref_at, ref_stride = columns[ref_id]
                info_at, info_stride = columns[info_id]
                if ref_stride != 8 + 40 * capacity or info_stride != 4 + 32 * capacity:
                    raise InitChunkDrawError(
                        f"group {group_index} draw strides {ref_stride}/{info_stride} for capacity {capacity}"
                    )
                ref = ref_at + entity_index * ref_stride
                info = info_at + entity_index * info_stride
                count = struct.unpack_from("<Q", data, ref)[0]
                if count > capacity or _u32(data, info) != count:
                    raise InitChunkDrawError(f"group {group_index} entity {entity_index} draw counts disagree")
                for draw in range(count):
                    material, mesh = struct.unpack_from("<QQ", data, ref + 8 + draw * 40)
                    submesh = data[info + 4 + draw * 24 + 2]
                    flags = _u32(data, info + 4 + draw * 24 + 16)
                    draws.append((material, mesh, submesh, flags))
            lod_count = 1
            lods = [0] * len(draws)
            if LOD_RANGES_COMPONENT in columns:
                at, stride = columns[LOD_RANGES_COMPONENT]
                base = at + entity_index * stride
                lod_count = data[base]
                ends = data[base + 16:base + 24]
                lod = 0
                for draw in range(len(draws)):
                    while lod < len(ends) and draw >= ends[lod]:
                        lod += 1
                    if lod >= len(ends):
                        raise InitChunkDrawError(
                            f"group {group_index} entity {entity_index} has more draws than LOD ranges"
                        )
                    lods[draw] = lod
            yield EntityDraws(
                group=group_index,
                index=entity_index,
                entity_id=_u32(data, ids_data + entity_index * 4),
                name=name,
                matrix=matrix,
                lod_count=lod_count,
                draws=tuple(
                    RendererDraw(material, mesh, submesh, flags, lods[position])
                    for position, (material, mesh, submesh, flags) in enumerate(draws)
                ),
            )


_ASSET_ROW = re.compile(
    rb'\{\s*"Name": "((?:[^"\\]|\\.)*)",\s*"Container": "((?:[^"\\]|\\.)*)",\s*'
    rb'"Source": "(?:[^"\\]|\\.)*",\s*"PathID": (-?\d+),\s*"Type": "(Mesh|Material)"'
)


def split_mesh_path(path: str) -> tuple[str, str | None]:
    """Split a catalog mesh path into (lowercase container, sub-asset name)."""
    container, _, sub_asset = path.partition("##")
    return container.casefold(), sub_asset or None


def scan_asset_map(path, containers: set[str]) -> dict[tuple[str, str], dict[str, set[int]]]:
    """Collect Mesh/Material rows of an AnimeStudio asset map for ``containers``.

    Returns ``{(type, container): {casefolded Name: {PathID, ...}}}``. The map
    is streamed through one regex pass; rows of other types are skipped.
    """
    import json
    import mmap

    out: dict[tuple[str, str], dict[str, set[int]]] = {}
    wanted = {value.casefold() for value in containers}
    with open(path, "rb") as source, mmap.mmap(source.fileno(), 0, access=mmap.ACCESS_READ) as view:
        for match in _ASSET_ROW.finditer(view):
            container = json.loads(b'"' + match.group(2) + b'"').casefold()
            if container not in wanted:
                continue
            name = json.loads(b'"' + match.group(1) + b'"').casefold()
            type_name = match.group(4).decode()
            out.setdefault((type_name, container), {}).setdefault(name, set()).add(int(match.group(3)))
    return out


class StringPathCatalog:
    """Exact StringPathHash value -> stored path lookup."""

    def __init__(self, raw: bytes, *, source: str = "StringPathHash") -> None:
        parsed = parse_string_path_hash(raw, source=source)
        if parsed.consumed_bytes != len(raw):
            raise InitChunkDrawError(f"{source}: catalog does not end at EOF")
        self._raw = raw
        self._count = parsed.count
        self._strings = parsed.str_data_offset
        self._cache: dict[int, str | None] = {}

    def lookup(self, value: int) -> str | None:
        if value in self._cache:
            return self._cache[value]
        raw = self._raw
        offset, count = struct.unpack_from("<II", raw, 8 + (value % self._count) * 8)
        found: list[str] = []
        for index in range(count):
            _word, candidate, path_offset = struct.unpack_from("<IQI", raw, offset + index * 16)
            if candidate != value:
                continue
            start = self._strings + path_offset
            length = _u32(raw, start)
            found.append(raw[start + 4:start + 4 + length].decode("utf-16-le", "strict"))
        if len(found) > 1:
            raise InitChunkDrawError(f"StringPathHash {value:016X} matches {len(found)} paths")
        result = found[0] if found else None
        self._cache[value] = result
        return result
