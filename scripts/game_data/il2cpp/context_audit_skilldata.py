"""SkillData branch witness, candidate replay and static-alignment evidence.

Moved verbatim out of ``context_audit``; that module owns the audit
contract and the report it assembles.
"""
from __future__ import annotations

import hashlib
import re
import struct
from pathlib import Path
from scripts.game_data.il2cpp.context import ContextError, GenericInstantiationTable, method_parameter_owner, type_image_owners, match_image_modules, method_spec_usage_index, generic_type_carrier, select_rgctx_range, unresolved_usage_index, rip_qword_load_target
from scripts.game_data.memorypack.skill_terminal import TerminalError as SkillTerminalError
from scripts.game_data.memorypack.skill_terminal import frame_skill_terminal_at
from scripts.game_data.memorypack.schemas import MEMORYPACK_FIELD_SCHEMAS
from scripts.game_data.memorypack.buff import read_skill_gameplay_tag_list_field
from scripts.game_data.memorypack.buff import read_skill_toggle_buff_data
from scripts.game_data.memorypack.buff import read_skill_ui_range_hint_data
from scripts.game_data.il2cpp.context import method_spec_record, usage_method_spec, relative_branch_target, method_token_pointer
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.context_audit_common import CORPUS_REPORT_RELATIVE, require
from scripts.game_data.il2cpp.context_audit_memorypack import module_methods


def skilldata_corpus_branch_evidence(corpus, *, source):
    """Cross-check the already-authenticated current SkillData census branches.

    This consumes report rows, not VFS bytes.  It keeps parser cursor and peek
    positions separate and never turns a conditional empty-list endpoint into
    an exact formatter cursor.
    """
    input_set = corpus.get('inputSetSha256')
    if not isinstance(input_set, str) or len(input_set) != 64:
        raise ContextError(source, 0, 'current 64-hex SkillData inputSetSha256', input_set)
    files = corpus.get('files')
    if not isinstance(files, list) or not files:
        raise ContextError(source, 0, 'nonempty current SkillData file rows', type(files).__name__)
    branch_counts = {'bothListsEmpty': 0, 'firstEmptySecondNonempty': 0, 'firstNonempty': 0}
    samples = {}
    def check_row(actual, expected, path, field):
        if actual != expected:
            raise ContextError(source, 0, f'{path}.{field} == {expected!r}', actual)

    for row in files:
        path = row.get('virtualPath')
        if not isinstance(path, str) or not path.startswith('Data/Json/SkillData/'):
            raise ContextError(source, 0, 'logical SkillData virtualPath', path)
        context = row.get('boundaryContext')
        prefix = row.get('commonPrefixFraming')
        if not isinstance(context, dict) or not isinstance(prefix, dict):
            raise ContextError(source, 0, 'bounded prefix and boundary context', path)
        check_row(context.get('inputSetSha256'), input_set, path, 'boundaryContext.inputSetSha256')
        check_row(context.get('logicalFileIdentity'), path, path, 'boundaryContext.logicalFileIdentity')
        check_row(context.get('logicalSha256'), row.get('logicalSha256'), path, 'boundaryContext.logicalSha256')
        check_row(context.get('parserCursor'), row.get('parserCursor'), path, 'boundaryContext.parserCursor')
        check_row(context.get('hardLimit'), row.get('hardLimit'), path, 'boundaryContext.hardLimit')
        lists = prefix.get('recordLists')
        if not isinstance(lists, list) or not lists:
            raise ContextError(source, 0, 'one or two current ActionGroupData list counts', path)
        first = lists[0].get('count')
        second = lists[1].get('count') if len(lists) > 1 else None
        if type(first) is not int or first < 0 or (second is not None and (type(second) is not int or second < 0)):
            raise ContextError(source, 0, 'nonnegative bounded list counts', {'path': path, 'counts': [first, second]})
        if first:
            branch = 'firstNonempty'
            expected_cursor = 6
            expected_stop = 0
        elif second:
            branch = 'firstEmptySecondNonempty'
            expected_cursor = 10
            expected_stop = 1
        else:
            branch = 'bothListsEmpty'
            expected_cursor = 10
            expected_stop = None
        check_row(prefix.get('parserCursor'), expected_cursor, path, 'commonPrefixFraming.parserCursor')
        check_row(prefix.get('cursorOffset'), f'0x{expected_cursor:x}', path, 'commonPrefixFraming.cursorOffset')
        ranges = prefix.get('byteRanges')
        if not isinstance(ranges, list):
            raise ContextError(source, 0, f'{path}.commonPrefixFraming.byteRanges list', ranges)
        range_cursor = 0
        for range_index, span in enumerate(ranges):
            start, end = span.get('start'), span.get('end')
            if (type(start) is not int or type(end) is not int or start != range_cursor
                    or end <= start or end > expected_cursor):
                raise ContextError(source, range_cursor,
                                   f'{path}.byteRanges[{range_index}] contiguous inside [0,{expected_cursor})',
                                   span)
            range_cursor = end
        if range_cursor != expected_cursor:
            raise ContextError(source, range_cursor,
                               f'{path}.byteRanges tile [0,{expected_cursor})', range_cursor)
        if expected_stop is not None:
            check_row(prefix.get('stopListIndex'), expected_stop, path, 'commonPrefixFraming.stopListIndex')
        else:
            check_row(prefix.get('stopListIndex'), None, path, 'commonPrefixFraming.stopListIndex')
        check_row(row.get('boundaryClass') in ('structural-prefix', 'exact-closed'),
                  True, path, 'boundaryClass is current supported state')
        candidates = row.get('framing', {}).get('candidateCount')
        check_row(type(candidates) is int and candidates >= 2, True, path, 'framing.candidateCount >= 2')
        branch_counts[branch] += 1
        sample = {
            'inputSetSha256': input_set,
            'logicalFileIdentity': path,
            'logicalSha256': row.get('logicalSha256'),
            'recordListCounts': [first] + ([] if second is None else [second]),
            'parserCursor': expected_cursor,
            'hardLimit': row.get('hardLimit'),
            'consumedByteRanges': prefix.get('byteRanges', []),
            'firstUnconsumedByteOffset': expected_cursor if branch != 'bothListsEmpty' else None,
            'peekOnlyMemberCount': (
                lists[0].get('firstRecordMemberCount') if branch == 'firstNonempty'
                else lists[1].get('firstRecordMemberCount') if branch == 'firstEmptySecondNonempty'
                else None
            ),
            'terminalCandidateStarts': [candidate.get('startOffset')
                                        for candidate in row.get('framing', {}).get('candidates', [])],
        }
        previous = samples.get(branch)
        sample_rank = (sum(sample['recordListCounts']), path)
        previous_rank = (sum(previous['recordListCounts']), previous['logicalFileIdentity']) if previous else None
        if previous_rank is None or sample_rank < previous_rank:
            samples[branch] = sample
    declared = corpus.get('summary', {}).get('filesSelected')
    if declared != len(files):
        raise ContextError(source, 0, 'summary.filesSelected equals report file row count',
                           {'declared': declared, 'actual': len(files)})
    return {
        'inputSetSha256': input_set,
        'filesSelected': len(files),
        'branchCounts': branch_counts,
        'representativeCurrentVfsSamples': samples,
        'emptyActionGroupCandidateRange': {
            'start': 1, 'end': 10, 'endExclusive': True,
            'candidateFiles': branch_counts['bothListsEmpty'],
            'conditionalOn': 'both List<T> reads taking the audited ListFormatter<T> candidate four-byte zero-count path',
            'exactClosedRecords': 0,
        },
        'wholeFileBoundary': {
            'boundedPartialFiles': sum(1 for row in files if row.get('boundaryClass') == 'structural-prefix'),
            'exactClosedRecords': corpus.get('summary', {}).get('byteBoundaryEvidence', {}).get('exactClosedRecords'),
            'boundary': 'The current report preserves all EOF candidates; these prefix branches do not choose the shifted terminal member.'
        },
        'boundary': 'Rows are cross-checked by inputSetSha256, logical identity/hash, parser cursor and hard limit. firstUnconsumedByteOffset is not consumed; peekOnlyMemberCount, where present, is a non-advancing peek. The current VFS report is authenticated but not re-streamed here.',
    }


def skilldata_actiongroup_branch_sample_witness(
        corpus, logical_path, raw, *, source, verified_action_tags=None,
        verified_action_prefix_tags=None):
    """Replay one current passiveEventActions list, stopping at unverified unions."""
    input_set = corpus.get('inputSetSha256')
    if (not isinstance(input_set, str) or len(input_set) != 64 or
            any(ch not in '0123456789abcdefABCDEF' for ch in input_set)):
        raise ContextError(source, 0, 'current 64-hex SkillData inputSetSha256', input_set)
    rows = [row for row in corpus.get('files', [])
            if isinstance(row, dict) and row.get('virtualPath') == logical_path]
    if len(rows) != 1:
        raise ContextError(source, 0,
                           f'exactly one current VFS SkillData row for {logical_path!r}',
                           len(rows))
    row = rows[0]
    if (not isinstance(logical_path, str) or
            not logical_path.startswith('Data/Json/SkillData/')):
        raise ContextError(source, 0, 'logical SkillData virtualPath', logical_path)
    if not isinstance(raw, bytes):
        raise ContextError(source, 0, 'current raw SkillData sample bytes', type(raw).__name__)

    hard_limit = row.get('hardLimit')
    if type(hard_limit) is not int or hard_limit != len(raw):
        raise ContextError(source, 0, 'sample hardLimit equals raw file length',
                           [hard_limit, len(raw)])
    logical_sha = hashlib.sha256(raw).hexdigest().upper()
    require(row.get('logicalSha256'), logical_sha, source, 0)
    require(row.get('inputSetSha256'), input_set, source, 0)
    boundary_context = row.get('boundaryContext')
    if not isinstance(boundary_context, dict):
        raise ContextError(source, 0, 'current sample boundaryContext', boundary_context)
    require(boundary_context.get('inputSetSha256'), input_set, source, 0)
    require(boundary_context.get('logicalFileIdentity'), logical_path, source, 0)
    require(boundary_context.get('logicalSha256'), logical_sha, source, 0)
    require(boundary_context.get('hardLimit'), hard_limit, source, 0)
    require(row.get('boundaryClass'), 'structural-prefix', source, 0)
    candidate_count = row.get('framing', {}).get('candidateCount')
    require(type(candidate_count) is int and candidate_count >= 2, True, source, 0)
    prefix = row.get('commonPrefixFraming')
    record_lists = prefix.get('recordLists') if isinstance(prefix, dict) else None
    if not isinstance(record_lists, list) or not record_lists:
        raise ContextError(source, 0, 'one current ActionGroupData list count', record_lists)
    expected_list_count = record_lists[0].get('count')
    if type(expected_list_count) is not int or expected_list_count <= 0:
        raise ContextError(source, 2, 'positive current passiveEventActions list count',
                           expected_list_count)
    if len(raw) < 2:
        raise ContextError(source, 0, 'complete SkillData and ActionGroupData headers', len(raw))
    require(raw[0], 48, source, 0)
    require(raw[1], 2, source, 1)
    if len(raw) >= 6:
        actual_list_count = struct.unpack_from('<i', raw, 2)[0]
        require(actual_list_count, expected_list_count, source, 2)

    if verified_action_tags is None:
        verified_action_tags = {0xD5, 0xD6}
    if (not isinstance(verified_action_tags, (set, frozenset)) or
            any(type(tag) is not int or not 0 <= tag <= 0xFFFF
                for tag in verified_action_tags)):
        raise ContextError(source, 0, 'verified action tags as a set of 16-bit integers',
                           verified_action_tags)
    if verified_action_prefix_tags is None:
        verified_action_prefix_tags = set()
    if (not isinstance(verified_action_prefix_tags, (set, frozenset)) or
            any(type(tag) is not int or not 0 <= tag <= 0xFFFF
                for tag in verified_action_prefix_tags)):
        raise ContextError(source, 0,
                           'verified action-prefix tags as a set of 16-bit integers',
                           verified_action_prefix_tags)

    from scripts.game_data.memorypack.buff_actions import Reader, Unsupported

    class StopBeforeUnverifiedUnionReader(Reader):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.action_prefix_stop = None

        def _action(self, depth, tag, width):
            if tag == 0xFF or tag in verified_action_tags:
                return super()._action(depth, tag, width)
            if tag == 0xC9 and tag in verified_action_prefix_tags:
                start = self.pos
                available = self.limit - self.pos
                if (width != 1 or available < 2 or self.data[self.pos] != 0xC9 or
                        self.data[self.pos + 1] != 8):
                    raise Unsupported(self.source, start,
                                      'non-null 0xC9 member-eight normal path',
                                      tag,
                                      'opaque-union')
                self.take(width, 'union-tag')
                self.header(8)
                self.take(1, 'anonymous-byte')
                for _ in range(3):
                    self.take(4, 'anonymous-scalar32')
                self.take(1, 'anonymous-byte')
                self.action_prefix_stop = {
                    'tag': tag,
                    'start': start,
                    'end': self.pos,
                    'memberHeader': 8,
                    'sourceReadWidthsAfterHeader': [1, 4, 4, 4, 1],
                    'consumedUnionRecord': False,
                    'nextSourceReadType': 'Beyond.Gameplay.Core.SequenceActionData',
                    'nextSourceReadOffset': self.pos,
                    'nextSourceReadConsumed': False,
                    'nextSourceReadFirstByte': (
                        self.data[self.pos] if self.pos < self.limit else None),
                    'remainingBytesOpaque': True,
                }
                raise Unsupported(self.source, self.pos,
                                  'first nested SequenceActionData call remains unread',
                                  tag, 'verified-prefix-stop')
            # _action is entered before the tag bytes are consumed, so this
            # keeps every unverified union at its first byte (including FA/u16).
            raise Unsupported(self.source, self.pos,
                              'non-null AbilityActionData payload remains opaque',
                              tag, 'opaque-union')

    reader = StopBeforeUnverifiedUnionReader(raw, source, limit=hard_limit)
    reader.pos = 2
    parser_error = None
    try:
        reader.ability_action_map_collection_profile(0)
        parse_status = 'passive-list-consumed-to-conditional-static-end'
        boundary_class = 'structural-prefix'
    except Exception as exc:
        diagnostic = getattr(exc, 'diagnostic', None)
        if not isinstance(diagnostic, dict):
            raise
        parser_error = diagnostic
        if diagnostic.get('category') == 'opaque-union':
            parse_status = 'stopped-before-first-nonnull-action-union'
            boundary_class = 'opaque'
        elif diagnostic.get('category') == 'verified-prefix-stop':
            parse_status = 'stopped-after-verified-action-prefix'
            boundary_class = 'structural-prefix'
        elif diagnostic.get('category') == 'truncated':
            parse_status = 'truncated-structural-prefix'
            boundary_class = 'structural-prefix'
        elif diagnostic.get('category') in ('member-count', 'count-bounds', 'malformed'):
            parse_status = 'invalid-structural-prefix'
            boundary_class = 'malformed'
        else:
            parse_status = 'unsupported-structural-prefix'
            boundary_class = 'unsupported'

    consumed_ranges = [
        {'start': 0, 'end': 1, 'kind': 'SkillData.memberCount', 'value': raw[0]},
        {'start': 1, 'end': 2, 'kind': 'ActionGroupData.memberCount', 'value': raw[1]},
        *reader.ranges,
    ]
    range_cursor = 0
    for index, span in enumerate(consumed_ranges):
        start, end = span.get('start'), span.get('end')
        if (type(start) is not int or type(end) is not int or start != range_cursor or
                end <= start or end > reader.pos):
            raise ContextError(source, range_cursor,
                               f'byteRanges[{index}] contiguous inside [0,{reader.pos})', span)
        range_cursor = end
    require(range_cursor, reader.pos, source, range_cursor)

    count_fields = []
    for span in consumed_ranges:
        if span.get('kind') == 'count-i32':
            count_fields.append({
                'offset': span['start'],
                'end': span['end'],
                'signedI32': struct.unpack_from('<i', raw, span['start'])[0],
            })
    unconsumed_union = None
    if parser_error and parser_error.get('category') == 'opaque-union':
        offset = reader.pos
        unconsumed_union = {
            'offset': offset,
            'firstByte': raw[offset],
            'tag': parser_error.get('actual'),
            'consumed': False,
        }
    action_union_prefix_stop = getattr(reader, 'action_prefix_stop', None)
    if parser_error and parser_error.get('category') == 'verified-prefix-stop':
        if not isinstance(action_union_prefix_stop, dict):
            raise ContextError(source, reader.pos,
                               'verified-prefix diagnostic has a bounded action-prefix stop record',
                               action_union_prefix_stop)
        require(action_union_prefix_stop.get('end'), reader.pos, source, reader.pos)
    union_header_observations = []
    for record in reader.records:
        if record.get('kind') != 'union' or record.get('tag') == 0xFF:
            continue
        start = record.get('start')
        if type(start) is not int or not start < record.get('end', start):
            raise ContextError(source, reader.pos, 'completed action union has a byte range', record)
        tag_width = 3 if raw[start] == 0xFA else 1
        header_offset = start + tag_width
        if header_offset >= record['end'] or raw[header_offset] == 0xFF:
            continue
        union_header_observations.append({
            'tag': record['tag'],
            'start': start,
            'end': record['end'],
            'tagWidth': tag_width,
            'tagPrefixByte': raw[start],
            'tagEncodingHex': raw[start:header_offset].hex().upper(),
            'memberHeaderOffset': header_offset,
            'memberHeaderValue': raw[header_offset],
        })
    next_member_count_peek = None
    if (parse_status == 'passive-list-consumed-to-conditional-static-end' and
            reader.pos + 4 <= hard_limit):
        next_member_count_peek = {
            'fieldName': 'timelineActions.count',
            'offset': reader.pos,
            'signedI32': struct.unpack_from('<i', raw, reader.pos)[0],
            'consumed': False,
        }
    return {
        'inputSetSha256': input_set,
        'logicalFileIdentity': logical_path,
        'logicalSha256': logical_sha,
        'hardLimit': hard_limit,
        'parserCursor': reader.pos,
        'passiveEventActionsListCount': expected_list_count,
        'status': parse_status,
        'boundaryClass': boundary_class,
        'consumedByteRanges': consumed_ranges,
        'countI32Fields': count_fields,
        'completedNestedRecords': reader.records,
        'completedActionUnionHeaderObservations': union_header_observations,
        'nextMemberCountPeekOnly': next_member_count_peek,
        'opaqueByteRanges': ([] if reader.pos == hard_limit else [
            {'start': reader.pos, 'end': hard_limit, 'kind': 'unconsumed-actiongroup-and-skilldata-bytes'}
        ]),
        'firstUnconsumedActionUnionByte': unconsumed_union,
        'actionUnionPrefixStop': action_union_prefix_stop,
        'parserError': parser_error,
        'wholeSkillDataClassification': 'ambiguous',
        'wholeSkillDataExactClosedRecords': 0,
        'boundary': ('Only the first ActionGroupData passiveEventActions list is replayed. A union advances '
                     'only when its current-build tag route and hash-pinned native action reader are supplied '
                     'to the separate alignment gate; every other non-null tag stops at its first byte. '
                     'timelineActions, the rest of ActionGroupData, and the whole SkillData endpoint are '
                     'not consumed.'),
    }


def skilldata_timeline_branch_sample_witness(corpus, logical_path, raw, *, source):
    """Replay only the first TimelineActionData structural prefix in a current VFS row."""
    input_set = corpus.get('inputSetSha256')
    if (not isinstance(input_set, str) or len(input_set) != 64 or
            any(ch not in '0123456789abcdefABCDEF' for ch in input_set)):
        raise ContextError(source, 0, 'current 64-hex SkillData inputSetSha256', input_set)
    rows = [row for row in corpus.get('files', [])
            if isinstance(row, dict) and row.get('virtualPath') == logical_path]
    if len(rows) != 1:
        raise ContextError(source, 0,
                           f'exactly one current VFS SkillData row for {logical_path!r}',
                           len(rows))
    row = rows[0]
    if (not isinstance(logical_path, str) or
            not logical_path.startswith('Data/Json/SkillData/')):
        raise ContextError(source, 0, 'logical SkillData virtualPath', logical_path)
    if not isinstance(raw, bytes):
        raise ContextError(source, 0, 'current raw SkillData sample bytes',
                           type(raw).__name__)
    hard_limit = row.get('hardLimit')
    if type(hard_limit) is not int or hard_limit != len(raw):
        raise ContextError(source, 0, 'sample hardLimit equals raw file length',
                           [hard_limit, len(raw)])
    logical_sha = hashlib.sha256(raw).hexdigest().upper()
    require(row.get('logicalSha256'), logical_sha, source, 0)
    require(row.get('inputSetSha256'), input_set, source, 0)
    boundary_context = row.get('boundaryContext')
    if not isinstance(boundary_context, dict):
        raise ContextError(source, 0, 'current sample boundaryContext', boundary_context)
    for key, expected in (
            ('inputSetSha256', input_set),
            ('logicalFileIdentity', logical_path),
            ('logicalSha256', logical_sha),
            ('hardLimit', hard_limit)):
        require(boundary_context.get(key), expected, source, 0)
    require(row.get('boundaryClass'), 'structural-prefix', source, 0)
    require(row.get('parserCursor'), 10, source, 0)
    require(row.get('hardLimit'), hard_limit, source, 0)
    framing = row.get('framing')
    if not isinstance(framing, dict):
        raise ContextError(source, 0, 'current ambiguous SkillData framing', framing)
    candidate_count = framing.get('candidateCount')
    require(type(candidate_count) is int and candidate_count >= 2, True, source, 0)
    prefix = row.get('commonPrefixFraming')
    if not isinstance(prefix, dict):
        raise ContextError(source, 0, 'current common SkillData prefix', prefix)
    require(prefix.get('parserCursor'), 10, source, 0)
    record_lists = prefix.get('recordLists')
    if not isinstance(record_lists, list) or len(record_lists) != 2:
        raise ContextError(source, 0, 'two current ActionGroupData list-count reads',
                           record_lists)
    count_offsets = []
    for index, item in enumerate(record_lists):
        raw_offset = item.get('countOffset')
        try:
            count_offsets.append(int(raw_offset, 0) if isinstance(raw_offset, str)
                                 else raw_offset)
        except ValueError as exc:
            raise ContextError(source, 2 + index * 4,
                               'bounded list-count source offset', raw_offset) from exc
    require(count_offsets, [2, 6], source, 2)
    first_count, timeline_count = (item.get('count') for item in record_lists)
    require(first_count, 0, source, 2)
    if type(timeline_count) is not int or timeline_count <= 0:
        raise ContextError(source, 6, 'positive current timelineActions list count',
                           timeline_count)
    if hard_limit < 10:
        raise ContextError(source, 0, 'current common prefix fits within hardLimit',
                           hard_limit)
    require(raw[0], 48, source, 0)
    require(raw[1], 2, source, 1)
    require(struct.unpack_from('<i', raw, 2)[0], first_count, source, 2)
    require(struct.unpack_from('<i', raw, 6)[0], timeline_count, source, 6)

    prefix_ranges = prefix.get('byteRanges')
    if not isinstance(prefix_ranges, list):
        raise ContextError(source, 0, 'current common-prefix byte-range manifest',
                           prefix_ranges)
    prefix_cursor = 0
    for index, span in enumerate(prefix_ranges):
        start, end = span.get('start'), span.get('end')
        if (type(start) is not int or type(end) is not int or
                start != prefix_cursor or end <= start or end > 10):
            raise ContextError(source, prefix_cursor,
                               f'common prefix byteRanges[{index}] contiguous in [0,10)', span)
        prefix_cursor = end
    require(prefix_cursor, 10, source, prefix_cursor)

    cursor = 10
    candidate_ranges = []
    failure = None

    def take(width, kind):
        nonlocal cursor, failure
        if type(width) is not int or width < 0:
            failure = {'category': 'malformed', 'offset': cursor,
                       'expected': 'non-negative byte width', 'actual': width}
            return None
        if width > hard_limit - cursor:
            failure = {'category': 'truncated', 'offset': cursor,
                       'expected': {'bytes': width},
                       'actual': {'remaining': hard_limit - cursor}}
            return None
        start = cursor
        cursor += width
        if width:
            candidate_ranges.append({'start': start, 'end': cursor, 'kind': kind})
        return raw[start:cursor]

    def header(expected, kind):
        nonlocal failure
        if cursor >= hard_limit:
            failure = {'category': 'truncated', 'offset': cursor,
                       'expected': {'bytes': 1}, 'actual': {'remaining': 0}}
            return False
        if raw[cursor] != expected:
            failure = {'category': 'member-count', 'offset': cursor,
                       'expected': expected, 'actual': raw[cursor]}
            return False
        return take(1, kind) is not None

    if not header(4, 'TimelineActionData.member-header'):
        pass
    elif take(4, 'TimelineActionData.endFrame.i32') is None:
        pass
    elif not header(3, 'SequenceActionData.member-header'):
        pass
    else:
        count_raw = take(4, 'SequenceActionData.actionData.count-i32')
        if count_raw is not None:
            action_count = struct.unpack('<i', count_raw)[0]
            if action_count < -1:
                failure = {'category': 'count-bounds', 'offset': cursor - 4,
                           'expected': {'minimum': -1}, 'actual': action_count}
            else:
                maximum = max(0, hard_limit - cursor - 2)
                if action_count > maximum:
                    failure = {'category': 'count-bounds', 'offset': cursor - 4,
                               'expected': {'minimum': -1, 'maximum': maximum},
                               'actual': action_count}

    tag_peek = None
    if failure is None and len(candidate_ranges) == 4 and action_count > 0:
        if cursor >= hard_limit:
            failure = {'category': 'truncated-action-tag', 'offset': cursor,
                       'expected': {'minimumBytes': 1},
                       'actual': {'remaining': 0}}
        else:
            first_byte = raw[cursor]
            tag_width = 3 if first_byte == 0xFA else 1
            if tag_width > hard_limit - cursor:
                failure = {'category': 'truncated-action-tag', 'offset': cursor,
                           'expected': {'bytes': tag_width},
                           'actual': {'remaining': hard_limit - cursor}}
                tag_peek = {'offset': cursor, 'firstByte': first_byte,
                            'tag': None, 'tagWidth': tag_width,
                            'encodingHex': raw[cursor:hard_limit].hex().upper(),
                            'consumed': False}
            else:
                tag = (struct.unpack_from('<H', raw, cursor + 1)[0]
                       if tag_width == 3 else first_byte)
                tag_peek = {'offset': cursor, 'firstByte': first_byte,
                            'tag': tag, 'tagWidth': tag_width,
                            'encodingHex': raw[cursor:cursor + tag_width].hex().upper(),
                            'consumed': False}

    candidate_status = 'candidate-first-timeline-sequence-prefix'
    if failure is not None:
        if failure['category'] in ('member-count', 'count-bounds', 'malformed'):
            candidate_status = 'malformed-timeline-structural-prefix'
        elif failure['category'] == 'truncated-action-tag':
            candidate_status = 'truncated-first-action-tag'
        else:
            candidate_status = 'truncated-timeline-structural-prefix'
    elif action_count <= 0:
        candidate_status = 'empty-first-sequence-action-list'

    return {
        'inputSetSha256': input_set.upper(),
        'logicalFileIdentity': logical_path,
        'logicalSha256': logical_sha,
        'hardLimit': hard_limit,
        'authoritativeParserCursor': 10,
        'candidateStart': 10,
        'candidateCursor': cursor,
        'timelineActionsListCount': timeline_count,
        'firstSequenceActionDataCount': action_count if failure is None or cursor >= 20 else None,
        'status': candidate_status,
        'failure': failure,
        'currentParserByteRanges': prefix_ranges,
        'candidateByteRanges': candidate_ranges,
        'firstActionUnionTagPeekOnly': tag_peek,
        'opaqueByteRanges': ([] if cursor == hard_limit else [
            {'start': cursor, 'end': hard_limit,
             'kind': 'unconsumed-timeline-actiongroup-and-skilldata-bytes'}]),
        'exactClosedTimelineActionRecords': 0,
        'exactClosedActionGroupDataRecords': 0,
        'wholeSkillDataClassification': 'ambiguous',
        'wholeSkillDataExactClosedRecords': 0,
        'boundary': ('The current corpus parser remains at byte 10. This separate structural candidate follows only the '
                     'first TimelineActionData header/endFrame and its SequenceActionData header/action count, then peeks '
                     'at most the first action tag. It does not close a timeline action, ActionGroupData or SkillData.'),
    }


def _skilldata_action_fixed_member_width(read_type):
    """Return widths for scalar members that the selected native reader reads inline."""
    if not isinstance(read_type, str):
        return None
    normalized = read_type.strip().lower().replace('_', '-')
    if normalized in ('byte', 'boolean', 'bool'):
        return 1
    if normalized in ('scalar32', 'float32', 'raw-float32', 'raw-float32-bits'):
        return 4
    if normalized == 'scalar64':
        return 8
    match = re.fullmatch(r'raw(\d+)', normalized)
    if match is not None:
        width = int(match.group(1))
        return width if width in (1, 2, 4, 8, 12, 16) else None
    return None


def _skilldata_verified_byte_payload_reader(action_reader, shared_helper, *, source):
    """Join the two PlayAnimation payload callsites to the audited signed-length helper."""
    call_sites = action_reader.get('verifiedSourceReadCallSites')
    if not isinstance(call_sites, list):
        raise ContextError(source, 0x115,
                           'verified PlayAnimation byte-payload source callsites', call_sites)
    selected = [row for row in call_sites if isinstance(row, dict) and
                row.get('readType') == 'byte-payload']
    expected_sites = {
        (4, 0x3777126, 0x2CA8700),
        (14, 0x377730E, 0x2CA8700),
    }
    actual_sites = {(row.get('memberIndex'), row.get('callInstructionRva'),
                     row.get('targetRva')) for row in selected}
    require(actual_sites, expected_sites, source, 0x115)
    require(len(selected), 2, source, 0x115)

    if not isinstance(shared_helper, dict):
        raise ContextError(source, 0x2CA8700,
                           'independent current signed-length byte-payload helper audit',
                           shared_helper)
    expected_windows = {
        0x2CA8729: '488B43504863388B733083EE040F885C8CE30148834350048343400483434404897330',
        0x2CA874C: '48634344488B4B18482BC8483BCF0F8C528CE30183FFFF743785FF7517',
        0x2CA8780: '4533C08BD7488BCB488B5C2430488B7424384883C4205FE974020000',
        0x2CA8A97: '4533C9448BC7488BD5488BCEE878F8FFFF488BE885FF7418',
        0x2CA8AAF: '8B73302BF70F88B0A4F70148017B50017B40017B44897330',
    }
    windows = shared_helper.get('windows')
    if not isinstance(windows, list):
        raise ContextError(source, 0x2CA8700,
                           'independent byte-payload helper/consumer instruction windows', windows)
    actual_windows = {row.get('rva'): row.get('rawHex', '').upper()
                      for row in windows if isinstance(row, dict)}
    for rva, raw_hex in expected_windows.items():
        require(actual_windows.get(rva), raw_hex, source, rva)
    helper_calls = shared_helper.get('orderedCalls')
    if not isinstance(helper_calls, list):
        raise ContextError(source, 0x2CA8700,
                           'independent byte-payload helper consumer callsites', helper_calls)
    expected_helper_calls = {(0x3D9BBE5, 0x2CA8700),
                             (0x3D9BC37, 0x2CA8700)}
    actual_helper_calls = {(row.get('rva'), row.get('targetRva'))
                           for row in helper_calls if isinstance(row, dict) and
                           row.get('targetRva') == 0x2CA8700}
    require(actual_helper_calls, expected_helper_calls, source, 0x2CA8700)
    boundary = shared_helper.get('boundary')
    if (not isinstance(boundary, str) or 'signed DWORD' not in boundary or
            '-1 returns null' not in boundary or 'positive length' not in boundary):
        raise ContextError(source, 0x2CA8700,
                           'bounded signed-length/null/positive payload consumer evidence', boundary)
    return {
        'actionTag': 0x115,
        'actionMemberCallSites': [dict(row) for row in selected],
        'sharedHelperTargetRva': 0x2CA8700,
        'independentConsumerCallSites': [
            {'callInstructionRva': rva, 'targetRva': target}
            for rva, target in sorted(actual_helper_calls)],
        'verifiedHelperWindows': [
            {'rva': rva, 'rawHex': actual_windows[rva]}
            for rva in sorted(expected_windows)],
        'lengthSemantics': 'signed-i32; -1 null; 0 empty; positive length-bounded opaque payload',
        'payloadSemantics': 'opaque; no decoding or gameplay field name is assigned',
        'providerSelection': 'unobserved',
    }


def _skilldata_read_byte_payload_candidate(raw, start, hard_limit, *, kind, source):
    """Read only a signed length and its in-bounds opaque payload bytes."""
    if start < 0 or hard_limit < start or hard_limit > len(raw):
        raise ContextError(source, start, 'byte-payload start and hard limit inside current raw bytes',
                           {'start': start, 'hardLimit': hard_limit, 'rawLength': len(raw)})
    if hard_limit - start < 4:
        return {
            'cursor': start, 'ranges': [], 'opaquePayloadByteRanges': [],
            'length': None, 'complete': False, 'status': 'truncated-byte-payload-length',
            'failure': {'category': 'truncated', 'offset': start,
                        'kind': f'{kind}.length-i32', 'expectedBytes': 4,
                        'remainingBytes': hard_limit - start},
        }
    length = struct.unpack_from('<i', raw, start)[0]
    ranges = [{'start': start, 'end': start + 4,
               'kind': f'{kind}.length-i32', 'value': length}]
    after_length = start + 4
    if length < -1:
        return {
            'cursor': after_length, 'ranges': ranges, 'opaquePayloadByteRanges': [],
            'length': length, 'complete': False, 'status': 'unsupported-byte-payload-length',
            'failure': {'category': 'unsupported', 'offset': start,
                        'kind': f'{kind}.length-i32', 'actual': length,
                        'supportedValues': '-1, 0, or a positive in-limit length'},
        }
    payload_length = max(length, 0)
    available = hard_limit - after_length
    if payload_length > available:
        return {
            'cursor': after_length, 'ranges': ranges, 'opaquePayloadByteRanges': [],
            'length': length, 'complete': False, 'status': 'truncated-byte-payload',
            'failure': {'category': 'truncated', 'offset': after_length,
                        'kind': f'{kind}.opaque-bytes', 'expectedBytes': payload_length,
                        'remainingBytes': available},
        }
    opaque_ranges = []
    if payload_length:
        payload_range = {'start': after_length, 'end': after_length + payload_length,
                         'kind': f'{kind}.opaque-bytes'}
        ranges.append(payload_range)
        opaque_ranges.append(dict(payload_range))
    return {
        'cursor': after_length + payload_length, 'ranges': ranges,
        'opaquePayloadByteRanges': opaque_ranges, 'length': length,
        'complete': True, 'status': 'bounded-byte-payload', 'failure': None,
    }


def _skilldata_read_sequence_data_candidate(raw, start, hard_limit, *, source):
    """Read SequenceActionData's null/empty path; stop before any list element."""
    ranges = []
    position = start
    if hard_limit - position < 1:
        return {'cursor': position, 'ranges': ranges, 'complete': False,
                'status': 'truncated-sequence-action-header', 'failure': {
                    'category': 'truncated', 'offset': position,
                    'kind': 'SequenceActionData.member-header', 'expectedBytes': 1,
                    'remainingBytes': 0}}
    header = raw[position]
    ranges.append({'start': position, 'end': position + 1,
                   'kind': 'SequenceActionData.member-header', 'value': header})
    position += 1
    if header == 0xFF:
        return {'cursor': position, 'ranges': ranges, 'complete': True,
                'status': 'candidate-null-sequence', 'header': header,
                'count': None, 'failure': None}
    if header != 3:
        return {'cursor': position, 'ranges': ranges, 'complete': False,
                'status': 'malformed-sequence-action-header', 'header': header,
                'failure': {'category': 'member-count', 'offset': start,
                            'expected': [3, 0xFF], 'actual': header}}
    if hard_limit - position < 4:
        return {'cursor': position, 'ranges': ranges, 'complete': False,
                'status': 'truncated-sequence-action-count', 'header': header,
                'failure': {'category': 'truncated', 'offset': position,
                            'kind': 'SequenceActionData.list-count-i32',
                            'expectedBytes': 4, 'remainingBytes': hard_limit - position}}
    count = struct.unpack_from('<i', raw, position)[0]
    ranges.append({'start': position, 'end': position + 4,
                   'kind': 'SequenceActionData.list-count-i32', 'value': count})
    position += 4
    if count < -1:
        return {'cursor': position, 'ranges': ranges, 'complete': False,
                'status': 'unsupported-sequence-action-count', 'header': header,
                'count': count, 'failure': {'category': 'unsupported',
                    'offset': position - 4, 'kind': 'SequenceActionData.list-count-i32',
                    'actual': count, 'supportedLowerBound': -1}}
    if count > 0:
        first_action_tag = None
        if position < hard_limit:
            first_action_tag = {
                'offset': position,
                'firstByte': raw[position],
                'consumed': False,
            }
        return {'cursor': position, 'ranges': ranges, 'complete': False,
                'status': 'stopped-before-sequence-action-elements', 'header': header,
                'count': count, 'firstActionUnionTagPeekOnly': first_action_tag,
                'failure': (None if first_action_tag is not None else {
                    'category': 'truncated', 'offset': position,
                    'kind': 'SequenceActionData.firstActionUnionTag',
                    'expectedBytes': 1, 'remainingBytes': 0})}
    for index in range(2):
        if position >= hard_limit:
            return {'cursor': position, 'ranges': ranges, 'complete': False,
                    'status': 'truncated-sequence-action-tail', 'header': header,
                    'count': count, 'failure': {'category': 'truncated',
                        'offset': position, 'kind': f'SequenceActionData.trailing-byte[{index}]',
                        'expectedBytes': 1, 'remainingBytes': 0}}
        ranges.append({'start': position, 'end': position + 1,
                       'kind': f'SequenceActionData.trailing-byte[{index}]',
                       'value': raw[position]})
        position += 1
    return {'cursor': position, 'ranges': ranges, 'complete': True,
            'status': 'candidate-empty-sequence', 'header': header,
            'count': count, 'failure': None}


