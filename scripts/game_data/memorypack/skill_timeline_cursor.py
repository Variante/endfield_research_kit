"""Join current SkillData VFS bytes to bounded TimelineActionData candidates.

The report keeps the maintained SkillData parser cursor separate from the
conditional native-reader candidate. It requires a complete current AnimeStudio
stream and the exact-build IL2CPP context report; candidate prefixes never
count as closed records.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import struct
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

from scripts.game_data.il2cpp_context_audit import (
    GA_SHA,
    MD_SHA,
    _skilldata_continue_following_play_animation_candidate,
    _skilldata_continue_timeline_parent_candidate,
    _skilldata_read_following_timeline_action_data_prefix_candidate,
    _skilldata_sequence_tail_windows,
    _skilldata_verified_byte_payload_reader,
    skilldata_action_union_c9_prefix_reader_evidence,
    skilldata_action_union_static_reader_evidence,
    skilldata_timeline_branch_sample_witness,
    skilldata_timeline_branch_static_alignment,
)
from scripts.game_data.memorypack.buff_actions import (
    FrameError as BuffActionFrameError,
    Reader as BuffActionReader,
)
from scripts.game_data.memorypack.skill_corpus import (
    SKILL_REPORT_FORMAT,
    verify_current_report_inputs,
)


from scripts.repo_paths import REPO_ROOT
from scripts.common import sha256_file_upper as _sha256_file

ROOT = REPO_ROOT
DEFAULT_CORPUS = ROOT / 'reports/animestudio/skilldata_current_latest.json'
DEFAULT_NATIVE = ROOT / 'reports/animestudio/il2cpp_context_current_latest.json'
DEFAULT_BUFF = ROOT / 'reports/animestudio/buffdata_current_latest.json'
DEFAULT_JSON = ROOT / 'reports/animestudio/skilldata_timeline_cursor_latest.json'
DEFAULT_MD = ROOT / 'reports/animestudio/skilldata_timeline_cursor_latest.md'
SKILL_PREFIX = 'Data/Json/SkillData/'
ACTION_CONTRACT_RE = re.compile(r'^buff_([0-9a-f]+)_native[.]json$', re.IGNORECASE)
IMAGE_BASE_FALLBACK = 0x180000000


class TimelineCursorError(ValueError):
    """The supplied current corpus, native context or stream did not join."""


def _selected_action_reader_candidate(raw: bytes, start: int, hard_limit: int, *,
                                      tag: int, reader_contract: Mapping[str, Any],
                                      routes: Mapping[str, Any], image_base: int,
                                      source: str) -> dict[str, Any]:
    """Replay one selected action reader inside this file's explicit limit.

    The current registered route and native reader contract are checked before
    the independent structural action parser is allowed to move its cursor.
    An unsupported nested tag remains at its first byte.
    """
    if (type(start) is not int or type(hard_limit) is not int or
            not 0 <= start <= hard_limit <= len(raw)):
        raise TimelineCursorError(
            f'{source}: selected action start/limit is outside current bytes: '
            f'{start!r}, {hard_limit!r}, {len(raw)}')
    if type(tag) is not int or not 0 <= tag <= 0xFFFF:
        raise TimelineCursorError(f'{source}: selected action tag is invalid: {tag!r}')

    reader_evidence = skilldata_action_union_static_reader_evidence(
        tag, dict(reader_contract), dict(routes),
        gameassembly_image_base=image_base, source=source)
    member_count = reader_evidence.get('rootMemberCount')
    if type(member_count) is not int or not 0 <= member_count <= 0xFF:
        raise TimelineCursorError(
            f'{source}: 0x{tag:04X} native root member count is invalid: {member_count!r}')

    tag_bytes = (b'\xFA' + struct.pack('<H', tag)) if tag >= 0xFA else bytes((tag,))
    if len(tag_bytes) > hard_limit - start:
        return {
            'tag': tag, 'start': start, 'cursor': start, 'complete': False,
            'status': 'truncated-selected-action-union-tag', 'failure': {
                'category': 'truncated', 'offset': start,
                'expectedBytes': len(tag_bytes), 'remainingBytes': hard_limit - start,
            }, 'ranges': [], 'opaquePayloadByteRanges': [],
            'readerEvidence': reader_evidence, 'recordEndCandidate': None,
        }
    actual_tag = raw[start:start + len(tag_bytes)]
    if actual_tag != tag_bytes:
        return {
            'tag': tag, 'start': start, 'cursor': start, 'complete': False,
            'status': 'stopped-before-mismatched-action-union-tag', 'failure': {
                'category': 'ambiguous', 'offset': start,
                'expectedHex': tag_bytes.hex().upper(),
                'actualHex': actual_tag.hex().upper(),
            }, 'ranges': [], 'opaquePayloadByteRanges': [],
            'readerEvidence': reader_evidence, 'recordEndCandidate': None,
        }

    union_range = {
        'start': start, 'end': start + len(tag_bytes),
        'kind': 'AbilityActionData.union-tag',
        'rawHex': tag_bytes.hex().upper(),
    }
    header_offset = start + len(tag_bytes)
    if header_offset >= hard_limit:
        return {
            'tag': tag, 'start': start, 'cursor': header_offset, 'complete': False,
            'status': 'truncated-selected-action-member-header', 'failure': {
                'category': 'truncated', 'offset': header_offset,
                'expectedBytes': 1, 'remainingBytes': 0,
            }, 'ranges': [union_range], 'opaquePayloadByteRanges': [],
            'readerEvidence': reader_evidence, 'recordEndCandidate': None,
        }
    actual_header = raw[header_offset]
    if actual_header not in (0xFF, member_count):
        return {
            'tag': tag, 'start': start, 'cursor': header_offset, 'complete': False,
            'status': 'stopped-before-selected-action-member-header', 'failure': {
                'category': 'member-count', 'offset': header_offset,
                'expected': member_count, 'actual': actual_header,
            }, 'ranges': [union_range], 'opaquePayloadByteRanges': [],
            'readerEvidence': reader_evidence, 'recordEndCandidate': None,
        }

    bounded = raw[start:hard_limit]
    parser = BuffActionReader(bounded, source, len(bounded))
    parse_error: BuffActionFrameError | None = None
    try:
        parser.action(0)
    except BuffActionFrameError as exc:
        parse_error = exc

    ranges = []
    relative_cursor = 0
    for span in parser.ranges:
        relative_start, relative_end = span.get('start'), span.get('end')
        if (type(relative_start) is not int or type(relative_end) is not int or
                relative_start != relative_cursor or
                not relative_start < relative_end <= parser.limit):
            raise TimelineCursorError(
                f'{source}: 0x{tag:04X} action-reader ranges are not contiguous/in-limit: {span!r}')
        absolute_start, absolute_end = start + relative_start, start + relative_end
        ranges.append({
            'start': absolute_start,
            'end': absolute_end,
            'kind': f"AbilityActionData.reader.{span.get('kind', 'anonymous-bytes')}",
            'rawHex': bounded[relative_start:relative_end].hex().upper(),
        })
        relative_cursor = relative_end
    if relative_cursor != parser.pos:
        raise TimelineCursorError(
            f'{source}: 0x{tag:04X} action-reader range cursor {relative_cursor} '
            f'differs from parser cursor {parser.pos}')

    opaque_payload_ranges = []
    for record in parser.records:
        if record.get('kind') != 'anonymous-byte-payload' or record.get('isNull'):
            continue
        payload_spans = [span for span in parser.ranges
                         if span.get('kind') == 'anonymous-length-prefixed-bytes' and
                         record.get('start', -1) < span.get('start', -1) < span.get('end', -1) <=
                         record.get('end', -1)]
        opaque_payload_ranges.extend({
            'start': start + span['start'], 'end': start + span['end'],
            'kind': 'AbilityActionData.reader.length-prefixed-opaque-payload',
        } for span in payload_spans)

    cursor = start + parser.pos
    failure = None
    record_end = None
    complete = parse_error is None
    if parse_error is not None:
        failure = dict(parse_error.diagnostic)
        if type(failure.get('offset')) is int:
            failure['offset'] += start
        source_category = failure.get('category')
        if source_category in ('union-tag', 'nested-profile', 'special-aim-shape-tag',
                               'depth-limit', 'unsupported-profile'):
            failure['sourceCategory'] = source_category
            failure['category'] = 'unsupported'
        category = failure.get('category')
        if category == 'unsupported':
            status = 'stopped-at-unsupported-action-subreader-tag'
        elif category == 'truncated':
            status = 'truncated-selected-action-reader-prefix'
        elif category in ('member-count', 'count-bounds', 'malformed'):
            status = 'malformed-selected-action-reader-prefix'
        else:
            status = 'stopped-at-action-reader-error'
    else:
        root_records = [row for row in parser.records
                        if row.get('kind') == 'union' and row.get('start') == 0]
        if (len(root_records) != 1 or root_records[0].get('tag') != tag or
                root_records[0].get('end') != parser.pos):
            raise TimelineCursorError(
                f'{source}: 0x{tag:04X} selected action reader did not close its root union: '
                f'{root_records!r}, cursor={parser.pos}')
        status = 'candidate-action-reader-member-sequence-exhausted'
        record_end = {
            'start': start, 'end': cursor, 'tag': tag,
            'memberCount': member_count,
            'sourceReadOrderKey': reader_evidence.get('rootReadOrderKey'),
            'contractFile': reader_evidence.get('contractFile'),
            'contractSha256': reader_evidence.get('contractSha256'),
            'classification': (
                'candidate selected action reader field-sequence end; '
                'runtime formatter/provider selection unobserved'),
        }
    return {
        'tag': tag, 'start': start, 'cursor': cursor, 'complete': complete,
        'status': status, 'failure': failure, 'ranges': ranges,
        'opaquePayloadByteRanges': opaque_payload_ranges,
        'readerEvidence': reader_evidence,
        'recordEndCandidate': record_end,
    }


def _validate_candidate_ranges(ranges: list[Mapping[str, Any]], *, start: int,
                               end: int, hard_limit: int, source: str) -> None:
    cursor = start
    for span in sorted(ranges, key=lambda row: (row.get('start', -1), row.get('end', -1))):
        span_start, span_end = span.get('start'), span.get('end')
        if (type(span_start) is not int or type(span_end) is not int or
                span_start != cursor or not cursor < span_end <= hard_limit):
            raise TimelineCursorError(
                f'{source}: candidate byte ranges do not tile [{start},{end}): {span!r}')
        cursor = span_end
    if cursor != end:
        raise TimelineCursorError(
            f'{source}: candidate range cursor {cursor} differs from declared end {end}')


def _merge_action_reader_ranges(alignment: dict[str, Any],
                                candidate: Mapping[str, Any], *,
                                source: str) -> tuple[bool, str | None]:
    """Join a selected action reader's bytes without duplicating old ranges."""
    action_start = candidate.get('start')
    reader_cursor = candidate.get('cursor')
    old_cursor = alignment.get('candidateCursor')
    candidate_start = alignment.get('candidateStart')
    hard_limit = alignment.get('hardLimit')
    existing = alignment.get('candidateByteRanges')
    reader_ranges = candidate.get('ranges')
    if (type(action_start) is not int or type(reader_cursor) is not int or
            type(old_cursor) is not int or type(candidate_start) is not int or
            type(hard_limit) is not int or not isinstance(existing, list) or
            not isinstance(reader_ranges, list)):
        raise TimelineCursorError(f'{source}: action reader candidate range metadata is incomplete')
    _validate_candidate_ranges(existing, start=candidate_start, end=old_cursor,
                               hard_limit=hard_limit, source=source)
    if reader_cursor < old_cursor:
        return False, 'reader stopped before the already recorded candidate cursor'
    _validate_candidate_ranges(reader_ranges, start=action_start, end=reader_cursor,
                               hard_limit=hard_limit, source=source)

    additions = []
    for span in reader_ranges:
        if span['end'] <= old_cursor:
            continue
        if span['start'] < old_cursor:
            return False, 'an action-reader scalar crosses the existing candidate cursor'
        additions.append(dict(span))
    if reader_cursor > old_cursor and (
            not additions or additions[0]['start'] != old_cursor):
        return False, 'the action-reader continuation does not begin at the candidate cursor'
    alignment['candidateByteRanges'].extend(additions)
    alignment['candidateByteRanges'].sort(
        key=lambda row: (row['start'], row['end']))
    alignment['candidateCursor'] = reader_cursor
    _validate_candidate_ranges(
        alignment['candidateByteRanges'], start=candidate_start, end=reader_cursor,
        hard_limit=hard_limit, source=source)
    return True, None


