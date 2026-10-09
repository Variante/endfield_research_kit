"""Named SetAnimatorParam storage with two independent five-member children.

Raw floats and parameter enum values are retained. The end and primary
parameter records keep separate null states; no animator effects are claimed.
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

LABEL='buffAnimatorParamAction'
CONTRACT_PATH=CONTRACTS_DIR/'buff_animator_param_action_native.json'

def _contract() -> dict[str, Any]:
    c,_=read_reviewed_contract(CONTRACT_PATH,schema='endfield.buff-animator-param-action-native-contract.v1',status='exact-current-build',label=LABEL)
    if (set(c.get('records',{}))!={'setAnimatorParam','animatorParam'} or c.get('actionDispatch')!={'330':'setAnimatorParam'}
            or c.get('childTypes')!={'animator-param-profile':'Beyond.Gameplay.Core.AnimatorParamAction'}
            or [m['fieldName'] for m in c['records']['setAnimatorParam']['members']]!=[
                'isEnable','priorityLevel','priorityOffset','serverActionIndex','actionOnEnd','endAction','paramAction','paramName']
            or [m['fieldName'] for m in c['records']['animatorParam']['members']]!=[
                'animatorParam','boolValue','floatValue','intValue','paramType']
            or c['records']['animatorParam']['members'][-1]['declaredType']!='UnityEngine.AnimatorControllerParameterType'):
        raise ValueError(f'{LABEL}.contract:shape')
    for m in c['records']['setAnimatorParam']['members']:
        if m['kind'] in c['childTypes'] and (m['declaredType']!=c['childTypes'][m['kind']] or m.get('sourceContextInstructionRva') is None):
            raise ValueError(f'{LABEL}.contract:typed-child={m["fieldName"]}')
    return c

def supported_tags() -> frozenset[int]:
    return frozenset(map(int,_contract()['actionDispatch']))

def _members(c: dict[str, Any]) -> dict[str, Any]:
    return {k:[{'fieldName':m['fieldName'],'kind':m['kind']} for m in r['members']] for k,r in c['records'].items()}

def _fail(check: str,expected: Any,actual: Any,**details: Any) -> None:
    error=CensusGateError(f'{LABEL}.{check}',source=CONTRACT_PATH.as_posix(),expected=str(expected)[:1024],actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL,nativeInputs=_contract()['nativeInputs'],**details)
    raise error

def validate_current_native_contract(*,gameassembly: Path|None=None,metadata: Path|None=None) -> dict[str, Any]:
    c=_contract();pins=c['nativeInputs']
    gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
    if gate.status!='validated':return {'status':gate.status,'detail':gate.detail,'nativeInputs':pins}
    unity=Path(gate.gameassembly).parent/'UnityPlayer.dll'
    if not unity.is_file() or hashlib.sha256(unity.read_bytes()).hexdigest().upper()!=pins['UnityPlayer.dll']:
        _fail('UnityPlayer.dll',pins['UnityPlayer.dll'],'missing-or-mismatched')
    image=open_native_image(gate.gameassembly,gate.metadata)
    source_path=CONTRACTS_DIR/c['records']['setAnimatorParam']['sourceContract'];source=json.loads(source_path.read_bytes())
    if c['records']['animatorParam']['sourceContract']!=source_path.name:
        _fail('source-family',source_path.name,c['records']['animatorParam']['sourceContract'])
    buff_action_read_order(image.pe,image.metadata,image.registration,image.instantiations,image.modules,image.owners,
        source=str(gate.gameassembly),contract_path=source_path)
    proved=named.validate_named_records(image,source,c['records'],label=LABEL,fail=_fail)
    routes,audit=load_action_routes(gameassembly=gate.gameassembly,metadata=gate.metadata)
    record=c['records']['setAnimatorParam'];route=routes.get(next(iter(supported_tags())))
    if (audit.get('status')!='validated' or route is None or route.status!='resolved' or route.wrapper_name!=record['wrapperTypeName']
            or list(route.member_order)!=[m['fieldName'] for m in record['members']]
            or list(route.member_declared_types)!=[m['declaredType'] for m in record['members']]):
        _fail('dispatcher-members',record['wrapperTypeName'],None if route is None else route.row())
    after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
    if after.status!='validated':return {'status':after.status,'detail':after.detail,'nativeInputs':pins}
    if hashlib.sha256(unity.read_bytes()).hexdigest().upper()!=pins['UnityPlayer.dll']:_fail('UnityPlayer.dll-after',pins['UnityPlayer.dll'],'mismatched')
    return {'status':'validated','nativeInputs':pins,'recordMembers':proved,'actionDispatch':c['actionDispatch'],'evidenceBoundary':c['evidenceBoundary']}

def decode_action(data: bytes,*,source: str,digest: str,start: int,end: int,tag: int,native_validation: dict[str, Any]) -> dict[str, Any]:
    c=_contract();native=native_validation.get('children',{}).get('animatorParamAction',{})
    if (native_validation.get('status')!='validated' or native.get('status')!='validated'
            or native_validation.get('nativeInputs')!=c['nativeInputs'] or native.get('nativeInputs')!=c['nativeInputs']
            or native.get('recordMembers')!=_members(c) or native.get('actionDispatch')!=c['actionDispatch']
            or str(tag) not in c['actionDispatch'] or not isinstance(data,bytes) or not source or not isinstance(digest,str)
            or hashlib.sha256(data).hexdigest().upper()!=digest.upper()
            or type(start) is not int or type(end) is not int or not 0<=start<end<=len(data)):
        raise ValueError(f'{LABEL}.decode:native-source-or-span')
    reader=Reader(data,source,end);reader.pos=start
    if reader.nested_union_tag((tag,),'animator-param-action')!=tag:raise ValueError(f'{LABEL}.decode:physical-tag')
    def record(key: str) -> dict[str, Any]:
        at=reader.pos;plan=c['records'][key];fields=[]
        if reader.peek()==255:
            reader.take(1,'null-'+key)
            return {'start':at,'end':reader.pos,'status':'exact-null-wrapper','namedFields':[],'recursiveStoredSchemaExact':True}
        reader.header(len(plan['members']))
        for m in plan['members']:
            begin=reader.pos;kind=m['kind'];value={}
            if kind in ('byte','scalar32','raw4'):value['rawHex']=reader.take(1 if kind=='byte' else 4,m['fieldName']).hex().upper()
            elif kind=='byte-payload':
                reader.byte_payload();value.update(rawHex=data[begin:reader.pos].hex().upper(),payloadEncoding='unresolved')
            elif kind=='animator-param-profile':value['child']=record('animatorParam')
            else:raise ValueError(f'{LABEL}.decode:unsupported-kind={kind}')
            fields.append({'fieldName':m['fieldName'],'declaredType':m['declaredType'],'kind':kind,'start':begin,'end':reader.pos,**value})
        return {'start':at,'end':reader.pos,'typeName':plan['runtimeTypeName'],'status':'named-record-exact-span','namedFields':fields,'recursiveStoredSchemaExact':True}
    parent=record('setAnimatorParam')
    if reader.pos!=end:raise ValueError(f'{LABEL}.decode:action-end={reader.pos}; expected={end}')
    return {'schema':'endfield.buff-animator-param-action-receipt.v1','source':source,'logicalSha256':digest.upper(),'tag':tag,'start':start,'end':end,
        'typeName':c['records']['setAnimatorParam']['runtimeTypeName'],'parent':parent,'recursiveStoredSchemaExact':True,'runtimeMeaningExact':False}
