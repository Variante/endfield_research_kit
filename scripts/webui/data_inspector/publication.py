"""Read a complete Data publication after validating its selected export sources.

Cross-page consumers use this read-only boundary instead of importing the Data
builder or decoding its sources again. Each caller supplies its native gate.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable

from scripts.webui.data_inspector.contract import (
    DATASET_SCHEMA, ROOT_SCHEMA, SHARD_SCHEMA, json_safe,
)

def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"object expected: {path.name}")
    return value


def _within(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    path.relative_to(root.resolve())
    return path


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label}: object expected")
    return value


def _rows(value: Any, label: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ValueError(f"{label}: list expected")
    return [_object(row, f"{label}[{index}]") for index, row in enumerate(value)]


def input_file_signature(root: Path) -> dict[str, Any]:
    """Data's documented loose-file cache signature, checked without decoding."""
    digest = hashlib.sha256()
    total = latest = count = 0
    for path in sorted(root.rglob("*.json")):
        stat = path.stat()
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0" + str(stat.st_size).encode("ascii"))
        digest.update(b"\0" + str(stat.st_mtime_ns).encode("ascii") + b"\n")
        count += 1
        total += stat.st_size
        latest = max(latest, stat.st_mtime_ns)
    return json_safe({"algorithm": "relative-path-size-mtime-ns-sha256",
                      "sha256": digest.hexdigest(), "files": count,
                      "bytes": total, "latestMtimeNs": latest})


def load_dataset(data_root: Path, export_root: Path, dataset: str, source_root_rel: str,
                 *, signature_check: Callable[[dict[str, Any]], str] | None = None,
                 ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Validate the complete published family; optional caller owns native proof.

    ``signature_check`` receives the recorded input signature and returns a
    diagnostic on rejection. Consumers of native-backed fields must supply it.
    """
    audit: dict[str, Any] = {"datasetId": dataset, "status": "unavailable"}
    try:
        root = _read(data_root / "index.json")
        if root.get("schema") != ROOT_SCHEMA:
            raise ValueError("Data root schema is unsupported")
        descriptors = [row for row in _rows(root.get("datasets"), "Data root datasets") if row.get("id") == dataset]
        if len(descriptors) > 1:
            raise ValueError(f"Data root has duplicate dataset descriptors: {dataset}")
        descriptor = descriptors[0] if descriptors else None
        if not descriptor or not descriptor.get("available"):
            raise ValueError((descriptor or {}).get("diagnostic") or "Data dataset is not published")
        manifest_path = _within(data_root, str(descriptor["path"]))
        manifest = _read(manifest_path)
        if manifest.get("schema") != DATASET_SCHEMA or manifest.get("id") != dataset:
            raise ValueError("Data dataset schema/id mismatch")
        if not manifest.get("available"):
            raise ValueError(manifest.get("diagnostic") or "Data dataset is unavailable")
        provenance = _object(manifest.get("provenance"), "Data provenance")
        if provenance.get("sourceRoot") != source_root_rel:
            raise ValueError("Data sourceRoot does not match the requested family")
        source_root = _within(export_root, source_root_rel)
        if not source_root.is_dir():
            raise ValueError(f"source directory missing: {source_root_rel}")
        current = input_file_signature(source_root)
        recorded = _object(provenance.get("inputSignature"), "Data provenance inputSignature")
        if any(recorded.get(key) != value for key, value in current.items()):
            raise ValueError("Data publication is stale for the selected export; rebuild the Data page")
        if signature_check:
            diagnostic = signature_check(recorded)
            if diagnostic:
                raise ValueError(diagnostic)
        catalog = _rows(manifest.get("catalog"), "Data catalog")
        expected = {str(row.get("id")): row for row in catalog}
        if len(expected) != len(catalog) or len(catalog) != manifest.get("recordCount"):
            raise ValueError("Data catalog ids/count mismatch")
        records: list[dict[str, Any]] = []
        seen: set[str] = set()
        for shard in _rows(manifest.get("shards"), "Data shards"):
            payload = _read(_within(manifest_path.parent, str(shard["path"])))
            rows = _rows(payload.get("records"), f"Data shard {shard['path']} records")
            if (payload.get("schema") != SHARD_SCHEMA or payload.get("datasetId") != dataset
                    or payload.get("offset") != shard.get("offset") or len(rows) != shard.get("count")):
                raise ValueError(f"Data shard schema/count mismatch: {shard['path']}")
            for row in rows:
                key = str(row.get("id") or "")
                entry = expected.get(key) or {}
                source = _object(row.get("source"), f"Data record {key} source")
                if (key in seen or entry.get("shard") != shard["path"]
                        or entry.get("status") != row.get("status")
                        or entry.get("sourcePath") != source.get("path")):
                    raise ValueError(f"Data shard/catalog mismatch: {key}")
                source_path = _within(source_root, str(_within(export_root, source["path"]).relative_to(source_root)))
                if source_path.stat().st_size != source.get("bytes"):
                    raise ValueError(f"Data source size mismatch: {source['path']}")
                seen.add(key)
                records.append(row)
        if seen != set(expected) or len(records) != descriptor.get("recordCount"):
            raise ValueError("Data root/catalog/shard record count mismatch")
        audit.update(status="current", recordCount=len(records), inputSignature=current,
                     manifestSha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest())
        return records, audit
    except (OSError, ValueError, KeyError, TypeError, StopIteration) as exc:
        audit["diagnostic"] = str(exc)[:600]
        return [], audit


