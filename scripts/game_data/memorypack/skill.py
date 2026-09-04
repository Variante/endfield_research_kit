"""Fail-closed structural framing for current SkillData MemoryPack payloads.

This module deliberately does not assign authored field names to the terminal
members.  The selected-build metadata proves the wrapper's member count and
declared setter surface, but does not expose the formatter body/cursor order.
The byte shapes below are therefore structural claims only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from collections import Counter
from pathlib import Path
from typing import Any

from .buff import decode_skill_post_switch_tail_at
from .schemas import SKILL_MEMBER_COUNT


SKILL_TERMINAL_SHAPE_NOTE = (
    "exact EOF-anchored structural suffix; member names and serialized field "
    "ownership remain unresolved without a current formatter cursor"
)


SKILL_COMMON_PREFIX_MAX_RECORDS = 256


def _read_prefix_u32(data: bytes, offset: int, label: str) -> tuple[int, int]:
    if offset + 4 > len(data):
        raise ValueError(f"SkillData.commonPrefix:{label}:truncated-u32")
    return struct.unpack_from("<I", data, offset)[0], offset + 4


def frame_skill_common_prefix(data: bytes) -> dict[str, Any]:
    """Consume only the anonymous SkillData prefix before its first record body.

    Current 175A bytes expose a 48-member top-level envelope followed by a
    two-member anonymous envelope.  Its members begin as counted record lists.
    We consume counts in their actual byte order, validate the first record's
    member-count byte when non-empty, and stop before that variable record
    body.  No declaration/setter order or authored field name is used.
    """

    if not data:
        raise ValueError("SkillData.commonPrefix:truncated-member-count")
    if data[0] != SKILL_MEMBER_COUNT:
        raise ValueError(
            "SkillData.commonPrefix:top-member-count "
            f"expected={SKILL_MEMBER_COUNT} actual={data[0]}"
        )
    if len(data) < 2:
        raise ValueError("SkillData.commonPrefix:truncated-nested-envelope")
    nested_member_count = data[1]
    if nested_member_count != 2:
        raise ValueError(
            "SkillData.commonPrefix:nested-member-count "
            f"expected=2 actual={nested_member_count}"
        )

    first_count, cursor = _read_prefix_u32(data, 2, "record-list-0-count")
    if first_count > SKILL_COMMON_PREFIX_MAX_RECORDS:
        raise ValueError(
            "SkillData.commonPrefix:record-list-0-count "
            f"max={SKILL_COMMON_PREFIX_MAX_RECORDS} actual={first_count}"
        )
    lists = [{"index": 0, "count": first_count, "countOffset": "0x2"}]
    if first_count:
        if cursor >= len(data):
            raise ValueError("SkillData.commonPrefix:record-list-0:truncated-first-record")
        first_record_member_count = data[cursor]
        if first_record_member_count != 2:
            raise ValueError(
                "SkillData.commonPrefix:record-list-0:first-record-member-count "
                f"expected=2 actual={first_record_member_count}"
            )
        lists[0]["firstRecordMemberCount"] = first_record_member_count
        return {
            "status": "stopped-at-first-opaque-record-body",
            "topLevelMemberCount": SKILL_MEMBER_COUNT,
            "anonymousEnvelopeMemberCount": nested_member_count,
            "recordLists": lists,
            "cursorOffset": _format_offset(cursor),
            "provenPrefixByteLength": cursor,
            "stopListIndex": 0,
            "stopReason": "first non-empty anonymous record body; nested union cursor unavailable",
            "wholeSchemaExact": False,
        }

    second_count, cursor = _read_prefix_u32(data, cursor, "record-list-1-count")
    if second_count > SKILL_COMMON_PREFIX_MAX_RECORDS:
        raise ValueError(
            "SkillData.commonPrefix:record-list-1-count "
            f"max={SKILL_COMMON_PREFIX_MAX_RECORDS} actual={second_count}"
        )
    lists.append({"index": 1, "count": second_count, "countOffset": "0x6"})
    result = {
        "status": "anonymous-envelope-count-prefix-consumed",
        "topLevelMemberCount": SKILL_MEMBER_COUNT,
        "anonymousEnvelopeMemberCount": nested_member_count,
        "recordLists": lists,
        "cursorOffset": _format_offset(cursor),
        "provenPrefixByteLength": cursor,
        "wholeSchemaExact": False,
    }
    if second_count:
        if cursor >= len(data):
            raise ValueError("SkillData.commonPrefix:record-list-1:truncated-first-record")
        first_record_member_count = data[cursor]
        if first_record_member_count != 4:
            raise ValueError(
                "SkillData.commonPrefix:record-list-1:first-record-member-count "
                f"expected=4 actual={first_record_member_count}"
            )
        lists[1]["firstRecordMemberCount"] = first_record_member_count
        result.update({
            "status": "stopped-at-first-opaque-record-body",
            "stopListIndex": 1,
            "stopReason": "first non-empty anonymous record body; nested union cursor unavailable",
        })
    else:
        result["stopReason"] = "two-member anonymous envelope consumed; later top-level bytes remain opaque"
    return result


def _format_offset(offset: int) -> str:
    return f"0x{offset:x}"


def _terminal_candidate(data: bytes, start: int) -> dict[str, Any] | None:
    """Return one exact EOF-anchored candidate starting at ``start``.

    The maintained nested readers already enforce booleans, counts, member
    counts, strings, and exact EOF.  This adapter intentionally strips their
    provisional semantic labels and exposes only the proven byte shape.
    """

    decoded = decode_skill_post_switch_tail_at(
        data,
        start,
        start - 1,
        "opaque-prefix",
    )
    if decoded.get("status") != "parsed-through-exact-tail":
        return None

    tag_list = decoded.get("tagDuringAttach") or {}
    nested_list_a = decoded.get("toggleBuffs") or []
    nested_list_b = decoded.get("uiRangeHints") or []
    return {
        "status": "exact-eof-anchored-terminal-shape",
        "startOffset": _format_offset(start),
        "endOffset": _format_offset(len(data)),
        "byteLength": len(data) - start,
        "exactToEof": True,
        "shape": [
            "bool",
            "counted-member-record-list",
            "counted-nested-object-list-a",
            "counted-nested-object-list-b",
            "bool",
        ],
        "members": [
            {"index": 0, "type": "bool", "value": decoded["switchToCenterBeforeCast"]},
            {
                "index": 1,
                "type": "counted-member-record-list",
                "count": tag_list.get("count", 0),
                "encoding": tag_list.get("branch", ""),
            },
            {
                "index": 2,
                "type": "counted-nested-object-list",
                "count": decoded["toggleBuffsCount"],
                "sampledItemBounds": [
                    {
                        "offset": item.get("offset", ""),
                        "byteLength": item.get("byteLength"),
                        "memberCount": item.get("memberCount"),
                    }
                    for item in nested_list_a
                ],
            },
            {
                "index": 3,
                "type": "counted-nested-object-list",
                "count": decoded["uiRangeHintsCount"],
                "sampledItemBounds": [
                    {
                        "offset": item.get("offset", ""),
                        "byteLength": item.get("byteLength"),
                        "memberCount": item.get("memberCount"),
                    }
                    for item in nested_list_b
                ],
            },
            {"index": 4, "type": "bool", "value": decoded["useAIExclusiveFrame"]},
        ],
        "semanticFieldNamesStatus": "unresolved",
        "evidenceBoundary": SKILL_TERMINAL_SHAPE_NOTE,
    }


def frame_skill_memorypack(data: bytes) -> dict[str, Any]:
    """Frame the SkillData envelope and every exact terminal-shape candidate.

    A unique candidate proves one terminal boundary.  Multiple candidates are
    retained as ambiguity instead of selecting one by declaration/setter
    order.  The bytes before each candidate remain explicitly opaque.
    """

    if not data:
        raise ValueError("SkillData:truncated-member-count")
    member_count = data[0]
    if member_count != SKILL_MEMBER_COUNT:
        raise ValueError(
            f"SkillData:member-count expected={SKILL_MEMBER_COUNT} actual={member_count}"
        )
    if len(data) < 2:
        raise ValueError("SkillData:truncated-payload")

    candidates: list[dict[str, Any]] = []
    # The terminal shape begins with a strict MemoryPack bool.  Filtering on
    # that byte avoids invoking nested readers at impossible offsets while
    # retaining all structurally valid candidates.
    for start in range(1, len(data)):
        if data[start] not in (0, 1):
            continue
        candidate = _terminal_candidate(data, start)
        if candidate is not None:
            candidate["opaquePrefix"] = {
                "startOffset": "0x1",
                "endOffset": _format_offset(start),
                "byteLength": start - 1,
            }
            candidates.append(candidate)

    if len(candidates) == 1:
        status = "unique-exact-terminal-shape"
    elif candidates:
        status = "ambiguous-exact-terminal-shape"
    else:
        status = "terminal-shape-unresolved"

    ambiguity: dict[str, Any] | None = None
    if len(candidates) == 2:
        early, late = candidates
        early_start = int(early["startOffset"], 0)
        late_start = int(late["startOffset"], 0)
        early_members = early["members"]
        late_members = late["members"]
        shared_counts_early = [early_members[index].get("count") for index in (1, 2, 3)]
        shared_counts_late = [late_members[index].get("count") for index in (1, 2, 3)]
        if (
            late_start == early_start + 1
            and early_members[0].get("value") is False
            and late_members[0].get("value") is True
            and early_members[1].get("encoding") == "one-member-wrapper"
            and late_members[1].get("encoding") == "counted"
            and shared_counts_early == shared_counts_late
            and early_members[4].get("value") == late_members[4].get("value")
        ):
            ambiguity = {
                "kind": "one-byte-bool-vs-counted-wrapper-collision",
                "candidateStartOffsets": [early["startOffset"], late["startOffset"]],
                "sharedCountedRecordCounts": shared_counts_early,
                "resolutionStatus": "unresolved-both-exact-to-eof",
                "minimumMissingEvidence": (
                    "an independently proven end cursor for the immediately preceding "
                    "anonymous structure, or the current formatter read cursor"
                ),
            }

    result = {
        "status": status,
        "memberCount": member_count,
        "envelope": {
            "startOffset": "0x0",
            "payloadStartOffset": "0x1",
            "endOffset": _format_offset(len(data)),
            "byteLength": len(data),
        },
        "candidateCount": len(candidates),
        "candidates": candidates,
        "wholeSchemaExact": False,
        "serializedFieldOrderStatus": "unresolved",
        "evidenceBoundary": (
            "48-member outer envelope plus EOF-anchored terminal byte shape; "
            "opaque prefix, semantic field ownership, and complete nested union "
            "cursor remain unresolved"
        ),
    }
    if ambiguity is not None:
        result["ambiguity"] = ambiguity
    return result


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audit_skill_census(
    census_path: Path,
    boundary_report_path: Path,
    *,
    expected_input_set_sha256: str | None = None,
) -> dict[str, Any]:
    """Rejoin a SkillData census to current sources and rerun framing.

    The historical census does not carry ``inputSetSha256`` itself.  This
    audit therefore authenticates every source fingerprint from the supplied
    boundary report and every census payload by its ledger SHA-256 before it
    reports structural coverage.  A changed Persistent tree must first obtain
    a new boundary report and census; stale rows fail closed here.
    """

    census = json.loads(census_path.read_text(encoding="utf-8"))
    boundary = json.loads(boundary_report_path.read_text(encoding="utf-8"))
    input_set_sha256 = str(boundary.get("inputSetSha256") or "").upper()
    if len(input_set_sha256) != 64:
        raise ValueError("boundary-report:missing-inputSetSha256")
    if (
        expected_input_set_sha256 is not None
        and input_set_sha256 != expected_input_set_sha256.upper()
    ):
        raise ValueError(
            "boundary-report:inputSetSha256-mismatch "
            f"expected={expected_input_set_sha256.upper()} actual={input_set_sha256}"
        )

    source_rows = boundary.get("sourceFingerprints")
    if not isinstance(source_rows, list) or not source_rows:
        raise ValueError("boundary-report:missing-sourceFingerprints")
    for index, source in enumerate(source_rows):
        source_path = Path(str(source.get("path") or ""))
        expected_hash = str(source.get("sha256") or "").lower()
        if not source_path.is_file():
            raise ValueError(
                f"sourceFingerprints[{index}]:missing path={source_path}"
            )
        actual_hash = _sha256_file(source_path)
        if actual_hash != expected_hash:
            raise ValueError(
                f"sourceFingerprints[{index}]:sha256-mismatch "
                f"path={source_path} expected={expected_hash} actual={actual_hash}"
            )

    metadata = census.get("inputs", {}).get("metadata")
    if not isinstance(metadata, dict):
        raise ValueError("census:missing-metadata-provenance")
    metadata_path = Path(str(metadata.get("path") or ""))
    metadata_hash = str(metadata.get("sha256") or "").lower()
    if not metadata_path.is_file():
        raise ValueError(f"census:missing-metadata path={metadata_path}")
    actual_metadata_hash = _sha256_file(metadata_path)
    if len(metadata_hash) != 64 or actual_metadata_hash != metadata_hash:
        raise ValueError(
            "census:metadata-sha256-mismatch "
            f"path={metadata_path} expected={metadata_hash} actual={actual_metadata_hash}"
        )

    rows = census.get("files")
    if not isinstance(rows, list):
        raise ValueError("census:missing-files")
    expected_files = census.get("summary", {}).get("files")
    if expected_files != len(rows):
        raise ValueError(
            f"census:file-count-mismatch expected={expected_files} actual={len(rows)}"
        )

    seen_paths: set[str] = set()
    status_counts: Counter[str] = Counter()
    shape_counts: Counter[str] = Counter()
    ambiguous: list[dict[str, Any]] = []
    total_bytes = 0
    for index, row in enumerate(rows):
        virtual_path = str(row.get("virtualPath") or "")
        if not virtual_path:
            raise ValueError(f"files[{index}]:missing-virtualPath")
        if virtual_path in seen_paths:
            raise ValueError(f"files[{index}]:duplicate-virtualPath path={virtual_path}")
        seen_paths.add(virtual_path)

        payload_path = Path(str(row.get("exportPath") or ""))
        if not payload_path.is_file():
            raise ValueError(f"files[{index}]:missing-payload path={payload_path}")
        data = payload_path.read_bytes()
        declared_length = row.get("declaredLength")
        actual_length = row.get("actualLength")
        if declared_length != len(data) or actual_length != len(data):
            raise ValueError(
                f"files[{index}]:length-mismatch path={virtual_path} "
                f"declared={declared_length} censusActual={actual_length} actual={len(data)}"
            )
        expected_hash = str(row.get("ledgerSha256") or "").lower()
        actual_hash = hashlib.sha256(data).hexdigest()
        if len(expected_hash) != 64 or actual_hash != expected_hash:
            raise ValueError(
                f"files[{index}]:sha256-mismatch path={virtual_path} "
                f"expected={expected_hash} actual={actual_hash}"
            )

        framed = frame_skill_memorypack(data)
        status_counts[framed["status"]] += 1
        total_bytes += len(data)
        for candidate in framed["candidates"]:
            members = candidate["members"]
            shape_key = "/".join(
                str(members[member_index]["count"])
                for member_index in (1, 2, 3)
            )
            shape_counts[shape_key] += 1
        if framed["candidateCount"] != 1:
            ambiguous.append(
                {
                    "virtualPath": virtual_path,
                    "candidateCount": framed["candidateCount"],
                    "candidateStartOffsets": [
                        candidate["startOffset"] for candidate in framed["candidates"]
                    ],
                }
            )

    declared_bytes = census.get("summary", {}).get("declaredBytes")
    if declared_bytes != total_bytes:
        raise ValueError(
            f"census:byte-count-mismatch expected={declared_bytes} actual={total_bytes}"
        )

    return {
        "schemaVersion": 1,
        "inputSetSha256": input_set_sha256,
        "boundaryReport": str(boundary_report_path.resolve()),
        "census": str(census_path.resolve()),
        "censusLedger": str(census.get("inputs", {}).get("ledger") or ""),
        "metadataSha256": metadata_hash,
        "sourceFingerprintCount": len(source_rows),
        "files": len(rows),
        "bytes": total_bytes,
        "statusCounts": dict(sorted(status_counts.items())),
        "terminalListCountShapes": dict(sorted(shape_counts.items())),
        "nonUniqueRows": ambiguous,
        "wholeSchemaExact": False,
        "evidenceBoundary": (
            "source fingerprints and payload hashes reverified; 48-member envelope "
            "and anonymous EOF terminal shape only"
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Reverify and frame a current SkillData MemoryPack census."
    )
    parser.add_argument("census", type=Path)
    parser.add_argument("boundary_report", type=Path)
    parser.add_argument("--expected-input-set-sha256")
    args = parser.parse_args(argv)
    result = audit_skill_census(
        args.census,
        args.boundary_report,
        expected_input_set_sha256=args.expected_input_set_sha256,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