def _skilldata_sequence_tail_windows(sequence_reader, *, source):
    expected = {
        0x39C6EA2: '488B43500FB6288B7B3083EF017911BA01000000488BCBE882B2100284C0750D48FF4350FF4340FF4344897B30',
        0x39C6F07: '488B43500FB6288B7B3083EF017911BA01000000488BCBE81DB2100284C0750D48FF4350FF4340FF4344897B30',
    }
    windows = sequence_reader.get('windows')
    if not isinstance(windows, list):
        raise ContextError(source, 0x39C6EA2,
                           'SequenceActionData empty-list trailing byte read windows', windows)
    actual = {row.get('rva'): str(row.get('rawHex', '')).upper()
              for row in windows if isinstance(row, dict)}
    for rva, raw_hex in expected.items():
        require(actual.get(rva), raw_hex, source, rva)
    return [{'rva': rva, 'rawHex': actual[rva]} for rva in sorted(expected)]


def _skilldata_continue_play_animation_candidate(raw, start, hard_limit, *,
                                                  action_start,
                                                  root_read_order,
                                                  sequence_reader,
                                                  payload_helper_evidence,
                                                  source):
    """Replay the 0x115 selected reader field sequence without closing parents."""
    if len(root_read_order) != 16 or root_read_order[:4] != [
            'byte', 'scalar32', 'scalar32', 'scalar32']:
        raise ContextError(source, start,
                           'PlayAnimation member16 reader order after the shared fixed prefix',
                           root_read_order)
    if (payload_helper_evidence.get('sharedHelperTargetRva') != 0x2CA8700 or
            payload_helper_evidence.get('providerSelection') != 'unobserved'):
        raise ContextError(source, start,
                           'current helper identity with runtime provider kept unobserved',
                           payload_helper_evidence)
    sequence_tail_windows = _skilldata_sequence_tail_windows(
        sequence_reader, source=source)
    ranges = []
    opaque_payload_ranges = []
    position = start
    nested_sequence = None
    failure = None
    status = None
    for member_index, member_type in enumerate(root_read_order[4:], start=4):
        member_kind = f'PlayAnimationAction.member{member_index}'
        if member_type == 'byte-payload':
            payload = _skilldata_read_byte_payload_candidate(
                raw, position, hard_limit, kind=f'{member_kind}.byte-payload',
                source=source)
            ranges.extend(payload['ranges'])
            opaque_payload_ranges.extend(payload['opaquePayloadByteRanges'])
            position = payload['cursor']
            if not payload['complete']:
                status = f'{payload["status"]}-member{member_index}'
                failure = payload['failure']
                break
            continue
        if member_type == 'sequence':
            nested_sequence = _skilldata_read_sequence_data_candidate(
                raw, position, hard_limit, source=source)
            nested_sequence['ranges'] = [
                {**row, 'kind': f'{member_kind}.sequence.{row["kind"]}'}
                for row in nested_sequence['ranges']
            ]
            ranges.extend(nested_sequence['ranges'])
            position = nested_sequence['cursor']
            if not nested_sequence['complete']:
                status = nested_sequence['status']
                failure = nested_sequence['failure']
                break
            continue
        width = _skilldata_action_fixed_member_width(member_type)
        if width is None:
            status = 'stopped-before-unsupported-play-animation-member'
            failure = {'category': 'unsupported', 'offset': position,
                       'memberIndex': member_index, 'readType': member_type}
            break
        if hard_limit - position < width:
            status = 'truncated-play-animation-fixed-member'
            failure = {'category': 'truncated', 'offset': position,
                       'memberIndex': member_index, 'kind': member_type,
                       'expectedBytes': width, 'remainingBytes': hard_limit - position}
            break
        ranges.append({'start': position, 'end': position + width,
                       'kind': f'{member_kind}.{member_type}'})
        position += width
    else:
        status = 'candidate-play-animation-reader-field-sequence-exhausted'
    complete = status == 'candidate-play-animation-reader-field-sequence-exhausted'
    return {
        'cursor': position,
        'ranges': ranges,
        'opaquePayloadByteRanges': opaque_payload_ranges,
        'complete': complete,
        'status': status,
        'failure': failure,
        'recordEndCandidate': ({
            'start': action_start,
            'end': position,
            'memberCount': 16,
            'sourceReadOrderKey': 'member16',
            'classification': 'candidate selected-reader field-sequence end; live provider/cache unobserved',
        } if complete else None),
        'nestedSequence': nested_sequence,
        'independentlyVerifiedSequenceTailWindows': sequence_tail_windows,
        'bytePayloadEvidence': payload_helper_evidence,
    }


def _skilldata_force_sync_reader_evidence(timeline_reader, *,
                                          payload_helper_evidence,
                                          bool_helper_evidence,
                                          gameassembly_image_base,
                                          source):
    """Verify the exact current ForceSync reader order before replaying bytes."""
    timeline_members = timeline_reader.get('serializedMembers')
    if not isinstance(timeline_members, list) or len(timeline_members) != 4:
        raise ContextError(source, 0, 'four current TimelineActionData members',
                           timeline_members)
    force_sync_member = timeline_members[3]
    force_sync_method_spec = force_sync_member.get('readerMethodSpec', {})
    require((force_sync_member.get('serializedOrderIndex'),
             force_sync_member.get('fieldName'),
             force_sync_method_spec.get('index'),
             force_sync_method_spec.get('genericType', {}).get('typeDefinitionIndex'),
             force_sync_method_spec.get('genericType', {}).get('typeName')),
            (3, 'forceSyncAnimData', 620038, 9198,
             'Beyond.Gameplay.Core.TimelineAction+ForceSyncAnimData'),
            source, 0x32CD16F)

    force_reader = timeline_reader.get('forceSyncAnimDataReader')
    if not isinstance(force_reader, dict):
        raise ContextError(source, 0x32CE4B0,
                           'current ForceSyncAnimData selected-reader evidence',
                           force_reader)
    require((force_reader.get('typeDefinitionIndex'), force_reader.get('typeName')),
            (9198, 'Beyond.Gameplay.Core.TimelineAction+ForceSyncAnimData'),
            source, 0x32CE4B0)

    methods = timeline_reader.get('methods')
    if not isinstance(methods, list):
        raise ContextError(source, 0x32CE4B0,
                           'TimelineActionData/ForceSync reader module-token rows', methods)
    root_type = ('Beyond.MemoryPack.Beyond_Gameplay_Core_TimelineAction_'
                 'ForceSyncAnimDataForMemoryPack')
    root_methods = [row for row in methods if isinstance(row, dict) and
                    row.get('methodIndex') == 107909]
    if len(root_methods) != 1:
        raise ContextError(source, 0x32CE4B0,
                           'one current ForceSyncAnimData root Deserialize method',
                           len(root_methods))
    root_method = root_methods[0]
    require((root_method.get('declaringType'), root_method.get('name'),
             root_method.get('image'), root_method.get('pointerVa')),
            (root_type, 'Deserialize', 'MemoryPack.Beyond.dll',
             gameassembly_image_base + 0x32CE4B0), source, 0x32CE4B0)

    windows = timeline_reader.get('codeWindows')
    if not isinstance(windows, list):
        raise ContextError(source, 0x32CE4B0,
                           'hash-pinned ForceSyncAnimData reader/formatter windows', windows)
    expected_root_window = (
        0x32CE4B0, 0x32CE75C,
        '1FB17BEDE173176E0BC082E7C315267B6FC6F3CE76796DB90A627E9B0E9D7767')
    matches = [row for row in windows if isinstance(row, dict) and
               (row.get('startRva'), row.get('endRva'), row.get('sha256')) ==
               expected_root_window]
    if len(matches) != 1:
        raise ContextError(source, 0x32CE4B0,
                           'one exact ForceSyncAnimData root code window', matches)

    expected_header_and_stores = {
        (0x32CE57E, '4080FE04'),
        (0x32CE5A9, '884610'),
        (0x32CE5D9, '49894018'),
    }
    reader_windows = force_reader.get('verifiedInstructionWindows')
    if not isinstance(reader_windows, list):
        raise ContextError(source, 0x32CE57E,
                           'ForceSync member-count and member-store instruction evidence',
                           reader_windows)
    actual_header_and_stores = {
        (row.get('rva'), str(row.get('rawHex', '')).upper())
        for row in reader_windows if isinstance(row, dict)
    }
    require(actual_header_and_stores, expected_header_and_stores, source, 0x32CE57E)

    members = force_reader.get('serializedMembers')
    if not isinstance(members, list) or len(members) != 4:
        raise ContextError(source, 0x32CE4B0,
                           'four current ForceSyncAnimData serialized members', members)
    expected_members = [
        (0, 'forceSync', 0x10, 'bool'),
        (1, 'montageName', 0x18, 'System.String'),
        (2, 'playbackSpeed', 0x24, 'System.Single'),
        (3, 'targetFrame', 0x20, 'System.Int32'),
    ]
    require([(row.get('serializedOrderIndex'), row.get('fieldName'),
              row.get('objectField', {}).get('fieldOffset'),
              row.get('objectField', {}).get('fieldType', {}).get('wireType'))
             for row in members], expected_members, source, 0x32CE4B0)
    for row in members:
        require(row.get('objectField', {}).get('typeDefinitionIndex'), 9198,
                source, row.get('serializedOrderIndex'))

    force_sync_reader = members[0].get('reader', {})
    montage_reader = members[1].get('reader', {})
    require((force_sync_reader.get('callInstructionRva'),
             force_sync_reader.get('callInstructionHex'),
             force_sync_reader.get('targetRva'), force_sync_reader.get('role')),
            (0x32CE58E, 'E82DA39DFF', 0x2CA88C0, 'read forceSync boolean'),
            source, 0x32CE58E)
    require((montage_reader.get('callInstructionRva'),
             montage_reader.get('callInstructionHex'),
             montage_reader.get('targetRva'), montage_reader.get('role')),
            (0x32CE5B2, 'E849A19DFF', 0x2CA8700, 'read montageName string'),
            source, 0x32CE5B2)

    scalar_expectations = {
        'playbackSpeed': (
            'inline-float32', 4,
            {(0x32CE635, 'F30F1030'), (0x32CE652, '4883435004'),
             (0x32CE67B, 'F30F117024')}),
        'targetFrame': (
            'inline-int32', 4,
            {(0x32CE69A, '8B28'), (0x32CE6B5, '4883435004'),
             (0x32CE6D8, '896820')}),
    }
    for field_name, (kind, byte_width, expected_instructions) in scalar_expectations.items():
        reader = next(row for row in members if row.get('fieldName') == field_name).get('reader', {})
        require((reader.get('kind'), reader.get('byteWidth')),
                (kind, byte_width), source, 0x32CE4B0)
        instructions = reader.get('verifiedInstructions')
        if not isinstance(instructions, list):
            raise ContextError(source, 0x32CE4B0,
                               f'{field_name} inline source-cursor instructions', instructions)
        actual_instructions = {
            (row.get('rva'), str(row.get('rawHex', '')).upper())
            for row in instructions if isinstance(row, dict)
        }
        require(actual_instructions, expected_instructions, source, 0x32CE4B0)

    shared_bool_reads = bool_helper_evidence.get('verifiedSharedHelperReads')
    if not isinstance(shared_bool_reads, list):
        raise ContextError(source, 0x2CA88C0,
                           'independent one-byte shared boolean-helper reader evidence',
                           shared_bool_reads)
    expected_shared_bool_reads = {
        (0x377410A, 0x2CA88C0, 1),
        (0x37741A1, 0x2CA88C0, 1),
    }
    actual_shared_bool_reads = {
        (row.get('callInstructionRva'), row.get('targetRva'),
         row.get('fastSerializedWidth'))
        for row in shared_bool_reads if isinstance(row, dict) and
        row.get('targetRva') == 0x2CA88C0
    }
    require(actual_shared_bool_reads, expected_shared_bool_reads,
            source, 0x2CA88C0)
    require((payload_helper_evidence.get('sharedHelperTargetRva'),
             payload_helper_evidence.get('providerSelection')),
            (0x2CA8700, 'unobserved'), source, 0x2CA8700)

    return {
        'timelineForceSyncMethodSpecIndex': 620038,
        'forceSyncTypeDefinitionIndex': 9198,
        'forceSyncRootMethodIndex': 107909,
        'forceSyncRootRva': 0x32CE4B0,
        'forceSyncRootCodeWindow': dict(matches[0]),
        'memberCountHeader': 4,
        'serializedMembers': [
            {'serializedOrderIndex': index, 'fieldName': field_name,
             'byteWidth': (1 if index == 0 else None if index == 1 else 4),
             'readerTargetRva': (0x2CA88C0 if index == 0 else
                                 0x2CA8700 if index == 1 else None)}
            for index, field_name, _, _ in expected_members],
        'sharedOneByteHelperEvidence': {
            'sourceRootRva': 0x3774060,
            'verifiedCallSites': [dict(row) for row in shared_bool_reads
                                  if row.get('targetRva') == 0x2CA88C0],
        },
        'sharedSignedLengthPayloadHelperTargetRva': 0x2CA8700,
        'runtimeProviderSelection': 'unobserved',
    }


def _skilldata_read_force_sync_candidate(raw, start, hard_limit, *,
                                         timeline_reader,
                                         payload_helper_evidence,
                                         bool_helper_evidence,
                                         gameassembly_image_base,
                                         source):
    """Consume the selected ForceSync reader's bounded field sequence only."""
    evidence = _skilldata_force_sync_reader_evidence(
        timeline_reader, payload_helper_evidence=payload_helper_evidence,
        bool_helper_evidence=bool_helper_evidence,
        gameassembly_image_base=gameassembly_image_base, source=source)
    if start < 0 or hard_limit < start or hard_limit > len(raw):
        raise ContextError(source, start,
                           'ForceSync candidate start and hard limit inside current raw bytes',
                           {'start': start, 'hardLimit': hard_limit,
                            'rawLength': len(raw)})
    ranges = []
    opaque_payload_ranges = []
    if hard_limit - start < 1:
        return {'cursor': start, 'ranges': ranges,
                'opaquePayloadByteRanges': opaque_payload_ranges,
                'complete': False, 'status': 'truncated-force-sync-member-header',
                'failure': {'category': 'truncated', 'offset': start,
                            'kind': 'ForceSyncAnimData.member-header',
                            'expectedBytes': 1, 'remainingBytes': 0},
                'recordEndCandidate': None, 'readerEvidence': evidence}
    header = raw[start]
    position = start + 1
    ranges.append({'start': start, 'end': position,
                   'kind': 'ForceSyncAnimData.member-header', 'value': header})
    if header != 4:
        return {'cursor': position, 'ranges': ranges,
                'opaquePayloadByteRanges': opaque_payload_ranges,
                'complete': False, 'status': 'malformed-force-sync-member-count',
                'failure': {'category': 'member-count', 'offset': start,
                            'expected': 4, 'actual': header},
                'recordEndCandidate': None, 'readerEvidence': evidence}
    if hard_limit - position < 1:
        return {'cursor': position, 'ranges': ranges,
                'opaquePayloadByteRanges': opaque_payload_ranges,
                'complete': False, 'status': 'truncated-force-sync-forceSync',
                'failure': {'category': 'truncated', 'offset': position,
                            'kind': 'ForceSyncAnimData.member0.forceSync.byte',
                            'expectedBytes': 1, 'remainingBytes': 0},
                'recordEndCandidate': None, 'readerEvidence': evidence}
    ranges.append({'start': position, 'end': position + 1,
                   'kind': 'ForceSyncAnimData.member0.forceSync.byte',
                   'value': raw[position],
                   'rawHex': raw[position:position + 1].hex().upper()})
    position += 1

    montage = _skilldata_read_byte_payload_candidate(
        raw, position, hard_limit,
        kind='ForceSyncAnimData.member1.montageName', source=source)
    ranges.extend(montage['ranges'])
    opaque_payload_ranges.extend(montage['opaquePayloadByteRanges'])
    position = montage['cursor']
    if not montage['complete']:
        return {'cursor': position, 'ranges': ranges,
                'opaquePayloadByteRanges': opaque_payload_ranges,
                'complete': False,
                'status': f'{montage["status"]}-montageName',
                'failure': montage['failure'], 'recordEndCandidate': None,
                'readerEvidence': evidence, 'montageNameLength': montage['length']}

    for member_index, field_name, kind in (
            (2, 'playbackSpeed', 'float32'),
            (3, 'targetFrame', 'int32')):
        if hard_limit - position < 4:
            return {'cursor': position, 'ranges': ranges,
                    'opaquePayloadByteRanges': opaque_payload_ranges,
                    'complete': False,
                    'status': f'truncated-force-sync-{field_name}',
                    'failure': {'category': 'truncated', 'offset': position,
                                'kind': f'ForceSyncAnimData.member{member_index}.{field_name}.{kind}',
                                'expectedBytes': 4,
                                'remainingBytes': hard_limit - position},
                    'recordEndCandidate': None, 'readerEvidence': evidence,
                    'montageNameLength': montage['length']}
        ranges.append({'start': position, 'end': position + 4,
                       'kind': f'ForceSyncAnimData.member{member_index}.{field_name}.{kind}',
                       'rawHex': raw[position:position + 4].hex().upper()})
        position += 4
    return {
        'cursor': position, 'ranges': ranges,
        'opaquePayloadByteRanges': opaque_payload_ranges,
        'complete': True,
        'status': 'candidate-force-sync-reader-field-sequence-exhausted',
        'failure': None,
        'recordEndCandidate': {
            'start': start, 'end': position, 'memberCount': 4,
            'sourceReadOrderKey': 'member4',
            'classification': 'candidate selected-reader field-sequence end; live provider/cache unobserved',
        },
        'readerEvidence': evidence,
        'montageNameLength': montage['length'],
    }


def _skilldata_read_following_timeline_action_data_prefix_candidate(
        raw, start, hard_limit, *, timeline_reader, sequence_reader,
        payload_helper_evidence, bool_helper_evidence,
        gameassembly_image_base, source):
    """Replay the next timeline element through its first nested action tag."""
    timeline_windows = timeline_reader.get('codeWindows')
    if not isinstance(timeline_windows, list) or not any(
            (row.get('startRva'), row.get('endRva'), row.get('sha256')) ==
            (0x32CCF70, 0x32CD277,
             'CB497F6362D9DA9396D6533F6CC037536FC9499D67848F1E8BBBAC8AA2F03688')
            for row in timeline_windows if isinstance(row, dict)):
        raise ContextError(source, 0x32CCF70,
                           'hash-pinned current TimelineActionData root reader', timeline_windows)
    timeline_members = timeline_reader.get('serializedMembers')
    if not isinstance(timeline_members, list) or len(timeline_members) != 4:
        raise ContextError(source, start, 'four current TimelineActionData member readers',
                           timeline_members)
    end_frame = timeline_members[0].get('reader', {})
    require((end_frame.get('callInstructionRva'), end_frame.get('callInstructionHex'),
             end_frame.get('targetRva'), end_frame.get('role')),
            (0x32CD05E, 'E84DB69DFF', 0x2CA86B0, 'read endFrame int32'),
            source, 0x32CD05E)
    header_windows = timeline_reader.get('verifiedInstructionWindows')
    if not isinstance(header_windows, list):
        raise ContextError(source, 0x32CD04E,
                           'TimelineActionData member-count header instruction evidence',
                           header_windows)
    require(any((row.get('rva'), str(row.get('rawHex', '')).upper()) ==
                (0x32CD04E, '4080FE04')
                for row in header_windows if isinstance(row, dict)), True,
            source, 0x32CD04E)

    shared_reads = bool_helper_evidence.get('verifiedSharedHelperReads')
    if not isinstance(shared_reads, list):
        raise ContextError(source, 0x2CA86B0,
                           'independent four-byte reader-helper evidence', shared_reads)
    expected_end_frame_witness = (0x3774135, 0x2CA86B0, 4)
    actual_shared_reads = {
        (row.get('callInstructionRva'), row.get('targetRva'),
         row.get('fastSerializedWidth'))
        for row in shared_reads if isinstance(row, dict)
    }
    require(expected_end_frame_witness in actual_shared_reads, True,
            source, 0x2CA86B0)
    _skilldata_sequence_tail_windows(sequence_reader, source=source)

    if start < 0 or hard_limit < start or hard_limit > len(raw):
        raise ContextError(source, start,
                           'following TimelineActionData start and hard limit inside raw bytes',
                           {'start': start, 'hardLimit': hard_limit,
                            'rawLength': len(raw)})
    ranges = []
    position = start
    if hard_limit - position < 1:
        return {'start': start, 'cursor': position, 'ranges': ranges,
                'status': 'truncated-following-timeline-action-member-header',
                'failure': {'category': 'truncated', 'offset': position,
                            'kind': 'TimelineActionData.member-header',
                            'expectedBytes': 1, 'remainingBytes': 0},
                'firstActionUnionTagPeekOnly': None,
                'candidateRecordEnd': None}
    header = raw[position]
    ranges.append({'start': position, 'end': position + 1,
                   'kind': 'TimelineActionData.member-header', 'value': header})
    position += 1
    if header != 4:
        return {'start': start, 'cursor': position, 'ranges': ranges,
                'status': 'malformed-following-timeline-action-member-count',
                'failure': {'category': 'member-count', 'offset': start,
                            'expected': 4, 'actual': header},
                'firstActionUnionTagPeekOnly': None,
                'candidateRecordEnd': None}
    if hard_limit - position < 4:
        return {'start': start, 'cursor': position, 'ranges': ranges,
                'status': 'truncated-following-timeline-action-end-frame',
                'failure': {'category': 'truncated', 'offset': position,
                            'kind': 'TimelineActionData.member0.endFrame.i32',
                            'expectedBytes': 4, 'remainingBytes': hard_limit - position},
                'firstActionUnionTagPeekOnly': None,
                'candidateRecordEnd': None}
    ranges.append({'start': position, 'end': position + 4,
                   'kind': 'TimelineActionData.member0.endFrame.i32',
                   'rawHex': raw[position:position + 4].hex().upper()})
    position += 4

    sequence_start = position
    sequence = _skilldata_read_sequence_data_candidate(
        raw, position, hard_limit, source=source)
    sequence['ranges'] = [
        {**row, 'kind': f'TimelineActionData.member1.{row["kind"]}'}
        for row in sequence['ranges']]
    ranges.extend(sequence['ranges'])
    position = sequence['cursor']
    tag_peek = sequence.get('firstActionUnionTagPeekOnly')
    if isinstance(tag_peek, dict):
        first_byte = tag_peek['firstByte']
        tag_width = 3 if first_byte == 0xFA else 1
        remaining = hard_limit - tag_peek['offset']
        if tag_width > remaining:
            tag_peek = {
                **tag_peek, 'tag': None, 'tagWidth': tag_width,
                'encodingHex': raw[tag_peek['offset']:hard_limit].hex().upper(),
            }
            return {
                'start': start, 'cursor': position, 'ranges': ranges,
                'status': 'truncated-following-timeline-action-tag',
                'failure': {'category': 'truncated-action-tag',
                            'offset': tag_peek['offset'],
                            'expected': {'bytes': tag_width},
                            'actual': {'remaining': remaining}},
                'timelineSequenceCount': sequence.get('count'),
                'timelineSequenceStart': sequence_start,
                'firstActionUnionTagPeekOnly': tag_peek,
                'candidateRecordEnd': None,
            }
        tag_peek = {
            **tag_peek,
            'tag': (struct.unpack_from('<H', raw, tag_peek['offset'] + 1)[0]
                    if tag_width == 3 else first_byte),
            'tagWidth': tag_width,
            'encodingHex': raw[tag_peek['offset']:tag_peek['offset'] + tag_width].hex().upper(),
        }

    if not sequence['complete']:
        status = ('stopped-before-following-timeline-sequence-action'
                  if sequence.get('status') == 'stopped-before-sequence-action-elements'
                  else sequence.get('status', 'ambiguous-following-timeline-sequence'))
        return {
            'start': start, 'cursor': position, 'ranges': ranges,
            'status': status, 'failure': sequence.get('failure'),
            'timelineSequenceCount': sequence.get('count'),
            'timelineSequenceStart': sequence_start,
            'timelineSequenceStatus': sequence.get('status'),
            'firstActionUnionTagPeekOnly': tag_peek,
            'candidateRecordEnd': None,
            'nextSourceReadType': 'TimelineActionData.member1.SequenceActionData action element',
            'nextSourceReadOffset': position,
            'nextSourceReadConsumed': False,
        }

    start_frame = timeline_members[2].get('reader', {})
    expected_start_frame = {
        (53268774, '448B30'), (53268802, '4883435004'),
        (53268807, '83434004'), (53268811, '83434404'),
    }
    actual_start_frame = {
        (row.get('rva'), str(row.get('rawHex', '')).upper())
        for row in start_frame.get('verifiedInstructions', [])
        if isinstance(row, dict)
    }
    require(actual_start_frame, expected_start_frame, source, position)
    if hard_limit - position < 4:
        return {'start': start, 'cursor': position, 'ranges': ranges,
                'status': 'truncated-following-timeline-action-start-frame',
                'failure': {'category': 'truncated', 'offset': position,
                            'kind': 'TimelineActionData.member2.startFrame.i32',
                            'expectedBytes': 4, 'remainingBytes': hard_limit - position},
                'timelineSequenceCount': sequence.get('count'),
                'timelineSequenceStart': sequence_start,
                'firstActionUnionTagPeekOnly': None,
                'candidateRecordEnd': None}
    ranges.append({'start': position, 'end': position + 4,
                   'kind': 'TimelineActionData.member2.startFrame.i32',
                   'rawHex': raw[position:position + 4].hex().upper()})
    position += 4
    force_sync = _skilldata_read_force_sync_candidate(
        raw, position, hard_limit, timeline_reader=timeline_reader,
        payload_helper_evidence=payload_helper_evidence,
        bool_helper_evidence=bool_helper_evidence,
        gameassembly_image_base=gameassembly_image_base, source=source)
    ranges.extend(force_sync['ranges'])
    position = force_sync['cursor']
    candidate_end = None
    if force_sync['complete']:
        candidate_end = {
            'start': start, 'end': position, 'memberCount': 4,
            'sourceReadOrderKey': 'member4',
            'classification': 'candidate selected TimelineActionData field-sequence end; live provider/cache unobserved',
        }
    return {
        'start': start, 'cursor': position, 'ranges': ranges,
        'status': (('candidate-following-timeline-action-field-sequence-exhausted'
                    if force_sync['complete'] else force_sync['status'])),
        'failure': force_sync.get('failure'),
        'timelineSequenceCount': sequence.get('count'),
        'timelineSequenceStart': sequence_start,
        'timelineSequenceStatus': sequence.get('status'),
        'firstActionUnionTagPeekOnly': tag_peek,
        'forceSyncAnimDataRecordEndCandidate': force_sync.get('recordEndCandidate'),
        'candidateRecordEnd': candidate_end,
        'forceSyncAnimDataReaderEvidence': force_sync['readerEvidence'],
        'opaquePayloadByteRanges': force_sync['opaquePayloadByteRanges'],
        'nextSourceReadType': ('next TimelineActionData list element'
                               if force_sync['complete'] else
                               force_sync.get('failure', {}).get('kind')),
        'nextSourceReadOffset': position,
        'nextSourceReadConsumed': False if force_sync['complete'] else None,
    }


def _skilldata_continue_following_play_animation_candidate(
        raw, following_timeline, hard_limit, *, timeline_actions_list_count,
        timeline_reader, sequence_reader, action_group_members, buff_routes,
        action_readers, payload_helper_evidence, bool_helper_evidence,
        gameassembly_image_base, source):
    """Continue a second TimelineActionData only for its exact 0x115 child path."""
    peek = following_timeline.get('firstActionUnionTagPeekOnly')
    if not isinstance(peek, dict) or peek.get('tag') != 0x115 or peek.get('tagWidth') != 3:
        raise ContextError(source, following_timeline.get('cursor', 0),
                           'non-consuming extended 0x115 child tag peek', peek)
    if following_timeline.get('timelineSequenceCount') != 1:
        raise ContextError(source, peek.get('offset', 0),
                           'one child in the second TimelineActionData SequenceActionData',
                           following_timeline.get('timelineSequenceCount'))
    reader = action_readers.get(0x115)
    if not isinstance(reader, dict):
        raise ContextError(source, peek['offset'],
                           'current 0x115 PlayAnimation selected reader', reader)
    union_evidence = skilldata_action_union_static_reader_evidence(
        0x115, reader, buff_routes,
        gameassembly_image_base=gameassembly_image_base, source=source)
    root_member_count = union_evidence.get('rootMemberCount')
    root_read_order = union_evidence.get('rootAnonymousReadOrder')
    require((root_member_count, union_evidence.get('rootReadOrderKey'),
             root_read_order[:4] if isinstance(root_read_order, list) else None),
            (16, 'member16', ['byte', 'scalar32', 'scalar32', 'scalar32']),
            source, peek['offset'])
    start = peek['offset']
    encoded_tag = bytes.fromhex(str(peek.get('encodingHex', '')))
    require((raw[start:start + 3], encoded_tag),
            (b'\xFA\x15\x01', b'\xFA\x15\x01'), source, start)
    header_offset = start + 3
    if header_offset >= hard_limit or raw[header_offset] != root_member_count:
        return {
            'cursor': start, 'ranges': [], 'opaquePayloadByteRanges': [],
            'status': 'stopped-before-following-play-animation-member-header',
            'failure': {'category': ('truncated' if header_offset >= hard_limit
                                     else 'member-count'),
                        'offset': header_offset, 'expected': root_member_count,
                        'actual': raw[header_offset] if header_offset < hard_limit else None},
            'candidatePlayAnimationRecordEnd': None,
            'candidateTimelineActionDataRecordEnd': None,
            'candidateActionGroupDataRecordEnd': None,
            'candidateTimelineContinuation': None,
            'readerEvidence': union_evidence,
        }
    position = header_offset + 1
    ranges = [
        {'start': start, 'end': header_offset,
         'kind': 'AbilityActionData.union-tag'},
        {'start': header_offset, 'end': position,
         'kind': 'PlayAnimationAction.memberCount'},
    ]
    fixed_members = []
    for member_index, member_type in enumerate(root_read_order[:4]):
        width = _skilldata_action_fixed_member_width(member_type)
        if width is None:
            raise ContextError(source, position,
                               'four current fixed 0x115 prefix member widths', member_type)
        if hard_limit - position < width:
            return {
                'cursor': position, 'ranges': ranges,
                'opaquePayloadByteRanges': [],
                'status': 'truncated-following-play-animation-fixed-prefix',
                'failure': {'category': 'truncated', 'offset': position,
                            'memberIndex': member_index, 'kind': member_type,
                            'expectedBytes': width,
                            'remainingBytes': hard_limit - position},
                'candidatePlayAnimationRecordEnd': None,
                'candidateTimelineActionDataRecordEnd': None,
                'candidateActionGroupDataRecordEnd': None,
                'candidateTimelineContinuation': None,
                'readerEvidence': union_evidence,
            }
        ranges.append({'start': position, 'end': position + width,
                       'kind': f'PlayAnimationAction.member{member_index}.{member_type}'})
        fixed_members.append(member_type)
        position += width

    require((payload_helper_evidence.get('actionTag'),
             payload_helper_evidence.get('sharedHelperTargetRva'),
             payload_helper_evidence.get('providerSelection')),
            (0x115, 0x2CA8700, 'unobserved'), source, start)
    payload_helper = payload_helper_evidence
    play_animation = _skilldata_continue_play_animation_candidate(
        raw, position, hard_limit, action_start=start,
        root_read_order=root_read_order, sequence_reader=sequence_reader,
        payload_helper_evidence=payload_helper, source=source)
    ranges.extend(play_animation['ranges'])
    position = play_animation['cursor']
    if not play_animation['complete']:
        return {
            'cursor': position, 'ranges': ranges,
            'opaquePayloadByteRanges': play_animation['opaquePayloadByteRanges'],
            'status': play_animation['status'], 'failure': play_animation['failure'],
            'candidatePlayAnimationRecordEnd': play_animation['recordEndCandidate'],
            'candidateTimelineActionDataRecordEnd': None,
            'candidateActionGroupDataRecordEnd': None,
            'candidateTimelineContinuation': None,
            'candidatePlayAnimationNestedSequence': play_animation.get('nestedSequence'),
            'readerEvidence': union_evidence,
            'bytePayloadHelperEvidence': payload_helper,
        }

    parent = _skilldata_continue_timeline_parent_candidate(
        raw, position, hard_limit, sequence_action_count=1,
        timeline_actions_list_count=timeline_actions_list_count,
        timeline_action_start=following_timeline['start'],
        timeline_reader=timeline_reader,
        sequence_tail_windows=play_animation['independentlyVerifiedSequenceTailWindows'],
        action_group_members=action_group_members,
        payload_helper_evidence=payload_helper,
        bool_helper_evidence=bool_helper_evidence,
        gameassembly_image_base=gameassembly_image_base,
        source=source)
    ranges.extend(parent['ranges'])
    position = parent['cursor']
    opaque_payload_ranges = [*play_animation['opaquePayloadByteRanges'],
                             *parent.get('opaquePayloadByteRanges', [])]
    return {
        'cursor': position, 'ranges': ranges,
        'opaquePayloadByteRanges': opaque_payload_ranges,
        'status': parent['status'], 'failure': parent.get('failure'),
        'candidatePlayAnimationRecordEnd': play_animation['recordEndCandidate'],
        'candidateTimelineActionDataRecordEnd': parent.get(
            'candidateTimelineActionDataRecordEnd'),
        'candidateActionGroupDataRecordEnd': parent.get(
            'candidateActionGroupDataRecordEnd'),
        'candidateTimelineContinuation': parent,
        'candidatePlayAnimationNestedSequence': play_animation.get('nestedSequence'),
        'readerEvidence': union_evidence,
        'bytePayloadHelperEvidence': payload_helper,
    }


def _skilldata_continue_timeline_parent_candidate(raw, start, hard_limit, *,
                                                   sequence_action_count,
                                                   timeline_actions_list_count,
                                                   timeline_action_start,
                                                   timeline_reader,
                                                   sequence_tail_windows,
                                                   action_group_members,
                                                   payload_helper_evidence,
                                                   bool_helper_evidence,
                                                   gameassembly_image_base,
                                                   source):
    """Continue one completed 0x115 child through its proven enclosing prefixes."""
    ranges = []
    position = start
    if sequence_action_count != 1:
        return {
            'cursor': position, 'ranges': ranges,
            'status': 'stopped-before-additional-sequence-action',
            'failure': None,
            'sequenceActionCount': sequence_action_count,
            'nextSourceReadType': 'next SequenceActionData action or trailing bytes',
            'nextSourceReadOffset': position,
        }
    for index in range(2):
        if position >= hard_limit:
            return {
                'cursor': position, 'ranges': ranges,
                'status': 'truncated-timeline-sequence-action-data-tail',
                'failure': {'category': 'truncated', 'offset': position,
                            'kind': f'TimelineActionData.member1.SequenceActionData.trailing-byte[{index}]',
                            'expectedBytes': 1, 'remainingBytes': 0},
                'sequenceActionCount': sequence_action_count,
                'nextSourceReadType': f'TimelineActionData.member1.SequenceActionData.trailing-byte[{index}]',
                'nextSourceReadOffset': position,
            }
        ranges.append({'start': position, 'end': position + 1,
                       'kind': f'TimelineActionData.member1.SequenceActionData.trailing-byte[{index}]',
                       'value': raw[position]})
        position += 1

    timeline_members = timeline_reader.get('serializedMembers')
    if not isinstance(timeline_members, list) or len(timeline_members) != 4:
        raise ContextError(source, position, 'four current TimelineActionData members',
                           timeline_members)
    start_frame = timeline_members[2].get('reader', {})
    expected_start_frame_instructions = {
        (53268774, '448B30'),
        (53268802, '4883435004'),
        (53268807, '83434004'),
        (53268811, '83434404'),
    }
    instructions = start_frame.get('verifiedInstructions')
    if not isinstance(instructions, list):
        raise ContextError(source, position,
                           'verified TimelineActionData startFrame source cursor instructions',
                           instructions)
    actual = {(row.get('rva'), row.get('rawHex')) for row in instructions
              if isinstance(row, dict)}
    require(actual, expected_start_frame_instructions, source, position)
    require((timeline_members[2].get('fieldName'), start_frame.get('kind'),
             start_frame.get('byteWidth')),
            ('_startFrame', 'inline-int32', 4), source, position)
    if hard_limit - position < 4:
        return {
            'cursor': position, 'ranges': ranges,
            'status': 'truncated-timeline-action-start-frame',
            'failure': {'category': 'truncated', 'offset': position,
                        'kind': 'TimelineActionData.member2.startFrame.i32',
                        'expectedBytes': 4, 'remainingBytes': hard_limit - position},
            'sequenceActionCount': sequence_action_count,
            'nextSourceReadType': 'TimelineActionData.member2.startFrame.i32',
            'nextSourceReadOffset': position,
        }
    ranges.append({'start': position, 'end': position + 4,
                   'kind': 'TimelineActionData.member2.startFrame.i32',
                   'rawHex': raw[position:position + 4].hex().upper()})
    position += 4
    force_sync_start = position
    force_sync = _skilldata_read_force_sync_candidate(
        raw, force_sync_start, hard_limit, timeline_reader=timeline_reader,
        payload_helper_evidence=payload_helper_evidence,
        bool_helper_evidence=bool_helper_evidence,
        gameassembly_image_base=gameassembly_image_base, source=source)
    ranges.extend(force_sync['ranges'])
    position = force_sync['cursor']
    common = {
        'sequenceActionCount': sequence_action_count,
        'timelineActionsListCount': timeline_actions_list_count,
        'sequenceTailEvidence': sequence_tail_windows,
        'timelineStartFrameEvidence': [
            {'rva': rva, 'rawHex': raw_hex}
            for rva, raw_hex in sorted(expected_start_frame_instructions)],
        'forceSyncAnimDataStart': force_sync_start,
        'forceSyncAnimDataContinuation': {
            'status': force_sync['status'],
            'cursor': force_sync['cursor'],
            'failure': force_sync['failure'],
            'montageNameLength': force_sync.get('montageNameLength'),
            'recordEndCandidate': force_sync.get('recordEndCandidate'),
            'readerEvidence': force_sync['readerEvidence'],
        },
        'forceSyncAnimDataRecordEndCandidate': force_sync.get('recordEndCandidate'),
        'opaquePayloadByteRanges': force_sync['opaquePayloadByteRanges'],
    }
    if not force_sync['complete']:
        return {
            'cursor': position, 'ranges': ranges,
            'status': force_sync['status'], 'failure': force_sync['failure'],
            'nextSourceReadType': (force_sync['failure'].get('kind')
                                   if isinstance(force_sync.get('failure'), dict)
                                   else 'ForceSyncAnimData remaining member reads'),
            'nextSourceReadOffset': position,
            'nextSourceReadConsumed': False,
            'classification': 'candidate TimelineActionData prefix; ForceSync reader incomplete',
            **common,
        }

    if type(timeline_action_start) is not int or not 0 <= timeline_action_start < force_sync_start:
        raise ContextError(source, force_sync_start,
                           'TimelineActionData start preceding its ForceSync child',
                           timeline_action_start)
    timeline_record_end = {
        'start': timeline_action_start, 'end': position,
        'memberCount': 4, 'sourceReadOrderKey': 'member4',
        'classification': 'candidate selected TimelineActionData field-sequence end; live provider/cache unobserved',
    }
    common['candidateTimelineActionDataRecordEnd'] = timeline_record_end

    if type(timeline_actions_list_count) is not int or timeline_actions_list_count < 1:
        return {
            'cursor': position, 'ranges': ranges,
            'status': 'unsupported-timeline-actions-list-count',
            'failure': {'category': 'unsupported',
                        'offset': timeline_action_start,
                        'actual': timeline_actions_list_count,
                        'supportedLowerBound': 1},
            'nextSourceReadType': None,
            'nextSourceReadOffset': position,
            'nextSourceReadConsumed': None,
            'classification': 'candidate TimelineActionData end; ActionGroupData list extent unsupported',
            **common,
        }

    if timeline_actions_list_count == 1:
        if not isinstance(action_group_members, list) or len(action_group_members) != 2:
            raise ContextError(source, 1, 'two current ActionGroupData serialized members',
                               action_group_members)
        require([row.get('serializedOrderIndex') for row in action_group_members],
                [0, 1], source, 1)
        require([row.get('fieldName') for row in action_group_members],
                ['passiveEventActions', 'timelineActions'], source, 1)
        action_group_end = {
            'start': 1, 'end': position, 'memberCount': 2,
            'sourceReadOrderKey': 'member2',
            'classification': 'candidate ActionGroupData field-sequence end; SkillData remains open',
        }
        return {
            'cursor': position, 'ranges': ranges,
            'status': 'candidate-actiongroup-reader-field-sequence-exhausted',
            'failure': None,
            'candidateActionGroupDataRecordEnd': action_group_end,
            'nextSourceReadType': 'next SkillData member after ActionGroupData',
            'nextSourceReadOffset': position,
            'nextSourceReadConsumed': False,
            'classification': 'candidate ActionGroupData field-sequence end; whole SkillData remains open',
            **common,
        }

    return {
        'cursor': position, 'ranges': ranges,
        'status': 'stopped-before-additional-timeline-action-data',
        'failure': None,
        'nextSourceReadType': 'next TimelineActionData list element',
        'nextSourceReadOffset': position,
        'nextSourceReadConsumed': False,
        'classification': 'candidate first TimelineActionData end; remaining list and parents remain open',
        **common,
    }


