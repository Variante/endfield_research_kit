"""Named camera-control configuration and independently owned curve/list joins.

Stored configuration does not establish a camera change, lifecycle or custom
action result. Shared string bytes retain their conditional decoder boundary.
"""
from __future__ import annotations
import hashlib,json,struct
from pathlib import Path
from typing import Any
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.context_audit_memorypack import buff_action_read_order
from scripts.game_data.memorypack import named_native_records as named,animation_curve as curves
from scripts.game_data.memorypack.action_dispatcher import load_action_routes
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError

LABEL='buffCameraControlStateAction';CONTRACT_PATH=CONTRACTS_DIR/'buff_camera_control_state_action_native.json'
CHILDREN=('animationCurve','findSettings')

def _contract():
    c,_=read_reviewed_contract(CONTRACT_PATH,schema='endfield.buff-camera-control-state-action-native-contract.v1',status='exact-current-build',label=LABEL)
    if (set(c.get('records',{}))!={'cameraControlState'} or set(c.get('actionDispatch',{}).values())!={'cameraControlState'}
            or len(c['actionDispatch'])!=1 or len(c['records']['cameraControlState']['members'])!=23
            or c.get('curveFormatterReference')!={'contract':'memorypack_animation_curve_native.json'}
            or c.get('stringListReference')!={'contract':'buff_find_settings_child_native.json','contextName':'buffIdList'}):
        raise ValueError(f'{LABEL}.contract:shape')
    return c

def supported_tags():return frozenset(map(int,_contract()['actionDispatch']))
def _members(c):return {k:[{'fieldName':m['fieldName'],'kind':m['kind']} for m in r['members']] for k,r in c['records'].items()}
def _fail(check,expected,actual,**details):
    error=CensusGateError(f'{LABEL}.{check}',source=CONTRACT_PATH.as_posix(),expected=str(expected)[:1024],actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL,**details);raise error

def validate_current_native_contract(*,children:dict[str,Any],gameassembly:Path|None=None,metadata:Path|None=None):
    c=_contract();pins=c['nativeInputs'];gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
    if gate.status!='validated':return {'status':gate.status,'detail':gate.detail,'nativeInputs':pins}
    for key in CHILDREN:
        if children.get(key,{}).get('status')!='validated' or children[key].get('nativeInputs')!=pins:_fail('shared-child',key,children.get(key))
    unity=Path(gate.gameassembly).parent/'UnityPlayer.dll'
    if not unity.is_file() or hashlib.sha256(unity.read_bytes()).hexdigest().upper()!=pins['UnityPlayer.dll']:_fail('UnityPlayer.dll',pins['UnityPlayer.dll'],'missing-or-mismatched')
    image=open_native_image(gate.gameassembly,gate.metadata);record=c['records']['cameraControlState']
    source_path=CONTRACTS_DIR/record['sourceContract'];source=json.loads(source_path.read_bytes())
    buff_action_read_order(image.pe,image.metadata,image.registration,image.instantiations,image.modules,image.owners,source=str(gate.gameassembly),contract_path=source_path)
    proved=named.validate_named_records(image,source,c['records'],label=LABEL,fail=_fail)
    curve=curves.formatter_curve_type(image)
    for name in ('blendInCustomCurve','blendOutCustomCurve'):
        member=next(m for m in record['members'] if m['fieldName']==name)
        context=next(v for v in source['nestedContexts'] if v['instructionRva']==member['sourceContextInstructionRva'])
        if context['typeDefinition']!=curve['typeDefinition'] or member['declaredType']!=curve['typeName']:
            _fail('curve-child-type',curve,context,field=name)
    ref=c['stringListReference'];find_contract=json.loads((CONTRACTS_DIR/ref['contract']).read_bytes())
    if find_contract['nativeInputs']!=pins:_fail('string-list-reference-build',pins,find_contract['nativeInputs'])
    shared_path=CONTRACTS_DIR/find_contract['sourceReaderContract'];shared=json.loads(shared_path.read_bytes())
    shared_context=next(v for v in shared['nestedContexts'] if v['instructionRva']==find_contract['contextRvas'][ref['contextName']])
    member=next(m for m in record['members'] if m['fieldName']=='inheritSkillIds')
    context=next(v for v in source['nestedContexts'] if v['instructionRva']==member['sourceContextInstructionRva'])
    declared='System.Collections.Generic.List`1<string>'
    named.check_typed_context(image,shared_context,declared,label=LABEL,fail=_fail)
    named.check_typed_context(image,context,declared,label=LABEL,fail=_fail)
    if any(context[k]!=shared_context[k] for k in ('methodSpec','argumentRawHex','typeDefinition')):
        _fail('string-list-closed-context',shared_context,context)
    # Check the same physical shared call, not only the two declared types.
    first=find_contract['children'][0]['fields'][0]['store'][0]
    at=shared_context['instructionRva']+len(bytes.fromhex(shared_context['instructionHex']))
    code=image.pe.bytes_at_va(image.pe.image_base+at,first-at)
    instructions=image.mapper.decode_x64_subset(code,image.pe.image_base+at,stop_offset=len(code))
    calls=[r for r in instructions if len(bytes.fromhex(r['bytes']))==5 and bytes.fromhex(r['bytes'])[0]==0xe8]
    if not calls:_fail('string-list-shared-call','one bounded call before its independently proved store',instructions)
    call=calls[0];raw=bytes.fromhex(call['bytes']);target=int(call['va'],16)-image.pe.image_base+5+struct.unpack_from('<i',raw,1)[0]
    if target!=member['sourceCall']['targetRva']:_fail('string-list-physical-source',member['sourceCall']['targetRva'],target)
    routes,audit=load_action_routes(gameassembly=gate.gameassembly,metadata=gate.metadata)
    route=routes.get(next(iter(supported_tags())))
    if (audit.get('status')!='validated' or route is None or route.status!='resolved' or route.wrapper_name!=record['wrapperTypeName']
            or list(route.member_order)!=[m['fieldName'] for m in record['members']]
            or list(route.member_declared_types)!=[m['declaredType'] for m in record['members']]):
        _fail('dispatcher-members',record['wrapperTypeName'],None if route is None else route.row())
    after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
    if after.status!='validated':return {'status':after.status,'detail':after.detail,'nativeInputs':pins}
    if hashlib.sha256(unity.read_bytes()).hexdigest().upper()!=pins['UnityPlayer.dll']:_fail('UnityPlayer.dll-after',pins['UnityPlayer.dll'],'mismatched')
    return {'status':'validated','nativeInputs':pins,'recordMembers':proved,'actionDispatch':c['actionDispatch'],
            'curveTypeDefinition':curve['typeDefinition'],'stringListContextJoined':True,'evidenceBoundary':c['evidenceBoundary']}

