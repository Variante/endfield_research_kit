"""Shared readers for published AnimeStudio object indexes.

The exporter owns index production.  Consumers use this module to make the
published merged index the first source and resolve an indexed object to
its exported document, a row of the export's Unity object store
(``game/Unity.sqlite``, see scripts/game_data/unity_store.py).
"""

from __future__ import annotations

import gzip
import json
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from scripts.source_paths import INSTALLED_LAYERS, ExportLayout
from scripts.game_data.unity_store import UnityObjectRow, UnityObjectStore
from scripts.game_data.extraction.unity_overlay import chunk_slot_key, effective_chunk_slot_keys


class ObjectIndexUnavailable(RuntimeError):
    """The published index is absent, incomplete, or malformed."""


def object_index_dir(export_root: Path, source: str) -> Path:
    return ExportLayout(export_root).object_index_dir(source)


def published_object_index_path(export_root: Path, source: str) -> Path:
    directory = object_index_dir(export_root, source)
    summary_path = directory / "summary.json"
    objects_path = directory / "objects.jsonl.gz"
    if not summary_path.is_file():
        raise ObjectIndexUnavailable(f"{source}: missing published object-index summary")
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ObjectIndexUnavailable(f"{source}: unreadable object-index summary: {exc}") from exc
    if not isinstance(summary, dict) or summary.get("complete") is not True:
        raise ObjectIndexUnavailable(f"{source}: published object index is incomplete")
    outputs = summary.get("outputs")
    output = outputs.get("objects") if isinstance(outputs, dict) else None
    if not isinstance(output, dict):
        raise ObjectIndexUnavailable(f"{source}: published object output is not declared")
    declared = Path(str(output.get("path") or ""))
    if declared.name != declared.as_posix() or declared.name != objects_path.name:
        raise ObjectIndexUnavailable(f"{source}: unsafe or unsupported object output path")
    if not objects_path.is_file():
        raise ObjectIndexUnavailable(f"{source}: published object output is missing")
    return objects_path


def iter_published_objects(export_root: Path, source: str) -> Iterator[dict[str, Any]]:
    """Yield object rows from the validated merged index exactly once."""

    path = published_object_index_path(export_root, source)
    try:
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ObjectIndexUnavailable(
                        f"{source}: malformed object row {line_number}: {exc}"
                    ) from exc
                if not isinstance(row, dict) or row.get("recordType") != "object":
                    continue
                yield row
    except OSError as exc:
        raise ObjectIndexUnavailable(f"{source}: cannot read object index: {exc}") from exc