def skilldata_timeline_branch_static_alignment(
        witness, raw, skilldata_reader_order, sequence_reader, buff_routes,
        buff_action_readers, c9_prefix_evidence, *,
        gameassembly_image_base=0x180000000,
        byte_payload_helper_evidence=None, source):
    """Add typed native alignment and only bounded first-child prefixes to a candidate cursor."""
    if not isinstance(witness, dict) or not isinstance(raw, bytes):
        raise ContextError(source, 0, 'current timeline candidate witness and raw bytes',
                           [type(witness).__name__, type(raw).__name__])
    if not all(isinstance(value, dict) for value in
               (skilldata_reader_order, sequence_reader, buff_routes)):
        raise ContextError(source, 0, 'SkillData, Sequence and action-route native evidence objects',
                           [type(skilldata_reader_order).__name__, type(sequence_reader).__name__,
                            type(buff_routes).__name__])
    if not isinstance(buff_action_readers, dict) or any(
            type(tag) is not int or not isinstance(reader, dict)
            for tag, reader in buff_action_readers.items()):
        raise ContextError(source, 0, 'current tag-to-native action reader map',
                           type(buff_action_readers).__name__)
    input_set = witness.get('inputSetSha256')
    require(skilldata_reader_order.get('inputSetSha256'), input_set, source, 0)
    require(witness.get('hardLimit'), len(raw), source, 0)
    require(witness.get('logicalSha256'), hashlib.sha256(raw).hexdigest().upper(), source, 0)
    require(witness.get('authoritativeParserCursor'), 10, source, 0)
    require(witness.get('candidateStart'), 10, source, 0)
    if not isinstance(witness.get('candidateByteRanges'), list):
        raise ContextError(source, witness.get('candidateCursor', 10),
                           'candidate byte-range manifest', witness.get('candidateByteRanges'))

    require(skilldata_reader_order.get('firstSkillDataField', {}).get('fieldName'),
            'actionGroupData', source, 0)
    action_group_members = skilldata_reader_order.get('actionGroupDataMembers')
    if not isinstance(action_group_members, list) or len(action_group_members) != 2:
        raise ContextError(source, 1, 'two native ActionGroupData member reads',
                           action_group_members)
    require([row.get('fieldName') for row in action_group_members],
            ['passiveEventActions', 'timelineActions'], source, 1)
    require([row.get('serializedOrderIndex') for row in action_group_members],
            [0, 1], source, 1)
    require([row.get('readerMethodSpec', {}).get('index')
             for row in action_group_members], [610662, 610915], source, 1)
    first_list_type = action_group_members[0].get('readerMethodSpec', {}).get('genericType', {})
    timeline_list_type = action_group_members[1].get('readerMethodSpec', {}).get('genericType', {})
    require((first_list_type.get('typeName'), first_list_type.get('elementTypeName')),
            ('System.Collections.Generic.List`1',
             'Beyond.Gameplay.Core.AbilityActionMap'), source, 2)
    require((timeline_list_type.get('typeName'), timeline_list_type.get('elementTypeName'),
             timeline_list_type.get('elementTypeDefinitionIndex')),
            ('System.Collections.Generic.List`1',
             'Beyond.Gameplay.Core.TimelineAction+TimelineActionData', 9199), source, 6)
    action_group_windows = skilldata_reader_order.get('codeWindows')
    if not isinstance(action_group_windows, list) or not any(
            (row.get('rva'), row.get('byteLength'), row.get('sha256')) ==
            (58581179, 2314,
             'FEA359985EBF5DF75CC58D871469481F0F692B1768D84724FF5941D47CAD8132')
            for row in action_group_windows):
        raise ContextError(source, 1, 'hash-pinned SkillData/ActionGroupData root reader window',
                           action_group_windows)
    instructions = skilldata_reader_order.get('verifiedInstructionWindows')
    if not isinstance(instructions, list):
        raise ContextError(source, 1, 'current SkillData and ActionGroupData header/store instructions',
                           instructions)
    expected_instructions = {
        (58581199, '4080FD30'),
        (65273925, '4080FD02'),
        (65273975, '48894118'),
        (65274020, '48894110'),
    }
    actual_instructions = {(row.get('rva'), row.get('rawHex')) for row in instructions}
    require(expected_instructions <= actual_instructions, True, source, 1)

    timeline = skilldata_reader_order.get('timelineActionDataReader')
    if not isinstance(timeline, dict):
        raise ContextError(source, 10, 'current TimelineActionData native reader evidence', timeline)
    require((timeline.get('elementTypeDefinitionIndex'), timeline.get('elementTypeName')),
            (9199, 'Beyond.Gameplay.Core.TimelineAction+TimelineActionData'), source, 10)
    require(timeline.get('listReaderMethodSpec', {}).get('index'), 610915, source, 10)
    timeline_methods = timeline.get('methods')
    if not isinstance(timeline_methods, list):
        raise ContextError(source, 10, 'TimelineActionData and ForceSync reader module/token rows',
                           timeline_methods)
    require(sorted(row.get('methodIndex') for row in timeline_methods),
            [104653, 104654, 107909, 107910], source, 10)
    timeline_windows = timeline.get('codeWindows')
    if not isinstance(timeline_windows, list):
        raise ContextError(source, 10, 'TimelineActionData hash-pinned reader windows',
                           timeline_windows)
    require(any((row.get('startRva'), row.get('endRva'), row.get('sha256')) ==
                (0x32CCF70, 0x32CD277,
                 'CB497F6362D9DA9396D6533F6CC037536FC9499D67848F1E8BBBAC8AA2F03688')
                for row in timeline_windows), True, source, 10)
    timeline_members = timeline.get('serializedMembers')
    if not isinstance(timeline_members, list) or len(timeline_members) != 4:
        raise ContextError(source, 10, 'four selected TimelineActionData member reads',
                           timeline_members)
    require([row.get('fieldName') for row in timeline_members],
            ['_endFrame', '_sequenceActionData', '_startFrame', 'forceSyncAnimData'],
            source, 10)
    end_frame_reader = timeline_members[0].get('reader', {})
    require((end_frame_reader.get('targetRva'), end_frame_reader.get('role')),
            (0x2CA86B0, 'read endFrame int32'), source, 11)
    sequence_method = timeline_members[1].get('readerMethodSpec', {})
    require((sequence_method.get('index'),
             sequence_method.get('genericType', {}).get('typeDefinitionIndex')),
            (619962, 9202), source, 15)
    require((timeline_members[2].get('reader', {}).get('kind'),
             timeline_members[2].get('reader', {}).get('byteWidth')),
            ('inline-int32', 4), source, 0)
    sequence_reference = timeline.get('sequenceActionDataReaderReference', {})
    sequence_window = sequence_reader.get('rootCodeWindow', {})
    require((sequence_reference.get('methodIndex'), sequence_reference.get('rootRva'),
             sequence_reference.get('rootCodeWindowSha256')),
            (104346, 0x39C6AA0,
             '6444AF67AF86E7809AF5A50AE6DEE922B699DCB1CA686DC81F4C3584AB817B90'),
            source, 15)
    require((sequence_window.get('startRva'), sequence_window.get('endRva'),
             sequence_window.get('sha256')),
            (0x39C6AA0, 0x39C6FA7,
             '6444AF67AF86E7809AF5A50AE6DEE922B699DCB1CA686DC81F4C3584AB817B90'),
            source, 15)
    sequence_methods = sequence_reader.get('methods')
    if not isinstance(sequence_methods, list):
        raise ContextError(source, 15, 'selected SequenceActionData reader module/token rows',
                           sequence_methods)
    sequence_root_methods = [row for row in sequence_methods
                             if row.get('methodIndex') == 104346 and
                             row.get('declaringType') ==
                             'Beyond.MemoryPack.Beyond_Gameplay_Core_SequenceActionDataForMemoryPack' and
                             row.get('name') == 'Deserialize' and
                             row.get('image') == 'MemoryPack.Beyond.dll']
    if len(sequence_root_methods) != 1:
        raise ContextError(source, 15, 'one exact SequenceActionData root Deserialize method',
                           len(sequence_root_methods))
    require(sequence_root_methods[0].get('pointerVa'),
            gameassembly_image_base + 0x39C6AA0, source, 15)
    sequence_windows = sequence_reader.get('windows')
    if not isinstance(sequence_windows, list):
        raise ContextError(source, 15, 'selected SequenceActionData header/count instruction',
                           sequence_windows)
    sequence_header = [row for row in sequence_windows
                       if row.get('rva') == 0x39C6B82]
    if len(sequence_header) != 1:
        raise ContextError(source, 15, 'one selected SequenceActionData member-three header check',
                           len(sequence_header))
    require(sequence_header[0].get('rawHex'), '4080FE030F85DD030000', source, 0x39C6B82)

    typed_prefix_ownership = [
        {'start': 0, 'end': 1, 'kind': 'SkillData.memberCount', 'value': 48},
        {'start': 1, 'end': 2, 'kind': 'ActionGroupData.memberCount', 'value': 2},
        {'start': 2, 'end': 6, 'kind': 'ActionGroupData.passiveEventActions.count-i32',
         'value': 0},
        {'start': 6, 'end': 10, 'kind': 'ActionGroupData.timelineActions.count-i32',
         'value': witness.get('timelineActionsListCount')},
    ]
    candidate_ranges = [dict(row) for row in witness['candidateByteRanges']]
    candidate_cursor = witness.get('candidateCursor')
    status = witness.get('status')
    failure = witness.get('failure')
    union_peek = witness.get('firstActionUnionTagPeekOnly')
    union_evidence = None
    prefix_stop = None
    candidate_play_animation_record_end = None
    candidate_timeline_continuation = None
    candidate_timeline_action_data_record_end = None
    candidate_action_group_data_record_end = None
    candidate_following_timeline_action_prefix = None
    candidate_following_timeline_action_data_record_end = None
    candidate_following_play_animation_record_end = None
    candidate_following_timeline_continuation = None
    candidate_play_animation_nested_sequence = None
    candidate_opaque_payload_ranges = []
    candidate_byte_payload_helper_evidence = None
    route_rows = buff_routes.get('rows')
    if not isinstance(route_rows, list):
        raise ContextError(source, 20, 'current AbilityActionData route rows', route_rows)

    if (failure is None and isinstance(union_peek, dict) and
            type(union_peek.get('tag')) is int):
        tag = union_peek['tag']
        tag_routes = [row for row in route_rows if row.get('tag') == tag]
        if tag == 0xFF and union_peek.get('tagWidth') == 1:
            start = union_peek['offset']
            if start < len(raw):
                candidate_ranges.append({'start': start, 'end': start + 1,
                                         'kind': 'candidate-null-action-union'})
                candidate_cursor = start + 1
                status = 'stopped-after-null-action-union'
                prefix_stop = {
                    'tag': tag, 'start': start, 'end': candidate_cursor,
                    'classification': 'candidate-null-union-only',
                    'parentCompleted': False,
                }
        elif tag != 0xC9 and (tag == 0x115 or tag in buff_action_readers):
            reader = buff_action_readers.get(tag)
            if reader is None:
                status = 'stopped-before-action-without-current-reader'
            else:
                union_evidence = skilldata_action_union_static_reader_evidence(
                    tag, reader, buff_routes,
                    gameassembly_image_base=gameassembly_image_base, source=source)
                require(len(tag_routes), 1, source, union_peek['offset'])
                root_member_count = union_evidence.get('rootMemberCount')
                root_read_order_key = union_evidence.get('rootReadOrderKey')
                root_read_order = union_evidence.get('rootAnonymousReadOrder')
                if not isinstance(root_read_order, list):
                    raise ContextError(source, union_peek['offset'],
                                       'current selected action member read order',
                                       root_read_order)
                common_prefix = ['byte', 'scalar32', 'scalar32', 'scalar32']
                if tag == 0x115:
                    require((root_member_count, root_read_order_key,
                             root_read_order[:4]),
                            (16, 'member16', common_prefix),
                            source, union_peek['offset'])
                    require(root_read_order[4], 'byte-payload',
                            source, union_peek['offset'])
                    nested_contexts = reader.get('nestedContexts')
                    if not isinstance(nested_contexts, list):
                        raise ContextError(source, union_peek['offset'],
                                           'PlayAnimation SequenceActionData static type context',
                                           nested_contexts)
                    nested_sequence_contexts = [row for row in nested_contexts
                                                if row.get('methodSpecIndex') == 619962 and
                                                row.get('typeDefinition') == 9202 and
                                                row.get('typeName') ==
                                                'Beyond.Gameplay.Core.SequenceActionData']
                    require(len(nested_sequence_contexts), 1, source,
                            union_peek['offset'])
                if root_read_order[:4] != common_prefix:
                    status = 'stopped-before-action-without-bounded-prefix-contract'
                else:
                    start = union_peek['offset']
                    width = union_peek.get('tagWidth')
                    expected_width = 3 if union_peek.get('firstByte') == 0xFA else 1
                    try:
                        encoded_tag = bytes.fromhex(union_peek.get('encodingHex', ''))
                    except ValueError as error:
                        raise ContextError(source, start,
                                           'hex-encoded current action union tag',
                                           union_peek) from error
                    if (type(width) is not int or width != expected_width or
                            len(encoded_tag) != width or raw[start:start + width] != encoded_tag):
                        raise ContextError(source, start,
                                           'complete current AbilityActionData union tag encoding',
                                           union_peek)
                    header_offset = start + width
                    header_good = (header_offset < len(raw) and
                                   raw[header_offset] == root_member_count)
                    if not header_good:
                        status = ('stopped-before-play-animation-member-header'
                                  if tag == 0x115 else
                                  'stopped-before-action-member-header')
                        failure = {
                            'category': ('truncated' if header_offset >= len(raw)
                                         else 'member-count'),
                            'offset': header_offset,
                            'expected': root_member_count,
                            'actual': raw[header_offset] if header_offset < len(raw) else None,
                        }
                    else:
                        position = header_offset + 1
                        prefix_rows = [
                            {'start': start, 'end': header_offset,
                             'kind': 'AbilityActionData.union-tag'},
                            {'start': header_offset, 'end': position,
                             'kind': ('PlayAnimationAction.memberCount' if tag == 0x115
                                      else 'AbilityActionData.root-memberCount')},
                        ]
                        next_field = None
                        next_member_type = None
                        consumed_member_types = []
                        for member_index, member_type in enumerate(root_read_order):
                            member_width = _skilldata_action_fixed_member_width(member_type)
                            if member_width is None:
                                next_member_type = member_type
                                break
                            if member_width > len(raw) - position:
                                next_field = {
                                    'offset': position,
                                    'memberIndex': member_index,
                                    'kind': member_type,
                                    'expectedBytes': member_width,
                                    'remainingBytes': len(raw) - position,
                                }
                                break
                            member_label = ('PlayAnimationAction' if tag == 0x115
                                            else 'AbilityActionData')
                            prefix_rows.append({
                                'start': position,
                                'end': position + member_width,
                                'kind': f'{member_label}.member{member_index}.{member_type}',
                            })
                            position += member_width
                            consumed_member_types.append(member_type)
                        candidate_ranges.extend(prefix_rows)
                        candidate_cursor = position
                        if next_field is not None:
                            status = ('truncated-play-animation-fixed-prefix'
                                      if tag == 0x115 else
                                      'truncated-action-fixed-prefix')
                            failure = {'category': 'truncated', **next_field}
                        elif (tag == 0x115 and next_member_type == 'byte-payload'):
                            payload_helper = _skilldata_verified_byte_payload_reader(
                                reader, byte_payload_helper_evidence, source=source)
                            candidate_byte_payload_helper_evidence = payload_helper
                            action_continuation = _skilldata_continue_play_animation_candidate(
                                raw, position, witness['hardLimit'],
                                root_read_order=root_read_order,
                                sequence_reader=sequence_reader,
                                payload_helper_evidence=payload_helper,
                                action_start=start, source=source)
                            candidate_ranges.extend(action_continuation['ranges'])
                            candidate_opaque_payload_ranges.extend(
                                action_continuation['opaquePayloadByteRanges'])
                            candidate_cursor = action_continuation['cursor']
                            status = action_continuation['status']
                            failure = action_continuation['failure']
                            candidate_play_animation_record_end = action_continuation[
                                'recordEndCandidate']
                            candidate_play_animation_nested_sequence = action_continuation.get(
                                'nestedSequence')
                            if candidate_play_animation_record_end is not None:
                                parent_continuation = _skilldata_continue_timeline_parent_candidate(
                                    raw, candidate_cursor, witness['hardLimit'],
                                    sequence_action_count=witness.get(
                                        'firstSequenceActionDataCount'),
                                    timeline_actions_list_count=witness.get(
                                        'timelineActionsListCount'),
                                    timeline_action_start=witness.get('candidateStart'),
                                    timeline_reader=timeline,
                                    sequence_tail_windows=action_continuation[
                                        'independentlyVerifiedSequenceTailWindows'],
                                    action_group_members=action_group_members,
                                    payload_helper_evidence=payload_helper,
                                    bool_helper_evidence=c9_prefix_evidence,
                                    gameassembly_image_base=gameassembly_image_base,
                                    source=source)
                                candidate_timeline_continuation = parent_continuation
                                candidate_ranges.extend(parent_continuation['ranges'])
                                candidate_opaque_payload_ranges.extend(
                                    parent_continuation.get('opaquePayloadByteRanges', []))
                                candidate_timeline_action_data_record_end = (
                                    parent_continuation.get(
                                        'candidateTimelineActionDataRecordEnd'))
                                candidate_action_group_data_record_end = (
                                    parent_continuation.get(
                                        'candidateActionGroupDataRecordEnd'))
                                candidate_cursor = parent_continuation['cursor']
                                status = parent_continuation['status']
                                failure = parent_continuation['failure']
                                prefix_stop = {
                                    'tag': tag, 'start': start,
                                    'recordEndCandidate': candidate_play_animation_record_end,
                                    'end': candidate_cursor,
                                    'nextSourceReadType': parent_continuation.get(
                                        'nextSourceReadType'),
                                    'nextSourceReadOffset': parent_continuation.get(
                                        'nextSourceReadOffset'),
                                    'nextSourceReadConsumed': False,
                                    'classification': parent_continuation.get(
                                        'classification',
                                        'candidate-static-reader-record end; parent incomplete'),
                                }
                                if (parent_continuation.get('status') ==
                                        'stopped-before-additional-timeline-action-data'):
                                    following_timeline = (
                                        _skilldata_read_following_timeline_action_data_prefix_candidate(
                                            raw, candidate_cursor, witness['hardLimit'],
                                            timeline_reader=timeline,
                                            sequence_reader=sequence_reader,
                                            payload_helper_evidence=payload_helper,
                                            bool_helper_evidence=c9_prefix_evidence,
                                            gameassembly_image_base=gameassembly_image_base,
                                            source=source))
                                    candidate_following_timeline_action_prefix = following_timeline
                                    candidate_ranges.extend(following_timeline['ranges'])
                                    candidate_opaque_payload_ranges.extend(
                                        following_timeline.get('opaquePayloadByteRanges', []))
                                    candidate_cursor = following_timeline['cursor']
                                    status = following_timeline['status']
                                    failure = following_timeline.get('failure')
                                    prefix_stop = {
                                        'tag': tag, 'start': following_timeline['start'],
                                        'end': candidate_cursor,
                                        'nextSourceReadType': following_timeline.get(
                                            'nextSourceReadType'),
                                        'nextSourceReadOffset': following_timeline.get(
                                            'nextSourceReadOffset', candidate_cursor),
                                        'nextSourceReadConsumed': following_timeline.get(
                                            'nextSourceReadConsumed', False),
                                        'firstActionUnionTagPeekOnly': following_timeline.get(
                                            'firstActionUnionTagPeekOnly'),
                                        'classification': (
                                            'candidate following TimelineActionData prefix; '
                                            'nested action and later parents remain open'),
                                    }
                                    following_tag = following_timeline.get(
                                        'firstActionUnionTagPeekOnly')
                                    if (following_timeline.get('status') ==
                                            'stopped-before-following-timeline-sequence-action' and
                                            isinstance(following_tag, dict) and
                                            following_tag.get('tag') == 0x115 and
                                            following_timeline.get('timelineSequenceCount') == 1):
                                        remaining_timeline_actions = (
                                            witness.get('timelineActionsListCount') - 1)
                                        following_action = (
                                            _skilldata_continue_following_play_animation_candidate(
                                                raw, following_timeline, witness['hardLimit'],
                                                timeline_actions_list_count=remaining_timeline_actions,
                                                timeline_reader=timeline,
                                                sequence_reader=sequence_reader,
                                                action_group_members=action_group_members,
                                                buff_routes=buff_routes,
                                                action_readers=buff_action_readers,
                                                payload_helper_evidence=payload_helper,
                                                bool_helper_evidence=c9_prefix_evidence,
                                                gameassembly_image_base=gameassembly_image_base,
                                                source=source))
                                        following_timeline['playAnimationContinuation'] = {
                                            key: value for key, value in following_action.items()
                                            if key != 'ranges'}
                                        following_timeline['ranges'].extend(
                                            following_action['ranges'])
                                        following_timeline['opaquePayloadByteRanges'] = (
                                            following_action['opaquePayloadByteRanges'])
                                        following_timeline['cursor'] = following_action['cursor']
                                        following_timeline['status'] = following_action['status']
                                        following_timeline['failure'] = following_action['failure']
                                        following_timeline['candidateRecordEnd'] = (
                                            following_action.get(
                                                'candidateTimelineActionDataRecordEnd'))
                                        following_timeline['candidatePlayAnimationRecordEnd'] = (
                                            following_action.get(
                                                'candidatePlayAnimationRecordEnd'))
                                        following_timeline['candidateTimelineContinuation'] = (
                                            following_action.get(
                                                'candidateTimelineContinuation'))
                                        candidate_ranges.extend(following_action['ranges'])
                                        candidate_opaque_payload_ranges.extend(
                                            following_action['opaquePayloadByteRanges'])
                                        candidate_cursor = following_action['cursor']
                                        status = following_action['status']
                                        failure = following_action['failure']
                                        candidate_following_timeline_action_data_record_end = (
                                            following_action.get(
                                                'candidateTimelineActionDataRecordEnd'))
                                        candidate_following_play_animation_record_end = (
                                            following_action.get(
                                                'candidatePlayAnimationRecordEnd'))
                                        candidate_following_timeline_continuation = (
                                            following_action.get(
                                                'candidateTimelineContinuation'))
                                        if following_action.get(
                                                'candidateActionGroupDataRecordEnd') is not None:
                                            candidate_action_group_data_record_end = (
                                                following_action.get(
                                                    'candidateActionGroupDataRecordEnd'))
                                        next_continuation = following_action.get(
                                            'candidateTimelineContinuation')
                                        prefix_stop = {
                                            'tag': tag, 'start': following_timeline['start'],
                                            'end': candidate_cursor,
                                            'nextSourceReadType': (
                                                next_continuation.get('nextSourceReadType')
                                                if isinstance(next_continuation, dict) else
                                                following_action.get('nextSourceReadType')),
                                            'nextSourceReadOffset': (
                                                next_continuation.get('nextSourceReadOffset')
                                                if isinstance(next_continuation, dict) else
                                                candidate_cursor),
                                            'nextSourceReadConsumed': False,
                                            'classification': following_action.get(
                                                'classification',
                                                'candidate following TimelineActionData reader end; later parents remain open'),
                                        }
                            else:
                                nested = action_continuation.get('nestedSequence')
                                next_type = ('SequenceActionData list element'
                                if isinstance(nested, dict) and
                                             nested.get('status') ==
                                             'stopped-before-sequence-action-elements'
                                             else 'PlayAnimationAction remaining member reads')
                                prefix_stop = {
                                    'tag': tag, 'start': start,
                                    'end': candidate_cursor,
                                    'nextSourceReadType': next_type,
                                    'nextSourceReadOffset': candidate_cursor,
                                    'nextSourceReadConsumed': False,
                                    'classification': 'candidate-static-reader prefix; parent incomplete',
                                }
                        elif next_member_type is not None:
                            status = ('stopped-before-play-animation-byte-payload'
                                      if tag == 0x115 else
                                      'stopped-before-action-variable-member')
                            if tag == 0x115:
                                prefix_stop = {
                                    'tag': tag, 'start': start, 'end': position,
                                    'memberHeader': root_member_count,
                                    'sourceReadOrderPrefix': consumed_member_types,
                                    'nextSourceReadType': next_member_type,
                                    'nextSourceReadOffset': position,
                                    'nextSourceReadConsumed': False,
                                    'consumedUnionRecord': False,
                                    'classification': 'candidate-static-reader-prefix; provider unobserved',
                                }
                            else:
                                prefix_stop = {
                                    'tag': tag, 'start': start, 'end': position,
                                    'memberHeader': root_member_count,
                                    'rootReadOrderKey': root_read_order_key,
                                    'sourceReadOrderPrefix': consumed_member_types,
                                    'nextSourceReadType': next_member_type,
                                    'nextSourceReadOffset': position,
                                    'nextSourceReadConsumed': False,
                                    'consumedUnionRecord': False,
                                    'classification': 'candidate-static-reader-prefix; provider unobserved',
                                }
                        else:
                            status = 'candidate-action-reader-member-sequence-exhausted'
                            prefix_stop = {
                                'tag': tag, 'start': start, 'end': position,
                                'memberHeader': root_member_count,
                                'rootReadOrderKey': root_read_order_key,
                                'sourceReadOrderPrefix': consumed_member_types,
                                'nextSourceReadType': None,
                                'nextSourceReadOffset': position,
                                'nextSourceReadConsumed': None,
                                'consumedUnionRecord': False,
                                'classification': 'candidate-static-reader-member-sequence; provider unobserved',
                            }
        elif tag == 0xC9:
            require(len(tag_routes), 1, source, union_peek['offset'])
            if not isinstance(c9_prefix_evidence, dict):
                raise ContextError(source, union_peek['offset'],
                                   'current exact-build C9 member-eight prefix reader evidence',
                                   c9_prefix_evidence)
            c9_route = tag_routes[0]
            require((c9_prefix_evidence.get('tag'),
                     c9_prefix_evidence.get('switchTargetRva'),
                     c9_prefix_evidence.get('typeDefinition'),
                     c9_prefix_evidence.get('wrapperName')),
                    (0xC9, c9_route.get('switchTargetRva'), c9_route.get('typeDefinition'),
                     c9_route.get('wrapperName')), source, union_peek['offset'])
            require(c9_prefix_evidence.get('providerSelection'), 'unobserved', source,
                    union_peek['offset'])
            start = union_peek['offset']
            if union_peek.get('tagWidth') != 1 or raw[start] != 0xC9:
                raise ContextError(source, start, 'one-byte C9 union tag', union_peek)
            header_offset = start + 1
            header_good = header_offset < len(raw) and raw[header_offset] == 8
            if not header_good:
                status = 'stopped-before-if-else-member-header'
                failure = {'category': ('truncated' if header_offset >= len(raw)
                                        else 'member-count'),
                           'offset': header_offset, 'expected': 8,
                           'actual': raw[header_offset] if header_offset < len(raw) else None}
            else:
                position = start
                prefix_fields = [
                    (1, 'AbilityActionData.union-tag'),
                    (1, 'IfElseAction.memberCount'),
                    (1, 'IfElseAction.member0.byte'),
                    (4, 'IfElseAction.member1.scalar32'),
                    (4, 'IfElseAction.member2.scalar32'),
                    (4, 'IfElseAction.member3.scalar32'),
                    (1, 'IfElseAction.member4.byte'),
                ]
                prefix_rows = []
                next_field = None
                for field_width, kind in prefix_fields:
                    if field_width > len(raw) - position:
                        next_field = {'offset': position, 'kind': kind,
                                      'expectedBytes': field_width,
                                      'remainingBytes': len(raw) - position}
                        break
                    prefix_rows.append({'start': position,
                                        'end': position + field_width,
                                        'kind': kind})
                    position += field_width
                candidate_ranges.extend(prefix_rows)
                candidate_cursor = position
                if next_field is not None:
                    status = 'truncated-if-else-fixed-prefix'
                    failure = {'category': 'truncated', **next_field}
                else:
                    status = 'stopped-before-if-else-sequence-call'
                    prefix_stop = {
                        'tag': tag, 'start': start, 'end': position,
                        'memberHeader': 8,
                        'sourceReadWidthsAfterHeader': [1, 4, 4, 4, 1],
                        'nextSourceReadType': 'Beyond.Gameplay.Core.SequenceActionData',
                        'nextSourceReadOffset': position,
                        'nextSourceReadConsumed': False,
                        'consumedUnionRecord': False,
                        'classification': 'candidate-static-reader-prefix; provider unobserved',
                    }
        else:
            reader = buff_action_readers.get(tag)
            if len(tag_routes) == 1 and reader is not None:
                union_evidence = skilldata_action_union_static_reader_evidence(
                    tag, reader, buff_routes,
                    gameassembly_image_base=gameassembly_image_base, source=source)
                status = 'stopped-before-action-without-bounded-prefix-contract'
            elif tag_routes:
                status = 'stopped-before-action-without-current-reader'
            else:
                status = 'stopped-at-unknown-action-tag'

    candidate_ranges.sort(key=lambda row: (row['start'], row['end']))
    range_cursor = 10
    for index, span in enumerate(candidate_ranges):
        if (type(span.get('start')) is not int or type(span.get('end')) is not int or
                span['start'] != range_cursor or span['end'] <= span['start'] or
                span['end'] > witness['hardLimit']):
            raise ContextError(source, range_cursor,
                               f'timeline candidate byteRanges[{index}] contiguous from byte 10',
                               span)
        range_cursor = span['end']
    require(range_cursor, candidate_cursor, source, candidate_cursor)
    if status == 'stopped-at-unknown-action-tag':
        require(witness['firstActionUnionTagPeekOnly'].get('consumed'), False,
                source, candidate_cursor)
        require(candidate_cursor, witness['firstActionUnionTagPeekOnly']['offset'],
                source, candidate_cursor)

    return {
        'status': 'conditional-static-reader-alignment',
        'inputSetSha256': input_set,
        'logicalFileIdentity': witness.get('logicalFileIdentity'),
        'logicalSha256': witness.get('logicalSha256'),
        'hardLimit': witness.get('hardLimit'),
        'authoritativeParserCursor': witness.get('authoritativeParserCursor'),
        'candidateCursor': candidate_cursor,
        'timelineActionsListCount': witness.get('timelineActionsListCount'),
        'firstSequenceActionDataCount': witness.get('firstSequenceActionDataCount'),
        'typedPrefixOwnershipCandidate': typed_prefix_ownership,
        'candidateByteRanges': candidate_ranges,
        'firstActionUnionTagPeekOnly': witness.get('firstActionUnionTagPeekOnly'),
        'candidateActionReaderEvidence': union_evidence,
        'candidateActionPrefixStop': prefix_stop,
        'candidatePlayAnimationRecordEnd': candidate_play_animation_record_end,
        'candidatePlayAnimationNestedSequence': candidate_play_animation_nested_sequence,
        'candidateTimelineContinuation': candidate_timeline_continuation,
        'candidateTimelineActionDataRecordEnd': candidate_timeline_action_data_record_end,
        'candidateActionGroupDataRecordEnd': candidate_action_group_data_record_end,
        'candidateFollowingTimelineActionDataPrefix': candidate_following_timeline_action_prefix,
        'candidateFollowingTimelineActionDataRecordEnd': (
            candidate_following_timeline_action_data_record_end),
        'candidateFollowingPlayAnimationRecordEnd': (
            candidate_following_play_animation_record_end),
        'candidateFollowingTimelineContinuation': candidate_following_timeline_continuation,
        'opaquePayloadByteRanges': candidate_opaque_payload_ranges,
        'bytePayloadHelperEvidence': candidate_byte_payload_helper_evidence,
        'candidateStatus': status,
        'failure': failure,
        'opaqueByteRanges': ([] if candidate_cursor == witness['hardLimit'] else [{
            'start': candidate_cursor, 'end': witness['hardLimit'],
            'kind': 'unconsumed-timeline-actiongroup-and-skilldata-bytes'}]),
        'exactClosedTimelineActionRecords': 0,
        'exactClosedActionGroupDataRecords': 0,
        'wholeSkillDataClassification': 'ambiguous',
        'wholeSkillDataExactClosedRecords': 0,
        'runtimeProviderCacheSelection': 'unobserved',
        'boundary': ('This reader-path alignment is a separate candidate and never changes parserCursor 10. The 0x115 '
                     'candidate may follow exact-build signed-length byte-payload helpers, its static SequenceActionData '
                     'null/empty path, and the enclosing sequence tail/startFrame when each current byte fits. Opaque '
                     'payload content is not decoded; runtime formatter/provider selection remains unobserved. Unknown '
                     'tags remain at their first byte. No TimelineActionData, ActionGroupData or SkillData parent is '
                     'counted closed.'),
    }


def skilldata_action_readers_from_locals(local_values, *, source):
    """Collect only current native action readers backed by matching contracts."""
    readers = {}
    for variable_name, reader in local_values.items():
        variable_match = re.fullmatch(r'buff_([0-9a-f]+)', variable_name)
        if variable_match is None or not isinstance(reader, dict):
            continue
        contract_value = reader.get('contractPath')
        if not isinstance(contract_value, str) or not contract_value:
            continue
        contract_path = Path(contract_value).resolve()
        contract_match = re.fullmatch(r'buff_([0-9a-f]+)_native\.json',
                                      contract_path.name, flags=re.IGNORECASE)
        if contract_match is None:
            continue
        tag = int(variable_match.group(1), 16)
        require(int(contract_match.group(1), 16), tag, source, tag)
        expected_path = (CONTRACTS_DIR / f'buff_{tag:02x}_native.json').resolve()
        require(contract_path, expected_path, source, tag)
        if not contract_path.is_file():
            raise ContextError(source, tag, 'current selected action reader contract file',
                               str(contract_path))
        contract_sha = hashlib.sha256(contract_path.read_bytes()).hexdigest().upper()
        require(reader.get('contractSha256'), contract_sha, source, tag)
        if tag in readers:
            raise ContextError(source, tag, 'one selected native action reader per tag',
                               [variable_name, readers[tag]['variableName']])
        reader = dict(reader)
        reader['variableName'] = variable_name
        readers[tag] = reader
    return readers


