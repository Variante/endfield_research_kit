"""Authenticate saved JsonData source receipts against the selected installation.

This reuses the current-corpus fingerprint and catalog guards without importing
page builders or replaying other families' readers. Call it before and after
an operation and compare the returned snapshots. A source receipt does not
admit a schema, formatter, parent reader, or runtime observation.
"""
from __future__ import annotations

import gzip
import json
import os
from pathlib import Path
from typing import Any, Mapping

from scripts.game_data.memorypack.corpus_gate import (
    CensusGateError, HEX64, _discover_blc_paths, _expected_blc_paths,
    _fingerprint, _snapshot_pinned_files,
)

SCHEMA = "endfield.jsondata-current-source-receipt.v1"
REGISTRY_FORMAT = "endfield-jsondata-current-corpus-v1"


def _require(check: str, source: Any, expected: Any, actual: Any) -> None:
    if actual != expected:
        raise CensusGateError(check, source=str(source), expected=expected, actual=actual)


def _path_key(path: str | Path) -> str:
    return os.path.normcase(str(Path(path).resolve()))


def _pins(provenance: Mapping[str, Any], role: str) -> list[dict[str, Any]]:
    rows = provenance.get(role)
    if not isinstance(rows, list) or not rows or not all(isinstance(row, dict) for row in rows):
        raise CensusGateError("receipt-fingerprint-list", source=f"provenance.{role}",
                              expected="nonempty fingerprint list", actual=type(rows).__name__)
    return _snapshot_pinned_files(rows, label=f"provenance.{role}")


