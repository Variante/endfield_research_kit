"""Decide which exported Unity outputs belong to the client's effective data.

AnimeStudio exports each installed root (StreamingAssets, Persistent) in its
own run, so the StreamingAssets run also exports bundles that a hot update has
replaced or deleted. The client loads one logical file per VFS path, chosen by
the newest block manifest. That manifest is the Persistent VFS catalogue: its
Bundle and InitBundle blocks list every logical file once, each resolved to
the chunk (Persistent or StreamingAssets) that holds the live copy.

A slot is ``(normalized chunk path, offset)``: one logical file inside one
chunk. An export output is kept exactly when its source slot is in the
effective slot set. That single rule covers replaced bundles (their
StreamingAssets slot is not effective), new bundles, and bundles the update
deleted. Outputs whose slot cannot be established are reported, never guessed.
"""
from __future__ import annotations

import functools
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Iterator

from scripts.source_paths import INSTALLED_LAYERS, ExportLayout

OVERLAY_BLOCK_INDEXES: tuple[str, ...] = ("bundle", "initial-bundle")
EFFECTIVE_LAYER = INSTALLED_LAYERS[-1]
BASE_LAYER = INSTALLED_LAYERS[0]

Slot = tuple[str, int]

_PATH_ID_SUFFIX_RE = re.compile(r"_p([0-9A-Fa-f]{16})(?=\.|$)")
_JSON_SOURCE_RE = re.compile(rb'"sourceOriginalPath"\s*:\s*"((?:[^"\\]|\\.)*)"')
_JSON_OFFSET_RE = re.compile(rb'"sourceOffset"\s*:\s*(-?\d+)')
_JSON_HEAD_BYTES = 16384


class OverlayError(RuntimeError):
    """The catalogues cannot prove which outputs are effective."""


def normalize_chunk_path(path: str) -> str:
    return os.path.normcase(os.path.normpath(str(path).replace("/", os.sep)))


def vfs_index_path(vfs_index_dir: Path, block_index: str) -> Path:
    return vfs_index_dir / f"{block_index}_vfs_index.json"


@dataclass
class OverlayCatalog:
    """Effective slots plus the base slots they supersede, with the proof."""

    effective: dict[Slot, str] = field(default_factory=dict)
    base: dict[Slot, str] = field(default_factory=dict)
    block_evidence: list[dict] = field(default_factory=list)

    def is_effective(self, slot: Slot) -> bool:
        return slot in self.effective

    def superseded_base_slots(self) -> set[Slot]:
        return set(self.base) - set(self.effective)

    def deleted_logical_files(self) -> set[str]:
        return set(self.base.values()) - set(self.effective.values())

    def is_stale_chunk(self, slot: Slot) -> bool:
        """The slot's chunk sits in a block folder these catalogues index, yet
        neither catalogue lists that chunk and the chunk is gone from the
        install: an older build's chunk.

        A slot whose block folder is unknown (for example after the game was
        installed elsewhere) is not called stale, and neither is a chunk that
        still exists (it may be newer than the catalogues); both stay unproven.
        """
        chunk = slot[0]
        known_chunks = self._known_chunks()
        if chunk in known_chunks[0]:
            return False
        return os.path.dirname(chunk) in known_chunks[1] and not os.path.exists(chunk)

    def _known_chunks(self) -> tuple[set[str], set[str]]:
        cached = getattr(self, "_known_chunk_cache", None)
        if cached is None:
            chunks = {slot[0] for slot in (*self.base, *self.effective)}
            cached = (chunks, {os.path.dirname(chunk) for chunk in chunks})
            self._known_chunk_cache = cached
        return cached


