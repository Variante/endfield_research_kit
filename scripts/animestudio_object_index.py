#!/usr/bin/env python3
"""Deterministically merge AnimeStudio object-index JSONL process parts.

This stdlib-only merger treats the sidecars as original-data evidence and
fails closed: names, GUIDs, PathIDs by themselves, and a worker's first-loaded
external dependency never create an exact edge.
"""

from __future__ import annotations

import argparse
from collections import Counter
import copy
from functools import lru_cache
import gzip
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from typing import Any, Callable, Iterable


PART_SCHEMA_VERSION = 1
MERGE_CONTRACT = "endfield-animestudio-object-index-merge-v1"
MERGED_RESOLUTION_STATUS = "resolved_postmerge_unique_external_filename_pathid"
MERGED_RESOLUTION_BASIS = "postmerge_unique_external_filename_pathid"
COUNT_KEYS = (
    "objects",
    "schemas",
    "monoScripts",
    "scalars",
    "pptrs",
    "objectsWithTruncatedScalars",
)


class MergeError(RuntimeError):
    pass


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise MergeError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def parse_json(text: str, context: str) -> Any:
    try:
        return json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise MergeError(f"{context}: invalid JSON: {exc}") from exc


def canonical_json(value: Any) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as exc:
        raise MergeError(f"value is not canonical JSON: {exc}") from exc


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_int(value: Any, context: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise MergeError(f"{context}: expected integer")
    return value


def validate_identity(value: Any, context: str) -> tuple[str, str, int, int]:
    if not isinstance(value, dict):
        raise MergeError(f"{context}: object identity is missing")
    expected = {"serializedFile", "source", "sourceOffset", "pathId"}
    if set(value) != expected:
        raise MergeError(f"{context}: identity keys must be {sorted(expected)}")
    serialized_file = value["serializedFile"]
    source = value["source"]
    if not isinstance(serialized_file, str) or not serialized_file:
        raise MergeError(f"{context}: serializedFile must be nonempty")
    if not isinstance(source, str):
        raise MergeError(f"{context}: source must be a string")
    source_offset = require_int(value["sourceOffset"], f"{context}.sourceOffset")
    path_id = require_int(value["pathId"], f"{context}.pathId")
    if source_offset < 0:
        raise MergeError(f"{context}: sourceOffset must be nonnegative")
    if not -(1 << 63) <= path_id < (1 << 63):
        raise MergeError(f"{context}: pathId is outside signed Int64")
    return serialized_file, source, source_offset, path_id


def identity_key(identity: dict[str, Any]) -> str:
    return canonical_json(list(validate_identity(identity, "identity")))


def target_identity_key(target: Any, context: str) -> str:
    if not isinstance(target, dict):
        raise MergeError(f"{context}: target is not an object")
    identity = {
        key: target.get(key)
        for key in ("serializedFile", "source", "sourceOffset", "pathId")
    }
    return canonical_json(list(validate_identity(identity, context)))


def schema_digest(fields: list[str]) -> str:
    return hashlib.sha256("\n".join(fields).encode("utf-8")).hexdigest()


def connect_database(path: Path) -> sqlite3.Connection:
    if path.exists():
        path.unlink()
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        PRAGMA journal_mode=OFF;
        PRAGMA synchronous=OFF;
        PRAGMA temp_store=FILE;
        CREATE TABLE schemas (
            schema_id TEXT PRIMARY KEY,
            row_json TEXT NOT NULL
        ) WITHOUT ROWID;
        CREATE TABLE records (
            identity_key TEXT PRIMARY KEY,
            record_type TEXT NOT NULL,
            serialized_file TEXT NOT NULL COLLATE BINARY,
            source TEXT NOT NULL COLLATE BINARY,
            source_offset INTEGER NOT NULL,
            path_id INTEGER NOT NULL,
            schema_id TEXT,
            row_json TEXT NOT NULL
        ) WITHOUT ROWID;
        CREATE INDEX records_external_lookup
            ON records(serialized_file COLLATE BINARY, path_id);
        CREATE TABLE runtime_observations (
            owner_key TEXT NOT NULL,
            edge_index INTEGER NOT NULL,
            target_key TEXT NOT NULL,
            target_json TEXT NOT NULL,
            PRIMARY KEY(owner_key, edge_index, target_key)
        ) WITHOUT ROWID;
        """
    )
    return connection


def _insert_exact(
    connection: sqlite3.Connection,
    table: str,
    key_column: str,
    key: str,
    row_json: str,
    extra: tuple[Any, ...] = (),
) -> bool:
    found = connection.execute(
        f"SELECT row_json FROM {table} WHERE {key_column} = ?", (key,)
    ).fetchone()
    if found is not None:
        if found[0] != row_json:
            raise MergeError(f"conflicting duplicate {table} key {key}")
        return False
    if table == "schemas":
        connection.execute(
            "INSERT INTO schemas(schema_id, row_json) VALUES (?, ?)", (key, row_json)
        )
    elif table == "records":
        connection.execute(
            """INSERT INTO records(
                   identity_key, record_type, serialized_file, source,
                   source_offset, path_id, schema_id, row_json
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (key, *extra, row_json),
        )
    else:  # pragma: no cover - internal programming error
        raise AssertionError(table)
    return True


def normalize_object_row(
    row: dict[str, Any],
    owner_key: str,
) -> tuple[dict[str, Any], list[tuple[int, str, str]]]:
    normalized = copy.deepcopy(row)
    pptrs = normalized.get("pptrs")
    scalars = normalized.get("scalars")
    if not isinstance(pptrs, list) or not isinstance(scalars, list):
        raise MergeError(f"object {owner_key}: scalars and pptrs must be arrays")
    observations: list[tuple[int, str, str]] = []
    for edge_index, pptr in enumerate(pptrs):
        if not isinstance(pptr, dict):
            raise MergeError(f"object {owner_key}: PPtr {edge_index} is not an object")
        file_id = require_int(pptr.get("fileId"), f"object {owner_key}: PPtr fileId")
        require_int(pptr.get("pathId"), f"object {owner_key}: PPtr pathId")
        if file_id <= 0:
            continue

        # Runtime PPtr<T>.TryGet can select the first loaded external filename.
        # Preserve that as a diagnostic observation, then remove it from the
        # invariant duplicate body and recompute the final edge globally.
        target = pptr.pop("target", None)
        if target is not None:
            target_key = target_identity_key(target, f"object {owner_key}: runtime target")
            observations.append((edge_index, target_key, canonical_json(target)))
        pptr.pop("resolutionBasis", None)
        pptr["status"] = "__pending_external__"
    return normalized, observations


def validate_summary_counts(
    part_name: str,
    summary: dict[str, Any],
    actual: Counter[str],
) -> None:
    if summary.get("complete") is not True:
        raise MergeError(f"{part_name}: part summary is not complete")
    errors = summary.get("errors")
    if errors not in (None, []):
        raise MergeError(f"{part_name}: complete part summary contains errors")
    counts = summary.get("counts")
    if not isinstance(counts, dict):
        raise MergeError(f"{part_name}: summary counts are missing")
    for key in COUNT_KEYS:
        reported = require_int(counts.get(key), f"{part_name}: summary.counts.{key}")
        if reported != actual[key]:
            raise MergeError(
                f"{part_name}: summary count mismatch for {key}: "
                f"reported {reported}, parsed {actual[key]}"
            )


def ingest_part(
    connection: sqlite3.Connection,
    part: Path,
    unique_counts: Counter[str],
) -> dict[str, Any]:
    if not part.is_file():
        raise MergeError(f"missing expected part: {part}")
    actual: Counter[str] = Counter()
    summary: dict[str, Any] | None = None
    nonblank_lines = 0
    with part.open("r", encoding="utf-8", newline="") as stream:
        for line_number, line in enumerate(stream, 1):
            text = line.rstrip("\r\n")
            if not text:
                continue
            nonblank_lines += 1
            if summary is not None:
                raise MergeError(f"{part.name}:{line_number}: record after terminal summary")
            row = parse_json(text, f"{part.name}:{line_number}")
            if not isinstance(row, dict):
                raise MergeError(f"{part.name}:{line_number}: row is not an object")
            if row.get("schemaVersion") != PART_SCHEMA_VERSION:
                raise MergeError(f"{part.name}:{line_number}: unsupported schemaVersion")
            record_type = row.get("recordType")

            if record_type == "summary":
                summary = row
                continue

            if record_type == "schema":
                schema_id = row.get("schemaId")
                fields = row.get("fields")
                if not isinstance(schema_id, str) or not isinstance(fields, list) or not all(
                    isinstance(field, str) for field in fields
                ):
                    raise MergeError(f"{part.name}:{line_number}: malformed schema row")
                if schema_digest(fields) != schema_id:
                    raise MergeError(f"{part.name}:{line_number}: schemaId hash mismatch")
                inserted = _insert_exact(
                    connection, "schemas", "schema_id", schema_id, canonical_json(row)
                )
                actual["schemas"] += 1
                unique_counts["schemas"] += int(inserted)
                continue

            if record_type not in {"object", "monoScript"}:
                raise MergeError(f"{part.name}:{line_number}: unknown recordType {record_type!r}")
            identity = row.get("object")
            serialized_file, source, source_offset, path_id = validate_identity(
                identity, f"{part.name}:{line_number}"
            )
            owner_key = identity_key(identity)
            observations: list[tuple[int, str, str]] = []
            stored_row = row
            if record_type == "object":
                stored_row, observations = normalize_object_row(row, owner_key)
                actual["objects"] += 1
                actual["scalars"] += len(row["scalars"])
                actual["pptrs"] += len(row["pptrs"])
                actual["objectsWithTruncatedScalars"] += int(
                    row.get("scalarsTruncated") is True
                )
            else:
                for key in ("className", "namespace", "assemblyName"):
                    if not isinstance(row.get(key), str):
                        raise MergeError(
                            f"{part.name}:{line_number}: monoScript.{key} must be a string"
                        )
                actual["monoScripts"] += 1

            schema_id = stored_row.get("schemaId") if record_type == "object" else None
            if schema_id is not None and not isinstance(schema_id, str):
                raise MergeError(f"{part.name}:{line_number}: schemaId must be a string or null")
            inserted = _insert_exact(
                connection,
                "records",
                "identity_key",
                owner_key,
                canonical_json(stored_row),
                (record_type, serialized_file, source, source_offset, path_id, schema_id),
            )
            unique_counts[record_type] += int(inserted)
            for edge_index, target_key, target_json in observations:
                connection.execute(
                    """INSERT OR IGNORE INTO runtime_observations(
                           owner_key, edge_index, target_key, target_json
                       ) VALUES (?, ?, ?, ?)""",
                    (owner_key, edge_index, target_key, target_json),
                )

    if summary is None:
        raise MergeError(f"{part.name}: missing terminal summary")
    validate_summary_counts(part.name, summary, actual)
    return {
        "name": part.name,
        "sha256": sha256_file(part),
        "bytes": part.stat().st_size,
        "records": nonblank_lines,
        "counts": {key: actual[key] for key in COUNT_KEYS},
    }


def candidate_rows(
    connection: sqlite3.Connection,
    serialized_file: str,
    path_id: int,
) -> list[tuple[str, str, dict[str, Any]]]:
    cursor = connection.execute(
        """SELECT identity_key, record_type, row_json
           FROM records
           WHERE serialized_file = ? COLLATE BINARY AND path_id = ?
           ORDER BY source COLLATE BINARY, source_offset, identity_key COLLATE BINARY""",
        (serialized_file, path_id),
    )
    try:
        rows = cursor.fetchall()
    finally:
        cursor.close()
    return [(key, kind, parse_json(text, "stored candidate")) for key, kind, text in rows]


def target_from_candidate(kind: str, row: dict[str, Any]) -> dict[str, Any]:
    target = dict(row["object"])
    if kind == "monoScript":
        target.update({"type": "MonoScript", "name": row.get("className", "")})
    else:
        target.update({"type": row.get("type"), "name": row.get("name", "")})
    return target


def enrich_script_from_candidate(
    row: dict[str, Any],
    candidate_kind: str,
    candidate: dict[str, Any],
    owner_key: str,
) -> None:
    if candidate_kind != "monoScript":
        raise MergeError(f"object {owner_key}: m_Script resolved to {candidate_kind}")
    namespace = candidate.get("namespace", "")
    class_name = candidate.get("className", "")
    assembly = candidate.get("assemblyName", "")
    full_name = f"{namespace}.{class_name}" if namespace else class_name
    script = row.setdefault("script", {})
    if not isinstance(script, dict):
        raise MergeError(f"object {owner_key}: script field is not an object")
    for key, recovered in (("fullName", full_name), ("assembly", assembly)):
        existing = script.get(key)
        if existing not in (None, "", recovered):
            raise MergeError(
                f"object {owner_key}: existing script {key} conflicts with MonoScript"
            )
        script[key] = recovered


def resolve_object_row(
    connection: sqlite3.Connection,
    owner_key: str,
    row: dict[str, Any],
    resolution_counts: Counter[str],
    candidate_lookup: Callable[[str, int], list[tuple[str, str, dict[str, Any]]]],
) -> dict[str, Any]:
    observations_by_edge: dict[int, set[str]] = {}
    observation_cursor = connection.execute(
        """SELECT edge_index, target_key FROM runtime_observations
           WHERE owner_key = ?
           ORDER BY edge_index, target_key COLLATE BINARY""",
        (owner_key,),
    )
    try:
        for edge_index, target_key in observation_cursor:
            observations_by_edge.setdefault(edge_index, set()).add(target_key)
    finally:
        observation_cursor.close()
    for edge_index, pptr in enumerate(row.get("pptrs", [])):
        file_id = pptr.get("fileId")
        if not isinstance(file_id, int) or isinstance(file_id, bool) or file_id <= 0:
            continue
        expected = pptr.get("expected")
        serialized_file = expected.get("serializedFile") if isinstance(expected, dict) else None
        if not isinstance(serialized_file, str) or not serialized_file:
            pptr.pop("target", None)
            pptr.pop("resolutionBasis", None)
            if pptr.get("status") == "__pending_external__":
                pptr["status"] = "external_not_exported"
            resolution_counts[pptr["status"]] += 1
            continue

        path_id = require_int(pptr.get("pathId"), f"object {owner_key}: PPtr pathId")
        candidates = candidate_lookup(serialized_file, path_id)
        observed_keys = observations_by_edge.get(edge_index, set())

        if len(candidates) == 1:
            candidate_key, candidate_kind, candidate = candidates[0]
            if observed_keys and observed_keys != {candidate_key}:
                raise MergeError(
                    f"object {owner_key}: runtime external target conflicts with the "
                    "unique global candidate"
                )
            pptr["status"] = MERGED_RESOLUTION_STATUS
            pptr["target"] = target_from_candidate(candidate_kind, candidate)
            pptr["resolutionBasis"] = MERGED_RESOLUTION_BASIS
            resolution_counts["resolved"] += 1
            if pptr.get("path") == "$.m_Script":
                enrich_script_from_candidate(row, candidate_kind, candidate, owner_key)
        elif not candidates:
            pptr["status"] = "external_not_exported"
            pptr.pop("target", None)
            pptr.pop("resolutionBasis", None)
            resolution_counts["notExported"] += 1
            resolution_counts["runtimeObservationsDemoted"] += len(observed_keys)
        else:
            pptr["status"] = "ambiguous_external"
            pptr.pop("target", None)
            pptr.pop("resolutionBasis", None)
            resolution_counts["ambiguous"] += 1
            resolution_counts["runtimeObservationsDemoted"] += len(observed_keys)
    return row


def _write_deterministic_gzip(path: Path, lines: Iterable[str]) -> dict[str, Any]:
    temporary = path.with_name(path.name + ".tmp")
    if temporary.exists():
        temporary.unlink()
    iterator = iter(lines)
    try:
        with temporary.open("wb") as raw:
            with gzip.GzipFile(
                filename="", mode="wb", compresslevel=9, fileobj=raw, mtime=0
            ) as compressed:
                for line in iterator:
                    compressed.write(line.encode("utf-8"))
                    compressed.write(b"\n")
            raw.flush()
            os.fsync(raw.fileno())
    finally:
        close = getattr(iterator, "close", None)
        if close is not None:
            close()
    result = {
        "path": path.name,
        "sha256": sha256_file(temporary),
        "bytes": temporary.stat().st_size,
    }
    return {"temporary": temporary, "result": result}


def merge_parts(
    parts: list[Path],
    output_dir: Path,
    stage_signature: Any | None = None,
    *,
    keep_work_db: bool = False,
) -> dict[str, Any]:
    if not parts:
        raise MergeError("at least one expected part is required")
    output_dir.mkdir(parents=True, exist_ok=True)
    ordered_parts = sorted((part.resolve() for part in parts), key=lambda path: path.name)
    part_names = [part.name for part in ordered_parts]
    if len(set(part_names)) != len(part_names):
        raise MergeError("expected part basenames must be unique")

    database_path = output_dir / ".merge.sqlite3.tmp"
    connection = connect_database(database_path)
    unique_counts: Counter[str] = Counter()
    part_summaries: list[dict[str, Any]] = []
    try:
        for part in ordered_parts:
            part_summaries.append(ingest_part(connection, part, unique_counts))
            connection.commit()

        missing_schemas = connection.execute(
            """SELECT COUNT(*) FROM records r
               WHERE r.record_type = 'object'
                 AND r.schema_id IS NOT NULL
                 AND NOT EXISTS (
                     SELECT 1 FROM schemas s
                     WHERE s.schema_id = r.schema_id
                 )"""
        ).fetchone()[0]
        if missing_schemas:
            raise MergeError(f"{missing_schemas} object record(s) reference missing schemas")

        resolution_counts: Counter[str] = Counter()

        @lru_cache(maxsize=65_536)
        def cached_candidates(
            serialized_file: str, path_id: int
        ) -> tuple[tuple[str, str, dict[str, Any]], ...]:
            return tuple(candidate_rows(connection, serialized_file, path_id))

        def object_lines() -> Iterable[str]:
            cursor = connection.execute(
                """SELECT identity_key, record_type, row_json
                   FROM records
                   ORDER BY serialized_file COLLATE BINARY, source COLLATE BINARY,
                            source_offset, path_id, record_type COLLATE BINARY"""
            )
            try:
                for owner_key, record_type, row_text in cursor:
                    row = parse_json(row_text, "stored record")
                    if record_type == "object":
                        row = resolve_object_row(
                            connection,
                            owner_key,
                            row,
                            resolution_counts,
                            lambda serialized_file, path_id: list(
                                cached_candidates(serialized_file, path_id)
                            ),
                        )
                    yield canonical_json(row)
            finally:
                cursor.close()

        def schema_lines() -> Iterable[str]:
            cursor = connection.execute(
                "SELECT row_json FROM schemas ORDER BY schema_id COLLATE BINARY"
            )
            try:
                for (row_text,) in cursor:
                    yield row_text
            finally:
                cursor.close()

        objects_out = output_dir / "objects.jsonl.gz"
        schemas_out = output_dir / "schemas.jsonl.gz"
        objects_write = _write_deterministic_gzip(objects_out, object_lines())
        schemas_write = _write_deterministic_gzip(schemas_out, schema_lines())
        summary = {
            "schemaVersion": PART_SCHEMA_VERSION,
            "mergeContract": MERGE_CONTRACT,
            "complete": True,
            "stageSignature": stage_signature,
            "inputParts": part_summaries,
            "counts": {
                "objects": unique_counts["object"],
                "monoScripts": unique_counts["monoScript"],
                "schemas": unique_counts["schemas"],
                "duplicateRowsRemoved": sum(
                    sum(part["counts"][key] for part in part_summaries)
                    for key in ("objects", "monoScripts", "schemas")
                )
                - unique_counts["object"]
                - unique_counts["monoScript"]
                - unique_counts["schemas"],
            },
            "externalResolutions": dict(sorted(resolution_counts.items())),
            "outputs": {
                "objects": objects_write["result"],
                "schemas": schemas_write["result"],
            },
            "errors": [],
        }
        summary_text = canonical_json(summary) + "\n"
        summary_out = output_dir / "summary.json"
        summary_tmp = summary_out.with_name(summary_out.name + ".tmp")
        summary_tmp.write_text(summary_text, encoding="utf-8", newline="\n")

        # summary.json is the commit marker. Consumers verify its two hashes;
        # replacing it last prevents a partial publication from looking valid.
        os.replace(objects_write["temporary"], objects_out)
        os.replace(schemas_write["temporary"], schemas_out)
        os.replace(summary_tmp, summary_out)
        return summary
    finally:
        connection.close()
        if not keep_work_db and database_path.exists():
            database_path.unlink()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("parts", nargs="+", type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument(
        "--stage-signature-json",
        help="Optional canonical stage-signature JSON embedded in summary.json.",
    )
    parser.add_argument("--keep-work-db", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    signature = (
        parse_json(args.stage_signature_json, "--stage-signature-json")
        if args.stage_signature_json
        else None
    )
    try:
        summary = merge_parts(
            args.parts,
            args.output_dir,
            signature,
            keep_work_db=args.keep_work_db,
        )
    except MergeError as exc:
        raise SystemExit(f"object-index merge failed: {exc}") from exc
    print(canonical_json(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
