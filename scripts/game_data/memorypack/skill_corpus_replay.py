"""Authenticated selection-only replay of a complete unselected SkillData basis.

The source report is explicitly SHA-256 pinned and must still describe the
current parser, native inputs, catalog, CLI and selected physical chunks. Its
stored framing is reused only after every identity joins the complete current
ledger. This never streams or decrypts bytes and never creates a capture.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

from scripts.common import canonical_json_sha256
from scripts.game_data.memorypack.corpus_gate import (
    HEX64, _fail, _fingerprint, _snapshot_pinned_files, verify_current_report_inputs,
)

IDENTITY_FIELDS = (
    "virtualPath", "blockTypeValue", "length", "logicalMd5", "logicalSha256",
    "physicalChunkPath", "physicalChunkSource", "metadataProvenance", "overlayState",
    "chunkOverlayState", "physicalOffset", "encrypted",
)
SELECTION_FIELDS = ("cursorVerification", "captureTargetVerification", "captureTargetSetVerification")


def skill_identity_set_sha256(rows: list[Mapping[str, Any]]) -> str:
    return canonical_json_sha256([{key: row[key] for key in IDENTITY_FIELDS} for row in rows])


def _live_snapshot(report: Mapping[str, Any], timeline_contract_paths: list[Path]) -> dict[str, Any]:
    checked = verify_current_report_inputs(report, label="SkillData selection-replay basis")
    provenance = report["provenance"]
    recorded = provenance.get("timelinePlayAnimationContracts")
    if not isinstance(recorded, list) or not all(isinstance(row, Mapping) for row in recorded):
        _fail("skill-replay-contract-pins-missing", source="source corpus provenance",
              expected="timeline contract fingerprint list", actual=type(recorded).__name__)
    contracts = _snapshot_pinned_files(recorded, label="source corpus timeline contracts")
    recorded_paths = sorted(str(Path(row["path"]).resolve()) for row in recorded)
    current_paths = sorted(str(path.resolve()) for path in timeline_contract_paths)
    if recorded_paths != current_paths:
        _fail("skill-replay-contract-set-drift", source="source corpus timeline contracts",
              expected=current_paths, actual=recorded_paths)
    return {"inputs": checked, "timelineContracts": contracts}


def load_selection_replay_basis(
    *, source_path: Path, expected_source_sha256: str,
    ledger_rows: list[Mapping[str, Any]], expected_input_set_sha256: str,
    current_provenance: Mapping[str, Any], timeline_contract_paths: list[Path],
) -> dict[str, Any]:
    expected = str(expected_source_sha256).upper()
    if not HEX64.fullmatch(expected):
        _fail("skill-replay-source-hash-invalid", source=str(source_path),
              expected="explicit 64-hex SHA-256", actual=expected_source_sha256)
    source_pin = _fingerprint(source_path)
    if source_pin["sha256"] != expected:
        _fail("skill-replay-source-hash-mismatch", source=str(source_path),
              expected=expected, actual=source_pin["sha256"])
    try:
        report = json.loads(source_path.read_bytes())
    except (OSError, ValueError) as exc:
        _fail("skill-replay-source-readable", source=str(source_path),
              expected="complete current SkillData report", actual=str(exc)[:240])
    if (not isinstance(report, dict)
            or report.get("format") != "animestudio-skilldata-current-vfs-corpus"
            or type(report.get("schemaVersion")) is not int or report["schemaVersion"] != 1
            or report.get("status") != "complete" or report.get("publicationEligible") is not True
            or report.get("targetedVirtualPaths")):
        _fail("skill-replay-source-incomplete", source=str(source_path),
              expected="complete publication-eligible v1 SkillData corpus",
              actual={key: report.get(key) for key in ("format", "schemaVersion", "status", "publicationEligible")}
                     if isinstance(report, dict) else type(report).__name__)
    if report.get("inputSetSha256") != expected_input_set_sha256.upper():
        _fail("skill-replay-input-set-mismatch", source=str(source_path),
              expected=expected_input_set_sha256.upper(), actual=report.get("inputSetSha256"))
    provenance = report.get("provenance")
    if not isinstance(provenance, Mapping):
        _fail("skill-replay-provenance-missing", source=str(source_path), expected="provenance object")
    if any(provenance.get(field) is not None for field in SELECTION_FIELDS):
        _fail("skill-replay-source-already-selected", source=str(source_path),
              expected="all-unselected basis; replay supplied overlays independently",
              actual=[field for field in SELECTION_FIELDS if provenance.get(field) is not None])
    live_start = _live_snapshot(report, timeline_contract_paths)
    for role in ("outer", "ledger", "sourceFingerprints", "buildFingerprints", "blcPaths",
                 "corpusGate", "parser", "streamToolFingerprints", "selectedChunkFingerprints",
                 "selectedChunkResolution", "timelinePlayAnimationContracts"):
        if provenance.get(role) != current_provenance.get(role):
            _fail("skill-replay-current-provenance-mismatch", source=f"source corpus.{role}",
                  expected="the selected current input and parser closure", actual="receipt differs")
    rows = report.get("files")
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        _fail("skill-replay-files-invalid", source=str(source_path), expected="complete file list", actual=type(rows).__name__)
    expected_paths = [str(row["virtualPath"]) for row in ledger_rows]
    actual_paths = [row.get("virtualPath") for row in rows]
    if actual_paths != expected_paths:
        _fail("skill-replay-ledger-set-mismatch", source=str(source_path),
              expected={"files": len(expected_paths), "first": expected_paths[:3]},
              actual={"files": len(actual_paths), "first": actual_paths[:3]})
    framing_counts: Counter[str] = Counter()
    for row, ledger in zip(rows, ledger_rows):
        path = str(ledger["virtualPath"])
        for field in IDENTITY_FIELDS:
            if field == "logicalSha256":
                value = row.get(field)
                if not isinstance(value, str) or not HEX64.fullmatch(value):
                    _fail("skill-replay-logical-sha256-invalid", source=path, expected="uppercase SHA-256", actual=value)
                continue
            expected_value = ledger.get({"logicalMd5": "recomputedFileDataMd5", "physicalOffset": "offset"}.get(field, field))
            if row.get(field) != expected_value:
                _fail("skill-replay-ledger-identity-mismatch", source=f"{path}.{field}",
                      expected=expected_value, actual=row.get(field))
        if row.get("inputSetSha256") != expected_input_set_sha256.upper():
            _fail("skill-replay-row-input-set-mismatch", source=path,
                  expected=expected_input_set_sha256.upper(), actual=row.get("inputSetSha256"))
        if row.get("terminalSelection") is not None or row.get("wholeSchemaExact") is True:
            _fail("skill-replay-row-already-selected", source=path,
                  expected="unselected static framing row", actual=row.get("coverageStatus"))
        framing = row.get("framing")
        if not isinstance(framing, Mapping) or not isinstance(framing.get("status"), str):
            _fail("skill-replay-framing-missing", source=path, expected="recorded static framing status")
        framing_counts[framing["status"]] += 1
    identity_set = skill_identity_set_sha256(rows)
    if report.get("identitySetSha256") != identity_set:
        _fail("skill-replay-identity-set-mismatch", source=str(source_path),
              expected=report.get("identitySetSha256"), actual=identity_set)
    summary = report.get("summary")
    if not isinstance(summary, Mapping):
        _fail("skill-replay-summary-missing", source=str(source_path), expected="complete summary")
    for field, expected_value in (
        ("ledgerSkillFiles", len(rows)), ("filesSelected", len(rows)),
        ("filesSucceeded", len(rows)), ("filesFailed", 0),
        ("logicalBytes", sum(row["length"] for row in rows)),
        ("framingStatusCounts", dict(sorted(framing_counts.items()))),
        ("coverageStatusCounts", dict(sorted(Counter(row.get("coverageStatus", "failed-framing") for row in rows).items()))),
    ):
        if summary.get(field) != expected_value:
            _fail("skill-replay-summary-mismatch", source=f"{source_path}:{field}",
                  expected=expected_value, actual=summary.get(field))
    if _fingerprint(source_path) != source_pin:
        _fail("skill-replay-source-drift", source=str(source_path), expected=source_pin, actual=_fingerprint(source_path))
    return {"report": report, "sourcePin": source_pin, "liveStart": live_start,
            "rows": rows, "framingCounts": dict(sorted(framing_counts.items())),
            "identitySetSha256": identity_set, "timelineContractPaths": timeline_contract_paths}


def verify_selection_replay_basis(basis: Mapping[str, Any]) -> dict[str, Any]:
    source_pin = basis["sourcePin"]
    actual = _fingerprint(Path(source_pin["path"]))
    if actual != source_pin:
        _fail("skill-replay-source-drift", source=source_pin["path"], expected=source_pin, actual=actual)
    identity_set = skill_identity_set_sha256(basis["rows"])
    if identity_set != basis["identitySetSha256"]:
        _fail("skill-replay-row-identity-drift", source=source_pin["path"],
              expected=basis["identitySetSha256"], actual=identity_set)
    live_end = _live_snapshot(basis["report"], basis["timelineContractPaths"])
    if live_end != basis["liveStart"]:
        _fail("skill-replay-input-drift", source=source_pin["path"],
              expected="unchanged authenticated source inputs before and after selection", actual="inputs changed")
    return {"mode": "selection-only-complete-corpus-replay", "sourceCorpus": source_pin,
            "identitySetSha256": basis["identitySetSha256"], "currentInputsRechecked": True,
            "evidenceBoundary": "Reuses current authenticated stored framing; no new stream or runtime observation."}


def replay_protected_paths(basis: Mapping[str, Any]) -> list[Path]:
    paths = [Path(basis["sourcePin"]["path"])]
    for pins in basis["liveStart"]["inputs"].values():
        paths.extend(Path(pin["path"]) for pin in pins)
    paths.extend(Path(pin["path"]) for pin in basis["liveStart"]["timelineContracts"])
    return paths
