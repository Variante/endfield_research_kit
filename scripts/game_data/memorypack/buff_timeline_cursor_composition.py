"""Compose selected nullable child cursor equations below list/root admission.

The native plan proves the caller's direct advances and same-Reader joins.
Receipt checks account for already certified original storage spans; they do
not establish the action callback's native cursor advance or runtime effects.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.memorypack.corpus_gate import CensusGateError
from scripts.game_data.memorypack import buff_timeline_element_sources as sources
from scripts.game_data.memorypack import buff_timeline_read_value as read_value
from scripts.game_data.memorypack import buff_timeline_source_returns as source_returns
from scripts.game_data.memorypack import buff_timeline_composition as composition
from scripts.game_data.memorypack import buff_sequence_array_source as array_source
from scripts.game_data.memorypack import utf8_source_helper as strings

LABEL = 'buffTimelineCursorComposition'
SCOPE = 'selected-nullable-child-cursor-equations-and-receipted-storage-spans'
SCHEMA = 'endfield.buff-timeline-cursor-composition.v1'


def _fail(check: str, expected: Any, actual: Any) -> None:
    error = CensusGateError(f'{LABEL}.{check}', source=sources.CONTRACT_PATH.as_posix(),
                           expected=str(expected)[:1024], actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL, scope=SCOPE)
    error.args = (json.dumps(error.diagnostic, sort_keys=True),)
    raise error


def _contracts() -> dict:
    values = {'sources': sources._contract(), 'readValue': read_value._contract(),
              'returns': source_returns._contract(), 'static': composition._contract(),
              'array': array_source._contract()}
    pins = values['sources']['nativeInputs']
    if any(c['nativeInputs'] != pins for c in values.values()):
        _fail('dependency-build', 'all cursor dependencies describe the same selected build',
              {k: c['nativeInputs'] for k, c in values.items()})
    return values


def derive_cursor_plan(source: dict, value: dict, array: dict, returns: dict) -> dict:
    """Derive direct widths only from the independently validated field profiles."""
    records = source['records']
    if set(records) != {'timeline', 'forceSync'}:
        _fail('source-records', 'one Timeline and ForceSync source', list(records))
    timeline, force = records['timeline'], records['forceSync']
    fields = timeline['members']
    if ([(m['fieldName'], m['declaredType']) for m in fields] != sources.FIELD_TYPES['timeline']
            or [m['kind'] for m in fields] != sources.KINDS['timeline']
            or [(m['fieldName'], m['declaredType']) for m in force['members']] != sources.FIELD_TYPES['forceSync']
            or [m['kind'] for m in force['members']] != sources.KINDS['forceSync']
            or timeline['memberCount'] != 4 or force['memberCount'] != 4):
        _fail('ordered-cursor-profile', 'same independently owned ordered fields and source kinds', records)
    if (fields[1]['declaredType'] != array['originalType']
            or fields[3]['declaredType'] != force['runtimeTypeName']
            or value['sourceChildFields'] != [fields[1]['fieldName'], fields[3]['fieldName']]
            or any(m['sourceCall']['targetRva'] != value['outerReadValueTransfer']['entryRva']
                   for m in (fields[1], fields[3]))):
        _fail('closed-child-reader-join', 'same original Sequence/ForceSync children and actual ReadValue helper', fields)
    outer = value['outerReadValueTransfer']
    modes = value['optimizedAdapterTransfers']
    if (outer['sameReaderForwarded'] is not True or outer['sameLocalOutputReturned'] is not True
            or outer['directReaderCursorStores'] != 0 or outer['completeReturnProved'] is not True
            or set(modes) != {'ff', 'nonnull', 'nullWrapperOutput'}):
        _fail('outer-reader-return', 'same Reader and complete output return with no direct cursor stores', outer)
    for mode, proof in modes.items():
        width = 1 if mode == 'ff' else 0
        stores = 4 if mode == 'ff' else 0
        if (proof['sameReaderPreserved'] is not True or proof['completeReturnProved'] is not True
                or proof['wireBytesConsumedDirectly'] != width or proof['readerCursorStoresDirectly'] != stores):
            _fail('adapter-direct-cursor', {'mode': mode, 'wireBytes': width, 'cursorStores': stores}, proof)
    complete = returns['completeSourceReturns']
    if set(complete) != {'timeline', 'forceSync'} or any(
            p['completeReturn'] is not True or p['suffixCalls'] != 0 or p['suffixReaderWrites'] != 0
            for p in complete.values()):
        _fail('source-return-cursor', 'complete source epilogues without additional cursor transfers', complete)
    arrays = array['completeSourcePrograms']
    if (arrays['completeSelectedReturns'] is not True or arrays['wrapperNullWireBytes'] != 1
            or arrays['nonNullDirectWireBytes'] != 7):
        _fail('sequence-array-direct-cursor', 'complete one-byte FF and seven-byte nonnull array programs', arrays)

    def scalar_width(member: dict, bits: int) -> int:
        if member['widthBits'] != bits:
            _fail('scalar-wire-width', bits, member)
        return bits // 8

    timeline_bytes = 1 + scalar_width(fields[0], 32) + scalar_width(fields[2], 32)
    fm = force['members']
    force_bytes = 1 + scalar_width(fm[0], 8) + scalar_width(fm[2], 32) + scalar_width(fm[3], 32)
    return {
        'schema': SCHEMA, 'scope': SCOPE,
        'timelineType': timeline['runtimeTypeName'], 'forceSyncType': force['runtimeTypeName'],
        'sequenceType': fields[1]['declaredType'],
        'timelineFields': sources.FIELD_TYPES['timeline'], 'forceSyncFields': sources.FIELD_TYPES['forceSync'],
        'stringSourceHelperRva': fm[1]['sourceCall']['targetRva'],
        'nullableNullWireBytes': modes['ff']['wireBytesConsumedDirectly'],
        'positiveAdapterDirectWireBytes': modes['nonnull']['wireBytesConsumedDirectly'],
        'timelinePositiveDirectWireBytes': timeline_bytes,
        'forceSyncPositiveDirectWireBytes': force_bytes,
        'sequencePositiveDirectWireBytes': arrays['nonNullDirectWireBytes'],
        'equations': {
            'nullableChildFF': '1',
            'sequenceNonnull': '7 + sum(action callback cursor advances)',
            'forceSyncNonnull': '10 + string helper cursor advance',
            'timelinePositiveSource': '9 + nullable Sequence advance + nullable ForceSync advance',
        },
        'positivePeekConsumesHeader': False,
        'headerContinuityCondition': 'same stable buffered Reader bytes and unchanged cursor across non-reading helper calls',
        'sameReaderAndCompleteReturns': True,
        'actionCallbackCursorEqualityProved': False,
        'indirectGlobalReaderEffectsProved': False,
        'positiveListAdmitted': False, 'wholeRootAdmitted': False, 'runtimeMeaningExact': False,
    }


def _validate_image(image: Any, contracts: dict) -> dict:
    # These are the newly joined callers, concrete forwarding and source returns.
    composition._validate_image(image, contracts['static'])
    value = read_value._validate_image(image, contracts['readValue'])
    returns = source_returns._validate_image(image, contracts['returns'])
    array = array_source._validate_image(image, contracts['array'])
    return derive_cursor_plan(contracts['sources'], value, array, returns)


def validate_current_native_contract(*, gameassembly: Path | None = None,
                                     metadata: Path | None = None) -> dict:
    contracts = _contracts()
    pins = contracts['sources']['nativeInputs']
    gate = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
                                        gameassembly=gameassembly, metadata=metadata)
    if gate.status != 'validated':
        return {'status': gate.status, 'detail': gate.detail, 'scope': SCOPE, 'nativeInputs': pins}
    unity = Path(gate.gameassembly).parent / 'UnityPlayer.dll'

    def unity_matches():
        return unity.is_file() and hashlib.sha256(unity.read_bytes()).hexdigest().upper() == pins['UnityPlayer.dll']

    if not unity_matches():
        return {'status': 'mismatched' if unity.is_file() else 'missing',
                'detail': 'UnityPlayer.dll missing or mismatched', 'scope': SCOPE, 'nativeInputs': pins}
    try:
        plan = _validate_image(open_native_image(gate.gameassembly, gate.metadata), contracts)
        utf8 = strings.validate_current_native_contract(gameassembly=gate.gameassembly, metadata=gate.metadata)
        if utf8.get('status') != 'validated' or utf8.get('nativeInputs') != pins:
            status = utf8.get('status', 'unresolved')
            if status in ('validated', 'mismatch'):
                status = 'mismatched'
            return {'status': status, 'detail': 'UTF-8 source helper gate',
                    'scope': SCOPE, 'nativeInputs': pins}
    except ValueError as error:
        if isinstance(error, CensusGateError):
            raise
        _fail('native-cursor-joins', 'complete current nullable/forwarding/source/return joins', str(error))
    after = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
                                         gameassembly=gate.gameassembly, metadata=gate.metadata)
    if after.status != 'validated' or not unity_matches():
        return {'status': after.status if after.status != 'validated' else 'mismatched',
                'detail': 'native inputs changed during cursor composition', 'scope': SCOPE, 'nativeInputs': pins}
    return {'status': 'validated', 'scope': SCOPE, 'nativeInputs': pins, 'plan': plan,
            'utf8Source': utf8, 'childSchemaAdmitted': False, 'positiveListAdmitted': False,
            'wholeRootAdmitted': False, 'runtimeMeaningExact': False,
            'evidenceBoundary': 'Exact direct cursor equations and complete same-Reader nullable caller/source joins on selected paths. Stable buffered bytes, compatible runtime selection, typed normal returns and unmodified Reader aliases remain conditions. Original action/string receipts measure stored spans; action callback cursor equality, global effects, allocation state, positive list/root admission and runtime execution remain unresolved.'}


def check_original_element_cursor_receipt(receipt: dict, plan: dict) -> dict:
    """Check a certified original element's framing arithmetic, without reparsing."""
    if (plan.get('schema') != SCHEMA or plan.get('scope') != SCOPE
            or receipt.get('typeName') != plan['timelineType']
            or receipt.get('positiveSourceFieldsExact') is not True
            or receipt.get('recursiveStoredSchemaExact') is not False
            or receipt.get('scope') != sources.SCOPE
            or any(receipt.get(k) is not False for k in ('positiveListAdmitted', 'wholeRootAdmitted', 'runtimeMeaningExact'))):
        _fail('receipt-boundary', 'previous certified source-only original element', receipt.get('schema'))

    def span(row: dict) -> int:
        a, b = row.get('start'), row.get('end')
        if type(a) is not int or type(b) is not int or not 0 <= a < b:
            _fail('original-span', 'bounded nonempty integer span', [a, b])
        return b - a

    def fields(owner: dict, expected: list) -> list:
        rows = owner.get('namedFields', [])
        if [(r.get('fieldName'), r.get('declaredType')) for r in rows] != [tuple(r) for r in expected]:
            _fail('ordered-original-fields', expected, rows)
        cursor = owner['start'] + 1
        for row in rows:
            span(row)
            if row['start'] != cursor:
                _fail('contiguous-original-fields', cursor, row['start'])
            cursor = row['end']
        if cursor != owner['end']:
            _fail('complete-original-field-span', owner['end'], cursor)
        return rows

    total = span(receipt)
    rows = fields(receipt, plan['timelineFields'])
    if span(rows[0]) != 4 or span(rows[2]) != 4:
        _fail('original-timeline-scalars', 'two exact Int32 spans', [span(rows[0]), span(rows[2])])
    sequence = rows[1]['child']
    if (sequence.get('typeName') != plan['sequenceType'] or sequence.get('recursiveStoredSchemaExact') is not True
            or [sequence.get('start'), sequence.get('end')] != [rows[1]['start'], rows[1]['end']]):
        _fail('original-sequence-child', 'same previously certified nullable child span', sequence)
    action_bytes = 0
    if sequence['status'] == 'exact-null':
        seq_bytes = plan['nullableNullWireBytes']
        if sequence.get('namedFields') != []:
            _fail('null-sequence-payload', 'no fields after FF', sequence)
    elif sequence['status'] == 'named-sequence-exact':
        count, actions = sequence.get('count'), sequence.get('actions', [])
        if type(count) is not int or count < -1 or len(actions) != max(0, count):
            _fail('original-action-count', 'same signed nullable count and child roster', [count, len(actions)])
        cursor = sequence['start'] + 5
        for action in actions:
            width = span(action)
            if action.get('recursiveStoredSchemaExact') is not True or action['start'] != cursor:
                _fail('original-action-spans', 'certified ordered adjacent child spans', action)
            if action.get('status') == 'exact-null' and width != 1:
                _fail('null-action-width', 1, width)
            cursor = action['end']
            action_bytes += width
        flags = sequence.get('flags', [])
        if [f.get('name') for f in flags] != ['onlyExecuteWhenSourceIsGuard', 'onlyExecuteWhenSourceIsMainChar']:
            _fail('original-sequence-flags', 'both ordered terminal source flags', flags)
        for flag in flags:
            if (flag.get('start') != cursor or span(flag) != 1
                    or type(flag.get('rawByte')) is not int or not 0 <= flag['rawByte'] <= 255):
                _fail('original-normalized-flag-span', 'one stored raw byte at the next cursor', flag)
            cursor = flag['end']
        if cursor != sequence['end']:
            _fail('complete-sequence-original-span', sequence['end'], cursor)
        seq_bytes = plan['sequencePositiveDirectWireBytes'] + action_bytes
    else:
        _fail('sequence-receipt-selection', 'certified null or named Sequence', sequence['status'])
    if seq_bytes != span(sequence):
        _fail('sequence-cursor-equation', seq_bytes, span(sequence))

    force = rows[3]['child']
    if [force.get('start'), force.get('end')] != [rows[3]['start'], rows[3]['end']]:
        _fail('original-force-child', 'same previously certified child span', force)
    if force.get('status') == 'exact-null':
        # The current source-element producer only certifies positive ForceSync.
        _fail('force-null-source-receipt', 'independent original null child receipt required', force)
    if force.get('positiveSourceFieldsExact') is not True:
        _fail('force-source-fields', 'independent certified positive ForceSync fields', force)
    force_rows = fields(force, plan['forceSyncFields'])
    if [span(force_rows[n]) for n in (0, 2, 3)] != [1, 4, 4]:
        _fail('force-original-scalars', 'one normalized byte and two four-byte scalars', force_rows)
    string = force_rows[1]['child']
    length = string.get('byteLength')
    if (string.get('storedStringValueExact') is not True or string.get('wholeStoredSpanExact') is not True
            or string.get('nativeStatus') != 'validated' or string.get('runtimeMeaningExact') is not False
            or string.get('source') != receipt.get('source')
            or string.get('logicalSha256') != receipt.get('logicalSha256')
            or string.get('sourceHelperRva') != plan['stringSourceHelperRva']
            or [string.get('start'), string.get('end')] != [force_rows[1]['start'], force_rows[1]['end']]
            or type(length) is not int or length < -1 or span(string) != 4 + max(0, length)):
        _fail('original-string-cursor-span', 'same authenticated source helper and exact stored UTF-8 length span', string)
    force_bytes = plan['forceSyncPositiveDirectWireBytes'] + span(string)
    if force_bytes != span(force):
        _fail('force-cursor-equation', force_bytes, span(force))
    expected = plan['timelinePositiveDirectWireBytes'] + seq_bytes + force_bytes
    if expected != total:
        _fail('complete-timeline-cursor-equation', expected, total)
    return {'source': receipt['source'], 'logicalSha256': receipt['logicalSha256'],
            'start': receipt['start'], 'end': receipt['end'], 'timelineStoredBytes': total,
            'sequenceStoredBytes': seq_bytes, 'forceSyncStoredBytes': force_bytes,
            'actionStoredBytes': action_bytes, 'stringStoredBytes': span(string),
            'originalStorageSpanEquationChecked': True, 'actionCallbackCursorEqualityProved': False,
            'positiveListAdmitted': False, 'wholeRootAdmitted': False, 'runtimeMeaningExact': False}
