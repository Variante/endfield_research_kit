"""Reuse complete current canonical LevelScript frames without a second decode.

The canonical source receipt alone cannot admit a saved reader result. Reuse
also requires the complete current reader input snapshot and a one-to-one
export/ledger byte join. Older or changed receipts fall back to the maintained
direct reader; their payloads are never partially merged into current output.
"""
from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any

from scripts.common import resolve_installed_native_inputs, sha256_file
from scripts.game_data.jsondata_source_provenance import authenticate_current_jsondata_receipt
from scripts.game_data.levelscript_reader_inputs import SCHEMA as READER_INPUT_SCHEMA, require_current_reader_inputs
from scripts.source_paths import ExportLayout
from scripts.webui.data_inspector.current_receipts import DEFAULT_LEDGER, DEFAULT_SUMMARY
from scripts.webui.data_inspector.levelscript_records import levelscript_record_from_detail
from scripts.webui.data_inspector.levelscript_native_inputs import selected_child_native_signature


def _require(ok: bool, check: str, source: str = "") -> None:
    if not ok:
        raise ValueError(f"levelscript-canonical-receipt:{check}:{source}")


def _source_pins(export_root: Path) -> dict[str, dict[str, Any]]:
    folder = ExportLayout(export_root).json_dir / "LevelScriptData"
    rows = {}
    for path in sorted(folder.rglob("*.json")):
        relative = path.relative_to(folder.parent).as_posix()
        key = relative.casefold()
        _require(key not in rows, "duplicate-export-path", relative)
        raw = path.read_bytes()
        rows[key] = {"path": relative, "length": len(raw), "sha256": hashlib.sha256(raw).hexdigest().upper()}
    return rows


def _load_rows(ledger_path: Path) -> dict[str, dict[str, Any]]:
    rows = {}
    with gzip.open(ledger_path, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            _require(isinstance(row, dict), "ledger-row-object")
            if row.get("family") != "LevelScriptData":
                continue
            relative = row.get("exportRelativePath")
            _require(isinstance(relative, str), "source-path-type")
            parts = PurePosixPath(relative).parts
            _require(len(parts) > 1 and parts[0] == "LevelScriptData" and all(p not in (".", "..", "") for p in parts)
                     and "\\" not in relative and ":" not in relative,
                     "unsafe-source-path", relative)
            _require(row.get("virtualPath") == "Data/Json/" + relative, "virtual-path-join", relative)
            key = relative.casefold()
            _require(key not in rows, "duplicate-ledger-path", relative)
            rows[key] = row
    _require(bool(rows), "empty-family")
    return rows


def load_current_levelscript_records(export_root: Path, *, summary_path: Path = DEFAULT_SUMMARY,
                                    ledger_path: Path = DEFAULT_LEDGER) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return only a complete authenticated projection; never a partial cache."""
    raw = summary_path.read_bytes()
    summary = json.loads(raw)
    _require(isinstance(summary, dict), "summary-object")
    provenance = summary.get("provenance", {})
    _require(isinstance(provenance, dict), "provenance-object")
    recorded = provenance.get("levelscriptReaderInputs")
    _require(isinstance(recorded, dict) and recorded.get("schema") == READER_INPUT_SCHEMA,
             "complete-reader-receipt-unavailable")
    reader_before = require_current_reader_inputs(recorded)
    layout = ExportLayout(export_root)
    _require(Path(summary.get("exportRoot", "")).resolve() == layout.json_dir.resolve(), "selected-export-root")
    gameassembly, metadata = resolve_installed_native_inputs()
    native_sources = {"GameAssembly.dll": str(gameassembly), "global-metadata.dat": str(metadata)}
    native_inputs = {name: sha256_file(Path(path)).upper() for name, path in native_sources.items()}
    child_native_before = selected_child_native_signature(native_inputs, gameassembly=gameassembly)
    _require(child_native_before["status"] == "validated", "child-native-inputs",
             json.dumps(child_native_before, ensure_ascii=False, separators=(",", ":")))
    args = {"summary_path": summary_path, "ledger_path": ledger_path,
            "expected_summary_sha256": hashlib.sha256(raw).hexdigest().upper(),
            "native_sources": native_sources, "native_inputs": native_inputs}
    before = authenticate_current_jsondata_receipt(**args)
    sources = _source_pins(export_root)
    rows = _load_rows(ledger_path)
    _require(set(rows) == set(sources), "one-to-one-source-path-set")
    family = summary.get("summary", {}).get("families", {}).get("LevelScriptData", {})
    _require(family.get("files") == len(rows), "family-count")
    records = []
    for key, source in sorted(sources.items()):
        row = rows[key]
        _require(row.get("exportRelativePath") == source["path"] and row.get("length") == source["length"]
                 and row.get("logicalSha256") == source["sha256"], "exported-source-byte-join", source["path"])
        detail = row.get("detail")
        _require(isinstance(detail, dict), "missing-reader-detail", source["path"])
        exact = detail.get("schemaStatus") == "named_exact"
        _require(row.get("status") == ("schema_decoded" if exact else "bounded_partial"), "reader-status-join", source["path"])
        _require(row.get("reader") == detail.get("reader") and isinstance(row.get("reader"), str)
                 and row["reader"].startswith("scripts.game_data.levelscript_binary."), "reader-identity", source["path"])
        if exact:
            _require(detail.get("bytesConsumed") == source["length"], "physical-eof", source["path"])
        records.append(levelscript_record_from_detail(layout.json_dir / source["path"], export_root, detail))
    _require(_source_pins(export_root) == sources, "exported-source-drift")
    _require(authenticate_current_jsondata_receipt(**args) == before, "source-receipt-drift")
    _require(require_current_reader_inputs(reader_before) == reader_before, "reader-input-drift")
    _require(selected_child_native_signature(None) == child_native_before,
             "child-native-input-drift")
    return records, {"status": "current-canonical-reader-reuse", "currentSourceReceipt": before,
                     "readerInputs": reader_before, "childNativeGate": child_native_before, "sourceCount": len(records),
                     "detailPolicy": "unchanged canonical reader detail; source locators inside refusals remain Json-relative"}


def try_current_levelscript_records(export_root: Path) -> tuple[list[dict[str, Any]] | None, dict[str, Any]]:
    try:
        return load_current_levelscript_records(export_root)
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as error:
        return None, {"status": "direct-reader-fallback", "reason": str(error)[:1000]}
