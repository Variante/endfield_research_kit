"""FinishGlobalBuff parent with a reviewed conditional original-value ID list.

Stored bytes and static default formatters are authenticated independently.
Actual provider returns, blackboard values and finishing effects stay unresolved.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from typing import Any
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.formatter_composition import (
    validate_registered_formatter_composition, validate_source_list_formatter_registration)
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.action_dispatcher import load_action_routes
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack import named_native_records as named
from scripts.game_data.memorypack import buff_global_creation_action as id_owner
from scripts.game_data.memorypack import buff_adding_cooldown as scalar
from scripts.game_data.memorypack.value_wrapper_sources import validate_inline_wrapper_fields
from scripts.game_data.memorypack.corpus_gate import CensusGateError

LABEL='buffFinishGlobalAction'
CONTRACT_PATH=CONTRACTS_DIR/'buff_finish_global_action_native.json'
TAG=3
_KINDS=('byte','scalar32','scalar32','scalar32','byte','scalar-payload','byte','single-payload-list','byte')
_FIELDS=('isEnable','priorityLevel','priorityOffset','serverActionIndex','finishAll','finishCount','finishParent','globalBuffIds','isFinishedEarly')

def _contract() -> dict[str, Any]:
    value,_=read_reviewed_contract(CONTRACT_PATH,schema='endfield.buff-finish-global-action-native-contract.v1',status='exact-current-build',label=LABEL)
    if (value.get('actionDispatch')!={'3':'finishGlobal'}
            or [m['fieldName'] for m in value['record']['members']]!=list(_FIELDS)
            or [m['kind'] for m in value['record']['members']]!=list(_KINDS)
            or value.get('wire')!={'headerMembers':9,'count':'signed-i32-null-minus-one','elementHeaderMembers':1,
                'elementField':'id','elementPayload':'signed-length-raw-bytes','elementNull':'FF-default-ID',
                'runtimeElementBytes':8,'requiredFollowingField':'isFinishedEarly'}
            or value['dependencies']['idOwner']!=id_owner.CONTRACT_PATH.name):
        raise ValueError(f'{LABEL}.contract:shape')
    return value

def supported_tags() -> frozenset[int]:
    _contract();return frozenset((TAG,))

def _members(contract: dict[str, Any]) -> list[dict[str, str]]:
    return [{'fieldName':m['fieldName'],'kind':m['kind']} for m in contract['record']['members']]

def _fail(check: str, expected: Any, actual: Any, **details: Any) -> None:
    error=CensusGateError(f'{LABEL}.{check}',source=CONTRACT_PATH.as_posix(),expected=str(expected)[:1024],actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL,**details)
    error.args=(json.dumps(error.diagnostic,sort_keys=True),);raise error

def _validate_image(image: Any, contract: dict[str, Any]) -> dict[str, Any]:
    parent=contract['record'];source=json.loads((CONTRACTS_DIR/contract['dependencies']['source']).read_bytes())
    fields=named.validate_named_records(image,source,{'finishGlobal':parent},label=LABEL,fail=_fail)['finishGlobal']
    id_contract=id_owner._contract()
    if id_contract['nativeInputs']!=contract['nativeInputs']:
        _fail('ID-owner-inputs',contract['nativeInputs'],id_contract['nativeInputs'])
    record=id_contract['records']['globalBuffId']
    if record['sourceContract']!=contract['dependencies']['idSource']:
        _fail('ID-source-binding',contract['dependencies']['idSource'],record['sourceContract'])
    id_source=json.loads((CONTRACTS_DIR/record['sourceContract']).read_bytes())
    id_fields=validate_inline_wrapper_fields(image,id_source,record,label=LABEL,fail=_fail)
    owner=image.metadata.types[record['runtimeTypeDefinition']]
    size_table=int(image.registration['typeDefinitionsSizes'],16)
    value_bytes=image.pe.u32_at_va(image.pe.u64_at_va(size_table+owner.index*8))-16
    if image.metadata.metadata_type_name(owner.parent_index)!='System.ValueType' or value_bytes!=contract['wire']['runtimeElementBytes']:
        _fail('ID-runtime-value-size',contract['wire']['runtimeElementBytes'],value_bytes)
    flow=contract['listRegistration']
    context=next(c for c in source['nestedContexts'] if c['instructionRva']==parent['members'][7]['sourceContextInstructionRva'])
    if context!=flow['sourceContext'] or flow['elementType']!=record['runtimeTypeName']:
        _fail('list-source-context',context,flow['sourceContext'])
    named.check_typed_context(image,context,parent['members'][7]['declaredType'],label=LABEL,fail=_fail)
    validate_source_list_formatter_registration(image,flow,label=LABEL)
    validate_registered_formatter_composition(image,contract['composition'],label=LABEL)
    image.check_windows(contract['codeWindows'],label=LABEL)
    image.check_instruction_windows(contract['instructionWindows'],label=LABEL)
    entries=GenericEntries(image)
    for selected in contract['genericEntries']:
        actual=entries.resolve(selected['methodDefinition'],selected['classArguments'],selected['methodArguments'])
        if actual['methodSpecIndex']!=selected['methodSpecIndex'] or actual['pointer']!=image.pe.image_base+selected['entryRva']:
            _fail('collection-entry',selected,actual)
    return {'recordMembers':fields,'idRecordMembers':id_fields}

def validate_current_native_contract(*, children: dict[str, Any]) -> dict[str, Any]:
    contract=_contract();pins=contract['nativeInputs']
    gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'])
    if gate.status!='validated':return {'status':gate.status,'detail':gate.detail,'nativeInputs':pins}
    unity=Path(gate.gameassembly).parent/'UnityPlayer.dll'
    if not unity.is_file() or hashlib.sha256(unity.read_bytes()).hexdigest().upper()!=pins['UnityPlayer.dll']:
        return {'status':'mismatched' if unity.is_file() else 'missing','detail':'UnityPlayer.dll missing or mismatched','nativeInputs':pins}
    blackboard=children.get('blackboard',{})
    if blackboard.get('status')!='validated' or blackboard.get('nativeInputs')!=pins:
        _fail('blackboard-gate',{'status':'validated','nativeInputs':pins},blackboard)
    proved=_validate_image(open_native_image(gate.gameassembly,gate.metadata),contract)
    routes,audit=load_action_routes(gameassembly=gate.gameassembly,metadata=gate.metadata);route=routes.get(TAG)
    parent=contract['record']
    if (audit.get('status')!='validated' or route is None or route.status!='resolved'
            or route.wrapper_name!=parent['wrapperTypeName']
            or list(route.member_order)!=list(_FIELDS)
            or list(route.member_declared_types)!=[m['declaredType'] for m in parent['members']]):
        _fail('dispatcher',parent,None if route is None else route.row())
    after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
    if after.status!='validated':return {'status':after.status,'detail':after.detail,'nativeInputs':pins}
    if hashlib.sha256(unity.read_bytes()).hexdigest().upper()!=pins['UnityPlayer.dll']:
        return {'status':'mismatched','detail':'UnityPlayer.dll changed during validation','nativeInputs':pins}
    return {'status':'validated','nativeInputs':pins,**proved,'actionDispatch':contract['actionDispatch'],
            'conditionalDefaultComposition':True,'evidenceBoundary':contract['evidenceBoundary']}

def decode_action(data: bytes, *, source: str, digest: str, start: int, end: int,
                  tag: int, native_validation: dict[str, Any]) -> dict[str, Any]:
    contract=_contract();pins=contract['nativeInputs'];context=native_validation.get('children',{})
    packet=context.get('finishGlobal',{});blackboard=context.get('blackboard',{})
    if (native_validation.get('status')!='validated' or native_validation.get('nativeInputs')!=pins
            or packet.get('status')!='validated' or packet.get('nativeInputs')!=pins
            or packet.get('recordMembers')!=_members(contract)
            or packet.get('idRecordMembers')!=[{'fieldName':'id','kind':'byte-payload'}]
            or packet.get('conditionalDefaultComposition') is not True
            or packet.get('actionDispatch')!=contract['actionDispatch']
            or blackboard.get('status')!='validated' or blackboard.get('nativeInputs')!=pins
            or not isinstance(data,bytes) or not source or not isinstance(digest,str)
            or hashlib.sha256(data).hexdigest().upper()!=digest.upper()
            or type(tag) is not int or tag!=TAG or type(start) is not int or type(end) is not int
            or not 0<=start<end<=len(data)):
        raise ValueError(f'{LABEL}.decode:native-source-or-span')
    reader=Reader(data,source,end);reader.pos=start;reader.nested_union_tag((TAG,),LABEL);fields=[]
    if reader.peek()==255:
        reader.take(1,'null-FinishGlobal')
    else:
        reader.header(len(_FIELDS))
        for member in contract['record']['members']:
            begin=reader.pos;kind=member['kind'];value={}
            if kind in ('byte','scalar32'):
                value['rawHex']=reader.take(1 if kind=='byte' else 4,member['fieldName']).hex().upper()
            elif kind=='scalar-payload':
                reader.scalar_payload()
                child=scalar.decode_adding_cooldown(data,begin,reader.pos,native_validation=blackboard['childNative'])
                if child.get('wholeValueExact') is not True or [child.get('startOffset'),child.get('consumedEnd')]!=[begin,reader.pos]:
                    raise ValueError(f'{LABEL}.decode:finish-count-span')
                value['child']={**child,'start':begin,'end':reader.pos,'recursiveStoredSchemaExact':True}
            else:
                count=reader.count(1,reserve=1,nullable=True);elements=[]
                for _ in range(max(0,count)):
                    at=reader.pos
                    if reader.peek()==255:
                        reader.take(1,'null-GlobalBuffId');element={'start':at,'end':reader.pos,'status':'exact-null-wrapper-default-ID','namedFields':[]}
                    else:
                        reader.header(1);field_start=reader.pos;reader.byte_payload()
                        element={'start':at,'end':reader.pos,'typeName':contract['listRegistration']['elementType'],
                            'namedFields':[{'fieldName':'id','kind':'byte-payload','start':field_start,'end':reader.pos,
                                'rawHex':data[field_start:reader.pos].hex().upper(),'payloadEncoding':'unresolved'}]}
                    elements.append({**element,'recursiveStoredSchemaExact':True})
                value['child']={'start':begin,'end':reader.pos,'count':count,'elements':elements,
                    'conditionalDefaultComposition':True,'recursiveStoredSchemaExact':True}
            fields.append({'fieldName':member['fieldName'],'declaredType':member['declaredType'],
                'kind':kind,'start':begin,'end':reader.pos,**value})
    if reader.pos!=end:raise ValueError(f'{LABEL}.decode:physical-action-end={reader.pos}; expected={end}')
    return {'schema':'endfield.buff-finish-global-action-receipt.v1','source':source,'logicalSha256':digest.upper(),
        'tag':TAG,'start':start,'end':end,'typeName':contract['record']['runtimeTypeName'],'namedFields':fields,
        'conditionalDefaultComposition':True,'recursiveStoredSchemaExact':True,'runtimeMeaningExact':False}