def skilldata_action_union_static_reader_evidence(tag, reader, buff_routes, *,
                                                   gameassembly_image_base,
                                                   source):
    """Join one sample tag to its registered wrapper and exact current reader body."""
    if not isinstance(reader, dict):
        raise ContextError(source, tag, 'hash-pinned native reader for consumed action tag',
                           type(reader).__name__)
    route_rows = buff_routes.get('rows') if isinstance(buff_routes, dict) else None
    if not isinstance(route_rows, list):
        raise ContextError(source, tag, 'current AbilityActionData union route rows', route_rows)
    matching_routes = [row for row in route_rows if row.get('tag') == tag]
    if len(matching_routes) != 1:
        raise ContextError(source, tag, f'exactly one current route for tag {tag:#x}',
                           len(matching_routes))
    route = matching_routes[0]
    operands = route.get('operands')
    if not isinstance(operands, list) or not operands:
        raise ContextError(source, tag, 'registered tag-to-wrapper type-usage operand', operands)
    operand_rows = []
    for index, operand in enumerate(operands):
        if not isinstance(operand, dict):
            raise ContextError(source, tag, f'route operand {index} object', operand)
        if (type(operand.get('usageTag')) is not int or
                type(operand.get('registeredTypeIndex')) is not int):
            raise ContextError(source, tag, f'route operand {index} exact usage/type indices', operand)
        operand_rows.append({
            'usageTag': operand['usageTag'],
            'registeredTypeIndex': operand['registeredTypeIndex'],
        })

    expected_contract = (CONTRACTS_DIR / f'buff_{tag:02x}_native.json').resolve()
    contract_path = Path(reader.get('contractPath', '')).resolve()
    require(contract_path, expected_contract, source, tag)
    if not expected_contract.is_file():
        raise ContextError(source, tag, 'current selected action reader contract file',
                           str(expected_contract))
    contract_sha = hashlib.sha256(expected_contract.read_bytes()).hexdigest().upper()
    require(reader.get('contractSha256'), contract_sha, source, tag)

    methods = reader.get('methods')
    if not isinstance(methods, list):
        raise ContextError(source, tag, 'native action Deserialize module/token rows', methods)
    selected_methods = [row for row in methods
                        if row.get('declaringType') == route.get('wrapperName') and
                        row.get('name') == 'Deserialize']
    if len(selected_methods) != 1:
        raise ContextError(source, tag, 'one module/token-joined registered wrapper reader',
                           len(selected_methods))
    method = selected_methods[0]
    require(method.get('image'), 'MemoryPack.Beyond.dll', source, tag)
    pointer_va = method.get('pointerVa')
    if type(pointer_va) is not int:
        raise ContextError(source, tag, 'current root reader native pointer VA', pointer_va)
    root_rva = pointer_va - gameassembly_image_base
    code_windows = reader.get('codeWindows')
    if not isinstance(code_windows, list):
        raise ContextError(source, tag, 'hash-pinned selected action reader code windows',
                           code_windows)
    root_windows = [row for row in code_windows
                    if isinstance(row, dict) and row.get('startRva') == root_rva]
    if len(root_windows) != 1:
        raise ContextError(source, tag,
                           'one exact reader code window beginning at the registered method pointer',
                           {'rootRva': root_rva, 'matches': len(root_windows)})
    root_window = root_windows[0]
    if (type(root_window.get('endRva')) is not int or
            root_window['endRva'] <= root_window['startRva'] or
            not isinstance(root_window.get('sha256'), str) or
            not re.fullmatch(r'[0-9A-Fa-f]{64}', root_window['sha256'])):
        raise ContextError(source, tag, 'bounded 64-hex root reader code-window fingerprint',
                           root_window)

    read_order = reader.get('anonymousReadOrder')
    if not isinstance(read_order, dict) or not read_order:
        raise ContextError(source, tag, 'anonymous native member read order', read_order)
    root_order_key = next(iter(read_order))
    header_match = (re.search(r'member(\d+)$', root_order_key, flags=re.IGNORECASE)
                    if isinstance(root_order_key, str) else None)
    if header_match is None:
        raise ContextError(source, tag, 'root read-order key ending in its member count',
                           root_order_key)
    root_member_count = int(header_match.group(1))
    root_member_order = read_order[root_order_key]
    if not isinstance(root_member_order, list):
        raise ContextError(source, tag, 'root anonymous member read-order list',
                           root_member_order)
    return {
        'tag': tag,
        'switchTargetRva': route.get('switchTargetRva'),
        'typeDefinition': route.get('typeDefinition'),
        'wrapperName': route.get('wrapperName'),
        'operands': operand_rows,
        'methodIndex': method.get('methodIndex'),
        'contractFile': expected_contract.name,
        'contractSha256': contract_sha,
        'rootCodeWindow': {
            'startRva': root_window['startRva'],
            'endRva': root_window['endRva'],
            'sha256': root_window['sha256'],
        },
        'rootReadOrderKey': root_order_key,
        'rootMemberCount': root_member_count,
        'rootAnonymousReadOrder': root_member_order,
    }


def skilldata_action_union_c9_prefix_reader_evidence(reader, buff_routes, *,
                                                       gameassembly_image_base,
                                                       source):
    """Pin only the C9 member-eight scalar prefix before its generic children."""
    if not isinstance(reader, dict):
        raise ContextError(source, 0xC9,
                           'current exact-build IfElse selected-reader evidence',
                           type(reader).__name__)
    route_rows = buff_routes.get('rows') if isinstance(buff_routes, dict) else None
    if not isinstance(route_rows, list):
        raise ContextError(source, 0xC9, 'current AbilityActionData union route rows',
                           route_rows)
    matching_routes = [row for row in route_rows if row.get('tag') == 0xC9]
    if len(matching_routes) != 1:
        raise ContextError(source, 0xC9, 'one exact current C9 union route',
                           len(matching_routes))
    route = matching_routes[0]
    wrapper = ('Beyond.MemoryPack.Beyond_Gameplay_Core_IfElseAction_'
               'IfElseActionDataForMemoryPack')
    require(route.get('switchTargetRva'), 0x390DA8A, source, 0xC9)
    require(route.get('typeDefinition'), 16163, source, 0xC9)
    require(route.get('wrapperName'), wrapper, source, 0xC9)
    operands = route.get('operands')
    if not isinstance(operands, list):
        raise ContextError(source, 0xC9, 'C9 registered type-usage operands', operands)
    selected_operands = [row for row in operands
                         if row.get('usageTag') == 1 and
                         row.get('registeredTypeIndex') == 106672]
    require(len(selected_operands), 1, source, 0xC9)

    methods = reader.get('methods')
    if not isinstance(methods, list):
        raise ContextError(source, 0xC9, 'IfElse selected reader method rows', methods)
    selected_methods = [row for row in methods
                        if row.get('methodIndex') == 120613 and
                        row.get('declaringType') == wrapper and
                        row.get('name') == 'Deserialize']
    if len(selected_methods) != 1:
        raise ContextError(source, 0xC9,
                           'one token/module-joined IfElse root Deserialize method',
                           len(selected_methods))
    method = selected_methods[0]
    require(method.get('image'), 'MemoryPack.Beyond.dll', source, 0xC9)
    pointer_va = method.get('pointerVa')
    if type(pointer_va) is not int:
        raise ContextError(source, 0xC9, 'exact IfElse root reader pointer VA', pointer_va)
    root_rva = pointer_va - gameassembly_image_base
    require(root_rva, 0x3774060, source, 0xC9)
    root_window = reader.get('rootCodeWindow')
    if not isinstance(root_window, dict):
        raise ContextError(source, 0xC9, 'hash-pinned complete IfElse reader code window',
                           root_window)
    require((root_window.get('startRva'), root_window.get('endRva'),
             root_window.get('sha256')),
            (0x3774060, 0x37742A8,
             'AC1FF978FEF71639E74980B43AE00D9746518A9DD94B41772F2867963A596ED8'),
            source, 0xC9)

    expected_windows = {
        0x3774093:
            '837B30010F8C089A6B01488B43500FB6288B733083EE010F880B9A6B0148FF4350FF4340FF43448973304080FDFF0F8482010000',
        0x37740FA: '4080FD080F85D1996B01',
    }
    windows = reader.get('windows')
    if not isinstance(windows, list):
        raise ContextError(source, 0xC9, 'selected IfElse reader instruction windows', windows)
    window_evidence = []
    for rva, expected_hex in expected_windows.items():
        matches = [row for row in windows if row.get('rva') == rva]
        if len(matches) != 1:
            raise ContextError(source, rva, 'one exact selected IfElse normal-path window',
                               len(matches))
        actual_hex = matches[0].get('rawHex')
        require(actual_hex, expected_hex, source, rva)
        raw_window = bytes.fromhex(actual_hex)
        window_evidence.append({
            'startRva': rva,
            'endRva': rva + len(raw_window),
            'byteLength': len(raw_window),
            'sha256': hashlib.sha256(raw_window).hexdigest().upper(),
            'rawHex': actual_hex,
        })

    expected_calls = [
        (0x377410A, 0x2CA88C0, 1),
        (0x3774135, 0x2CA86B0, 4),
        (0x3774159, 0x2CA86B0, 4),
        (0x377417D, 0x2CA86B0, 4),
        (0x37741A1, 0x2CA88C0, 1),
        (0x37741CA, 0x2DA5C90, None),
        (0x37741F3, 0x2DA5C90, None),
        (0x377421C, 0x2DA5C90, None),
    ]
    calls = reader.get('orderedCalls')
    if not isinstance(calls, list):
        raise ContextError(source, 0xC9, 'selected IfElse ordered source-call rows', calls)
    actual_calls = [(row.get('rva'), row.get('targetRva'),
                     row.get('fastSerializedWidth')) for row in calls]
    require(actual_calls, expected_calls, source, 0x377410A)

    expected_nested_operand_rvas = [0x37741BD, 0x37741E6, 0x377420F]
    nested_operands = reader.get('nestedOperands')
    if not isinstance(nested_operands, list):
        raise ContextError(source, 0xC9, 'three exact nested generic type-usage rows',
                           nested_operands)
    require([row.get('rva') for row in nested_operands],
            expected_nested_operand_rvas, source, 0xC9)
    require(len({row.get('cellVa') for row in nested_operands}), 1, source, 0xC9)
    require(len({row.get('usageRawHex') for row in nested_operands}), 1, source, 0xC9)
    require(reader.get('nestedMethodSpecIndex'), 619962, source, 0xC9)
    require(reader.get('nestedTypeDefinition'), 9202, source, 0xC9)
    require(reader.get('nestedTypeName'),
            'Beyond.Gameplay.Core.SequenceActionData', source, 0xC9)
    instantiation = reader.get('nestedInstantiation')
    if not isinstance(instantiation, dict):
        raise ContextError(source, 0xC9,
                           'exact nested SequenceActionData type instantiation',
                           instantiation)
    arguments = instantiation.get('arguments')
    if not isinstance(arguments, (list, tuple)) or len(arguments) != 1:
        raise ContextError(source, 0xC9, 'one selected SequenceActionData type argument',
                           arguments)
    require(arguments[0].get('raw_type_record_hex'),
            'F2230000000000000000120000000000', source, 0xC9)

    return {
        'tag': 0xC9,
        'switchTargetRva': route['switchTargetRva'],
        'typeDefinition': route['typeDefinition'],
        'wrapperName': wrapper,
        'registeredTypeIndex': 106672,
        'methodIndex': method['methodIndex'],
        'rootMethodRva': root_rva,
        'rootCodeWindow': root_window,
        'memberHeader': 8,
        'prefixSourceReadWidthsAfterHeader': [1, 4, 4, 4, 1],
        'prefixByteLengthIncludingTagAndMemberHeader': 16,
        'codeWindows': window_evidence,
        'nestedSequenceMethodSpecIndex': reader['nestedMethodSpecIndex'],
        'nestedSequenceTypeDefinition': reader['nestedTypeDefinition'],
        'nestedSequenceTypeName': reader['nestedTypeName'],
        'verifiedSharedHelperReads': [
            {'callInstructionRva': rva, 'targetRva': target,
             'fastSerializedWidth': width}
            for rva, target, width in expected_calls[:5]],
        'nestedSequenceCallSites': [
            {'rva': rva, 'targetRva': target}
            for rva, target, width in expected_calls[5:]],
        'providerSelection': 'unobserved',
        'boundary': ('The current C9 route selects the exact IfElse root reader. Its selected member-eight '
                     'normal path reads a one-byte member header, widths 1/4/4/4/1, then makes three '
                     'generic calls whose MethodSpec type argument is SequenceActionData. This evidence '
                     'ends before the first generic child call; it does not establish which runtime '
                     'formatter/provider supplies that child reader or close the C9 union.'),
    }


def skilldata_actiongroup_c9_nested_sequence_candidate_replay(
        witness, raw, c9_prefix_reader, sequence_reader, buff_action_readers,
        buff_routes, *, source, gameassembly_image_base=0x180000000,
        candidate_limit=None):
    """Keep a bounded C9->Sequence replay explicitly separate from the parser cursor."""
    if not isinstance(witness, dict) or not isinstance(raw, bytes):
        raise ContextError(source, 0, 'current SkillData prefix witness and raw bytes',
                           [type(witness).__name__, type(raw).__name__])
    if not all(isinstance(value, dict) for value in
               (c9_prefix_reader, sequence_reader, buff_routes)):
        raise ContextError(source, 0,
                           'C9, SequenceActionData and action-route static evidence objects',
                           [type(c9_prefix_reader).__name__, type(sequence_reader).__name__,
                            type(buff_routes).__name__])
    if not isinstance(buff_action_readers, dict) or any(
            type(tag) is not int or not isinstance(reader, dict)
            for tag, reader in buff_action_readers.items()):
        raise ContextError(source, 0, 'current tag-to-native action reader map',
                           type(buff_action_readers).__name__)

    input_set = witness.get('inputSetSha256')
    if not isinstance(input_set, str) or not re.fullmatch(r'[0-9A-Fa-f]{64}', input_set):
        raise ContextError(source, 0, 'current SkillData inputSetSha256', input_set)
    logical_path = witness.get('logicalFileIdentity')
    if not isinstance(logical_path, str) or not logical_path.startswith('Data/Json/SkillData/'):
        raise ContextError(source, 0, 'logical SkillData file identity', logical_path)
    logical_sha = hashlib.sha256(raw).hexdigest().upper()
    require(witness.get('logicalSha256'), logical_sha, source, 0)
    hard_limit = witness.get('hardLimit')
    require(hard_limit, len(raw), source, 0)
    require(witness.get('status'), 'stopped-after-verified-action-prefix', source, 0)
    prefix = witness.get('actionUnionPrefixStop')
    if not isinstance(prefix, dict):
        raise ContextError(source, witness.get('parserCursor', 0),
                           'C9 structural-prefix witness', prefix)
    prefix_start = prefix.get('start')
    prefix_end = prefix.get('end')
    if (type(prefix_start) is not int or type(prefix_end) is not int or
            prefix_start < 0 or prefix_end <= prefix_start or prefix_end > hard_limit):
        raise ContextError(source, 0, 'C9 prefix range within current hardLimit',
                           [prefix_start, prefix_end, hard_limit])
    require(prefix.get('tag'), 0xC9, source, prefix_start if type(prefix_start) is int else 0)
    require(prefix.get('memberHeader'), 8, source,
            prefix_start + 1 if type(prefix_start) is int else 0)
    require(prefix.get('sourceReadWidthsAfterHeader'), [1, 4, 4, 4, 1], source,
            prefix_start if type(prefix_start) is int else 0)
    require(prefix_end - prefix_start, 16, source,
            prefix_start if type(prefix_start) is int else 0)
    require(witness.get('parserCursor'), prefix_end, source,
            prefix_end if type(prefix_end) is int else 0)
    require(prefix.get('consumedUnionRecord'), False, source,
            prefix_start if type(prefix_start) is int else 0)
    require(prefix.get('nextSourceReadType'),
            'Beyond.Gameplay.Core.SequenceActionData', source, prefix_end)
    require(prefix.get('nextSourceReadOffset'), prefix_end, source, prefix_end)
    require(prefix.get('nextSourceReadConsumed'), False, source, prefix_end)
    require(prefix.get('remainingBytesOpaque'), True, source, prefix_end)
    require(c9_prefix_reader.get('tag'), 0xC9, source, prefix_start)
    require(c9_prefix_reader.get('memberHeader'), 8, source, prefix_start + 1)
    require(c9_prefix_reader.get('prefixSourceReadWidthsAfterHeader'),
            [1, 4, 4, 4, 1], source, prefix_start)
    require(c9_prefix_reader.get('prefixByteLengthIncludingTagAndMemberHeader'),
            16, source, prefix_start)
    require(c9_prefix_reader.get('nestedSequenceMethodSpecIndex'), 619962, source, prefix_start)
    require(c9_prefix_reader.get('nestedSequenceTypeDefinition'), 9202, source, prefix_start)
    require(c9_prefix_reader.get('nestedSequenceTypeName'),
            'Beyond.Gameplay.Core.SequenceActionData', source, prefix_start)
    require(c9_prefix_reader.get('providerSelection'), 'unobserved', source, prefix_start)
    c9_root = c9_prefix_reader.get('rootCodeWindow')
    require((c9_root.get('startRva'), c9_root.get('endRva'), c9_root.get('sha256'))
            if isinstance(c9_root, dict) else None,
            (0x3774060, 0x37742A8,
             'AC1FF978FEF71639E74980B43AE00D9746518A9DD94B41772F2867963A596ED8'),
            source, prefix_start)
    expected_call_sites = [
        {'rva': 0x37741CA, 'targetRva': 0x2DA5C90},
        {'rva': 0x37741F3, 'targetRva': 0x2DA5C90},
        {'rva': 0x377421C, 'targetRva': 0x2DA5C90},
    ]
    require(c9_prefix_reader.get('nestedSequenceCallSites'), expected_call_sites,
            source, prefix_start)

    sequence_methods = sequence_reader.get('methods')
    if not isinstance(sequence_methods, list):
        raise ContextError(source, prefix_end, 'SequenceActionData native method rows',
                           sequence_methods)
    selected_sequence_methods = [row for row in sequence_methods
                                 if isinstance(row, dict) and
                                 row.get('methodIndex') == 104346 and
                                 row.get('declaringType') ==
                                 'Beyond.MemoryPack.Beyond_Gameplay_Core_SequenceActionDataForMemoryPack' and
                                 row.get('name') == 'Deserialize' and
                                 row.get('image') == 'MemoryPack.Beyond.dll']
    if len(selected_sequence_methods) != 1:
        raise ContextError(source, prefix_end,
                           'one module/token-joined SequenceActionData root reader',
                           len(selected_sequence_methods))
    sequence_method = selected_sequence_methods[0]
    if type(sequence_method.get('pointerVa')) is not int:
        raise ContextError(source, prefix_end,
                           'SequenceActionData root reader pointer VA', sequence_method)
    sequence_root_rva = sequence_method['pointerVa'] - gameassembly_image_base
    require(sequence_root_rva, 0x39C6AA0, source, prefix_end)
    sequence_root = sequence_reader.get('rootCodeWindow')
    require((sequence_root.get('startRva'), sequence_root.get('endRva'),
             sequence_root.get('sha256')) if isinstance(sequence_root, dict) else None,
            (0x39C6AA0, 0x39C6FA7,
             '6444AF67AF86E7809AF5A50AE6DEE922B699DCB1CA686DC81F4C3584AB817B90'),
            source, prefix_end)

    if candidate_limit is None:
        candidate_limit = hard_limit
    if (type(candidate_limit) is not int or
            not prefix_end <= candidate_limit <= hard_limit):
        raise ContextError(source, prefix_end,
                           'candidateLimit within [C9 prefix end, current hardLimit]',
                           candidate_limit)

    from scripts.game_data.memorypack.buff_actions import FrameError, Reader, Unsupported

    class GuardedSequenceReader(Reader):
        def action(self, depth):
            start = self.pos
            lead = self.peek()
            width = 3 if lead == 0xFA else 1
            if width > self.limit - self.pos:
                raise FrameError(self.source, self.pos, {'bytes': width},
                                 {'remaining': self.limit - self.pos}, 'truncated')
            tag = struct.unpack_from('<H', self.data, self.pos + 1)[0] if width == 3 else lead
            if tag != 0xFF and tag not in buff_action_readers:
                raise Unsupported(self.source, start,
                                  'current selected native action-reader contract for nested tag',
                                  tag, 'union-tag')
            if tag != 0xFF:
                native_reader = buff_action_readers[tag]
                native_evidence = skilldata_action_union_static_reader_evidence(
                    tag, native_reader, buff_routes,
                    gameassembly_image_base=gameassembly_image_base,
                    source=self.source)
                action_reader_evidence_by_tag.setdefault(tag, native_evidence)
                header_offset = start + width
                if (header_offset < self.limit and
                        self.data[header_offset] != 0xFF and
                        self.data[header_offset] != native_evidence['rootMemberCount']):
                    raise Unsupported(
                        self.source, start,
                        {'nativeReaderMemberCount': native_evidence['rootMemberCount'],
                         'firstUnconsumedByte': start},
                        {'tag': tag, 'memberHeaderOffset': header_offset,
                         'memberHeaderValue': self.data[header_offset]},
                        'native-header')
            return super().action(depth)

    reader = GuardedSequenceReader(raw, source, limit=candidate_limit)
    reader.pos = prefix_end
    candidate_sequence_ranges = []
    candidate_calls = []
    candidate_action_ranges = []
    action_reader_evidence_by_tag = {}
    failure = None
    for call_index, call_site in enumerate(expected_call_sites):
        start = reader.pos
        first_range_index = len(reader.ranges)
        first_record_index = len(reader.records)
        call_error = None
        try:
            reader.sequence(depth=0)
        except FrameError as exc:
            diagnostic = getattr(exc, 'diagnostic', None)
            if not isinstance(diagnostic, dict):
                raise
            call_error = diagnostic
            failure = diagnostic

        end = reader.pos
        new_ranges = [dict(row) for row in reader.ranges[first_range_index:]]
        range_cursor = start
        for range_index, byte_range in enumerate(new_ranges):
            if (type(byte_range.get('start')) is not int or
                    type(byte_range.get('end')) is not int or
                    byte_range['start'] != range_cursor or
                    byte_range['end'] <= range_cursor or byte_range['end'] > end):
                raise ContextError(source, range_cursor,
                                   f'candidate call {call_index} byteRanges[{range_index}] contiguous',
                                   byte_range)
            range_cursor = byte_range['end']
        require(range_cursor, end, source, end)

        new_records = reader.records[first_record_index:]
        for record in new_records:
            if record.get('kind') != 'union':
                continue
            tag = record.get('tag')
            union_start, union_end = record.get('start'), record.get('end')
            if (type(tag) is not int or type(union_start) is not int or
                    type(union_end) is not int or
                    not start <= union_start < union_end <= end):
                raise ContextError(source, start,
                                   'candidate child union range contained within attempted SequenceActionData call',
                                   record)
            lead = raw[union_start]
            tag_width = 3 if lead == 0xFA else 1
            if tag_width == 3:
                actual_tag = struct.unpack_from('<H', raw, union_start + 1)[0]
            else:
                actual_tag = lead
            require(actual_tag, tag, source, union_start)
            if tag == 0xFF:
                candidate_action_ranges.append({
                    'tag': tag, 'start': union_start, 'end': union_end,
                    'sequenceCallIndex': call_index,
                    'memberHeaderValue': None,
                    'nativeActionReaderEvidence': None,
                    'classification': 'candidate-only-null-action-range',
                })
                continue
            native_reader = buff_action_readers.get(tag)
            if not isinstance(native_reader, dict):
                raise ContextError(source, union_start,
                                   'native action-reader contract for completed candidate child tag', tag)
            native_evidence = skilldata_action_union_static_reader_evidence(
                tag, native_reader, buff_routes,
                gameassembly_image_base=gameassembly_image_base, source=source)
            header_offset = union_start + tag_width
            if header_offset >= union_end:
                raise ContextError(source, header_offset,
                                   'candidate non-null child contains its member header',
                                   [union_start, union_end, tag_width])
            member_header = raw[header_offset]
            if member_header != 0xFF:
                require(member_header, native_evidence['rootMemberCount'], source,
                        header_offset)
            action_reader_evidence_by_tag.setdefault(tag, native_evidence)
            candidate_action_ranges.append({
                'tag': tag, 'start': union_start, 'end': union_end,
                'sequenceCallIndex': call_index,
                'memberHeaderValue': member_header,
                'nativeActionReaderEvidence': native_evidence,
                'classification': 'candidate-only-static-reader-child-range',
            })

        matching_outer_sequences = [row for row in new_records
                                    if row.get('kind') == 'sequence' and
                                    row.get('start') == start and row.get('end') == end]
        complete = call_error is None
        if complete:
            require(len(matching_outer_sequences), 1, source, start)
            candidate_range = {
                'start': start,
                'end': end,
                'kind': 'candidate-SequenceActionData-call-range',
                'callSiteRva': call_site['rva'],
                'byteRanges': new_ranges,
                'completedChildActionTags': [
                    row['tag'] for row in candidate_action_ranges
                    if row['sequenceCallIndex'] == call_index],
                'classification': 'candidate-only; runtime provider/cache selection unobserved',
            }
            candidate_sequence_ranges.append(candidate_range)
            call_status = 'candidate-sequence-range-replayed'
        else:
            require(matching_outer_sequences, [], source, start)
            call_status = call_error.get('category', 'unsupported')
            call_row = {
                'callIndex': call_index,
                'callSiteRva': call_site['rva'],
                'start': start,
                'candidateCursor': end,
                'completed': False,
                'status': call_status,
                'diagnostic': call_error,
                'consumedByteRanges': new_ranges,
            }
            if call_status in ('union-tag', 'native-header') and end < candidate_limit:
                lead = raw[end]
                width = 3 if lead == 0xFA else 1
                peeked_tag = (struct.unpack_from('<H', raw, end + 1)[0]
                              if width == 3 and candidate_limit - end >= 3 else
                              lead if width == 1 else None)
                call_row['firstUnconsumedActionUnionByte'] = {
                    'offset': end,
                    'firstByte': lead,
                    'decodedTag': peeked_tag,
                    'consumed': False,
                }
                if call_status == 'native-header':
                    call_row['nativeReaderHeaderConflict'] = call_error.get('actual')
            candidate_calls.append(call_row)
            break
        candidate_calls.append({
            'callIndex': call_index,
            'callSiteRva': call_site['rva'],
            'start': start,
            'end': end,
            'completed': True,
            'status': call_status,
            'candidateRange': candidate_range,
        })

    candidate_cursor = reader.pos
    overall_ranges = [dict(row) for row in reader.ranges]
    range_cursor = prefix_end
    for range_index, byte_range in enumerate(overall_ranges):
        if (type(byte_range.get('start')) is not int or
                type(byte_range.get('end')) is not int or
                byte_range['start'] != range_cursor or
                byte_range['end'] <= range_cursor or
                byte_range['end'] > candidate_cursor):
            raise ContextError(source, range_cursor,
                               f'candidateByteRanges[{range_index}] contiguous from C9 prefix cursor',
                               byte_range)
        range_cursor = byte_range['end']
    require(range_cursor, candidate_cursor, source, candidate_cursor)
    if failure is None:
        status = 'three-sequence-call-candidates-replayed'
    elif failure.get('category') == 'union-tag':
        status = 'stopped-before-first-unverified-nested-action'
    elif failure.get('category') == 'native-header':
        status = 'ambiguous-native-reader-header'
    elif failure.get('category') == 'truncated':
        status = 'truncated-candidate-sequence'
    elif failure.get('category') in ('count-bounds', 'member-count', 'malformed'):
        status = 'malformed-candidate-sequence'
    else:
        status = 'unsupported-candidate-sequence'
    return {
        'candidateOnly': True,
        'status': status,
        'inputSetSha256': input_set,
        'logicalFileIdentity': logical_path,
        'logicalSha256': logical_sha,
        'hardLimit': hard_limit,
        'candidateLimit': candidate_limit,
        'candidateStart': prefix_end,
        'candidateCursor': candidate_cursor,
        'candidateByteRanges': overall_ranges,
        'sequenceCallCandidates': candidate_calls,
        'candidateSequenceRanges': candidate_sequence_ranges,
        'candidateActionUnionRanges': candidate_action_ranges,
        'currentActionReaderEvidence': [
            action_reader_evidence_by_tag[tag]
            for tag in sorted(action_reader_evidence_by_tag)],
        'selectedNativeSequenceReader': {
            'methodIndex': sequence_method['methodIndex'],
            'image': sequence_method['image'],
            'rootCodeWindow': sequence_root,
        },
        'runtimeProviderCacheSelection': 'unobserved',
        'authoritativeParserCursor': witness['parserCursor'],
        'authoritativeParserCursorUnchanged': True,
        'exactClosedSequenceRecords': 0,
        'exactClosedC9UnionRecords': 0,
        'exactClosedActionGroupDataRecords': 0,
        'exactClosedWholeSkillDataRecords': 0,
        'failure': failure,
        'remainingSourceBytesOpaque': [
            *([] if candidate_cursor >= candidate_limit else [{
                'start': candidate_cursor,
                'end': candidate_limit,
                'kind': 'candidate-replay-remainder-opaque',
            }]),
            *([] if candidate_limit >= hard_limit else [{
                'start': candidate_limit,
                'end': hard_limit,
                'kind': 'beyond-candidateLimit-opaque',
            }]),
        ],
        'boundary': ('The three SequenceActionData calls are replayed only as a separate candidate using the '
                     'current native Sequence root and child-action reader contracts. Runtime provider/cache '
                     'selection for the C9 generic calls is unobserved. Candidate ranges never advance the '
                     'authoritative parser cursor and never close the C9 union, AbilityActionMap, parent list, '
                     'ActionGroupData, or whole SkillData record.'),
    }


