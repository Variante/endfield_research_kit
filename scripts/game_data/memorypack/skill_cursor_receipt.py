"""Verify bounded runtime SkillData cursor receipts against the current corpus.

The receipt's source bytes are treated as private input: output rows retain the
SHA-256 and structural ranges, never the supplied hex payload. A promoted row
proves only the observed terminal candidate cursor under the maintained
anonymous framer, not whole-schema semantics.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from scripts.game_data.memorypack.skill import (
    frame_skill_common_prefix,
    frame_skill_memorypack,
)


SCHEMA = "endfieldCapture.skillDataCursorCapture.v1"
OUTPUT_SCHEMA = "endfield.skillDataCursorVerification.v1"
SKILL_REPORT_FORMAT = "animestudio-skilldata-current-vfs-corpus"
START_CALLSITE_RVA = 0x37DE8C5
FINAL_CALLSITE_RVA = 0x37DE99D
HEX64_RE = re.compile(r"^[0-9a-fA-F]{64}$")
HEX_RE = re.compile(r"^(?:[0-9a-fA-F]{2})+$")
SKILL_PREFIX = "Data/Json/SkillData/"
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CORPUS_REPORT = REPO_ROOT / "reports/animestudio/skilldata_current_latest.json"
DEFAULT_NATIVE_CONTEXT = REPO_ROOT / "reports/animestudio/il2cpp_context_current_latest.json"


class ReceiptVerificationError(ValueError):
    """A global receipt/report gate failed; the capture cannot be verified."""


def _sha256_text(value: Any, *, source: str) -> str:
    if not isinstance(value, str) or HEX64_RE.fullmatch(value) is None:
        raise ReceiptVerificationError(f"{source}: expected a 64-character SHA-256")
    return value.upper()


def _integer(value: Any, *, source: str, minimum: int = 0) -> int:
    if type(value) is int:
        result = value
    elif isinstance(value, str):
        try:
            result = int(value, 0)
        except ValueError as exc:
            raise ReceiptVerificationError(f"{source}: invalid integer") from exc
    else:
        raise ReceiptVerificationError(f"{source}: expected an integer")
    if result < minimum:
        raise ReceiptVerificationError(f"{source}: value is below {minimum}")
    return result


def _zero_counter(value: Any) -> bool:
    if type(value) is int:
        return value == 0
    if isinstance(value, Mapping):
        return bool(value) and all(_zero_counter(child) for child in value.values())
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return bool(value) and all(_zero_counter(child) for child in value)
    return False


def _load_json(path: Path, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReceiptVerificationError(f"{label}: cannot read valid JSON ({exc})") from exc
    if not isinstance(value, dict):
        raise ReceiptVerificationError(f"{label}: expected a JSON object")
    return value


def _load_json_with_sha256(path: Path, *, label: str) -> tuple[dict[str, Any], str]:
    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReceiptVerificationError(f"{label}: cannot read valid JSON ({exc})") from exc
    if not isinstance(value, dict):
        raise ReceiptVerificationError(f"{label}: expected a JSON object")
    return value, hashlib.sha256(raw).hexdigest().upper()


def _normalise_required_path(value: str) -> str:
    text = value.replace("\\", "/").strip("/")
    if not text:
        raise ReceiptVerificationError("required logical path cannot be empty")
    if "/" not in text:
        text = SKILL_PREFIX + text
    if not text.startswith(SKILL_PREFIX) or not text.endswith(".json"):
        raise ReceiptVerificationError(
            f"required logical path must be a SkillData JSON path: {value!r}"
        )
    return text


def _require_capture_gates(receipt: Mapping[str, Any]) -> tuple[str, str, str, int]:
    if receipt.get("schema") != SCHEMA:
        raise ReceiptVerificationError("receipt.schema: unsupported schema")
    input_set = _sha256_text(receipt.get("inputSetSha256"), source="receipt.inputSetSha256")
    native = receipt.get("nativeInputs")
    if not isinstance(native, Mapping):
        raise ReceiptVerificationError("receipt.nativeInputs: expected an object")
    game_hash = _sha256_text(
        native.get("gameAssemblySha256"), source="receipt.nativeInputs.gameAssemblySha256"
    )
    metadata_hash = _sha256_text(
        native.get("metadataSha256"), source="receipt.nativeInputs.metadataSha256"
    )
    for field in ("captureComplete", "hooksInstalled", "quiescentCleanup"):
        if receipt.get(field) is not True:
            raise ReceiptVerificationError(f"receipt.{field}: required gate is not true")
    for field in ("losses", "overflow"):
        if not _zero_counter(receipt.get(field)):
            raise ReceiptVerificationError(f"receipt.{field}: expected all counters to be zero")
    unsupported_count = receipt.get("unsupported")
    if type(unsupported_count) is not int or unsupported_count < 0:
        raise ReceiptVerificationError("receipt.unsupported: expected a non-negative integer counter")
    observations = receipt.get("observations")
    if not isinstance(observations, list):
        raise ReceiptVerificationError("receipt.observations: expected an array")
    return input_set, game_hash, metadata_hash, unsupported_count


def _validate_report_gates(
    input_set: str,
    game_hash: str,
    metadata_hash: str,
    corpus: Mapping[str, Any],
    native_context: Mapping[str, Any],
    corpus_report_sha256: str | None,
) -> list[Mapping[str, Any]]:
    if corpus.get("format") != SKILL_REPORT_FORMAT:
        raise ReceiptVerificationError("corpus report has an unexpected format")
    if corpus.get("status") != "complete" or corpus.get("publicationEligible") is not True:
        raise ReceiptVerificationError("corpus report is not a complete current census")
    if _sha256_text(corpus.get("inputSetSha256"), source="corpus.inputSetSha256") != input_set:
        raise ReceiptVerificationError("receipt input set differs from the current SkillData corpus")
    rows = corpus.get("files")
    if not isinstance(rows, list) or not all(isinstance(row, Mapping) for row in rows):
        raise ReceiptVerificationError("corpus.files: expected an array of file objects")
    seen_paths: set[str] = set()
    for index, row in enumerate(rows):
        path = row.get("virtualPath")
        if not isinstance(path, str) or re.fullmatch(
            r"Data/Json/SkillData/[^/]+[.]json", path
        ) is None:
            raise ReceiptVerificationError(f"corpus.files[{index}]: invalid SkillData JsonData path")
        if path in seen_paths:
            raise ReceiptVerificationError(f"corpus.files[{index}]: duplicate logical path {path}")
        seen_paths.add(path)
        if str(row.get("inputSetSha256", "")).upper() != input_set:
            raise ReceiptVerificationError(f"corpus.files[{index}]: input set differs from report")
        if row.get("blockName") != "JsonData" or row.get("blockTypeValue") != 19:
            raise ReceiptVerificationError(f"corpus.files[{index}]: not a JsonData block")
        _sha256_text(row.get("logicalSha256"), source=f"corpus.files[{index}].logicalSha256")
        _integer(row.get("length"), source=f"corpus.files[{index}].length", minimum=1)
    if native_context.get("schemaVersion") != 1:
        raise ReceiptVerificationError("IL2CPP context report has an unsupported schema")
    if _sha256_text(native_context.get("inputSetSha256"), source="nativeContext.inputSetSha256") != input_set:
        raise ReceiptVerificationError("receipt input set differs from the IL2CPP context report")
    native = native_context.get("nativeInputs")
    if not isinstance(native, Mapping):
        raise ReceiptVerificationError("nativeContext.nativeInputs: expected an object")
    context_game_hash = _sha256_text(
        native.get("gameassemblySha256"), source="nativeContext.nativeInputs.gameassemblySha256"
    )
    context_metadata_hash = _sha256_text(
        native.get("metadataSha256"), source="nativeContext.nativeInputs.metadataSha256"
    )
    if (game_hash, metadata_hash) != (context_game_hash, context_metadata_hash):
        raise ReceiptVerificationError("receipt native hashes differ from the IL2CPP context report")
    corpus_reference = native_context.get("corpusReference")
    if not isinstance(corpus_reference, Mapping):
        raise ReceiptVerificationError("nativeContext.corpusReference: expected an object")
    expected_corpus_hash = _sha256_text(
        corpus_reference.get("sha256"),
        source="nativeContext.corpusReference.sha256",
    )
    if corpus_report_sha256 is None:
        raise ReceiptVerificationError(
            "corpus report bytes are required to verify nativeContext.corpusReference.sha256"
        )
    if _sha256_text(corpus_report_sha256, source="corpusReport.sha256") != expected_corpus_hash:
        raise ReceiptVerificationError(
            "SkillData corpus report bytes differ from nativeContext.corpusReference.sha256"
        )
    return rows


def preflight_skilldata_corpus(
    *,
    corpus_report_path: Path = DEFAULT_CORPUS_REPORT,
    native_context_path: Path = DEFAULT_NATIVE_CONTEXT,
) -> str:
    """Authenticate current corpus/native cross-references and return its input set."""
    corpus, corpus_digest = _load_json_with_sha256(
        corpus_report_path, label="SkillData corpus report"
    )
    native_context = _load_json(native_context_path, label="IL2CPP context report")
    input_set = _sha256_text(corpus.get("inputSetSha256"), source="corpus.inputSetSha256")
    native = native_context.get("nativeInputs")
    if not isinstance(native, Mapping):
        raise ReceiptVerificationError("nativeContext.nativeInputs: expected an object")
    game_hash = _sha256_text(
        native.get("gameassemblySha256"), source="nativeContext.nativeInputs.gameassemblySha256"
    )
    metadata_hash = _sha256_text(
        native.get("metadataSha256"), source="nativeContext.nativeInputs.metadataSha256"
    )
    _validate_report_gates(
        input_set,
        game_hash,
        metadata_hash,
        corpus,
        native_context,
        corpus_digest,
    )
    return input_set


def _decode_source(observation: Mapping[str, Any], index: int) -> tuple[bytes, str]:
    value = observation.get("sourceHex")
    if not isinstance(value, str) or HEX_RE.fullmatch(value) is None:
        raise ReceiptVerificationError(f"observation[{index}].sourceHex: expected contiguous even-length hex")
    data = bytes.fromhex(value)
    length = _integer(observation.get("sourceLength"), source=f"observation[{index}].sourceLength")
    if length != len(data):
        raise ReceiptVerificationError(f"observation[{index}].sourceLength does not match sourceHex")
    return data, hashlib.sha256(data).hexdigest().upper()


def _join_source(
    rows: list[Mapping[str, Any]], input_set: str, digest: str, length: int
) -> tuple[Mapping[str, Any] | None, str | None]:
    matches = [
        row for row in rows
        if str(row.get("inputSetSha256", "")).upper() == input_set
        and str(row.get("logicalSha256", "")).upper() == digest
    ]
    if len(matches) != 1:
        return None, "source-hash-join-missing" if not matches else "source-hash-join-ambiguous"
    row = matches[0]
    if _integer(row.get("length"), source="corpus file length") != length:
        return None, "source-length-mismatch"
    virtual_path = row.get("virtualPath")
    if not isinstance(virtual_path, str) or not virtual_path.startswith(SKILL_PREFIX):
        return None, "source-logical-path-invalid"
    return row, None


def _offset(value: Any, *, source: str, maximum: int) -> int:
    result = _integer(value, source=source)
    if result > maximum:
        raise ReceiptVerificationError(f"{source}: offset exceeds the source hard limit")
    return result


def _member_ranges(candidate: Mapping[str, Any]) -> list[dict[str, Any]]:
    ranges: list[dict[str, Any]] = []
    for member in candidate.get("members", []):
        span = member.get("range") if isinstance(member, Mapping) else None
        if not isinstance(span, Mapping):
            continue
        start, end = span.get("start"), span.get("end")
        if type(start) is not int or type(end) is not int or start < 0 or end < start:
            continue
        ranges.append({
            "start": start,
            "end": end,
            "kind": member.get("kind", "anonymous-terminal-member"),
            "memberIndex": member.get("index"),
        })
    return ranges


def _prefix_ranges(prefix: Mapping[str, Any]) -> list[dict[str, Any]]:
    hard_end = int(str(prefix["cursorOffset"]), 0)
    counts: list[tuple[int, int, int]] = []
    for row in prefix.get("recordLists", []):
        start = int(str(row["countOffset"]), 0)
        if start < 0 or start + 4 > hard_end:
            return [{"start": 0, "end": hard_end, "kind": "anonymous-structural-prefix"}]
        counts.append((start, start + 4, int(row.get("index", len(counts)))))
    ranges: list[dict[str, Any]] = []
    cursor = 0
    for start, end, index in sorted(counts):
        if start < cursor:
            return [{"start": 0, "end": hard_end, "kind": "anonymous-structural-prefix"}]
        if cursor < start:
            ranges.append({"start": cursor, "end": start, "kind": "anonymous-prefix-bytes"})
        ranges.append({
            "start": start, "end": end,
            "kind": "anonymous-record-list-count", "index": index,
        })
        cursor = end
    if cursor < hard_end:
        ranges.append({"start": cursor, "end": hard_end, "kind": "anonymous-prefix-bytes"})
    return ranges


def _candidate_alternatives(
    candidates: Sequence[Mapping[str, Any]], prefix_cursor: int
) -> list[dict[str, Any]]:
    alternatives = []
    for index, candidate in enumerate(candidates):
        start = int(str(candidate.get("startOffset", "-1")), 0)
        end = int(str(candidate.get("endOffset", "-1")), 0)
        gap = []
        if prefix_cursor < start:
            gap.append({
                "start": prefix_cursor,
                "end": start,
                "kind": "opaque-before-candidate",
            })
        alternatives.append({
            "candidateIndex": index,
            "start": start,
            "end": end,
            "encoding": candidate.get("encoding"),
            "byteRanges": _member_ranges(candidate),
            "opaqueByteRanges": gap,
            "prefixCandidateOverlap": start < prefix_cursor,
            "selected": False,
        })
    return alternatives


def _merge_opaque_ranges(spans: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    intervals = sorted(
        (int(span["start"]), int(span["end"]))
        for span in spans
        if type(span.get("start")) is int
        and type(span.get("end")) is int
        and span["start"] < span["end"]
    )
    merged: list[list[int]] = []
    for start, end in intervals:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [
        {"start": start, "end": end, "kind": "unresolved-opaque-range"}
        for start, end in merged
    ]


def _verify_observation(
    observation: Any,
    index: int,
    rows: list[Mapping[str, Any]],
    input_set: str,
) -> dict[str, Any]:
    base: dict[str, Any] = {"observationIndex": index, "boundaryClass": "unsupported"}
    if not isinstance(observation, Mapping):
        base["diagnostic"] = "observation-not-object"
        return base
    try:
        data, digest = _decode_source(observation, index)
    except ReceiptVerificationError as exc:
        base["diagnostic"] = str(exc).split(": ", 1)[-1]
        return base
    source_length = len(data)
    base.update({"logicalSha256": digest, "hardLimit": source_length})
    corpus_row, join_error = _join_source(rows, input_set, digest, source_length)
    if corpus_row is None:
        base["diagnostic"] = join_error
        return base
    logical_path = str(corpus_row["virtualPath"])
    base["logicalPath"] = logical_path
    try:
        prefix = frame_skill_common_prefix(data)
        framed = frame_skill_memorypack(data, source=logical_path)
    except (ValueError, TypeError, KeyError) as exc:
        base["diagnostic"] = str(exc).split(": ", 1)[-1]
        return base

    prefix_cursor = int(str(prefix["cursorOffset"]), 0)
    prefix_ranges = _prefix_ranges(prefix)
    candidates = framed.get("candidates", [])
    alternatives = _candidate_alternatives(candidates, prefix_cursor)
    has_prefix_candidate_overlap = any(
        alternative["prefixCandidateOverlap"] for alternative in alternatives
    )
    result: dict[str, Any] = {
        **base,
        "hardLimit": source_length,
        "parserCursor": None,
        "byteRanges": prefix_ranges,
        "opaqueByteRanges": _merge_opaque_ranges([
            {"start": prefix_cursor, "end": min(
                (alt["start"] for alt in alternatives), default=source_length
            )}
        ]),
        "candidateAlternatives": alternatives,
        "prefixCandidateOverlap": has_prefix_candidate_overlap,
        "framerStatus": framed.get("status"),
        "structuralPrefix": (
            type(prefix.get("provenPrefixByteLength")) is int
            and prefix["provenPrefixByteLength"] > 0
        ),
        "boundaryClass": "ambiguous" if candidates else "unsupported",
    }
    try:
        if _integer(observation.get("startCallsiteRva"), source="startCallsiteRva") != START_CALLSITE_RVA:
            raise ReceiptVerificationError("start-callsite-mismatch")
        if _integer(observation.get("finalCallsiteRva"), source="finalCallsiteRva") != FINAL_CALLSITE_RVA:
            raise ReceiptVerificationError("final-callsite-mismatch")
        if observation.get("sameReader") is not True or observation.get("sameThread") is not True:
            raise ReceiptVerificationError("reader-or-thread-identity-drift")
        start_before = _offset(observation.get("startCursorBefore"), source="startCursorBefore", maximum=source_length)
        start_after = _offset(observation.get("startCursorAfter"), source="startCursorAfter", maximum=source_length)
        final_before = _offset(observation.get("finalCursorBefore"), source="finalCursorBefore", maximum=source_length)
        final_after = _offset(observation.get("finalCursorAfter"), source="finalCursorAfter", maximum=source_length)
        start_byte = _integer(observation.get("startByte"), source="startByte", minimum=0)
        final_byte = _integer(observation.get("finalByte"), source="finalByte", minimum=0)
        start_result = observation.get("startResult")
        final_result = observation.get("finalResult")
        if type(start_result) is not bool:
            raise ReceiptVerificationError("start-result-not-boolean")
        if type(final_result) is not bool:
            raise ReceiptVerificationError("final-result-not-boolean")
        if start_byte > 255 or final_byte > 255:
            raise ReceiptVerificationError("observed-byte-out-of-range")
        if start_after != start_before + 1 or start_before >= source_length:
            raise ReceiptVerificationError("start-cursor-step-invalid")
        if data[start_before] != start_byte or start_byte not in (0, 1):
            raise ReceiptVerificationError("start-byte-does-not-match-source-bool")
        if start_result != (start_byte == 1):
            raise ReceiptVerificationError("start-result-does-not-match-source-byte")
        if final_after != final_before + 1 or final_before >= source_length:
            raise ReceiptVerificationError("final-cursor-step-invalid")
        if data[final_before] != final_byte or final_byte not in (0, 1):
            raise ReceiptVerificationError("final-byte-does-not-match-source-bool")
        if final_result != (final_byte == 1):
            raise ReceiptVerificationError("final-result-does-not-match-source-byte")
    except (ReceiptVerificationError, ValueError, TypeError, KeyError) as exc:
        result["boundaryClass"] = "unsupported"
        result["diagnostic"] = str(exc).split(": ", 1)[-1]
        return result

    start_matches = [
        candidate for candidate in candidates
        if int(str(candidate.get("startOffset", "-1")), 0) == start_before
    ]
    result["range"] = {"start": start_before, "end": source_length}
    result["parserCursor"] = final_after
    # A short but otherwise valid final cursor leaves an explicit runtime tail.
    runtime_tail = (
        {"start": final_after, "end": source_length}
        if final_after < source_length else None
    )
    result["opaqueByteRanges"] = _merge_opaque_ranges([
        *result["opaqueByteRanges"],
        *([runtime_tail] if runtime_tail is not None else []),
    ])
    result["candidateAlternatives"] = alternatives
    result["boundaryClass"] = "ambiguous" if candidates else "unsupported"
    if not start_matches:
        result["diagnostic"] = "observed-start-does-not-match-framer-candidate"
        return result
    if len(start_matches) != 1:
        result["diagnostic"] = "observed-start-matches-multiple-framer-candidates"
        return result

    candidate = start_matches[0]
    candidate_start = int(str(candidate.get("startOffset", "-1")), 0)
    for alternative in alternatives:
        alternative["selected"] = alternative["start"] == candidate_start
    candidate_end = int(str(candidate.get("endOffset", "-1")), 0)
    final_members = candidate.get("members", [])
    last_member = final_members[-1] if final_members else {}
    last_range = last_member.get("range", {}) if isinstance(last_member, Mapping) else {}
    last_start = last_range.get("start") if isinstance(last_range, Mapping) else None
    result["candidate"] = {
        "start": candidate_start,
        "end": candidate_end,
        "encoding": candidate.get("encoding"),
        "framerCandidateCount": len(candidates),
    }
    selected_prefix_overlap = candidate_start < prefix_cursor
    result["prefixCandidateOverlap"] = selected_prefix_overlap
    if selected_prefix_overlap:
        result["diagnostic"] = "prefix-candidate-range-overlap"
        result["prefixCandidateOverlap"] = True
        return result
    if (
        candidate_end != source_length
        or final_after != candidate_end
        or final_before != candidate_end - 1
        or last_member.get("kind") != "bool"
        or last_start != final_before
    ):
        result["diagnostic"] = "observed-final-cursor-does-not-close-candidate-at-hard-limit"
        return result

    result.update({
        "boundaryClass": "exact-closed",
        "prefixCandidateOverlap": False,
        "byteRanges": [*prefix_ranges, *_member_ranges(candidate)],
    })
    result["opaqueByteRanges"] = _merge_opaque_ranges([
        {"start": prefix_cursor, "end": start_before}
    ])
    return result


def verify_skilldata_cursor_capture(
    receipt: Mapping[str, Any],
    *,
    corpus_report_path: Path = DEFAULT_CORPUS_REPORT,
    native_context_path: Path = DEFAULT_NATIVE_CONTEXT,
    required_logical_paths: Sequence[str] = (),
) -> dict[str, Any]:
    """Verify receipt gates, source-hash joins, native pins and observed cursors."""
    input_set, game_hash, metadata_hash, receipt_unsupported = _require_capture_gates(receipt)
    corpus_report, corpus_report_sha256 = _load_json_with_sha256(
        corpus_report_path, label="SkillData corpus report"
    )
    native_context = _load_json(native_context_path, label="IL2CPP context report")
    corpus_rows = _validate_report_gates(
        input_set, game_hash, metadata_hash, corpus_report, native_context,
        corpus_report_sha256,
    )
    observations = receipt["observations"]
    rows = [
        _verify_observation(observation, index, corpus_rows, input_set)
        for index, observation in enumerate(observations)
    ]
    required = sorted({_normalise_required_path(value) for value in required_logical_paths})
    exact_paths = {
        str(row.get("logicalPath")) for row in rows
        if row.get("boundaryClass") == "exact-closed"
    }
    missing_required = [path for path in required if path not in exact_paths]
    opaque_by_row = [
        _merge_opaque_ranges([
            *row.get("opaqueByteRanges", []),
            *(
                span
                for alternative in row.get("candidateAlternatives", [])
                for span in alternative.get("opaqueByteRanges", [])
            ),
        ])
        for row in rows
    ]
    counts = {
        "exactClosed": sum(row.get("boundaryClass") == "exact-closed" for row in rows),
        "structuralPrefix": sum(row.get("structuralPrefix") is True for row in rows),
        "ambiguous": sum(row.get("boundaryClass") == "ambiguous" for row in rows),
        "unsupported": (
            sum(row.get("boundaryClass") == "unsupported" for row in rows)
            + receipt_unsupported
        ),
        "unsupportedReceiptEvents": receipt_unsupported,
        "opaque": sum(bool(spans) for spans in opaque_by_row),
        "opaqueBytes": sum(
            int(span["end"]) - int(span["start"])
            for spans in opaque_by_row for span in spans
        ),
    }
    all_rows_closed = bool(rows) and counts["exactClosed"] == len(rows)
    status = "complete" if all_rows_closed and not missing_required else "failed"
    return {
        "schema": OUTPUT_SCHEMA,
        "status": status,
        "inputSetSha256": input_set,
        "nativeInputs": {
            "gameAssemblySha256": game_hash,
            "metadataSha256": metadata_hash,
        },
        "summary": {
            "observations": len(rows),
            **counts,
            "requiredLogicalPaths": required,
            "verifiedRequiredLogicalPaths": [path for path in required if path in exact_paths],
            "missingRequiredLogicalPaths": missing_required,
            "wholeSchemaExact": False,
            "boundary": (
            "exactClosed counts only runtime-selected terminal candidates that the maintained "
                "framer consumes to the source hard limit; structuralPrefix is also counted when "
                "present, and opaqueBytes count merged file-level gaps and runtime-unconsumed tails. "
                "Unresolved alternatives retain separate candidate ranges and per-candidate gaps"
            ),
        },
        "rows": rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt", type=Path, nargs="?")
    parser.add_argument(
        "--preflight", action="store_true",
        help="authenticate the current corpus/native cross-reference and print its inputSet SHA-256",
    )
    parser.add_argument("--corpus-report", type=Path, default=DEFAULT_CORPUS_REPORT)
    parser.add_argument("--native-context", type=Path, default=DEFAULT_NATIVE_CONTEXT)
    parser.add_argument(
        "--required-logical-path", action="append", default=[],
        help="SkillData path (repeatable; a basename is expanded under Data/Json/SkillData/)",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if args.preflight:
        if args.receipt is not None:
            parser.error("--preflight does not accept a receipt positional argument")
        if args.output:
            parser.error("--preflight does not accept --output")
        try:
            input_set = preflight_skilldata_corpus(
                corpus_report_path=args.corpus_report,
                native_context_path=args.native_context,
            )
        except ReceiptVerificationError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        sys.stdout.write(input_set + "\n")
        return 0
    if args.receipt is None:
        parser.error("receipt is required unless --preflight is selected")
    try:
        receipt = _load_json(args.receipt, label="capture receipt")
        result = verify_skilldata_cursor_capture(
            receipt,
            corpus_report_path=args.corpus_report,
            native_context_path=args.native_context,
            required_logical_paths=args.required_logical_path,
        )
    except ReceiptVerificationError as exc:
        result = {"schema": OUTPUT_SCHEMA, "status": "failed", "diagnostic": str(exc)}
    encoded = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8", newline="\n")
    else:
        sys.stdout.write(encoded)
    return 0 if result.get("status") == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
