"""Current-input SkillData corpus gate.

The authoritative outer VFS
ledger supplies identity and encrypted physical boundaries.  AnimeStudio
``stream --verify-md5`` supplies the decrypted logical bytes; every stream row
must join one-for-one to the current ledger before the MemoryPack framer runs.

Family-agnostic provenance and drift gating lives in :mod:`corpus_gate`; this
module owns only the SkillData selection, framing, and report contract.
"""

from __future__ import annotations

import argparse
import base64
import functools
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

from scripts.common import canonical_json_sha256 as _canonical_sha256
from scripts.game_data.memorypack.corpus_gate import (
    DEFAULT_CLI,
    DEFAULT_LEDGER,
    DEFAULT_OUTER,
    HEX64,
    MODULE_REPO_ROOT,
    CensusGateError,
    _atomic_write_json,
    _chunk_fingerprints,
    _chunk_selection_snapshot,
    _discover_blc_paths,
    _expected_blc_paths,
    _fail,
    _fingerprint,
    _guard_output_path,
    _guard_partial_output,
    _parser_source_snapshots,
    _read_outer_and_ledger,
    _require_int,
    _sha256_file,
    _snapshot_pinned_files,
    _stream_tool_snapshot,
    family_rows,
    verify_current_report_inputs as _verify_current_report_inputs,
)
from scripts.game_data.memorypack.skill import (
    frame_skill_exact_timeline_action_group_profile,
    frame_skill_common_prefix,
    frame_skill_empty_action_group_profile,
    frame_skill_memorypack,
)
from scripts.game_data.memorypack.skill_timeline_play_animation import (
    CONTRACT_PATH as TIMELINE_PLAY_ANIMATION_CONTRACT_PATH,
    decode_first_timeline_play_animation,
    validate_current_native_contract as validate_timeline_play_animation_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_play_animation_step import (
    CONTRACT_PATH as TIMELINE_PLAY_ANIMATION_STEP_CONTRACT_PATH,
    decode_first_timeline_play_animation_step,
    validate_current_native_contract as validate_timeline_play_animation_step_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_create_buff import (
    CONTRACT_PATH as TIMELINE_CREATE_BUFF_CONTRACT_PATH,
    decode_first_timeline_create_buff,
    validate_current_native_contract as validate_timeline_create_buff_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_find_target import (
    CONTRACT_PATH as TIMELINE_FIND_TARGET_CONTRACT_PATH,
    decode_first_timeline_find_target,
    validate_current_native_contract as validate_timeline_find_target_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_continuous_find_target import (
    CONTRACT_PATH as TIMELINE_CONTINUOUS_FIND_TARGET_CONTRACT_PATH,
    decode_first_timeline_continuous_find_target,
    validate_current_native_contract as validate_timeline_continuous_find_target_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_shared_sequence import (
    CONTRACT_PATH as TIMELINE_SHARED_SEQUENCE_CONTRACT_PATH,
    decode_first_timeline_shared_sequence,
    validate_current_native_contract as validate_timeline_shared_sequence_native_contract,
)
from scripts.game_data.memorypack.skill_cursor_receipt import (
    OUTPUT_SCHEMA as CURSOR_VERIFICATION_SCHEMA,
    TERMINAL_FIELD_CONTRACT,
    verify_skilldata_cursor_capture,
)
from scripts.game_data.memorypack.schemas import MEMORYPACK_FIELD_SCHEMAS


SKILL_PREFIX = "Data/Json/SkillData/"
SKILL_PATTERN = re.compile(r"^Data/Json/SkillData/[^/]+[.]json$")
SKILL_REPORT_FORMAT = "animestudio-skilldata-current-vfs-corpus"
VERIFIED_TERMINAL_COVERAGE = "verified-terminal-selection-disjoint-independent-ranges"
VERIFIED_ACTION_GROUP_PREFIX_COVERAGE = "verified-action-group-named-prefix-and-terminal"
VERIFIED_EMPTY_ACTION_GROUP_EXACT = "verified-whole-schema-exact-empty-action-group-profile"
VERIFIED_EMPTY_ACTION_GROUP_PARTIAL = "verified-empty-action-group-named-prefix-and-terminal"
VERIFIED_TIMELINE_PLAY_ANIMATION_PREFIX = "verified-timeline-play-animation-named-prefix-and-terminal"
VERIFIED_TIMELINE_PLAY_ANIMATION_EXACT = "verified-whole-schema-exact-timeline-play-animation-profile"
VERIFIED_TIMELINE_PLAY_ANIMATION_STEP_PREFIX = (
    "verified-timeline-play-animation-step-named-prefix-and-terminal"
)
VERIFIED_TIMELINE_PLAY_ANIMATION_STEP_EXACT = (
    "verified-whole-schema-exact-timeline-play-animation-step-profile"
)
VERIFIED_TIMELINE_CREATE_BUFF_ACTION_PREFIX = (
    "verified-timeline-create-buff-first-action-named-prefix-and-terminal"
)
VERIFIED_TIMELINE_CREATE_BUFF_RECORD_PREFIX = (
    "verified-timeline-create-buff-first-record-named-prefix-and-terminal"
)
VERIFIED_TIMELINE_CREATE_BUFF_EXACT = (
    "verified-whole-schema-exact-timeline-create-buff-profile"
)
VERIFIED_TIMELINE_FIND_TARGET_PREFIX = "verified-timeline-find-target-named-prefix-and-terminal"
VERIFIED_TIMELINE_FIND_TARGET_EXACT = "verified-whole-schema-exact-timeline-find-target-profile"
VERIFIED_TIMELINE_CONTINUOUS_FIND_TARGET_PREFIX = (
    "verified-timeline-continuous-find-target-named-prefix-and-terminal"
)
VERIFIED_TIMELINE_CONTINUOUS_FIND_TARGET_EXACT = (
    "verified-whole-schema-exact-timeline-continuous-find-target-profile"
)
VERIFIED_TIMELINE_SHARED_SEQUENCE_PREFIX = (
    "verified-timeline-shared-sequence-named-prefix-and-terminal"
)
VERIFIED_TIMELINE_SHARED_SEQUENCE_EXACT = (
    "verified-whole-schema-exact-timeline-shared-sequence-profile"
)

verify_current_report_inputs = functools.partial(
    _verify_current_report_inputs,
    expected_format=SKILL_REPORT_FORMAT,
    label="SkillData",
)


def _skill_rows(file_rows, *, expected_input: str) -> list[dict[str, Any]]:
    return family_rows(
        file_rows,
        expected_input=expected_input,
        prefix=SKILL_PREFIX,
        pattern=SKILL_PATTERN,
        label="skill",
    )


def _stream_command(cli_path: Path, outer: Mapping[str, Any], selected_rows: list[Mapping[str, Any]], *, partial: bool) -> list[str]:
    command = [
        str(cli_path.resolve()),
        "stream",
        "--streaming-assets", str(outer["primaryAssets"]),
        "--fallback-assets", str(outer["fallbackAssets"]),
        "--block-type", "json-data",
        "--verify-md5",
    ]
    if partial:
        for row in selected_rows:
            command.extend(("--file-regex", "^" + re.escape(str(row["virtualPath"])).replace(r"/", "/") + "$"))
    else:
        command.extend(("--file-regex", r"^Data/Json/SkillData/[^/]+[.]json$"))
    return command


def _read_stream_rows(command: list[str]) -> tuple[list[dict[str, Any]], str]:
    # The selected corpus is about 24 MiB (roughly 33 MiB base64), so bounded
    # communicate() avoids the stdout/stderr pipe deadlock of sequential drains.
    process = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", check=False)
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(process.stdout.splitlines(), 1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            _fail("stream-json-invalid", source="AnimeStudio stream stdout", offset=line_number, actual=str(exc))
        if not isinstance(row, dict):
            _fail("stream-row-not-object", source="AnimeStudio stream stdout", offset=line_number, actual=type(row).__name__)
        rows.append(row)
    if process.returncode != 0:
        _fail("stream-process-failed", source=command[0], expected=0, actual={"returnCode": process.returncode, "stderr": process.stderr[-4000:]})
    return rows, process.stderr


def _prefix_byte_ranges(common_prefix: Mapping[str, Any]) -> list[dict[str, Any]]:
    """List the ranges consumed by the anonymous envelope prefix parser."""
    hard_end = int(common_prefix["cursorOffset"], 0)
    counts: list[tuple[int, int, int]] = []
    for row in common_prefix.get("recordLists", []):
        raw_start = row.get("countOffset")
        start = int(raw_start, 0) if isinstance(raw_start, str) else raw_start
        if type(start) is not int or start < 0 or start + 4 > hard_end:
            return [{"start": 0, "end": hard_end, "kind": "anonymous-structural-prefix"}]
        counts.append((start, start + 4, int(row.get("index", len(counts)))))
    ranges: list[dict[str, Any]] = []
    cursor = 0
    for start, end, index in sorted(counts):
        if start < cursor:
            return [{"start": 0, "end": hard_end, "kind": "anonymous-structural-prefix"}]
        if cursor < start:
            ranges.append({"start": cursor, "end": start, "kind": "anonymous-prefix-bytes"})
        ranges.append({"start": start, "end": end, "kind": "anonymous-record-list-count", "index": index})
        cursor = end
    if cursor < hard_end:
        ranges.append({"start": cursor, "end": hard_end, "kind": "anonymous-prefix-bytes"})
    return ranges


def _candidate_byte_ranges(candidate: Mapping[str, Any]) -> list[dict[str, Any]]:
    ranges = []
    for member in candidate.get("members", []):
        span = member.get("range")
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


def _boundary_evidence_summary(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    candidates = [
        candidate
        for row in rows
        for candidate in row.get("framing", {}).get("candidates", [])
    ]
    opaque_by_candidate = sum(
        span["end"] - span["start"]
        for candidate in candidates
        for span in candidate.get("opaqueByteRanges", [])
    )
    opaque_at_file_level = sum(
        span["end"] - span["start"]
        for row in rows
        for span in row.get("opaqueByteRanges", [])
    )
    class_counts = Counter(row.get("boundaryClass", "failed") for row in rows)
    return {
        "exactClosedRecords": sum(row.get("boundaryClass") == "exact-closed" for row in rows),
        "filesWithStructuralPrefix": sum(bool(row.get("commonPrefixFraming", {}).get("provenPrefixByteLength")) for row in rows),
        "opaqueBytesByCandidate": opaque_by_candidate,
        "opaqueBytesAtFileLevel": opaque_at_file_level,
        "boundaryClassCounts": dict(sorted(class_counts.items())),
        "unsupportedFiles": class_counts.get("unsupported", 0),
        "failedFiles": class_counts.get("failed", 0),
        "ambiguousFiles": class_counts.get("ambiguous", 0),
        "selectedTerminalFiles": sum(
            row.get("terminalSelection", {}).get("status") == "verified-native-reader-alignment"
            for row in rows
        ),
        "namedActionGroupPrefixFiles": sum(
            row.get("actionGroupPrefix", {}).get("status") == "verified-named-prefix"
            for row in rows
        ),
        "namedActionGroupPrefixBytes": sum(
            row.get("actionGroupPrefix", {}).get("byteLength", 0)
            for row in rows
            if row.get("actionGroupPrefix", {}).get("status") == "verified-named-prefix"
        ),
        "exactFirstTimelinePlayAnimationRecords": sum(
            (row.get("timelinePlayAnimationProfile") or {}).get("status")
            == "verified-exact-first-timeline-play-animation-record"
            for row in rows
        ),
        "namedTimelinePlayAnimationBytes": sum(
            (row.get("timelinePlayAnimationProfile") or {}).get("newNamedBytesAfterPriorPrefix", 0)
            for row in rows
        ),
        "exactTimelinePlayAnimationWholeFiles": sum(
            row.get("coverageStatus") == VERIFIED_TIMELINE_PLAY_ANIMATION_EXACT
            for row in rows
        ),
        "exactFirstTimelinePlayAnimationStepRecords": sum(
            (row.get("timelinePlayAnimationStepProfile") or {}).get("status")
            == "verified-exact-first-timeline-play-animation-step-record"
            for row in rows
        ),
        "namedTimelinePlayAnimationStepBytes": sum(
            (row.get("timelinePlayAnimationStepProfile") or {}).get(
                "newNamedBytesAfterPriorPrefix", 0
            )
            for row in rows
        ),
        "exactTimelinePlayAnimationStepWholeFiles": sum(
            row.get("coverageStatus") == VERIFIED_TIMELINE_PLAY_ANIMATION_STEP_EXACT
            for row in rows
        ),
        "exactFirstTimelineCreateBuffActions": sum(
            (row.get("timelineCreateBuffProfile") or {}).get("status")
            in {
                "verified-exact-first-timeline-create-buff-action",
                "verified-exact-first-timeline-create-buff-record",
            }
            for row in rows
        ),
        "exactFirstTimelineCreateBuffRecords": sum(
            (row.get("timelineCreateBuffProfile") or {}).get("status")
            == "verified-exact-first-timeline-create-buff-record"
            for row in rows
        ),
        "namedTimelineCreateBuffBytes": sum(
            (row.get("timelineCreateBuffProfile") or {}).get(
                "newNamedBytesAfterPriorPrefix", 0
            )
            for row in rows
        ),
        "exactTimelineCreateBuffWholeFiles": sum(
            row.get("coverageStatus") == VERIFIED_TIMELINE_CREATE_BUFF_EXACT
            for row in rows
        ),
        "exactFirstTimelineFindTargetRecords": sum(
            (row.get("timelineFindTargetProfile") or {}).get("status")
            == "verified-exact-first-timeline-find-target-record"
            for row in rows
        ),
        "namedTimelineFindTargetBytes": sum(
            (row.get("timelineFindTargetProfile") or {}).get("newNamedBytesAfterPriorPrefix", 0)
            for row in rows
        ),
        "exactTimelineFindTargetWholeFiles": sum(
            row.get("coverageStatus") == VERIFIED_TIMELINE_FIND_TARGET_EXACT
            for row in rows
        ),
        "exactFirstTimelineContinuousFindTargetRecords": sum(
            (row.get("timelineContinuousFindTargetProfile") or {}).get("status")
            == "verified-exact-first-timeline-continuous-find-target-record"
            for row in rows
        ),
        "namedTimelineContinuousFindTargetBytes": sum(
            (row.get("timelineContinuousFindTargetProfile") or {}).get(
                "newNamedBytesAfterPriorPrefix", 0
            )
            for row in rows
        ),
        "exactTimelineContinuousFindTargetWholeFiles": sum(
            row.get("coverageStatus") == VERIFIED_TIMELINE_CONTINUOUS_FIND_TARGET_EXACT
            for row in rows
        ),
        "exactFirstTimelineSharedSequenceRecords": sum(
            (row.get("timelineSharedSequenceProfile") or {}).get("status")
            == "verified-exact-first-timeline-shared-sequence-record"
            for row in rows
        ),
        "namedTimelineSharedSequenceBytes": sum(
            (row.get("timelineSharedSequenceProfile") or {}).get(
                "newNamedBytesAfterPriorPrefix", 0
            )
            for row in rows
        ),
        "exactTimelineSharedSequenceWholeFiles": sum(
            row.get("coverageStatus") == VERIFIED_TIMELINE_SHARED_SEQUENCE_EXACT
            for row in rows
        ),
        "boundary": (
            "Exact closures count independently established records only; EOF-anchored grammar candidates are not promoted. "
            "Files with structural prefixes may also be ambiguous. Opaque-by-candidate counts alternatives separately; "
            "file-level opaque bytes are ranges outside the bounded prefix and candidate grammar."
        ),
    }


def _promote_action_group_prefix(row: dict[str, Any]) -> None:
    """Name the exact field-0 prefix authenticated by the current native reader.

    The caller has already replayed the hash-pinned cursor verification and
    checked the current SkillData and ActionGroupData callsite order.  A
    positive child list remains open: this promotes only the member-count and
    list-count reads before its first record body.
    """
    prefix = row.get("commonPrefixFraming")
    if not isinstance(prefix, Mapping):
        _fail(
            "skill-action-group-prefix-missing",
            source=row.get("virtualPath"), expected="current structural prefix", actual=prefix,
        )
    records = prefix.get("recordLists")
    cursor = prefix.get("parserCursor")
    if type(cursor) is not int:
        raw_cursor = prefix.get("cursorOffset")
        try:
            cursor = int(raw_cursor, 0)
        except (TypeError, ValueError):
            cursor = None
    expected_records: list[tuple[int, int, int]]
    if (
        prefix.get("topLevelMemberCount") != 48
        or prefix.get("anonymousEnvelopeMemberCount") != 2
        or not isinstance(records, list)
        or cursor not in (6, 10)
    ):
        _fail(
            "skill-action-group-prefix-shape-drift",
            source=row.get("virtualPath"), expected="48/2 header and cursor 6 or 10", actual=prefix,
        )
    if cursor == 6:
        expected_records = [(0, 2, 6)]
        if len(records) != 1 or records[0].get("count", 0) <= 0:
            _fail(
                "skill-passive-action-prefix-drift",
                source=row.get("virtualPath"), expected="positive first child list", actual=records,
            )
    else:
        expected_records = [(0, 2, 6), (1, 6, 10)]
        if (
            len(records) != 2
            or records[0].get("count") != 0
            or records[1].get("count", -1) < 0
        ):
            _fail(
                "skill-timeline-action-prefix-drift",
                source=row.get("virtualPath"), expected="empty first and present second child list", actual=records,
            )
    for record, (index, start, end) in zip(records, expected_records):
        raw_offset = record.get("countOffset", -1)
        count_offset = int(raw_offset, 0) if isinstance(raw_offset, str) else raw_offset
        if record.get("index") != index or count_offset != start:
            _fail(
                "skill-action-group-count-offset-drift",
                source=row.get("virtualPath"), expected={"index": index, "offset": start}, actual=record,
            )
    child_names = ("passiveEventActions", "timelineActions")
    named_ranges = [
        {"start": 0, "end": 1, "kind": "SkillData.member-count", "value": 48,
         "evidence": "authenticated-current-wrapper-reader-prefix"},
        {"fieldIndex": 0, "fieldName": "actionGroupData", "start": 1, "end": 2,
         "kind": "ActionGroupData.member-count", "value": 2,
         "evidence": "authenticated-current-wrapper-reader-prefix"},
    ]
    for record, (index, start, end) in zip(records, expected_records):
        named_ranges.append({
            "fieldIndex": 0,
            "fieldName": f"actionGroupData.{child_names[index]}.count",
            "start": start,
            "end": end,
            "kind": "nullable-list-count-i32",
            "value": record["count"],
            "evidence": "authenticated-current-wrapper-reader-prefix",
        })
    row["byteRanges"] = named_ranges + [
        span for span in row.get("byteRanges", [])
        if isinstance(span, Mapping) and span.get("start", -1) >= cursor
    ]
    row["actionGroupPrefix"] = {
        "status": "verified-named-prefix",
        "fieldIndex": 0,
        "fieldName": "actionGroupData",
        "memberOrder": list(child_names),
        "parserCursor": cursor,
        "byteLength": cursor - 1,
        "namedRanges": named_ranges[1:],
        "openChildList": child_names[len(records) - 1] if records[-1].get("count", 0) > 0 else None,
        "wholeFieldExact": False,
        "evidenceBoundary": (
            "The authenticated current SkillData reader selects field 0 and the current "
            "ActionGroupData reader calls passiveEventActions then timelineActions. Counts "
            "advance at their physical cursors; a positive list stops before its first record body."
        ),
    }
    row["coverageStatus"] = VERIFIED_ACTION_GROUP_PREFIX_COVERAGE


def _load_exact_json_provenance(
    value: Any, *, label: str, decode_json: bool = True
) -> tuple[dict[str, Any] | None, Path]:
    if not isinstance(value, Mapping):
        _fail("cursor-provenance-missing", source=label, expected="file provenance object", actual=value)
    raw_path = value.get("path")
    expected_length = value.get("length")
    expected_sha256 = value.get("sha256")
    if not isinstance(raw_path, str) or type(expected_length) is not int or not isinstance(expected_sha256, str):
        _fail("cursor-provenance-invalid", source=label, expected="path/length/sha256", actual=value)
    path = Path(raw_path).resolve()
    try:
        raw = path.read_bytes()
        decoded = json.loads(raw.decode("utf-8")) if decode_json else None
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _fail(
            "cursor-provenance-unreadable", source=label,
            expected="valid JSON" if decode_json else "readable file", actual=str(exc),
        )
    actual_sha256 = hashlib.sha256(raw).hexdigest().upper()
    if len(raw) != expected_length or actual_sha256 != expected_sha256.upper():
        _fail(
            "cursor-provenance-drift",
            source=label,
            expected={"length": expected_length, "sha256": expected_sha256.upper()},
            actual={"length": len(raw), "sha256": actual_sha256},
        )
    if decode_json and not isinstance(decoded, dict):
        _fail("cursor-provenance-not-object", source=label, expected="JSON object", actual=type(decoded).__name__)
    return decoded, path


#: The one build fingerprint whose change alone may carry a verification across
#: input sets. The input-set hash covers the exporter binary, so rebuilding it
#: moves the hash with the game data untouched.
EXPORTER_FINGERPRINT_NAME = "animestudio.cli.exe"

#: A timeline continuation the reader stopped short of field 42. It is a valid
#: unverified state, not drift: the verified prefix stands and nothing more is
#: promoted. Any other non-exact status still fails closed.
PARTIAL_TOP_LEVEL_CONTINUATION = "stopped-at-unsupported-top-level-field"


def _exporter_only_rebinding(
    *,
    verification: Mapping[str, Any],
    source_corpus: Mapping[str, Any],
    rows: list[Mapping[str, Any]],
    expected_input_set_sha256: str,
    identity_set_sha256: str,
    build_fingerprints: list[Mapping[str, Any]],
    blc_paths: list[str],
    source: str,
) -> dict[str, Any]:
    """Prove a verification from another input set describes this corpus exactly.

    Sound only when nothing the receipt observed can differ: the same selected
    logical files with the same bytes and physical identities, the same game
    build, the same asset roots, and the exporter binary as the only moved
    fingerprint. Anything else is a different corpus and fails closed.
    """

    def by_name(fingerprints: Any) -> dict[str, tuple[Any, str]]:
        if not isinstance(fingerprints, list):
            _fail("cursor-rebind-fingerprints-missing", source=source, expected="fingerprint list", actual=fingerprints)
        return {
            Path(str(row.get("path"))).name.casefold(): (row.get("length"), str(row.get("sha256", "")).upper())
            for row in fingerprints
        }

    source_provenance = source_corpus.get("provenance")
    if not isinstance(source_provenance, Mapping):
        _fail("cursor-rebind-source-provenance-missing", source=source, expected="provenance object", actual=source_provenance)
    old = by_name(source_provenance.get("buildFingerprints"))
    new = by_name(build_fingerprints)
    if set(old) != set(new) or EXPORTER_FINGERPRINT_NAME not in new:
        _fail("cursor-rebind-fingerprint-set-drift", source=source, expected=sorted(new), actual=sorted(old))
    moved = sorted(name for name in new if old[name] != new[name])
    if moved != [EXPORTER_FINGERPRINT_NAME]:
        _fail("cursor-rebind-not-exporter-only", source=source, expected=[EXPORTER_FINGERPRINT_NAME], actual=moved)
    if source_corpus.get("inputSetSha256") != verification.get("inputSetSha256"):
        _fail("cursor-rebind-source-input-set-mismatch", source=source, expected=verification.get("inputSetSha256"), actual=source_corpus.get("inputSetSha256"))
    if sorted(source_provenance.get("blcPaths") or []) != sorted(blc_paths):
        _fail("cursor-rebind-asset-root-drift", source=source, expected="identical BLC path set", actual="BLC path set differs")
    if source_corpus.get("identitySetSha256") != identity_set_sha256:
        _fail("cursor-rebind-identity-drift", source=source, expected=identity_set_sha256, actual=source_corpus.get("identitySetSha256"))
    old_files = {
        row.get("virtualPath"): (row.get("logicalSha256"), row.get("length"))
        for row in source_corpus.get("files") or []
    }
    new_files = {row["virtualPath"]: (row.get("logicalSha256"), row.get("length")) for row in rows}
    if old_files != new_files:
        changed = sorted(path for path in set(old_files) | set(new_files) if old_files.get(path) != new_files.get(path))
        _fail("cursor-rebind-logical-file-drift", source=source, expected="identical logical bytes", actual=changed[:8])
    return {
        "status": "exporter-only-rebinding",
        "fromInputSetSha256": verification.get("inputSetSha256"),
        "toInputSetSha256": expected_input_set_sha256.upper(),
        "movedFingerprint": {
            "name": EXPORTER_FINGERPRINT_NAME,
            "from": {"length": old[EXPORTER_FINGERPRINT_NAME][0], "sha256": old[EXPORTER_FINGERPRINT_NAME][1]},
            "to": {"length": new[EXPORTER_FINGERPRINT_NAME][0], "sha256": new[EXPORTER_FINGERPRINT_NAME][1]},
        },
        "unchanged": {
            "identitySetSha256": identity_set_sha256,
            "logicalFiles": len(new_files),
            "buildFingerprints": sorted(name for name in new if name != EXPORTER_FINGERPRINT_NAME),
            "blcPaths": len(blc_paths),
        },
        "evidenceBoundary": (
            "The receipt was observed under another input set. The selected "
            "logical files, their bytes and physical identities, the game build "
            "and the asset roots are identical; only the exporter binary moved. "
            "A fresh capture under the current input set supersedes this."
        ),
    }


def _apply_verified_terminal_selection(
    rows: list[dict[str, Any]],
    *,
    verification_path: Path,
    expected_input_set_sha256: str,
    identity_set_sha256: str,
    build_fingerprints: list[Mapping[str, Any]],
    blc_paths: list[str] | None = None,
    allow_exporter_rebind: bool = False,
) -> dict[str, Any]:
    """Replay and apply a hash-pinned runtime terminal selection to this corpus."""
    try:
        verification_raw = verification_path.read_bytes()
        verification = json.loads(verification_raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _fail("cursor-verification-unreadable", source=str(verification_path), expected="valid JSON", actual=str(exc))
    if not isinstance(verification, dict):
        _fail("cursor-verification-not-object", source=str(verification_path), expected="JSON object", actual=type(verification).__name__)
    if (
        verification.get("schema") != CURSOR_VERIFICATION_SCHEMA
        or verification.get("status") != "complete"
        or verification.get("summary", {}).get("wholeSchemaExact") is not False
    ):
        _fail("cursor-verification-gate-failed", source=str(verification_path), expected="complete bounded verification", actual={"schema": verification.get("schema"), "status": verification.get("status")})
    rebinding_required = verification.get("inputSetSha256") != expected_input_set_sha256.upper()
    if rebinding_required and not allow_exporter_rebind:
        _fail("cursor-verification-input-set-mismatch", source=str(verification_path), expected=expected_input_set_sha256.upper(), actual=verification.get("inputSetSha256"))
    provenance = verification.get("provenance")
    if not isinstance(provenance, Mapping):
        _fail("cursor-verification-provenance-missing", source=str(verification_path), expected="provenance object", actual=provenance)
    receipt, receipt_path = _load_exact_json_provenance(provenance.get("receipt"), label="cursor receipt")
    source_corpus, source_corpus_path = _load_exact_json_provenance(
        provenance.get("corpusReport"), label="cursor source corpus"
    )
    native_context, native_context_path = _load_exact_json_provenance(
        provenance.get("nativeContext"), label="cursor native context"
    )
    _verifier_source, verifier_source_path = _load_exact_json_provenance(
        provenance.get("verifier"), label="cursor verifier", decode_json=False
    )
    if verifier_source_path != Path(__file__).with_name("skill_cursor_receipt.py").resolve():
        _fail("cursor-verifier-path-mismatch", source=str(verification_path), expected=str(Path(__file__).with_name("skill_cursor_receipt.py").resolve()), actual=str(verifier_source_path))
    required_paths = verification.get("summary", {}).get("requiredLogicalPaths")
    if not isinstance(required_paths, list) or not all(isinstance(value, str) for value in required_paths):
        _fail("cursor-required-paths-invalid", source=str(verification_path), expected="string array", actual=required_paths)
    replayed = verify_skilldata_cursor_capture(
        receipt,
        corpus_report_path=source_corpus_path,
        native_context_path=native_context_path,
        required_logical_paths=required_paths,
        receipt_path=receipt_path,
        receipt_sha256=str(provenance["receipt"]["sha256"]),
    )
    if replayed != verification:
        _fail("cursor-verification-replay-mismatch", source=str(verification_path), expected="exact verifier replay", actual="report bytes decode to a different result")
    if source_corpus.get("identitySetSha256") != identity_set_sha256:
        _fail("cursor-corpus-identity-drift", source=str(source_corpus_path), expected=identity_set_sha256, actual=source_corpus.get("identitySetSha256"))
    recorded_identity = provenance.get("corpusReport", {}).get("identitySetSha256")
    if recorded_identity != identity_set_sha256:
        _fail("cursor-provenance-identity-drift", source=str(verification_path), expected=identity_set_sha256, actual=recorded_identity)
    rebinding = None
    if rebinding_required:
        rebinding = _exporter_only_rebinding(
            verification=verification,
            source_corpus=source_corpus,
            rows=rows,
            expected_input_set_sha256=expected_input_set_sha256,
            identity_set_sha256=identity_set_sha256,
            build_fingerprints=build_fingerprints,
            blc_paths=list(blc_paths or []),
            source=str(verification_path),
        )
    native_hashes = verification.get("nativeInputs")
    installed_hashes = {
        Path(str(row.get("path"))).name.casefold(): str(row.get("sha256", "")).upper()
        for row in build_fingerprints
    }
    expected_native = {
        "gameAssemblySha256": installed_hashes.get("gameassembly.dll"),
        "metadataSha256": installed_hashes.get("global-metadata.dat"),
    }
    if native_hashes != expected_native:
        _fail("cursor-native-input-drift", source=str(verification_path), expected=expected_native, actual=native_hashes)
    contract = verification.get("terminalSelectionContract")
    expected_kinds = [row[3] for row in TERMINAL_FIELD_CONTRACT]
    if (
        not isinstance(contract, Mapping)
        or contract.get("candidateEncoding") != "one-member-wrapper"
        or contract.get("rejectedAlternativeEncoding") != "counted"
        or contract.get("fieldStartIndex") != 43
        or contract.get("fieldEndIndex") != 47
        or contract.get("memberKinds") != expected_kinds
        or contract.get("wholeSchemaExact") is not False
    ):
        _fail("cursor-terminal-contract-mismatch", source=str(verification_path), expected="field43..47 one-member-wrapper", actual=contract)
    all_rows = verification.get("rows")
    if not isinstance(all_rows, list):
        _fail("cursor-sample-set-invalid", source=str(verification_path), expected="row list", actual=type(all_rows).__name__)
    # Only the required samples are applied. A receipt may also carry
    # supplemental observations (the 568-byte nonempty-ActionGroup lane); they
    # are verified by the receipt checker but stay unpromoted here until their
    # own profile is reviewed. A verification with no named requirement keeps
    # the original rule of exactly two samples.
    if required_paths:
        sample_rows = [row for row in all_rows if row.get("logicalPath") in set(required_paths)]
        if sorted(row.get("logicalPath") for row in sample_rows) != sorted(required_paths):
            _fail("cursor-sample-set-invalid", source=str(verification_path), expected=sorted(required_paths),
                  actual=sorted(str(row.get("logicalPath")) for row in sample_rows))
    else:
        sample_rows = all_rows
        if len(sample_rows) != 2:
            _fail("cursor-sample-set-invalid", source=str(verification_path), expected="two required samples", actual=len(sample_rows))
    for sample in sample_rows:
        alternatives = sample.get("candidateAlternatives", [])
        fields = sample.get("runtimeFieldRanges", [])
        field43 = next((field for field in fields if field.get("fieldIndex") == 43), None)
        field47 = next((field for field in fields if field.get("fieldIndex") == 47), None)
        if (
            sample.get("boundaryClass") != "exact-closed"
            or len(alternatives) != 2
            or alternatives[0].get("encoding") != "one-member-wrapper"
            or alternatives[0].get("selected") is not True
            or alternatives[1].get("encoding") != "counted"
            or alternatives[1].get("selected") is not False
            or not isinstance(field43, Mapping)
            or not isinstance(field47, Mapping)
            or alternatives[0].get("start") != field43.get("start")
            or alternatives[0].get("end") != field47.get("end")
            or field47.get("end") != sample.get("hardLimit")
        ):
            _fail("cursor-sample-selection-invalid", source=str(sample.get("logicalPath")), expected="field43 through field47 selected to EOF", actual=sample)

    rows_by_path = {row["virtualPath"]: row for row in rows}
    expected_names = MEMORYPACK_FIELD_SCHEMAS["SkillData"]
    observer = native_context.get("selectedSkillDataReaderOrder", {}).get("runtimeCursorObserver", {})
    observed_fields = observer.get("fieldCallsites")
    inline_field = observer.get("inlineField")
    observed_action_group_children = observer.get("actionGroupChildCallsites")
    if (
        not isinstance(observed_fields, list)
        or [(item.get("fieldIndex"), item.get("fieldName")) for item in observed_fields]
        != [(index, name) for index, name in enumerate(expected_names) if index != 17]
        or not isinstance(inline_field, Mapping)
        or (inline_field.get("fieldIndex"), inline_field.get("fieldName")) != (17, expected_names[17])
    ):
        _fail(
            "skill-field-order-native-context-drift",
            source=str(native_context_path),
            expected="current 48-field SkillData reader order",
            actual={"directCount": len(observed_fields) if isinstance(observed_fields, list) else None, "inline": inline_field},
        )
    if (
        not isinstance(observed_action_group_children, list)
        or [
            (item.get("childIndex"), item.get("fieldName"))
            for item in observed_action_group_children
            if isinstance(item, Mapping)
        ] != [(0, "passiveEventActions"), (1, "timelineActions")]
    ):
        _fail(
            "skill-action-group-order-native-context-drift",
            source=str(native_context_path),
            expected=[(0, "passiveEventActions"), (1, "timelineActions")],
            actual=observed_action_group_children,
        )
    for sample in sample_rows:
        path = sample.get("logicalPath")
        corpus_row = rows_by_path.get(path)
        candidate = corpus_row.get("emptyActionGroupProfile") if isinstance(corpus_row, Mapping) else None
        runtime_ranges = sample.get("runtimeFieldRanges")
        candidate_fields = candidate.get("namedFields") if isinstance(candidate, Mapping) else None
        if (
            not isinstance(candidate_fields, list)
            or candidate.get("status") != "exact-through-field-42"
            or not isinstance(runtime_ranges, list)
        ):
            _fail(
                "skill-empty-action-group-sample-profile-missing",
                source=str(path),
                expected="exact fields 0 through 42",
                actual=candidate,
            )
        expected_sample_ranges = [
            {key: field.get(key) for key in ("fieldIndex", "fieldName", "start", "end")}
            for field in runtime_ranges
            if isinstance(field, Mapping) and 0 <= field.get("fieldIndex", -1) <= 42
        ]
        actual_sample_ranges = [
            {key: field.get(key) for key in ("fieldIndex", "fieldName", "start", "end")}
            for field in candidate_fields
        ]
        if actual_sample_ranges != expected_sample_ranges:
            _fail(
                "skill-empty-action-group-sample-cursor-mismatch",
                source=str(path),
                expected=expected_sample_ranges,
                actual=actual_sample_ranges,
            )

    terminal_names = [row[1] for row in TERMINAL_FIELD_CONTRACT]
    for row in rows:
        candidates = row.get("framing", {}).get("candidates", [])
        if len(candidates) != 2:
            _fail("skill-terminal-candidate-count-drift", source=row["virtualPath"], expected=2, actual=len(candidates))
        selected, rejected = candidates
        selected_start = int(selected.get("startOffset", "-1"), 0)
        rejected_start = int(rejected.get("startOffset", "-1"), 0)
        selected_end = int(selected.get("endOffset", "-1"), 0)
        selected_kinds = [member.get("kind") for member in selected.get("members", [])]
        rejected_kinds = [member.get("kind") for member in rejected.get("members", [])]
        if (
            selected.get("encoding") != "one-member-wrapper"
            or rejected.get("encoding") != "counted"
            or selected_kinds != expected_kinds
            or rejected_kinds != expected_kinds
            or rejected_start != selected_start + 1
            or selected_end != row["length"]
            or int(rejected.get("endOffset", "-1"), 0) != row["length"]
        ):
            _fail("skill-terminal-shape-drift", source=row["virtualPath"], expected="shared field43..47 candidate pair", actual={"encodings": [selected.get("encoding"), rejected.get("encoding")], "memberKinds": [selected_kinds, rejected_kinds], "starts": [selected_start, rejected_start], "end": selected_end})
        named_ranges = []
        for (field_index, field_name, _target, _kind), member in zip(TERMINAL_FIELD_CONTRACT, selected["members"]):
            span = member["range"]
            named_ranges.append({
                "fieldIndex": field_index,
                "fieldName": field_name,
                "start": span["start"],
                "end": span["end"],
                "kind": member["kind"],
                "evidence": "native-reader-aligned-terminal-field",
            })
        selected["selected"] = True
        selected["boundaryClass"] = "selected-terminal"
        selected["semanticFieldNamesStatus"] = "named-by-authenticated-reader-alignment"
        rejected["selected"] = False
        rejected["boundaryClass"] = "rejected-alternative"
        for index, coverage in enumerate(row.get("candidateCoverage", [])):
            coverage["selected"] = index == 0
        row["boundaryClass"] = "structural-prefix"
        row["coverageStatus"] = VERIFIED_TERMINAL_COVERAGE
        row["byteRanges"] = [*row.get("byteRanges", []), *named_ranges]
        row["opaqueByteRanges"] = list(selected.get("opaqueByteRanges", []))
        row["terminalSelection"] = {
            "status": "verified-native-reader-alignment",
            "candidateIndex": 0,
            "encoding": "one-member-wrapper",
            "start": selected_start,
            "end": selected_end,
            "fieldStartIndex": 43,
            "fieldEndIndex": 47,
            "namedFields": terminal_names,
            "wholeSchemaExact": False,
        }
        timeline_profile = row.get("timelinePlayAnimationProfile")
        timeline_profile_key = "timelinePlayAnimationProfile"
        timeline_profile_kind = "play-animation"
        timeline_profile_raw_status = "exact-first-timeline-play-animation-record"
        timeline_profile_verified_status = "verified-exact-first-timeline-play-animation-record"
        timeline_prefix_coverage = VERIFIED_TIMELINE_PLAY_ANIMATION_PREFIX
        timeline_exact_coverage = VERIFIED_TIMELINE_PLAY_ANIMATION_EXACT
        timeline_opaque_kind = "opaque-after-first-timeline-action-record"
        if not isinstance(timeline_profile, Mapping):
            timeline_profile = row.get("timelinePlayAnimationStepProfile")
            timeline_profile_key = "timelinePlayAnimationStepProfile"
            timeline_profile_kind = "play-animation-step"
            timeline_profile_raw_status = (
                "exact-first-timeline-play-animation-step-record"
            )
            timeline_profile_verified_status = (
                "verified-exact-first-timeline-play-animation-step-record"
            )
            timeline_prefix_coverage = VERIFIED_TIMELINE_PLAY_ANIMATION_STEP_PREFIX
            timeline_exact_coverage = VERIFIED_TIMELINE_PLAY_ANIMATION_STEP_EXACT
        if not isinstance(timeline_profile, Mapping):
            timeline_profile = row.get("timelineSharedSequenceProfile")
            timeline_profile_key = "timelineSharedSequenceProfile"
            timeline_profile_kind = "shared-sequence"
            timeline_profile_raw_status = (
                "exact-first-timeline-shared-sequence-record"
            )
            timeline_profile_verified_status = (
                "verified-exact-first-timeline-shared-sequence-record"
            )
            timeline_prefix_coverage = VERIFIED_TIMELINE_SHARED_SEQUENCE_PREFIX
            timeline_exact_coverage = VERIFIED_TIMELINE_SHARED_SEQUENCE_EXACT
        if not isinstance(timeline_profile, Mapping):
            timeline_profile = row.get("timelineCreateBuffProfile")
            timeline_profile_key = "timelineCreateBuffProfile"
            timeline_profile_kind = "create-buff"
            raw_status = (
                timeline_profile.get("status")
                if isinstance(timeline_profile, Mapping) else None
            )
            if raw_status == "exact-first-timeline-create-buff-action":
                timeline_profile_raw_status = raw_status
                timeline_profile_verified_status = (
                    "verified-exact-first-timeline-create-buff-action"
                )
                timeline_prefix_coverage = VERIFIED_TIMELINE_CREATE_BUFF_ACTION_PREFIX
                timeline_opaque_kind = "opaque-after-first-sequence-action"
            else:
                timeline_profile_raw_status = (
                    "exact-first-timeline-create-buff-record"
                )
                timeline_profile_verified_status = (
                    "verified-exact-first-timeline-create-buff-record"
                )
                timeline_prefix_coverage = VERIFIED_TIMELINE_CREATE_BUFF_RECORD_PREFIX
            timeline_exact_coverage = VERIFIED_TIMELINE_CREATE_BUFF_EXACT
        if not isinstance(timeline_profile, Mapping):
            timeline_profile = row.get("timelineFindTargetProfile")
            timeline_profile_key = "timelineFindTargetProfile"
            timeline_profile_kind = "find-target"
            timeline_profile_raw_status = "exact-first-timeline-find-target-record"
            timeline_profile_verified_status = "verified-exact-first-timeline-find-target-record"
            timeline_prefix_coverage = VERIFIED_TIMELINE_FIND_TARGET_PREFIX
            timeline_exact_coverage = VERIFIED_TIMELINE_FIND_TARGET_EXACT
        if not isinstance(timeline_profile, Mapping):
            timeline_profile = row.get("timelineContinuousFindTargetProfile")
            timeline_profile_key = "timelineContinuousFindTargetProfile"
            timeline_profile_kind = "continuous-find-target"
            timeline_profile_raw_status = (
                "exact-first-timeline-continuous-find-target-record"
            )
            timeline_profile_verified_status = (
                "verified-exact-first-timeline-continuous-find-target-record"
            )
            timeline_prefix_coverage = VERIFIED_TIMELINE_CONTINUOUS_FIND_TARGET_PREFIX
            timeline_exact_coverage = VERIFIED_TIMELINE_CONTINUOUS_FIND_TARGET_EXACT
        if isinstance(timeline_profile, Mapping):
            if timeline_profile.get("status") != timeline_profile_raw_status:
                _fail(
                    f"skill-timeline-{timeline_profile_kind}-status-drift",
                    source=row["virtualPath"],
                    expected=timeline_profile_raw_status,
                    actual=timeline_profile.get("status"),
                )
            profile_cursor = timeline_profile.get("parserCursor")
            profile_ranges = timeline_profile.get("namedRanges")
            if type(profile_cursor) is not int or not isinstance(profile_ranges, list):
                _fail(
                    f"skill-timeline-{timeline_profile_kind}-profile-missing",
                    source=row["virtualPath"],
                    expected="exact cursor and named ranges",
                    actual=timeline_profile,
                )
            range_cursor = 0
            promoted_nested_ranges = []
            for span in profile_ranges:
                start, end, name = span.get("start"), span.get("end"), span.get("name")
                if (
                    type(start) is not int
                    or type(end) is not int
                    or not isinstance(name, str)
                    or start != range_cursor
                    or end <= start
                    or end > profile_cursor
                ):
                    _fail(
                        f"skill-timeline-{timeline_profile_kind}-range-drift",
                        source=row["virtualPath"],
                        expected={"start": range_cursor, "endAtMost": profile_cursor},
                        actual=span,
                    )
                promoted_nested_ranges.append({
                    "start": start,
                    "end": end,
                    "kind": name,
                    "evidence": f"authenticated-current-timeline-{timeline_profile_kind}-reader",
                })
                range_cursor = end
            if range_cursor != profile_cursor or profile_cursor > selected_start:
                _fail(
                    f"skill-timeline-{timeline_profile_kind}-cursor-drift",
                    source=row["virtualPath"],
                    expected={"rangeEnd": profile_cursor, "terminalStartAtLeast": profile_cursor},
                    actual={"rangeEnd": range_cursor, "terminalStart": selected_start},
                )
            _promote_action_group_prefix(row)
            row["byteRanges"] = [*promoted_nested_ranges, *named_ranges]
            row["opaqueByteRanges"] = ([] if profile_cursor == selected_start else [{
                "start": profile_cursor,
                "end": selected_start,
                "kind": timeline_opaque_kind,
            }])
            row["parserCursor"] = profile_cursor
            row["boundaryContext"]["parserCursor"] = profile_cursor
            row["coverageStatus"] = timeline_prefix_coverage
            row[timeline_profile_key] = {
                **timeline_profile,
                "status": timeline_profile_verified_status,
                "newNamedBytesAfterPriorPrefix": profile_cursor - 10,
            }

            continuation = timeline_profile.get("topLevelContinuation")
            if (
                isinstance(continuation, Mapping)
                and continuation.get("status") == PARTIAL_TOP_LEVEL_CONTINUATION
            ):
                # The reader stopped at a top-level field it cannot frame yet.
                # The verified prefix above still holds; the partial
                # continuation is kept as recorded and promotes nothing.
                continuation = None
            if continuation is not None:
                fields = continuation.get("namedFields") if isinstance(continuation, Mapping) else None
                if (
                    not isinstance(fields, list)
                    or continuation.get("status") != "exact-through-field-42"
                    or continuation.get("parserCursor") != selected_start
                ):
                    _fail(
                        f"skill-timeline-{timeline_profile_kind}-continuation-drift",
                        source=row["virtualPath"],
                        expected="exact fields 0 through 42 ending at selected terminal",
                        actual=continuation,
                    )
                field_cursor = 1
                promoted_fields = []
                for expected_index, field in enumerate(fields):
                    start, end = field.get("start"), field.get("end")
                    if (
                        field.get("fieldIndex") != expected_index
                        or field.get("fieldName") != expected_names[expected_index]
                        or start != field_cursor
                        or type(end) is not int
                        or end <= start
                        or end > selected_start
                    ):
                        _fail(
                            f"skill-timeline-{timeline_profile_kind}-top-level-range-drift",
                            source=row["virtualPath"],
                            expected={"fieldIndex": expected_index, "start": field_cursor},
                            actual=field,
                        )
                    promoted_fields.append({
                        **field,
                        "evidence": f"authenticated-current-timeline-{timeline_profile_kind}-and-wrapper-reader",
                    })
                    field_cursor = end
                if field_cursor != selected_start:
                    _fail(
                        f"skill-timeline-{timeline_profile_kind}-top-level-cursor-drift",
                        source=row["virtualPath"],
                        expected=selected_start,
                        actual=field_cursor,
                    )
                row["byteRanges"] = [
                    {"start": 0, "end": 1, "kind": "SkillData.member-count"},
                    *promoted_fields,
                    *named_ranges,
                ]
                row["opaqueByteRanges"] = []
                row["parserCursor"] = selected_end
                row["boundaryContext"]["parserCursor"] = selected_end
                row["boundaryClass"] = "exact-closed"
                row["coverageStatus"] = timeline_exact_coverage
                row["wholeSchemaExact"] = True
                row["framing"]["wholeSchemaExact"] = True
                row["terminalSelection"]["wholeSchemaExact"] = True
                row[timeline_profile_key]["topLevelContinuation"] = {
                    **continuation,
                    "status": "verified-exact-through-field-42",
                }
            continue
        profile = row.get("emptyActionGroupProfile")
        if not isinstance(profile, Mapping) or profile.get("status") == "not-applicable":
            if isinstance(profile, Mapping) and profile.get("status") == "not-applicable":
                _promote_action_group_prefix(row)
            continue
        profile_fields = profile.get("namedFields")
        if not isinstance(profile_fields, list) or not profile_fields:
            _fail("skill-empty-profile-fields-missing", source=row["virtualPath"], expected="non-empty field ranges", actual=profile_fields)
        expected_index = 0
        profile_cursor = 1
        promoted_fields = []
        for field in profile_fields:
            field_index = field.get("fieldIndex")
            start, end = field.get("start"), field.get("end")
            if (
                field_index != expected_index
                or field.get("fieldName") != expected_names[field_index]
                or type(start) is not int
                or type(end) is not int
                or start != profile_cursor
                or end <= start
                or end > selected_start
            ):
                _fail(
                    "skill-empty-profile-range-drift",
                    source=row["virtualPath"],
                    expected={"fieldIndex": expected_index, "start": profile_cursor, "endAtMost": selected_start},
                    actual=field,
                )
            promoted_fields.append({
                **field,
                "evidence": "runtime-sample-authenticated-current-wrapper-reader",
            })
            profile_cursor = end
            expected_index += 1
        if profile.get("parserCursor") != profile_cursor:
            _fail("skill-empty-profile-cursor-drift", source=row["virtualPath"], expected=profile_cursor, actual=profile.get("parserCursor"))
        row["byteRanges"] = [
            {"start": 0, "end": 1, "kind": "SkillData.member-count"},
            *promoted_fields,
            *named_ranges,
        ]
        opaque_gap = [] if profile_cursor == selected_start else [{
            "start": profile_cursor,
            "end": selected_start,
            "kind": "opaque-unsupported-switchToBuffConfig-remainder",
        }]
        row["opaqueByteRanges"] = opaque_gap
        row["parserCursor"] = selected_end if not opaque_gap else profile_cursor
        row["boundaryContext"]["parserCursor"] = row["parserCursor"]
        row["emptyActionGroupProfile"] = {
            **profile,
            "status": (
                "verified-exact-through-field-42"
                if not opaque_gap else "verified-exact-through-field-41"
            ),
            "evidenceBoundary": (
                "The accepted runtime receipt authenticates the exact field-0 through field-42 cursor on two byte-distinct empty-ActionGroupData samples. "
                "The current wrapper/type-driven reader is generalized only to rows with the identical empty field-0 representation and fails closed at unsupported nested unions."
            ),
        }
        if not opaque_gap:
            row["boundaryClass"] = "exact-closed"
            row["coverageStatus"] = VERIFIED_EMPTY_ACTION_GROUP_EXACT
            row["wholeSchemaExact"] = True
            row["framing"]["wholeSchemaExact"] = True
            row["terminalSelection"]["wholeSchemaExact"] = True
        else:
            row["boundaryClass"] = "structural-prefix"
            row["coverageStatus"] = VERIFIED_EMPTY_ACTION_GROUP_PARTIAL
    return {
        "path": verification_path.resolve().as_posix(),
        "length": len(verification_raw),
        "sha256": hashlib.sha256(verification_raw).hexdigest().upper(),
        "sourceCorpus": dict(provenance["corpusReport"]),
        "receipt": dict(provenance["receipt"]),
        "nativeContext": dict(provenance["nativeContext"]),
        "verifier": dict(provenance["verifier"]),
        **({"rebinding": rebinding} if rebinding is not None else {}),
    }


def _join_and_frame(
    ledger_rows: list[Mapping[str, Any]],
    stream_rows: list[Mapping[str, Any]],
    *,
    stderr: str,
    expected_input_set_sha256: str,
) -> tuple[list[dict[str, Any]], dict[str, int], dict[str, int]]:
    ledger_by_path = {str(row["virtualPath"]): row for row in ledger_rows}
    seen: set[str] = set()
    results: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    coverage_counts: Counter[str] = Counter()
    for index, stream_row in enumerate(stream_rows):
        path = stream_row.get("fileName")
        if not isinstance(path, str) or path not in ledger_by_path:
            _fail("unexpected-stream-identity", source=f"stream[{index}].fileName", expected="selected ledger identity", actual=path)
        if path in seen:
            _fail("duplicate-stream-identity", source=f"stream[{index}]", actual=path)
        seen.add(path)
        ledger = ledger_by_path[path]
        if stream_row.get("blockType") != "JsonData" or stream_row.get("blockTypeValue") != 19:
            _fail("stream-block-mismatch", source=path, expected=["JsonData", 19], actual=[stream_row.get("blockType"), stream_row.get("blockTypeValue")])
        length = _require_int(stream_row.get("length"), source=f"stream:{path}.length", minimum=1)
        encoded = stream_row.get("dataBase64")
        if not isinstance(encoded, str):
            _fail("stream-base64-missing", source=path, actual=type(encoded).__name__)
        try:
            data = base64.b64decode(encoded, validate=True)
        except ValueError as exc:
            _fail("stream-base64-invalid", source=path, actual=str(exc))
        if length != len(data) or length != ledger["length"]:
            _fail("stream-length-mismatch", source=path, expected=ledger["length"], actual={"declared": length, "decoded": len(data)})
        actual_md5 = hashlib.md5(data).hexdigest().upper()
        if actual_md5 != ledger["recomputedFileDataMd5"]:
            _fail("stream-ledger-md5-mismatch", source=path, expected=ledger["recomputedFileDataMd5"], actual=actual_md5)
        identity_result = {
            "inputSetSha256": str(ledger["inputSetSha256"]).upper(),
            "virtualPath": path,
            "blockName": ledger["blockName"],
            "blockTypeValue": ledger["blockTypeValue"],
            "length": length,
            "logicalMd5": actual_md5,
            "logicalSha256": hashlib.sha256(data).hexdigest().upper(),
            "physicalChunkPath": ledger["physicalChunkPath"],
            "physicalChunkSource": ledger["physicalChunkSource"],
            "metadataProvenance": ledger["metadataProvenance"],
            "overlayState": ledger["overlayState"],
            "chunkOverlayState": ledger["chunkOverlayState"],
            "physicalOffset": ledger["offset"],
            "encrypted": ledger["encrypted"],
        }
        common_prefix = None
        framed = None
        try:
            common_prefix = frame_skill_common_prefix(data)
            framed = frame_skill_memorypack(data, source=path)
        except Exception as exc:
            coverage_counts["failed-framing"] += 1
            prefix_end = int(common_prefix["cursorOffset"], 0) if common_prefix is not None else 0
            prefix_ranges = _prefix_byte_ranges(common_prefix) if common_prefix is not None else []
            hard_limit = len(data)
            opaque = [{"start": prefix_end, "end": hard_limit, "kind": "opaque-after-failed-frame"}] if prefix_end < hard_limit else []
            results.append({
                **identity_result,
                "boundaryClass": "failed",
                "boundaryContext": {
                    "inputSetSha256": identity_result["inputSetSha256"],
                    "logicalFileIdentity": path,
                    "logicalSha256": identity_result["logicalSha256"],
                    "startOffset": 0,
                    "hardLimit": hard_limit,
                    "parserCursor": prefix_end if common_prefix is not None else None,
                },
                "parserCursor": prefix_end if common_prefix is not None else None,
                "hardLimit": hard_limit,
                "byteRanges": prefix_ranges,
                "opaqueByteRanges": opaque,
                "commonPrefixFraming": common_prefix,
                "coverageStatus": "failed-framing",
                "framingFailure": {
                    "code": "skill-framer-failed",
                    "source": path,
                    "offset": "0x0",
                    "expected": "valid maintained SkillData structural profile",
                    "actual": f"{type(exc).__name__}: {exc}",
                },
                "wholeSchemaExact": False,
            })
            continue
        status_counts[framed["status"]] += 1
        empty_action_group_profile = None
        if framed.get("candidates"):
            empty_action_group_profile = frame_skill_empty_action_group_profile(
                data,
                int(framed["candidates"][0]["startOffset"], 0),
            )
        timeline_play_animation_profile = None
        if len(data) >= 23 and data[20:23] == b"\xFA\x15\x01":
            try:
                timeline_play_animation_profile = decode_first_timeline_play_animation(
                    data,
                    input_set_sha256=expected_input_set_sha256,
                )
            except ValueError as exc:
                _fail(
                    "skill-timeline-play-animation-profile-failed",
                    source=path,
                    expected="exact current tag-0x0115 first TimelineActionData",
                    actual=str(exc),
                )
            if timeline_play_animation_profile.get("wholeActionGroupDataExact"):
                candidate_start = int(framed["candidates"][0]["startOffset"], 0)
                continuation = frame_skill_exact_timeline_action_group_profile(
                    data,
                    candidate_start,
                    action_group_end=timeline_play_animation_profile["parserCursor"],
                )
                timeline_play_animation_profile["topLevelContinuation"] = continuation
        timeline_play_animation_step_profile = None
        if len(data) >= 23 and data[20:23] == b"\xFA\x16\x01":
            try:
                timeline_play_animation_step_profile = (
                    decode_first_timeline_play_animation_step(
                        data,
                        input_set_sha256=expected_input_set_sha256,
                    )
                )
            except ValueError as exc:
                _fail(
                    "skill-timeline-play-animation-step-profile-failed",
                    source=path,
                    expected="exact current tag-0x0116 first TimelineActionData",
                    actual=str(exc),
                )
            if timeline_play_animation_step_profile.get("wholeActionGroupDataExact"):
                candidate_start = int(framed["candidates"][0]["startOffset"], 0)
                continuation = frame_skill_exact_timeline_action_group_profile(
                    data,
                    candidate_start,
                    action_group_end=timeline_play_animation_step_profile["parserCursor"],
                )
                timeline_play_animation_step_profile["topLevelContinuation"] = continuation
        timeline_create_buff_profile = None
        if (
            len(data) >= 22
            and data[0] == 48
            and data[1] == 2
            and int.from_bytes(data[2:6], "little", signed=True) == 0
            and int.from_bytes(data[6:10], "little", signed=True) > 0
            and data[10] == 4
            and data[15] == 3
            and data[20] == 0x92
            and int.from_bytes(data[16:20], "little", signed=True) > 0
        ):
            try:
                timeline_create_buff_profile = decode_first_timeline_create_buff(
                    data,
                    input_set_sha256=expected_input_set_sha256,
                )
            except ValueError as exc:
                _fail(
                    "skill-timeline-create-buff-profile-failed",
                    source=path,
                    expected="exact current tag-0x0092 first CreateBuff action",
                    actual=str(exc),
                )
            if timeline_create_buff_profile.get("wholeActionGroupDataExact"):
                candidate_start = int(framed["candidates"][0]["startOffset"], 0)
                continuation = frame_skill_exact_timeline_action_group_profile(
                    data,
                    candidate_start,
                    action_group_end=timeline_create_buff_profile["parserCursor"],
                )
                timeline_create_buff_profile["topLevelContinuation"] = continuation
        timeline_shared_sequence_profile = None
        try:
            timeline_shared_sequence_profile = decode_first_timeline_shared_sequence(
                data,
                input_set_sha256=expected_input_set_sha256,
            )
        except ValueError:
            # The shared decoder is intentionally sparse. Non-contracted roots,
            # later action tags, and member-count drift retain the established
            # ActionGroupData prefix without turning the corpus run into a
            # family-wide failure.
            timeline_shared_sequence_profile = None
        if (
            timeline_shared_sequence_profile is not None
            and timeline_shared_sequence_profile.get("wholeActionGroupDataExact")
        ):
            candidate_start = int(framed["candidates"][0]["startOffset"], 0)
            continuation = frame_skill_exact_timeline_action_group_profile(
                data,
                candidate_start,
                action_group_end=timeline_shared_sequence_profile["parserCursor"],
            )
            timeline_shared_sequence_profile["topLevelContinuation"] = continuation
        timeline_find_target_profile = None
        if (
            len(data) >= 22
            and data[20] == 0xB2
            and int.from_bytes(data[16:20], "little", signed=True) == 1
        ):
            try:
                timeline_find_target_profile = decode_first_timeline_find_target(
                    data,
                    input_set_sha256=expected_input_set_sha256,
                )
            except ValueError:
                # The current contract intentionally covers only authenticated
                # selector subtype routes. Other tag-B2 bodies retain the
                # already verified ActionGroupData prefix and stay opaque.
                timeline_find_target_profile = None
        timeline_continuous_find_target_profile = None
        if (
            len(data) >= 22
            and data[20] == 0x8A
            and int.from_bytes(data[16:20], "little", signed=True) == 1
        ):
            try:
                timeline_continuous_find_target_profile = (
                    decode_first_timeline_continuous_find_target(
                        data,
                        input_set_sha256=expected_input_set_sha256,
                    )
                )
                if timeline_continuous_find_target_profile.get("wholeActionGroupDataExact"):
                    candidate_start = int(framed["candidates"][0]["startOffset"], 0)
                    continuation = frame_skill_exact_timeline_action_group_profile(
                        data,
                        candidate_start,
                        action_group_end=timeline_continuous_find_target_profile[
                            "parserCursor"
                        ],
                    )
                    timeline_continuous_find_target_profile[
                        "topLevelContinuation"
                    ] = continuation
            except ValueError:
                # Only the exact current selector subtype routes in the
                # byte-pinned contract are promoted.
                timeline_continuous_find_target_profile = None
        prefix_end = int(common_prefix["cursorOffset"], 0)
        prefix_ranges = _prefix_byte_ranges(common_prefix)
        common_prefix["parserCursor"] = prefix_end
        common_prefix["hardLimit"] = len(data)
        common_prefix["byteRanges"] = prefix_ranges
        candidate_coverage: list[dict[str, Any]] = []
        has_overlap = False
        for candidate_index, candidate in enumerate(framed["candidates"]):
            candidate_start = int(candidate["startOffset"], 0)
            overlap = candidate_start < prefix_end
            has_overlap = has_overlap or overlap
            candidate_coverage.append({
                "candidateIndex": candidate_index,
                "prefixCertifiedRange": {"start": 0, "end": prefix_end, "endExclusive": True},
                "terminalCertifiedRange": {"start": candidate_start, "end": len(data), "endExclusive": True},
                "rangesOverlap": overlap,
                "opaqueGap": None if overlap else {
                    "start": prefix_end,
                    "end": candidate_start,
                    "length": candidate_start - prefix_end,
                },
            })
        if has_overlap:
            coverage_status = "unsupported-overlapping-independent-ranges"
        elif framed["candidateCount"] == 0:
            coverage_status = "unsupported-no-terminal-candidate"
        elif framed["candidateCount"] > 1:
            coverage_status = "ambiguous-disjoint-independent-ranges"
        else:
            coverage_status = "unique-disjoint-independent-ranges"
        if coverage_status == "ambiguous-disjoint-independent-ranges":
            boundary_class = "ambiguous"
        elif coverage_status.startswith("unsupported-"):
            boundary_class = "unsupported"
        else:
            # The candidate grammar is bounded and EOF-anchored, but no
            # independent formatter cursor promotes it to an exact record.
            boundary_class = "structural-prefix"
        candidate_opaque_ranges: list[list[dict[str, Any]]] = []
        for candidate_index, candidate in enumerate(framed["candidates"]):
            candidate_start = int(candidate["startOffset"], 0)
            candidate_end = int(candidate.get("endOffset", hex(len(data))), 0)
            gap = candidate_coverage[candidate_index]["opaqueGap"]
            opaque_ranges = [] if gap is None else [{
                "start": gap["start"],
                "end": gap["end"],
                "kind": "opaque-between-prefix-and-terminal-candidate",
            }]
            if candidate_end < len(data):
                opaque_ranges.append({
                    "start": candidate_end,
                    "end": len(data),
                    "kind": "opaque-after-terminal-candidate",
                })
            candidate["boundaryClass"] = boundary_class
            candidate["candidateRange"] = {"start": candidate_start, "end": candidate_end, "endExclusive": True}
            candidate["parserCursor"] = candidate_end
            candidate["hardLimit"] = len(data)
            candidate["byteRanges"] = _candidate_byte_ranges(candidate)
            candidate["opaqueByteRanges"] = opaque_ranges
            candidate["boundaryContext"] = {
                "inputSetSha256": identity_result["inputSetSha256"],
                "logicalFileIdentity": path,
                "logicalSha256": identity_result["logicalSha256"],
                "startOffset": candidate_start,
                "hardLimit": len(data),
                "parserCursor": candidate_end,
                "candidateRange": [candidate_start, candidate_end],
            }
            candidate_opaque_ranges.append(opaque_ranges)
        if boundary_class == "ambiguous":
            gaps = [candidate_coverage[index]["opaqueGap"] for index in range(len(candidate_coverage))]
            common_gap = None
            if gaps and all(gap is not None for gap in gaps):
                common_start = max(gap["start"] for gap in gaps)
                common_end = min(gap["end"] for gap in gaps)
                if common_start < common_end:
                    common_gap = {"start": common_start, "end": common_end, "kind": "opaque-common-to-all-candidates"}
            row_opaque = [common_gap] if common_gap is not None else []
        elif boundary_class == "unsupported":
            row_opaque = [{"start": prefix_end, "end": len(data), "kind": "opaque-after-structural-prefix"}] if prefix_end < len(data) else []
        elif candidate_opaque_ranges:
            row_opaque = candidate_opaque_ranges[0]
        else:
            row_opaque = [{"start": prefix_end, "end": len(data), "kind": "opaque-after-structural-prefix"}] if prefix_end < len(data) else []
        row_context = {
            "inputSetSha256": identity_result["inputSetSha256"],
            "logicalFileIdentity": path,
            "logicalSha256": identity_result["logicalSha256"],
            "startOffset": 0,
            "hardLimit": len(data),
            "parserCursor": prefix_end,
        }
        common_prefix["boundaryContext"] = row_context
        for candidate, coverage in zip(framed["candidates"], candidate_coverage):
            coverage["boundaryContext"] = candidate["boundaryContext"]
            coverage["opaqueByteRanges"] = candidate["opaqueByteRanges"]
        coverage_counts[coverage_status] += 1
        results.append({
            **identity_result,
            "boundaryClass": boundary_class,
            "boundaryContext": row_context,
            "parserCursor": prefix_end,
            "hardLimit": len(data),
            "byteRanges": prefix_ranges,
            "opaqueByteRanges": row_opaque,
            "commonPrefixFraming": common_prefix,
            "emptyActionGroupProfile": empty_action_group_profile,
            "timelinePlayAnimationProfile": timeline_play_animation_profile,
            "timelinePlayAnimationStepProfile": timeline_play_animation_step_profile,
            "timelineCreateBuffProfile": timeline_create_buff_profile,
            "timelineSharedSequenceProfile": timeline_shared_sequence_profile,
            "timelineFindTargetProfile": timeline_find_target_profile,
            "timelineContinuousFindTargetProfile": timeline_continuous_find_target_profile,
            "framing": framed,
            "coverageStatus": coverage_status,
            "candidateCoverage": candidate_coverage,
            "wholeSchemaExact": False,
        })
    missing = sorted(set(ledger_by_path) - seen)
    if missing:
        _fail("stream-missing-identities", source="AnimeStudio stream", expected=len(ledger_by_path), actual={"count": len(seen), "firstMissing": missing[:10]})
    matches = re.findall(r"(?m)^Streamed ([0-9]+) files\s*$", stderr)
    if len(matches) != 1 or int(matches[0]) != len(stream_rows):
        _fail("stream-terminal-count-mismatch", source="AnimeStudio stream stderr", expected=len(stream_rows), actual={"matches": matches, "stderrTail": stderr[-1000:]})
    return (
        sorted(results, key=lambda row: row["virtualPath"]),
        dict(sorted(status_counts.items())),
        dict(sorted(coverage_counts.items())),
    )


def build_current_census(
    *,
    outer_path: Path,
    ledger_path: Path,
    cli_path: Path,
    expected_input_set_sha256: str,
    max_files: int | None = None,
    output_path: Path | None = None,
    output_md_path: Path | None = None,
    cursor_verification_path: Path | None = None,
    allow_exporter_rebind: bool = False,
) -> dict[str, Any]:
    if max_files is not None:
        _require_int(max_files, source="maxFiles", minimum=1)
    if output_path is not None and output_md_path is not None:
        _guard_output_path(output_path, [output_md_path])
    outer, _header, file_rows, provenance_start = _read_outer_and_ledger(
        outer_path, ledger_path, expected_input_set_sha256=expected_input_set_sha256
    )
    all_skill_rows = _skill_rows(file_rows, expected_input=expected_input_set_sha256.upper())
    selected = all_skill_rows if max_files is None else all_skill_rows[:max_files]
    partial = max_files is not None
    chunk_selection_start = _chunk_selection_snapshot(selected, outer)
    selected_chunks_start = _chunk_fingerprints(selected)
    stream_tool_start = _stream_tool_snapshot(cli_path)
    cli_key = os.path.normcase(str(cli_path.resolve()))
    authenticated_build_paths = {
        os.path.normcase(str(Path(row["path"]).resolve()))
        for row in provenance_start["buildFingerprints"]
    }
    if cli_key not in authenticated_build_paths:
        _fail("stream-cli-not-in-outer-build-fingerprints", source=str(cli_path.resolve()),
              expected=sorted(authenticated_build_paths), actual=cli_key)
    parser_start = _parser_source_snapshots(Path(__file__))
    gate_start = _fingerprint(Path(__file__))
    timeline_contract_paths = [
        TIMELINE_PLAY_ANIMATION_CONTRACT_PATH,
        TIMELINE_PLAY_ANIMATION_CONTRACT_PATH.with_name("buff_115_native.json"),
        TIMELINE_PLAY_ANIMATION_STEP_CONTRACT_PATH,
        TIMELINE_CREATE_BUFF_CONTRACT_PATH,
        TIMELINE_CREATE_BUFF_CONTRACT_PATH.with_name("buff_92_native.json"),
        TIMELINE_FIND_TARGET_CONTRACT_PATH,
        TIMELINE_FIND_TARGET_CONTRACT_PATH.with_name("buff_b2_native.json"),
        TIMELINE_CONTINUOUS_FIND_TARGET_CONTRACT_PATH,
        TIMELINE_CONTINUOUS_FIND_TARGET_CONTRACT_PATH.with_name("buff_8a_native.json"),
        TIMELINE_SHARED_SEQUENCE_CONTRACT_PATH,
        *[
            TIMELINE_SHARED_SEQUENCE_CONTRACT_PATH.with_name(name)
            for name in (
                "buff_0b_native.json", "buff_24_native.json", "buff_3c_native.json",
                "buff_8c_native.json", "buff_92_native.json",
                "buff_9a_native.json", "buff_a2_native.json", "buff_a9_native.json",
                "buff_b2_native.json", "buff_b4_native.json", "buff_b6_native.json",
                "buff_c0_native.json", "buff_d4_native.json", "buff_de_native.json", "buff_fe_native.json",
                "buff_9b_native.json", "buff_ea_native.json", "buff_119_native.json",
                "buff_145_native.json", "buff_166_native.json", "buff_169_native.json",
                "buff_16d_native.json",
            )
        ],
    ]
    timeline_contract_start = [_fingerprint(path) for path in timeline_contract_paths]
    timeline_native_validation = validate_timeline_play_animation_native_contract()
    timeline_play_animation_step_native_validation = (
        validate_timeline_play_animation_step_native_contract()
    )
    timeline_create_buff_native_validation = validate_timeline_create_buff_native_contract()
    timeline_find_target_native_validation = validate_timeline_find_target_native_contract()
    timeline_continuous_find_target_native_validation = (
        validate_timeline_continuous_find_target_native_contract()
    )
    timeline_shared_sequence_native_validation = (
        validate_timeline_shared_sequence_native_contract()
    )
    outputs = [path for path in (output_path, output_md_path) if path is not None]
    if outputs:
        protected = [outer_path, ledger_path, Path(__file__),
                     Path(outer["primaryAssets"]), Path(outer["fallbackAssets"])]
        if cursor_verification_path is not None:
            protected.append(cursor_verification_path)
        # Outputs must not damage unselected format families either. Retain
        # all ledger chunk paths for collision checks without hashing them.
        chunk_paths = sorted({str(row.get("physicalChunkPath")) for row in file_rows
                              if row.get("physicalChunkPath")})
        vfs_roots = [(Path(outer[field]) / "VFS").resolve()
                     for field in ("primaryAssets", "fallbackAssets")]
        for raw_path in chunk_paths:
            chunk_path = Path(raw_path).resolve()
            if not any(chunk_path.is_relative_to(root) for root in vfs_roots):
                _fail("ledger-chunk-outside-input-roots", source=raw_path,
                      expected=[str(root) for root in vfs_roots], actual=str(chunk_path))
            protected.append(chunk_path)
        protected.extend(Path(row["path"]) for row in provenance_start["sourceFingerprints"])
        protected.extend(Path(row["path"]) for row in provenance_start["buildFingerprints"])
        protected.extend(Path(row["path"]) for row in stream_tool_start)
        protected.extend(Path(row["path"]) for row in selected_chunks_start)
        protected.extend(Path(row["path"]) for row in parser_start)
        protected.extend(timeline_contract_paths)
        for output in outputs:
            if partial:
                _guard_partial_output(output)
            _guard_output_path(output, protected + [path for path in outputs if path != output])
    command = _stream_command(cli_path, outer, selected, partial=partial)
    stream_rows, stderr = _read_stream_rows(command)
    rows, status_counts, coverage_counts = _join_and_frame(
        selected,
        stream_rows,
        stderr=stderr,
        expected_input_set_sha256=expected_input_set_sha256,
    )

    _outer_end, _header_end, end_file_rows, provenance_end = _read_outer_and_ledger(
        outer_path, ledger_path, expected_input_set_sha256=expected_input_set_sha256
    )
    end_skill_rows = _skill_rows(end_file_rows, expected_input=expected_input_set_sha256.upper())
    if [row["virtualPath"] for row in end_skill_rows] != [row["virtualPath"] for row in all_skill_rows]:
        _fail("skill-ledger-set-drift", source=str(ledger_path), expected=len(all_skill_rows), actual=len(end_skill_rows))
    stream_tool_end = _stream_tool_snapshot(cli_path)
    selected_chunks_end = _chunk_fingerprints(selected)
    chunk_selection_end = _chunk_selection_snapshot(selected, outer)
    parser_end = _parser_source_snapshots(Path(__file__))
    gate_end = _fingerprint(Path(__file__))
    timeline_contract_end = [_fingerprint(path) for path in timeline_contract_paths]
    if provenance_start != provenance_end:
        _fail("outer-provenance-drift", source=str(outer_path), expected=provenance_start, actual=provenance_end)
    if stream_tool_start != stream_tool_end:
        _fail("stream-tool-drift", source=str(cli_path), expected=stream_tool_start, actual=stream_tool_end)
    if selected_chunks_start != selected_chunks_end:
        _fail("selected-chunk-drift", source="SkillData physical chunks", expected=selected_chunks_start, actual=selected_chunks_end)
    if chunk_selection_start != chunk_selection_end:
        _fail("chunk-overlay-selection-drift", source="SkillData chunk selection", expected=chunk_selection_start, actual=chunk_selection_end)
    if parser_start != parser_end or gate_start != gate_end:
        _fail("code-drift", source="SkillData census code", expected={"parser": parser_start, "corpusGate": gate_start}, actual={"parser": parser_end, "corpusGate": gate_end})
    if timeline_contract_start != timeline_contract_end:
        _fail(
            "skill-timeline-contract-drift",
            source=str(TIMELINE_PLAY_ANIMATION_CONTRACT_PATH),
            expected=timeline_contract_start,
            actual=timeline_contract_end,
        )
    for output in outputs:
        _guard_output_path(output, protected + [path for path in outputs if path != output])

    identity_rows = [
        {key: row[key] for key in (
            "virtualPath", "blockTypeValue", "length", "logicalMd5", "logicalSha256",
            "physicalChunkPath", "physicalChunkSource", "metadataProvenance", "overlayState",
            "chunkOverlayState", "physicalOffset", "encrypted",
        )}
        for row in rows
    ]
    identity_set_sha256 = _canonical_sha256(identity_rows)
    cursor_verification_provenance = None
    if cursor_verification_path is not None:
        cursor_verification_provenance = _apply_verified_terminal_selection(
            rows,
            verification_path=cursor_verification_path,
            expected_input_set_sha256=expected_input_set_sha256,
            identity_set_sha256=identity_set_sha256,
            build_fingerprints=provenance_start["buildFingerprints"],
            blc_paths=provenance_start["blcPaths"],
            allow_exporter_rebind=allow_exporter_rebind,
        )
        parser_after_verification = _parser_source_snapshots(Path(__file__))
        gate_after_verification = _fingerprint(Path(__file__))
        if parser_start != parser_after_verification or gate_start != gate_after_verification:
            _fail("code-drift", source="SkillData cursor integration", expected={"parser": parser_start, "corpusGate": gate_start}, actual={"parser": parser_after_verification, "corpusGate": gate_after_verification})
        for label in ("sourceCorpus", "receipt", "nativeContext", "verifier"):
            recorded = cursor_verification_provenance[label]
            actual = _fingerprint(Path(recorded["path"]))
            if actual["length"] != recorded["length"] or actual["sha256"] != recorded["sha256"]:
                _fail("cursor-input-drift", source=label, expected=recorded, actual=actual)
        actual_verification = _fingerprint(cursor_verification_path)
        if (
            actual_verification["length"] != cursor_verification_provenance["length"]
            or actual_verification["sha256"] != cursor_verification_provenance["sha256"]
        ):
            _fail("cursor-verification-drift", source=str(cursor_verification_path), expected=cursor_verification_provenance, actual=actual_verification)
    coverage_counts = dict(sorted(Counter(row.get("coverageStatus", "failed-framing") for row in rows).items()))
    unique_count = (
        coverage_counts.get("unique-disjoint-independent-ranges", 0)
        + coverage_counts.get(VERIFIED_TERMINAL_COVERAGE, 0)
        + coverage_counts.get(VERIFIED_ACTION_GROUP_PREFIX_COVERAGE, 0)
        + coverage_counts.get(VERIFIED_EMPTY_ACTION_GROUP_EXACT, 0)
        + coverage_counts.get(VERIFIED_EMPTY_ACTION_GROUP_PARTIAL, 0)
        + coverage_counts.get(VERIFIED_TIMELINE_PLAY_ANIMATION_PREFIX, 0)
        + coverage_counts.get(VERIFIED_TIMELINE_PLAY_ANIMATION_EXACT, 0)
        + coverage_counts.get(VERIFIED_TIMELINE_PLAY_ANIMATION_STEP_PREFIX, 0)
        + coverage_counts.get(VERIFIED_TIMELINE_PLAY_ANIMATION_STEP_EXACT, 0)
        + coverage_counts.get(VERIFIED_TIMELINE_CREATE_BUFF_ACTION_PREFIX, 0)
        + coverage_counts.get(VERIFIED_TIMELINE_CREATE_BUFF_RECORD_PREFIX, 0)
        + coverage_counts.get(VERIFIED_TIMELINE_CREATE_BUFF_EXACT, 0)
        + coverage_counts.get(VERIFIED_TIMELINE_FIND_TARGET_PREFIX, 0)
        + coverage_counts.get(VERIFIED_TIMELINE_FIND_TARGET_EXACT, 0)
        + coverage_counts.get(VERIFIED_TIMELINE_CONTINUOUS_FIND_TARGET_PREFIX, 0)
        + coverage_counts.get(VERIFIED_TIMELINE_CONTINUOUS_FIND_TARGET_EXACT, 0)
        + coverage_counts.get(VERIFIED_TIMELINE_SHARED_SEQUENCE_PREFIX, 0)
        + coverage_counts.get(VERIFIED_TIMELINE_SHARED_SEQUENCE_EXACT, 0)
    )
    ambiguous_count = coverage_counts.get("ambiguous-disjoint-independent-ranges", 0)
    failed_count = coverage_counts.get("failed-framing", 0)
    unsupported_count = len(rows) - unique_count - ambiguous_count - failed_count
    boundary_evidence = _boundary_evidence_summary(rows)
    final_status = "failed" if failed_count else "partial" if partial else "complete"
    return {
        "format": SKILL_REPORT_FORMAT,
        "schemaVersion": 1,
        "status": final_status,
        "publicationEligible": not partial and failed_count == 0,
        "inputSetSha256": expected_input_set_sha256.upper(),
        "provenance": {
            **provenance_start,
            "combinedOuterFingerprintCount": len(provenance_start["sourceFingerprints"]) + len(provenance_start["buildFingerprints"]),
            "streamToolFingerprints": stream_tool_start,
            "selectedChunkFingerprints": selected_chunks_start,
            "selectedChunkResolution": chunk_selection_start,
            "parser": parser_start,
            "corpusGate": gate_start,
            "cursorVerification": cursor_verification_provenance,
            "timelinePlayAnimationContracts": timeline_contract_start,
            "timelinePlayAnimationNativeValidation": timeline_native_validation,
            "timelinePlayAnimationStepNativeValidation": (
                timeline_play_animation_step_native_validation
            ),
            "timelineCreateBuffNativeValidation": timeline_create_buff_native_validation,
            "timelineFindTargetNativeValidation": timeline_find_target_native_validation,
            "timelineContinuousFindTargetNativeValidation": (
                timeline_continuous_find_target_native_validation
            ),
            "timelineSharedSequenceNativeValidation": (
                timeline_shared_sequence_native_validation
            ),
        },
        "summary": {
            "ledgerSkillFiles": len(all_skill_rows),
            "filesSelected": len(selected),
            "filesSucceeded": len(rows) - failed_count,
            "filesFailed": failed_count,
            "filesUnique": unique_count,
            "filesAmbiguous": ambiguous_count,
            "filesUnsupported": unsupported_count,
            "logicalBytes": sum(row["length"] for row in rows),
            "physicalChunkCount": len({row["physicalChunkPath"] for row in rows}),
            "framingStatusCounts": status_counts,
            "coverageStatusCounts": coverage_counts,
            "byteBoundaryEvidence": boundary_evidence,
        },
        "identitySetSha256": identity_set_sha256,
        "wholeSchemaExact": False,
        "evidenceBoundary": (
            "current outer-ledger identities plus AnimeStudio stream --verify-md5 decrypted bytes; "
            "the maintained framer proves the 48-member envelope and EOF terminal shapes. When cursorVerification "
            "is present, its exact receipt/corpus/native/verifier replay selects the one-member-wrapper terminal "
            "as fields 43 through 47 for every row with the same authenticated candidate pair. It also names "
            "the field-0 ActionGroupData member and child-list count prefix through the first positive list. "
            "The remaining intervening action bodies stay opaque unless an executed cursor authenticates them"
        ),
        "files": rows,
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    summary = report["summary"]
    selected_terminal_files = summary["byteBoundaryEvidence"].get("selectedTerminalFiles", 0)
    lines = [
        "# SkillData current VFS corpus", "",
        f"Status: `{report['status']}`; inputSetSha256: `{report['inputSetSha256']}`.", "",
        f"Selected: {summary['filesSelected']}/{summary['ledgerSkillFiles']}; "
        f"successful: {summary['filesSucceeded']}; failed: {summary['filesFailed']}; "
        f"unsupported: {summary['filesUnsupported']}.",
        f"Unique supported candidates: {summary['filesUnique']}; "
        f"ambiguous: {summary['filesAmbiguous']}; logical bytes: {summary['logicalBytes']}.", "",
        "Boundary evidence: "
        f"exact closed records {summary['byteBoundaryEvidence']['exactClosedRecords']}; "
        f"files with structural prefixes {summary['byteBoundaryEvidence']['filesWithStructuralPrefix']}; "
        f"ambiguous {summary['byteBoundaryEvidence']['ambiguousFiles']}; "
        f"unsupported {summary['byteBoundaryEvidence']['unsupportedFiles']}; "
        f"failed {summary['byteBoundaryEvidence']['failedFiles']}; "
        f"opaque bytes by candidate {summary['byteBoundaryEvidence']['opaqueBytesByCandidate']}; "
        f"opaque bytes at file level {summary['byteBoundaryEvidence']['opaqueBytesAtFileLevel']}.", "",
        "Authenticated ActionGroupData named prefixes: "
        f"{summary['byteBoundaryEvidence'].get('namedActionGroupPrefixFiles', 0)} files / "
        f"{summary['byteBoundaryEvidence'].get('namedActionGroupPrefixBytes', 0)} bytes.", "",
        report["evidenceBoundary"], "",
        (
            "The authenticated cursor receipt selects fields 43 through 47 through EOF; "
            "the current native reader also names field 0 and its ordered child-list counts. "
            "Positive list bodies remain bounded at their first record."
            if selected_terminal_files
            else "A candidate is not an independently proven formatter start. "
                 "Whole-schema exactness and field semantics remain unresolved."
        ), "",
        "Full identities, hashes, ranges and source gates are in the companion JSON.", "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outer-summary", type=Path, default=DEFAULT_OUTER)
    parser.add_argument("--outer-ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--animestudio-cli", type=Path, default=DEFAULT_CLI)
    parser.add_argument("--expected-input-set-sha256", required=True)
    parser.add_argument("--max-files", type=int)
    parser.add_argument(
        "--cursor-verification", type=Path,
        help="complete SkillData cursor verification report to replay and apply fail-closed",
    )
    parser.add_argument(
        "--allow-exporter-rebind", action="store_true",
        help=(
            "accept a verification recorded under another input set when only the "
            "AnimeStudio.CLI fingerprint moved and every selected logical file, "
            "game-build fingerprint and asset root is identical"
        ),
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--output-md", type=Path)
    args = parser.parse_args(argv)
    try:
        result = build_current_census(
            outer_path=args.outer_summary,
            ledger_path=args.outer_ledger,
            cli_path=args.animestudio_cli,
            expected_input_set_sha256=args.expected_input_set_sha256,
            max_files=args.max_files,
            output_path=args.output,
            output_md_path=args.output_md,
            cursor_verification_path=args.cursor_verification,
            allow_exporter_rebind=args.allow_exporter_rebind,
        )
        if args.output_md is not None:
            if args.max_files is not None:
                _guard_partial_output(args.output_md)
            protected = [args.output, args.outer_summary, args.outer_ledger]
            provenance = result["provenance"]
            for field in ("sourceFingerprints", "buildFingerprints", "streamToolFingerprints",
                          "selectedChunkFingerprints", "parser"):
                protected.extend(Path(row["path"]) for row in provenance[field])
            _guard_output_path(args.output_md, protected)
            args.output_md.parent.mkdir(parents=True, exist_ok=True)
            descriptor, temporary = tempfile.mkstemp(dir=args.output_md.parent, suffix=".tmp")
            try:
                with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                    handle.write(render_markdown(result))
                os.replace(temporary, args.output_md)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
        # JSON is the final publication marker after the optional Markdown.
        _atomic_write_json(args.output, result)
    except Exception as exc:
        diagnostic = exc.diagnostic if isinstance(exc, CensusGateError) else {
            "code": "unexpected-error", "source": "skilldata-current-census", "offset": None,
            "expected": None, "actual": f"{type(exc).__name__}: {exc}",
        }
        print(json.dumps({"status": "failed", "diagnostic": diagnostic}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps({"status": result["status"], "files": result["summary"]["filesSucceeded"], "output": str(args.output)}, ensure_ascii=False))
    return 1 if result["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