def skilldata_actiongroup_branch_static_alignment(witness, skilldata_reader,
                                                   ability_map_reader,
                                                   shared_list_reader,
                                                   sequence_reader,
                                                   buff_d5_reader,
                                                   buff_d6_reader,
                                                   buff_routes, *, source,
                                                   buff_action_readers=None,
                                                   buff_action_prefixes=None,
                                                   gameassembly_image_base=0x180000000):
    """Align current ActionGroupData samples with separately audited native readers."""
    if not all(isinstance(value, dict) for value in
               (witness, skilldata_reader, ability_map_reader,
                shared_list_reader, sequence_reader, buff_d5_reader,
                buff_d6_reader, buff_routes)):
        raise ContextError(source, 0,
                           'sample plus SkillData, AbilityActionMap, List<T>, Sequence and D5/D6 static evidence',
                           [type(value).__name__ for value in
                            (witness, skilldata_reader, ability_map_reader,
                             shared_list_reader, sequence_reader, buff_d5_reader,
                             buff_d6_reader, buff_routes)])
    if buff_action_readers is None:
        buff_action_readers = {}
    if not isinstance(buff_action_readers, dict) or any(
            type(tag) is not int or not isinstance(reader, dict)
            for tag, reader in buff_action_readers.items()):
        raise ContextError(source, 0, 'tag-to-current-native-action-reader mapping',
                           type(buff_action_readers).__name__)
    if buff_action_prefixes is None:
        buff_action_prefixes = {}
    if not isinstance(buff_action_prefixes, dict) or any(
            type(tag) is not int or not isinstance(evidence, dict)
            for tag, evidence in buff_action_prefixes.items()):
        raise ContextError(source, 0, 'tag-to-current-native-action-prefix evidence mapping',
                           type(buff_action_prefixes).__name__)
    native_action_readers = {0xD5: buff_d5_reader, 0xD6: buff_d6_reader}
    native_action_readers.update(buff_action_readers)
    require(skilldata_reader.get('firstSkillDataField', {}).get('fieldName'),
            'actionGroupData', source, 0)
    require(skilldata_reader.get('inputSetSha256'), witness.get('inputSetSha256'), source, 0)
    members = skilldata_reader.get('actionGroupDataMembers')
    if not isinstance(members, list) or len(members) != 2:
        raise ContextError(source, 0, 'two native ActionGroupData member reads', members)
    require([row.get('fieldName') for row in members],
            ['passiveEventActions', 'timelineActions'], source, 0)
    require([row.get('serializedOrderIndex') for row in members], [0, 1], source, 0)
    require([row.get('readerMethodSpec', {}).get('index') for row in members],
            [610662, 610915], source, 0)
    first_generic = members[0].get('readerMethodSpec', {}).get('genericType', {})
    require(first_generic.get('typeName'), 'System.Collections.Generic.List`1', source, 0)
    require(first_generic.get('elementTypeName'),
            'Beyond.Gameplay.Core.AbilityActionMap', source, 0)
    skilldata_code_windows = skilldata_reader.get('codeWindows')
    if not isinstance(skilldata_code_windows, list):
        raise ContextError(source, 0, 'current SkillData/ActionGroupData code windows',
                           skilldata_code_windows)
    require(any((row.get('rva'), row.get('byteLength'), row.get('sha256')) ==
                (58581179, 2314,
                 'FEA359985EBF5DF75CC58D871469481F0F692B1768D84724FF5941D47CAD8132')
                for row in skilldata_code_windows), True, source, 0)
    skilldata_instructions = skilldata_reader.get('verifiedInstructionWindows')
    if not isinstance(skilldata_instructions, list):
        raise ContextError(source, 0, 'current SkillData verified instruction windows',
                           skilldata_instructions)
    expected_skilldata_instructions = {
        (65273925, '4080FD02', 'ActionGroupData member-count comparison against 2'),
        (65273975, '48894118', 'store passiveEventActions result at object offset +0x18'),
        (65274020, '48894110', 'store timelineActions result at object offset +0x10'),
    }
    actual_skilldata_instructions = {
        (row.get('rva'), row.get('rawHex'), row.get('role'))
        for row in skilldata_instructions
    }
    require(expected_skilldata_instructions <= actual_skilldata_instructions,
            True, source, 0)

    ability_methods = ability_map_reader.get('methods')
    if not isinstance(ability_methods, list):
        raise ContextError(source, 0, 'native AbilityActionMap method identities', ability_methods)
    ability_reader_methods = [row for row in ability_methods
                              if row.get('methodIndex') in (104445, 104446)]
    require(sorted(row['methodIndex'] for row in ability_reader_methods),
            [104445, 104446], source, 0)
    require(ability_map_reader.get('anonymousReadOrder', {}).get('mapMember2'),
            ['scalar32', 'nullable-sequence-array'], source, 0)
    ability_map_windows = ability_map_reader.get('codeWindows')
    if not isinstance(ability_map_windows, list):
        raise ContextError(source, 0, 'current AbilityActionMap code windows', ability_map_windows)
    require(any((row.get('startRva'), row.get('endRva'), row.get('sha256')) ==
                (63974160, 63974463,
                 'ADDDF617D14CF2A723E7E6CDD2978D46BC6557DEE539EA28A21A12619CCF42BB')
                for row in ability_map_windows), True, source, 0)
    sequence_contexts = [row for row in ability_map_reader.get('nestedContexts', [])
                         if row.get('typeName') == 'Beyond.Gameplay.Core.SequenceActionData']
    require(len(sequence_contexts), 1, source, 0)
    require(sequence_contexts[0].get('methodSpecIndex'), 610597, source, 0)

    expected_shared_contract = (CONTRACTS_DIR / 'buff_b4_native.json').resolve()
    shared_contract = Path(shared_list_reader.get('contractPath', '')).resolve()
    require(shared_contract, expected_shared_contract, source, 0)
    shared_contract_sha = hashlib.sha256(expected_shared_contract.read_bytes()).hexdigest().upper()
    require(shared_list_reader.get('contractSha256'), shared_contract_sha, source, 0)
    shared_code_windows = shared_list_reader.get('codeWindows')
    if not isinstance(shared_code_windows, list):
        raise ContextError(source, 0, 'current shared List<T> native code windows',
                           shared_code_windows)
    require(any((row.get('startRva'), row.get('endRva'), row.get('sha256')) ==
                (46828560, 46829514,
                 'CD9E5FC3BAB5502AC7D168F445CA3DC207C39D61A9CFF7D7F52F51A1F447B7C5')
                for row in shared_code_windows), True, source, 0)
    if not shared_list_reader.get('methods'):
        raise ContextError(source, 0, 'current shared list reader method identities',
                           shared_list_reader.get('methods'))
    sequence_methods = sequence_reader.get('methods')
    if not isinstance(sequence_methods, list):
        raise ContextError(source, 0, 'native SequenceActionData method identities', sequence_methods)
    require(sorted(row.get('methodIndex') for row in sequence_methods),
            [104346, 104347], source, 0)
    sequence_header_window = [row for row in sequence_reader.get('windows', [])
                             if row.get('rva') == 0x39C6B82]
    if len(sequence_header_window) != 1:
        raise ContextError(source, 0, 'one exact SequenceActionData count window',
                           len(sequence_header_window))
    require(sequence_header_window[0].get('rawHex'),
            '4080FE030F85DD030000', source, 0)
    if 'header 3 takes a signed dword count after the one-byte header' not in sequence_reader.get('boundary', '').lower():
        raise ContextError(source, 0, 'SequenceActionData header/count boundary statement',
                           sequence_reader.get('boundary'))

    expected_action_readers = (
        (0xD5, buff_d5_reader, 120788,
         'Beyond.MemoryPack.Beyond_Gameplay_Core_IntResourceHpCheckAction_DataForMemoryPack',
         16187, 106689, 0x4E67C83, 153753548, 153753943,
         '24DFDAE1E252056FB43AB54D51BFA7443249A2FFA932B4636ACEA7F01C3EF1EB'),
        (0xD6, buff_d6_reader, 120799,
         'Beyond.MemoryPack.Beyond_Gameplay_Core_IntResourceOnHpZeroAction_DataForMemoryPack',
         16189, 106690, 0x4E67CC6, 153754580, 153754975,
         '2256CCF5032B30A1906A9830B8D815D491B6963EA04330DA4E67BBE49D399F7F'),
    )
    route_rows = buff_routes.get('rows')
    if not isinstance(route_rows, list):
        raise ContextError(source, 0, 'current AbilityActionData union route rows', route_rows)
    action_union_reader_evidence_by_tag = {}
    for (tag, reader, method_index, wrapper_name, type_definition,
         usage_index, switch_target, start_rva, end_rva, window_sha) in expected_action_readers:
        matching_routes = [row for row in route_rows if row.get('tag') == tag]
        if len(matching_routes) != 1:
            raise ContextError(source, tag, f'exactly one current route for D5/D6 tag {tag:#x}',
                               len(matching_routes))
        route = matching_routes[0]
        require(route.get('switchTargetRva'), switch_target, source, tag)
        require(route.get('typeDefinition'), type_definition, source, tag)
        require(route.get('wrapperName'), wrapper_name, source, tag)
        operands = route.get('operands')
        if not isinstance(operands, list) or len(operands) != 1:
            raise ContextError(source, tag, 'one exact tag-to-wrapper type-usage operand', operands)
        require((operands[0].get('usageTag'), operands[0].get('registeredTypeIndex')),
                (1, usage_index), source, tag)

        methods = reader.get('methods')
        if not isinstance(methods, list):
            raise ContextError(source, tag, 'selected D5/D6 Deserialize module/token row', methods)
        selected_methods = [row for row in methods if row.get('methodIndex') == method_index]
        if len(selected_methods) != 1:
            raise ContextError(source, tag, f'exactly one method row {method_index}', len(selected_methods))
        method = selected_methods[0]
        require((method.get('declaringType'), method.get('name'), method.get('image')),
                (wrapper_name, 'Deserialize', 'MemoryPack.Beyond.dll'), source, tag)
        require(reader.get('anonymousReadOrder', {}).get('member4'),
                ['boolean', 'scalar32', 'scalar32', 'scalar32'], source, tag)
        code_windows = reader.get('codeWindows')
        if not isinstance(code_windows, list):
            raise ContextError(source, tag, 'selected D5/D6 native code windows', code_windows)
        if not any((row.get('startRva'), row.get('endRva'), row.get('sha256')) ==
                   (start_rva, end_rva, window_sha) for row in code_windows):
            raise ContextError(source, tag,
                               'hash-pinned selected D5/D6 reader positive path through RET',
                               code_windows)
        action_union_reader_evidence_by_tag[tag] = {
            'tag': tag,
            'switchTargetRva': switch_target,
            'wrapperName': wrapper_name,
            'registeredTypeIndex': usage_index,
            'methodIndex': method_index,
            'codeWindow': {'startRva': start_rva, 'endRva': end_rva,
                           'sha256': window_sha},
            'anonymousReadOrder': reader['anonymousReadOrder']['member4'],
            'contractSha256': reader.get('contractSha256'),
        }

    require(witness.get('wholeSkillDataClassification'), 'ambiguous', source, 0)
    require(witness.get('wholeSkillDataExactClosedRecords'), 0, source, 0)
    count_fields = {row['offset']: row['signedI32']
                    for row in witness.get('countI32Fields', [])}
    map_records = [row for row in witness.get('completedNestedRecords', [])
                   if row.get('kind') == 'anonymous-ability-action-map']
    all_union_records = sorted(
        [row for row in witness.get('completedNestedRecords', [])
         if row.get('kind') == 'union'], key=lambda row: row['start'])
    non_null_union_records = [row for row in all_union_records
                              if row.get('tag') != 0xFF]
    d5d6_union_records = [row for row in non_null_union_records
                          if row.get('tag') in (0xD5, 0xD6)]
    observed_union_headers = witness.get('completedActionUnionHeaderObservations')
    if not isinstance(observed_union_headers, list):
        raise ContextError(source, witness.get('parserCursor'),
                           'completed action union header observations',
                           observed_union_headers)
    native_reader_evidence_by_tag = {}
    for record in non_null_union_records:
        tag = record.get('tag')
        if type(tag) is not int:
            raise ContextError(source, record.get('start', 0),
                               'completed action union with integer tag', record)
        reader = native_action_readers.get(tag)
        if reader is None:
            raise ContextError(source, record.get('start', 0),
                               'current selected native reader for every consumed non-null tag',
                               tag)
        evidence = skilldata_action_union_static_reader_evidence(
            tag, reader, buff_routes,
            gameassembly_image_base=gameassembly_image_base, source=source)
        native_reader_evidence_by_tag[tag] = evidence

    observed_ids = set()
    for observation in observed_union_headers:
        if not isinstance(observation, dict):
            raise ContextError(source, witness.get('parserCursor'),
                               'action union header observation object', observation)
        record = next((row for row in non_null_union_records
                       if (row.get('tag'), row.get('start'), row.get('end')) ==
                       (observation.get('tag'), observation.get('start'), observation.get('end'))),
                      None)
        if record is None:
            raise ContextError(source, observation.get('start', 0),
                               'header observation belongs to a completed union range',
                               observation)
        observation_id = (observation['tag'], observation['start'], observation['end'])
        if observation_id in observed_ids:
            raise ContextError(source, observation['start'],
                               'one member-header observation per completed union',
                               observation)
        observed_ids.add(observation_id)
        reader_evidence = native_reader_evidence_by_tag[observation['tag']]
        require(observation.get('memberHeaderValue'),
                reader_evidence['rootMemberCount'], source,
                observation.get('memberHeaderOffset', observation['start']))
        tag_width = observation.get('tagWidth')
        expected_tag_width = (3 if observation.get('tagPrefixByte') == 0xFA else 1)
        require(tag_width, expected_tag_width, source, observation['start'])
        tag_encoding_hex = observation.get('tagEncodingHex')
        if not isinstance(tag_encoding_hex, str):
            raise ContextError(source, observation['start'],
                               'raw one-byte or FA-prefixed extended tag encoding',
                               tag_encoding_hex)
        try:
            tag_encoding = bytes.fromhex(tag_encoding_hex)
        except ValueError as exc:
            raise ContextError(source, observation['start'],
                               'hexadecimal action tag encoding', tag_encoding_hex) from exc
        require(len(tag_encoding), expected_tag_width, source, observation['start'])
        require(tag_encoding[0],
                0xFA if expected_tag_width == 3 else observation['tag'],
                source, observation['start'])
        decoded_tag = (struct.unpack_from('<H', tag_encoding, 1)[0]
                       if expected_tag_width == 3 else tag_encoding[0])
        require(decoded_tag, observation['tag'], source, observation['start'])
        require(observation.get('memberHeaderOffset'),
                observation['start'] + tag_width, source, observation['start'])
    for record in non_null_union_records:
        record_id = (record.get('tag'), record.get('start'), record.get('end'))
        if record_id not in observed_ids:
            tag_width = 3 if record['tag'] == 0xFA or record['tag'] > 0xFF else 1
            require(record.get('end') - record.get('start'), tag_width + 1,
                    source, record.get('start', 0))

    for tag in (0xD5, 0xD6):
        if tag in native_reader_evidence_by_tag:
            native_reader_evidence_by_tag[tag].update(
                action_union_reader_evidence_by_tag[tag])
    action_union_reader_evidence = [
        native_reader_evidence_by_tag[tag]
        for tag in dict.fromkeys(row['tag'] for row in non_null_union_records)
    ]
    action_union_prefix_evidence = []

    if witness.get('status') == 'passive-list-consumed-to-conditional-static-end':
        next_count = witness.get('nextMemberCountPeekOnly')
        if not isinstance(next_count, dict):
            raise ContextError(source, witness.get('parserCursor'),
                               'non-advancing timelineActions count peek', next_count)
        require(next_count.get('fieldName'), 'timelineActions.count', source, 15)
        require(next_count.get('consumed'), False, source, 15)
        cursor = witness.get('parserCursor')
        map_lists = [row for row in witness.get('completedNestedRecords', [])
                     if row.get('kind') == 'anonymous-ability-action-map-list']
        require([(row.get('start'), row.get('end')) for row in map_lists],
                [(2, cursor)], source, 2)
        require(len(map_records), witness.get('passiveEventActionsListCount'), source, 0)
        if not non_null_union_records and cursor == 15:
            require(len(map_records), witness.get('passiveEventActionsListCount'), source, 0)
            require(count_fields.get(11), 0, source, 11)
            require(next_count.get('offset'), cursor, source, cursor)
            require(next_count.get('signedI32'), 0, source, cursor)
            expected_disposition = (
                'empty SequenceActionData array branch reaches the conditional passiveEventActions end; '
                'timelineActions remains unread')
        elif sorted((row.get('tag'), row.get('start'), row.get('end'))
                    for row in d5d6_union_records) == [
                        (0xD5, 20, 35), (0xD6, 51, 66)
                    ] and len(non_null_union_records) == 2:
            require([(row.get('tag'), row.get('start'), row.get('end'))
                     for row in d5d6_union_records],
                    [(0xD5, 20, 35), (0xD6, 51, 66)], source, 20)
            require(cursor, 68, source, 68)
            require(witness.get('passiveEventActionsListCount'), 2, source, 2)
            require(count_fields, {2: 2, 11: 1, 16: 1, 42: 1, 47: 1}, source, 2)
            require(sorted((row.get('start'), row.get('end')) for row in map_records),
                    [(6, 37), (37, 68)], source, 6)
            sequence_records = sorted(
                [(row.get('start'), row.get('end'))
                 for row in witness.get('completedNestedRecords', [])
                 if row.get('kind') == 'sequence'])
            require(sequence_records, [(15, 37), (46, 68)], source, 15)
            require(next_count.get('offset'), cursor, source, cursor)
            require(next_count.get('signedI32'), 0, source, cursor)
            expected_disposition = (
                'two D5/D6 child ranges and both SequenceActionData entries reach the conditional '
                'passiveEventActions list end; timelineActions count is peek-only')
        else:
            require(type(cursor) is int and 15 <= cursor <= witness.get('hardLimit'),
                    True, source, 0)
            require(next_count.get('offset'), cursor, source, cursor)
            opaque = witness.get('opaqueByteRanges')
            expected_opaque = ([] if cursor == witness.get('hardLimit') else [{
                'start': cursor,
                'end': witness.get('hardLimit'),
                'kind': 'unconsumed-actiongroup-and-skilldata-bytes',
            }])
            require(opaque, expected_opaque, source, cursor)
            expected_disposition = (
                f'{len(non_null_union_records)} non-null child unions align to their selected native readers; '
                f'{len(map_records)} AbilityActionMap entries reach the conditional passiveEventActions '
                f'list end at {cursor}; timelineActions remains peek-only')
    elif witness.get('status') == 'stopped-before-first-nonnull-action-union':
        cursor = witness.get('parserCursor')
        first_union = witness.get('firstUnconsumedActionUnionByte')
        if not isinstance(first_union, dict):
            raise ContextError(source, cursor, 'first unconsumed nested action-union byte', first_union)
        require(first_union.get('offset'), cursor, source, cursor)
        require(first_union.get('tag') not in native_action_readers, True, source, cursor)
        require(first_union.get('tag'), witness.get('parserError', {}).get('actual'), source, cursor)
        require(first_union.get('consumed'), False, source, cursor)
        require(first_union.get('firstByte') not in (0xFF,), True, source, cursor)
        parser_error = witness.get('parserError')
        if not isinstance(parser_error, dict):
            raise ContextError(source, cursor, 'opaque diagnostic for unverified tag', parser_error)
        require(parser_error.get('category'), 'opaque-union', source, cursor)
        require(parser_error.get('offset'), cursor, source, cursor)
        map_lists = [row for row in witness.get('completedNestedRecords', [])
                     if row.get('kind') == 'anonymous-ability-action-map-list']
        require(map_lists, [], source, cursor)
        for parent_kind in ('anonymous-ability-action-map', 'sequence'):
            crossing = [row for row in witness.get('completedNestedRecords', [])
                        if row.get('kind') == parent_kind and
                        row.get('start', cursor) <= cursor < row.get('end', cursor)]
            require(crossing, [], source, cursor)
        require(witness.get('nextMemberCountPeekOnly'), None, source, cursor)
        require(witness.get('opaqueByteRanges'), [{
            'start': cursor,
            'end': witness.get('hardLimit'),
            'kind': 'unconsumed-actiongroup-and-skilldata-bytes',
        }], source, cursor)
        expected_disposition = (
            'SequenceActionData stops before the first unverified non-null action tag; '
            'parent list remains incomplete')
    elif witness.get('status') == 'stopped-after-verified-action-prefix':
        prefix = witness.get('actionUnionPrefixStop')
        if not isinstance(prefix, dict):
            raise ContextError(source, witness.get('parserCursor'),
                               'bounded C9 action-union prefix-stop witness', prefix)
        tag = prefix.get('tag')
        if tag not in buff_action_prefixes:
            raise ContextError(source, prefix.get('start', 0),
                               'exact current static reader prefix for consumed action tag', tag)
        prefix_evidence = buff_action_prefixes[tag]
        require(tag, prefix_evidence.get('tag'), source, prefix.get('start', 0))
        require(prefix.get('memberHeader'), prefix_evidence.get('memberHeader'),
                source, prefix.get('start', 0))
        require(prefix.get('sourceReadWidthsAfterHeader'),
                prefix_evidence.get('prefixSourceReadWidthsAfterHeader'),
                source, prefix.get('start', 0))
        start = prefix.get('start')
        cursor = witness.get('parserCursor')
        require(type(start) is int and type(cursor) is int and cursor > start,
                True, source, start if type(start) is int else 0)
        require(cursor - start,
                prefix_evidence.get('prefixByteLengthIncludingTagAndMemberHeader'),
                source, start)
        require(prefix.get('end'), cursor, source, cursor)
        require(prefix.get('consumedUnionRecord'), False, source, start)
        require(prefix.get('nextSourceReadType'),
                prefix_evidence.get('nestedSequenceTypeName'), source, cursor)
        require(prefix.get('nextSourceReadOffset'), cursor, source, cursor)
        require(prefix.get('nextSourceReadConsumed'), False, source, cursor)
        next_lead = prefix.get('nextSourceReadFirstByte')
        if next_lead not in (None, 3, 0xFF):
            raise ContextError(source, cursor,
                               'peeked next SequenceActionData lead is header 3, null FF, or beyond hardLimit',
                               next_lead)
        prefix_ranges = [row for row in witness.get('consumedByteRanges', [])
                         if row.get('start', -1) >= start and
                         row.get('end', cursor + 1) <= cursor]
        require([(row.get('start'), row.get('end'), row.get('kind'))
                 for row in prefix_ranges], [
                     (start, start + 1, 'union-tag'),
                     (start + 1, start + 2, 'member-header'),
                     (start + 2, start + 3, 'anonymous-byte'),
                     (start + 3, start + 7, 'anonymous-scalar32'),
                     (start + 7, start + 11, 'anonymous-scalar32'),
                     (start + 11, start + 15, 'anonymous-scalar32'),
                     (start + 15, start + 16, 'anonymous-byte'),
                 ], source, start)
        require(not any(row.get('kind') == 'union' and row.get('start') == start
                        for row in witness.get('completedNestedRecords', [])),
                True, source, start)
        for parent_kind in ('anonymous-ability-action-map',
                            'anonymous-ability-action-map-list', 'sequence'):
            crossing = [row for row in witness.get('completedNestedRecords', [])
                        if row.get('kind') == parent_kind and
                        row.get('start', cursor) <= start < row.get('end', start)]
            require(crossing, [], source, start)
        require(witness.get('nextMemberCountPeekOnly'), None, source, cursor)
        require(witness.get('opaqueByteRanges'), ([] if cursor == witness.get('hardLimit') else [{
            'start': cursor,
            'end': witness.get('hardLimit'),
            'kind': 'unconsumed-actiongroup-and-skilldata-bytes',
        }]), source, cursor)
        action_union_prefix_evidence.append(prefix_evidence)
        expected_disposition = (
            f'C9 tag and member-eight scalar prefix [ {start}, {cursor} ) align with the current '
            'IfElse reader; stop before its first SequenceActionData generic call, leaving the union '
            'and enclosing map/list incomplete')
    else:
        raise ContextError(source, 0,
                           'one recognized closed-list or opaque-union ActionGroupData branch',
                           witness.get('status'))
    return {
        'status': 'conditional-static-reader-alignment',
        'inputSetSha256': witness.get('inputSetSha256'),
        'logicalFileIdentity': witness.get('logicalFileIdentity'),
        'logicalSha256': witness.get('logicalSha256'),
        'hardLimit': witness.get('hardLimit'),
        'parserCursor': witness.get('parserCursor'),
        'consumedByteRanges': witness.get('consumedByteRanges'),
        'opaqueByteRanges': witness.get('opaqueByteRanges'),
        'actionGroupDataMemberOrder': ['passiveEventActions', 'timelineActions'],
        'passiveEventActionsElementType': 'Beyond.Gameplay.Core.AbilityActionMap',
        'abilityActionMapMemberOrder': ['scalar32', 'nullable-sequence-array'],
        'sequenceActionDataReaderEvidence': {
            'methodSpecIndex': sequence_contexts[0]['methodSpecIndex'],
            'headerCountWindowRva': sequence_header_window[0]['rva'],
            'headerCountWindowRawHex': sequence_header_window[0]['rawHex'],
        },
        'abilityActionUnionReaderEvidence': action_union_reader_evidence,
        'verifiedActionUnionReaderTags': [row['tag'] for row in action_union_reader_evidence],
        'abilityActionUnionPrefixReaderEvidence': action_union_prefix_evidence,
        'verifiedActionUnionPrefixTags': [row['tag'] for row in action_union_prefix_evidence],
        'completedActionUnionRanges': [
            {'tag': row['tag'], 'start': row['start'], 'end': row['end']}
            for row in non_null_union_records],
        'completedD5D6UnionRanges': [
            {'tag': row['tag'], 'start': row['start'], 'end': row['end']}
            for row in d5d6_union_records],
        'conditionalDisposition': expected_disposition,
        'runtimeProviderCacheSelection': 'unobserved',
        'actionGroupDataExactClosedRecords': 0,
        'wholeSkillDataClassification': 'ambiguous',
        'wholeSkillDataExactClosedRecords': 0,
        'boundary': ('The raw ActionGroupData passive-action samples align with current-build registered wrapper '
                     'routes and hash-pinned action readers, including the observed child member-header counts. '
                     'Child ranges and passiveEventActions list ends remain conditional static-reader evidence; '
                     'unknown tags stop at their first byte. Provider/cache selection is unobserved, timelineActions '
                     'is only peeked, and neither ActionGroupData nor whole SkillData is promoted.'),
    }


def skilldata_terminal_collision_evidence(
        corpus, *, source,
        logical_path='Data/Json/SkillData/Potential_test.json'):
    """Validate one current EOF collision and keep its candidate byte tilings.

    This checks the authenticated VFS corpus report, not source bytes or a live
    reader cursor.  It makes no decision between candidates.
    """
    input_set = corpus.get('inputSetSha256')
    if not isinstance(input_set, str) or len(input_set) != 64:
        raise ContextError(source, 0, 'current 64-hex SkillData inputSetSha256', input_set)
    rows = [row for row in corpus.get('files', [])
            if isinstance(row, dict) and row.get('virtualPath') == logical_path]
    if len(rows) != 1:
        raise ContextError(source, 0, f'exactly one current VFS row for {logical_path!r}',
                           len(rows))
    row = rows[0]

    def check(actual, expected, field, offset=0):
        if actual != expected:
            raise ContextError(source, offset, f'{logical_path}.{field} == {expected!r}', actual)

    def integer(value, field, offset=0):
        if type(value) is int and value >= 0:
            return value
        if isinstance(value, str):
            try:
                parsed = int(value, 0)
            except ValueError:
                parsed = -1
            if parsed >= 0:
                return parsed
        raise ContextError(source, offset, f'{logical_path}.{field} is a nonnegative byte offset',
                           value)

    def check_hash(value, field):
        if (not isinstance(value, str) or len(value) != 64 or
                any(ch not in '0123456789abcdefABCDEF' for ch in value)):
            raise ContextError(source, 0, f'{logical_path}.{field} is a 64-hex SHA-256',
                               value)

    def check_context(context, field, *, start, cursor, hard_limit, logical_sha):
        if not isinstance(context, dict):
            raise ContextError(source, 0, f'{logical_path}.{field} is an identity context',
                               type(context).__name__)
        check(context.get('inputSetSha256'), input_set, f'{field}.inputSetSha256')
        check(context.get('logicalFileIdentity'), logical_path,
              f'{field}.logicalFileIdentity')
        check(context.get('logicalSha256'), logical_sha, f'{field}.logicalSha256')
        check(context.get('startOffset'), start, f'{field}.startOffset')
        check(context.get('hardLimit'), hard_limit, f'{field}.hardLimit')
        check(context.get('parserCursor'), cursor, f'{field}.parserCursor')

    def tile(ranges, start, end, field):
        if not isinstance(ranges, list):
            raise ContextError(source, start, f'{logical_path}.{field} is a byte-range list',
                               type(ranges).__name__)
        cursor = start
        for index, span in enumerate(ranges):
            if not isinstance(span, dict):
                raise ContextError(source, cursor,
                                   f'{logical_path}.{field}[{index}] is a byte range', span)
            range_start, range_end = span.get('start'), span.get('end')
            if (type(range_start) is not int or type(range_end) is not int or
                    range_start != cursor or range_end <= range_start or range_end > end):
                raise ContextError(source, cursor,
                                   f'{logical_path}.{field}[{index}] continues [{start},{end})',
                                   span)
            cursor = range_end
        if cursor != end:
            raise ContextError(source, cursor,
                               f'{logical_path}.{field} tiles [{start},{end})', cursor)

    logical_sha = row.get('logicalSha256')
    check_hash(logical_sha, 'logicalSha256')
    check(row.get('boundaryClass'), 'exact-closed', 'boundaryClass')
    hard_limit = row.get('hardLimit')
    if type(hard_limit) is not int or hard_limit <= 0:
        raise ContextError(source, 0, f'{logical_path}.hardLimit is a positive byte limit',
                           hard_limit)
    parser_cursor = row.get('parserCursor')
    if type(parser_cursor) is not int or parser_cursor != hard_limit:
        raise ContextError(source, 0,
                           f'{logical_path}.parserCursor equals exact hard limit {hard_limit}',
                           parser_cursor)
    check_context(row.get('boundaryContext'), 'boundaryContext', start=0,
                  cursor=parser_cursor, hard_limit=hard_limit, logical_sha=logical_sha)

    prefix = row.get('commonPrefixFraming')
    if not isinstance(prefix, dict):
        raise ContextError(source, 0, f'{logical_path}.commonPrefixFraming is present',
                           type(prefix).__name__)
    prefix_cursor = prefix.get('parserCursor')
    check(prefix_cursor, 10, 'commonPrefixFraming.parserCursor')
    check(prefix.get('hardLimit'), hard_limit, 'commonPrefixFraming.hardLimit')
    check(integer(prefix.get('cursorOffset'), 'commonPrefixFraming.cursorOffset'),
          prefix_cursor, 'commonPrefixFraming.cursorOffset')
    check_context(prefix.get('boundaryContext'), 'commonPrefixFraming.boundaryContext',
                  start=0, cursor=parser_cursor, hard_limit=hard_limit,
                  logical_sha=logical_sha)
    tile(prefix.get('byteRanges'), 0, prefix_cursor, 'commonPrefixFraming.byteRanges')

    framing = row.get('framing')
    if not isinstance(framing, dict):
        raise ContextError(source, 0, f'{logical_path}.framing is present',
                           type(framing).__name__)
    check(framing.get('status'), 'ambiguous-exact-terminal-shape', 'framing.status')
    check(framing.get('memberCount'), 48, 'framing.memberCount')
    check(framing.get('wholeSchemaExact'), True, 'framing.wholeSchemaExact')
    check(framing.get('serializedFieldOrderStatus'), 'unresolved',
          'framing.serializedFieldOrderStatus')
    ambiguity = framing.get('ambiguity')
    if not isinstance(ambiguity, dict):
        raise ContextError(source, 0, f'{logical_path}.framing.ambiguity is present',
                           type(ambiguity).__name__)
    check(ambiguity.get('kind'), 'one-byte-bool-vs-counted-wrapper-collision',
          'framing.ambiguity.kind')
    check(ambiguity.get('resolutionStatus'), 'unresolved-both-exact-to-eof',
          'framing.ambiguity.resolutionStatus')
    check(ambiguity.get('sharedCountedRecordCounts'), [0, 0, 0],
          'framing.ambiguity.sharedCountedRecordCounts')

    candidates = framing.get('candidates')
    if not isinstance(candidates, list) or len(candidates) != 2:
        raise ContextError(source, parser_cursor,
                           f'{logical_path}.framing.candidates has exactly two shapes',
                           type(candidates).__name__ if not isinstance(candidates, list)
                           else len(candidates))
    check(framing.get('candidateCount'), len(candidates), 'framing.candidateCount')
    evidence_candidates = []
    normalized_starts = []
    expected_shape = [
        'bool', 'counted-member-record-list',
        'counted-nested-object-list-a', 'counted-nested-object-list-b', 'bool',
    ]
    for index, candidate in enumerate(candidates):
        field = f'framing.candidates[{index}]'
        if not isinstance(candidate, dict):
            raise ContextError(source, parser_cursor, f'{logical_path}.{field} is an object',
                               type(candidate).__name__)
        start = integer(candidate.get('startOffset'), f'{field}.startOffset', parser_cursor)
        end = integer(candidate.get('endOffset'), f'{field}.endOffset', start)
        expected_start = 518 + index
        check(start, expected_start, f'{field}.startOffset', start)
        if not (prefix_cursor <= start < end == hard_limit):
            raise ContextError(source, start,
                               f'{logical_path}.{field} is EOF-anchored inside [{prefix_cursor},{hard_limit})',
                               [start, end])
        check(candidate.get('status'), 'exact-eof-anchored-terminal-shape', f'{field}.status',
              start)
        check(candidate.get('exactToEof'), True, f'{field}.exactToEof', start)
        check(candidate.get('byteLength'), end - start, f'{field}.byteLength', start)
        check(candidate.get('parserCursor'), end, f'{field}.parserCursor', start)
        check(candidate.get('hardLimit'), hard_limit, f'{field}.hardLimit', start)
        check(candidate.get('boundaryClass'),
              'selected-terminal' if index == 0 else 'rejected-alternative',
              f'{field}.boundaryClass', start)
        candidate_range = candidate.get('candidateRange')
        if not isinstance(candidate_range, dict):
            raise ContextError(source, start, f'{logical_path}.{field}.candidateRange is an object',
                               candidate_range)
        check(candidate_range.get('start'), start, f'{field}.candidateRange.start', start)
        check(candidate_range.get('end'), end, f'{field}.candidateRange.end', start)
        check(candidate_range.get('endExclusive'), True,
              f'{field}.candidateRange.endExclusive', start)
        check_context(candidate.get('boundaryContext'), f'{field}.boundaryContext',
                      start=start, cursor=end, hard_limit=hard_limit,
                      logical_sha=logical_sha)
        check(candidate.get('boundaryContext', {}).get('candidateRange'), [start, end],
              f'{field}.boundaryContext.candidateRange', start)

        shape = candidate.get('shape')
        check(shape, expected_shape, f'{field}.shape', start)
        members = candidate.get('members')
        if not isinstance(members, list) or len(members) != len(expected_shape):
            raise ContextError(source, start,
                               f'{logical_path}.{field}.members has five entries',
                               type(members).__name__ if not isinstance(members, list)
                               else len(members))
        byte_ranges = candidate.get('byteRanges')
        tile(byte_ranges, start, end, f'{field}.byteRanges')
        if len(byte_ranges) != len(members):
            raise ContextError(source, start,
                               f'{logical_path}.{field}.byteRanges has one range per member',
                               [len(byte_ranges), len(members)])
        expected_member_ranges = (
            (start, start + 1),
            (519 if index == 0 else 520, 524),
            (524, 528),
            (528, 532),
            (532, 533),
        )
        for member_index, (member, byte_range) in enumerate(zip(members, byte_ranges)):
            if not isinstance(member, dict) or not isinstance(byte_range, dict):
                raise ContextError(source, start,
                                   f'{logical_path}.{field}.members[{member_index}] and byte range are objects',
                                   [type(member).__name__, type(byte_range).__name__])
            member_range = member.get('range')
            if not isinstance(member_range, dict):
                raise ContextError(source, start,
                                   f'{logical_path}.{field}.members[{member_index}].range is an object',
                                   member_range)
            expected_member_start, expected_member_end = expected_member_ranges[member_index]
            expected_member_range = {
                'start': expected_member_start,
                'end': expected_member_end,
                'byteLength': expected_member_end - expected_member_start,
            }
            check(member_range, expected_member_range,
                  f'{field}.members[{member_index}].range', start)
            check(byte_range.get('start'), member_range.get('start'),
                  f'{field}.byteRanges[{member_index}].start', start)
            check(byte_range.get('end'), member_range.get('end'),
                  f'{field}.byteRanges[{member_index}].end', start)
            check(byte_range.get('kind'), member.get('kind'),
                  f'{field}.byteRanges[{member_index}].kind', start)
            check(byte_range.get('memberIndex'), member_index,
                  f'{field}.byteRanges[{member_index}].memberIndex', start)
        check(members[0].get('kind'), 'bool', f'{field}.members[0].kind', start)
        check(members[0].get('range'), {
            'start': start, 'end': start + 1, 'byteLength': 1,
        }, f'{field}.members[0].range', start)
        check(members[0].get('value'), index == 1, f'{field}.members[0].value', start)
        check(candidate.get('encoding'), 'one-member-wrapper' if index == 0 else 'counted',
              f'{field}.encoding', start)
        list_member = members[1]
        check(list_member.get('kind'), 'counted-member-record-list',
              f'{field}.members[1].kind', start)
        check(list_member.get('count'), 0, f'{field}.members[1].count', start)
        check(list_member.get('encoding'), 'one-member-wrapper' if index == 0 else 'counted',
              f'{field}.members[1].encoding', start)
        wrapper = list_member.get('wrapperRange')
        if index == 0:
            check(wrapper, {'start': start + 1, 'end': start + 2, 'byteLength': 1},
                  f'{field}.members[1].wrapperRange', start)
        else:
            check(wrapper, None, f'{field}.members[1].wrapperRange', start)
        count_range = list_member.get('countRange')
        if not isinstance(count_range, dict):
            raise ContextError(source, start, f'{logical_path}.{field}.members[1].countRange is an object',
                               count_range)
        check(count_range.get('start'), 520, f'{field}.members[1].countRange.start', start)
        check(count_range.get('end'), 524, f'{field}.members[1].countRange.end', start)
        for member_index in (2, 3):
            nested = members[member_index]
            check(nested.get('kind'), 'counted-nested-object-list',
                  f'{field}.members[{member_index}].kind', start)
            check(nested.get('count'), 0, f'{field}.members[{member_index}].count', start)
            nested_range = nested.get('range')
            nested_count_range = nested.get('countRange')
            if not isinstance(nested_range, dict) or not isinstance(nested_count_range, dict):
                raise ContextError(source, start,
                                   f'{logical_path}.{field}.members[{member_index}] has bounded range objects',
                                   [nested_range, nested_count_range])
            check(nested_range, nested_count_range,
                  f'{field}.members[{member_index}].range equals countRange', start)
            check(nested_range.get('byteLength'), 4,
                  f'{field}.members[{member_index}].range.byteLength', start)
        final_member = members[4]
        check(final_member.get('kind'), 'bool', f'{field}.members[4].kind', start)
        check(final_member.get('value'), False, f'{field}.members[4].value', start)
        check(final_member.get('range'), {
            'start': hard_limit - 1, 'end': hard_limit, 'byteLength': 1,
        }, f'{field}.members[4].range', start)
        opaque = candidate.get('opaqueByteRanges')
        check(opaque, [{
            'start': prefix_cursor, 'end': start,
            'kind': 'opaque-between-prefix-and-terminal-candidate',
        }], f'{field}.opaqueByteRanges', start)
        normalized_starts.append(start)
        evidence_candidates.append({
            'encoding': candidate.get('encoding'),
            'start': start,
            'end': end,
            'byteLength': end - start,
            'parserCursor': end,
            'hardLimit': hard_limit,
            'boundaryContext': candidate.get('boundaryContext'),
            'candidateRange': candidate_range,
            'classification': candidate.get('boundaryClass'),
            'byteRanges': byte_ranges,
            'opaqueByteRanges': opaque,
            'terminalMembers': members,
        })

    check(normalized_starts[1] - normalized_starts[0], 1,
          'framing.candidates are shifted by one byte', normalized_starts[0])
    starts_as_hex = [candidate.get('startOffset') for candidate in candidates]
    check(ambiguity.get('candidateStartOffsets'), starts_as_hex,
          'framing.ambiguity.candidateStartOffsets', normalized_starts[0])
    if evidence_candidates[0]['terminalMembers'][2:] != evidence_candidates[1]['terminalMembers'][2:]:
        raise ContextError(source, normalized_starts[0],
                           f'{logical_path}.framing.candidates share the final three member ranges',
                           'different suffix manifests')

    envelope = framing.get('envelope')
    if not isinstance(envelope, dict):
        raise ContextError(source, 0, f'{logical_path}.framing.envelope is present',
                           type(envelope).__name__)
    check(integer(envelope.get('startOffset'), 'framing.envelope.startOffset'), 0,
          'framing.envelope.startOffset')
    check(integer(envelope.get('endOffset'), 'framing.envelope.endOffset'), hard_limit,
          'framing.envelope.endOffset', hard_limit)
    check(envelope.get('byteLength'), hard_limit, 'framing.envelope.byteLength')

    return {
        'inputSetSha256': input_set,
        'logicalFileIdentity': logical_path,
        'logicalSha256': logical_sha,
        'sourceRange': {'start': 0, 'end': hard_limit, 'endExclusive': True},
        'parserCursor': parser_cursor,
        'prefixCursor': prefix_cursor,
        'hardLimit': hard_limit,
        'consumedPrefixByteRanges': prefix.get('byteRanges'),
        'candidates': evidence_candidates,
        'classification': 'selected-by-authenticated-runtime-cursor',
        'resolutionStatus': ambiguity.get('resolutionStatus'),
        'sharedCountedRecordCounts': ambiguity.get('sharedCountedRecordCounts'),
        'exactClosedRecords': 1,
        'boundary': 'Both structural candidate tilings reach the same hard limit; the authenticated runtime cursor selects the one-member-wrapper candidate. This cross-check retains the rejected shifted alternative explicitly.',
    }


def skilldata_terminal_sample_byte_witness(collision, raw, *, source):
    """Recheck the selected logical file's terminal bytes against the report."""
    logical_path = collision.get('logicalFileIdentity')
    logical_sha = collision.get('logicalSha256')
    hard_limit = collision.get('hardLimit')
    input_set = collision.get('inputSetSha256')
    if not isinstance(raw, bytes):
        raise ContextError(source, 0, 'raw current SkillData logical bytes', type(raw).__name__)
    if type(hard_limit) is not int or len(raw) != hard_limit:
        raise ContextError(source, 0, f'{logical_path} byte length equals hardLimit {hard_limit}',
                           len(raw))
    digest = hashlib.sha256(raw).hexdigest().upper()
    if digest != logical_sha:
        raise ContextError(source, 0, f'{logical_path} SHA-256 equals corpus identity',
                           digest)
    candidates = collision.get('candidates')
    if not isinstance(candidates, list) or len(candidates) != 2:
        raise ContextError(source, 0, f'{logical_path} retains both terminal candidates',
                           type(candidates).__name__ if not isinstance(candidates, list)
                           else len(candidates))
    first, shifted = candidates
    start = first.get('start')
    end = first.get('end')
    if type(start) is not int or type(end) is not int or end != hard_limit or end - start != 15:
        raise ContextError(source, 0, f'{logical_path} first candidate is 15 bytes to hardLimit',
                           [start, end, hard_limit])
    if shifted.get('start') != start + 1 or shifted.get('end') != hard_limit:
        raise ContextError(source, start,
                           f'{logical_path} second candidate begins one byte later and shares EOF',
                           [shifted.get('start'), shifted.get('end')])
    if end - start > len(raw) - start:
        raise ContextError(source, start, f'{logical_path} candidate lies inside raw source',
                           [start, end, len(raw)])

    first_bool = raw[start]
    wrapper_member_count = raw[start + 1]
    count_offsets = [start + 2, start + 6, start + 10]
    counts = []
    for offset in count_offsets:
        if offset + 4 > end:
            raise ContextError(source, offset, 'four-byte terminal list count inside hardLimit',
                               [offset, end])
        counts.append(struct.unpack_from('<i', raw, offset)[0])
    final_bool = raw[end - 1]
    if first_bool not in (0, 1) or final_bool not in (0, 1):
        raise ContextError(source, start,
                           'terminal boolean bytes are normalized zero or one',
                           [first_bool, final_bool])
    if wrapper_member_count != 1:
        raise ContextError(source, start + 1,
                           'GameplayTagList member header is one',
                           wrapper_member_count)
    if counts != [0, 0, 0]:
        raise ContextError(source, count_offsets[0],
                           'current terminal sample contains three signed zero counts',
                           counts)
    members = first.get('terminalMembers')
    if not isinstance(members, list) or len(members) != 5:
        raise ContextError(source, start, 'first candidate preserves five terminal members',
                           type(members).__name__ if not isinstance(members, list)
                           else len(members))
    if members[0].get('value') != bool(first_bool) or members[4].get('value') != bool(final_bool):
        raise ContextError(source, start,
                           'raw first/final booleans match the current candidate parse',
                           [first_bool, final_bool])
    shifted_members = shifted.get('terminalMembers')
    if (not isinstance(shifted_members, list) or len(shifted_members) != 5 or
            shifted_members[0].get('value') != bool(wrapper_member_count)):
        raise ContextError(source, start + 1,
                           'shifted candidate interprets the wrapper byte as its first boolean',
                           shifted_members)
    return {
        'inputSetSha256': input_set,
        'logicalFileIdentity': logical_path,
        'logicalSha256': digest,
        'byteLength': len(raw),
        'hardLimit': hard_limit,
        'candidateRange': {'start': start, 'end': end, 'endExclusive': True},
        'parserCursor': end,
        'terminalRawHex': raw[start:end].hex().upper(),
        'firstBooleanByte': {'offset': start, 'value': bool(first_bool)},
        'nestedMemberCountByte': {'offset': start + 1, 'value': wrapper_member_count},
        'signedListCounts': [
            {'offset': offset, 'value': count}
            for offset, count in zip(count_offsets, counts)
        ],
        'finalBooleanByte': {'offset': end - 1, 'value': bool(final_bool)},
        'boundary': 'The source bytes and corpus row agree for this logical identity and hard limit; this byte witness alone does not select a runtime formatter.',
    }


def select_skilldata_terminal_branch_samples(corpus, *, source):
    """Choose deterministic current files for every observed positive tail-list count."""
    input_set = corpus.get('inputSetSha256')
    if (not isinstance(input_set, str) or len(input_set) != 64 or
            any(ch not in '0123456789abcdefABCDEF' for ch in input_set)):
        raise ContextError(source, 0, '64-hex SkillData inputSetSha256', input_set)
    files = corpus.get('files')
    if not isinstance(files, list):
        raise ContextError(source, 0, 'current SkillData file row list', type(files).__name__)
    branch_fields = {
        1: 'tagDuringAttach.predefinedTag',
        2: 'toggleBuffs',
        3: 'uiRangeHints',
    }
    requirements = []
    for member_index, field_name in branch_fields.items():
        observed_counts = set()
        for row in files:
            if not isinstance(row, dict):
                continue
            candidates = row.get('framing', {}).get('candidates', [])
            if (not isinstance(candidates, list) or len(candidates) != 2 or
                    candidates[0].get('encoding') != 'one-member-wrapper'):
                continue
            members = candidates[0].get('members', [])
            if not isinstance(members, list) or len(members) != 5:
                continue
            count = members[member_index].get('count')
            if type(count) is int and count > 0:
                observed_counts.add(count)
        if not observed_counts:
            raise ContextError(source, 0,
                               f'current corpus has a positive {field_name} branch', 0)
        requirements.extend(
            {'fieldName': field_name, 'memberIndex': member_index, 'count': count}
            for count in sorted(observed_counts)
        )
    selected = []
    for requirement in requirements:
        matches = []
        for row in files:
            if not isinstance(row, dict):
                continue
            candidates = row.get('framing', {}).get('candidates', [])
            if not isinstance(candidates, list) or len(candidates) != 2:
                continue
            members = candidates[0].get('members', [])
            index = requirement['memberIndex']
            if (candidates[0].get('encoding') == 'one-member-wrapper' and
                    isinstance(members, list) and len(members) == 5 and
                    isinstance(members[index], dict) and
                    members[index].get('count') == requirement['count']):
                matches.append(row)
        if not matches:
            raise ContextError(source, 0,
                               f'current corpus has a positive {requirement["fieldName"]} branch with count {requirement["count"]}',
                               0)
        selected.append({**requirement, 'row': matches[0]})
    if len({sample['row'].get('virtualPath') for sample in selected}) != len(selected):
        raise ContextError(source, 0, 'distinct current SkillData branch sample identities',
                           [sample['row'].get('virtualPath') for sample in selected])
    return selected


