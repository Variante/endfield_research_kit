"""Authenticate every available JsonData source identity without classifying it.

The full VFS audit owns installed catalog and chunk boundaries. This producer
joins all available JsonData/JsonLip identities to one complete export, including
packed LipSync rows, and checks its inputs again before returning. It opens no
NativeImage and invokes no family decoder. Named schemas, owner EOF and runtime
effects require their independent consumers.
"""
from __future__ import annotations

if __name__ == '__main__' and __spec__ is None:
    raise SystemExit('Run from repository root: python -m scripts.game_data.jsondata_source_inventory')

import argparse
from collections import Counter
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile

from scripts.game_data.game_file_store import GameFileStore, iter_game_tree, loose_packed_files
from scripts.game_data.jsondata_blocks import JSON_BLOCKS, is_jsondata_identity
from scripts.game_data.jsondata_source_provenance import (
    SOURCE_INVENTORY_FORMAT, SOURCE_INVENTORY_SCHEMA, source_inventory_flags)
from scripts.game_data.memorypack.corpus_gate import (
    CensusGateError, _atomic_write_json, _chunk_fingerprints,
    _chunk_selection_snapshot, _discover_blc_paths, _fingerprint,
    _guard_output_path, _package_import_closure, _read_outer_and_ledger,
    _snapshot_pinned_files)
from scripts.repo_paths import REPO_ROOT
from scripts.source_paths import ExportLayout, game_relative_path

ROW_STATUS = "source-bytes-verified"


def _require(check, source, expected, actual):
    if actual != expected:
        raise CensusGateError(check, source=str(source), expected=expected, actual=actual)


def _digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(",", ":")).encode("utf-8")).hexdigest().upper()


def _producer_inputs():
    return [_fingerprint(path) for path in _package_import_closure(Path(__file__))]


def _selected_rows(rows, input_set):
    selected = []
    seen = set()
    for row in rows:
        if not is_jsondata_identity(row):
            continue
        # Missing optional language downloads are explicitly outside the
        # available identity set. A present failed/unverified file is never skipped.
        if row.get("boundaryStatus") in ("excluded_missing_voice", "excluded_missing_audio"):
            continue
        _require("inventory-current-file", row.get("virtualPath"),
            [input_set, "verified", "boundary_verified"],
            [row.get("inputSetSha256"), row.get("status"), row.get("boundaryStatus")])
        logical = row.get("virtualPath")
        if not isinstance(logical, str) or not logical.startswith("Data/Json/"):
            raise CensusGateError("inventory-logical-path", source=str(logical), expected="Data/Json relative file")
        relative = game_relative_path(logical).as_posix()
        if not relative.startswith("Json/") or relative.casefold() in seen:
            raise CensusGateError("inventory-duplicate-or-unsafe-path", source=logical)
        if type(row.get("length")) is not int or row["length"] < 0 or not re.fullmatch(
                r"[0-9A-Fa-f]{32}", str(row.get("recomputedFileDataMd5", ""))):
            raise CensusGateError("inventory-logical-identity", source=logical,
                expected="nonnegative length and full logical MD5")
        seen.add(relative.casefold())
        selected.append(row)
    if not selected:
        raise CensusGateError("inventory-empty-jsondata", source="current outer ledger")
    return sorted(selected, key=lambda row: row["virtualPath"])


