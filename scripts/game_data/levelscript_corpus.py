"""Authenticate current LevelScript families independently of Buff/Skill receipts.

Run ``python -m scripts.game_data.levelscript_corpus --help``. This sweeps both
LevelScriptData and LevelScriptTemplateData from a complete VFS audit, joins
every source to its export, and uses the existing owning readers. Its separate
receipt does not replace the complete JsonData registry or publish WebUI data.
The complete raw-package reader snapshot remains mandatory before and after.
"""
from __future__ import annotations

if __name__ == "__main__" and not __package__:
    raise SystemExit("Run python -m scripts.game_data.levelscript_corpus")

import argparse
import base64
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any, Callable

from scripts.common import check_installed_native_inputs
from scripts.game_data.corpus_common import atomic_write_text
from scripts.game_data import levelscript_union_tags as union_tags
from scripts.game_data.codecs.levelscript.framing_common import bounded_diagnostic_rows
from scripts.game_data.game_file_store import iter_game_tree, read_game_file
from scripts.game_data.levelscript_binary import frame_levelscript_named
from scripts.game_data.levelscript_template_binary import frame_levelscript_template
from scripts.game_data.levelscript_reader_inputs import (
    complete_reader_input_paths, snapshot_complete_reader_inputs, reader_input_changes,
)
from scripts.game_data.levelscript_first_stop_census import (
    LAYOUT_CONTRACT_PATH, NATIVE_REFUSAL, TEMPLATE_RECORD, module_first_stop,
)
from scripts.game_data.memorypack.corpus_gate import (
    DEFAULT_OUTER, DEFAULT_LEDGER, DEFAULT_CLI, CensusGateError, _read_outer_and_ledger,
    _fingerprint, _guard_output_path, _snapshot_pinned_files,
    _chunk_selection_snapshot, _discover_blc_paths,
    _stream_tool_snapshot, family_rows,
)
from scripts.repo_paths import REPO_ROOT
from scripts.source_paths import ExportLayout

FORMAT = "endfield-levelscript-current-corpus-v1"
FAMILIES = ("LevelScriptData", "LevelScriptTemplateData")
DEFAULT_EXPORT = REPO_ROOT / "export_full"
DEFAULT_OUTPUT = REPO_ROOT / "reports/game_data/levelscript_current_latest.json"


def _fail(check: str, source: str | Path, expected: Any, actual: Any,
          **extra: Any) -> None:
    error = CensusGateError(check, source=str(source), expected=expected, actual=actual)
    error.diagnostic.update({"validator": "levelscript_corpus", "check": check, **extra})
    raise error


def _native_inputs(gameassembly: Path | None, metadata: Path | None) -> list[dict[str, Any]]:
    pins = union_tags.contract_native_inputs()
    hashes = (pins['gameAssemblySha256'],pins['metadataSha256'])
    if any(not re.fullmatch(r'[0-9A-Fa-f]{64}',value) for value in hashes):
        _fail('native-contract-inputs',union_tags.DEFAULT_CONTRACT,'two SHA-256 values',pins)
    selected = check_installed_native_inputs(*hashes, gameassembly=gameassembly, metadata=metadata)
    if selected.status != "validated":
        _native_refusal("native-inputs", selected, hashes, fallback=gameassembly or "selected native build")
    # Existing owning readers resolve their own effective native pair. Check
    # that pair too; an explicit copied build never bypasses their build gate.
    effective = check_installed_native_inputs(*hashes)
    if effective.status != "validated":
        _native_refusal("reader-native-inputs", effective, hashes, fallback="owning readers' effective native build")
    paths = {Path(path).resolve() for gate in (selected, effective)
             for path in (gate.gameassembly, gate.metadata)}
    return [_fingerprint(path) for path in sorted(paths)]