def skilldata_shifted_terminal_wrapper_probe(raw, first_candidate_start,
                                             hard_limit, *, source):
    """Record how a one-byte-shifted SkillData tail reaches GameplayTagList."""
    if not isinstance(raw, bytes):
        raise ContextError(source, 0, 'raw sample bytes', type(raw).__name__)
    if (type(first_candidate_start) is not int or first_candidate_start < 0 or
            type(hard_limit) is not int or hard_limit != len(raw) or
            first_candidate_start + 1 >= hard_limit):
        raise ContextError(source, first_candidate_start
                           if type(first_candidate_start) is int else 0,
                           'first candidate start and hardLimit bound the raw sample',
                           [first_candidate_start, hard_limit, len(raw)])
    shifted_start = first_candidate_start + 1
    wrapper_offset = shifted_start + 1
    if wrapper_offset >= hard_limit:
        raise ContextError(source, wrapper_offset,
                           'shifted candidate has an in-limit GameplayTagList header',
                           hard_limit)
    header = raw[wrapper_offset]
    result = {
        'shiftedCandidateStart': shifted_start,
        'shiftedBooleanByte': {'offset': shifted_start,
                               'value': raw[shifted_start]},
        'gameplayTagListHeaderByte': {'offset': wrapper_offset,
                                      'value': header},
        'nestedListCount': None,
    }
    if header == 1:
        count_offset = wrapper_offset + 1
        count_end = count_offset + 4
        available = max(0, min(4, hard_limit - count_offset))
        count_bytes = raw[count_offset:count_offset + available]
        count_row = {
            'offset': count_offset,
            'availableByteLength': available,
            'rawHex': count_bytes.hex().upper(),
            'complete': available == 4,
        }
        if available == 4:
            count_row.update({
                'signedI32': struct.unpack('<i', count_bytes)[0],
                'remainingAfterCount': hard_limit - count_end,
            })
        result['nestedListCount'] = count_row
    return result


def skilldata_terminal_branch_sample_witness(corpus, selection, raw, *, source):
    """Reparse two EOF hypotheses from a byte-authenticated nonempty branch sample."""
    if not isinstance(selection, dict) or not isinstance(selection.get('row'), dict):
        raise ContextError(source, 0, 'selected SkillData branch row', selection)
    row = selection['row']
    logical_path = row.get('virtualPath')
    logical_sha = row.get('logicalSha256')
    input_set = corpus.get('inputSetSha256')
    corpus_rows = [candidate for candidate in corpus.get('files', [])
                   if isinstance(candidate, dict) and
                   candidate.get('virtualPath') == logical_path]
    if len(corpus_rows) != 1 or corpus_rows[0] != row:
        raise ContextError(source, 0, 'selected row is the unique current corpus identity',
                           [len(corpus_rows), logical_path])
    if not isinstance(logical_path, str) or not logical_path.startswith(
            'Data/Json/SkillData/'):
        raise ContextError(source, 0, 'logical SkillData sample identity', logical_path)
    if (not isinstance(input_set, str) or len(input_set) != 64 or
            any(ch not in '0123456789abcdefABCDEF' for ch in input_set)):
        raise ContextError(source, 0, '64-hex current SkillData inputSetSha256', input_set)
    if (not isinstance(logical_sha, str) or len(logical_sha) != 64 or
            any(ch not in '0123456789abcdefABCDEF' for ch in logical_sha)):
        raise ContextError(source, 0, '64-hex logical sample SHA-256', logical_sha)
    if (not isinstance(raw, bytes) or type(row.get('hardLimit')) is not int or
            len(raw) != row['hardLimit']):
        raise ContextError(source, 0, 'sample byte length equals current hardLimit',
                           [len(raw) if isinstance(raw, bytes) else type(raw).__name__,
                            row.get('hardLimit')])
    digest = hashlib.sha256(raw).hexdigest().upper()
    if digest != logical_sha:
        raise ContextError(source, 0, 'sample bytes match current logical SHA-256',
                           [logical_sha, digest])
    hard_limit = row['hardLimit']
    parser_cursor = row.get('parserCursor')
    context = row.get('boundaryContext')
    if type(parser_cursor) is not int or not 0 < parser_cursor <= hard_limit:
        raise ContextError(source, 0, 'current row cursor at or inside hardLimit',
                           parser_cursor)
    for field, expected in (
            ('inputSetSha256', input_set), ('logicalFileIdentity', logical_path),
            ('logicalSha256', logical_sha), ('parserCursor', parser_cursor),
            ('hardLimit', hard_limit)):
        if not isinstance(context, dict) or context.get(field) != expected:
            raise ContextError(source, 0, f'boundaryContext.{field} matches current sample',
                               context.get(field) if isinstance(context, dict) else context)
    if row.get('boundaryClass') not in ('structural-prefix', 'exact-closed'):
        raise ContextError(source, 0, 'branch sample has a supported current boundary',
                           row.get('boundaryClass'))
    prefix = row.get('commonPrefixFraming')
    prefix_cursor = prefix.get('parserCursor') if isinstance(prefix, dict) else None
    if type(prefix_cursor) is not int or not 0 < prefix_cursor < hard_limit:
        raise ContextError(source, 0, 'current ActionGroup prefix cursor inside hardLimit',
                           prefix_cursor)
    parser_cursor = prefix_cursor
    framing = row.get('framing')
    candidates = framing.get('candidates') if isinstance(framing, dict) else None
    if not isinstance(candidates, list) or len(candidates) != 2:
        raise ContextError(source, 0, 'two EOF-anchored branch candidates', candidates)
    first, shifted = candidates
    def offset(value, field):
        if type(value) is int and value >= 0:
            return value
        if isinstance(value, str):
            try:
                parsed = int(value, 0)
            except ValueError:
                parsed = -1
            if parsed >= 0:
                return parsed
        raise ContextError(source, 0, f'{field} is a bounded byte offset', value)

    start = offset(first.get('startOffset'), 'candidate[0].startOffset')
    shifted_start = offset(shifted.get('startOffset'), 'candidate[1].startOffset')
    if (shifted_start != start + 1 or start < parser_cursor or
            offset(first.get('endOffset'), 'candidate[0].endOffset') != hard_limit or
            offset(shifted.get('endOffset'), 'candidate[1].endOffset') != hard_limit or
            first.get('encoding') != 'one-member-wrapper' or
            shifted.get('encoding') != 'counted'):
        raise ContextError(source, start,
                           'wrapper/count candidates are shifted one byte and share hardLimit',
                           [first.get('startOffset'), shifted.get('startOffset'),
                            first.get('endOffset'), shifted.get('endOffset'),
                            first.get('encoding'), shifted.get('encoding')])
    for candidate_index, (candidate, candidate_start) in enumerate(
            ((first, start), (shifted, shifted_start))):
        candidate_context = candidate.get('boundaryContext')
        expected_candidate_range = [candidate_start, hard_limit]
        for field, expected in (
                ('inputSetSha256', input_set),
                ('logicalFileIdentity', logical_path),
                ('logicalSha256', logical_sha),
                ('startOffset', candidate_start),
                ('hardLimit', hard_limit),
                ('parserCursor', hard_limit),
                ('candidateRange', expected_candidate_range)):
            if (not isinstance(candidate_context, dict) or
                    candidate_context.get(field) != expected):
                raise ContextError(source, candidate_start,
                                   f'candidate[{candidate_index}].boundaryContext.{field} matches current sample',
                                   candidate_context.get(field)
                                   if isinstance(candidate_context, dict)
                                   else candidate_context)

    def tile(ranges, begin, end, label):
        if not isinstance(ranges, list):
            raise ContextError(source, begin, f'{label} is a bounded byte-range list',
                               type(ranges).__name__)
        cursor = begin
        for index, span in enumerate(ranges):
            if (not isinstance(span, dict) or type(span.get('start')) is not int or
                    type(span.get('end')) is not int or span['start'] != cursor or
                    span['end'] <= span['start'] or span['end'] > end):
                raise ContextError(source, cursor, f'{label}[{index}] continues [{begin},{end})',
                                   span)
            cursor = span['end']
        if cursor != end:
            raise ContextError(source, cursor, f'{label} tiles [{begin},{end})', cursor)

    def replay(candidate_report, candidate_start, expected_encoding):
        try:
            parsed_report = frame_skill_terminal_at(
                raw, candidate_start, source=logical_path)
        except SkillTerminalError as error:
            raise ContextError(source, candidate_start,
                               f'current raw sample reparses {expected_encoding} candidate',
                               error.diagnostics) from error
        parsed = [candidate for candidate in parsed_report.get('candidates', [])
                  if candidate.get('encoding') == expected_encoding and
                  candidate.get('end') == hard_limit]
        if len(parsed) != 1:
            raise ContextError(source, candidate_start,
                               f'one raw-parsed {expected_encoding} candidate ends at hardLimit',
                               [(candidate.get('encoding'), candidate.get('end'))
                                for candidate in parsed_report.get('candidates', [])])
        parsed_candidate = parsed[0]
        expected_boundary = ('selected-terminal' if expected_encoding == 'one-member-wrapper'
                             else 'rejected-alternative')
        if (candidate_report.get('boundaryClass') != expected_boundary or
                candidate_report.get('exactToEof') is not True or
                candidate_report.get('parserCursor') != hard_limit or
                candidate_report.get('hardLimit') != hard_limit):
            raise ContextError(source, candidate_start,
                               'corpus candidate has selected/rejected status and ends exactly at hardLimit',
                               candidate_report)
        candidate_range = candidate_report.get('candidateRange')
        if (not isinstance(candidate_range, dict) or
                candidate_range.get('start') != candidate_start or
                candidate_range.get('end') != hard_limit or
                candidate_range.get('endExclusive') is not True):
            raise ContextError(source, candidate_start,
                               'candidate range equals raw parser [start,hardLimit)',
                               candidate_range)
        if (parsed_candidate.get('start') != candidate_start or
                parsed_candidate.get('byteLength') != hard_limit - candidate_start):
            raise ContextError(source, candidate_start, 'raw parser candidate byte span',
                               [parsed_candidate.get('start'), parsed_candidate.get('end')])
        report_members = candidate_report.get('members')
        parsed_members = parsed_candidate.get('members')
        if (not isinstance(report_members, list) or len(report_members) != 5 or
                not isinstance(parsed_members, list) or len(parsed_members) != 5):
            raise ContextError(source, candidate_start,
                               'five current terminal members in report and raw parse',
                               [report_members, parsed_members])
        for member_index, (reported, parsed_member) in enumerate(
                zip(report_members, parsed_members)):
            if reported.get('range') != parsed_member.get('range'):
                raise ContextError(source, candidate_start,
                                   f'candidate member {member_index} raw/report byte range',
                                   [reported.get('range'), parsed_member.get('range')])
            if 'count' in parsed_member and reported.get('count') != parsed_member.get('count'):
                raise ContextError(source, candidate_start,
                                   f'candidate member {member_index} raw/report count',
                                   [reported.get('count'), parsed_member.get('count')])
            report_records = reported.get('records', [])
            parsed_records = parsed_member.get('records', [])
            if len(report_records) != len(parsed_records):
                raise ContextError(source, candidate_start,
                                   f'candidate member {member_index} raw/report record count',
                                   [len(report_records), len(parsed_records)])
            for record_index, (reported_record, parsed_record) in enumerate(
                    zip(report_records, parsed_records)):
                if (reported_record.get('range') != parsed_record.get('range') or
                        reported_record.get('memberCount') != parsed_record.get('memberCount')):
                    raise ContextError(source, candidate_start,
                                       f'candidate member {member_index} record {record_index} raw/report range/header',
                                       [reported_record, parsed_record])
        byte_ranges = candidate_report.get('byteRanges')
        tile(byte_ranges, candidate_start, hard_limit,
             f'{logical_path} {expected_encoding} candidate byteRanges')
        if len(byte_ranges) != 5:
            raise ContextError(source, candidate_start,
                               'candidate byte-range manifest has five outer members',
                               len(byte_ranges))
        return parsed_candidate

    parsed_first = replay(first, start, 'one-member-wrapper')
    parsed_shifted = replay(shifted, shifted_start, 'counted')
    wrapper_header = raw[start + 1]
    if wrapper_header != 1:
        raise ContextError(source, start + 1, 'GameplayTagList one-member raw header', wrapper_header)
    if raw[start] not in (0, 1) or raw[hard_limit - 1] not in (0, 1):
        raise ContextError(source, start, 'terminal bool bytes are zero or one',
                           [raw[start], raw[hard_limit - 1]])
    if (first['members'][0].get('value') != bool(raw[start]) or
            first['members'][4].get('value') != bool(raw[hard_limit - 1]) or
            shifted['members'][0].get('value') != bool(wrapper_header)):
        raise ContextError(source, start, 'raw bool/header bytes match both shifted candidate parses',
                           [first['members'][0], shifted['members'][0], first['members'][4]])

    list_counts = []
    for member_index in (1, 2, 3):
        member = first['members'][member_index]
        count_range = member.get('countRange')
        if (not isinstance(count_range, dict) or type(count_range.get('start')) is not int or
                count_range.get('end') != count_range.get('start') + 4 or
                count_range['end'] > hard_limit):
            raise ContextError(source, start,
                               f'terminal member {member_index} has an in-limit four-byte count range',
                               count_range)
        raw_count = struct.unpack_from('<I', raw, count_range['start'])[0]
        count_value = None if member_index == 1 and raw_count == 0xFFFFFFFF else raw_count
        if count_value != member.get('count'):
            raise ContextError(source, count_range['start'],
                               f'terminal member {member_index} raw count matches report',
                               [member.get('count'), count_value])
        list_counts.append({
            'memberIndex': member_index,
            'fieldName': ('tagDuringAttach.predefinedTag' if member_index == 1 else
                          'toggleBuffs' if member_index == 2 else 'uiRangeHints'),
            'countRange': count_range,
            'count': count_value,
            'recordRanges': [record.get('range') for record in member.get('records', [])],
            'recordHeaderMemberCounts': [
                record.get('memberCount') for record in member.get('records', [])
            ],
        })
    member_index = selection.get('memberIndex')
    expected_count = selection.get('count')
    if member_index not in (1, 2, 3) or type(expected_count) is not int or expected_count <= 0:
        raise ContextError(source, 0, 'selected positive SkillData list branch',
                           [member_index, expected_count])
    branch_count = first['members'][member_index].get('count')
    if branch_count != expected_count:
        raise ContextError(source, start,
                           f'selected {selection.get("fieldName")} count is {expected_count}',
                           branch_count)
    return {
        'inputSetSha256': input_set,
        'logicalFileIdentity': logical_path,
        'logicalSha256': digest,
        'sourceRange': {'start': 0, 'end': hard_limit, 'endExclusive': True},
        'parserCursor': parser_cursor,
        'hardLimit': hard_limit,
        'terminalCandidateRanges': [
            {'start': start, 'end': hard_limit, 'endExclusive': True},
            {'start': shifted_start, 'end': hard_limit, 'endExclusive': True},
        ],
        'shiftedCandidateTypeProbe': skilldata_shifted_terminal_wrapper_probe(
            raw, start, hard_limit, source=source),
        'rawWrapperHeaderByte': {'offset': start + 1, 'value': wrapper_header},
        'terminalBooleanBytes': [
            {'offset': start, 'value': bool(raw[start])},
            {'offset': hard_limit - 1, 'value': bool(raw[hard_limit - 1])},
        ],
        'listCounts': list_counts,
        'positiveBranch': {
            'fieldName': selection['fieldName'],
            'memberIndex': member_index,
            'count': branch_count,
            'recordRanges': [record.get('range') for record in
                             first['members'][member_index].get('records', [])],
            'recordHeaderMemberCounts': [record.get('memberCount') for record in
                                         first['members'][member_index].get('records', [])],
        },
        'rawParserReplay': {
            'oneMemberWrapperCandidate': {
                'start': parsed_first['start'], 'end': parsed_first['end'],
                'encoding': parsed_first['encoding'],
            },
            'shiftedCountedCandidate': {
                'start': parsed_shifted['start'], 'end': parsed_shifted['end'],
                'encoding': parsed_shifted['encoding'],
            },
        },
        'classification': 'terminal-selected-with-bounded-middle',
        'staticShapeDisposition': 'wrapper candidate matches the exact SkillData tail order; shifted counted candidate conflicts with the one-member wrapper if registered paths are selected',
        'exactClosedRecords': 0,
        'boundary': 'Current raw bytes, parser replay and report ranges agree for this nonempty branch sample. The accepted runtime cursor selects the wrapper candidate while the middle remains bounded; record internals remain anonymous where noted.',
    }


def skilldata_positive_branch_reader_replay(sample, raw, *, source):
    """Replay one positive terminal-list branch with its bounded nested reader."""
    if not isinstance(sample, dict) or not isinstance(raw, bytes):
        raise ContextError(source, 0, 'branch witness object and raw bytes',
                           [type(sample).__name__, type(raw).__name__])
    input_set = sample.get('inputSetSha256')
    logical_path = sample.get('logicalFileIdentity')
    digest = hashlib.sha256(raw).hexdigest().upper()
    hard_limit = sample.get('hardLimit')
    if not isinstance(input_set, str) or len(input_set) != 64:
        raise ContextError(source, 0, '64-character current inputSetSha256', input_set)
    if not isinstance(logical_path, str) or not logical_path.startswith('Data/Json/SkillData/'):
        raise ContextError(source, 0, 'logical SkillData VFS identity', logical_path)
    require(sample.get('logicalSha256'), digest, source)
    require(hard_limit, len(raw), source)
    require(sample.get('sourceRange'),
            {'start': 0, 'end': hard_limit, 'endExclusive': True}, source)
    require(sample.get('classification'), 'terminal-selected-with-bounded-middle', source)
    require(sample.get('exactClosedRecords'), 0, source)

    candidate_ranges = sample.get('terminalCandidateRanges')
    if (not isinstance(candidate_ranges, list) or len(candidate_ranges) != 2 or
            any(not isinstance(row, dict) for row in candidate_ranges)):
        raise ContextError(source, 0, 'two bounded terminal candidate ranges', candidate_ranges)
    start = candidate_ranges[0].get('start')
    for ordinal, row in enumerate(candidate_ranges):
        if (type(row.get('start')) is not int or row.get('end') != hard_limit or
                row.get('endExclusive') is not True or
                row.get('start') != start + ordinal):
            raise ContextError(source, start if type(start) is int else 0,
                               'two adjacent shifted [start, hardLimit) candidates', row)
    if type(start) is not int or start < 0 or start + 1 >= hard_limit:
        raise ContextError(source, 0, 'in-limit first terminal candidate start', start)

    branch = sample.get('positiveBranch')
    if not isinstance(branch, dict):
        raise ContextError(source, start, 'positive branch evidence object', branch)
    field_name = branch.get('fieldName')
    member_index = branch.get('memberIndex')
    count = branch.get('count')
    record_ranges = branch.get('recordRanges')
    header_counts = branch.get('recordHeaderMemberCounts')
    if (field_name not in ('tagDuringAttach.predefinedTag', 'toggleBuffs', 'uiRangeHints') or
            type(member_index) is not int or member_index not in (1, 2, 3) or
            type(count) is not int or count <= 0 or
            not isinstance(record_ranges, list) or len(record_ranges) != count or
            not isinstance(header_counts, list) or len(header_counts) != count):
        raise ContextError(source, start, 'positive bounded nested list branch',
                           [field_name, member_index, count, record_ranges, header_counts])
    expected_field_by_index = {
        1: 'tagDuringAttach.predefinedTag', 2: 'toggleBuffs', 3: 'uiRangeHints'}
    require(field_name, expected_field_by_index[member_index], source, start)
    count_rows = [row for row in sample.get('listCounts', [])
                  if isinstance(row, dict) and row.get('memberIndex') == member_index]
    if len(count_rows) != 1:
        raise ContextError(source, start, 'one raw count witness for selected list member',
                           count_rows)
    count_row = count_rows[0]
    require(count_row.get('fieldName'), field_name, source, start)
    require(count_row.get('count'), count, source, start)
    require(count_row.get('recordRanges'), record_ranges, source, start)
    require(count_row.get('recordHeaderMemberCounts'), header_counts, source, start)
    for ordinal, span in enumerate(record_ranges):
        if (not isinstance(span, dict) or type(span.get('start')) is not int or
                type(span.get('end')) is not int or span['start'] < start or
                span['end'] <= span['start'] or span['end'] > hard_limit):
            raise ContextError(source, start, 'nested record range within hardLimit', span)
        if ordinal and span['start'] != record_ranges[ordinal - 1].get('end'):
            raise ContextError(source, span['start'],
                               'selected sibling nested records are contiguous',
                               [record_ranges[ordinal - 1], span])

    replayed_records = []
    if field_name == 'tagDuringAttach.predefinedTag':
        count_range = count_row.get('countRange')
        if (not isinstance(count_range, dict) or
                type(count_range.get('start')) is not int or
                count_range.get('end') != count_range['start'] + 4):
            raise ContextError(source, start, 'four-byte wrapped GameplayTag count range',
                               count_range)
        reader_start = count_range['start'] - 1
        require(reader_start, start + 1, source, reader_start)
        require(raw[reader_start], 1, source, reader_start)
        try:
            parsed, cursor = read_skill_gameplay_tag_list_field(
                raw, reader_start, 'tagDuringAttach')
        except ValueError as error:
            raise ContextError(source, reader_start,
                               'bounded one-member GameplayTagList parser replay', str(error)) from error
        require(parsed.get('branch'), 'one-member-wrapper', source, reader_start)
        require(parsed.get('prefixMemberCount'), 1, source, reader_start)
        require(parsed.get('count'), count, source, reader_start)
        expected_cursor = record_ranges[-1]['end']
        require(cursor, expected_cursor, source, reader_start)
        parsed_tags = parsed.get('tags')
        if not isinstance(parsed_tags, list) or len(parsed_tags) != count:
            raise ContextError(source, reader_start, 'one parsed GameplayTag per bounded count',
                               parsed_tags)
        for ordinal, (tag, span, header) in enumerate(
                zip(parsed_tags, record_ranges, header_counts)):
            tag_start = int(tag.get('offset', '0'), 16)
            tag_end = tag_start + tag.get('byteLength', 0)
            require({'start': tag_start, 'end': tag_end},
                    {'start': span['start'], 'end': span['end']}, source, tag_start)
            require(tag.get('memberCount'), header, source, tag_start)
            replayed_records.append({
                'index': ordinal, 'recordRange': span,
                'memberCount': tag.get('memberCount'),
                'encoding': tag.get('encoding'),
                'tagId': tag.get('tagId'), 'tagHash': tag.get('tagHash'),
            })
        reader_row = {
            'reader': 'read_skill_gameplay_tag_list_field',
            'readerRange': {'start': reader_start, 'end': cursor, 'endExclusive': True},
            'wrapperMemberCount': parsed['prefixMemberCount'],
            'elementCount': parsed['count'],
            'elementRecords': replayed_records,
        }
    elif field_name == 'toggleBuffs':
        parser_field_order = None
        for ordinal, (span, header) in enumerate(zip(record_ranges, header_counts)):
            try:
                parsed, cursor = read_skill_toggle_buff_data(raw, span['start'], ordinal)
            except ValueError as error:
                raise ContextError(source, span['start'],
                                   'bounded ToggleBuffData reader replay', str(error)) from error
            require(cursor, span['end'], source, span['start'])
            require(parsed.get('memberCount'), header, source, span['start'])
            require(parsed.get('metadataFieldOrder'), ['buffs', 'conditions'],
                    source, span['start'])
            if parser_field_order is None:
                parser_field_order = parsed['metadataFieldOrder']
            else:
                require(parsed['metadataFieldOrder'], parser_field_order,
                        source, span['start'])
            replayed_records.append({
                'index': ordinal, 'recordRange': span,
                'memberCount': parsed['memberCount'],
                'byteLength': parsed['byteLength'],
                'buffsCount': parsed['buffsCount'],
                'conditionsCount': parsed['conditionsCount'],
            })
        reader_row = {
            'reader': 'read_skill_toggle_buff_data',
            'readerRange': {'start': record_ranges[0]['start'],
                            'end': record_ranges[-1]['end'], 'endExclusive': True},
            'parserFieldOrder': parser_field_order,
            'elementRecords': replayed_records,
        }
    else:
        for ordinal, (span, header) in enumerate(zip(record_ranges, header_counts)):
            try:
                parsed, cursor = read_skill_ui_range_hint_data(raw, span['start'], ordinal)
            except ValueError as error:
                raise ContextError(source, span['start'],
                                   'bounded UIRangeHintData/SkillHintShapeData reader replay',
                                   str(error)) from error
            require(cursor, span['end'], source, span['start'])
            require(parsed.get('memberCount'), header, source, span['start'])
            shape = parsed.get('shapeData')
            if not isinstance(shape, dict):
                raise ContextError(source, span['start'], 'nested SkillHintShapeData parse', shape)
            require(shape.get('memberCount'), 21, source, span['start'])
            shape_start = int(shape.get('offset', '0'), 16)
            shape_end = shape_start + shape.get('byteLength', 0)
            replayed_records.append({
                'index': ordinal, 'recordRange': span,
                'memberCount': parsed['memberCount'],
                'byteLength': parsed['byteLength'],
                'selectAll': parsed['selectAll'],
                'shapeData': {
                    'recordRange': {'start': shape_start, 'end': shape_end,
                                    'endExclusive': True},
                    'memberCount': shape['memberCount'],
                    'byteLength': shape['byteLength'],
                    'shapeRaw': shape.get('shapeRaw'),
                    'shapeName': shape.get('shapeName'),
                },
                'targetFactionRaw': parsed['targetFactionRaw'],
            })
        reader_row = {
            'reader': 'read_skill_ui_range_hint_data',
            'readerRange': {'start': record_ranges[0]['start'],
                            'end': record_ranges[-1]['end'], 'endExclusive': True},
            'parserFieldOrder': ['selectAll', 'shapeData', 'targetFaction'],
            'nestedShapeParserFieldOrder': [
                'angle', 'angleKey', 'centerBaseIsEndPoint', 'centerOffset',
                'centerOffsetXKey', 'centerOffsetZKey', 'extent', 'extentXKey',
                'extentZKey', 'fixedExtent', 'radius', 'radiusKey',
                'restrictEndPointInRange', 'shape', 'useAngleKey',
                'useCenterOffsetKey', 'useExtentKey', 'useRadiusKey',
                'useWidthKey', 'width', 'widthKey'],
            'elementRecords': replayed_records,
        }
    return {
        'inputSetSha256': input_set,
        'logicalFileIdentity': logical_path,
        'logicalSha256': digest,
        'hardLimit': hard_limit,
        'positiveFieldName': field_name,
        'conditionalOnTerminalCandidateStart': start,
        'terminalCandidateRanges': candidate_ranges,
        'shiftedCandidateTypeProbe': sample.get('shiftedCandidateTypeProbe'),
        'nestedReaderReplay': reader_row,
        'wholeSkillDataClassification': 'ambiguous',
        'wholeSkillDataExactClosedRecords': 0,
        'boundary': 'The bounded nested reader reaches the reported positive-list element end in these authenticated raw bytes. This does not resolve the one-byte-shifted parent tail, select a runtime provider or observe a live cursor.',
    }


def skilldata_shifted_candidate_reader_assessment(branch_replay,
                                                  gameplay_tag_list,
                                                  list_formatter, *, source):
    """Evaluate the shifted hypothesis against registered wrapper/count guards."""
    if not isinstance(branch_replay, dict) or not isinstance(gameplay_tag_list, dict):
        raise ContextError(source, 0, 'branch replay and GameplayTagList static evidence',
                           [type(branch_replay).__name__, type(gameplay_tag_list).__name__])
    hard_limit = branch_replay.get('hardLimit')
    start = branch_replay.get('conditionalOnTerminalCandidateStart')
    ranges = branch_replay.get('terminalCandidateRanges')
    probe = branch_replay.get('shiftedCandidateTypeProbe')
    if (type(hard_limit) is not int or type(start) is not int or
            not isinstance(ranges, list) or len(ranges) != 2 or
            not isinstance(probe, dict)):
        raise ContextError(source, 0, 'identity-bound shifted candidate byte probe',
                           [hard_limit, start, ranges, probe])
    expected_ranges = [
        {'start': start, 'end': hard_limit, 'endExclusive': True},
        {'start': start + 1, 'end': hard_limit, 'endExclusive': True},
    ]
    input_set = branch_replay.get('inputSetSha256')
    logical_path = branch_replay.get('logicalFileIdentity')
    logical_sha = branch_replay.get('logicalSha256')
    if (not isinstance(input_set, str) or len(input_set) != 64 or
            not isinstance(logical_path, str) or
            not logical_path.startswith('Data/Json/SkillData/') or
            not isinstance(logical_sha, str) or len(logical_sha) != 64):
        raise ContextError(source, start,
                           'current SkillData inputSet, logical identity and SHA-256',
                           [input_set, logical_path, logical_sha])
    require(ranges, expected_ranges, source, start)
    require(probe.get('shiftedCandidateStart'), start + 1, source, start + 1)
    header = gameplay_tag_list.get('headerEvidence')
    if not isinstance(header, dict):
        raise ContextError(source, start + 2, 'static GameplayTagList header evidence', header)
    header_width = header.get('headerByteWidth')
    accepted = header.get('acceptedNonNullHeaderByte')
    null_header = header.get('nullHeaderByte')
    require(header_width, 1, source, start + 2)
    require(accepted, 1, source, start + 2)
    require(null_header, 0xFF, source, start + 2)
    raw_header = probe.get('gameplayTagListHeaderByte')
    if (not isinstance(raw_header, dict) or
            raw_header.get('offset') != start + 2 or
            type(raw_header.get('value')) is not int or
            not 0 <= raw_header['value'] <= 0xFF):
        raise ContextError(source, start + 2,
                           'shifted candidate GameplayTagList header byte and offset',
                           raw_header)
    value = raw_header['value']
    assessment = {
        'inputSetSha256': input_set,
        'logicalFileIdentity': logical_path,
        'logicalSha256': logical_sha,
        'parserCursor': hard_limit,
        'hardLimit': hard_limit,
        'shiftedCandidateRange': expected_ranges[1],
        'readerFieldAfterShiftedBoolean': 'tagDuringAttach',
        'gameplayTagListHeaderByte': raw_header,
        'acceptedWrapperHeaders': [accepted, null_header],
        'runtimeProviderSelection': 'unobserved',
        'classification': 'conditional-on-registered-reader-and-provider-path',
    }
    if value not in (accepted, null_header):
        assessment.update({
            'status': 'outside-registered-GameplayTagList-header-path',
            'boundary': 'The registered GameplayTagList reader accepts only header 1 or null header 0xFF; this shifted byte is outside that path.',
        })
        return assessment
    if value == null_header:
        assessment.update({
            'status': 'not-rejected-by-null-wrapper-header',
            'boundary': 'The shifted candidate reaches the registered null-wrapper path; this probe alone does not distinguish it.',
        })
        return assessment

    count = probe.get('nestedListCount')
    if not isinstance(count, dict):
        raise ContextError(source, start + 3,
                           'one-byte wrapper header followed by bounded signed list count', count)
    if count.get('complete') is not True:
        assessment.update({
            'nestedListCount': count,
            'status': 'truncated-registered-list-count',
            'boundary': 'The registered non-null wrapper path requires a complete four-byte list count inside hardLimit.',
        })
        return assessment
    if (type(count.get('offset')) is not int or count.get('offset') != start + 3 or
            count.get('availableByteLength') != 4 or
            type(count.get('signedI32')) is not int or
            type(count.get('remainingAfterCount')) is not int or
            count['remainingAfterCount'] < 0):
        raise ContextError(source, start + 3,
                           'complete bounded signed list count and remaining byte budget', count)
    assessment['nestedListCount'] = count
    if list_formatter is None:
        assessment.update({
            'status': 'unresolved-list-formatter-selection',
            'boundary': 'The wrapper header is accepted, but no matching registered List<GameplayTag> count guard was supplied.',
        })
        return assessment
    if not isinstance(list_formatter, dict):
        raise ContextError(source, start + 3, 'registered List<GameplayTag> formatter evidence',
                           type(list_formatter).__name__)
    wrapper_inst = gameplay_tag_list.get('nestedReadInstantiation')
    formatter_inst = list_formatter.get('classInstantiation')
    if not isinstance(wrapper_inst, dict) or not isinstance(formatter_inst, dict):
        raise ContextError(source, start + 3,
                           'wrapper and formatter generic-instantiation evidence',
                           [wrapper_inst, formatter_inst])
    require(formatter_inst.get('index'), wrapper_inst.get('index'), source, start + 3)
    guard = list_formatter.get('fastHeaderGuard')
    if not isinstance(guard, dict):
        raise ContextError(source, start + 3, 'audited signed List<T> remaining-byte guard', guard)
    require(guard.get('countWidthBytes'), 4, source, start + 3)
    require(guard.get('signedCount'), True, source, start + 3)
    require(guard.get('remainingBytesComparedToCount'), True, source, start + 3)
    require(guard.get('rangeFailureCondition'), 'remaining < signed count', source, start + 3)
    require(guard.get('comparisonRva'), 0x3BA4130, source, start + 3)
    require(guard.get('comparisonRawHex'),
            '48634744488B4F18482BC84863C6483BC8', source, start + 3)
    require(guard.get('rangeFailureBranchRva'), 0x3BA4141, source, start + 3)
    require(guard.get('rangeFailureBranchRawHex'), '0F8CB4653201', source, start + 3)
    require(guard.get('rangeFailureTargetRva'), 0x4ECA6FB, source, start + 3)
    require(guard.get('rangeFailureBodyRawHex'),
            '33D28BCEE8900A8404CCCC', source, start + 3)
    if count['signedI32'] > count['remainingAfterCount']:
        assessment.update({
            'status': 'rejected-by-registered-list-count-bound',
            'listFormatterMethodSpecIndices': list_formatter.get('methodSpecIndices'),
            'listFormatterInstantiationIndex': formatter_inst.get('index'),
            'rangeFailureBranchRva': guard.get('rangeFailureBranchRva'),
            'rangeFailureTargetRva': guard.get('rangeFailureTargetRva'),
            'boundary': 'The shifted path reads a signed count greater than the bytes remaining after that count; the matching registered List<GameplayTag> body takes its bounded range-failure path before element iteration.',
        })
    else:
        assessment.update({
            'status': 'not-rejected-by-registered-list-count-bound',
            'boundary': 'The shifted path passes this bounded count comparison; more reader evidence is required.',
        })
    return assessment


