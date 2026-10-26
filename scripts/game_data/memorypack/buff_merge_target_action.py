"""Current named MergeTarget configuration and independent target-list elements.

Stored targets and the merge flag do not establish selected runtime entities,
group replacement, merging or execution. Historical tags/layouts are excluded.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.context_audit_memorypack import buff_action_read_order
from scripts.game_data.memorypack.action_dispatcher import load_action_routes
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError, _fingerprint, _package_import_closure
from scripts.game_data.memorypack import named_native_records as named, utf8_source_helper as strings

LABEL = 'buffMergeTargetAction'
CONTRACT_PATH = CONTRACTS_DIR / 'buff_merge_target_action_native.json'
RECORD = 'mergeTarget'
TARGET_TYPE = 'Beyond.Gameplay.Core.TargetSettings'


def _contract() -> dict[str, Any]:
    value, _ = read_reviewed_contract(CONTRACT_PATH,
        schema='endfield.buff-merge-target-action-native-contract.v1', status='exact-current-build', label=LABEL)
    if (set(value.get('records', {})) != {RECORD}
            or len(value.get('actionDispatch', {})) != 1
            or set(value['actionDispatch'].values()) != {RECORD}):
        raise ValueError(f'{LABEL}.contract:shape')
    record = value['records'][RECORD]
    expected = [('isEnable', 'byte'), ('priorityLevel', 'scalar32'),
        ('priorityOffset', 'scalar32'), ('serverActionIndex', 'scalar32'),
        ('mergeHittableTargets', 'byte'), ('targetGroupKey', 'byte-payload'), ('targets', 'target-list')]
    if (record.get('inheritedMemberCount') != 4
            or [(m['fieldName'], m['kind']) for m in record['members']] != expected
            or record['members'][4]['declaredType'] != 'bool'
            or record['members'][5]['declaredType'] != 'string'
            or record['members'][6]['declaredType'] != f'System.Collections.Generic.List`1<{TARGET_TYPE}>'
            or record['members'][6].get('sourceContextInstructionRva') is None):
        raise ValueError(f'{LABEL}.contract:typed-members')
    return value


def supported_tags() -> frozenset[int]:
    return frozenset(map(int, _contract()['actionDispatch']))


def _members(contract: dict[str, Any]) -> dict[str, Any]:
    return {k: [{'fieldName': m['fieldName'], 'kind': m['kind']} for m in row['members']]
            for k, row in contract['records'].items()}


def _fail(check: str, expected: Any, actual: Any, *, record: str = RECORD, field: str = '') -> None:
    c = _contract()
    error = CensusGateError(f'{LABEL}.{check}',
        source=(CONTRACTS_DIR / c['records'][record]['sourceContract']).as_posix(),
        expected=str(expected)[:1024], actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL, record=record, field=field, nativeInputs=c['nativeInputs'])
    error.args = (json.dumps(error.diagnostic, sort_keys=True),)
    raise error


def validate_current_native_contract(*, children: dict[str, Any],
                                     gameassembly: Path | None = None, metadata: Path | None = None) -> dict[str, Any]:
    c = _contract(); pins = c['nativeInputs']
    gate = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
        gameassembly=gameassembly, metadata=metadata)
    if gate.status != 'validated':
        return {'status': gate.status, 'detail': gate.detail, 'nativeInputs': pins}
    target = children.get('target', {})
    if target.get('status') != 'validated' or target.get('nativeInputs') != pins:
        _fail('target-child', {'status': 'validated', 'nativeInputs': pins}, target)
    source_path = CONTRACTS_DIR / c['records'][RECORD]['sourceContract']
    paths = set(_package_import_closure(Path(__file__))) | {CONTRACT_PATH, source_path, strings.CONTRACT_PATH}
    inputs = sorted((_fingerprint(p) for p in paths), key=lambda r: r['path'])
    unity = Path(gate.gameassembly).parent / 'UnityPlayer.dll'
    if not unity.is_file() or _fingerprint(unity)['sha256'] != pins['UnityPlayer.dll']:
        _fail('UnityPlayer.dll', pins['UnityPlayer.dll'], 'missing-or-mismatched')
    image = open_native_image(gate.gameassembly, gate.metadata)
    source = json.loads(source_path.read_bytes())
    buff_action_read_order(image.pe, image.metadata, image.registration, image.instantiations,
        image.modules, image.owners, source=str(gate.gameassembly), contract_path=source_path)
    proved = named.validate_named_records(image, source, c['records'], label=LABEL, fail=_fail)
    routes, audit = load_action_routes(gameassembly=gate.gameassembly, metadata=gate.metadata)
    tag = next(iter(supported_tags())); route = routes.get(tag); record = c['records'][RECORD]
    if (audit.get('status') != 'validated' or route is None or route.status != 'resolved'
            or route.wrapper_name != record['wrapperTypeName']
            or list(route.member_order) != [m['fieldName'] for m in record['members']]
            or list(route.member_declared_types) != [m['declaredType'] for m in record['members']]):
        _fail('dispatcher-members', record['wrapperTypeName'], None if route is None else route.row())
    string = strings.validate_current_native_contract(gameassembly=Path(gate.gameassembly), metadata=Path(gate.metadata))
    helper = record['members'][5]['sourceCall']['targetRva']
    if (string.get('status') != 'validated' or string.get('nativeInputs') != pins
            or helper not in string.get('sourceHelpers', ())):
        _fail('string-source-helper', helper, string)
    after = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
        gameassembly=gate.gameassembly, metadata=gate.metadata)
    if after.status != 'validated':
        return {'status': after.status, 'detail': after.detail, 'nativeInputs': pins}
    if _fingerprint(unity)['sha256'] != pins['UnityPlayer.dll']:
        _fail('UnityPlayer.dll-after', pins['UnityPlayer.dll'], 'mismatched')
    for pin in inputs:
        actual = _fingerprint(Path(pin['path']))
        if actual != pin:
            _fail('source-drift', pin, actual)
    return {'status': 'validated', 'nativeInputs': pins, 'recordMembers': proved,
        'actionDispatch': c['actionDispatch'], 'stringSource': string,
        'provenance': {'inputs': inputs}, 'evidenceBoundary': c['evidenceBoundary']}


def decode_action(data: bytes, *, source: str, digest: str, start: int, end: int, tag: int,
                  native_validation: dict[str, Any], target_decoder: Callable[..., dict[str, Any]]) -> dict[str, Any]:
    c = _contract(); context = native_validation.get('children', {})
    proof = context.get('mergeTarget', {}); target = context.get('target', {})
    if (native_validation.get('status') != 'validated' or native_validation.get('nativeInputs') != c['nativeInputs']
            or proof.get('status') != 'validated' or proof.get('nativeInputs') != c['nativeInputs']
            or proof.get('recordMembers') != _members(c) or proof.get('actionDispatch') != c['actionDispatch']
            or target.get('status') != 'validated' or target.get('nativeInputs') != c['nativeInputs']
            or type(tag) is not int or str(tag) not in c['actionDispatch']
            or not isinstance(data, bytes) or not source or not isinstance(digest, str)
            or hashlib.sha256(data).hexdigest().upper() != digest.upper()
            or type(start) is not int or type(end) is not int or not 0 <= start < end <= len(data)):
        raise ValueError(f'{LABEL}.decode:native-source-or-span')
    physical = bytes((tag,)) if tag < 250 else b'\xfa' + tag.to_bytes(2, 'little')
    if data[start:start + len(physical)] != physical:
        raise ValueError(f'{LABEL}.decode:physical-union-tag')
    reader = Reader(data, source, end); reader.pos = start
    if reader.nested_union_tag((tag,), 'merge-target') != tag:
        raise ValueError(f'{LABEL}.decode:unexpected-null-union')
    record = c['records'][RECORD]; fields = []
    if reader.peek() == 255:
        reader.take(1, 'null-merge-target-wrapper')
    else:
        reader.header(len(record['members']))
        for member in record['members']:
            at = reader.pos; kind = member['kind']; value = {}
            if kind in ('byte', 'scalar32'):
                value['rawHex'] = reader.take(1 if kind == 'byte' else 4, member['fieldName']).hex().upper()
            elif kind == 'byte-payload':
                reader.byte_payload()
                value['child'] = strings.decode_source_string(data, source=source, digest=digest,
                    start=at, end=reader.pos, source_helper_rva=member['sourceCall']['targetRva'],
                    native_validation=proof.get('stringSource', {}))
            elif kind == 'target-list':
                count = reader.count(1, nullable=True); items = None if count == -1 else []
                for i in range(max(0, count)):
                    begin = reader.pos
                    reader.target_profile()
                    span = {'start': begin, 'end': reader.pos, 'fieldName': f'{member["fieldName"]}[{i}]'}
                    child = ({**span, 'status': 'exact-null-wrapper', 'recursiveStoredSchemaExact': True}
                        if data[begin:reader.pos] == b'\xff' else target_decoder(data, source, digest, span, context))
                    if (child.get('recursiveStoredSchemaExact') is not True
                            or [child.get('start'), child.get('end')] != [begin, reader.pos]):
                        raise ValueError(f'{LABEL}.decode:target-span index={i} at={begin}')
                    items.append(child)
                value['child'] = {'start': at, 'end': reader.pos, 'count': count, 'items': items,
                    'recursiveStoredSchemaExact': True}
            else:
                raise ValueError(f'{LABEL}.decode:unsupported-kind={kind}')
            fields.append({'fieldName': member['fieldName'], 'declaredType': member['declaredType'],
                'kind': kind, 'start': at, 'end': reader.pos, **value})
    if reader.pos != end:
        raise ValueError(f'{LABEL}.decode:action-end={reader.pos}; expected={end}')
    return {'schema': 'endfield.buff-merge-target-action-receipt.v1', 'source': source,
        'logicalSha256': digest.upper(), 'tag': tag, 'start': start, 'end': end,
        'typeName': record['runtimeTypeName'], 'namedFields': fields,
        'recursiveStoredSchemaExact': True, 'runtimeMeaningExact': False,
        'nativeProviderSelectionAndExecutionProved': False}