def _append_alignment_ranges(alignment: dict[str, Any], ranges: list[Mapping[str, Any]], *,
                             source: str, label: str) -> None:
    start = alignment.get('candidateCursor')
    candidate_start = alignment.get('candidateStart')
    hard_limit = alignment.get('hardLimit')
    all_ranges = alignment.get('candidateByteRanges')
    if (type(start) is not int or type(candidate_start) is not int or
            type(hard_limit) is not int or not isinstance(all_ranges, list)):
        raise TimelineCursorError(f'{source}: {label} has incomplete candidate range state')
    _validate_candidate_ranges(all_ranges, start=candidate_start, end=start,
                               hard_limit=hard_limit, source=source)
    cursor = start
    for span in ranges:
        span_start, span_end = span.get('start'), span.get('end')
        if (type(span_start) is not int or type(span_end) is not int or
                span_start != cursor or not cursor < span_end <= hard_limit):
            raise TimelineCursorError(
                f'{source}: {label} byte ranges do not continue at {cursor}: {span!r}')
        all_ranges.append(dict(span))
        cursor = span_end
    alignment['candidateCursor'] = cursor
    _validate_candidate_ranges(all_ranges, start=candidate_start, end=cursor,
                               hard_limit=hard_limit, source=source)


def _refresh_alignment_opaque_ranges(alignment: dict[str, Any]) -> None:
    cursor, hard_limit = alignment.get('candidateCursor'), alignment.get('hardLimit')
    if type(cursor) is not int or type(hard_limit) is not int or cursor > hard_limit:
        raise TimelineCursorError('candidate cursor is outside its hard limit')
    alignment['opaqueByteRanges'] = ([] if cursor == hard_limit else [{
        'start': cursor, 'end': hard_limit,
        'kind': 'unconsumed-timeline-actiongroup-and-skilldata-bytes',
    }])


def _continue_selected_action_parent(alignment: dict[str, Any], raw: bytes,
                                     candidate: Mapping[str, Any], *, role: str,
                                     sequence_action_count: int,
                                     timeline_actions_list_count: int,
                                     timeline_action_start: int,
                                     timeline_reader: Mapping[str, Any],
                                     sequence_reader: Mapping[str, Any],
                                     action_group_members: list[Mapping[str, Any]],
                                     payload_helper_evidence: Mapping[str, Any],
                                     bool_helper_evidence: Mapping[str, Any],
                                     image_base: int, source: str) -> dict[str, Any]:
    if alignment.get('candidateCursor') != candidate.get('cursor'):
        raise TimelineCursorError(
            f'{source}: action reader endpoint does not match the candidate cursor')
    sequence_tail_windows = _skilldata_sequence_tail_windows(
        sequence_reader, source=source)
    continuation = _skilldata_continue_timeline_parent_candidate(
        raw, int(candidate['cursor']), int(alignment['hardLimit']),
        sequence_action_count=sequence_action_count,
        timeline_actions_list_count=timeline_actions_list_count,
        timeline_action_start=timeline_action_start,
        timeline_reader=dict(timeline_reader),
        sequence_tail_windows=sequence_tail_windows,
        action_group_members=[dict(row) for row in action_group_members],
        payload_helper_evidence=dict(payload_helper_evidence),
        bool_helper_evidence=dict(bool_helper_evidence),
        gameassembly_image_base=image_base, source=source)
    _append_alignment_ranges(alignment, continuation['ranges'],
                             source=source, label=f'{role} TimelineActionData parent')
    alignment['candidateStatus'] = continuation['status']
    alignment['failure'] = continuation.get('failure')
    if role == 'first-timeline-sequence-action':
        alignment['candidateTimelineContinuation'] = continuation
        if isinstance(continuation.get('candidateTimelineActionDataRecordEnd'), Mapping):
            alignment['candidateTimelineActionDataRecordEnd'] = continuation[
                'candidateTimelineActionDataRecordEnd']
    else:
        alignment['candidateFollowingTimelineContinuation'] = continuation
        if isinstance(continuation.get('candidateTimelineActionDataRecordEnd'), Mapping):
            alignment['candidateFollowingTimelineActionDataRecordEnd'] = continuation[
                'candidateTimelineActionDataRecordEnd']
    if isinstance(continuation.get('candidateActionGroupDataRecordEnd'), Mapping):
        alignment['candidateActionGroupDataRecordEnd'] = continuation[
            'candidateActionGroupDataRecordEnd']
    alignment.setdefault('opaquePayloadByteRanges', []).extend(
        continuation.get('opaquePayloadByteRanges', []))
    _refresh_alignment_opaque_ranges(alignment)
    return continuation


