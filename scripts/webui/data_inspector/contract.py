"""Shared publication contract for WebUI decoded-data inspector datasets."""

from __future__ import annotations

from collections import Counter
import math
from pathlib import Path
import re
from typing import Any, Iterable

from scripts.common import write_json


ROOT_SCHEMA = "endfield.webui.decoded-data-root.v1"
DATASET_SCHEMA = "endfield.webui.decoded-data-dataset.v1"
SHARD_SCHEMA = "endfield.webui.decoded-data-shard.v1"
_SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
_MAX_SAFE_JAVASCRIPT_INTEGER = (1 << 53) - 1

# Who produced a record's ``payload``. The browser labels the two differently
# because they carry different authority, and a publisher must declare it rather
# than let the frontend guess from the payload's shape:
#
#   reader      a maintained ``scripts/game_data`` reader returned this, so its
#               own framing status and ranges describe it exactly.
#   projection  the WebUI publisher assembled it from an already-decoded source.
#               It is a selected part, and the mounted raw file stays
#               authoritative.
PAYLOAD_KINDS = ("reader", "projection")


def _json_safe(value: Any) -> Any:
    """Return strict browser-safe JSON without losing numeric identity."""

    if type(value) is int and abs(value) > _MAX_SAFE_JAVASCRIPT_INTEGER:
        return str(value)
    if isinstance(value, float) and not math.isfinite(value):
        if math.isnan(value):
            return "NaN"
        return "Infinity" if value > 0 else "-Infinity"
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def json_safe(value: Any) -> Any:
    """Public alias: normalize a value exactly as publication would write it.

    A caller that compares against something already written to disk must
    normalize its own side the same way, or a value this function rewrites --
    such as an integer outside JavaScript's exact range -- never compares equal.
    """

    return _json_safe(value)


def _require_id(value: str, label: str) -> str:
    value = str(value or "")
    if not _SAFE_ID.fullmatch(value):
        raise ValueError(f"{label} must match {_SAFE_ID.pattern}: {value!r}")
    return value


def source_descriptor(
    path: Path,
    *,
    export_root: Path,
    media_type: str,
) -> dict[str, Any]:
    """Describe one export file without copying it into ``webui/data``."""

    relative = path.resolve().relative_to(export_root.resolve()).as_posix()
    return {
        "path": relative,
        "href": f"/export_full/{relative}",
        "bytes": path.stat().st_size,
        "mediaType": media_type,
    }


def _require_payload_kind(record: dict[str, Any], dataset_id: str) -> None:
    """A record carrying a payload must say who produced it."""

    kind = record.get("payloadKind")
    if record.get("payload") is None:
        if kind is not None:
            raise ValueError(
                f"{dataset_id}: {record.get('id')!r} declares payloadKind without a payload"
            )
        return
    if kind not in PAYLOAD_KINDS:
        raise ValueError(
            f"{dataset_id}: {record.get('id')!r} payloadKind must be one of "
            f"{PAYLOAD_KINDS}, got {kind!r}"
        )


def _catalog_entry(record: dict[str, Any], shard: str) -> dict[str, Any]:
    source = record.get("source") if isinstance(record.get("source"), dict) else {}
    return {
        "id": str(record["id"]),
        "title": str(record.get("title") or record["id"]),
        "status": str(record.get("status") or "unknown"),
        "summary": str(record.get("summary") or ""),
        "tags": [str(value) for value in record.get("tags") or [] if str(value)],
        "sourcePath": str(source.get("path") or ""),
        "shard": shard,
    }


def publish_dataset(
    output_root: Path,
    *,
    dataset_id: str,
    title: str,
    description: str,
    records: Iterable[dict[str, Any]],
    provenance: dict[str, Any],
    shard_size: int = 100,
    available: bool = True,
    diagnostic: str = "",
) -> dict[str, Any]:
    """Write one deterministic catalog and its lazy record shards."""

    dataset_id = _require_id(dataset_id, "dataset_id")
    if shard_size < 1:
        raise ValueError("shard_size must be positive")
    dataset_dir = output_root / "datasets" / dataset_id
    dataset_dir.mkdir(parents=True, exist_ok=True)

    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for record in records:
        if not isinstance(record, dict):
            raise ValueError(f"{dataset_id}: record is not an object")
        record_id = str(record.get("id") or "")
        if not record_id:
            raise ValueError(f"{dataset_id}: record id is empty")
        if record_id in seen:
            raise ValueError(f"{dataset_id}: duplicate record id {record_id!r}")
        seen.add(record_id)
        _require_payload_kind(record, dataset_id)
        normalized.append(_json_safe(record))
    normalized.sort(key=lambda row: str(row["id"]).casefold())

    expected_shards: set[str] = set()
    catalog: list[dict[str, Any]] = []
    shards: list[dict[str, Any]] = []
    for offset in range(0, len(normalized), shard_size):
        rows = normalized[offset:offset + shard_size]
        name = f"records.{offset // shard_size:04d}.json"
        expected_shards.add(name)
        write_json(
            dataset_dir / name,
            {
                "schema": SHARD_SCHEMA,
                "datasetId": dataset_id,
                "offset": offset,
                "records": rows,
            },
        )
        catalog.extend(_catalog_entry(row, name) for row in rows)
        shards.append({"path": name, "offset": offset, "count": len(rows)})

    for stale in dataset_dir.glob("records.*.json"):
        if stale.name not in expected_shards:
            stale.unlink()

    statuses = Counter(str(row.get("status") or "unknown") for row in normalized)
    manifest = {
        "schema": DATASET_SCHEMA,
        "id": dataset_id,
        "title": title,
        "description": description,
        "available": bool(available),
        "diagnostic": diagnostic,
        "recordCount": len(normalized),
        "statusCounts": dict(sorted(statuses.items())),
        "provenance": _json_safe(provenance),
        "shardSize": shard_size,
        "catalog": catalog,
        "shards": shards,
    }
    write_json(dataset_dir / "index.json", manifest)
    return {
        "id": dataset_id,
        "title": title,
        "description": description,
        "available": bool(available),
        "diagnostic": diagnostic,
        "recordCount": len(normalized),
        "statusCounts": dict(sorted(statuses.items())),
        "path": f"datasets/{dataset_id}/index.json",
    }


def publish_root_index(output_root: Path, datasets: Iterable[dict[str, Any]]) -> Path:
    output_root.mkdir(parents=True, exist_ok=True)
    path = output_root / "index.json"
    write_json(
        path,
        {
            "schema": ROOT_SCHEMA,
            "datasets": list(datasets),
        },
    )
    return path