def authenticate_current_jsondata_receipt(
    *, summary_path: Path, ledger_path: Path, expected_summary_sha256: str,
    native_sources: Mapping[str, str], native_inputs: Mapping[str, str],
) -> dict[str, Any]:
    """Authenticate source/build pins and bind them to the selected native paths.

    The logical ledger and selected exported bytes are joined by the caller.
    The returned snapshot is stable only after a second successful check; it
    deliberately makes no use of another family's stored admission rows.
    """
    summary_pin = _fingerprint(summary_path)
    _require("summary-byte-join", summary_path, expected_summary_sha256.upper(), summary_pin["sha256"])
    summary = json.loads(summary_path.read_bytes())
    if not isinstance(summary, dict):
        raise CensusGateError("summary-object", source=str(summary_path), expected="object", actual=type(summary).__name__)
    _require("summary-format", summary_path, [REGISTRY_FORMAT, 1],
             [summary.get("format"), summary.get("schemaVersion")])
    _require("summary-status", summary_path, "complete", summary.get("status"))
    input_set = summary.get("inputSetSha256")
    if not isinstance(input_set, str) or not HEX64.fullmatch(input_set.upper()):
        raise CensusGateError("summary-input-set", source=str(summary_path), expected="SHA-256", actual=input_set)
    provenance = summary.get("provenance")
    if not isinstance(provenance, dict):
        raise CensusGateError("summary-provenance", source=str(summary_path), expected="object", actual=type(provenance).__name__)
    checked: dict[str, Any] = {"schema": SCHEMA, "summary": summary_pin, "inputSetSha256": input_set}
    for role in ("outer", "ledger", "registry"):
        pin = provenance.get(role)
        checked[role] = _snapshot_pinned_files([pin] if isinstance(pin, dict) else [],
                                              label=f"provenance.{role}")[0]
    for role in ("sourceFingerprints", "buildFingerprints"):
        checked[role] = _pins(provenance, role)
    output = provenance.get("outputFiles")
    checked["outputFiles"] = _snapshot_pinned_files(
        [{**output, "path": ledger_path.as_posix()}] if isinstance(output, dict) else [],
        label="provenance.outputFiles")[0]

    outer_path = Path(checked["outer"]["path"])
    outer = json.loads(outer_path.read_bytes())
    if not isinstance(outer, dict):
        raise CensusGateError("outer-object", source=str(outer_path), expected="object", actual=type(outer).__name__)
    _require("outer-format", outer_path, ["animestudio-vfs-boundary-audit", 1],
             [outer.get("format"), outer.get("schemaVersion")])
    outer_summary = outer.get("summary")
    publication = outer.get("publication")
    if not isinstance(outer_summary, dict) or not isinstance(publication, dict):
        raise CensusGateError("outer-summary-publication", source=str(outer_path),
                              expected="summary and publication objects", actual="missing or malformed")
    _require("outer-complete", outer_path, True, outer_summary.get("fullAuditPassed"))
    _require("outer-input-set", outer_path, input_set, outer.get("inputSetSha256"))
    _require("outer-ledger-publication", outer_path, checked["ledger"]["sha256"],
             str(publication.get("ledgerSha256", "")).upper())
    for role in ("sourceFingerprints", "buildFingerprints"):
        rows = outer.get(role)
        if not isinstance(rows, list) or not rows or not all(isinstance(row, dict) for row in rows):
            raise CensusGateError("outer-fingerprint-list", source=f"outer.{role}",
                                  expected="nonempty fingerprint list", actual=type(rows).__name__)
        # These paths and digests were already rechecked above; compare their
        # canonical declaration instead of hashing the same binaries twice.
        normalized = [{"path": Path(row["path"]).resolve().as_posix(), "length": row["length"],
                       "sha256": str(row["sha256"]).upper(), "role": row.get("role")} for row in rows]
        _require("outer-registry-fingerprints", f"outer.{role}", True, normalized == checked[role])
    with gzip.open(Path(checked["ledger"]["path"]), "rt", encoding="utf-8") as stream:
        header = json.loads(stream.readline())
    if not isinstance(header, dict):
        raise CensusGateError("outer-ledger-header", source=checked["ledger"]["path"],
                              expected="audit header object", actual=type(header).__name__)
    _require("outer-ledger-header", checked["ledger"]["path"], ["audit_header", 1, input_set],
             [header.get("recordType"), header.get("schemaVersion"), header.get("inputSetSha256")])
    for role in ("primaryAssets", "fallbackAssets", "sourceFingerprints", "buildFingerprints"):
        _require("outer-ledger-header-field", f"header.{role}", True, header.get(role) == outer.get(role))
    current_blcs = _discover_blc_paths(outer)
    for role, expected in (("registry", provenance.get("blcPaths")), ("outer", _expected_blc_paths(outer))):
        if not isinstance(expected, list) or not all(isinstance(path, str) for path in expected):
            raise CensusGateError("catalog-path-list", source=f"{role}.blcPaths",
                                  expected="catalog path list", actual=type(expected).__name__)
        if current_blcs != expected:
            raise CensusGateError("catalog-path-set", source=f"{role}.blcPaths",
                expected={"count": len(expected) if isinstance(expected, list) else None},
                actual={"count": len(current_blcs), "added": sorted(set(current_blcs) - set(expected or []))[:8],
                        "removed": sorted(set(expected or []) - set(current_blcs))[:8]})
    checked["blcPaths"] = current_blcs
    tools = [row for row in checked["buildFingerprints"] if Path(row["path"]).name.lower() == "animestudio.cli.exe"]
    _require("outer-cli-identity", "outer.buildFingerprints", 1, len(tools))
    selected = {}
    for name in ("GameAssembly.dll", "global-metadata.dat"):
        path = native_sources.get(name)
        digest = native_inputs.get(name)
        if not isinstance(path, str) or not path or not isinstance(digest, str) or not HEX64.fullmatch(digest.upper()):
            raise CensusGateError("selected-native-identity", source=name,
                                  expected="authenticated selected path and SHA-256", actual={"path": path, "sha256": digest})
        matches = [row for row in checked["buildFingerprints"] if _path_key(row["path"]) == _path_key(path)]
        _require("selected-native-path", name, 1, len(matches))
        _require("selected-native-build", path, digest.upper(), matches[0]["sha256"])
        selected[name] = matches[0]
    game_root = Path(selected["global-metadata.dat"]["path"]).parents[2]
    _require("selected-native-game-root", "GameAssembly.dll", _path_key(game_root.parent / "GameAssembly.dll"),
             _path_key(selected["GameAssembly.dll"]["path"]))
    for role, folder in (("primaryAssets", "Persistent"), ("fallbackAssets", "StreamingAssets")):
        _require("selected-assets-root", role, _path_key(game_root / folder), _path_key(outer[role]))
    checked["selectedNative"] = selected
    checked["evidenceBoundary"] = "current source/build receipt only; no schema, parent-reader or runtime admission"
    return checked