def _add_following_timeline_prefix(alignment: dict[str, Any], raw: bytes, *,
                                   timeline_reader: Mapping[str, Any],
                                   sequence_reader: Mapping[str, Any],
                                   payload_helper_evidence: Mapping[str, Any],
                                   bool_helper_evidence: Mapping[str, Any],
                                   image_base: int, source: str) -> dict[str, Any]:
    prefix = _skilldata_read_following_timeline_action_data_prefix_candidate(
        raw, int(alignment['candidateCursor']), int(alignment['hardLimit']),
        timeline_reader=dict(timeline_reader), sequence_reader=dict(sequence_reader),
        payload_helper_evidence=dict(payload_helper_evidence),
        bool_helper_evidence=dict(bool_helper_evidence),
        gameassembly_image_base=image_base, source=source)
    _append_alignment_ranges(alignment, prefix['ranges'], source=source,
                             label='following TimelineActionData prefix')
    alignment['candidateFollowingTimelineActionDataPrefix'] = prefix
    alignment['candidateStatus'] = prefix['status']
    alignment['failure'] = prefix.get('failure')
    alignment.setdefault('opaquePayloadByteRanges', []).extend(
        prefix.get('opaquePayloadByteRanges', []))
    _refresh_alignment_opaque_ranges(alignment)
    return prefix


def _extend_selected_action(alignment: dict[str, Any], raw: bytes, *,
                            role: str, tag_peek: Mapping[str, Any],
                            action_readers: Mapping[int, Mapping[str, Any]],
                            routes: Mapping[str, Any], timeline_reader: Mapping[str, Any],
                            sequence_reader: Mapping[str, Any],
                            action_group_members: list[Mapping[str, Any]],
                            payload_helper_evidence: Mapping[str, Any],
                            bool_helper_evidence: Mapping[str, Any],
                            image_base: int, action_reader_sha256: str,
                            source: str) -> dict[str, Any] | None:
    tag = tag_peek.get('tag')
    if (type(tag) is not int or tag in (0x115, 0xC9) or tag not in action_readers):
        return None
    action_start = tag_peek.get('offset')
    if type(action_start) is not int:
        raise TimelineCursorError(f'{source}: selected action has no exact tag offset')
    expected_tag_bytes = ((b'\xFA' + struct.pack('<H', tag)) if tag >= 0xFA
                          else bytes((tag,)))
    if (tag_peek.get('tagWidth') != len(expected_tag_bytes) or
            str(tag_peek.get('encodingHex', '')).upper() != expected_tag_bytes.hex().upper()):
        raise TimelineCursorError(
            f'{source}: action tag peek disagrees with its selected 0x{tag:04X} encoding')
    reader_candidate = _selected_action_reader_candidate(
        raw, action_start, int(alignment['hardLimit']), tag=tag,
        reader_contract=action_readers[tag], routes=routes,
        image_base=image_base, source=source)
    accepted, reason = _merge_action_reader_ranges(
        alignment, reader_candidate, source=source)
    attempt = {
        'role': role,
        'tag': f'0x{tag:04X}',
        'readRange': {'start': action_start, 'hardLimit': alignment['hardLimit']},
        'parserCursor': reader_candidate['cursor'],
        'complete': reader_candidate['complete'],
        'status': reader_candidate['status'],
        'failure': reader_candidate.get('failure'),
        'candidateRecordEnd': reader_candidate.get('recordEndCandidate'),
        'contractFile': reader_candidate['readerEvidence'].get('contractFile'),
        'contractSha256': reader_candidate['readerEvidence'].get('contractSha256'),
        'actionReaderSource': 'scripts/game_data/memorypack/buff_actions.py',
        'actionReaderSha256': action_reader_sha256,
        'rangeAccepted': accepted,
        'rangeAcceptanceReason': reason,
    }
    alignment.setdefault('candidateActionReaderCandidates', []).append(attempt)
    if not accepted:
        return reader_candidate

    alignment.setdefault('opaquePayloadByteRanges', []).extend(
        reader_candidate.get('opaquePayloadByteRanges', []))
    if not reader_candidate['complete']:
        alignment['candidateStatus'] = reader_candidate['status']
        alignment['failure'] = reader_candidate.get('failure')
        stop = {
            'tag': tag, 'start': action_start,
            'end': alignment['candidateCursor'],
            'nextSourceReadType': 'selected action reader remaining source field or nested tag',
            'nextSourceReadOffset': alignment['candidateCursor'],
            'nextSourceReadConsumed': False,
            'classification': 'candidate selected action reader prefix; action and parents remain open',
        }
        if role == 'first-timeline-sequence-action':
            alignment['candidateActionPrefixStop'] = stop
        else:
            alignment['candidateFollowingActionPrefixStop'] = stop
        _refresh_alignment_opaque_ranges(alignment)
        return reader_candidate

    sequence_count = (alignment.get('firstSequenceActionDataCount')
                      if role == 'first-timeline-sequence-action' else
                      (alignment.get('candidateFollowingTimelineActionDataPrefix') or {}).get(
                          'timelineSequenceCount'))
    timeline_count = alignment.get('timelineActionsListCount')
    timeline_start = (alignment.get('candidateStart')
                      if role == 'first-timeline-sequence-action' else
                      (alignment.get('candidateFollowingTimelineActionDataPrefix') or {}).get('start'))
    if type(sequence_count) is not int or type(timeline_count) is not int or type(timeline_start) is not int:
        raise TimelineCursorError(
            f'{source}: selected action parent counts/identity are incomplete: '
            f'{sequence_count!r}, {timeline_count!r}, {timeline_start!r}')
    if role == 'following-timeline-sequence-action':
        timeline_count -= 1
    continuation = _continue_selected_action_parent(
        alignment, raw, reader_candidate, role=role,
        sequence_action_count=sequence_count,
        timeline_actions_list_count=timeline_count,
        timeline_action_start=timeline_start,
        timeline_reader=timeline_reader, sequence_reader=sequence_reader,
        action_group_members=action_group_members,
        payload_helper_evidence=payload_helper_evidence,
        bool_helper_evidence=bool_helper_evidence,
        image_base=image_base, source=source)
    attempt['parentStatus'] = continuation['status']
    attempt['candidateTimelineActionDataRecordEnd'] = continuation.get(
        'candidateTimelineActionDataRecordEnd')
    attempt['candidateActionGroupDataRecordEnd'] = continuation.get(
        'candidateActionGroupDataRecordEnd')
    if (role == 'first-timeline-sequence-action' and
            continuation.get('status') == 'stopped-before-additional-timeline-action-data'):
        _add_following_timeline_prefix(
            alignment, raw, timeline_reader=timeline_reader,
            sequence_reader=sequence_reader,
            payload_helper_evidence=payload_helper_evidence,
            bool_helper_evidence=bool_helper_evidence,
            image_base=image_base, source=source)
    return reader_candidate


def _extend_following_play_animation(alignment: dict[str, Any], raw: bytes, *,
                                     timeline_reader: Mapping[str, Any],
                                     sequence_reader: Mapping[str, Any],
                                     action_group_members: list[Mapping[str, Any]],
                                     routes: Mapping[str, Any],
                                     action_readers: Mapping[int, Mapping[str, Any]],
                                     payload_helper_evidence: Mapping[str, Any],
                                     bool_helper_evidence: Mapping[str, Any],
                                     image_base: int, source: str) -> None:
    prefix = alignment.get('candidateFollowingTimelineActionDataPrefix')
    if not isinstance(prefix, Mapping):
        return
    peek = prefix.get('firstActionUnionTagPeekOnly')
    if (not isinstance(peek, Mapping) or peek.get('tag') != 0x115 or
            prefix.get('timelineSequenceCount') != 1 or
            alignment.get('candidateFollowingPlayAnimationRecordEnd') is not None):
        return
    remaining_timeline_actions = alignment.get('timelineActionsListCount')
    if type(remaining_timeline_actions) is not int or remaining_timeline_actions < 2:
        raise TimelineCursorError(
            f'{source}: following 0x115 action has no remaining TimelineActionData element')
    remaining_timeline_actions -= 1
    continuation = _skilldata_continue_following_play_animation_candidate(
        raw, dict(prefix), int(alignment['hardLimit']),
        timeline_actions_list_count=remaining_timeline_actions,
        timeline_reader=dict(timeline_reader), sequence_reader=dict(sequence_reader),
        action_group_members=[dict(row) for row in action_group_members],
        buff_routes=dict(routes), action_readers=dict(action_readers),
        payload_helper_evidence=dict(payload_helper_evidence),
        bool_helper_evidence=dict(bool_helper_evidence),
        gameassembly_image_base=image_base, source=source)
    _append_alignment_ranges(alignment, continuation['ranges'],
                             source=source, label='following PlayAnimationAction continuation')
    alignment['candidateFollowingPlayAnimationRecordEnd'] = continuation.get(
        'candidatePlayAnimationRecordEnd')
    alignment['candidateFollowingTimelineActionDataRecordEnd'] = continuation.get(
        'candidateTimelineActionDataRecordEnd')
    alignment['candidateFollowingTimelineContinuation'] = continuation.get(
        'candidateTimelineContinuation')
    if isinstance(continuation.get('candidateActionGroupDataRecordEnd'), Mapping):
        alignment['candidateActionGroupDataRecordEnd'] = continuation[
            'candidateActionGroupDataRecordEnd']
    alignment['candidateStatus'] = continuation['status']
    alignment['failure'] = continuation.get('failure')
    alignment.setdefault('opaquePayloadByteRanges', []).extend(
        continuation.get('opaquePayloadByteRanges', []))
    _refresh_alignment_opaque_ranges(alignment)


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()



