"""Fail-closed structural framing for current SkillData MemoryPack payloads.

This module deliberately does not assign authored field names to the terminal
members.  The selected-build metadata proves the wrapper's member count and
declared setter surface, but does not expose the formatter body/cursor order.
The byte shapes below are therefore structural claims only.
"""

from __future__ import annotations

import struct
from typing import Any

from .schemas import SKILL_MEMBER_COUNT
from .skill_terminal import TerminalError, frame_skill_terminal_at


SKILL_TERMINAL_SHAPE_NOTE = (
    "EOF-anchored candidate within supported structural grammar; member names and serialized field "
    "ownership remain unresolved without a current formatter cursor"
)


SKILL_COMMON_PREFIX_MAX_RECORDS = 256


def _read_prefix_u32(data: bytes, offset: int, label: str) -> tuple[int, int]:
    if offset + 4 > len(data):
        raise ValueError(
            f"SkillData.commonPrefix:{label}:truncated-u32 offset={offset} "
            f"expected=4 actual={max(0, len(data) - offset)}"
        )
    return struct.unpack_from("<I", data, offset)[0], offset + 4


def _check_prefix_count(data: bytes, count: int, cursor: int, index: int) -> None:
    # Only one member-count byte per record is known here. Do not infer a
    # fixed record width from the first record or the managed declaration.
    if count > len(data) - cursor:
        raise ValueError(
            f"SkillData.commonPrefix:record-list-{index}-count offset={cursor - 4} "
            f"expected<=remaining-marker-bytes:{len(data) - cursor} actual={count}"
        )


def frame_skill_common_prefix(data: bytes) -> dict[str, Any]:
    """Consume only the anonymous SkillData prefix before its first record body.

    Supported bytes expose a 48-member top-level envelope followed by a
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
        _check_prefix_count(data, first_count, cursor, 0)
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
        _check_prefix_count(data, second_count, cursor, 1)
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


def _terminal_candidates(data: bytes, start: int, source: str) -> list[dict[str, Any]]:
    """Adapt all supported branch parses without choosing a preferred encoding."""
    try:
        parsed = frame_skill_terminal_at(data, start, source=source)
    except TerminalError:
        return []
    result = []
    for candidate in parsed["candidates"]:
        members = [
            {**member, "type": member["kind"]}
            for member in candidate["members"]
        ]
        result.append({
            "status": "exact-eof-anchored-terminal-shape",
            "startOffset": _format_offset(start),
            "endOffset": _format_offset(len(data)),
            "byteLength": len(data) - start,
            "exactToEof": True,
            "encoding": candidate["encoding"],
            "shape": [
                "bool", "counted-member-record-list",
                "counted-nested-object-list-a", "counted-nested-object-list-b", "bool",
            ],
            "members": members,
            "semanticFieldNamesStatus": "unresolved",
            "evidenceBoundary": SKILL_TERMINAL_SHAPE_NOTE,
        })
    return result


def frame_skill_memorypack(data: bytes, *, source: str = "SkillData") -> dict[str, Any]:
    """Frame the SkillData envelope and every exact terminal-shape candidate.

    A unique candidate is unique only within the supported grammar, not proof
    of the actual preceding cursor. Multiple starts or branches remain
    ambiguous. The bytes before each candidate remain explicitly opaque.
    """

    if not data:
        raise ValueError(f"{source}:truncated-member-count offset=0 expected=1 actual=0")
    member_count = data[0]
    if member_count != SKILL_MEMBER_COUNT:
        raise ValueError(
            f"{source}:member-count expected={SKILL_MEMBER_COUNT} actual={member_count} offset=0"
        )
    if len(data) < 2:
        raise ValueError(f"{source}:truncated-payload offset=1 expected>=1 actual=0")

    candidates: list[dict[str, Any]] = []
    # The terminal shape begins with a strict MemoryPack bool.  Filtering on
    # that byte avoids invoking nested readers at impossible offsets while
    # retaining all structurally valid candidates.
    for start in range(1, len(data)):
        if data[start] not in (0, 1):
            continue
        for candidate in _terminal_candidates(data, start, source):
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


if __name__ == "__main__":
    raise SystemExit(
        "Historical census rebinding is not supported. Run "
        "python -m scripts.game_data.memorypack.skill_corpus against the current VFS ledger."
    )