def skilldata_nested_branch_static_alignment(branch_replay, nested_readers,
                                              gameplay_tag_list, *,
                                              list_formatter=None, source):
    """Require positive raw nested replays to match exact static reader schemas."""
    if not isinstance(branch_replay, dict) or not isinstance(nested_readers, dict):
        raise ContextError(source, 0, 'branch replay and static nested-reader evidence',
                           [type(branch_replay).__name__, type(nested_readers).__name__])
    if branch_replay.get('wholeSkillDataClassification') != 'ambiguous':
        raise ContextError(source, 0, 'whole SkillData sample remains ambiguous',
                           branch_replay.get('wholeSkillDataClassification'))
    if branch_replay.get('wholeSkillDataExactClosedRecords') != 0:
        raise ContextError(source, 0, 'no whole SkillData record credited as closed',
                           branch_replay.get('wholeSkillDataExactClosedRecords'))
    shifted_assessment = skilldata_shifted_candidate_reader_assessment(
        branch_replay, gameplay_tag_list, list_formatter, source=source)
    field_name = branch_replay.get('positiveFieldName')
    replay = branch_replay.get('nestedReaderReplay')
    records = replay.get('elementRecords') if isinstance(replay, dict) else None
    if not isinstance(records, list) or not records:
        raise ContextError(source, 0, 'at least one raw nested element replay', records)
    if field_name == 'tagDuringAttach.predefinedTag':
        wrapper_members = gameplay_tag_list.get('memberCount')
        require(wrapper_members, 1, source)
        header = gameplay_tag_list.get('headerEvidence')
        if not isinstance(header, dict):
            raise ContextError(source, 0, 'static GameplayTagList header evidence', header)
        require(header.get('acceptedNonNullHeaderByte'), 1, source)
        require(replay.get('wrapperMemberCount'), wrapper_members, source)
        require(replay.get('elementCount'), len(records), source)
        require(replay.get('reader'), 'read_skill_gameplay_tag_list_field', source)
        element_schema = nested_readers.get('gameplayTagElement')
        if not isinstance(element_schema, dict):
            raise ContextError(source, 0, 'registered GameplayTag element reader schema',
                               element_schema)
        native_element_count = element_schema.get('memberCountCheck', {}).get(
            'acceptedMemberCount')
        require(native_element_count, 1, source)
        require(element_schema.get('tagIdField', {}).get('fieldType', {}).get('wireType'),
                'System.Int32', source)
        require(element_schema.get('readerCall', {}).get('targetRva'), 0x2CA86B0, source)
        cursor_advancement = element_schema.get('cursorAdvancement')
        if not isinstance(cursor_advancement, dict):
            raise ContextError(source, 0, 'bounded int32/member-count cursor helper evidence',
                               cursor_advancement)
        native_record_width = cursor_advancement.get('validNormalPathByteWidth')
        require(native_record_width, 5, source)
        native_reader_method = element_schema.get('readerMethodIdentity', {})
        require(native_reader_method.get('methodIndex'), 104467, source)
        native_ranges = []
        for ordinal, row in enumerate(records):
            require(row.get('memberCount'), native_element_count, source, ordinal)
            span = row.get('recordRange')
            actual_width = span.get('end') - span.get('start') if isinstance(span, dict) else None
            require(actual_width, native_record_width, source, ordinal)
            native_ranges.append({
                'recordRange': span,
                'staticReaderEnd': span['start'] + native_record_width,
                'cursorByteWidth': native_record_width,
                'classification': 'exact-under-registered-reader-path',
            })
        raw_ids = []
        for ordinal, row in enumerate(records):
            raw_id = row.get('tagId')
            if type(raw_id) is not int or not 0 <= raw_id <= 0xFFFFFFFF:
                raise ContextError(source, ordinal,
                                   'GameplayTag raw id as an unsigned 32-bit bit pattern', raw_id)
            signed_id = raw_id if raw_id < 0x80000000 else raw_id - 0x100000000
            raw_ids.append({'rawU32': raw_id, 'rawHex': f'0x{raw_id:08X}',
                            'signedI32': signed_id})
        alignment = {
            'readerField': field_name,
            'rawWrapperMemberCount': replay['wrapperMemberCount'],
            'staticWrapperMemberCount': wrapper_members,
            'rawElementCount': replay['elementCount'],
            'staticSchema': gameplay_tag_list['typeName'],
            'rawElementMemberCounts': [row.get('memberCount') for row in records],
            'staticElementMemberCount': native_element_count,
            'nativeElementIdWireType': 'System.Int32',
            'staticReaderCursorDerivation': cursor_advancement['derivation'],
            'conditionalExactNativeElementRanges': native_ranges,
            'rawU32AndSignedI32Views': raw_ids,
        }
    elif field_name == 'toggleBuffs':
        schema = nested_readers.get('toggleBuffData')
        if not isinstance(schema, dict):
            raise ContextError(source, 0, 'exact ToggleBuffData reader schema', schema)
        member_count = schema.get('memberCountCompare', {}).get('memberCount')
        require(member_count, 2, source)
        field_order = [row.get('fieldName') for row in schema.get('members', [])]
        require(replay.get('parserFieldOrder'), field_order, source)
        require(replay.get('reader'), 'read_skill_toggle_buff_data', source)
        for ordinal, row in enumerate(records):
            require(row.get('memberCount'), member_count, source, ordinal)
        alignment = {
            'readerField': field_name,
            'rawRecordMemberCounts': [row.get('memberCount') for row in records],
            'staticMemberCount': member_count,
            'rawAndStaticFieldOrder': field_order,
        }
    elif field_name == 'uiRangeHints':
        schema = nested_readers.get('uiRangeHintData')
        shape_schema = nested_readers.get('skillHintShapeData')
        if not isinstance(schema, dict) or not isinstance(shape_schema, dict):
            raise ContextError(source, 0, 'exact UIRangeHintData and nested shape schemas',
                               [schema, shape_schema])
        member_count = schema.get('memberCountCompare', {}).get('memberCount')
        shape_count = shape_schema.get('memberCountCompare', {}).get('memberCount')
        require(member_count, 3, source)
        require(shape_count, 21, source)
        field_order = [row.get('fieldName') for row in schema.get('members', [])]
        shape_order = [row.get('fieldName') for row in shape_schema.get('serializedOrder', [])]
        require(replay.get('parserFieldOrder'), field_order, source)
        require(replay.get('nestedShapeParserFieldOrder'), shape_order, source)
        require(replay.get('reader'), 'read_skill_ui_range_hint_data', source)
        for ordinal, row in enumerate(records):
            require(row.get('memberCount'), member_count, source, ordinal)
            require(row.get('shapeData', {}).get('memberCount'), shape_count, source, ordinal)
        alignment = {
            'readerField': field_name,
            'rawRecordMemberCounts': [row.get('memberCount') for row in records],
            'staticMemberCount': member_count,
            'rawAndStaticFieldOrder': field_order,
            'nestedShapeMemberCounts': [row.get('shapeData', {}).get('memberCount')
                                        for row in records],
            'nestedShapeStaticMemberCount': shape_count,
            'rawAndStaticShapeFieldOrder': shape_order,
        }
    else:
        raise ContextError(source, 0, 'recognized positive SkillData nested reader field', field_name)
    return {
        'status': 'positive-raw-sample-matches-static-nested-reader-schema',
        'alignment': alignment,
        'shiftedCandidateAssessment': shifted_assessment,
        'wholeSkillDataClassification': 'ambiguous',
        'exactClosedWholeSkillDataRecords': 0,
        'boundary': ('For GameplayTag, the exact five-byte nested element endpoint follows from the registered reader plus its bounded one-byte/four-byte cursor helpers, and the source parser reaches the same end. Other nested endpoints are parser-to-schema cross-checks. All are conditional on the registered terminal path; none proves runtime provider selection or a live cursor.'),
    }


def skilldata_terminal_tail_layout(collision, sample_witness, tail_reads,
                                   tag_list_wrapper, *, source):
    """Compare exact terminal reader/type evidence to both current VFS shapes."""
    expected_reads = [
        (43, 'switchToCenterBeforeCast', 'bool', 0xA5, 0x37DE8C5, 0x2CA88C0, 0x37DE8E0),
        (44, 'tagDuringAttach', 'Beyond.Gameplay.Core.GameplayTagList',
         0xB8, 0x37DE8F3, 0x2DA5C90, 0x37DE90E),
        (45, 'toggleBuffs',
         'System.Collections.Generic.List`1<Beyond.Gameplay.Core.ToggleBuffData>',
         0xD8, 0x37DE92E, 0x381F8F0, 0x37DE949),
        (46, 'uiRangeHints',
         'System.Collections.Generic.List`1<Beyond.Gameplay.Core.UIRangeHintData>',
         0xC8, 0x37DE969, 0x381F8F0, 0x37DE984),
        (47, 'useAIExclusiveFrame', 'bool', 0x58, 0x37DE99D, 0x2CA88C0, 0x37DE9C2),
    ]
    if not isinstance(tail_reads, list) or len(tail_reads) != len(expected_reads):
        raise ContextError(source, 0, 'five exact terminal SkillData reader operations',
                           type(tail_reads).__name__ if not isinstance(tail_reads, list)
                           else len(tail_reads))
    actual_reads = []
    for row in tail_reads:
        if not isinstance(row, dict) or not isinstance(row.get('objectField'), dict):
            raise ContextError(source, 0, 'terminal SkillData reader rows include object fields',
                               row)
        actual_reads.append((
            row.get('serializedOrderIndex'), row.get('fieldName'), row.get('wireType'),
            row['objectField'].get('fieldOffset'), row.get('callInstructionRva'),
            row.get('readerTargetRva'), row.get('storeInstructionRva'),
        ))
    if actual_reads != expected_reads:
        raise ContextError(source, 0,
                           'terminal SkillData type/order/call/store rows match exact expectations',
                           actual_reads)

    if not isinstance(sample_witness, dict):
        raise ContextError(source, 0, 'authenticated current raw terminal byte witness',
                           type(sample_witness).__name__)
    for key in ('inputSetSha256', 'logicalFileIdentity', 'logicalSha256', 'hardLimit'):
        if sample_witness.get(key) != collision.get(key):
            raise ContextError(source, 0, f'terminal raw witness {key} equals corpus collision',
                               [sample_witness.get(key), collision.get(key)])
    if sample_witness.get('candidateRange') != collision['candidates'][0].get('candidateRange'):
        raise ContextError(source, 0, 'raw witness candidate range equals first corpus hypothesis',
                           sample_witness.get('candidateRange'))
    header = sample_witness.get('nestedMemberCountByte')
    if not isinstance(header, dict) or header.get('value') != 1:
        raise ContextError(source, 0, 'first candidate raw wrapper header is one',
                           header)

    if not isinstance(tag_list_wrapper, dict):
        raise ContextError(source, 0, 'exact GameplayTagList wrapper layout evidence',
                           type(tag_list_wrapper).__name__)
    expected_wrapper_type = 'Beyond.Gameplay.Core.GameplayTagList'
    if (tag_list_wrapper.get('typeName') != expected_wrapper_type or
            tag_list_wrapper.get('memberCount') != 1):
        raise ContextError(source, 0,
                           'GameplayTagList is the one-member SkillData tail wrapper',
                           [tag_list_wrapper.get('typeName'), tag_list_wrapper.get('memberCount')])
    member = tag_list_wrapper.get('member')
    expected_member_type = (
        'System.Collections.Generic.List`1<Beyond.Gameplay.Core.GameplayTag>')
    if (not isinstance(member, dict) or member.get('name') != 'predefinedTag' or
            member.get('wireType') != expected_member_type):
        raise ContextError(source, 0,
                           'GameplayTagList member is predefinedTag: List<GameplayTag>',
                           member)
    reader_identity = tag_list_wrapper.get('readerMethodIdentity')
    if (not isinstance(reader_identity, dict) or
            reader_identity.get('pointerVa') is None or
            reader_identity.get('name') != 'Deserialize' or
            reader_identity.get('declaringType') !=
            'Beyond.MemoryPack.Beyond_Gameplay_Core_GameplayTagListForMemoryPack'):
        raise ContextError(source, 0,
                           'wrapper reader method is the exact GameplayTagList Deserialize identity',
                           reader_identity)
    nested_type = tag_list_wrapper.get('nestedReadType')
    if nested_type != expected_member_type:
        raise ContextError(source, 0,
                           'wrapper reader MethodSpec reads its exact List<GameplayTag> member',
                           nested_type)
    header_evidence = tag_list_wrapper.get('headerEvidence')
    if (not isinstance(header_evidence, dict) or
            header_evidence.get('headerByteWidth') != 1 or
            header_evidence.get('acceptedNonNullHeaderByte') != 1 or
            header_evidence.get('nullHeaderByte') != 0xFF):
        raise ContextError(source, 0,
                           'wrapper reader consumes one header byte and accepts member count one',
                           header_evidence)

    candidates = collision.get('candidates')
    if not isinstance(candidates, list) or len(candidates) != 2:
        raise ContextError(source, 0, 'two terminal candidates remain available for comparison',
                           type(candidates).__name__ if not isinstance(candidates, list)
                           else len(candidates))
    first, shifted = candidates
    first_members = first.get('terminalMembers')
    shifted_members = shifted.get('terminalMembers')
    if not isinstance(first_members, list) or len(first_members) != 5:
        raise ContextError(source, 0, 'first terminal candidate has five member rows',
                           first_members)
    if not isinstance(shifted_members, list) or len(shifted_members) != 5:
        raise ContextError(source, 0, 'shifted terminal candidate has five member rows',
                           shifted_members)
    if (first.get('encoding') != 'one-member-wrapper' or
            first_members[1].get('wrapperRange') is None):
        raise ContextError(source, first.get('start', 0),
                           'first candidate carries the one-member GameplayTagList wrapper',
                           first.get('encoding'))
    if shifted.get('encoding') != 'counted' or shifted_members[1].get('wrapperRange') is not None:
        raise ContextError(source, shifted.get('start', 0),
                           'shifted candidate omits the required GameplayTagList wrapper',
                           shifted.get('encoding'))
    return {
        'tailReads': tail_reads,
        'nestedWrapperMemberCount': tag_list_wrapper.get('memberCount'),
        'gameplayTagListWrapper': tag_list_wrapper,
        'rawSampleByteWitness': sample_witness,
        'candidateComparison': [
            {
                'candidateRange': first.get('candidateRange'),
                'status': 'static-type-and-reader-order match, conditional on registered reader paths being selected',
                'fieldSequence': [name for _, name, *_ in expected_reads],
                'rawWrapperHeaderByte': header,
            },
            {
                'candidateRange': shifted.get('candidateRange'),
                'status': 'statically incompatible with the one-member GameplayTagList wrapper if its registered reader path is selected',
                'conflict': 'The shifted candidate treats the raw wrapper header byte 1 as switchToCenterBeforeCast and omits the nested wrapper header.',
            },
        ],
        'wholeFileBoundary': 'The terminal field group is independently matched to the current source bytes, but the bytes between the proven [0,10) prefix and this tail remain opaque. Do not classify the whole SkillData file as closed.',
        'runtimeProviderSelection': 'unobserved',
        'runtimeCursor': 'unobserved',
        'classification': 'static-terminal-shape-match-with-conditional-shifted-candidate-conflict',
        'exactClosedRecords': 0,
    }


def skilldata_cursor_hook_call_sites(pe, *, source):
    """Verify exact SkillData E8 edges and the post-CALL return RVAs.

    The native observer classifies the return address from _ReturnAddress(),
    not the start of the E8 instruction.
    """
    sites = []
    for name, instruction_rva in (
            ('firstTerminalByte', 0x37DE8C5),
            ('finalTerminalByte', 0x37DE99D)):
        raw = pe.bytes_at_va(pe.image_base + instruction_rva, 5)
        require(raw[:1], b'\xE8', source, instruction_rva)
        target = relative_branch_target(
            raw, pe.image_base + instruction_rva, source=source)
        require(target, pe.image_base + 0x2CA88C0, source, instruction_rva)
        return_rva = instruction_rva + len(raw)
        sites.append({
            'name': name,
            'callInstructionRva': instruction_rva,
            'instructionByteLength': len(raw),
            'rawHex': raw.hex().upper(),
            'targetRva': target - pe.image_base,
            'returnAddressRva': return_rva,
            'classificationBasis': '_ReturnAddress() after the five-byte E8 rel32 call',
        })
    return {
        'sites': sites,
        'level': 'exact selected-build direct helper call and post-CALL return address',
        'boundary': 'These checks validate the observer allow-list coordinates against the selected SkillData body. They do not prove that either call executes for a current VFS file or provide its runtime cursor.',
    }