def _read_json(path: Path, *, label: str) -> tuple[dict[str, Any], str]:
    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode('utf-8-sig'))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise TimelineCursorError(f'{label}: cannot read UTF-8 JSON ({exc})') from exc
    if not isinstance(value, dict):
        raise TimelineCursorError(f'{label}: expected a JSON object')
    return value, _sha256_bytes(raw)


def _stream_encoding(path: Path) -> str:
    with path.open('rb') as stream:
        marker = stream.read(4)
    if marker.startswith((b'\xff\xfe', b'\xfe\xff')):
        return 'utf-16'
    return 'utf-8-sig'


def _context_source_hash(native: Mapping[str, Any], path: Path, *, label: str) -> None:
    source_hashes = native.get('sourceHashes')
    if not isinstance(source_hashes, Mapping):
        raise TimelineCursorError('native context sourceHashes: expected an object')
    expected = _sha256_file(path)
    matches = [digest for source, digest in source_hashes.items()
               if isinstance(source, str) and
               Path(source).resolve() == path.resolve()]
    if len(matches) != 1 or str(matches[0]).upper() != expected:
        raise TimelineCursorError(
            f'native context does not pin the current {label} source bytes')


def _native_image_base(native: Mapping[str, Any]) -> int:
    skill = native.get('selectedSkillDataReaderOrder')
    timeline = skill.get('timelineActionDataReader') if isinstance(skill, Mapping) else None
    methods = timeline.get('methods') if isinstance(timeline, Mapping) else None
    windows = timeline.get('codeWindows') if isinstance(timeline, Mapping) else None
    if not isinstance(methods, list) or not isinstance(windows, list):
        raise TimelineCursorError('native context is missing TimelineActionData methods/windows')
    method_rows = [row for row in methods if row.get('methodIndex') == 104653]
    root_rows = [row for row in windows if row.get('startRva') == 0x32CCF70]
    if len(method_rows) != 1 or len(root_rows) != 1:
        raise TimelineCursorError('native context lacks one exact TimelineActionData reader root')
    pointer_va = method_rows[0].get('pointerVa')
    root_rva = root_rows[0].get('startRva')
    if type(pointer_va) is not int or type(root_rva) is not int:
        raise TimelineCursorError('TimelineActionData root pointer/RVA is not an integer pair')
    image_base = pointer_va - root_rva
    if image_base <= 0 or image_base & 0xFFF:
        raise TimelineCursorError('TimelineActionData root does not imply a page-aligned image base')
    return image_base


def _action_readers_from_context(native: Mapping[str, Any], routes: Mapping[str, Any],
                                *, image_base: int, source: str,
                                allowed_tags: set[int] | None = None) -> dict[int, dict[str, Any]]:
    route_rows = routes.get('rows')
    if not isinstance(route_rows, list):
        raise TimelineCursorError('native action routes do not contain a rows array')
    route_wrappers = {
        row.get('tag'): row.get('wrapperName')
        for row in route_rows
        if isinstance(row, Mapping) and type(row.get('tag')) is int
    }
    readers: dict[int, dict[str, Any]] = {}
    for value in native.values():
        if not isinstance(value, Mapping):
            continue
        contract_path = value.get('contractPath')
        if not isinstance(contract_path, str):
            continue
        match = ACTION_CONTRACT_RE.fullmatch(Path(contract_path).name)
        if match is None:
            continue
        tag = int(match.group(1), 16)
        if allowed_tags is not None and tag not in allowed_tags:
            continue
        route_wrapper = route_wrappers.get(tag)
        methods = value.get('methods')
        if (route_wrapper is None or not isinstance(methods, list) or
                not any(row.get('declaringType') == route_wrapper and
                        row.get('name') == 'Deserialize'
                        for row in methods if isinstance(row, Mapping))):
            continue
        read_order = value.get('anonymousReadOrder')
        root_read_order_key = (next(iter(read_order), None)
                               if isinstance(read_order, Mapping) else None)
        if (not isinstance(root_read_order_key, str) or
                re.search(r'member\d+$', root_read_order_key,
                          flags=re.IGNORECASE) is None):
            # Some same-named Buff contracts describe a different root shape
            # (for example header6). Preserve them as unsupported at the
            # first tag byte instead of applying the action member-count rule.
            continue
        if tag in readers:
            raise TimelineCursorError(f'multiple selected reader contracts match action tag 0x{tag:X}')
        # This independently verifies the exact contract file, current route,
        # module/token join and root code-window identity for each used tag.
        skilldata_action_union_static_reader_evidence(
            tag, dict(value), routes, gameassembly_image_base=image_base,
            source=source)
        readers[tag] = dict(value)
    return readers


def _candidate_class(status: str, failure: Mapping[str, Any] | None) -> str:
    if isinstance(failure, Mapping) and failure.get('category') == 'unsupported':
        return 'unsupported'
    if isinstance(failure, Mapping):
        if str(failure.get('category', '')).startswith('truncated') or failure.get('category') == 'truncated':
            return 'truncated'
        if failure.get('category') in ('member-count', 'count-bounds', 'malformed'):
            return 'malformed'
    if status in ('stopped-before-play-animation-byte-payload',
                  'stopped-before-if-else-sequence-call',
                  'stopped-after-null-action-union',
                  'empty-first-sequence-action-list',
                  'candidate-first-timeline-sequence-prefix',
                  'stopped-before-action-variable-member',
                  'candidate-action-reader-member-sequence-exhausted',
                  'candidate-play-animation-reader-field-sequence-exhausted',
                  'candidate-timeline-action-prefix-before-force-sync',
                  'candidate-force-sync-reader-field-sequence-exhausted',
                  'candidate-timeline-action-reader-field-sequence-exhausted-before-next-element',
                  'candidate-following-timeline-action-field-sequence-exhausted',
                  'candidate-actiongroup-reader-field-sequence-exhausted',
                  'stopped-before-additional-sequence-action',
                  'stopped-before-additional-timeline-action-data',
                  'stopped-before-following-timeline-sequence-action',
                  'stopped-before-sequence-action-elements'):
        return 'structural-prefix'
    if status == 'stopped-at-unknown-action-tag':
        return 'opaque'
    if 'without-current-reader' in status or 'without-bounded-prefix-contract' in status:
        return 'unsupported'
    if status.startswith('truncated'):
        return 'truncated'
    if status.startswith('malformed') or 'member-header' in status:
        return 'malformed'
    return 'ambiguous'


