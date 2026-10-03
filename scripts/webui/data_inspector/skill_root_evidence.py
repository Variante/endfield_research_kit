"""Additive canonical Skill facts; derived values keep their own tier."""
from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from scripts.game_data.levelscript_reader_inputs import require_current_reader_inputs
from scripts.game_data.memorypack import skill_corpus
from scripts.game_data.memorypack.corpus_gate import _fingerprint, _parser_source_snapshots
from scripts.game_data.memorypack.skill_corpus_replay import _live_snapshot
from scripts.webui.data_inspector.current_receipts import (
    DEFAULT_LEDGER, DEFAULT_SUMMARY, select_current_family_report,
)

_SOURCE = re.compile(r"^SkillData/[^/\\:]+[.]json$")
_NATIVE_NAMES = {
    "GameAssembly.dll": "GameAssembly.dll", "gameassemblySha256": "GameAssembly.dll",
    "gameAssemblySha256": "GameAssembly.dll",
    "global-metadata.dat": "global-metadata.dat", "globalMetadataSha256": "global-metadata.dat",
    "metadataSha256": "global-metadata.dat",
    "UnityPlayer.dll": "UnityPlayer.dll", "unityplayerSha256": "UnityPlayer.dll",
}
_BOUNDARY = (
    "Authenticated canonical stored-root evidence. Complete stored framing and "
    "recursively named schema are separate claims; derived values retain their "
    "structuralOnly evidence tier. No runtime execution or provider selection is inferred."
)


def _require(ok: bool, check: str, source: str = "SkillData") -> None:
    if not ok:
        raise ValueError(f"skill-canonical-evidence:{check}:{source}")


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, "duplicate-json-key", key)
        result[key] = value
    return result


def read_report_header(path: Path, *, limit: int = 32 << 20, chunk_size: int = 64 << 10) -> dict[str, Any]:
    """Read bounded top-level values, stopping before the large files array.

    This is not report authentication: callers must first join the entire file
    to the canonical hash. The maintained writer emits files last. A reordered
    or incomplete header is refused instead of reading the corpus into memory.
    """
    def invalid_constant(name):
        raise ValueError(f"skill-canonical-evidence:non-json-number:{name}")

    decoder = json.JSONDecoder(object_pairs_hook=_unique_object, parse_constant=invalid_constant)
    result, buffer, loaded = {}, "", 0
    with path.open("r", encoding="utf-8") as stream:
        def fill() -> None:
            nonlocal buffer, loaded
            piece = stream.read(chunk_size)
            _require(bool(piece), "truncated-report-header", str(path))
            loaded += len(piece)
            _require(loaded <= limit, "report-header-limit", str(path))
            buffer += piece

        def whitespace() -> None:
            nonlocal buffer
            while not buffer.strip():
                fill()
            buffer = buffer.lstrip()

        def token(expected: str) -> None:
            nonlocal buffer
            whitespace()
            _require(buffer[0] == expected, "report-header-token", expected)
            buffer = buffer[1:]

        def value(delimiter: str):
            nonlocal buffer
            whitespace()
            while True:
                try:
                    decoded, end = decoder.raw_decode(buffer)
                    tail = buffer[end:].lstrip()
                    if not tail:
                        fill()
                        continue
                    if tail[0] != delimiter:
                        # raw_decode accepts a complete numeric prefix of an
                        # unfinished exponent. Wait for the lexical delimiter
                        # before accepting a top-level scalar split by a read.
                        if type(decoded) in (int, float) and not any(c in buffer for c in ",}:]"):
                            fill()
                            continue
                        _require(False, "report-header-value-delimiter", delimiter)
                    buffer = buffer[end:]
                    return decoded
                except json.JSONDecodeError:
                    fill()

        token("{")
        while True:
            name = value(":")
            _require(isinstance(name, str) and name not in result, "report-header-key", str(name))
            token(":")
            if name == "files":
                token("[")
                required = {"format", "schemaVersion", "status", "publicationEligible", "inputSetSha256",
                            "provenance", "summary", "identitySetSha256", "wholeSchemaExact", "evidenceBoundary"}
                _require(required <= result.keys(), "report-header-fields", str(path))
                return result
            result[name] = value(",")
            token(",")


def _current_family_inputs(header: dict[str, Any], selection: dict[str, Any]) -> dict[str, Any]:
    current = _live_snapshot(header, skill_corpus._timeline_contract_paths())
    parser = _parser_source_snapshots(Path(skill_corpus.__file__))
    _require(header["provenance"].get("parser") == parser, "parser-closure-drift")
    declared = {}

    def visit(value):
        if isinstance(value, dict):
            pins = value.get("nativeInputs")
            if isinstance(pins, dict):
                for name, digest in pins.items():
                    _require(name in _NATIVE_NAMES, "unknown-native-pin", name)
                    name = _NATIVE_NAMES[name]
                    _require(isinstance(digest, str) and re.fullmatch(r"[0-9A-Fa-f]{64}", digest) is not None,
                             "native-pin-shape", name)
                    _require(name not in declared or declared[name] == digest.upper(), "native-pin-conflict", name)
                    declared[name] = digest.upper()
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(header["provenance"])
    selected = dict(selection["currentSourceReceipt"]["selectedNative"])
    _require({"GameAssembly.dll", "global-metadata.dat"} <= declared.keys(), "native-pair-missing")
    if "UnityPlayer.dll" in declared:
        selected["UnityPlayer.dll"] = _fingerprint(Path(selected["GameAssembly.dll"]["path"]).parent / "UnityPlayer.dll")
    _require(declared.keys() <= selected.keys(), "unknown-native-input")
    for name, digest in declared.items():
        _require(selected[name]["sha256"].upper() == digest, "selected-native-mismatch", name)
    return {"family": current, "parser": parser, "selectedNative": selected}


