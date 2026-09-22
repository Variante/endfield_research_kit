"""The CABMap container index, and the rule that resolves a cross-file PPtr.

The map is a .NET ``BinaryWriter`` stream, and the framing here is taken from
the writer that produces it -- ``AssetsHelper.DumpCABMap`` in the AnimeStudio
submodule -- rather than inferred from the bytes::

    string  BaseFolder
    int32   entryCount
    entryCount times:
        string  cabName
        string  path
        int64   offset
        int32   dependencyCount
        dependencyCount times: string cabName

Strings carry .NET's 7-bit encoded length prefix. Nothing here is a guess, which
is why the reader can insist on consuming every file exactly to EOF: a file that
ends early or late is not a weaker result, it means the writer is not the one
documented above and the caller should stop.

What this gives a caller is the container index: which CAB lives in which file,
at what offset, and which other CABs it depends on. It is not an asset
inventory -- it says nothing about the objects inside a CAB, their types or
their names.

**The dependency list is ordered, and that order is what a PPtr's ``m_FileID``
indexes.** A serialized Unity file names its externals in an array and refers to
them by 1-based position, with 0 meaning the file itself. The exported objects
do not carry that array, so a cross-file PPtr used to resolve to nothing better
than "some other container". It resolves exactly::

    m_FileID == k  ->  dependencies(referring CAB)[k - 1]

That is measured, not assumed, and it was measurable because a PathID already
resolves to exactly one exported object whose own ``sourceFile`` is the answer
the rule predicts. Over a 40,000-object sample the rule agreed on **859 of 859**
checkable references, with no miss, across 82 distinct ``m_FileID`` values and
both VFS roots. The same question asked against a *foreign* dependency list of
equal length agreed on 2 of 100, so the rule carries the information rather than
being cheap to satisfy.

Two things a caller must not skip:

- **Pick the map by the referrer's own VFS root.** 694 CAB names appear in both
  maps with *different* dependency lists, so resolving against the wrong one is
  wrong silently. ``sourceOriginalPath`` in the export's ``$animestudio`` block
  is what names the root: call `vfs_root_of` once, where that path is, and pass
  the *name* onward. This repo has already paid for the alternative -- carrying
  the resolved name and running it back through `vfs_root_of` sends every
  persistent referrer to the streaming map, because the bare string
  ``"Persistent"`` is not a path containing ``Persistent``. It surfaced as one
  contradicted field out of 4,998 checks, which is exactly how little a silent
  two-root error shows.
- **Resolving the container is not resolving the object.** The rule gives the
  target's exact ``(source CAB, PathID)`` -- Unity object identity, the second
  rung of the binding-evidence order. Most targets are GameObjects, Transforms
  and MonoScripts the WebUI export scope never writes, so knowing the container
  is frequently as far as the export can go, and that is a different fact from
  an unresolved reference.
"""

from __future__ import annotations

import os
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from scripts.repo_paths import REPO_ROOT


DEFAULT_CAB_MAP_DIR = REPO_ROOT / "export_full" / "meta" / "cab_map"

#: Each map is written against one VFS root, and the root decides which map a
#: referrer resolves against. The keys are the export's own directory names.
ROOT_MAPS = {
    "Persistent": "endfield_persistent_assets.bin",
    "StreamingAssets": "endfield_streamingassets_assets.bin",
}

#: ``m_FileID`` is 1-based over the externals array; 0 is the file itself.
SELF_FILE_ID = 0

# .NET writes a 7-bit encoded length in at most five bytes.
MAX_LENGTH_BYTES = 5
# A single entry is at least two empty strings, an int64 and an int32.
MINIMUM_ENTRY_BYTES = 1 + 1 + 8 + 4
# A logical file holds one CAB; two is the most this corpus shows.
MAXIMUM_CABS_PER_LOGICAL_FILE = 2


class CabMapError(ValueError):
    """The bytes do not match the documented writer."""


@dataclass(frozen=True)
class CabEntry:
    cab: str
    path: str
    offset: int
    dependencies: tuple[str, ...]


def _read_7bit_length(data: bytes, cursor: int) -> tuple[int, int]:
    value = 0
    shift = 0
    for _ in range(MAX_LENGTH_BYTES):
        if cursor >= len(data):
            raise CabMapError(f"truncated 7-bit length at {cursor}")
        byte = data[cursor]
        cursor += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, cursor
        shift += 7
    raise CabMapError(f"unterminated 7-bit length at {cursor - MAX_LENGTH_BYTES}")


def _read_string(data: bytes, cursor: int) -> tuple[str, int]:
    length, cursor = _read_7bit_length(data, cursor)
    if length < 0 or length > len(data) - cursor:
        raise CabMapError(f"string of {length} bytes runs past the end at {cursor}")
    try:
        return data[cursor:cursor + length].decode("utf-8"), cursor + length
    except UnicodeDecodeError as exc:
        raise CabMapError(f"string at {cursor} is not UTF-8") from exc


def _read_int(data: bytes, cursor: int, fmt: str, width: int, what: str) -> tuple[int, int]:
    if cursor + width > len(data):
        raise CabMapError(f"truncated {what} at {cursor}")
    return struct.unpack_from(fmt, data, cursor)[0], cursor + width