def _read_index(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise OverlayError(f"cannot read VFS index {path}: {exc}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("files"), list):
        raise OverlayError(f"VFS index has no file list: {path}")
    return payload


def _check_complete(path: Path, payload: dict) -> dict:
    blocks = payload.get("blocks") or []
    if payload.get("missingBlocks"):
        raise OverlayError(f"{path}: missing blocks {payload['missingBlocks']}")
    if len(blocks) != 1:
        raise OverlayError(f"{path}: expected one block, found {len(blocks)}")
    block = blocks[0]
    if int(block.get("missingChunkCount") or 0) != 0:
        raise OverlayError(f"{path}: {block['missingChunkCount']} missing chunk(s)")
    declared = block.get("declaredFileCount")
    if declared is None or int(declared) != len(payload["files"]):
        raise OverlayError(
            f"{path}: block declares {declared} file(s) but the index lists {len(payload['files'])}"
        )
    return block


def _slots(payload: dict, path: Path) -> dict[Slot, str]:
    out: dict[Slot, str] = {}
    for row in payload["files"]:
        slot = (normalize_chunk_path(row["chunkAbsolutePath"]), int(row["offset"]))
        previous = out.get(slot)
        if previous is not None and previous != row["fileName"]:
            raise OverlayError(f"{path}: slot {slot} holds both {previous} and {row['fileName']}")
        out[slot] = row["fileName"]
    return out


def load_overlay_catalog(base_vfs_index_dir: Path, effective_vfs_index_dir: Path) -> OverlayCatalog:
    """Load both layers' catalogues and prove the effective one is the newer manifest."""
    catalog = OverlayCatalog()
    for block_index in OVERLAY_BLOCK_INDEXES:
        base_path = vfs_index_path(base_vfs_index_dir, block_index)
        effective_path = vfs_index_path(effective_vfs_index_dir, block_index)
        base_payload = _read_index(base_path)
        effective_payload = _read_index(effective_path)
        base_block = _check_complete(base_path, base_payload)
        effective_block = _check_complete(effective_path, effective_payload)
        if base_block.get("blockType") != effective_block.get("blockType"):
            raise OverlayError(
                f"block type mismatch: {base_path} has {base_block.get('blockType')}, "
                f"{effective_path} has {effective_block.get('blockType')}"
            )
        if int(effective_block.get("version") or 0) < int(base_block.get("version") or 0):
            raise OverlayError(
                f"{effective_path}: {EFFECTIVE_LAYER} block version {effective_block.get('version')} is older "
                f"than {BASE_LAYER} version {base_block.get('version')}; the overlay is conflicting"
            )
        catalog.base.update(_slots(base_payload, base_path))
        catalog.effective.update(_slots(effective_payload, effective_path))
        catalog.block_evidence.append({
            "block": effective_block.get("blockType"),
            "baseVersion": base_block.get("version"),
            "effectiveVersion": effective_block.get("version"),
            "baseFileCount": len(base_payload["files"]),
            "effectiveFileCount": len(effective_payload["files"]),
        })
    # Index readers match slots by chunk file name (chunk_slot_key), which is
    # sound only while one name never denotes two chunks across both layers.
    chunks_by_name: dict[str, str] = {}
    for chunk, _offset in (*catalog.base, *catalog.effective):
        name = os.path.basename(chunk).lower()
        other = chunks_by_name.setdefault(name, chunk)
        if other != chunk:
            raise OverlayError(f"chunk file name {name} names two chunks: {other} and {chunk}")
    return catalog


ChunkSlotKey = tuple[str, int]


def chunk_slot_key(chunk_path: str, offset: int) -> ChunkSlotKey:
    """(chunk file name, bundle offset): readers that record the chunk relative
    to their layer root match catalogue slots this way. Chunk files are named
    by content hash, so the name identifies the chunk across both layers."""
    return (os.path.basename(str(chunk_path).replace("\\", "/")).lower(), int(offset))


@functools.lru_cache(maxsize=4)
def _effective_chunk_slot_keys(export_root_text: str) -> frozenset[ChunkSlotKey] | None:
    layout = ExportLayout(Path(export_root_text))
    base, effective = INSTALLED_LAYERS[0], INSTALLED_LAYERS[-1]
    if not (vfs_index_path(layout.vfs_index_dir(base), "bundle").is_file()
            and vfs_index_path(layout.vfs_index_dir(effective), "bundle").is_file()):
        return None
    catalog = load_overlay_catalog(layout.vfs_index_dir(base), layout.vfs_index_dir(effective))
    return frozenset(chunk_slot_key(chunk, offset) for chunk, offset in catalog.effective)


def effective_chunk_slot_keys(export_root: Path) -> frozenset[ChunkSlotKey] | None:
    """Every bundle slot the client loads, or None when no overlay applies.

    None is returned only when at most one layer has an object index, so no
    replaced-bundle row can reach a reader. With both layers indexed but a
    catalogue missing, this fails closed instead of keeping every row.
    """
    keys = _effective_chunk_slot_keys(os.path.normcase(os.path.abspath(export_root)))
    if keys is None:
        layout = ExportLayout(export_root)
        indexed = [
            layer for layer in INSTALLED_LAYERS
            if (layout.object_index_dir(layer) / "summary.json").is_file()
        ]
        if len(indexed) > 1:
            raise OverlayError(
                f"{export_root}: both layers have object indexes but a VFS bundle catalogue is missing "
                f"under meta/<Layer>/vfs_index; replaced-bundle rows cannot be excluded"
            )
    return keys


def iter_asset_map_rows(path: Path) -> Iterator[dict]:
    """Stream ``AssetEntries`` rows from an AnimeStudio asset-map JSON.

    The maps run to hundreds of megabytes, so this reads the pretty-printed
    file line by line. It relies on one ``"key": value`` pair per line and
    fails closed on any row that does not carry the four fields it needs.
    """
    row: dict = {}
    in_entries = False
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if not in_entries:
                in_entries = text.startswith('"AssetEntries"')
                continue
            if text in ("{",):
                row = {}
                continue
            if text in ("}", "},"):
                if not {"Source", "Offset", "PathID", "Type"} <= row.keys():
                    raise OverlayError(f"{path}: asset-map row without Source/Offset/PathID/Type: {row}")
                yield row
                row = {}
                continue
            if text.startswith("]"):
                return
            key, sep, value = text.partition(":")
            if not sep:
                raise OverlayError(f"{path}: unexpected asset-map line {text[:120]!r}")
            row[json.loads(key)] = json.loads(value.strip().rstrip(","))
    raise OverlayError(f"{path}: asset map ended before AssetEntries closed")


def path_id_hex(path_id: int) -> str:
    return f"{int(path_id) & 0xFFFFFFFFFFFFFFFF:016X}"


def build_path_id_slots(
    asset_map_paths: Iterable[Path],
    types_out: set[str] | None = None,
) -> dict[str, set[Slot]]:
    """PathID (hex, as in export file names) -> every slot that holds it.

    Pass only the asset maps of the layer whose export run produced the
    outputs being classified. That run loaded only its own chunks, so a
    replaced bundle's objects must not also match the other layer's slot.
    """
    out: dict[str, set[Slot]] = {}
    for path in asset_map_paths:
        for row in iter_asset_map_rows(path):
            slot = (normalize_chunk_path(row["Source"]), int(row["Offset"]))
            out.setdefault(path_id_hex(row["PathID"]), set()).add(slot)
            if types_out is not None:
                types_out.add(str(row["Type"]))
    return out


def json_output_slot(path: Path) -> Slot | None:
    """Read the source slot AnimeStudio records at the head of an object JSON."""
    with path.open("rb") as handle:
        head = handle.read(_JSON_HEAD_BYTES)
    source = _JSON_SOURCE_RE.search(head)
    offset = _JSON_OFFSET_RE.search(head)
    if not source or not offset:
        return None
    return (normalize_chunk_path(json.loads(b'"' + source.group(1) + b'"')), int(offset.group(1)))


def output_path_id_hex(path: Path) -> str | None:
    """The `_p<PathID>` AnimeStudio appends to a name, before any extension.

    Markers such as ``Font Texture_p<id>.png.empty.json`` carry more than one
    extension, so the whole file name is searched, not just the stem.
    """
    matches = _PATH_ID_SUFFIX_RE.findall(path.name)
    return matches[-1].upper() if matches else None


EFFECTIVE = "effective"
SUPERSEDED = "superseded"
# Left over from an earlier run against an older build: its chunk is gone.
STALE = "stale"
UNPROVEN = "unproven"
NO_IDENTITY_REASON = "no source slot and no PathID in the file name"


def classify_output(
    path: Path,
    catalog: OverlayCatalog,
    path_id_slots: dict[str, set[Slot]],
) -> tuple[str, str]:
    """Return (verdict, reason) for one exported file."""
    if path.suffix.lower() == ".json":
        slot = json_output_slot(path)
        if slot is not None:
            if catalog.is_effective(slot):
                return EFFECTIVE, "json source slot is effective"
            if slot in catalog.base:
                return SUPERSEDED, f"json source slot holds {catalog.base[slot]}, replaced or deleted"
            if catalog.is_stale_chunk(slot):
                return STALE, "json source chunk is absent from both catalogues of its indexed block"
            return UNPROVEN, "json source slot is in neither catalogue"
    path_id = output_path_id_hex(path)
    if path_id is None:
        return UNPROVEN, NO_IDENTITY_REASON
    slots = path_id_slots.get(path_id)
    if not slots:
        return UNPROVEN, f"PathID {path_id} is not in the asset maps"
    effective = [slot for slot in slots if catalog.is_effective(slot)]
    if effective:
        # One asset packed into several bundles is one output file; it stays
        # live while any bundle that holds it is still loaded.
        return EFFECTIVE, f"{len(effective)} of {len(slots)} asset-map slot(s) for this PathID are effective"
    return SUPERSEDED, "no asset-map slot for this PathID is effective"