def _source_pins(export_root: Path) -> dict[str, dict[str, Any]]:
    root = export_root / "game/Json"
    result = {}
    for path in sorted((root / "SkillData").rglob("*.json")):
        source = path.relative_to(root).as_posix()
        _require(_SOURCE.fullmatch(source) is not None and source.casefold() not in result, "export-source", source)
        raw = path.read_bytes()
        result[source.casefold()] = {"path": source, "length": len(raw), "sha256": hashlib.sha256(raw).hexdigest().upper()}
    _require(bool(result), "empty-export-family")
    return result


def _registry_rows(ledger_path: Path) -> dict[str, dict[str, Any]]:
    result = {}
    with gzip.open(ledger_path, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            _require(isinstance(row, dict), "ledger-row-object")
            if row.get("family") != "SkillData":
                continue
            source = row.get("exportRelativePath")
            _require(isinstance(source, str) and _SOURCE.fullmatch(source) is not None, "ledger-source", str(source))
            _require(row.get("virtualPath") == "Data/Json/" + source and source.casefold() not in result,
                     "ledger-path-join", source)
            result[source.casefold()] = row
    return result


def _project(row: dict[str, Any]) -> dict[str, Any]:
    """Consume the corrected classifier's explicit boundary, never infer it."""
    detail = row.get("detail")
    _require(isinstance(detail, dict), "canonical-detail", row["exportRelativePath"])
    _require(type(detail.get("storedFrameExact")) is bool
             and detail.get("namedSchemaStatus") == "unproved"
             and detail.get("wholeSchemaExact") is False,
             "corrected-schema-boundary-unavailable", row["exportRelativePath"])
    # Current family receipts contain no recursively named complete Skill root.
    # Future positive admission requires a versioned new classifier contract.
    _require(row.get("status") != "schema_decoded", "canonical-status-boundary", row["exportRelativePath"])
    _require(not detail["storedFrameExact"] or row.get("status") == "format_framed_anonymous",
             "stored-frame-status", row["exportRelativePath"])
    gap = detail.get("namedSchemaGap")
    _require(isinstance(gap, dict) and isinstance(gap.get("reason"), str) and bool(gap["reason"]),
             "named-schema-gap", row["exportRelativePath"])
    return {"canonicalStatus": row["status"], "storedFrameExact": detail["storedFrameExact"],
            "namedSchemaStatus": detail["namedSchemaStatus"], "namedSchemaGap": gap,
            "boundaryClass": detail.get("boundaryClass"), "coverageStatus": detail.get("coverageStatus"),
            "sourceSha256": row["logicalSha256"], "evidenceBoundary": _BOUNDARY}


def load_skill_root_evidence(export_root: Path, *, summary_path: Path = DEFAULT_SUMMARY,
                             ledger_path: Path = DEFAULT_LEDGER) -> tuple[dict[str, Any], dict[str, Any]]:
    summary = json.loads(summary_path.read_bytes())
    reader = require_current_reader_inputs(summary.get("provenance", {}).get("levelscriptReaderInputs"))
    path, selection = select_current_family_report("SkillData", export_root, summary_path=summary_path, ledger_path=ledger_path)
    header = read_report_header(path)
    pin = selection["familyReport"]
    _require(header.get("format") == pin.get("format")
             and header.get("identitySetSha256") == pin.get("identitySetSha256"), "family-header-pin-join")
    inputs = _current_family_inputs(header, selection)
    _require(header["inputSetSha256"] == selection["currentSourceReceipt"]["inputSetSha256"], "input-set-join")
    sources, rows = _source_pins(export_root), _registry_rows(ledger_path)
    _require(sources.keys() == rows.keys(), "one-to-one-source-set")
    _require(header["summary"].get("filesSelected") == header["summary"].get("filesSucceeded") == len(rows)
             and header["summary"].get("filesFailed") == 0, "family-completeness")
    evidence = {}
    for key, source in sources.items():
        row = rows[key]
        _require(row.get("exportRelativePath") == source["path"] and row.get("length") == source["length"]
                 and row.get("logicalSha256") == source["sha256"], "source-byte-join", source["path"])
        evidence["game/Json/" + source["path"]] = _project(row)
    _require(_source_pins(export_root) == sources, "export-source-drift")
    _require(select_current_family_report("SkillData", export_root, summary_path=summary_path, ledger_path=ledger_path)
             == (path, selection), "canonical-receipt-drift")
    _require(_current_family_inputs(header, selection) == inputs, "family-input-drift")
    _require(require_current_reader_inputs(reader) == reader, "reader-input-drift")
    return evidence, {"status": "current-canonical-skill-evidence", "selection": selection,
                      "inputs": inputs, "readerInputs": reader, "sourceCount": len(evidence)}


def try_skill_root_evidence(export_root: Path):
    try:
        return load_skill_root_evidence(export_root)
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as error:
        return None, {"status": "canonical-skill-evidence-unavailable", "reason": str(error)[:1000]}


def attach_skill_root_evidence(records: list[dict[str, Any]], evidence: dict[str, Any] | None):
    """Add separate proof facts without changing derived status or payload."""
    if evidence is None:
        return records
    ids = [record["id"] for record in records]
    _require(len(ids) == len(set(ids)) and set(ids) == evidence.keys(), "derived-record-source-set")
    return [{**record, "facts": {**record.get("facts", {}), "canonicalRootEvidence": evidence[record["id"]]}}
            for record in records]