def skilldata_static_reader_order(pe, md, modules, image_owners, table, reg, specs_raw,
                                  corpus, representative_sample_raw, wrapper_evidence,
                                  *, source):
    """Pin the first SkillData reader field and nested ActionGroupData order.

    Static AOT method, MethodSpec, field-offset and bounded-code joins are
    exact-build evidence. They do not establish which formatter/provider ran
    for a VFS file, so the empty-list end stays conditional.
    """
    selected_methods = module_methods(pe, md, modules, image_owners, [
        (102566, 'Beyond.MemoryPack.Beyond_Gameplay_Core_SkillDataForMemoryPack', 'Deserialize', 0x37DE060),
        (102567, 'Beyond.MemoryPack.Beyond_Gameplay_Core_SkillDataForMemoryPack+Beyond_Gameplay_Core_SkillDataForMemoryPackFormatter', 'Deserialize', 0x37DDF70),
        (104262, 'Beyond.MemoryPack.Beyond_Gameplay_Core_ActionGroupDataForMemoryPack', 'Deserialize', 0x3E3FFE0),
        (104263, 'Beyond.MemoryPack.Beyond_Gameplay_Core_ActionGroupDataForMemoryPack+Beyond_Gameplay_Core_ActionGroupDataForMemoryPackFormatter', 'Deserialize', 0x3E3FF80),
    ], source=source, expected_image='MemoryPack.Beyond.dll')
    code_windows = []
    for rva, length, expected in (
        (0x37DE060, 0x5B, '0926899BA44C601CEBAC2B4E70580B397CDDAB4FC60060C1E8DC0EF99A2555FB'),
        (0x37DE0BB, 0x90A, 'FEA359985EBF5DF75CC58D871469481F0F692B1768D84724FF5941D47CAD8132'),
        (0x3E3FFE0, 0x13F, 'D2C4A8B7F40CDB99154F7EE9EFA9FB85CD8F2F086932F03C1BC2FF8568E1AB4E'),
    ):
        raw = pe.bytes_at_va(pe.image_base + rva, length)
        digest = hashlib.sha256(raw).hexdigest().upper()
        require(digest, expected, source, rva)
        code_windows.append({'rva': rva, 'byteLength': length, 'sha256': digest})
    instruction_windows = []
    for rva, raw_hex, role in (
        (0x37DE0CF, '4080FD30', 'SkillData member-count comparison against 48'),
        (0x37DE101, '488981C0000000', 'store first SkillData result at object offset +0xC0'),
        (0x3E40045, '4080FD02', 'ActionGroupData member-count comparison against 2'),
        (0x3E40077, '48894118', 'store passiveEventActions result at object offset +0x18'),
        (0x3E400A4, '48894110', 'store timelineActions result at object offset +0x10'),
    ):
        raw = pe.bytes_at_va(pe.image_base + rva, len(bytes.fromhex(raw_hex)))
        require(raw, bytes.fromhex(raw_hex), source, rva)
        instruction_windows.append({'rva': rva, 'rawHex': raw.hex().upper(), 'role': role})
    formatter_thunks = []
    for rva, target in ((0x37DDFAC, 0x37DE060), (0x3E3FFBC, 0x3E3FFE0)):
        raw = pe.bytes_at_va(pe.image_base + rva, 5)
        actual = relative_branch_target(raw, pe.image_base + rva, source=source) - pe.image_base
        require(actual, target, source, rva)
        formatter_thunks.append({'rva': rva, 'rawHex': raw.hex().upper(),
                                 'targetRva': target, 'kind': 'conditional tail jump after formatter initialization'})

    def type_index(full_name, expected_image):
        matches = [index for index, item in enumerate(md.types) if md.type_full_name(item) == full_name]
        if len(matches) != 1:
            raise ContextError(source, 0, f'one metadata type definition named {full_name}', matches)
        index = matches[0]
        image_name = md.string(md.images[image_owners[index]].name_index)
        require(image_name, expected_image, source, index)
        return index

    def field_layout(type_def_index, field_names):
        require(reg['fieldOffsetsCount'], len(md.types), source, int(reg['fieldOffsets'], 16))
        definition = md.types[type_def_index]
        table_base = int(reg['fieldOffsets'], 16)
        vector = pe.u64_at_va(table_base + type_def_index * 8)
        require(vector != 0, True, source, table_base + type_def_index * 8)
        result = {}
        for local_index in range(definition.field_count):
            field_index = definition.field_start + local_index
            field = md.fields[field_index]
            name = md.string(field.name_index)
            if name not in field_names:
                continue
            raw_offset = pe.bytes_at_va(vector + local_index * 4, 4)
            offset = struct.unpack('<i', raw_offset)[0]
            result[name] = {'metadataFieldIndex': field_index, 'fieldOffset': offset,
                            'metadataTypeIndex': field.type_index}
        for name in field_names:
            if name not in result:
                raise ContextError(source, type_def_index,
                                   f'field {name!r} in type definition {type_def_index}', 'missing')
        return result

    def field_wire_identity(field_name, layout):
        field = md.fields[layout['metadataFieldIndex']]
        type_index = field.type_index
        if type(type_index) is not int or not 0 <= type_index < reg['typesCount']:
            raise ContextError(source, layout['metadataFieldIndex'],
                               'field type index inside registered IL2CPP type table', type_index)
        type_slot = int(reg['types'], 16) + type_index * 8
        type_pointer = pe.u64_at_va(type_slot)
        if type_pointer == 0:
            raise ContextError(source, type_slot, 'non-null field type pointer', type_pointer)
        raw = pe.bytes_at_va(type_pointer, 16)
        kind = raw[10]
        identity = {
            'metadataTypeIndex': type_index,
            'typePointerVa': type_pointer,
            'typeRawHex': raw.hex().upper(),
            'typeKind': kind,
        }
        primitive_names = {
            0x02: 'bool', 0x03: 'System.Char',
            0x04: 'System.SByte', 0x05: 'System.Byte',
            0x06: 'System.Int16', 0x07: 'System.UInt16',
            0x08: 'System.Int32', 0x09: 'System.UInt32',
            0x0A: 'System.Int64', 0x0B: 'System.UInt64',
            0x0C: 'System.Single', 0x0D: 'System.Double',
            0x0E: 'System.String',
        }
        if kind in primitive_names:
            identity['wireType'] = primitive_names[kind]
        elif kind in (0x11, 0x12):
            definition = struct.unpack_from('<Q', raw)[0]
            if definition >= len(md.types):
                raise ContextError(source, type_pointer,
                                   'bounded direct field type definition', definition)
            identity.update({
                'typeDefinitionIndex': definition,
                'wireType': md.type_full_name(md.types[definition]),
            })
        elif kind == 0x15:
            carrier_pointer = struct.unpack_from('<Q', raw)[0]
            carrier_raw = pe.bytes_at_va(carrier_pointer, 32)
            base_pointer = struct.unpack_from('<Q', carrier_raw)[0]
            base_raw = pe.bytes_at_va(base_pointer, 16)
            carrier = generic_type_carrier(
                raw, carrier_raw, base_raw, type_pointer=type_pointer,
                type_count=len(md.types), source=source)
            inst = table.resolve_pointer(carrier['classInstantiationPointerVa'])
            if len(inst.arguments) != 1:
                raise ContextError(source, inst.record_va,
                                   'one concrete generic list element type', len(inst.arguments))
            element = inst.arguments[0]
            element_raw = bytes.fromhex(element.raw_type_record_hex)
            element_kind = element_raw[10]
            element_definition = struct.unpack_from('<Q', element_raw)[0]
            if element_kind not in (0x11, 0x12) or element_definition >= len(md.types):
                raise ContextError(source, element.type_pointer_va,
                                   'bounded direct class/value list element type',
                                   [element_kind, element_definition])
            base_name = md.type_full_name(md.types[carrier['baseDefinitionIndex']])
            element_name = md.type_full_name(md.types[element_definition])
            identity.update({
                'typeDefinitionIndex': carrier['baseDefinitionIndex'],
                'typeName': base_name,
                'wireType': f'{base_name}<{element_name}>',
                'classCarrier': carrier,
                'genericInstantiation': inst.as_dict(),
                'elementTypeDefinitionIndex': element_definition,
                'elementTypeName': element_name,
                'elementRawTypeRecordHex': element.raw_type_record_hex,
            })
        else:
            raise ContextError(source, type_pointer,
                               'boolean, direct class/value or generic-list field type',
                               hex(kind))
        return identity

    skill_type = type_index('Beyond.Gameplay.Core.SkillData', 'Gameplay.Beyond.dll')
    action_group_type = type_index('Beyond.Gameplay.Core.ActionGroupData', 'Gameplay.Beyond.dll')
    skill_fields = field_layout(skill_type, {
        'actionGroupData', 'switchToCenterBeforeCast', 'tagDuringAttach',
        'toggleBuffs', 'uiRangeHints', 'useAIExclusiveFrame',
    })
    action_fields = field_layout(action_group_type, {'passiveEventActions', 'timelineActions'})
    require(skill_fields['actionGroupData']['fieldOffset'], 0xC0, source, skill_fields['actionGroupData']['metadataFieldIndex'])
    require(action_fields['passiveEventActions']['fieldOffset'], 0x18, source, action_fields['passiveEventActions']['metadataFieldIndex'])
    require(action_fields['timelineActions']['fieldOffset'], 0x10, source, action_fields['timelineActions']['metadataFieldIndex'])

    def call_method_spec(load_rva, call_rva, expected_method_index, expected_method_name, expected_target_rva):
        instruction = pe.bytes_at_va(pe.image_base + load_rva, 7)
        cell = rip_qword_load_target(instruction, pe.image_base + load_rva, source=source)
        raw_usage = pe.bytes_at_va(cell, 8)
        context = usage_method_spec(
            raw_usage, specs_raw, len(md.methods), table.count, source=source,
            usage_offset=cell, records_offset=int(reg['methodSpecs'], 16))
        require(context['definition'], expected_method_index, source, cell)
        method = md.methods[context['definition']]
        owner = md.types[method.declaring_type]
        require((md.type_full_name(owner), md.string(method.name_index)),
                ('MemoryPack.MemoryPackReader', expected_method_name), source, cell)
        target = relative_branch_target(
            pe.bytes_at_va(pe.image_base + call_rva, 5), pe.image_base + call_rva, source=source)
        require(target, pe.image_base + expected_target_rva, source, call_rva)
        context['methodIdentity'] = {
            'methodIndex': context['definition'], 'token': method.token,
            'declaringType': md.type_full_name(owner), 'name': md.string(method.name_index),
        }
        context['loadRva'] = load_rva
        context['callRva'] = call_rva
        context['targetRva'] = expected_target_rva
        inst = table.resolve(context['methodInstantiationIndex'])
        require(len(inst.arguments), 1, source, inst.record_va)
        type_arg = inst.arguments[0]
        type_raw = bytes.fromhex(type_arg.raw_type_record_hex)
        type_kind = type_raw[10]
        type_index_or_pointer = struct.unpack_from('<Q', type_raw)[0]
        if type_kind in (0x11, 0x12):
            require(type_index_or_pointer < len(md.types), True, source, type_arg.type_pointer_va)
            context['genericType'] = {
                'typeDefinitionIndex': type_index_or_pointer,
                'typeName': md.type_full_name(md.types[type_index_or_pointer]),
                'rawTypeRecordHex': type_arg.raw_type_record_hex,
            }
        elif type_kind == 0x15:
            carrier_raw = pe.bytes_at_va(type_index_or_pointer, 32)
            base_pointer = struct.unpack_from('<Q', carrier_raw)[0]
            base_raw = pe.bytes_at_va(base_pointer, 16)
            carrier = generic_type_carrier(
                type_raw, carrier_raw, base_raw, type_pointer=type_arg.type_pointer_va,
                type_count=len(md.types), source=source)
            base_name = md.type_full_name(md.types[carrier['baseDefinitionIndex']])
            require(base_name, 'System.Collections.Generic.List`1', source, base_pointer)
            element_inst = table.resolve_pointer(carrier['classInstantiationPointerVa'])
            require(len(element_inst.arguments), 1, source, element_inst.record_va)
            element_arg = element_inst.arguments[0]
            element_raw = bytes.fromhex(element_arg.raw_type_record_hex)
            element_kind = element_raw[10]
            element_index = struct.unpack_from('<Q', element_raw)[0]
            require(element_kind in (0x11, 0x12), True, source, element_arg.type_pointer_va)
            require(element_index < len(md.types), True, source, element_arg.type_pointer_va)
            context['genericType'] = {
                'typeDefinitionIndex': carrier['baseDefinitionIndex'],
                'typeName': base_name,
                'elementTypeDefinitionIndex': element_index,
                'elementTypeName': md.type_full_name(md.types[element_index]),
                'rawTypeRecordHex': type_arg.raw_type_record_hex,
                'elementRawTypeRecordHex': element_arg.raw_type_record_hex,
            }
        else:
            raise ContextError(source, type_arg.type_pointer_va,
                               'direct class or List<T> generic type argument', hex(type_kind))
        return context

    action_group_call = call_method_spec(0x37DE0D9, 0x37DE0E6, 428464, 'ReadValue', 0x2DA5C90)
    require(action_group_call['index'], 619840, source, action_group_call['usageVa'])
    require(action_group_call['genericType']['typeName'], 'Beyond.Gameplay.Core.ActionGroupData',
            source, action_group_call['usageVa'])
    require(action_group_call['genericType']['typeDefinitionIndex'], action_group_type,
            source, action_group_call['usageVa'])
    list_calls = [
        call_method_spec(0x3E4004F, 0x3E4005C, 428462, 'ReadPackable', 0x381F8F0),
        call_method_spec(0x3E40084, 0x3E40091, 428462, 'ReadPackable', 0x381F8F0),
    ]
    require([row['index'] for row in list_calls], [610662, 610915], source)
    for row in list_calls:
        require(row['genericType']['typeName'], 'System.Collections.Generic.List`1', source, row['usageVa'])
    require(list_calls[0]['genericType']['elementTypeName'],
            'Beyond.Gameplay.Core.AbilityActionMap', source)
    require(list_calls[1]['genericType']['elementTypeName'],
            'Beyond.Gameplay.Core.TimelineAction+TimelineActionData', source)
    require(action_group_call['genericType']['typeName'], 'Beyond.Gameplay.Core.ActionGroupData', source)

    # Continue the second ActionGroupData list through the concrete timeline
    # element reader. These are exact static reader/type joins; formatter and
    # provider selection for any current VFS file remain unobserved.
    timeline_action_type = type_index(
        'Beyond.Gameplay.Core.TimelineAction+TimelineActionData',
        'Gameplay.Beyond.dll')
    require(timeline_action_type, 9199, source, timeline_action_type)
    timeline_action_fields = field_layout(timeline_action_type, {
        '_startFrame', '_endFrame', '_sequenceActionData', 'forceSyncAnimData',
    })
    force_sync_type = type_index(
        'Beyond.Gameplay.Core.TimelineAction+ForceSyncAnimData',
        'Gameplay.Beyond.dll')
    require(force_sync_type, 9198, source, force_sync_type)
    force_sync_fields = field_layout(force_sync_type, {
        'forceSync', 'montageName', 'targetFrame', 'playbackSpeed',
    })
    timeline_field_expectations = (
        ('_endFrame', 0x14, 'System.Int32'),
        ('_sequenceActionData', 0x18,
         'Beyond.Gameplay.Core.SequenceActionData'),
        ('_startFrame', 0x10, 'System.Int32'),
        ('forceSyncAnimData', 0x20,
         'Beyond.Gameplay.Core.TimelineAction+ForceSyncAnimData'),
    )
    timeline_field_rows = {}
    for field_name, field_offset, wire_type in timeline_field_expectations:
        field = timeline_action_fields[field_name]
        require(field['fieldOffset'], field_offset, source,
                field['metadataFieldIndex'])
        identity = field_wire_identity(field_name, field)
        require(identity['wireType'], wire_type, source,
                field['metadataFieldIndex'])
        timeline_field_rows[field_name] = {
            'typeDefinitionIndex': timeline_action_type,
            **field,
            'fieldType': identity,
        }
    force_sync_field_expectations = (
        ('forceSync', 0x10, 'bool'),
        ('montageName', 0x18, 'System.String'),
        ('playbackSpeed', 0x24, 'System.Single'),
        ('targetFrame', 0x20, 'System.Int32'),
    )
    force_sync_field_rows = {}
    for field_name, field_offset, wire_type in force_sync_field_expectations:
        field = force_sync_fields[field_name]
        require(field['fieldOffset'], field_offset, source,
                field['metadataFieldIndex'])
        identity = field_wire_identity(field_name, field)
        require(identity['wireType'], wire_type, source,
                field['metadataFieldIndex'])
        force_sync_field_rows[field_name] = {
            'typeDefinitionIndex': force_sync_type,
            **field,
            'fieldType': identity,
        }

    timeline_reader_methods = module_methods(pe, md, modules, image_owners, [
        (104653,
         'Beyond.MemoryPack.Beyond_Gameplay_Core_TimelineAction_TimelineActionDataForMemoryPack',
         'Deserialize', 0x32CCF70),
        (104654,
         'Beyond.MemoryPack.Beyond_Gameplay_Core_TimelineAction_TimelineActionDataForMemoryPack+'
         'Beyond_Gameplay_Core_TimelineAction_TimelineActionDataForMemoryPackFormatter',
         'Deserialize', 0x32CE8C0),
        (107909,
         'Beyond.MemoryPack.Beyond_Gameplay_Core_TimelineAction_ForceSyncAnimDataForMemoryPack',
         'Deserialize', 0x32CE4B0),
        (107910,
         'Beyond.MemoryPack.Beyond_Gameplay_Core_TimelineAction_ForceSyncAnimDataForMemoryPack+'
         'Beyond_Gameplay_Core_TimelineAction_ForceSyncAnimDataForMemoryPackFormatter',
         'Deserialize', 0x32CE860),
    ], source=source, expected_image='MemoryPack.Beyond.dll')
    timeline_reader_code_windows = []
    for start_rva, end_rva, expected_sha, role in (
        (0x32CCF70, 0x32CD277,
         'CB497F6362D9DA9396D6533F6CC037536FC9499D67848F1E8BBBAC8AA2F03688',
         'TimelineActionData Deserialize: selected source-read path and bounded failure/return fragments'),
        (0x32CE4B0, 0x32CE75C,
         '1FB17BEDE173176E0BC082E7C315267B6FC6F3CE76796DB90A627E9B0E9D7767',
         'ForceSyncAnimData Deserialize: selected source-read path and bounded failure/return fragments'),
        (0x32CE860, 0x32CE8C0,
         '1F6F3F32B14A6DCBB87743E94C1DB14106B3AB3EE17D6C6EBB14F7DB0347A3EB',
         'ForceSyncAnimData formatter forwarding window'),
        (0x32CE8C0, 0x32CE920,
         'D0D022A7D27D843AD4BFFE86FEC8A5FA07037249273A8ECB5AEC0167FEF98F33',
         'TimelineActionData formatter forwarding window'),
    ):
        raw = pe.bytes_at_va(pe.image_base + start_rva, end_rva - start_rva)
        digest = hashlib.sha256(raw).hexdigest().upper()
        require(digest, expected_sha, source, start_rva)
        timeline_reader_code_windows.append({
            'startRva': start_rva,
            'endRva': end_rva,
            'byteLength': end_rva - start_rva,
            'sha256': digest,
            'role': role,
        })

    timeline_sequence_read = call_method_spec(
        0x32CD07F, 0x32CD089, 428464, 'ReadValue', 0x2DA5C90)
    require(timeline_sequence_read['index'], 619962, source,
            timeline_sequence_read['usageVa'])
    require(timeline_sequence_read['genericType']['typeDefinitionIndex'], 9202,
            source, timeline_sequence_read['usageVa'])
    require(timeline_sequence_read['genericType']['typeName'],
            'Beyond.Gameplay.Core.SequenceActionData', source,
            timeline_sequence_read['usageVa'])
    timeline_force_sync_read = call_method_spec(
        0x32CD16F, 0x32CD179, 428464, 'ReadValue', 0x2DA5C90)
    require(timeline_force_sync_read['index'], 620038, source,
            timeline_force_sync_read['usageVa'])
    require(timeline_force_sync_read['genericType']['typeDefinitionIndex'], 9198,
            source, timeline_force_sync_read['usageVa'])
    require(timeline_force_sync_read['genericType']['typeName'],
            'Beyond.Gameplay.Core.TimelineAction+ForceSyncAnimData', source,
            timeline_force_sync_read['usageVa'])

    def timeline_helper_call(call_rva, target_rva, role):
        raw = pe.bytes_at_va(pe.image_base + call_rva, 5)
        require(raw[:1], b'\xE8', source, call_rva)
        require(relative_branch_target(raw, pe.image_base + call_rva, source=source),
                pe.image_base + target_rva, source, call_rva)
        return {'callInstructionRva': call_rva,
                'callInstructionHex': raw.hex().upper(),
                'targetRva': target_rva,
                'role': role}

    timeline_reader_instructions = []
    for rva, expected_hex, role in (
        (0x32CD04E, '4080FE04', 'TimelineActionData accepts member-count header 4 on this path'),
        (0x32CD079, '894614', 'store endFrame result at object offset +0x14'),
        (0x32CD0BC, '49894018', 'store SequenceActionData result at object offset +0x18'),
        (0x32CD126, '448B30', 'load the startFrame DWORD from the current cursor'),
        (0x32CD142, '4883435004', 'advance the startFrame source cursor by four bytes'),
        (0x32CD147, '83434004', 'advance the consumed counter for startFrame by four'),
        (0x32CD14B, '83434404', 'advance the total counter for startFrame by four'),
        (0x32CD168, '44897010', 'store startFrame at object offset +0x10'),
        (0x32CD19B, '49894020', 'store ForceSyncAnimData result at object offset +0x20'),
        (0x32CE57E, '4080FE04', 'ForceSyncAnimData accepts member-count header 4 on this path'),
        (0x32CE5A9, '884610', 'store forceSync byte at object offset +0x10'),
        (0x32CE5D9, '49894018', 'store montageName result at object offset +0x18'),
        (0x32CE635, 'F30F1030', 'load playbackSpeed float32 from the current cursor'),
        (0x32CE652, '4883435004', 'advance playbackSpeed source cursor by four bytes'),
        (0x32CE67B, 'F30F117024', 'store playbackSpeed float32 at object offset +0x24'),
        (0x32CE69A, '8B28', 'load targetFrame int32 from the current cursor'),
        (0x32CE6B5, '4883435004', 'advance targetFrame source cursor by four bytes'),
        (0x32CE6D8, '896820', 'store targetFrame int32 at object offset +0x20'),
    ):
        raw = pe.bytes_at_va(pe.image_base + rva, len(bytes.fromhex(expected_hex)))
        require(raw, bytes.fromhex(expected_hex), source, rva)
        timeline_reader_instructions.append({
            'rva': rva, 'rawHex': raw.hex().upper(), 'role': role,
        })
    timeline_direct_calls = [
        timeline_helper_call(0x32CD05E, 0x2CA86B0,
                             'read endFrame int32'),
        timeline_helper_call(0x32CE58E, 0x2CA88C0,
                             'read forceSync boolean'),
        timeline_helper_call(0x32CE5B2, 0x2CA8700,
                             'read montageName string'),
    ]
    timeline_action_data_reader = {
        'elementTypeDefinitionIndex': timeline_action_type,
        'elementTypeName': md.type_full_name(md.types[timeline_action_type]),
        'listReaderMethodSpec': list_calls[1],
        'methods': timeline_reader_methods,
        'codeWindows': timeline_reader_code_windows,
        'serializedMembers': [
            {'serializedOrderIndex': 0, 'fieldName': '_endFrame',
             'objectField': timeline_field_rows['_endFrame'],
             'reader': timeline_direct_calls[0]},
            {'serializedOrderIndex': 1, 'fieldName': '_sequenceActionData',
             'objectField': timeline_field_rows['_sequenceActionData'],
             'readerMethodSpec': timeline_sequence_read},
            {'serializedOrderIndex': 2, 'fieldName': '_startFrame',
             'objectField': timeline_field_rows['_startFrame'],
             'reader': {'kind': 'inline-int32', 'byteWidth': 4,
                        'verifiedInstructions': [
                            row for row in timeline_reader_instructions
                            if row['rva'] in (0x32CD126, 0x32CD142,
                                             0x32CD147, 0x32CD14B)]}},
            {'serializedOrderIndex': 3, 'fieldName': 'forceSyncAnimData',
             'objectField': timeline_field_rows['forceSyncAnimData'],
             'readerMethodSpec': timeline_force_sync_read},
        ],
        'forceSyncAnimDataReader': {
            'typeDefinitionIndex': force_sync_type,
            'typeName': md.type_full_name(md.types[force_sync_type]),
            'serializedMembers': [
                {'serializedOrderIndex': 0, 'fieldName': 'forceSync',
                 'objectField': force_sync_field_rows['forceSync'],
                 'reader': timeline_direct_calls[1]},
                {'serializedOrderIndex': 1, 'fieldName': 'montageName',
                 'objectField': force_sync_field_rows['montageName'],
                 'reader': timeline_direct_calls[2]},
                {'serializedOrderIndex': 2, 'fieldName': 'playbackSpeed',
                 'objectField': force_sync_field_rows['playbackSpeed'],
                 'reader': {'kind': 'inline-float32', 'byteWidth': 4,
                            'verifiedInstructions': [
                                row for row in timeline_reader_instructions
                                if row['rva'] in (0x32CE635, 0x32CE652,
                                                 0x32CE67B)]}},
                {'serializedOrderIndex': 3, 'fieldName': 'targetFrame',
                 'objectField': force_sync_field_rows['targetFrame'],
                 'reader': {'kind': 'inline-int32', 'byteWidth': 4,
                            'verifiedInstructions': [
                                row for row in timeline_reader_instructions
                                if row['rva'] in (0x32CE69A, 0x32CE6B5,
                                                 0x32CE6D8)]}},
            ],
            'verifiedInstructionWindows': [
                row for row in timeline_reader_instructions
                if row['rva'] in (0x32CE57E, 0x32CE5A9, 0x32CE5D9)],
        },
        'verifiedInstructionWindows': timeline_reader_instructions,
        'sequenceActionDataReaderReference': {
            'reportKey': 'selectedBuffSequenceReadOrder',
            'methodIndex': 104346,
            'rootRva': 0x39C6AA0,
            'rootCodeWindowSha256': '6444AF67AF86E7809AF5A50AE6DEE922B699DCB1CA686DC81F4C3584AB817B90',
        },
        'level': 'exact current-build module/token, generic MethodSpec, TypeDef field-offset and selected source-read code joins',
        'runtimeProviderSelection': 'unobserved',
        'runtimeCursor': 'unobserved',
        'boundary': ('The exact static list element type is TimelineActionData. Its selected Deserialize normal path reads endFrame, '
                     'SequenceActionData, startFrame and ForceSyncAnimData in that order. ForceSyncAnimData reads forceSync, '
                     'montageName, playbackSpeed and targetFrame; the two trailing scalar members each advance four bytes. '
                     'This establishes a native reader order and widths for those scalar fields only. The list/formatter/provider '
                     'chosen for current VFS files, dynamic string extent, successful runtime cursor and enclosing record/EOF '
                     'remain unobserved; these static paths do not close a SkillData parent.'),
    }

    terminal_method_calls = {
        'tagDuringAttach': call_method_spec(
            0x37DE8E9, 0x37DE8F3, 428464, 'ReadValue', 0x2DA5C90),
        'toggleBuffs': call_method_spec(
            0x37DE921, 0x37DE92E, 428462, 'ReadPackable', 0x381F8F0),
        'uiRangeHints': call_method_spec(
            0x37DE95C, 0x37DE969, 428462, 'ReadPackable', 0x381F8F0),
    }
    require(terminal_method_calls['tagDuringAttach']['genericType']['typeName'],
            'Beyond.Gameplay.Core.GameplayTagList', source)
    for field_name, element_name in (
            ('toggleBuffs', 'Beyond.Gameplay.Core.ToggleBuffData'),
            ('uiRangeHints', 'Beyond.Gameplay.Core.UIRangeHintData')):
        generic = terminal_method_calls[field_name]['genericType']
        require(generic['typeName'], 'System.Collections.Generic.List`1',
                source, terminal_method_calls[field_name]['usageVa'])
        require(generic['elementTypeName'], element_name,
                source, terminal_method_calls[field_name]['usageVa'])

    cursor_hook_sites = skilldata_cursor_hook_call_sites(pe, source=source)
    observer_calls = (
        (0,0x37DE0E6,0x2DA5C90),(1,0x37DE11A,0x2CA86B0),(2,0x37DE145,0x2CA86B0),(3,0x37DE170,0x381F8F0),(4,0x37DE1AB,0x2DA5C90),(5,0x37DE1E6,0x381F8F0),(6,0x37DE21A,0x2CA88C0),(7,0x37DE241,0x2CA88C0),(8,0x37DE268,0x2CA88C0),(9,0x37DE28F,0x2CA88C0),(10,0x37DE2BD,0x2DA5C90),(11,0x37DE2F8,0x2DA5C90),(12,0x37DE32D,0x2CA86B0),(13,0x37DE351,0x2CA88C0),(14,0x37DE378,0x2CA8700),(15,0x37DE3AC,0x2CA8700),(16,0x37DE3E0,0x2CA88C0),(18,0x37DE461,0x2CA86B0),(19,0x37DE485,0x2CA86B0),(20,0x37DE4A9,0x2CA8BB0),(21,0x37DE4D9,0x2CA86B0),(22,0x37DE4FD,0x2CA8700),(23,0x37DE52B,0x2CA86B0),(24,0x37DE54F,0x2CA88C0),(25,0x37DE576,0x2CA88C0),(26,0x37DE59D,0x2CA86B0),(27,0x37DE5C1,0x2CA88C0),(28,0x37DE5E8,0x2CA88C0),(29,0x37DE616,0x2CA86B0),(30,0x37DE63A,0x2CA88C0),(31,0x37DE668,0x2CA86B0),(32,0x37DE68C,0x2CA88C0),(33,0x37DE6BA,0x2DA5C90),(34,0x37DE6EE,0x2CA8700),(35,0x37DE71C,0x2CA8700),(36,0x37DE751,0x2CA86B0),(37,0x37DE77C,0x2DA5C90),(38,0x37DE7B7,0x2DA5C90),(39,0x37DE7F2,0x381F8F0),(40,0x37DE827,0x2CA86B0),(41,0x37DE857,0x3D3C620),(42,0x37DE891,0x2DA5C90),(43,0x37DE8C5,0x2CA88C0),(44,0x37DE8F3,0x2DA5C90),(45,0x37DE92E,0x381F8F0),(46,0x37DE969,0x381F8F0),(47,0x37DE99D,0x2CA88C0),
    )
    skill_names = MEMORYPACK_FIELD_SCHEMAS['SkillData']
    observer_rows = []
    for field_index, call_rva, target_rva in observer_calls:
        raw = pe.bytes_at_va(pe.image_base + call_rva, 5)
        require(raw[:1], b'\xE8', source, call_rva)
        require(relative_branch_target(raw, pe.image_base + call_rva, source=source),
                pe.image_base + target_rva, source, call_rva)
        observer_rows.append({
            'fieldIndex': field_index, 'fieldName': skill_names[field_index],
            'callInstructionRva': call_rva, 'returnAddressRva': call_rva + 5,
            'targetRva': target_rva, 'rawHex': raw.hex().upper(),
        })
    action_observer_rows = []
    for child_index, call_rva in enumerate((0x3E4005C, 0x3E40091)):
        raw = pe.bytes_at_va(pe.image_base + call_rva, 5)
        require(raw[:1], b'\xE8', source, call_rva)
        require(relative_branch_target(raw, pe.image_base + call_rva, source=source),
                pe.image_base + 0x381F8F0, source, call_rva)
        action_observer_rows.append({
            'childIndex': child_index,
            'fieldName': ('passiveEventActions', 'timelineActions')[child_index],
            'callInstructionRva': call_rva, 'returnAddressRva': call_rva + 5,
            'targetRva': 0x381F8F0, 'rawHex': raw.hex().upper(),
        })
    runtime_cursor_observer = {
        'status': 'exact-static-callsite-vector',
        'fieldCallsites': observer_rows,
        'inlineField': {'fieldIndex': 17, 'fieldName': skill_names[17],
                        'status': 'no-direct-helper-callsite'},
        'actionGroupChildCallsites': action_observer_rows,
        'sourceLengths': [424, 533],
        'boundary': ('The 47 direct top-level read calls and both ActionGroup child-list calls are exact '
                     'current-build E8 targets inside hash-pinned reader windows. Field 17 is inline and '
                     'has no observer callsite. This authenticates the observer allow-list, not execution.'),
    }
    tail_field_expectations = [
        (43, 'switchToCenterBeforeCast', 'bool', 0xA5, 0x37DE8C5,
         0x2CA88C0, 0x37DE8E0, '8881A5000000', None),
        (44, 'tagDuringAttach', 'Beyond.Gameplay.Core.GameplayTagList', 0xB8,
         0x37DE8F3, 0x2DA5C90, 0x37DE90E, '488981B8000000',
         terminal_method_calls['tagDuringAttach']),
        (45, 'toggleBuffs',
         'System.Collections.Generic.List`1<Beyond.Gameplay.Core.ToggleBuffData>',
         0xD8, 0x37DE92E, 0x381F8F0, 0x37DE949, '488981D8000000',
         terminal_method_calls['toggleBuffs']),
        (46, 'uiRangeHints',
         'System.Collections.Generic.List`1<Beyond.Gameplay.Core.UIRangeHintData>',
         0xC8, 0x37DE969, 0x381F8F0, 0x37DE984, '488981C8000000',
         terminal_method_calls['uiRangeHints']),
        (47, 'useAIExclusiveFrame', 'bool', 0x58, 0x37DE99D,
         0x2CA88C0, 0x37DE9C2, '884158', None),
    ]
    tail_reads = []
    for order_index, field_name, expected_wire_type, expected_offset, call_rva, target_rva, store_rva, store_hex, method_spec in tail_field_expectations:
        field = skill_fields[field_name]
        require(field['fieldOffset'], expected_offset, source,
                field['metadataFieldIndex'])
        field_type = field_wire_identity(field_name, field)
        require(field_type['wireType'], expected_wire_type, source,
                field['metadataFieldIndex'])
        if method_spec is not None:
            generic = method_spec['genericType']
            if field_type['typeKind'] == 0x15:
                require(field_type['typeDefinitionIndex'], generic['typeDefinitionIndex'],
                        source, field['metadataFieldIndex'])
                require(field_type['elementTypeDefinitionIndex'],
                        generic['elementTypeDefinitionIndex'], source,
                        field['metadataFieldIndex'])
            else:
                require(field_type['typeDefinitionIndex'],
                        generic['typeDefinitionIndex'], source,
                        field['metadataFieldIndex'])
        store_raw = pe.bytes_at_va(pe.image_base + store_rva, len(bytes.fromhex(store_hex)))
        require(store_raw, bytes.fromhex(store_hex), source, store_rva)
        call_raw = pe.bytes_at_va(pe.image_base + call_rva, 5)
        if method_spec is None:
            helper_site = next(site for site in cursor_hook_sites['sites']
                               if site['callInstructionRva'] == call_rva)
            require(helper_site['targetRva'], target_rva, source, call_rva)
        else:
            require(method_spec['targetRva'], target_rva, source, call_rva)
        tail_reads.append({
            'serializedOrderIndex': order_index,
            'fieldName': field_name,
            'wireType': field_type['wireType'],
            'fieldType': field_type,
            'objectField': {
                'metadataFieldIndex': field['metadataFieldIndex'],
                'fieldOffset': field['fieldOffset'],
                'metadataTypeIndex': field['metadataTypeIndex'],
            },
            'callInstructionRva': call_rva,
            'callInstructionHex': call_raw.hex().upper(),
            'readerTargetRva': target_rva,
            'readerOperation': ('native-bool-read-helper' if method_spec is None else
                                method_spec['methodIdentity']['name']),
            'readerMethodSpec': method_spec,
            'storeInstructionRva': store_rva,
            'storeInstructionHex': store_raw.hex().upper(),
        })

    gameplay_tag_list_type = type_index(
        'Beyond.Gameplay.Core.GameplayTagList', 'Gameplay.Beyond.dll')
    gameplay_tag_list_definition = md.types[gameplay_tag_list_type]
    require(gameplay_tag_list_definition.field_count, 1, source, gameplay_tag_list_type)
    wrapper_fields = field_layout(gameplay_tag_list_type, {'predefinedTag'})
    wrapper_member_field = wrapper_fields['predefinedTag']
    wrapper_member_type = field_wire_identity('predefinedTag', wrapper_member_field)
    if wrapper_member_type['typeKind'] != 0x15:
        raise ContextError(source, wrapper_member_field['metadataFieldIndex'],
                           'GameplayTagList.predefinedTag is a generic List<GameplayTag>',
                           wrapper_member_type)
    require(wrapper_member_type['wireType'],
            'System.Collections.Generic.List`1<Beyond.Gameplay.Core.GameplayTag>',
            source, wrapper_member_field['metadataFieldIndex'])
    wrapper_nested_arguments = wrapper_evidence.get('elementInstantiation', {}).get('arguments')
    if (not isinstance(wrapper_nested_arguments, (list, tuple)) or
            len(wrapper_nested_arguments) != 1):
        raise ContextError(source, 0, 'wrapper reader nested list has one generic element argument',
                           wrapper_nested_arguments)
    require(wrapper_member_type['elementRawTypeRecordHex'],
            wrapper_nested_arguments[0].get('raw_type_record_hex'),
            source, wrapper_member_field['metadataFieldIndex'])
    wrapper_method_identities = wrapper_evidence.get('methodIdentities')
    if not isinstance(wrapper_method_identities, list) or len(wrapper_method_identities) != 2:
        raise ContextError(source, 0, 'both exact GameplayTagList reader and formatter identities',
                           wrapper_method_identities)
    gameplay_tag_wrapper = {
        'typeDefinitionIndex': gameplay_tag_list_type,
        'typeName': md.type_full_name(gameplay_tag_list_definition),
        'memberCount': gameplay_tag_list_definition.field_count,
        'member': {
            'name': 'predefinedTag',
            'metadataFieldIndex': wrapper_member_field['metadataFieldIndex'],
            'fieldOffset': wrapper_member_field['fieldOffset'],
            'wireType': wrapper_member_type['wireType'],
            'fieldType': wrapper_member_type,
        },
        'readerMethodIdentity': wrapper_method_identities[0],
        'formatterMethodIdentity': wrapper_method_identities[1],
        'nestedReadType': wrapper_member_type['wireType'],
        'nestedReadInstantiation': wrapper_evidence['elementInstantiation'],
        'headerEvidence': wrapper_evidence['wrapperFraming'],
        'headerCodeWindows': wrapper_evidence['headerCodeWindows'],
    }

    nested_reader_methods = module_methods(pe, md, modules, image_owners, [
        (104420, 'Beyond.MemoryPack.Beyond_Gameplay_Core_ToggleBuffDataForMemoryPack',
         'Deserialize', 0x4438A40),
        (104433, 'Beyond.MemoryPack.Beyond_Gameplay_Core_UIRangeHintDataForMemoryPack',
         'Deserialize', 0x3A60AE0),
        (107721, 'Beyond.MemoryPack.Beyond_Gameplay_SkillHintShapeDataForMemoryPack',
         'Deserialize', 0x3997B70),
        (104467, 'Beyond.MemoryPack.Beyond_Gameplay_Core_GameplayTagForMemoryPack',
         'Deserialize', 0x40EFC30),
    ], source=source, expected_image='MemoryPack.Beyond.dll')
    nested_code_windows = []
    for rva, length, expected in (
            (0x4438A40, 0xB3, '79E10BB093386D263DED64AF51B082F0CDEF758DCB7C779AAAB6411839036CC1'),
            (0x3A60AE0, 0xD4, '98CCCC5E6DB50926C87C91CD5465CFAF1FB033DF01AD43ED3490BF760EDE3204'),
            (0x3997B70, 0x33F, '07D6FE9927BF0D51DC1B5BAC8E185C68B695890BCCEF3B780B3F7960AAAAC299'),
            (0x40EFC30, 0x66, '20E91A6A12C8F0744F68C6B10AF26032F7030FA75C62AD17CDCFDF986A18EF89')):
        raw = pe.bytes_at_va(pe.image_base + rva, length)
        digest = hashlib.sha256(raw).hexdigest().upper()
        require(digest, expected, source, rva)
        nested_code_windows.append({'rva': rva, 'byteLength': length,
                                    'sha256': digest, 'includesNormalReturn': True})

    def direct_reader_call(call_rva, target_rva, role):
        raw = pe.bytes_at_va(pe.image_base + call_rva, 5)
        require(raw[:1], b'\xE8', source, call_rva)
        target = relative_branch_target(raw, pe.image_base + call_rva, source=source)
        require(target, pe.image_base + target_rva, source, call_rva)
        return {'callInstructionRva': call_rva, 'callInstructionHex': raw.hex().upper(),
                'targetRva': target_rva, 'role': role}

    def nested_field(type_def_index, field_rows, field_name, expected_offset, expected_wire):
        field = field_rows[field_name]
        require(field['fieldOffset'], expected_offset, source,
                field['metadataFieldIndex'])
        identity = field_wire_identity(field_name, field)
        require(identity['wireType'], expected_wire, source,
                field['metadataFieldIndex'])
        return {'typeDefinitionIndex': type_def_index,
                'metadataFieldIndex': field['metadataFieldIndex'],
                'metadataTypeIndex': field['metadataTypeIndex'],
                'fieldOffset': field['fieldOffset'], 'fieldType': identity}

    toggle_type = type_index('Beyond.Gameplay.Core.ToggleBuffData',
                             'Gameplay.Beyond.dll')
    toggle_definition = md.types[toggle_type]
    require(toggle_definition.field_count, 2, source, toggle_type)
    toggle_fields = field_layout(toggle_type, {'buffs', 'conditions'})
    toggle_buff_field = nested_field(
        toggle_type, toggle_fields, 'buffs', 0x18,
        'System.Collections.Generic.List`1<Beyond.Gameplay.Core.BuffInput>')
    toggle_condition_field = nested_field(
        toggle_type, toggle_fields, 'conditions', 0x10,
        'System.Collections.Generic.List`1<Beyond.Gameplay.Core.Abilities.Condition.ConditionBase>')
    toggle_buff_read = call_method_spec(
        0x4438A95, 0x4438AA2, 428462, 'ReadPackable', 0x381F8F0)
    toggle_condition_read = call_method_spec(
        0x4438ABE, 0x4438ACB, 428462, 'ReadPackable', 0x381F8F0)
    for name, read, element_name in (
            ('buffs', toggle_buff_read, 'Beyond.Gameplay.Core.BuffInput'),
            ('conditions', toggle_condition_read,
             'Beyond.Gameplay.Core.Abilities.Condition.ConditionBase')):
        require(read['genericType']['typeName'],
                'System.Collections.Generic.List`1', source, read['usageVa'])
        require(read['genericType']['elementTypeName'], element_name,
                source, read['usageVa'])
    toggle_schema = {
        'typeDefinitionIndex': toggle_type,
        'typeName': md.type_full_name(toggle_definition),
        'memberCountCompare': {
            'rva': 0x4438A8B, 'rawHex': '4080FD02', 'memberCount': 2},
        'members': [
            {'serializedOrderIndex': 0, 'fieldName': 'buffs',
             'objectField': toggle_buff_field, 'readerMethodSpec': toggle_buff_read,
             'setterCall': direct_reader_call(0x4438AB9, 0x3209E50, 'store buffs result')},
            {'serializedOrderIndex': 1, 'fieldName': 'conditions',
             'objectField': toggle_condition_field,
             'readerMethodSpec': toggle_condition_read,
             'setterCall': direct_reader_call(0x4438ADE, 0x3207AC0,
                                               'store conditions result')},
        ],
        'sourceParserOrder': ['buffs', 'conditions'],
    }

    gameplay_tag_type = type_index('Beyond.Gameplay.Core.GameplayTag',
                                   'Gameplay.Beyond.dll')
    gameplay_tag_definition = md.types[gameplay_tag_type]
    require(gameplay_tag_definition.field_count, 4, source, gameplay_tag_type)
    gameplay_tag_fields = field_layout(gameplay_tag_type, {'tagId'})
    gameplay_tag_id_field = nested_field(
        gameplay_tag_type, gameplay_tag_fields, 'tagId', 0x10, 'System.Int32')
    tag_cursor_helper_windows = []
    for rva, length, expected in (
            (0x2CA8860, 0x57,
             'CA6788FE028DC684758CD40833EFA107116A7BF664BFBF1746D792E52114639F'),
            (0x2CA86B0, 0x50,
             '2358C208F5DDD372AF9E5401907272C1FB2A6E4C49E211689FFC047A2872BB65')):
        raw = pe.bytes_at_va(pe.image_base + rva, length)
        digest = hashlib.sha256(raw).hexdigest().upper()
        require(digest, expected, source, rva)
        tag_cursor_helper_windows.append({'rva': rva, 'byteLength': length,
                                          'sha256': digest})
    tag_cursor_instruction_rows = []
    for rva, raw_hex, operation, byte_width in (
            (0x2CA886F, '83793001', 'require at least one remaining byte', 0),
            (0x2CA8883, '0FB608', 'load one member-count byte', 1),
            (0x2CA8894, '48FF4350', 'advance cursor pointer by one byte', 1),
            (0x2CA8898, 'FF4340', 'increment consumed counter by one byte', 0),
            (0x2CA889B, 'FF4344', 'increment total counter by one byte', 0),
            (0x2CA889E, '897B30', 'store remaining length after subtracting one', 0),
            (0x2CA86BF, '83793004', 'require at least four remaining bytes', 0),
            (0x2CA86D0, '8B30', 'load one little-endian int32', 4),
            (0x2CA86DE, '4883435004', 'advance cursor pointer by four bytes', 4),
            (0x2CA86E3, '83434004', 'increment consumed counter by four bytes', 0),
            (0x2CA86E7, '83434404', 'increment total counter by four bytes', 0),
            (0x2CA86EB, '897B30', 'store remaining length after subtracting four', 0)):
        expected_raw = bytes.fromhex(raw_hex)
        actual_raw = pe.bytes_at_va(pe.image_base + rva, len(expected_raw))
        require(actual_raw, expected_raw, source, rva)
        tag_cursor_instruction_rows.append({
            'rva': rva, 'rawHex': actual_raw.hex().upper(),
            'operation': operation, 'byteWidth': byte_width,
        })
    gameplay_tag_reader = {
        'typeDefinitionIndex': gameplay_tag_type,
        'typeName': md.type_full_name(gameplay_tag_definition),
        'fieldCount': gameplay_tag_definition.field_count,
        'readerMethodIdentity': next(
            row for row in nested_reader_methods if row['methodIndex'] == 104467),
        'memberCountCheck': {
            'rva': 0x40EFC6D, 'rawHex': '807C243001',
            'acceptedMemberCount': 1,
        },
        'tagIdField': gameplay_tag_id_field,
        'readerCall': direct_reader_call(0x40EFC7E, 0x2CA86B0,
                                         'read int32/unmanaged tagId'),
        'storeInstruction': {
            'rva': 0x40EFC88, 'rawHex': '894310',
            'objectFieldOffset': 0x10,
            'wireType': gameplay_tag_id_field['fieldType']['wireType'],
        },
        'cursorAdvancement': {
            'helperCodeWindows': tag_cursor_helper_windows,
            'verifiedInstructions': tag_cursor_instruction_rows,
            'validNormalPathByteWidth': 5,
            'derivation': 'The count helper reads and advances one byte; the int32 helper requires four remaining bytes, reads a four-byte value, and advances cursor/consumed/total by four. The generated reader accepts count one before calling the int32 helper.',
        },
        'normalReturnPathWindow': {
            'rva': 0x40EFC30, 'byteLength': 0x66,
            'sha256': nested_code_windows[-1]['sha256'],
            'normalReturnRva': 0x40EFC95,
            'coldFailureTargetsOutsideWindow': [0xF7A932, 0xF7A95D, 0xF7A997],
        },
        'boundary': 'The registered generated GameplayTag reader accepts member count one on this normal path, consumes a raw int32 and stores it to tagId. Cold malformed-header handlers are outside the pinned normal-return window; this is not runtime list-element dispatch evidence.',
    }
    header_read = direct_reader_call(0x40EFC56, 0x2CA8860,
                                     'read one-byte member count')
    require(pe.bytes_at_va(pe.image_base + 0x40EFC6D, 5),
            bytes.fromhex('807C243001'), source, 0x40EFC6D)
    require(pe.bytes_at_va(pe.image_base + 0x40EFC88, 3),
            bytes.fromhex('894310'), source, 0x40EFC88)
    gameplay_tag_reader['memberCountReadCall'] = header_read

    ui_range_type = type_index('Beyond.Gameplay.Core.UIRangeHintData',
                               'Gameplay.Beyond.dll')
    ui_range_definition = md.types[ui_range_type]
    require(ui_range_definition.field_count, 3, source, ui_range_type)
    ui_range_fields = field_layout(ui_range_type, {'selectAll', 'shapeData', 'targetFaction'})
    ui_select_field = nested_field(ui_range_type, ui_range_fields, 'selectAll', 0x14, 'bool')
    ui_shape_field = nested_field(ui_range_type, ui_range_fields, 'shapeData', 0x18,
                                  'Beyond.Gameplay.SkillHintShapeData')
    ui_faction_field = nested_field(ui_range_type, ui_range_fields, 'targetFaction', 0x10,
                                    'Beyond.Gameplay.Core.FactionType')
    ui_shape_read = call_method_spec(
        0x3A60B57, 0x3A60B64, 428464, 'ReadValue', 0x2DA5C90)
    ui_faction_read = call_method_spec(
        0x3A60B80, 0x3A60B8D, 428448, 'ReadUnmanaged', 0x2CA86B0)
    require(ui_shape_read['genericType']['typeName'],
            'Beyond.Gameplay.SkillHintShapeData', source, ui_shape_read['usageVa'])
    require(ui_faction_read['genericType']['typeName'],
            'Beyond.Gameplay.Core.FactionType', source, ui_faction_read['usageVa'])
    ui_range_schema = {
        'typeDefinitionIndex': ui_range_type,
        'typeName': md.type_full_name(ui_range_definition),
        'memberCountCompare': {
            'rva': 0x3A60B2B, 'rawHex': '4080FD03', 'memberCount': 3},
        'members': [
            {'serializedOrderIndex': 0, 'fieldName': 'selectAll',
             'objectField': ui_select_field,
             'readerCall': direct_reader_call(0x3A60B3B, 0x2CA88C0,
                                               'read boolean member'),
             'setterCall': direct_reader_call(0x3A60B52, 0x50816CC,
                                               'store selectAll')},
            {'serializedOrderIndex': 1, 'fieldName': 'shapeData',
             'objectField': ui_shape_field, 'readerMethodSpec': ui_shape_read,
             'setterCall': direct_reader_call(0x3A60B7B, 0x3209E50,
                                               'store shapeData')},
            {'serializedOrderIndex': 2, 'fieldName': 'targetFaction',
             'objectField': ui_faction_field, 'readerMethodSpec': ui_faction_read,
             'setterCall': direct_reader_call(0x3A60B9F, 0x507E454,
                                               'store targetFaction')},
        ],
        'sourceParserOrder': ['selectAll', 'shapeData', 'targetFaction'],
    }

    shape_type = type_index('Beyond.Gameplay.SkillHintShapeData',
                            'Gameplay.Beyond.dll')
    shape_definition = md.types[shape_type]
    require(shape_definition.field_count, 21, source, shape_type)
    shape_field_names = {
        'angle', 'angleKey', 'centerBaseIsEndPoint', 'centerOffset',
        'centerOffsetXKey', 'centerOffsetZKey', 'extent', 'extentXKey',
        'extentZKey', 'fixedExtent', 'radius', 'radiusKey',
        'restrictEndPointInRange', 'shape', 'useAngleKey',
        'useCenterOffsetKey', 'useExtentKey', 'useRadiusKey',
        'useWidthKey', 'width', 'widthKey'}
    shape_fields = field_layout(shape_type, shape_field_names)
    shape_field_layout = {
        'shape': (0x10, 'Beyond.Gameplay.SkillHintShape'),
        'fixedExtent': (0x14, 'bool'),
        'centerBaseIsEndPoint': (0x15, 'bool'),
        'restrictEndPointInRange': (0x16, 'bool'),
        'useCenterOffsetKey': (0x17, 'bool'),
        'centerOffset': (0x18, 'UnityEngine.Vector2'),
        'centerOffsetXKey': (0x20, 'System.String'),
        'centerOffsetZKey': (0x28, 'System.String'),
        'useExtentKey': (0x30, 'bool'),
        'extent': (0x34, 'UnityEngine.Vector2'),
        'extentXKey': (0x40, 'System.String'),
        'extentZKey': (0x48, 'System.String'),
        'useWidthKey': (0x50, 'bool'),
        'width': (0x54, 'System.Single'),
        'widthKey': (0x58, 'System.String'),
        'useRadiusKey': (0x60, 'bool'),
        'radius': (0x64, 'System.Single'),
        'radiusKey': (0x68, 'System.String'),
        'useAngleKey': (0x70, 'bool'),
        'angle': (0x74, 'System.Single'),
        'angleKey': (0x78, 'System.String'),
    }
    shape_field_contracts = {}
    for name, (offset, wire_type) in shape_field_layout.items():
        shape_field_contracts[name] = nested_field(
            shape_type, shape_fields, name, offset, wire_type)

    shape_operations = [
        ('angle', 'System.Single', 0x3997BCB, 0x2CA8BB0, 0x3997BE2, 0x507E524, None, None),
        ('angleKey', 'System.String', 0x3997BED, 0x2CA8700, 0x3997C04, 0x320C9C0, None, None),
        ('centerBaseIsEndPoint', 'bool', 0x3997C0F, 0x2CA88C0, 0x3997C26, 0x50816E8, None, None),
        ('centerOffset', 'UnityEngine.Vector2', 0x3997C38, 0x3D7E030, 0x3997C4F, 0x5081704,
         0x3997C2B, 'UnityEngine.Vector2'),
        ('centerOffsetXKey', 'System.String', 0x3997C5A, 0x2CA8700, 0x3997C71, 0x3207A90, None, None),
        ('centerOffsetZKey', 'System.String', 0x3997C7C, 0x2CA8700, 0x3997C93, 0x320AC10, None, None),
        ('extent', 'UnityEngine.Vector2', 0x3997CA5, 0x3D7E030, 0x3997CBC, 0x508160C,
         0x3997C98, 'UnityEngine.Vector2'),
        ('extentXKey', 'System.String', 0x3997CC7, 0x2CA8700, 0x3997CDE, 0x3209DF0, None, None),
        ('extentZKey', 'System.String', 0x3997CE9, 0x2CA8700, 0x3997D00, 0x320BA00, None, None),
        ('fixedExtent', 'bool', 0x3997D0B, 0x2CA88C0, 0x3997D22, 0x50816CC, None, None),
        ('radius', 'System.Single', 0x3997D2D, 0x2CA8BB0, 0x3997D44, 0x5081400, None, None),
        ('radiusKey', 'System.String', 0x3997D4F, 0x2CA8700, 0x3997D66, 0x320C900, None, None),
        ('restrictEndPointInRange', 'bool', 0x3997D71, 0x2CA88C0, 0x3997D88, 0x50816B0, None, None),
        ('shape', 'Beyond.Gameplay.SkillHintShape', 0x3997D9A, 0x2CA86B0, 0x3997DB0, 0x507E454,
         0x3997D8D, 'Beyond.Gameplay.SkillHintShape'),
        ('useAngleKey', 'bool', 0x3997DBB, 0x2CA88C0, 0x3997DD2, 0x507E544, None, None),
        ('useCenterOffsetKey', 'bool', 0x3997DDD, 0x2CA88C0, 0x3997DF4, 0x5081694, None, None),
        ('useExtentKey', 'bool', 0x3997DFF, 0x2CA88C0, 0x3997E16, 0x507DEC8, None, None),
        ('useRadiusKey', 'bool', 0x3997E21, 0x2CA88C0, 0x3997E38, 0x507E5F8, None, None),
        ('useWidthKey', 'bool', 0x3997E43, 0x2CA88C0, 0x3997E5A, 0x507EFF0, None, None),
        ('width', 'System.Single', 0x3997E65, 0x2CA8BB0, 0x3997E7C, 0x5081674, None, None),
        ('widthKey', 'System.String', 0x3997E87, 0x2CA8700, 0x3997E9A, 0x320BA60, None, None),
    ]
    shape_serialized_rows = []
    for order_index, (name, wire_type, read_rva, read_target, store_rva,
                      store_target, spec_load_rva, spec_type_name) in enumerate(shape_operations):
        field_contract = shape_field_contracts[name]
        require(field_contract['fieldType']['wireType'], wire_type, source,
                field_contract['metadataFieldIndex'])
        method_spec = None
        if spec_load_rva is not None:
            method_spec = call_method_spec(
                spec_load_rva, read_rva, 428448, 'ReadUnmanaged', read_target)
            require(method_spec['genericType']['typeName'], spec_type_name,
                    source, method_spec['usageVa'])
        else:
            direct_reader_call(read_rva, read_target, f'read {name}')
        setter = direct_reader_call(store_rva, store_target, f'store {name}')
        shape_serialized_rows.append({
            'serializedOrderIndex': order_index,
            'fieldName': name,
            'wireType': wire_type,
            'objectField': field_contract,
            'readerMethodSpec': method_spec,
            'readerCall': {'callInstructionRva': read_rva,
                           'targetRva': read_target,
                           'role': 'MemoryPackReader.ReadUnmanaged generic' if method_spec else
                                   'primitive reader helper'},
            'setterCall': setter,
        })
    shape_schema = {
        'typeDefinitionIndex': shape_type,
        'typeName': md.type_full_name(shape_definition),
        'memberCountCompare': {
            'rva': 0x3997BBB, 'rawHex': '4080FD15', 'memberCount': 21},
        'serializedOrder': shape_serialized_rows,
        'metadataStorageOrder': [
            md.string(md.fields[shape_definition.field_start + index].name_index)
            for index in range(shape_definition.field_count)],
        'sourceParserOrder': [row[0] for row in shape_operations],
    }
    nested_terminal_readers = {
        'status': 'static-registered-reader-layout',
        'methods': nested_reader_methods,
        'codeWindows': nested_code_windows,
        'gameplayTagElement': gameplay_tag_reader,
        'toggleBuffData': toggle_schema,
        'uiRangeHintData': ui_range_schema,
        'skillHintShapeData': shape_schema,
        'boundary': 'The exact generated nested reader bodies, MethodSpecs, declared field types/offsets and parser order align for the authenticated build. The GameplayTag element path accepts member count one, then bounded helpers advance one header byte and four System.Int32 bytes; its five-byte endpoint agrees with the source parser under this static path. The parser preserves the id bytes as unsigned raw/hash and signed views. Other rows are static registered paths too; current per-file live selection and parent cursor remain unobserved.',
    }

    crosscheck = skilldata_corpus_branch_evidence(corpus, source=CORPUS_REPORT_RELATIVE)
    terminal_collision = skilldata_terminal_collision_evidence(
        corpus, source=CORPUS_REPORT_RELATIVE)
    terminal_sample = skilldata_terminal_sample_byte_witness(
        terminal_collision, representative_sample_raw,
        source='game/Json/SkillData/Potential_test.json')
    terminal_tail_layout = skilldata_terminal_tail_layout(
        terminal_collision, terminal_sample, tail_reads, gameplay_tag_wrapper,
        source=source)
    empty_count = crosscheck['branchCounts']['bothListsEmpty']
    return {
        'status': 'static-reader-order-conditional-cursor',
        'inputSetSha256': crosscheck['inputSetSha256'],
        'methods': selected_methods,
        'codeWindows': code_windows,
        'verifiedInstructionWindows': instruction_windows,
        'formatterThunkEdges': formatter_thunks,
        'firstSkillDataField': {
            'serializedOrderIndex': 0,
            'fieldName': 'actionGroupData',
            'objectField': {'typeDefinitionIndex': skill_type, **skill_fields['actionGroupData']},
            'readerMethodSpec': action_group_call,
            'staticEvidence': 'SkillData Deserialize validates top-level header 48, calls ReadValue<Core.ActionGroupData>, then stores the returned object to Core.SkillData+0xC0 before the next member reader call.',
        },
        'actionGroupDataMembers': [
            {'serializedOrderIndex': index, 'fieldName': name,
             'objectField': {'typeDefinitionIndex': action_group_type, **action_fields[name]},
             'readerMethodSpec': call}
            for index, (name, call) in enumerate((('passiveEventActions', list_calls[0]),
                                                   ('timelineActions', list_calls[1])))
        ],
        'timelineActionDataReader': timeline_action_data_reader,
        'currentVfsBranchCrossCheck': crosscheck,
        'representativeTerminalShapeCollision': terminal_collision,
        'representativeTerminalSampleByteWitness': terminal_sample,
        'representativeTerminalTailLayout': terminal_tail_layout,
        'nestedTerminalReaders': nested_terminal_readers,
        'cursorHookCallSites': cursor_hook_sites,
        'runtimeCursorObserver': runtime_cursor_observer,
        'conditionalEmptyObjectRange': {
            'start': 1, 'end': 10, 'endExclusive': True,
            'candidateFiles': empty_count,
            'status': 'conditional-on-provider-selection',
            'formatterCandidateReportKey': 'selectedListFormatterCandidate',
            'condition': 'The ordinary provider resolves both List<T> queries to the audited MemoryPack.Formatters.ListFormatter<T> candidate; each zero count consumes its four-byte collection header and returns without an element body.',
        },
        'exactClosedActionGroupDataRecords': 0,
        'level': 'exact selected-build generated-reader module/token, body-window, MethodSpec, generic field type, object-field-offset and current positive-branch byte-range joins',
        'boundary': 'The five terminal SkillData reads and nested GameplayTag, ToggleBuffData, UIRangeHintData and SkillHintShapeData readers join exact registered static bodies, MethodSpecs, declared IL2CPP field types/offsets and current source bytes. Selected branches cover every positive list-count shape observed in the authenticated corpus. GameplayTag elements match five-byte native paths; other nested parsers match their reported ends and field order. Under the registered wrapper/List<GameplayTag> path, shifted candidates with wrapper bytes 0 or 3 leave the supported header path, while the count-one case produces a signed list count of 0x01000000 with only 13 bytes remaining and takes the pinned count-range failure path. Runtime provider/cache selection and an executed parent cursor are still unobserved, so this is conditional static evidence, not a promoted whole-file endpoint. The intervening [10,518) bytes stay opaque, [1,10) remains conditional on the two generic list formatter paths, no whole SkillData record is closed, and all 2,621 whole-file terminal candidates remain ambiguous. The authenticated SkillData corpus is not re-streamed by this audit.',
    }