def parse_cabmap(data: bytes) -> tuple[str, list[CabEntry]]:
    """Parse one CABMap, requiring the whole file to be consumed."""
    base_folder, cursor = _read_string(data, 0)
    count, cursor = _read_int(data, cursor, "<i", 4, "entry count")
    if count < 0:
        raise CabMapError(f"negative entry count: {count}")
    # A count larger than the bytes could hold is a corrupt header, not a big map.
    if count > (len(data) - cursor) // MINIMUM_ENTRY_BYTES + 1:
        raise CabMapError(f"entry count {count} cannot fit in {len(data) - cursor} bytes")
    entries: list[CabEntry] = []
    for index in range(count):
        cab, cursor = _read_string(data, cursor)
        path, cursor = _read_string(data, cursor)
        offset, cursor = _read_int(data, cursor, "<q", 8, f"offset of entry {index}")
        if offset < 0:
            raise CabMapError(f"negative offset in entry {index}: {offset}")
        dependency_count, cursor = _read_int(
            data, cursor, "<i", 4, f"dependency count of entry {index}"
        )
        if dependency_count < 0:
            raise CabMapError(f"negative dependency count in entry {index}")
        dependencies: list[str] = []
        for _ in range(dependency_count):
            dependency, cursor = _read_string(data, cursor)
            dependencies.append(dependency)
        entries.append(CabEntry(cab, path, offset, tuple(dependencies)))
    if cursor != len(data):
        raise CabMapError(
            f"trailing bytes: consumed {cursor} of {len(data)}"
        )
    return base_folder, entries


def load_dependencies(
    cab_map_dir: Path = DEFAULT_CAB_MAP_DIR,
) -> dict[str, dict[str, tuple[str, ...]]]:
    """Read both maps into ``{root: {cab: ordered dependencies}}``.

    The two roots are kept apart rather than merged. 694 CAB names appear in
    both with different dependency lists, so a merged table would resolve each
    of those against whichever map happened to be read last.
    """

    directory = Path(cab_map_dir)
    loaded: dict[str, dict[str, tuple[str, ...]]] = {}
    for root, name in ROOT_MAPS.items():
        path = directory / name
        if not path.is_file():
            raise CabMapError(f"CABMap for {root} not found: {path}")
        _, entries = parse_cabmap(path.read_bytes())
        loaded[root] = {entry.cab: entry.dependencies for entry in entries}
    return loaded


def vfs_root_of(source_original_path: str) -> str:
    """Name the VFS root an exported object was read from.

    The export records the installed path it came from, and the root is the
    directory component the two CABMaps are written against. Anything not under
    ``Persistent`` is a StreamingAssets read, which is both the common case and
    the safe default, because the persistent map is the small one.
    """

    marker = f"{os.sep}Persistent{os.sep}"
    normalised = str(source_original_path).replace("/", os.sep).replace("\\", os.sep)
    return "Persistent" if marker in normalised else "StreamingAssets"


def resolve_external_cab(dependencies: Iterable[str], file_id: int) -> str | None:
    """Name the CAB a PPtr's ``m_FileID`` points into, or ``None``.

    ``None`` covers the self reference and an index the referrer's own list does
    not reach. Neither is repairable by guessing: an out-of-range slot means the
    list being read does not belong to this referrer, and returning a
    neighbouring CAB would invent a binding.
    """

    if file_id == SELF_FILE_ID:
        return None
    ordered = tuple(dependencies)
    index = file_id - 1
    if index < 0 or index >= len(ordered):
        return None
    return ordered[index]


def resolve_pptr(
    maps: dict[str, dict[str, tuple[str, ...]]],
    *,
    source_cab: str,
    source_root: str,
    file_id: int,
    path_id: int,
) -> dict[str, Any] | None:
    """Resolve one PPtr to an exact ``(cab, pathId)`` Unity object identity.

    ``source_root`` is a key of `ROOT_MAPS`, not an installed path: callers hold
    the root as a name far more often than as the path it came from, and taking
    the path here invited feeding a name back through `vfs_root_of`, which
    answers ``StreamingAssets`` for the string ``"Persistent"`` and sends every
    persistent referrer to the wrong map without a symptom. An unrecognised
    root is refused for the same reason -- silently defaulting it is how that
    bug stayed invisible. Call `vfs_root_of` once, where the path is.

    ``None`` means the PPtr is null. Every other result carries the basis it
    stands on, because "the container is known and the object is not exported"
    and "nothing resolved" are different answers, and a caller that cannot tell
    them apart will report the wrong one.
    """

    if path_id == 0:
        return None
    if file_id == SELF_FILE_ID:
        return {"cab": source_cab, "pathId": path_id, "tier": "exact", "basis": "self"}
    if source_root not in ROOT_MAPS:
        return {
            "cab": None,
            "pathId": path_id,
            "tier": "unresolved",
            "basis": f"unknown VFS root {source_root!r}",
        }
    dependencies = maps.get(source_root, {}).get(source_cab)
    if dependencies is None:
        return {
            "cab": None,
            "pathId": path_id,
            "tier": "unresolved",
            "basis": f"referrer CAB absent from the {source_root} map",
        }
    cab = resolve_external_cab(dependencies, file_id)
    if cab is None:
        return {
            "cab": None,
            "pathId": path_id,
            "tier": "unresolved",
            "basis": f"m_FileID {file_id} past {len(dependencies)} dependencies",
        }
    return {
        "cab": cab,
        "pathId": path_id,
        "tier": "exact",
        "basis": "cabmap dependency slot",
    }


if __name__ == "__main__":  # pragma: no cover - documented entry point
    raise SystemExit(
        "this module is a reader; import it, or run python -m scripts.webui.assets.cabmap"
    )