def _excluded_chunk_absences(rows, outer):
    """Recheck missing optional JsonData chunks without reading their payloads."""
    selected = {}
    for row in rows:
        if not is_jsondata_identity(row) or row.get("boundaryStatus") not in (
                "excluded_missing_voice", "excluded_missing_audio"):
            continue
        _require("inventory-excluded-current-file", row.get("virtualPath"),
            [outer["inputSetSha256"], row["boundaryStatus"]],
            [row.get("inputSetSha256"), row.get("status")])
        directory, name = row.get("hashDirectory"), row.get("chunkFile")
        if (not isinstance(directory, str) or not re.fullmatch(r"[0-9A-Fa-f]{8}", directory)
                or not isinstance(name, str) or not re.fullmatch(r"[0-9A-Fa-f]{32}[.]chk", name)):
            raise CensusGateError("inventory-excluded-chunk-name", source=str(row.get("virtualPath")),
                expected="literal hash directory and chunk filename", actual=[directory, name])
        key = (directory, name)
        selected.setdefault(key, {"blockNames": set(), "files": 0})
        selected[key]["blockNames"].add(row["blockName"])
        selected[key]["files"] += 1
    result = []
    for (directory, name), declaration in sorted(selected.items()):
        candidates = []
        for role in ("primaryAssets", "fallbackAssets"):
            value = outer.get(role)
            if not isinstance(value, str) or not value:
                raise CensusGateError("inventory-excluded-assets-root", source=role,
                    expected="explicit selected assets root", actual=value)
            assets = Path(value).resolve()
            path = assets / "VFS" / directory / name
            try:
                observed = path.lstat()
            except FileNotFoundError:
                # Missing is the only admitted state. A non-directory parent,
                # access error or another I/O failure cannot establish absence.
                resolved = path.resolve()
                if not resolved.is_relative_to(assets) or resolved != path.absolute():
                    raise CensusGateError("inventory-excluded-chunk-path-alias", source=str(path),
                        expected=str(path.absolute()), actual=str(resolved))
            except OSError as error:
                raise CensusGateError("inventory-excluded-chunk-stat", source=str(path),
                    expected="proved absence", actual=f"{type(error).__name__}: {error}"[:500]) from error
            else:
                # lstat also observes dangling symlinks and directories. Neither
                # is a missing file, even when exists()/is_file() returns False.
                import stat
                kind = ("symlink" if stat.S_ISLNK(observed.st_mode) else
                        "directory" if stat.S_ISDIR(observed.st_mode) else
                        "file" if stat.S_ISREG(observed.st_mode) else "other")
                raise CensusGateError("inventory-excluded-chunk-appeared", source=str(path),
                    expected="absent in both selected assets roots", actual={"kind": kind})
            candidates.append({"role": role, "path": path.as_posix(), "absent": True})
        result.append({"hashDirectory": directory, "chunkFile": name,
            "blockNames": sorted(declaration["blockNames"]), "excludedFiles": declaration["files"],
            "candidates": candidates})
    return result