def _native_refusal(check: str, gate: Any, hashes: tuple[str, str], *, fallback: Any) -> None:
    measured = []
    for role, path_key, hash_key in (("gameAssembly", "gameassembly", "gameassembly_sha256"),
                                    ("metadata", "metadata", "metadata_sha256")):
        path = getattr(gate, path_key, None)
        digest = getattr(gate, hash_key, "")
        measured.append({"role": role, "path": str(path) if path is not None else None,
                         "sha256": digest.upper() if digest else None})
    _fail(check, getattr(gate, "gameassembly", None) or fallback, "validated", gate.status,
          detail=gate.detail, expectedNativeInputs={"gameAssemblySha256": hashes[0].upper(),
                                                   "metadataSha256": hashes[1].upper()},
          measuredNativeInputs=measured)


def _relative_path(virtual_path: str, family: str) -> str:
    prefix = "Data/Json/"
    relative = virtual_path.removeprefix(prefix)
    posix = PurePosixPath(relative)
    if (not virtual_path.startswith(prefix + family + "/") or "\\" in relative
            or ":" in relative or any(ord(c) < 32 for c in relative)
            or posix.is_absolute() or any(p in (".", "..") for p in relative.split("/"))
            or posix.as_posix() != relative or not relative.endswith(".json")):
        _fail("safe-export-path", virtual_path, "safe family-relative JSON path", relative)
    return relative


