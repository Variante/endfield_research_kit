"""Custom ability event storage with independently owned string children.

BlackboardString keys and values preserve their original bytes. savedParamKey
additionally uses the current UTF-8 source helper. Event matching and parameter
capture remain unevaluated.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from typing import Any
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.context_audit_memorypack import buff_action_read_order
from scripts.game_data.memorypack.action_dispatcher import load_action_routes
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError
from scripts.game_data.memorypack import named_native_records as named
from scripts.game_data.memorypack import buff_blackboard_string_child_receipt as blackboard_string
from scripts.game_data.memorypack import utf8_source_helper as strings

LABEL = 'buffCustomAbilityEventCondition'
CONTRACT_PATH = CONTRACTS_DIR/'buff_custom_ability_event_condition_native.json'
RECORD = 'customAbilityEvent'


def _contract() -> dict[str, Any]:
    value, _ = read_reviewed_contract(CONTRACT_PATH,
        schema='endfield.buff-custom-ability-event-condition-native-contract.v1',
        status='exact-current-build', label=LABEL)
    if (set(value.get('records', {})) != {RECORD}
            or len(value.get('actionDispatch', {})) != 1
            or set(value['actionDispatch'].values()) != {RECORD}
            or value.get('blackboardStringSourceContract') != blackboard_string.CONTRACT_PATH.name
            or value.get('stringSourceContract') != strings.CONTRACT_PATH.name):
        raise ValueError(f'{LABEL}.contract:shape')
    members = value['records'][RECORD]['members']
    if ([(m['fieldName'],m['kind']) for m in members] != [
            ('isEnable','byte'), ('priorityLevel','scalar32'), ('priorityOffset','scalar32'),
            ('serverActionIndex','scalar32'), ('eventName','pairedPayload'), ('savedParamKey','bytePayload')]
            or value['records'][RECORD].get('inheritedMemberCount') != 4
            or members[4]['declaredType'] != 'Beyond.Blackboard+BlackboardString'
            or members[4].get('sourceContextInstructionRva') is None
            or members[5]['declaredType'] != 'string' or not isinstance(members[5].get('sourceCall'),dict)):
        raise ValueError(f'{LABEL}.contract:typed-members')
    return value


def supported_tags() -> frozenset[int]:
    return frozenset(map(int,_contract()['actionDispatch']))


def _members(contract: dict[str, Any]) -> dict[str, Any]:
    return {key:[{'fieldName':m['fieldName'],'kind':m['kind']} for m in row['members']]
            for key,row in contract['records'].items()}


def _fail(check: str, expected: Any, actual: Any, *, record: str = RECORD, field: str = '') -> None:
    contract = _contract()
    error = CensusGateError(f'{LABEL}.{check}',
        source=(CONTRACTS_DIR/contract['records'][record]['sourceContract']).as_posix(),
        expected=str(expected)[:1024],actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL,record=record,field=field,nativeInputs=contract['nativeInputs'])
    error.args = (json.dumps(error.diagnostic,sort_keys=True),)
    raise error


def validate_current_native_contract(*, children: dict[str, Any]) -> dict[str, Any]:
    contract = _contract(); expected = contract['nativeInputs']
    gate = check_installed_native_inputs(expected['GameAssembly.dll'],expected['global-metadata.dat'])
    if gate.status != 'validated':
        return {'status':gate.status,'detail':gate.detail,'nativeInputs':expected}
    child = children.get('blackboardString',{})
    if (child.get('status') != 'validated' or child.get('nativeInputs') != expected
            or child.get('selectedReadOrder') != list(blackboard_string.READ_ORDER)):
        _fail('blackboard-string-child',list(blackboard_string.READ_ORDER),child)
    unity = Path(gate.gameassembly).parent/'UnityPlayer.dll'
    actual = hashlib.sha256(unity.read_bytes()).hexdigest().upper() if unity.is_file() else 'missing'
    if actual != expected['UnityPlayer.dll']:
        _fail('UnityPlayer.dll',expected['UnityPlayer.dll'],actual)
    string_native = strings.validate_current_native_contract(gameassembly=gate.gameassembly,metadata=gate.metadata)
    if string_native.get('status') != 'validated' or string_native.get('nativeInputs') != expected:
        _fail('string-native',expected,string_native)
    image = open_native_image(gate.gameassembly,gate.metadata)
    record = contract['records'][RECORD]; path = CONTRACTS_DIR/record['sourceContract']
    source = json.loads(path.read_bytes())
    buff_action_read_order(image.pe,image.metadata,image.registration,image.instantiations,
        image.modules,image.owners,source=str(gate.gameassembly),contract_path=path)
    proved = named.validate_named_records(image,source,contract['records'],label=LABEL,fail=_fail)
    helper = record['members'][-1]['sourceCall']['targetRva']
    if helper not in string_native['sourceHelpers']:
        _fail('saved-param-key-source',string_native['sourceHelpers'],helper,field='savedParamKey')
    routes,audit = load_action_routes(gameassembly=gate.gameassembly,metadata=gate.metadata)
    tag = int(next(iter(contract['actionDispatch']))); route = routes.get(tag)
    if (audit.get('status') != 'validated' or route is None or route.status != 'resolved'
            or route.wrapper_name != record['wrapperTypeName']
            or list(route.member_order) != [m['fieldName'] for m in record['members']]
            or list(route.member_declared_types) != [m['declaredType'] for m in record['members']]):
        _fail('dispatcher-members',record['wrapperTypeName'],None if route is None else route.row())
    after = check_installed_native_inputs(expected['GameAssembly.dll'],expected['global-metadata.dat'],
        gameassembly=gate.gameassembly,metadata=gate.metadata)
    if after.status != 'validated':
        return {'status':after.status,'detail':after.detail,'nativeInputs':expected}
    if hashlib.sha256(unity.read_bytes()).hexdigest().upper() != expected['UnityPlayer.dll']:
        _fail('UnityPlayer.dll-after',expected['UnityPlayer.dll'],'mismatched')
    return {'status':'validated','nativeInputs':expected,'recordMembers':proved,
        'actionDispatch':contract['actionDispatch'],'stringNative':string_native,
        'evidenceBoundary':contract['evidenceBoundary']}


def decode_action(data: bytes, *, source: str, digest: str, start: int, end: int, tag: int,
                  native_validation: dict[str, Any]) -> dict[str, Any]:
    contract = _contract(); context = native_validation.get('children',{})
    native = context.get('customAbilityEvent',{}); child_native = context.get('blackboardString',{})
    if (native_validation.get('status') != 'validated' or native.get('status') != 'validated'
            or native_validation.get('nativeInputs') != contract['nativeInputs']
            or native.get('nativeInputs') != contract['nativeInputs']
            or native.get('recordMembers') != _members(contract)
            or native.get('actionDispatch') != contract['actionDispatch']
            or child_native.get('status') != 'validated' or child_native.get('nativeInputs') != contract['nativeInputs']
            or child_native.get('selectedReadOrder') != list(blackboard_string.READ_ORDER)
            or native.get('stringNative',{}).get('status') != 'validated'
            or native.get('stringNative',{}).get('nativeInputs') != contract['nativeInputs']
            or type(tag) is not int or str(tag) not in contract['actionDispatch']
            or not isinstance(data,bytes) or not source or not isinstance(digest,str)
            or hashlib.sha256(data).hexdigest().upper() != digest.upper()
            or type(start) is not int or type(end) is not int or not 0 <= start < end <= len(data)):
        raise ValueError(f'{LABEL}.decode:native-source-or-span')
    reader = Reader(data,source,end); reader.pos = start
    if reader.nested_union_tag((tag,),'custom-ability-event-condition') != tag:
        raise ValueError(f'{LABEL}.decode:physical-tag')
    fields = []; record = contract['records'][RECORD]
    if reader.peek() == 255:
        reader.take(1,'null-condition-wrapper')
    else:
        reader.header(len(record['members']))
        for member in record['members']:
            begin = reader.pos; kind = member['kind']; value = {}
            if kind in ('byte','scalar32'):
                value['rawHex'] = reader.take(1 if kind == 'byte' else 4,member['fieldName']).hex().upper()
            elif kind == 'pairedPayload':
                reader.paired_payload()
                child = blackboard_string.decode_blackboard_string_value(data,source=source,
                    logical_sha256=digest,start=begin,end=reader.pos,native_validation=child_native)
                if child.get('wholeStoredSpanExact') is not True or [child.get('start'),child.get('end')] != [begin,reader.pos]:
                    raise ValueError(f'{LABEL}.decode:event-name-span at={begin}')
                value['child'] = {**child,'recursiveStoredSchemaExact':True}
            elif kind == 'bytePayload':
                reader.byte_payload()
                child = strings.decode_source_string(data,source=source,digest=digest,start=begin,end=reader.pos,
                    source_helper_rva=member['sourceCall']['targetRva'],native_validation=native['stringNative'])
                if child.get('wholeStoredSpanExact') is not True or [child.get('start'),child.get('end')] != [begin,reader.pos]:
                    raise ValueError(f'{LABEL}.decode:saved-param-key-span at={begin}')
                value['child'] = {**child,'recursiveStoredSchemaExact':True}
            else:
                raise ValueError(f'{LABEL}.decode:unsupported-kind={kind}')
            fields.append({'fieldName':member['fieldName'],'declaredType':member['declaredType'],
                'kind':kind,'start':begin,'end':reader.pos,**value})
    if reader.pos != end:
        raise ValueError(f'{LABEL}.decode:condition-end={reader.pos}; expected={end}')
    return {'schema':'endfield.buff-custom-ability-event-condition-receipt.v1','source':source,
        'logicalSha256':digest.upper(),'tag':tag,'typeName':record['runtimeTypeName'],
        'start':start,'end':end,'namedFields':fields,'recursiveStoredSchemaExact':True,'runtimeMeaningExact':False}
