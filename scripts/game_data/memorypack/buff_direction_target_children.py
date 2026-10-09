"""DirectionSettings source/target references composed on strict original spans."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any, Callable
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.context_audit_memorypack import buff_action_read_order
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError
from scripts.game_data.memorypack import reference_output_sources as references
from scripts.game_data.memorypack import buff_direction_settings_child_receipt as direction

LABEL='buffDirectionTargetChildren'
CONTRACT_PATH=CONTRACTS_DIR/'buff_direction_target_joins_native.json'
DEPTH_LIMIT=64

def _contract():
    c,_=read_reviewed_contract(CONTRACT_PATH,schema='endfield.buff-direction-target-joins-native-contract.v1',status='exact-current-build',label=LABEL)
    if (set(c.get('joins',{}))!={'source','target'} or c.get('sourceContract')!='buff_ec_native.json'
            or any(p['fieldName']!=k or p['declaredType']!='Beyond.Gameplay.Core.TargetSettings' for k,p in c['joins'].items())):
        raise ValueError(f'{LABEL}.contract:shape')
    return c

def _fail(check,expected,actual,**details):
    error=CensusGateError(f'{LABEL}.{check}',source=CONTRACT_PATH.as_posix(),expected=str(expected)[:1024],actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL,**details);raise error

def validate_current_native_contract(*,children:dict[str,Any],gameassembly:Path|None=None,metadata:Path|None=None):
    c=_contract();pins=c['nativeInputs'];gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
    if gate.status!='validated':return {'status':gate.status,'detail':gate.detail,'nativeInputs':pins}
    for key in ('direction','target'):
        if children.get(key,{}).get('status')!='validated' or children[key].get('nativeInputs')!=pins:
            _fail('shared-child',{'name':key,'nativeInputs':pins},children.get(key))
    unity=Path(gate.gameassembly).parent/'UnityPlayer.dll'
    if not unity.is_file() or hashlib.sha256(unity.read_bytes()).hexdigest().upper()!=pins['UnityPlayer.dll']:
        _fail('UnityPlayer.dll',pins['UnityPlayer.dll'],'missing-or-mismatched')
    image=open_native_image(gate.gameassembly,gate.metadata);path=CONTRACTS_DIR/c['sourceContract'];source=json.loads(path.read_bytes())
    buff_action_read_order(image.pe,image.metadata,image.registration,image.instantiations,image.modules,image.owners,source=str(gate.gameassembly),contract_path=path)
    registry=children['direction']['_registry'];plan=registry.plans[children['direction']['directionDefinition']]
    for key,proof in c['joins'].items():
        references.validate_reference_join(image,source,proof,fail=lambda a,b,d:_fail(a,b,d,field=key))
        matches=[m for m in plan if m.name==key and m.kind=='object' and m.ref==children['target']['targetDefinition']]
        if len(matches)!=1 or registry.wrapped_names.get(matches[0].ref)!=proof['declaredType']:
            _fail('derived-child-join',proof['declaredType'],[m.row() for m in matches],field=key)
    after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
    if after.status!='validated':return {'status':after.status,'detail':after.detail,'nativeInputs':pins}
    if hashlib.sha256(unity.read_bytes()).hexdigest().upper()!=pins['UnityPlayer.dll']:_fail('UnityPlayer.dll-after',pins['UnityPlayer.dll'],'mismatched')
    return {'status':'validated','nativeInputs':pins,'targetMembers':list(c['joins']),'evidenceBoundary':c['evidenceBoundary']}

def decode_direction(data,*,source,digest,start,end,children,target_decoder:Callable[...,dict],depth=0):
    c=_contract();proof=children.get('directionTargets',{})
    if (proof.get('status')!='validated' or proof.get('nativeInputs')!=c['nativeInputs']
            or proof.get('targetMembers')!=list(c['joins'])
            or any(children.get(k,{}).get('status')!='validated' or children[k].get('nativeInputs')!=c['nativeInputs'] for k in ('direction','target'))
            or type(depth)is not int or not 0<=depth<=DEPTH_LIMIT):
        raise ValueError(f'{LABEL}.decode:native-or-depth')
    receipt=direction.decode_direction_settings_value(data,source=source,logical_sha256=digest,start=start,end=end,native_validation=children['direction'])
    targets={}
    if receipt['status']!='exact-null':
        members=[m for m in receipt['namedMembers'] if m['kind']=='object']
        if [m['fieldName'] for m in members]!=proof['targetMembers']:raise ValueError(f'{LABEL}.decode:member-plan')
        for member in members:
            a,b=member['start'],member['end']
            if not start<a<b<=end:raise ValueError(f'{LABEL}.decode:strict-child-span')
            if data[a:b]==b'\xff':
                child={'start':a,'end':b,'status':'exact-null','recursiveStoredSchemaExact':True}
            else:
                if depth==DEPTH_LIMIT:raise ValueError(f'{LABEL}.decode:depth-limit')
                if not callable(target_decoder):raise ValueError(f'{LABEL}.decode:target-decoder-required')
                child=target_decoder(data,source,digest,member,children,depth=depth+1)
            if child.get('recursiveStoredSchemaExact')is not True or [child.get('start'),child.get('end')]!=[a,b]:
                raise ValueError(f'{LABEL}.decode:child-incomplete-or-span')
            targets[member['fieldName']]=child
    return {**receipt,'targets':targets,'recursiveStoredSchemaExact':True,'runtimeDirectionKnown':False}