def decode_action(data:bytes,*,source:str,digest:str,start:int,end:int,tag:int,native_validation:dict[str,Any]):
    c=_contract();children=native_validation.get('children',{});proof=children.get('cameraControlState',{})
    if (native_validation.get('status')!='validated' or native_validation.get('nativeInputs')!=c['nativeInputs']
            or proof.get('status')!='validated' or proof.get('nativeInputs')!=c['nativeInputs'] or proof.get('recordMembers')!=_members(c)
            or proof.get('actionDispatch')!=c['actionDispatch'] or proof.get('stringListContextJoined')is not True
            or any(children.get(k,{}).get('status')!='validated' or children[k].get('nativeInputs')!=c['nativeInputs'] for k in CHILDREN)
            or not isinstance(data,bytes) or not source or not isinstance(digest,str) or hashlib.sha256(data).hexdigest().upper()!=digest.upper()
            or type(start)is not int or type(end)is not int or not 0<=start<end<=len(data) or str(tag)not in c['actionDispatch']):
        raise ValueError(f'{LABEL}.decode:native-source-or-span')
    reader=Reader(data,source,end);reader.pos=start
    if reader.nested_union_tag((tag,),'camera-control-state')!=tag:raise ValueError(f'{LABEL}.decode:physical-tag')
    plan=c['records']['cameraControlState'];fields=[]
    if reader.peek()==255:reader.take(1,'null-camera-control-state');status='exact-null-wrapper'
    else:
        reader.header(len(plan['members']));status='named-camera-control-state-exact-span'
        for member in plan['members']:
            at=reader.pos;kind=member['kind'];value={}
            if kind in ('byte','scalar32','raw4'):value['rawHex']=reader.take(1 if kind=='byte' else 4,member['fieldName']).hex().upper()
            elif kind=='byte-payload':
                reader.byte_payload();value.update(rawHex=data[at:reader.pos].hex().upper(),payloadEncoding='unresolved')
            elif kind=='curve-profile':
                reader.curve_profile();value['child']=curves.decode_curve(data,source=source,digest=digest,start=at,end=reader.pos,native_validation=children['animationCurve'])
            elif kind=='nullable-byte-payload-list':
                count=reader.count(4,reserve=6,nullable=True);items=[]
                for _ in range(max(0,count)):
                    begin=reader.pos;reader.byte_payload()
                    items.append({'start':begin,'end':reader.pos,'rawHex':data[begin:reader.pos].hex().upper(),
                                  'payloadEncoding':'unresolved','recursiveStoredSchemaExact':True})
                value['child']={'start':at,'end':reader.pos,'count':count,'elements':items,'recursiveStoredSchemaExact':True,
                                'grammarEvidenceBoundary':'conditional','liveProviderSelectionKnown':False,'decoderParityKnown':False}
            else:raise ValueError(f'{LABEL}.decode:unsupported-kind={kind}')
            if 'child' in value and (value['child'].get('recursiveStoredSchemaExact')is not True
                    or [value['child'].get('start'),value['child'].get('end')]!=[at,reader.pos]):raise ValueError(f'{LABEL}.decode:child-span={member["fieldName"]}')
            fields.append({'fieldName':member['fieldName'],'declaredType':member['declaredType'],'kind':kind,'start':at,'end':reader.pos,**value})
    if reader.pos!=end:raise ValueError(f'{LABEL}.decode:action-end={reader.pos}; expected={end}')
    return {'schema':'endfield.buff-camera-control-state-action-receipt.v1','source':source,'logicalSha256':digest.upper(),'tag':tag,
            'start':start,'end':end,'status':status,'typeName':plan['runtimeTypeName'],'namedFields':fields,
            'recursiveStoredSchemaExact':True,'runtimeCameraEffectKnown':False,'runtimeActionResultKnown':False}
