"""Native-only SkillData cursor observer audit over an unselected current basis.

This is deliberately separate from the full IL2CPP context audit, whose
terminal sample witnesses require an already selected SkillData corpus.

The full audit stops on an all-unselected basis at its ``ambiguous``
boundary before emitting a context, and that selected-sample prerequisite
stays intact.  This path instead validates a complete-shaped, all-ambiguous
current basis and its live source/tool provenance, pins the exact basis
report digest, and checks the selected native method identities, body windows
and every top-level and ActionGroup observer callsite.  It does not re-stream
the corpus or turn a static observer coordinate into an executed cursor.  A
context from an earlier input set cannot substitute, even with unchanged
native binaries.  The receipt verifiers' preflight consumes this context
without promoting a candidate.

Build it with ``--corpus-report`` set to the unselected basis
(``reports/animestudio/skilldata_cursor_basis_latest.json``), an optional
``--target-contract`` (for example
``contracts/skill_cursor_capture_purrche_combo_target.json``) and an
``--output`` per target (default
``reports/animestudio/skill_cursor_native_context_current_latest.json``);
``--preflight`` revalidates an existing context, and with
``--capture-binding`` prints the input set and exact target source SHA-256.

Pinned values.  The observer contract (``contracts/skill_cursor_observer_native.json``)
holds every build- and corpus-locked value this module checks: reader method
rows, body windows, observer callsites, receipt source lengths and the
recorder's selected source lengths (the capture-target length allow-list,
mirroring the EndfieldCapture SkillData provider).  The audit gates on that
contract's ``nativeInputs`` and fails closed on ``missing`` or ``mismatched``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import struct
import sys
import tempfile
from pathlib import Path
from typing import Any, Mapping

from scripts.common import check_installed_native_inputs, sha256_file_upper
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import NativeImage
from scripts.game_data.memorypack.corpus_gate import CensusGateError
from scripts.game_data.memorypack.skill_corpus import verify_current_report_inputs
from scripts.game_data.memorypack.skill_cursor_receipt import load_observer_contract
from scripts.repo_paths import REPO_ROOT


SCHEMA = "endfield.skill-cursor-native-context.v1"
CONTRACT_SCHEMA = "endfield.skill-cursor-observer-native.v2"
CONTRACT_PATH = CONTRACTS_DIR / "skill_cursor_observer_native.json"
TARGET_CONTRACT_PATH = CONTRACTS_DIR / "skill_cursor_capture_target.json"
DEFAULT_CORPUS = REPO_ROOT / "reports/animestudio/skilldata_cursor_basis_latest.json"
DEFAULT_CONTEXT = REPO_ROOT / "reports/animestudio/skill_cursor_native_context_current_latest.json"
HEX64 = re.compile(r"^[0-9A-Fa-f]{64}$")
# The recorder's selected source lengths are corpus-locked declarations in the
# observer contract, loaded through the receipt verifier's shape check.
RECORDER_SUPPORTED_SOURCE_LENGTHS = frozenset(
    load_observer_contract(CONTRACT_PATH)["recorderSelectedSourceLengths"])


class NativeCursorContextError(ValueError):
    def __init__(self, code: str, *, source: str, expected: Any, actual: Any) -> None:
        self.diagnostic = {
            "validator": "skill-cursor-native-context",
            "code": code,
            "source": source,
            "expected": expected,
            "actual": actual,
        }
        super().__init__(json.dumps(self.diagnostic, ensure_ascii=False, sort_keys=True))


def _require(condition: bool, code: str, *, source: str, expected: Any, actual: Any) -> None:
    if not condition:
        raise NativeCursorContextError(code, source=source, expected=expected, actual=actual)


def _file_reference(path: Path) -> dict[str, Any]:
    resolved = path.resolve()
    _require(resolved.is_file(), "input-missing", source=str(resolved),
             expected="regular file", actual="missing")
    return {
        "path": resolved.as_posix(),
        "length": resolved.stat().st_size,
        "sha256": sha256_file_upper(resolved),
    }


def _bounded(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value[:160] + "..." if isinstance(value, str) and len(value) > 160 else value
    if isinstance(value, Mapping):
        return {"type": "object", "keys": sorted(str(key) for key in value)[:12],
                "size": len(value)}
    if isinstance(value, list):
        return {"type": "array", "length": len(value)}
    return type(value).__name__


def _first_difference(expected: Any, actual: Any, path: str) -> tuple[str, Any, Any] | None:
    """Find one deterministic, bounded diagnostic in a regenerated context."""
    if isinstance(expected, Mapping):
        if not isinstance(actual, Mapping):
            return path, _bounded(expected), _bounded(actual)
        for key in sorted(set(expected) | set(actual)):
            child_path = f"{path}.{key}"
            if key not in expected:
                return child_path, "absent", _bounded(actual[key])
            if key not in actual:
                return child_path, _bounded(expected[key]), "missing"
            difference = _first_difference(expected[key], actual[key], child_path)
            if difference is not None:
                return difference
        return None
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            return path, {"type": "array", "length": len(expected)}, _bounded(actual)
        for index, (want, got) in enumerate(zip(expected, actual)):
            difference = _first_difference(want, got, f"{path}[{index}]")
            if difference is not None:
                return difference
        return None
    if expected != actual:
        return path, _bounded(expected), _bounded(actual)
    return None


def validate_unselected_basis(corpus: Mapping[str, Any], *, source: str) -> tuple[str, int]:
    """Reject any selected terminal, stale summary, or unbounded row state."""
    input_set = corpus.get("inputSetSha256")
    _require(isinstance(input_set, str) and HEX64.fullmatch(input_set) is not None,
             "input-set-invalid", source=source, expected="64-hex inputSetSha256", actual=input_set)
    _require(corpus.get("format") == "animestudio-skilldata-current-vfs-corpus"
             and corpus.get("status") == "complete"
             and corpus.get("publicationEligible") is True,
             "basis-not-complete", source=source,
             expected={"format": "animestudio-skilldata-current-vfs-corpus",
                       "status": "complete", "publicationEligible": True},
             actual={key: corpus.get(key) for key in ("format", "status", "publicationEligible")})
    rows = corpus.get("files")
    _require(isinstance(rows, list) and bool(rows), "basis-files-invalid", source=source,
             expected="nonempty files array", actual=type(rows).__name__)
    summary = corpus.get("summary")
    _require(isinstance(summary, Mapping), "basis-summary-invalid", source=source,
             expected="summary object", actual=type(summary).__name__)
    expected_summary = {
        "filesSelected": len(rows), "filesSucceeded": len(rows),
        "filesFailed": 0, "filesUnsupported": 0,
        "filesUnique": 0, "filesAmbiguous": len(rows),
    }
    actual_summary = {key: summary.get(key) for key in expected_summary}
    _require(actual_summary == expected_summary, "unselected-summary-mismatch", source=source,
             expected=expected_summary, actual=actual_summary)
    seen: set[str] = set()
    for row in rows:
        path = row.get("virtualPath") if isinstance(row, Mapping) else None
        _require(isinstance(path, str) and path.startswith("Data/Json/SkillData/")
                 and path not in seen, "basis-row-identity-invalid", source=source,
                 expected="unique SkillData virtualPath", actual=path)
        seen.add(path)
        framing = row.get("framing")
        _require(isinstance(framing, Mapping), "basis-framing-invalid", source=path,
                 expected="framing object", actual=type(framing).__name__)
        actual = {
            "inputSetSha256": row.get("inputSetSha256"),
            "boundaryClass": row.get("boundaryClass"),
            "coverageStatus": row.get("coverageStatus"),
            "wholeSchemaExact": row.get("wholeSchemaExact"),
            "terminalSelection": row.get("terminalSelection"),
            "candidateCount": framing.get("candidateCount"),
        }
        expected = {
            "inputSetSha256": input_set,
            "boundaryClass": "ambiguous",
            "coverageStatus": "ambiguous-disjoint-independent-ranges",
            "wholeSchemaExact": False,
            "terminalSelection": None,
            "candidateCount": 2,
        }
        _require(actual == expected, "selected-or-unbounded-row", source=path,
                 expected=expected, actual=actual)
        candidates = framing.get("candidates")
        _require(isinstance(candidates, list) and len(candidates) == 2
                 and all(isinstance(candidate, Mapping)
                         and candidate.get("boundaryClass") == "ambiguous"
                         and candidate.get("exactToEof") is True
                         for candidate in candidates),
                 "candidate-state-invalid", source=path,
                 expected="two unselected exact-EOF ambiguous candidates",
                 actual=[{key: candidate.get(key) for key in ("encoding", "boundaryClass", "exactToEof")}
                         if isinstance(candidate, Mapping) else type(candidate).__name__
                         for candidate in candidates] if isinstance(candidates, list) else type(candidates).__name__)
    return input_set.upper(), len(rows)


def validate_native_observer(contract: Mapping[str, Any], image: NativeImage, *, source: str) -> dict[str, int]:
    """Prove method identities, reader body windows, and all observer E8 edges."""
    _require(contract.get("schema") == CONTRACT_SCHEMA
             and contract.get("status") == "selected-build-native-only",
             "contract-shape-invalid", source=source,
             expected={"schema": CONTRACT_SCHEMA, "status": "selected-build-native-only"},
             actual={key: contract.get(key) for key in ("schema", "status")})
    methods = contract.get("methods")
    _require(isinstance(methods, list) and len(methods) == 4,
             "method-vector-invalid", source=source,
             expected="four SkillData/ActionGroup reader and formatter methods",
             actual=len(methods) if isinstance(methods, list) else type(methods).__name__)
    for row in methods:
        try:
            image.validate_method_row(row)
        except (ValueError, IndexError, KeyError, TypeError) as exc:
            raise NativeCursorContextError("method-identity-mismatch", source=source,
                                           expected=row, actual=str(exc)) from exc
    windows = contract.get("codeWindows")
    _require(isinstance(windows, list) and len(windows) == 3,
             "code-window-vector-invalid", source=source, expected="three reader body windows",
             actual=len(windows) if isinstance(windows, list) else type(windows).__name__)
    for window in windows:
        _require(isinstance(window, Mapping), "code-window-invalid", source=source,
                 expected="code window object", actual=type(window).__name__)
        rva, length, digest = window.get("rva"), window.get("byteLength"), window.get("sha256")
        _require(type(rva) is int and type(length) is int and length > 0
                 and isinstance(digest, str) and HEX64.fullmatch(digest) is not None,
                 "code-window-invalid", source=source,
                 expected="bounded RVA, length and SHA-256", actual=window)
        actual = hashlib.sha256(image.pe.bytes_at_va(image.pe.image_base + rva, length)).hexdigest().upper()
        _require(actual == digest.upper(), "code-window-mismatch", source=f"{source}@0x{rva:X}",
                 expected=digest.upper(), actual=actual)
    fields = contract.get("fieldCallsites")
    inline = contract.get("inlineField")
    children = contract.get("actionGroupChildCallsites")
    _require(isinstance(fields, list) and len(fields) == 47
             and isinstance(inline, Mapping) and type(inline.get("fieldIndex")) is int
             and isinstance(children, list) and len(children) == 2,
             "observer-vector-invalid", source=source,
             expected="47 direct fields, one inline field, two ActionGroup children",
             actual={"fields": len(fields) if isinstance(fields, list) else type(fields).__name__,
                     "inline": inline, "children": len(children) if isinstance(children, list) else type(children).__name__})
    indices = [row.get("fieldIndex") if isinstance(row, Mapping) else None for row in fields]
    child_indices = [row.get("childIndex") if isinstance(row, Mapping) else None
                     for row in children]
    _require(all(type(index) is int for index in indices + child_indices)
             and sorted(indices + [inline["fieldIndex"]]) == list(range(48))
             and child_indices == [0, 1],
             "observer-index-drift", source=source,
             expected="each field index 0..47 once; child indices 0,1",
             actual={"fields": indices, "inline": inline["fieldIndex"],
                     "children": child_indices})
    field_window = windows[1]
    child_window = windows[2]
    for label, rows, window in (("field", fields, field_window), ("child", children, child_window)):
        for row in rows:
            call, target, raw_hex, after = (
                row.get("callInstructionRva"), row.get("targetRva"),
                row.get("rawHex"), row.get("returnAddressRva")
            )
            _require(type(call) is int and type(target) is int
                     and isinstance(raw_hex, str) and re.fullmatch(r"[0-9A-Fa-f]{10}", raw_hex)
                     and after == call + 5
                     and window["rva"] <= call < window["rva"] + window["byteLength"] - 4,
                     "observer-callsite-invalid", source=f"{source}.{label}[{row.get('fieldIndex', row.get('childIndex'))}]",
                     expected="E8 rel32 inside owning body; return RVA = call + 5",
                     actual={"callInstructionRva": call, "targetRva": target,
                             "rawHex": raw_hex, "returnAddressRva": after})
            raw = image.pe.bytes_at_va(image.pe.image_base + call, 5)
            actual_target = call + 5 + struct.unpack_from("<i", raw, 1)[0] if raw[:1] == b"\xE8" else None
            _require(raw.hex().upper() == raw_hex.upper() and actual_target == target,
                     "observer-callsite-mismatch", source=f"{source}@0x{call:X}",
                     expected={"rawHex": raw_hex.upper(), "targetRva": target},
                     actual={"rawHex": raw.hex().upper(), "targetRva": actual_target})
    lengths = contract.get("receiptVerifierSourceLengths")
    _require(isinstance(lengths, list) and len(lengths) == 2
             and all(type(value) is int and value > 0 for value in lengths),
             "source-length-vector-invalid", source=source,
             expected="two prior accepted-receipt source lengths", actual=lengths)
    return {"methods": len(methods), "codeWindows": len(windows),
            "fieldCallsites": len(fields), "childCallsites": len(children)}


def validate_capture_target(corpus: Mapping[str, Any], contract: Mapping[str, Any],
                            *, source: str) -> dict[str, Any]:
    _require(contract.get("schema") == "endfield.skill-cursor-capture-target.v1"
             and contract.get("status") == "selected-current-logical-source",
             "target-contract-invalid", source=source,
             expected="reviewed current SkillData logical-source contract",
             actual={key: contract.get(key) for key in ("schema", "status")})
    target = contract.get("target")
    _require(isinstance(target, Mapping), "target-contract-invalid", source=source,
             expected="target object", actual=type(target).__name__)
    path, length, digest = (target.get("virtualPath"), target.get("length"),
                            target.get("logicalSha256"))
    _require(isinstance(path, str) and path.startswith("Data/Json/SkillData/")
             and path.endswith(".json") and type(length) is int
             and length in RECORDER_SUPPORTED_SOURCE_LENGTHS
             and isinstance(digest, str) and HEX64.fullmatch(digest) is not None,
             "target-contract-invalid", source=source,
             expected="SkillData path, supported bounded recorder length, logical SHA-256",
             actual=_bounded(target))
    matches = [row for row in corpus["files"] if row.get("virtualPath") == path]
    _require(len(matches) == 1, "target-row-missing", source=path,
             expected="one current source row", actual=len(matches))
    row = matches[0]
    actual = {"length": row.get("length"), "logicalSha256": row.get("logicalSha256"),
              "blockName": row.get("blockName"), "blockTypeValue": row.get("blockTypeValue")}
    expected = {"length": length, "logicalSha256": digest.upper(),
                "blockName": "JsonData", "blockTypeValue": 19}
    _require(actual == expected, "target-source-mismatch", source=path,
             expected=expected, actual=actual)
    return {"virtualPath": path, "length": length, "logicalSha256": digest.upper()}


def audit_native_only(corpus_path: Path = DEFAULT_CORPUS,
                      target_contract_path: Path | None = None) -> dict[str, Any]:
    corpus_path = Path(corpus_path).resolve()
    contract_path = CONTRACT_PATH.resolve()
    target_contract_path = Path(target_contract_path or TARGET_CONTRACT_PATH).resolve()
    corpus_reference = _file_reference(corpus_path)
    contract_reference = _file_reference(contract_path)
    target_contract_reference = _file_reference(target_contract_path)
    auditor_reference = _file_reference(Path(__file__))
    try:
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        target_contract = json.loads(target_contract_path.read_text(encoding="utf-8"))
        corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise NativeCursorContextError("input-json-invalid", source=str(corpus_path),
                                       expected="valid contract and SkillData corpus JSON", actual=str(exc)) from exc
    _require(isinstance(contract, Mapping) and isinstance(target_contract, Mapping)
             and isinstance(corpus, Mapping),
             "input-json-shape-invalid", source=str(corpus_path),
             expected="contract, target contract and corpus root objects",
             actual={"contract": type(contract).__name__,
                     "targetContract": type(target_contract).__name__,
                     "corpus": type(corpus).__name__})
    input_set, file_count = validate_unselected_basis(corpus, source=str(corpus_path))
    target = validate_capture_target(corpus, target_contract, source=str(target_contract_path))
    try:
        verify_current_report_inputs(corpus)
    except (CensusGateError, OSError, ValueError, KeyError, TypeError) as exc:
        raise NativeCursorContextError("basis-provenance-failed", source=str(corpus_path),
                                       expected="current VFS/source/parser provenance",
                                       actual=getattr(exc, "diagnostic", str(exc))) from exc
    expected_native = contract.get("nativeInputs")
    _require(isinstance(expected_native, Mapping)
             and all(isinstance(expected_native.get(name), str)
                     and HEX64.fullmatch(expected_native[name]) is not None
                     for name in ("GameAssembly.dll", "global-metadata.dat")),
             "contract-native-inputs-invalid", source=str(contract_path),
             expected="GameAssembly.dll and global-metadata.dat SHA-256", actual=expected_native)
    gate = check_installed_native_inputs(
        expected_native["GameAssembly.dll"], expected_native["global-metadata.dat"]
    )
    _require(gate.status == "validated", "native-inputs-unavailable", source=str(gate.gameassembly),
             expected="validated selected GameAssembly.dll and global-metadata.dat",
             actual={"status": gate.status, "detail": gate.detail})
    try:
        image = NativeImage(gate.gameassembly, gate.metadata, label="skill-cursor-native-only")
        native_counts = validate_native_observer(contract, image, source=str(contract_path))
    except NativeCursorContextError:
        raise
    except (OSError, ValueError, KeyError, IndexError, TypeError) as exc:
        raise NativeCursorContextError("native-observer-validation-failed", source=str(contract_path),
                                       expected="exact method, body and callsite validation",
                                       actual=str(exc)) from exc
    observer = {
        "status": "exact-static-callsite-vector",
        "fieldCallsites": contract["fieldCallsites"],
        "inlineField": contract["inlineField"],
        "actionGroupChildCallsites": contract["actionGroupChildCallsites"],
        "sourceLengths": contract["receiptVerifierSourceLengths"],
        "boundary": (
            "Native-only post-CALL observer coordinates. Source lengths are prior accepted-receipt "
            "verifier compatibility values; no new executed cursor or terminal selection."
        ),
    }
    return {
        "schema": SCHEMA,
        "schemaVersion": 1,
        "status": "native-only-unselected",
        "inputSetSha256": input_set,
        "nativeInputs": {
            "gameassembly": str(gate.gameassembly.resolve()),
            "gameassemblySha256": gate.gameassembly_sha256.upper(),
            "metadata": str(gate.metadata.resolve()),
            "metadataSha256": gate.metadata_sha256.upper(),
        },
        "corpusReference": {**corpus_reference, "inputSetSha256": input_set,
                            "filesSelected": file_count, "terminalSelections": 0},
        "contractReference": contract_reference,
        "captureTargetContractReference": target_contract_reference,
        "captureTarget": target,
        "auditorReference": auditor_reference,
        "nativeValidation": {"status": "validated", **native_counts},
        "selectedSkillDataReaderOrder": {
            "status": "native-only-unselected",
            "runtimeCursorObserver": observer,
        },
        "evidenceBoundary": (
            "The complete-shaped unselected SkillData report has current source/tool provenance "
            "and an exact report digest; this audit does not re-stream every file. Selected "
            "installed native files, registered reader methods, body hashes and 47+2 observer "
            "calls are validated. No selected terminal sample, formatter/provider execution "
            "or file cursor is inferred."
        ),
    }


def preflight_native_only(corpus_path: Path = DEFAULT_CORPUS,
                          context_path: Path = DEFAULT_CONTEXT,
                          target_contract_path: Path | None = None) -> str:
    expected = audit_native_only(corpus_path, target_contract_path)
    context_path = Path(context_path).resolve()
    _require(context_path.is_file(), "context-missing", source=str(context_path),
             expected="native-only context report", actual="missing")
    try:
        actual = json.loads(context_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise NativeCursorContextError("context-json-invalid", source=str(context_path),
                                       expected="valid native-only context JSON", actual=str(exc)) from exc
    difference = _first_difference(expected, actual, str(context_path))
    _require(difference is None, "context-replay-mismatch",
             source=difference[0] if difference else str(context_path),
             expected=difference[1] if difference else "current audited context",
             actual=difference[2] if difference else "matching")
    from scripts.game_data.memorypack.skill_cursor_receipt import (
        ReceiptVerificationError, preflight_skilldata_corpus,
    )
    try:
        result = preflight_skilldata_corpus(
            corpus_report_path=corpus_path,
            native_context_path=context_path,
        )
    except ReceiptVerificationError as exc:
        raise NativeCursorContextError("receipt-preflight-failed", source=str(context_path),
                                       expected="matching current corpus/native observer vector",
                                       actual=str(exc)) from exc
    _require(result == expected["inputSetSha256"], "receipt-input-set-drift",
             source=str(context_path), expected=expected["inputSetSha256"], actual=result)
    return result


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n",
                                     dir=path.parent, prefix=path.name + ".",
                                     suffix=".tmp", delete=False) as handle:
        stage = Path(handle.name)
        handle.write(encoded)
    try:
        os.replace(stage, path)
    finally:
        stage.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-report", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--native-context", type=Path, default=DEFAULT_CONTEXT,
                        help="existing report to revalidate for --preflight")
    parser.add_argument("--target-contract", type=Path, default=None,
                        help="reviewed exact logical source; default is the current 561-byte target")
    parser.add_argument("--output", type=Path, default=DEFAULT_CONTEXT,
                        help="atomic report output when building")
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--capture-binding", action="store_true",
                        help="with --preflight print input set and exact target source SHA-256")
    args = parser.parse_args(argv)
    if args.capture_binding and not args.preflight:
        parser.error("--capture-binding requires --preflight")
    try:
        if args.preflight:
            result = preflight_native_only(args.corpus_report, args.native_context,
                                           args.target_contract)
            if args.capture_binding:
                context = json.loads(args.native_context.read_text(encoding="utf-8"))
                print(result, context["captureTarget"]["logicalSha256"])
            else:
                print(result)
        else:
            result = audit_native_only(args.corpus_report, args.target_contract)
            _atomic_json(args.output, result)
            print(json.dumps({"status": result["status"],
                              "inputSetSha256": result["inputSetSha256"],
                              "filesSelected": result["corpusReference"]["filesSelected"],
                              "output": str(args.output)}, ensure_ascii=False))
    except NativeCursorContextError as exc:
        print(json.dumps({"status": "failed", "diagnostic": exc.diagnostic},
                         ensure_ascii=False), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