def _audit_chunks(ledger_path, selected):
    wanted = {os.path.normcase(str(Path(row["physicalChunkPath"]).resolve())) for row in selected}
    found = {}
    with gzip.open(ledger_path, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            if (row.get("recordType") != "chunk" or row.get("boundaryStatus") != "boundary_verified"
                    or JSON_BLOCKS.get(row.get("blockTypeValue")) != row.get("blockName")):
                continue
            key = os.path.normcase(str(Path(row["physicalChunkPath"]).resolve()))
            if key not in wanted:
                continue
            value = [row.get("actualPhysicalLength"), row.get("recomputedContentMd5")]
            if key in found:
                _require("inventory-conflicting-audit-chunk", key, found[key], value)
            found[key] = value
    _require("inventory-audit-chunk-set", ledger_path, sorted(wanted), sorted(found))
    return found


def _chunks(selected, outer, audited):
    selection = _chunk_selection_snapshot(selected, outer)
    fingerprints = _chunk_fingerprints(selected)
    for row in fingerprints:
        key = os.path.normcase(str(Path(row["path"]).resolve()))
        expected = audited[key]
        _require("inventory-audit-chunk-bytes", row["path"],
            [expected[0], str(expected[1]).upper()], [row["length"], row["rawMd5"]])
    return selection, fingerprints


def _export_rows(export_root, selected):
    layout = ExportLayout(export_root).require()
    _require("inventory-loose-packed-files", layout.root, {}, loose_packed_files(layout))
    # Reject resolved aliases before the shared store/loose walker can collapse
    # two logical names. The store itself is likewise one owned regular path.
    for path in (layout.json_dir, *layout.json_dir.rglob("*"), layout.game_file_store_path):
        if path.exists() and path.resolve() != path.absolute():
            raise CensusGateError("inventory-export-path-alias", source=str(path),
                expected=str(path.absolute()), actual=str(path.resolve()))
    storage_before = _storage(layout)
    store = GameFileStore(layout.game_file_store_path) if layout.game_file_store_path.is_file() else None
    try:
        result = _read_export(layout, selected, store)
    finally:
        if store is not None:
            store.close()
    _require("inventory-export-storage-drift", layout.root, storage_before, _storage(layout))
    return result


def _storage(layout):
    path = layout.game_file_store_path
    # A writable WAL would make the main SQLite file insufficient as a byte identity.
    for suffix in ("-wal", "-shm", "-journal"):
        sidecar = Path(str(path) + suffix)
        if sidecar.exists():
            raise CensusGateError("inventory-live-sqlite-sidecar", source=str(sidecar), expected="closed published store")
    return dict(path=path.as_posix(), present=path.is_file(),
        fingerprint=_fingerprint(path) if path.is_file() else None)


def _read_export(layout, selected, store):
    entries = list(iter_game_tree(layout.root, "Json", _store=store))
    actual = {}
    for entry in entries:
        key = entry.path.casefold()
        if key in actual:
            raise CensusGateError("inventory-duplicate-export-path", source=entry.path)
        actual[key] = entry
    expected = {game_relative_path(row["virtualPath"]).as_posix().casefold(): row for row in selected}
    if actual.keys() != expected.keys():
        missing = sorted(expected.keys() - actual.keys())
        extra = sorted(actual.keys() - expected.keys())
        raise CensusGateError("inventory-export-path-set", source=str(layout.json_dir),
            expected={"count": len(expected), "missing": missing[:8]},
            actual={"count": len(actual), "extra": extra[:8]})
    result = []
    for key in sorted(expected):
        row = expected[key]
        entry = actual[key]
        data = entry.read_bytes()
        md5 = hashlib.md5(data).hexdigest().upper()
        _require("inventory-export-byte-join", entry.path,
            [row["length"], row["recomputedFileDataMd5"].upper()], [len(data), md5])
        relative = game_relative_path(row["virtualPath"]).as_posix().removeprefix("Json/")
        result.append(dict(virtualPath=row["virtualPath"], exportRelativePath=relative,
            family=relative.split("/")[0], length=len(data), logicalMd5=md5,
            logicalSha256=hashlib.sha256(data).hexdigest().upper(), packed=entry.packed,
            status=ROW_STATUS, namedSchemaAdmitted=False))
    return result


def _summary(rows):
    families = Counter(row["family"] for row in rows)
    return dict(filesSelected=len(rows), filesJoined=len(rows),
        logicalBytes=sum(row["length"] for row in rows),
        familyCounts=dict(sorted(families.items())),
        packedFiles=sum(row["packed"] for row in rows), identitySetSha256=_digest(rows))


def _check_inputs(provenance, producer_inputs):
    for role in ("outer", "ledger"):
        _snapshot_pinned_files([provenance[role]], label=f"inventory.{role}")
    for role in ("sourceFingerprints", "buildFingerprints"):
        _snapshot_pinned_files(provenance[role], label=f"inventory.{role}")
    outer = json.loads(Path(provenance["outer"]["path"]).read_bytes())
    _require("inventory-catalog-path-drift", "installed catalogs", provenance["blcPaths"], _discover_blc_paths(outer))
    _require("inventory-producer-input-drift", __file__, producer_inputs, _producer_inputs())


def build_report(*, outer_path, ledger_path, export_root, expected_input_set_sha256):
    """Return a complete source report and rows only after full byte bookends."""
    producer_inputs = _producer_inputs()
    layout = ExportLayout(export_root).require()
    marker = layout.read_marker()
    layout_pin = _fingerprint(layout.layout_file)
    storage = _storage(layout)
    outer, _header, rows, provenance = _read_outer_and_ledger(Path(outer_path), Path(ledger_path),
        expected_input_set_sha256=expected_input_set_sha256)
    excluded_absences = _excluded_chunk_absences(rows, outer)
    selected = _selected_rows(rows, expected_input_set_sha256.upper())
    audited = _audit_chunks(ledger_path, selected)
    selection, chunks = _chunks(selected, outer, audited)
    result = _export_rows(layout.root, selected)
    _require("inventory-export-byte-drift", layout.json_dir, _digest(result),
             _digest(_export_rows(layout.root, selected)))
    _require("inventory-chunk-drift", "selected JsonData chunks", [selection, chunks],
             list(_chunks(selected, outer, audited)))
    _require("inventory-excluded-chunk-drift", "excluded JsonData chunks", excluded_absences,
             _excluded_chunk_absences(rows, outer))
    _require("inventory-layout-drift", layout.layout_file, marker, layout.read_marker())
    _require("inventory-layout-bytes-drift", layout.layout_file, layout_pin, _fingerprint(layout.layout_file))
    _require("inventory-export-storage-drift", layout.root, storage, _storage(layout))
    _check_inputs(provenance, producer_inputs)
    report = dict(format=SOURCE_INVENTORY_FORMAT, schema=SOURCE_INVENTORY_SCHEMA,
        schemaVersion=1, status="complete", inputSetSha256=expected_input_set_sha256.upper(),
        exportRoot=layout.root.as_posix(), jsonRoot=layout.json_dir.as_posix(),
        provenance={**provenance, "producer": _fingerprint(Path(__file__)),
            "producerInputs": producer_inputs, "layout": layout_pin,
            "exportStorage": storage,
            "selectedChunkResolution": selection, "selectedChunkFingerprints": chunks,
            "excludedChunkAbsences": excluded_absences},
        summary=_summary(result), **source_inventory_flags(),
        evidenceBoundary="Complete available JsonData source identities and exact exported bytes only; no named classification, native grammar, owner EOF, activation or playback admission.")
    return report, result


def verify_saved_inventory(summary, *, ledger_path):
    """Recompute all source facts; a saved report never supplies grammar."""
    provenance = summary["provenance"]
    producer_inputs = provenance.get("producerInputs")
    if not isinstance(producer_inputs, list):
        raise CensusGateError("inventory-producer-input-list", source="provenance.producerInputs")
    _snapshot_pinned_files(producer_inputs, label="source inventory producer inputs")
    old_paths = [row["path"] for row in producer_inputs]
    current_paths = [row["path"] for row in _producer_inputs()]
    if old_paths != current_paths:
        raise CensusGateError("inventory-producer-path-set", source=__file__,
            expected=dict(count=len(old_paths), removed=sorted(set(old_paths)-set(current_paths))[:8]),
            actual=dict(count=len(current_paths), added=sorted(set(current_paths)-set(old_paths))[:8]))
    fresh, fresh_rows = build_report(outer_path=Path(provenance["outer"]["path"]),
        ledger_path=Path(provenance["ledger"]["path"]), export_root=Path(summary["exportRoot"]),
        expected_input_set_sha256=summary["inputSetSha256"])
    _require("inventory-json-root", summary["exportRoot"], fresh["jsonRoot"], summary.get("jsonRoot"))
    expected_provenance = {key: value for key, value in provenance.items() if key != "outputFiles"}
    _require("inventory-source-provenance", "source inventory", fresh["provenance"], expected_provenance)
    _require("inventory-summary", "source inventory", fresh["summary"], summary.get("summary"))
    saved_rows = []
    with gzip.open(ledger_path, "rt", encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            try:
                saved_rows.append(json.loads(line))
            except ValueError as error:
                raise CensusGateError("inventory-ledger-json", source=str(ledger_path), offset=number,
                    expected="source inventory row", actual=str(error)[:300]) from error
    _require("inventory-ledger-full-byte-join", ledger_path, _digest(fresh_rows), _digest(saved_rows))
    return dict(identitySetSha256=fresh["summary"]["identitySetSha256"],
        filesJoined=len(fresh_rows), jsonRoot=fresh["jsonRoot"], sourceEntryExitPassed=True)


def _guard_outputs(outputs, protected):
    for index, output in enumerate(outputs):
        resolved = output.resolve()
        if not any(resolved.is_relative_to((REPO_ROOT / name).resolve()) for name in ("reports", "tmp", "scratch")):
            raise CensusGateError("inventory-output-generated-root", source=str(output),
                expected="reports/, tmp/ or scratch/")
        _guard_output_path(output, [*protected, *(path for n, path in enumerate(outputs) if n != index)])
        for other in outputs:
            if other != output and (resolved.is_relative_to(other.resolve()) or other.resolve().is_relative_to(resolved)):
                raise CensusGateError("inventory-nested-outputs", source=str(output), actual=str(other))


def _atomic_bytes(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("outer-summary", "outer-ledger", "export-root", "output-json", "output-files"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--expected-input-set-sha256", required=True)
    args = parser.parse_args(argv)
    failure = args.output_json.with_suffix(".validation.json")
    outputs = [args.output_json, args.output_files, failure]
    protected = [args.outer_summary, args.outer_ledger, args.export_root, REPO_ROOT / "scripts"]
    safe = False
    try:
        _guard_outputs(outputs, protected)
        # Add live installed/tool input identities before any failure report can write.
        outer = json.loads(args.outer_summary.read_bytes())
        # Installed roots remain protected even when an optional root does not
        # exist yet; the general guard only recognizes existing directories.
        for role in ("primaryAssets", "fallbackAssets"):
            assets = Path(outer[role]).resolve()
            for output in outputs:
                resolved = output.resolve()
                if resolved.is_relative_to(assets) or assets.is_relative_to(resolved):
                    raise CensusGateError("inventory-output-assets-overlap", source=str(output),
                        expected="outside and not an ancestor of selected assets roots", actual=str(assets))
        protected.extend(Path(outer[role]) for role in ("primaryAssets", "fallbackAssets"))
        protected.extend(Path(row["path"]) for role in ("sourceFingerprints", "buildFingerprints")
                         for row in outer.get(role, []))
        protected.extend(Path(row["physicalChunkPath"]) for row in outer.get("chunks", [])
                         if row.get("physicalChunkPath"))
        protected.extend(Path(row["path"]) for row in _producer_inputs())
        layout = ExportLayout(args.export_root)
        protected.extend(path for path in layout.json_dir.rglob("*") if path.is_file())
        protected.extend([layout.layout_file, layout.game_file_store_path])
        _guard_outputs(outputs, protected)
        safe = True
        report, rows = build_report(outer_path=args.outer_summary, ledger_path=args.outer_ledger,
            export_root=args.export_root, expected_input_set_sha256=args.expected_input_set_sha256)
        payload = gzip.compress(b"".join((json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
            for row in rows), mtime=0)
        report["provenance"]["outputFiles"] = dict(length=len(payload), sha256=hashlib.sha256(payload).hexdigest().upper())
        _guard_outputs(outputs, protected)
        _atomic_bytes(args.output_files, payload)
        _atomic_write_json(args.output_json, report)  # Final source receipt marker.
        _atomic_write_json(failure, dict(schema="endfield.jsondata-source-inventory-validation.v1",
            status="validated", inputSetSha256=report["inputSetSha256"], summary=report["summary"]))
    except (CensusGateError, OSError, ValueError, KeyError, TypeError) as error:
        diagnostic = getattr(error, "diagnostic", dict(code="source-inventory-run", source="jsondata_source_inventory",
            expected="complete authenticated current source identities", actual=f"{type(error).__name__}: {error}"[:600]))
        if safe:
            _atomic_write_json(failure, dict(schema="endfield.jsondata-source-inventory-validation.v1", status="failed", diagnostic=diagnostic))
        print(json.dumps(dict(status="failed", diagnostic=diagnostic)), file=sys.stderr)
        return 1
    print(json.dumps(dict(status=report["status"], summary=report["summary"], **source_inventory_flags())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