def load_published_schema_fields(export_root: Path, source: str) -> dict[str, frozenset[str]]:
    """schemaId -> serialized field paths from the layer's merged schema output.

    Returns an empty mapping when the index declares no schema output; raises
    ObjectIndexUnavailable when a declared output is missing or malformed.
    """
    published_object_index_path(export_root, source)
    directory = object_index_dir(export_root, source)
    summary = json.loads((directory / "summary.json").read_text(encoding="utf-8"))
    output = ((summary.get("outputs") or {}).get("schemas") or {})
    declared = Path(str(output.get("path") or ""))
    if not output:
        return {}
    if declared.name != declared.as_posix() or not declared.name:
        raise ObjectIndexUnavailable(f"{source}: unsafe schema output path")
    fields: dict[str, frozenset[str]] = {}
    try:
        with gzip.open(directory / declared.name, "rt", encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ObjectIndexUnavailable(
                        f"{source}: malformed schema row {line_number}: {exc}"
                    ) from exc
                if isinstance(row, dict) and row.get("recordType") == "schema" and row.get("schemaId"):
                    fields[str(row["schemaId"])] = frozenset(str(value) for value in row.get("fields") or [])
    except OSError as exc:
        raise ObjectIndexUnavailable(f"{source}: cannot read schema index: {exc}") from exc
    return fields


def _object_identity(row: dict[str, Any]) -> tuple[str, str] | None:
    identity = row.get("object") if isinstance(row.get("object"), dict) else {}
    serialized = str(identity.get("serializedFile") or "")
    path_id = identity.get("pathId")
    if not serialized or path_id is None:
        return None
    return serialized.casefold(), str(path_id)


def is_effective_row(row: dict[str, Any], slot_keys: frozenset | None) -> bool:
    """Whether an index row's bundle slot is one the client loads.

    ``slot_keys`` is ``effective_chunk_slot_keys(export_root)``; with no
    catalogues (None) every row is kept.
    """
    if slot_keys is None:
        return True
    identity = row.get("object") if isinstance(row.get("object"), dict) else {}
    source = identity.get("source")
    offset = identity.get("sourceOffset")
    return source is not None and offset is not None and chunk_slot_key(source, offset) in slot_keys


class EffectiveObjectRows:
    """Yield a raw index stream without objects from replaced or deleted bundles.

    ``read`` counts every ``object`` row, including dropped ones, so a caller's
    check against the published ``counts.objects`` still covers the whole
    index. Rows of other record types pass through uncounted.
    """

    def __init__(self, rows: Iterable[dict[str, Any]], slot_keys: frozenset | None) -> None:
        self._rows = rows
        self._slot_keys = slot_keys
        self.read = 0

    def __iter__(self) -> Iterator[dict[str, Any]]:
        for row in self._rows:
            if row.get("recordType") != "object":
                yield row
                continue
            self.read += 1
            if is_effective_row(row, self._slot_keys):
                yield row


def iter_effective_layer_objects(export_root: Path, source: str) -> Iterator[dict[str, Any]]:
    """One layer's published rows, without objects from replaced or deleted bundles."""
    slot_keys = effective_chunk_slot_keys(export_root)
    for row in iter_published_objects(export_root, source):
        if is_effective_row(row, slot_keys):
            yield row


def iter_effective_objects(export_root: Path) -> Iterator[tuple[str, dict[str, Any]]]:
    """Yield (layer, row) once per object the client loads.

    Each installed layer has its own index, and the base layer's index still
    lists objects from bundles the newer manifest replaced or deleted. A row
    is kept when its bundle slot (chunk, offset) is in the effective VFS
    catalogue; one asset packed into several live bundles is yielded once,
    newest layer first. Without the catalogues, a base row is dropped when a
    newer layer already yielded the same serialized file and PathID. Every
    layer's index must be readable, or this fails closed.
    """
    slot_keys = effective_chunk_slot_keys(export_root)
    layers = list(reversed(INSTALLED_LAYERS))
    failures: list[str] = []
    for layer in layers:
        try:
            published_object_index_path(export_root, layer)
        except ObjectIndexUnavailable as exc:
            failures.append(str(exc))
    if failures:
        raise ObjectIndexUnavailable("; ".join(failures))
    seen: set[tuple[str, str]] = set()
    for layer in layers:
        for row in iter_published_objects(export_root, layer):
            if not is_effective_row(row, slot_keys):
                continue
            key = _object_identity(row)
            if key is not None:
                if key in seen:
                    continue
                seen.add(key)
            yield layer, row


def indexed_document_key(row: dict[str, Any]) -> tuple[str, str] | None:
    """The ``(type, file name)`` an indexed object is exported as, or None.

    The exporter names each object document ``<name>_p<unsigned PathID hex>.json``
    in its type folder, and the Unity object store keys the row by that name.
    """

    identity = row.get("object") if isinstance(row.get("object"), dict) else {}
    name = str(row.get("name") or "")
    try:
        path_id = int(identity.get("pathId"))
    except (TypeError, ValueError):
        return None
    if not name:
        return None
    return str(row.get("type") or "MonoBehaviour"), f"{name}_p{path_id & ((1 << 64) - 1):016X}.json"


def indexed_object_row(store: UnityObjectStore, row: dict[str, Any]) -> UnityObjectRow | None:
    """The store row of an indexed object, or None when it has no identity or no document."""

    key = indexed_document_key(row)
    return store.row(*key) if key is not None else None


def iter_gzip_jsonl_objects(
    path: Path,
    *,
    error_type: type[Exception] = ValueError,
) -> Iterable[dict[str, Any]]:
    try:
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise error_type(f"{path}:{line_number}: row is not an object")
                yield value
    except (OSError, json.JSONDecodeError) as exc:
        raise error_type(
            f"{path}: cannot read merged object index: {exc}"
        ) from exc