def _diagnostic_messages(value: Any) -> list[str]:
    """Read every nested diagnostic, including later refused owner profiles."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [message for child in value.values() for message in _diagnostic_messages(child)]
    if isinstance(value, (tuple, list)):
        return [message for child in value for message in _diagnostic_messages(child)]
    return []


def _require_format_refusal(messages: list[str], source: str) -> None:
    for message in messages:
        if NATIVE_REFUSAL.search(message):
            _fail("native-refusal", source, "authenticated stored reader", message[:1500])


def _first_stop(frame: dict[str, Any], family: str) -> str:
    action_reason = (frame.get("actionMap") or {}).get("unresolvedReason")
    module_stop = module_first_stop(frame)
    if action_reason:
        stop = str(action_reason)
    elif module_stop:
        stop = module_stop
    elif family == "LevelScriptTemplateData" and frame.get("diagnostics"):
        stop = str(frame["diagnostics"][0].get("detail", frame.get("stopField")))
    else:
        stop = str(frame.get("stopField") or frame.get("status"))
    if frame.get("taskDiagnostics") and not module_stop:
        task = frame["taskDiagnostics"][0]
        stop += ":" + str(task.get("gate", ""))
        if task.get("conditionUnionTag"):
            stop += ":" + str(task["conditionUnionTag"])
    stop = re.sub(r"offset=\d+", "offset=<n>", stop)
    return TEMPLATE_RECORD.sub(r"\1[<n>]", stop) if family == "LevelScriptTemplateData" else stop


def _classify(data: bytes, family: str, source: str) -> dict[str, Any]:
    reader = (frame_levelscript_named if family == "LevelScriptData"
              else frame_levelscript_template)
    owner = ("scripts.game_data.levelscript_binary.frame_levelscript_named" if family == "LevelScriptData"
             else "scripts.game_data.levelscript_template_binary.frame_levelscript_template")
    try:
        frame = reader(data, source=source) if family == "LevelScriptData" else reader(data)
    except ValueError as exc:
        diagnostic = str(exc)[:1500]
        details = getattr(exc, "diagnostics", [])
        _require_format_refusal([str(exc), *_diagnostic_messages(details)], source)
        return {"status": "unclassified_binary", "reader": None,
                "namedSchemaStatus": "unproved", "diagnostic": diagnostic,
                "diagnostics": bounded_diagnostic_rows(details)}
    messages = _diagnostic_messages([frame.get(key, []) for key in
        ("readerRefusals", "diagnostics", "taskDiagnostics", "stopDetail")])
    messages.append(str((frame.get("actionMap") or {}).get("unresolvedReason", "")))
    _require_format_refusal(messages, source)
    if frame.get("schemaStatus") == "named_exact":
        if type(frame.get("bytesConsumed")) is not int or frame["bytesConsumed"] != len(data):
            _fail("named-owner-eof", source, len(data), frame.get("bytesConsumed"))
        return {"status": "schema_decoded", "reader": frame.get("reader", owner),
                "namedSchemaStatus": "named_exact", "bytesConsumed": len(data),
                "storedOwnerStatus": frame.get("status")}
    return {"status": "bounded_partial", "reader": frame.get("reader", owner),
            "namedSchemaStatus": "partial", "storedOwnerStatus": frame.get("status"),
            "firstStop": _first_stop(frame, family),
            **({"stopDetail": frame["stopDetail"]} if module_first_stop(frame) else {}),
            "diagnostics": {key: bounded_diagnostic_rows(frame.get(key, [])) for key in
                            ("readerRefusals", "diagnostics", "taskDiagnostics")}}


def _require_export_identity(export_root: Path, rows: list[dict[str, Any]]) -> None:
    expected_paths = {"Json/" + row["exportRelativePath"] for row in rows}
    current_paths = {entry.path for family in FAMILIES
                     for entry in iter_game_tree(export_root, "Json/" + family)}
    if current_paths != expected_paths:
        _fail("export-path-set-drift", export_root,
              {"count": len(expected_paths), "missing": sorted(expected_paths-current_paths)[:8]},
              {"count": len(current_paths), "extra": sorted(current_paths-expected_paths)[:8]})
    for row in rows:
        data = read_game_file(export_root, "Json/" + row["exportRelativePath"])
        expected = {"length": row["length"], "sha256": row["logicalSha256"]}
        actual = {"length": len(data), "sha256": hashlib.sha256(data).hexdigest().upper()}
        if actual != expected:
            _fail("export-content-drift", row["exportRelativePath"], expected, actual)


def _read_vfs_sources(cli: Path, outer: dict[str, Any], selected: list[dict[str, Any]]) -> dict[str, bytes]:
    """Join a selected logical stream to the audit, without writing exports."""
    command = [str(cli.resolve()), "stream", "--streaming-assets", str(outer["primaryAssets"]),
               "--fallback-assets", str(outer["fallbackAssets"]), "--block-type", "json-data",
               "--verify-md5", "--file-regex",
               r"^Data/Json/(LevelScriptData|LevelScriptTemplateData)/[^\x00\\:]+[.]json$"]
    # These families are bounded by their complete ledger selection. Draining
    # both pipes together avoids a stderr/stdout deadlock during the read.
    process = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", check=False)
    if process.returncode != 0:
        _fail("stream-process", cli, 0,
              {"returnCode": process.returncode, "stderr": process.stderr[-3000:]})
    by_path = {row["virtualPath"]: row for row in selected}
    result = {}
    for ordinal, line in enumerate(process.stdout.splitlines(), 1):
        try:
            row = json.loads(line)
        except ValueError as exc:
            _fail("stream-json", f"stream line {ordinal}", "JSON object", str(exc)[:240])
        if not isinstance(row, dict):
            _fail("stream-row", f"stream line {ordinal}", "JSON object", type(row).__name__)
        path = row.get("fileName")
        if not isinstance(path, str) or path not in by_path or path in result:
            _fail("stream-identity", f"stream line {ordinal}", "unique selected virtual path", path)
        if row.get("blockType") != "JsonData" or row.get("blockTypeValue") != 19:
            _fail("stream-block", path, ["JsonData", 19], [row.get("blockType"), row.get("blockTypeValue")])
        try:
            data = base64.b64decode(row.get("dataBase64", ""), validate=True)
        except (ValueError, TypeError) as exc:
            _fail("stream-base64", path, "base64 logical bytes", str(exc)[:240])
        ledger = by_path[path]
        if type(row.get("length")) is not int or row["length"] != len(data) or len(data) != ledger["length"]:
            _fail("stream-length", path, ledger["length"], {"declared": row.get("length"), "actual": len(data)})
        md5 = hashlib.md5(data).hexdigest().upper()
        if md5 != ledger["recomputedFileDataMd5"].upper():
            _fail("stream-ledger-md5", path, ledger["recomputedFileDataMd5"], md5)
        result[path] = data
    if set(result) != set(by_path):
        _fail("stream-path-set", cli, len(by_path),
              {"files": len(result), "missing": sorted(set(by_path)-set(result))[:8]})
    terminal = re.findall(r"(?m)^Streamed ([0-9]+) files\s*$", process.stderr)
    if len(terminal) != 1 or int(terminal[0]) != len(result):
        _fail("stream-terminal-count", cli, len(result), terminal)
    return result


def build_report(*, outer_path: Path, ledger_path: Path, export_root: Path,
                 expected_input_set_sha256: str, gameassembly: Path | None = None,
                 metadata: Path | None = None, cli_path: Path = DEFAULT_CLI,
                 reader_snapshot: dict[str, Any] | None = None,
                 progress: Callable[[str], None] | None = None) -> dict[str, Any]:
    announce = progress or (lambda message: None)
    inputs_before = reader_snapshot if reader_snapshot is not None else snapshot_complete_reader_inputs()
    native = _native_inputs(gameassembly, metadata)
    announce("native inputs authenticated; reading complete VFS ledger")
    outer, _, ledger_rows, provenance = _read_outer_and_ledger(
        outer_path, ledger_path, expected_input_set_sha256=expected_input_set_sha256)
    tool = _stream_tool_snapshot(cli_path)
    recorded_build = {str(Path(row["path"]).resolve()).casefold(): row for row in provenance["buildFingerprints"]}
    selected_tool_key = str(cli_path.resolve()).casefold()
    if selected_tool_key not in recorded_build:
        _fail("stream-cli-build", cli_path, "CLI included in outer build fingerprints", tool[0])
    selected = []
    for family in FAMILIES:
        prefix = f"Data/Json/{family}/"
        selected.extend(family_rows(ledger_rows, expected_input=outer["inputSetSha256"],
            prefix=prefix, pattern=re.compile(re.escape(prefix) + r"[^\x00\\:]+\.json"),
            label=family))
    selected.sort(key=lambda row: row["virtualPath"])
    del ledger_rows
    relatives = {}
    seen = set()
    for source in selected:
        family = source["virtualPath"].split("/")[2]
        relative = _relative_path(source["virtualPath"], family)
        if relative.casefold() in seen:
            _fail("duplicate-export-identity", source["virtualPath"], "unique casefold path", relative)
        seen.add(relative.casefold())
        relatives[source["virtualPath"]] = relative
    expected_paths = {"Json/" + path for path in relatives.values()}
    exported = {entry.path for family in FAMILIES
                for entry in iter_game_tree(export_root, "Json/" + family)}
    if expected_paths != exported:
        _fail("complete-export-path-set", export_root,
              {"count": len(expected_paths), "missing": sorted(expected_paths-exported)[:8]},
              {"count": len(exported), "extra": sorted(exported-expected_paths)[:8]})
    resolution = _chunk_selection_snapshot(selected, outer)
    # Streaming SHA-256 pins the physical inputs without materializing an
    # entire VFS chunk. Logical MD5 joins below still authenticate each payload.
    announce(f"selected sources={len(selected)}; fingerprinting physical chunks={len(resolution)}")
    chunks = [_fingerprint(path) for path in sorted({Path(row["selectedPath"]).resolve() for row in resolution})]
    provenance.update({"nativeInputs": native, "selectedChunkResolution": resolution,
                       "selectedChunkFingerprints": chunks, "readerInputs": inputs_before,
                       "streamToolFingerprints": tool})
    announce("streaming selected logical VFS bytes; no export writes")
    current_vfs = _read_vfs_sources(cli_path, outer, selected)
    rows = []
    announce("decoding selected sources with owning readers")
    for ordinal, source in enumerate(selected, 1):
        relative = relatives[source["virtualPath"]]
        family = relative.split("/")[0]
        data = read_game_file(export_root, "Json/" + relative)
        digest = hashlib.sha256(data).hexdigest().upper()
        md5 = hashlib.md5(data).hexdigest().upper()
        if len(data) != source["length"] or md5 != source["recomputedFileDataMd5"].upper():
            _fail("export-byte-identity", relative,
                  {"length": source["length"], "md5": source["recomputedFileDataMd5"]},
                  {"length": len(data), "md5": md5, "sha256": digest})
        vfs_data = current_vfs.pop(source["virtualPath"])
        if data != vfs_data:
            _fail("export-vfs-byte-identity", relative,
                  {"length": len(vfs_data), "sha256": hashlib.sha256(vfs_data).hexdigest().upper()},
                  {"length": len(data), "sha256": digest})
        classification = _classify(data, family, relative)
        rows.append({"virtualPath": source["virtualPath"], "exportRelativePath": relative,
                     "family": family, "length": len(data), "logicalMd5": md5,
                     "logicalSha256": digest, **classification})
        if ordinal % 1000 == 0:
            announce(f"decoded sources={ordinal}/{len(selected)}; publication still pending")
    announce("rechecking physical, logical and complete reader inputs before publication")
    for role in ("outer", "ledger"):
        _snapshot_pinned_files([provenance[role]], label=role)
    for role in ("sourceFingerprints", "buildFingerprints", "selectedChunkFingerprints", "nativeInputs", "streamToolFingerprints"):
        _snapshot_pinned_files(provenance[role], label=role)
    if _discover_blc_paths(outer) != provenance["blcPaths"]:
        _fail("blc-path-set-drift", "VFS roots", provenance["blcPaths"], _discover_blc_paths(outer))
    if _chunk_selection_snapshot(selected, outer) != resolution:
        _fail("chunk-selection-drift", "VFS roots", resolution, "selection changed")
    _require_export_identity(export_root, rows)
    inputs_after = snapshot_complete_reader_inputs()
    if inputs_after != inputs_before:
        _fail("complete-reader-inputs-drift", "complete raw-package reader scope",
              "unchanged", reader_input_changes(inputs_before, inputs_after))
    return {"format": FORMAT, "schemaVersion": 1, "status": "complete",
            "inputSetSha256": outer["inputSetSha256"], "exportRoot": (export_root / "game/Json").resolve().as_posix(),
            "families": list(FAMILIES), "provenance": provenance, "rows": rows,
            "summary": {"filesSelected": len(rows), "filesJoined": len(rows), "families": {
                family: {"files": sum(row["family"] == family for row in rows),
                         **dict(Counter(row["status"] for row in rows if row["family"] == family))}
                for family in FAMILIES}},
            "evidenceBoundary": "Current complete LevelScript family identities joined to export bytes under authenticated native and complete reader-input gates. Named owners close only at physical EOF; partial and refused sources stay distinct. This receipt is not the complete JsonData registry, a WebUI publication, runtime execution or mission ordering."}


def _guard_output(output: Path, inputs: list[Path]) -> None:
    target = output.resolve()
    repo = REPO_ROOT.resolve()
    roots = [(repo / name).resolve() for name in ("reports", "scratch", "tmp")]
    if not any(root.is_relative_to(repo) and target != root and target.is_relative_to(root) for root in roots):
        _fail("output-root", target, "ignored report file", str(target))
    _guard_output_path(target, inputs)


def _require_provenance_unchanged(provenance: dict[str, Any], outer: dict[str, Any],
                                  selected: list[dict[str, Any]]) -> None:
    """Close the verification interval after all logical export reads."""
    for role in ("outer", "ledger"):
        _snapshot_pinned_files([provenance[role]], label=role)
    for role in ("sourceFingerprints", "buildFingerprints", "selectedChunkFingerprints",
                 "nativeInputs", "streamToolFingerprints"):
        _snapshot_pinned_files(provenance[role], label=role)
    current_blc = _discover_blc_paths(outer)
    if current_blc != provenance["blcPaths"]:
        _fail("family-receipt-blc-path-set-drift", "VFS roots", provenance["blcPaths"], current_blc)
    current_resolution = _chunk_selection_snapshot(selected, outer)
    if current_resolution != provenance["selectedChunkResolution"]:
        _fail("family-receipt-chunk-selection-drift", "VFS roots",
              provenance["selectedChunkResolution"], current_resolution)


def verify_family_receipt(receipt_path: Path, *, expected_sha256: str,
                          expected_input_set_sha256: str, export_root: Path) -> dict[str, Any]:
    """Authenticate a saved family receipt and every live input it names.

    The explicit artifact hash selects reviewed generated bytes. Re-enumerated
    complete reader inputs, current source/chunk selection and logical exports
    still decide freshness; no saved positive result bypasses those gates.
    """
    fingerprint = _fingerprint(receipt_path)
    if (not re.fullmatch(r"[0-9A-Fa-f]{64}", expected_sha256)
            or fingerprint["sha256"] != expected_sha256.upper()):
        _fail("family-receipt-sha256", receipt_path, expected_sha256.upper(), fingerprint["sha256"])
    report = json.loads(receipt_path.read_bytes())
    if not isinstance(report, dict):
        _fail("family-receipt-object", receipt_path, "JSON object", type(report).__name__)
    for field, expected in (("format", FORMAT), ("schemaVersion", 1), ("status", "complete"),
                            ("inputSetSha256", expected_input_set_sha256.upper()),
                            ("families", list(FAMILIES))):
        if report.get(field) != expected:
            _fail("family-receipt-" + field, receipt_path, expected, report.get(field))
    if report.get("exportRoot") != (export_root / "game/Json").resolve().as_posix():
        _fail("family-receipt-export-root", receipt_path,
              (export_root / "game/Json").resolve().as_posix(), report.get("exportRoot"))
    provenance = report.get("provenance")
    if not isinstance(provenance, dict):
        _fail("family-receipt-provenance", receipt_path, "object", type(provenance).__name__)
    current_readers = snapshot_complete_reader_inputs()
    if provenance.get("readerInputs") != current_readers:
        previous = provenance.get("readerInputs")
        describable = (isinstance(previous, dict) and isinstance(previous.get("files"), list)
                       and all(isinstance(row, dict) and isinstance(row.get("path"), str)
                               for row in previous["files"]))
        _fail("family-receipt-reader-inputs", receipt_path, "complete current reader inputs",
              reader_input_changes(previous, current_readers) if describable else "missing or malformed complete snapshot")
    _native_inputs(None, None)
    for role in ("outer", "ledger"):
        if not isinstance(provenance.get(role), dict):
            _fail("family-receipt-fingerprint", role, "file fingerprint", provenance.get(role))
        _snapshot_pinned_files([provenance.get(role)], label=role)
    for role in ("sourceFingerprints", "buildFingerprints", "selectedChunkFingerprints", "nativeInputs", "streamToolFingerprints"):
        if not isinstance(provenance.get(role), list) or not all(isinstance(row, dict) for row in provenance[role]):
            _fail("family-receipt-fingerprints", role, "list of file fingerprints", type(provenance.get(role)).__name__)
        _snapshot_pinned_files(provenance.get(role), label=role)
    outer, _, ledger_rows, current_provenance = _read_outer_and_ledger(
        Path(provenance["outer"]["path"]), Path(provenance["ledger"]["path"]),
        expected_input_set_sha256=expected_input_set_sha256)
    for role in ("outer", "ledger", "sourceFingerprints", "buildFingerprints", "blcPaths"):
        if provenance.get(role) != current_provenance[role]:
            _fail("family-receipt-source-provenance", role, current_provenance[role], provenance.get(role))
    selected = [row for family in FAMILIES for row in family_rows(ledger_rows,
        expected_input=outer["inputSetSha256"], prefix=f"Data/Json/{family}/",
        pattern=re.compile(re.escape(f"Data/Json/{family}/") + r"[^\x00\\:]+\.json"), label=family)]
    resolution = _chunk_selection_snapshot(selected, outer)
    if resolution != provenance.get("selectedChunkResolution"):
        _fail("family-receipt-chunk-selection", receipt_path, resolution, provenance.get("selectedChunkResolution"))
    expected_chunks = {Path(row["selectedPath"]).resolve() for row in resolution}
    recorded_chunks = {Path(row["path"]).resolve() for row in provenance["selectedChunkFingerprints"]}
    if expected_chunks != recorded_chunks:
        _fail("family-receipt-chunk-path-set", receipt_path,
              sorted(map(str, expected_chunks)), sorted(map(str, recorded_chunks)))
    rows = report.get("rows")
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        _fail("family-receipt-rows", receipt_path, "list of rows", type(rows).__name__)
    identities = {}
    for row in rows:
        family = row.get("family")
        if family not in FAMILIES:
            _fail("family-receipt-row-family", receipt_path, list(FAMILIES), family)
        relative = _relative_path(str(row.get("virtualPath", "")), family)
        if row.get("exportRelativePath") != relative or relative.casefold() in identities:
            _fail("family-receipt-row-path", receipt_path, "unique exact family identity", relative)
        identities[relative.casefold()] = row
        if (type(row.get("length")) is not int or row["length"] <= 0
                or not isinstance(row.get("logicalSha256"), str)
                or not re.fullmatch(r"[0-9A-F]{64}", row["logicalSha256"])):
            _fail("family-receipt-row-bytes", relative, "positive length and logical SHA-256",
                  {key: row.get(key) for key in ("length", "logicalSha256")})
        if row.get("status") not in ("schema_decoded", "bounded_partial", "unclassified_binary"):
            _fail("family-receipt-row-status", relative, "stored classification", row.get("status"))
        if row["status"] == "schema_decoded" and (
                row.get("namedSchemaStatus") != "named_exact" or type(row.get("bytesConsumed")) is not int
                or row["bytesConsumed"] != row.get("length")):
            _fail("family-receipt-row-eof", relative, "named physical EOF", row.get("bytesConsumed"))
    if len(rows) != len(selected):
        _fail("family-receipt-complete-rows", receipt_path, len(selected), len(rows))
    for source in selected:
        family = source["virtualPath"].split("/")[2]
        relative = _relative_path(source["virtualPath"], family)
        row = identities.get(relative.casefold(), {})
        for key, expected in (("virtualPath", source["virtualPath"]), ("length", source["length"]),
                              ("logicalMd5", source["recomputedFileDataMd5"].upper())):
            if row.get(key) != expected:
                _fail("family-receipt-row-identity", relative, {key: expected}, {key: row.get(key)})
    summary = {"filesSelected": len(rows), "filesJoined": len(rows), "families": {
        family: {"files": sum(row["family"] == family for row in rows),
                 **dict(Counter(row["status"] for row in rows if row["family"] == family))}
        for family in FAMILIES}}
    if report.get("summary") != summary:
        _fail("family-receipt-summary", receipt_path, summary, report.get("summary"))
    _require_export_identity(export_root, rows)
    _require_provenance_unchanged(provenance, outer, selected)
    _snapshot_pinned_files([fingerprint], label="family receipt")
    final_readers = snapshot_complete_reader_inputs()
    if current_readers != final_readers:
        _fail("family-receipt-reader-drift", receipt_path, "unchanged",
              reader_input_changes(current_readers, final_readers))
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outer-summary", type=Path, default=DEFAULT_OUTER)
    parser.add_argument("--outer-ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--export-root", type=Path, default=DEFAULT_EXPORT)
    parser.add_argument("--expected-input-set-sha256", required=True)
    parser.add_argument("--gameassembly", type=Path)
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--cli", type=Path, default=DEFAULT_CLI)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    safe = False
    try:
        protected = [args.outer_summary, args.outer_ledger, args.export_root, Path(__file__),
                     LAYOUT_CONTRACT_PATH, REPO_ROOT / "scripts", args.cli]
        protected.extend(args.cli.parent.glob("AnimeStudio*.dll"))
        protected.extend(path for path in (args.gameassembly, args.metadata) if path is not None)
        protected.extend(complete_reader_input_paths())
        # Discover input identities before allowing any failure companion write.
        # In particular, a file hardlink outside an input directory is an alias.
        outer = json.loads(args.outer_summary.read_bytes())
        for role in ("sourceFingerprints", "buildFingerprints"):
            protected.extend(Path(row["path"]) for row in outer.get(role, []))
        for root_key in ("primaryAssets", "fallbackAssets"):
            protected.extend(path for path in (Path(outer[root_key]) / "VFS").rglob("*") if path.is_file())
        for family in FAMILIES:
            protected.extend(args.export_root / "game" / entry.path
                             for entry in iter_game_tree(args.export_root, "Json/" + family)
                             if not entry.packed)
        protected.append(ExportLayout(args.export_root).game_file_store_path)
        for gate in (check_installed_native_inputs(gameassembly=args.gameassembly, metadata=args.metadata),
                     check_installed_native_inputs()):
            protected.extend(Path(path) for path in (gate.gameassembly, gate.metadata) if path)
        _guard_output(args.output, protected)
        _guard_output(args.output.with_suffix(".validation.json"), protected + [args.output])
        safe = True
        reader_snapshot = snapshot_complete_reader_inputs()
        report = build_report(outer_path=args.outer_summary, ledger_path=args.outer_ledger,
            export_root=args.export_root, expected_input_set_sha256=args.expected_input_set_sha256,
            gameassembly=args.gameassembly, metadata=args.metadata, cli_path=args.cli, reader_snapshot=reader_snapshot,
            progress=lambda message: print("levelscript_corpus:" + message, file=sys.stderr, flush=True))
        for role in ("sourceFingerprints", "buildFingerprints", "selectedChunkFingerprints", "nativeInputs", "streamToolFingerprints"):
            protected.extend(Path(row["path"]) for row in report["provenance"][role])
        _guard_output(args.output, protected)
        _guard_output(args.output.with_suffix(".validation.json"), protected + [args.output])
        encoded = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        _require_export_identity(args.export_root, report["rows"])
        provenance = report["provenance"]
        outer = json.loads(Path(provenance["outer"]["path"]).read_bytes())
        # One representative per recorded chunk suffices to re-resolve its
        # overlay; these rows certify physical selection, never logical files.
        chunk_rows = [{"virtualPath": "publication chunk " + row["chunkFile"],
                       "hashDirectory": Path(row["primaryPath"]).parent.name,
                       "chunkFile": Path(row["primaryPath"]).name,
                       "physicalChunkPath": row["selectedPath"], "physicalChunkSource": row["selectedRole"],
                       "physicalChunkRoot": outer["primaryAssets" if row["selectedRole"] == "primary" else "fallbackAssets"]}
                      for row in provenance["selectedChunkResolution"]]
        _require_provenance_unchanged(provenance, outer, chunk_rows)
        current = snapshot_complete_reader_inputs()
        if current != reader_snapshot:
            _fail("publication-reader-inputs-drift", "complete reader scope", "unchanged",
                  reader_input_changes(reader_snapshot, current))
        atomic_write_text(args.output, encoded)
        atomic_write_text(args.output.with_suffix(".validation.json"), json.dumps(
            {"format": FORMAT, "status": "validated", "inputSetSha256": report["inputSetSha256"],
             "diagnostic": None}, ensure_ascii=False, indent=2) + "\n")
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        diagnostic = dict(getattr(exc, "diagnostic", {"check": "input-readable", "source": "selected inputs", "actual": str(exc)[:1500]}))
        diagnostic.setdefault("validator", "levelscript_corpus")
        diagnostic.setdefault("check", diagnostic.get("code", "input-readable"))
        publication_refusal = None
        if safe:
            companion = args.output.with_suffix(".validation.json")
            try:
                # The scan can fail after its output aliases or reader path
                # set have changed. Initial permission to publish is not a
                # permission to replace a newly aliased input on failure.
                _guard_output(companion, protected + [args.output, *complete_reader_input_paths()])
                atomic_write_text(companion, json.dumps(
                    {"format": FORMAT, "status": "failed", "diagnostic": diagnostic}, ensure_ascii=False, indent=2) + "\n")
            except (OSError, ValueError, KeyError, RuntimeError) as output_exc:
                publication_refusal = dict(getattr(output_exc, "diagnostic", {
                    "check": "diagnostic-output-refused", "source": str(companion),
                    "expected": "safe writable diagnostic path", "actual": str(output_exc)[:1500]}))
                publication_refusal.setdefault("validator", "levelscript_corpus")
                publication_refusal.setdefault("check", publication_refusal.get("code", "diagnostic-output-refused"))
        print(json.dumps({"status": "failed", "diagnostic": diagnostic,
                          **({"diagnosticPublicationRefusal": publication_refusal} if publication_refusal else {})},
                         ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps({"status": "complete", "families": report["summary"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