def _row_ranges(rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        return []
    return [dict(row) for row in rows if isinstance(row, Mapping)]


def _markdown(report: Mapping[str, Any]) -> str:
    summary = report['summary']
    lines = [
        '# SkillData TimelineActionData candidate cursor census',
        '',
        f"- Input set: `{report['inputSetSha256']}`",
        f"- Current stream rows joined: {summary['streamRowsJoined']} / {summary['corpusFiles']} ("
        f"{summary['timelineBranchFiles']} on the empty-passive/nonempty-timeline branch)",
        f"- First action tags: `{json.dumps(summary['firstActionTagCounts'], ensure_ascii=False, sort_keys=True)}`",
        f"- Candidate classes: `{json.dumps(summary['candidateBoundaryClassCounts'], ensure_ascii=False, sort_keys=True)}`",
        f"- Candidate cursors: `{json.dumps(summary['candidateCursorCounts'], ensure_ascii=False, sort_keys=True)}`",
        f"- Candidate-only bytes after the maintained parser cursor: {summary['candidateBytesAfterParserCursor']}",
        f"- Opaque bytes after candidate cursors: {summary['opaqueBytesAfterCandidateCursors']}",
        f"- 0x115 PlayAnimation / ForceSync reader end candidates: "
        f"{summary['playAnimationReaderEndCandidates']} / {summary['forceSyncReaderEndCandidates']}",
        f"- TimelineActionData / ActionGroupData field-sequence end candidates: "
        f"{summary['timelineActionDataRecordEndCandidates']} / "
        f"{summary['actionGroupDataRecordEndCandidates']}",
        f"- Following TimelineActionData prefixes / first action tags: "
        f"{summary['followingTimelineActionDataPrefixFiles']} / "
        f"{json.dumps(summary['followingTimelineActionFirstTagCounts'], ensure_ascii=False, sort_keys=True)}",
        f"- Following 0x115 reader / TimelineActionData end candidates: "
        f"{summary['followingPlayAnimationReaderEndCandidates']} / "
        f"{summary['followingTimelineActionDataRecordEndCandidates']}",
        f"- Other selected action-reader field-sequence candidates: "
        f"{json.dumps(summary['actionReaderRecordEndCandidatesByTag'], ensure_ascii=False, sort_keys=True)}",
        f"- Unsupported nested action-reader prefixes: "
        f"{json.dumps(summary['actionReaderPrefixStopsByTag'], ensure_ascii=False, sort_keys=True)}",
        f"- Bounded but undecoded 0x115 payload bytes: {summary['opaqueCandidatePayloadBytes']}",
        f"- Full corpus: {summary['wholeSkillDataExactClosedRecords']} exact closed records; "
        f"{summary['wholeSkillDataAmbiguousFiles']} whole SkillData files remain ambiguous; "
        f"{summary['wholeSkillDataStructuralPrefixFiles']} have parser structural prefixes",
        f"- Full corpus opaque bytes: {summary['wholeSkillDataOpaqueBytesAtFileLevel']} at file level; "
        f"{summary['wholeSkillDataOpaqueBytesByCandidate']} across candidate parsers",
        '- Exact closed TimelineActionData / ActionGroupData records: 0 / 0',
        '',
        'The 10-byte SkillData parser cursor remains authoritative. A selected action candidate is admitted only '
        'after its exact current AbilityActionData route, registered reader, code window and contract are joined; '
        'the hash-pinned structural action reader then stays inside the current file hard limit. Tag 0x115 also '
        'uses its direct payload callsites and shared signed-length helper to record bounded opaque payloads, its '
        'fixed tail and nested sequence. Completed one-child actions can continue through the enclosing sequence '
        'tail, startFrame and ForceSyncAnimData selected reader. Unknown action or nested tags stop at their first '
        'byte. Runtime formatter/provider selection remains unobserved, so no candidate is an exact closed parent '
        'record or whole SkillData file.',
        '',
        '| File | First tag | Candidate cursor | Candidate status | Opaque bytes |',
        '| --- | ---: | ---: | --- | ---: |',
    ]
    sample_rows = []
    seen = set()
    for row in report['files']:
        key = (row.get('candidateBoundaryClass'), row.get('firstActionTag'))
        if key not in seen:
            sample_rows.append(row)
            seen.add(key)
        if len(sample_rows) >= 8:
            break
    for row in sample_rows:
        opaque = sum(span['end'] - span['start'] for span in row.get('opaqueByteRanges', []))
        lines.append(
            f"| `{row['logicalFileIdentity'].rsplit('/', 1)[-1]}` | "
            f"`{row.get('firstActionTag', 'none')}` | {row['candidateCursor']} | "
            f"`{row['candidateStatus']}` | {opaque} |")
    lines.extend([
        '',
        'Per-file half-open byte ranges, source hashes, hard limits, non-advancing tag peeks and failures are in JSON. '
        'A structural-prefix candidate is not a closed record.',
        '',
    ])
    return '\n'.join(lines)


def build_timeline_cursor_report(*, corpus_path: Path, native_path: Path,
                                 stream_path: Path) -> dict[str, Any]:
    corpus, corpus_hash = _read_json(corpus_path, label='SkillData corpus report')
    native, native_hash = _read_json(native_path, label='IL2CPP context report')
    if corpus.get('format') != SKILL_REPORT_FORMAT:
        raise TimelineCursorError('SkillData corpus format is not current SkillData VFS corpus')
    if corpus.get('status') != 'complete' or corpus.get('publicationEligible') is not True:
        raise TimelineCursorError('SkillData corpus is incomplete or not current-input eligible')
    try:
        verify_current_report_inputs(corpus)
    except Exception as exc:
        raise TimelineCursorError(f'SkillData corpus input gate failed: {exc}') from exc
    input_set = str(corpus.get('inputSetSha256', '')).upper()
    if native.get('schemaVersion') != 1 or native.get('status') != 'structural-only':
        raise TimelineCursorError('IL2CPP context is not a complete structural-only report')
    if str(native.get('inputSetSha256', '')).upper() != input_set:
        raise TimelineCursorError('IL2CPP context and SkillData corpus input sets differ')
    native_inputs = native.get('nativeInputs')
    if not isinstance(native_inputs, Mapping):
        raise TimelineCursorError('IL2CPP context nativeInputs are missing')
    game_sha = str(native_inputs.get('gameassemblySha256', '')).upper()
    metadata_sha = str(native_inputs.get('metadataSha256', '')).upper()
    if (game_sha, metadata_sha) != (GA_SHA, MD_SHA):
        raise TimelineCursorError('IL2CPP context native hashes differ from the selected exact build')

    corpus_reference = native.get('corpusReference')
    if not isinstance(corpus_reference, Mapping):
        raise TimelineCursorError('IL2CPP context corpusReference is missing')
    if str(corpus_reference.get('sha256', '')).upper() != corpus_hash:
        raise TimelineCursorError('native context is not pinned to these exact SkillData corpus bytes')
    corpus_summary = corpus.get('summary')
    corpus_boundary = (corpus_summary.get('byteBoundaryEvidence')
                       if isinstance(corpus_summary, Mapping) else None)
    if not isinstance(corpus_boundary, Mapping):
        raise TimelineCursorError('current SkillData corpus byteBoundaryEvidence is missing')
    corpus_ambiguous = corpus_boundary.get('ambiguousFiles')
    corpus_structural_prefixes = corpus_boundary.get('filesWithStructuralPrefix')
    corpus_exact_records = corpus_boundary.get('exactClosedRecords')
    corpus_opaque_candidate_bytes = corpus_boundary.get('opaqueBytesByCandidate')
    corpus_opaque_file_bytes = corpus_boundary.get('opaqueBytesAtFileLevel')
    if (type(corpus_ambiguous) is not int or type(corpus_structural_prefixes) is not int or
            type(corpus_exact_records) is not int or
            type(corpus_opaque_candidate_bytes) is not int or
            type(corpus_opaque_file_bytes) is not int):
        raise TimelineCursorError('current SkillData corpus byte-boundary totals are not integers')
    buff_reference = native.get('buffCorpusReference')
    if not isinstance(buff_reference, Mapping):
        raise TimelineCursorError('IL2CPP context buffCorpusReference is missing')
    buff_reference_path = Path(str(buff_reference.get('path', '')))
    if not buff_reference_path.is_file() or _sha256_file(buff_reference_path) != str(
            buff_reference.get('sha256', '')).upper():
        raise TimelineCursorError('native context BuffData corpus reference is stale')
    _context_source_hash(native,
                         ROOT / 'scripts/game_data/il2cpp_context_audit.py',
                         label='IL2CPP context audit builder')

    skilldata_reader = native.get('selectedSkillDataReaderOrder')
    sequence_reader = native.get('selectedBuffSequenceReadOrder')
    byte_payload_helper = native.get('selectedBuffTag76ReadOrder')
    routes = native.get('selectedBuffUnionRoutes')
    if not all(isinstance(value, Mapping)
               for value in (skilldata_reader, sequence_reader, byte_payload_helper, routes)):
        raise TimelineCursorError('native context lacks SkillData, Sequence or union-route readers')
    image_base = _native_image_base(native)
    c9_reader = native.get('selectedBuffIfElseReadOrder')
    if not isinstance(c9_reader, Mapping):
        raise TimelineCursorError('native context lacks the selected C9/IfElse reader')
    c9_prefix = skilldata_action_union_c9_prefix_reader_evidence(
        dict(c9_reader), dict(routes), gameassembly_image_base=image_base,
        source=str(native_path))
    action_readers = _action_readers_from_context(
        native, routes, image_base=image_base, source=str(native_path),
        allowed_tags=None)
    if 0x115 not in action_readers:
        raise TimelineCursorError('native context lacks the current PlayAnimation action reader')
    action_reader_path = ROOT / 'scripts/game_data/memorypack/buff_actions.py'
    _context_source_hash(native, action_reader_path,
                         label='bounded native-selected action reader')
    action_reader_sha256 = _sha256_file(action_reader_path)
    timeline_reader = skilldata_reader.get('timelineActionDataReader')
    action_group_members = skilldata_reader.get('actionGroupDataMembers')
    if (not isinstance(timeline_reader, Mapping) or
            not isinstance(action_group_members, list)):
        raise TimelineCursorError(
            'native context lacks the current TimelineActionData/ActionGroupData readers')
    payload_helper = _skilldata_verified_byte_payload_reader(
        action_readers[0x115], dict(byte_payload_helper), source=str(native_path))
    # ForceSync's nullable montage-name reader uses the same independently
    # verified signed-length helper; do not infer its width from sample bytes.
    _skilldata_sequence_tail_windows(sequence_reader, source=str(native_path))

    corpus_rows = corpus.get('files')
    if not isinstance(corpus_rows, list):
        raise TimelineCursorError('SkillData corpus files is not an array')
    expected_rows: dict[str, Mapping[str, Any]] = {}
    for index, row in enumerate(corpus_rows):
        if not isinstance(row, Mapping):
            raise TimelineCursorError(f'corpus file row {index} is not an object')
        path = row.get('virtualPath')
        if not isinstance(path, str) or not path.startswith(SKILL_PREFIX):
            raise TimelineCursorError(f'corpus file row {index} is not a SkillData identity')
        if path in expected_rows:
            raise TimelineCursorError(f'duplicate corpus SkillData identity: {path}')
        if str(row.get('inputSetSha256', '')).upper() != input_set:
            raise TimelineCursorError(f'corpus row input set drift: {path}')
        expected_rows[path] = row

    reader_hashes = {}
    source_hashes = native.get('sourceHashes')
    if isinstance(source_hashes, Mapping):
        for source_path, digest in source_hashes.items():
            if isinstance(source_path, str) and ACTION_CONTRACT_RE.fullmatch(Path(source_path).name):
                reader_hashes[Path(source_path).name] = str(digest).upper()
    stream_hash = _sha256_file(stream_path)
    encoding = _stream_encoding(stream_path)
    seen: set[str] = set()
    candidate_files = []
    tag_counts: Counter[str] = Counter()
    status_counts: Counter[str] = Counter()
    candidate_class_counts: Counter[str] = Counter()
    cursor_counts: Counter[str] = Counter()
    tag_status_counts: Counter[str] = Counter()
    candidate_bytes = 0
    opaque_bytes = 0
    play_animation_reader_end_candidates = 0
    force_sync_reader_end_candidates = 0
    timeline_start_frame_prefix_candidates = 0
    timeline_action_data_record_end_candidates = 0
    action_group_data_record_end_candidates = 0
    following_timeline_action_prefix_files = 0
    following_timeline_action_tag_counts: Counter[str] = Counter()
    following_play_animation_reader_end_candidates = 0
    following_timeline_action_data_record_end_candidates = 0
    following_force_sync_reader_end_candidates = 0
    action_reader_end_candidates_by_tag: Counter[str] = Counter()
    action_reader_prefix_stops_by_tag: Counter[str] = Counter()
    first_action_reader_end_candidates_by_tag: Counter[str] = Counter()
    following_action_reader_end_candidates_by_tag: Counter[str] = Counter()
    opaque_candidate_payload_bytes = 0
    shared_byte_payload_evidence = None
    route_rows = routes.get('rows', [])
    route_tag_set = {row.get('tag') for row in route_rows if isinstance(row, Mapping)}

    try:
        stream = stream_path.open('r', encoding=encoding, newline='')
    except OSError as exc:
        raise TimelineCursorError(f'cannot open current SkillData stream: {exc}') from exc
    with stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                stream_row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise TimelineCursorError(
                    f'stream JSON row {line_number} is invalid: {exc}') from exc
            if not isinstance(stream_row, dict):
                raise TimelineCursorError(f'stream row {line_number} is not an object')
            path = stream_row.get('fileName')
            if not isinstance(path, str) or path not in expected_rows:
                raise TimelineCursorError(f'stream row {line_number} has an unexpected identity: {path!r}')
            if path in seen:
                raise TimelineCursorError(f'duplicate stream identity: {path}')
            seen.add(path)
            if (stream_row.get('blockType'), stream_row.get('blockTypeValue')) != ('JsonData', 19):
                raise TimelineCursorError(f'{path}: stream block type differs from JsonData/19')
            encoded = stream_row.get('dataBase64')
            if not isinstance(encoded, str):
                raise TimelineCursorError(f'{path}: stream row has no base64 data')
            try:
                raw = base64.b64decode(encoded, validate=True)
            except ValueError as exc:
                raise TimelineCursorError(f'{path}: invalid base64 ({exc})') from exc
            corpus_row = expected_rows[path]
            if (type(stream_row.get('length')) is not int or
                    stream_row['length'] != len(raw) or
                    stream_row['length'] != corpus_row.get('length')):
                raise TimelineCursorError(f'{path}: stream/corpus length mismatch')
            actual_md5 = hashlib.md5(raw).hexdigest().upper()
            if actual_md5 != str(corpus_row.get('logicalMd5', '')).upper():
                raise TimelineCursorError(f'{path}: stream/corpus logical MD5 mismatch')
            actual_sha = _sha256_bytes(raw)
            if actual_sha != str(corpus_row.get('logicalSha256', '')).upper():
                raise TimelineCursorError(f'{path}: stream/corpus logical SHA256 mismatch')

            record_lists = corpus_row.get('commonPrefixFraming', {}).get('recordLists', [])
            if not (len(record_lists) == 2 and record_lists[0].get('count') == 0 and
                    type(record_lists[1].get('count')) is int and
                    record_lists[1]['count'] > 0):
                continue
            source = f'{stream_path.name}:{line_number}:{path}'
            witness = skilldata_timeline_branch_sample_witness(
                corpus, path, raw, source=source)
            alignment = skilldata_timeline_branch_static_alignment(
                witness, raw, skilldata_reader, sequence_reader, routes,
                action_readers, c9_prefix,
                gameassembly_image_base=image_base,
                byte_payload_helper_evidence=dict(byte_payload_helper),
                source=source)
            alignment['hardLimit'] = len(raw)
            alignment.setdefault('candidateStart', witness['candidateStart'])
            alignment.setdefault('candidateActionReaderCandidates', [])
            alignment.setdefault('opaquePayloadByteRanges', [])
            first_peek = alignment.get('firstActionUnionTagPeekOnly')
            if isinstance(first_peek, Mapping):
                _extend_selected_action(
                    alignment, raw, role='first-timeline-sequence-action',
                    tag_peek=first_peek, action_readers=action_readers,
                    routes=routes, timeline_reader=timeline_reader,
                    sequence_reader=sequence_reader,
                    action_group_members=action_group_members,
                    payload_helper_evidence=payload_helper,
                    bool_helper_evidence=c9_prefix, image_base=image_base,
                    action_reader_sha256=action_reader_sha256, source=source)
            _extend_following_play_animation(
                alignment, raw, timeline_reader=timeline_reader,
                sequence_reader=sequence_reader,
                action_group_members=action_group_members, routes=routes,
                action_readers=action_readers,
                payload_helper_evidence=payload_helper,
                bool_helper_evidence=c9_prefix, image_base=image_base, source=source)
            following_prefix = alignment.get(
                'candidateFollowingTimelineActionDataPrefix')
            if isinstance(following_prefix, Mapping):
                following_peek = following_prefix.get('firstActionUnionTagPeekOnly')
                if isinstance(following_peek, Mapping):
                    _extend_selected_action(
                        alignment, raw,
                        role='following-timeline-sequence-action',
                        tag_peek=following_peek, action_readers=action_readers,
                        routes=routes, timeline_reader=timeline_reader,
                        sequence_reader=sequence_reader,
                        action_group_members=action_group_members,
                        payload_helper_evidence=payload_helper,
                        bool_helper_evidence=c9_prefix, image_base=image_base,
                        action_reader_sha256=action_reader_sha256, source=source)
            for attempt in alignment.get('candidateActionReaderCandidates', []):
                tag = attempt.get('tag')
                if not isinstance(tag, str):
                    continue
                if (attempt.get('rangeAccepted') is True and
                        isinstance(attempt.get('candidateRecordEnd'), Mapping)):
                    action_reader_end_candidates_by_tag[tag] += 1
                    if attempt.get('role') == 'first-timeline-sequence-action':
                        first_action_reader_end_candidates_by_tag[tag] += 1
                    elif attempt.get('role') == 'following-timeline-sequence-action':
                        following_action_reader_end_candidates_by_tag[tag] += 1
                elif (attempt.get('rangeAccepted') is True and
                      isinstance(attempt.get('failure'), Mapping) and
                      attempt['failure'].get('category') == 'unsupported'):
                    action_reader_prefix_stops_by_tag[tag] += 1
            alignment['candidateByteRanges'].sort(
                key=lambda row: (row['start'], row['end']))
            _validate_candidate_ranges(
                alignment['candidateByteRanges'],
                start=alignment['candidateStart'], end=alignment['candidateCursor'],
                hard_limit=alignment['hardLimit'], source=source)
            _refresh_alignment_opaque_ranges(alignment)
            tag_peek = alignment.get('firstActionUnionTagPeekOnly')
            if isinstance(tag_peek, Mapping) and type(tag_peek.get('tag')) is int:
                tag_key = f"0x{tag_peek['tag']:04X}"
            elif isinstance(tag_peek, Mapping):
                tag_key = 'truncated-tag'
            else:
                tag_key = 'none'
            candidate_status = str(alignment.get('candidateStatus'))
            candidate_class = _candidate_class(candidate_status, alignment.get('failure'))
            tag_counts[tag_key] += 1
            status_counts[candidate_status] += 1
            candidate_class_counts[candidate_class] += 1
            cursor_counts[str(alignment['candidateCursor'])] += 1
            tag_status_counts[f'{tag_key}:{candidate_status}'] += 1
            candidate_bytes += sum(span['end'] - span['start']
                                   for span in alignment['candidateByteRanges'])
            opaque_bytes += sum(span['end'] - span['start']
                                for span in alignment['opaqueByteRanges'])
            action_end = alignment.get('candidatePlayAnimationRecordEnd')
            if isinstance(action_end, Mapping):
                play_animation_reader_end_candidates += 1
            timeline_continuation = alignment.get('candidateTimelineContinuation')
            force_sync_end = (timeline_continuation.get(
                'forceSyncAnimDataRecordEndCandidate')
                if isinstance(timeline_continuation, Mapping) else None)
            if isinstance(force_sync_end, Mapping):
                force_sync_reader_end_candidates += 1
            timeline_data_end = alignment.get('candidateTimelineActionDataRecordEnd')
            if isinstance(timeline_data_end, Mapping):
                timeline_action_data_record_end_candidates += 1
            action_group_end = alignment.get('candidateActionGroupDataRecordEnd')
            if isinstance(action_group_end, Mapping):
                action_group_data_record_end_candidates += 1
            following_timeline = alignment.get(
                'candidateFollowingTimelineActionDataPrefix')
            if isinstance(following_timeline, Mapping):
                following_timeline_action_prefix_files += 1
                following_tag = following_timeline.get('firstActionUnionTagPeekOnly')
                if isinstance(following_tag, Mapping) and type(following_tag.get('tag')) is int:
                    following_timeline_action_tag_counts[
                        f"0x{following_tag['tag']:04X}"] += 1
                elif isinstance(following_tag, Mapping):
                    following_timeline_action_tag_counts['truncated-tag'] += 1
                else:
                    following_timeline_action_tag_counts['none'] += 1
            following_play_animation_end = alignment.get(
                'candidateFollowingPlayAnimationRecordEnd')
            if isinstance(following_play_animation_end, Mapping):
                following_play_animation_reader_end_candidates += 1
            following_timeline_end = alignment.get(
                'candidateFollowingTimelineActionDataRecordEnd')
            if isinstance(following_timeline_end, Mapping):
                following_timeline_action_data_record_end_candidates += 1
            following_continuation = alignment.get(
                'candidateFollowingTimelineContinuation')
            following_force_sync_end = (
                following_continuation.get('forceSyncAnimDataRecordEndCandidate')
                if isinstance(following_continuation, Mapping) else None)
            if isinstance(following_force_sync_end, Mapping):
                following_force_sync_reader_end_candidates += 1
            if (isinstance(timeline_continuation, Mapping) and
                    isinstance(timeline_continuation.get('timelineStartFrameEvidence'), list)):
                timeline_start_frame_prefix_candidates += 1
            opaque_candidate_payload_bytes += sum(
                span['end'] - span['start']
                for span in alignment.get('opaquePayloadByteRanges', [])
                if isinstance(span, Mapping) and
                type(span.get('start')) is int and type(span.get('end')) is int)
            if shared_byte_payload_evidence is None:
                evidence = alignment.get('bytePayloadHelperEvidence')
                if isinstance(evidence, Mapping):
                    shared_byte_payload_evidence = dict(evidence)
            file_row = {
                'inputSetSha256': input_set,
                'logicalFileIdentity': path,
                'logicalSha256': actual_sha,
                'logicalMd5': actual_md5,
                'hardLimit': len(raw),
                'parserCursor': witness['authoritativeParserCursor'],
                'candidateStart': witness['candidateStart'],
                'candidateCursor': alignment['candidateCursor'],
                'timelineActionsListCount': alignment['timelineActionsListCount'],
                'firstSequenceActionDataCount': alignment['firstSequenceActionDataCount'],
                'firstActionTag': tag_key,
                'candidateStatus': candidate_status,
                'candidateBoundaryClass': candidate_class,
                'wholeFileBoundaryClass': 'ambiguous',
                'typedPrefixOwnershipCandidate': alignment['typedPrefixOwnershipCandidate'],
                'currentParserByteRanges': _row_ranges(alignment.get('currentParserByteRanges')),
                'candidateByteRanges': _row_ranges(alignment.get('candidateByteRanges')),
                'firstActionUnionTagPeekOnly': alignment.get('firstActionUnionTagPeekOnly'),
                'candidateActionPrefixStop': alignment.get('candidateActionPrefixStop'),
                'candidateFollowingActionPrefixStop': alignment.get(
                    'candidateFollowingActionPrefixStop'),
                'candidateActionReaderCandidates': alignment.get(
                    'candidateActionReaderCandidates', []),
                'candidatePlayAnimationRecordEnd': action_end,
                'candidateTimelineContinuation': timeline_continuation,
                'candidateTimelineActionDataRecordEnd': timeline_data_end,
                'candidateActionGroupDataRecordEnd': action_group_end,
                'candidateFollowingTimelineActionDataPrefix': following_timeline,
                'candidateFollowingTimelineActionDataRecordEnd': following_timeline_end,
                'candidateFollowingPlayAnimationRecordEnd': following_play_animation_end,
                'candidateFollowingTimelineContinuation': following_continuation,
                'opaquePayloadByteRanges': _row_ranges(
                    alignment.get('opaquePayloadByteRanges')),
                'bytePayloadHelperEvidence': alignment.get('bytePayloadHelperEvidence'),
                'failure': alignment.get('failure'),
                'opaqueByteRanges': _row_ranges(alignment.get('opaqueByteRanges')),
                'exactClosedTimelineActionRecords': 0,
                'exactClosedActionGroupDataRecords': 0,
                'wholeSkillDataExactClosedRecords': 0,
            }
            candidate_files.append(file_row)

    missing = sorted(set(expected_rows) - seen)
    if missing:
        raise TimelineCursorError(
            f'current stream is missing {len(missing)} SkillData identities; first={missing[0]}')
    if len(seen) != len(expected_rows):
        raise TimelineCursorError('current stream/corpus SkillData row count differs')

    reader_evidence_by_tag = {}
    observed_action_tags = {
        int(tag, 16) for tag in tag_counts
        if re.fullmatch(r'0x[0-9A-Fa-f]+', tag) is not None
    }
    observed_action_tags.update(
        int(tag, 16) for tag in following_timeline_action_tag_counts
        if re.fullmatch(r'0x[0-9A-Fa-f]+', tag) is not None)
    for tag, reader in sorted(action_readers.items()):
        # Keep only readers that a current registered route actually selects.
        if tag not in observed_action_tags:
            continue
        matching_routes = [row for row in route_rows
                           if isinstance(row, Mapping) and row.get('tag') == tag]
        if not matching_routes:
            continue
        route = matching_routes[0]
        methods = reader.get('methods')
        root_methods = [row for row in methods
                        if isinstance(row, Mapping) and
                        row.get('declaringType') == route.get('wrapperName') and
                        row.get('name') == 'Deserialize']
        if len(root_methods) != 1 or type(root_methods[0].get('pointerVa')) is not int:
            raise TimelineCursorError(
                f'0x{tag:04X}: selected route has no unique registered root reader method')
        root_rva = root_methods[0]['pointerVa'] - image_base
        root_windows = [row for row in reader.get('codeWindows', [])
                        if isinstance(row, Mapping) and row.get('startRva') == root_rva]
        if len(root_windows) != 1:
            raise TimelineCursorError(
                f'0x{tag:04X}: no unique code window at selected root reader RVA')
        read_order = reader.get('anonymousReadOrder')
        root_read_order_key = (next(iter(read_order), None)
                               if isinstance(read_order, Mapping) else None)
        reader_evidence_by_tag[f'0x{tag:04X}'] = {
            'contractFile': Path(reader['contractPath']).name,
            'contractSha256': reader['contractSha256'],
            'rootMethod': dict(root_methods[0]),
            'rootCodeWindow': dict(root_windows[0]),
            'rootReadOrderKey': root_read_order_key,
            'rootMemberOrder': read_order,
            'verifiedSourceReadCallSites': _row_ranges(
                reader.get('verifiedSourceReadCallSites')),
        }
    reader_evidence_by_tag['0x00C9'] = {
        'rootCodeWindow': c9_prefix['rootCodeWindow'],
        'prefixByteLengthIncludingTagAndMemberHeader':
            c9_prefix['prefixByteLengthIncludingTagAndMemberHeader'],
        'nestedSequenceMethodSpecIndex': c9_prefix['nestedSequenceMethodSpecIndex'],
        'providerSelection': c9_prefix['providerSelection'],
    }

    return {
        'format': 'endfield.skilldataTimelineCursor.v1',
        'schemaVersion': 1,
        'status': 'complete',
        'publicationEligible': False,
        'inputSetSha256': input_set,
        'provenance': {
            'skillDataCorpusReport': {
                'path': str(corpus_path.resolve()), 'sha256': corpus_hash,
            },
            'nativeContextReport': {
                'path': str(native_path.resolve()), 'sha256': native_hash,
            },
            'nativeInputs': {
                'gameassemblySha256': game_sha,
                'metadataSha256': metadata_sha,
            },
            'currentSkillDataStream': {
                'path': str(stream_path.resolve()),
                'sha256': stream_hash,
                'encoding': encoding,
                'verifyMd5AgainstCorpus': True,
            },
            'boundedActionByteReader': {
                'path': str(action_reader_path.resolve()),
                'sha256': action_reader_sha256,
                'nativeContextSourceHashVerified': True,
            },
            'timelineCursorBuilderSha256': _sha256_file(Path(__file__)),
            'nativeImageBase': image_base,
        },
        'summary': {
            'corpusFiles': len(expected_rows),
            'streamRowsJoined': len(seen),
            'timelineBranchFiles': len(candidate_files),
            'candidateStatusCounts': dict(sorted(status_counts.items())),
            'candidateBoundaryClassCounts': dict(sorted(candidate_class_counts.items())),
            'firstActionTagCounts': dict(sorted(tag_counts.items())),
            'firstActionTagStatusCounts': dict(sorted(tag_status_counts.items())),
            'candidateCursorCounts': dict(sorted(cursor_counts.items())),
            'candidateBytesAfterParserCursor': candidate_bytes,
            'opaqueBytesAfterCandidateCursors': opaque_bytes,
            'playAnimationReaderEndCandidates': play_animation_reader_end_candidates,
            'forceSyncReaderEndCandidates': force_sync_reader_end_candidates,
            'timelineStartFramePrefixCandidates': timeline_start_frame_prefix_candidates,
            'timelineActionDataRecordEndCandidates': timeline_action_data_record_end_candidates,
            'actionGroupDataRecordEndCandidates': action_group_data_record_end_candidates,
            'followingTimelineActionDataPrefixFiles': following_timeline_action_prefix_files,
            'followingTimelineActionFirstTagCounts': dict(
                sorted(following_timeline_action_tag_counts.items())),
            'followingPlayAnimationReaderEndCandidates': (
                following_play_animation_reader_end_candidates),
            'followingTimelineActionDataRecordEndCandidates': (
                following_timeline_action_data_record_end_candidates),
            'followingForceSyncReaderEndCandidates': (
                following_force_sync_reader_end_candidates),
            'actionReaderRecordEndCandidatesByTag': dict(
                sorted(action_reader_end_candidates_by_tag.items())),
            'actionReaderPrefixStopsByTag': dict(
                sorted(action_reader_prefix_stops_by_tag.items())),
            'firstActionReaderRecordEndCandidatesByTag': dict(
                sorted(first_action_reader_end_candidates_by_tag.items())),
            'followingActionReaderRecordEndCandidatesByTag': dict(
                sorted(following_action_reader_end_candidates_by_tag.items())),
            'boundedActionByteReaderSha256': action_reader_sha256,
            'opaqueCandidatePayloadBytes': opaque_candidate_payload_bytes,
            'exactClosedTimelineActionRecords': 0,
            'exactClosedActionGroupDataRecords': 0,
            'exactClosedWholeSkillDataRecords': 0,
            'wholeSkillDataExactClosedRecords': corpus_exact_records,
            'wholeSkillDataAmbiguousFiles': corpus_ambiguous,
            'wholeSkillDataStructuralPrefixFiles': corpus_structural_prefixes,
            'wholeSkillDataBoundaryClassCounts': dict(
                corpus_boundary.get('boundaryClassCounts', {})),
            'wholeSkillDataOpaqueBytesByCandidate': corpus_opaque_candidate_bytes,
            'wholeSkillDataOpaqueBytesAtFileLevel': corpus_opaque_file_bytes,
            'ambiguousWholeSkillDataBranchFiles': len(candidate_files),
        },
        'nativeEvidenceByActionTag': reader_evidence_by_tag,
        'sharedBytePayloadHelperEvidence': shared_byte_payload_evidence,
        'files': candidate_files,
        'evidenceBoundary': (
            'The current SkillData corpus and native reports are hash-pinned to one inputSet/build, and every '
            'stream row is joined by logical identity, length, MD5 and SHA256. parserCursor is the maintained '
            'SkillData cursor and remains at 10. candidateCursor and its byte ranges belong to a separate '
            'conditional static-reader replay. A non-0x115 action advances only when the exact current union route, '
            'registered native reader and hash-pinned structural action reader agree on its root tag/header. '
            'Unsupported nested tags stop at their first byte. The 0x115 path additionally uses direct payload '
            'callsites and shared signed-length helper evidence for bounded opaque payloads and its nested sequence. '
            'For one-child paths, the candidate may continue through SequenceActionData tail bytes, startFrame and '
            'ForceSyncAnimData, and can reach a candidate ActionGroupData field-sequence end at the last list item; '
            'multi-element timeline lists are reported as open prefixes. C9 remains a fixed prefix before its '
            'nested sequence call. Runtime provider selection is unobserved. '
            'Reader-end candidates are not exact closed records; no TimelineActionData, ActionGroupData or whole '
            'SkillData boundary is promoted.'
        ),
    }


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(text, encoding='utf-8', newline='\n')
    os.replace(temporary, path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stream-jsonl', required=True, type=Path,
                        help='current AnimeStudio SkillData-only stream JSONL')
    parser.add_argument('--corpus-report', type=Path, default=DEFAULT_CORPUS)
    parser.add_argument('--native-context', type=Path, default=DEFAULT_NATIVE)
    parser.add_argument('--output-json', type=Path, default=DEFAULT_JSON)
    parser.add_argument('--output-md', type=Path, default=DEFAULT_MD)
    args = parser.parse_args(argv)
    try:
        report = build_timeline_cursor_report(
            corpus_path=args.corpus_report,
            native_path=args.native_context,
            stream_path=args.stream_jsonl)
        encoded = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
        _atomic_write(args.output_json, encoded)
        _atomic_write(args.output_md, _markdown(report))
    except (TimelineCursorError, OSError, ValueError, KeyError) as exc:
        print(f'skilldata_timeline_cursor: {exc}', file=sys.stderr)
        return 2
    print(json.dumps({
        'status': report['status'],
        'inputSetSha256': report['inputSetSha256'],
        'summary': report['summary'],
        'outputJson': str(args.output_json.resolve()),
        'outputMarkdown': str(args.output_md.resolve()),
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
