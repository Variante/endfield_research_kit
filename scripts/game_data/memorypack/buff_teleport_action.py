"""Source-bound Teleport stored fields, with separate sequence/scalar/target proofs.

The fourteen-member current layout preserves raw flags and floating bits.
Executed fallback actions, selected destinations and teleport effects remain
outside stored admission. A parent span never supplies a child's proof.
"""
from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path
from typing import Any
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.context_audit_memorypack import buff_action_read_order
from scripts.game_data.memorypack.action_dispatcher import load_action_routes
from scripts.game_data.memorypack.buff_actions import Reader,SEQUENCE_RECURSION_LIMIT
from scripts.game_data.memorypack import named_native_records as named
from scripts.game_data.memorypack import buff_sequence as sequences
from scripts.game_data.memorypack import buff_adding_cooldown as scalars
from scripts.game_data.memorypack import stored_plan_values as stored
from scripts.game_data.memorypack.source_bound_stored_tree import bind_source_named_tree

LABEL='buffTeleportAction'
SCHEMA='endfield.buff-teleport-stored-action-receipt.v1'
CONTRACT_PATH=CONTRACTS_DIR/'buff_teleport_action_native.json'
CHILDREN=('sequence','effectVectors','target','direction','selector','directionTargets','fixedPointFinder')
WIDTHS={'byte':1,'scalar32':4,'raw4':4}


def _contract():
    value,_=read_reviewed_contract(CONTRACT_PATH,schema='endfield.buff-teleport-action-native-contract.v1',
        status='exact-current-build',label=LABEL)
    if set(value.get('records',{}))!={'teleport'} or len(value.get('actionDispatch',{}))!=1:
        raise ValueError(f'{LABEL}.contract:shape')
    record=value['records']['teleport']
    if (len(record['members'])!=14 or record['inheritedMemberCount']!=4
            or set(value['actionDispatch'].values())!={'teleport'}
            or value['childTypes']!={'sequence':sequences.TYPE_NAME,
                'scalar-payload':'Beyond.Blackboard+BlackboardDouble','target':'Beyond.Gameplay.Core.TargetSettings'}):
        raise ValueError(f'{LABEL}.contract:typed-plan')
    for member in record['members']:
        kind=member['kind']
        if kind in value['childTypes']:
            if member['declaredType']!=value['childTypes'][kind] or member.get('sourceContextInstructionRva') is None:
                raise ValueError(f'{LABEL}.contract:typed-child={member["fieldName"]}')
        elif kind not in WIDTHS:
            raise ValueError(f'{LABEL}.contract:unsupported-kind={kind}')
    if (record['members'][4]['fieldName'],record['members'][4]['kind'])!=('actionOnTargetPointInvalid','sequence'):
        raise ValueError(f'{LABEL}.contract:current-sequence-field')
    if (record['members'][-1]['fieldName'],record['members'][-1]['kind'])!=('throughWall','byte'):
        raise ValueError(f'{LABEL}.contract:required-final-byte')
    return value


def supported_tags():
    return frozenset(map(int,_contract()['actionDispatch']))


def _members(contract):
    return {'teleport':[{'fieldName':m['fieldName'],'kind':m['kind']} for m in contract['records']['teleport']['members']]}


def _definitions(contract,children):
    pins=contract['nativeInputs']
    for key in CHILDREN:
        packet=children.get(key,{})
        if packet.get('status')!='validated' or packet.get('nativeInputs')!=pins:
            raise ValueError(f'{LABEL}.native:child-build={key}')
    sequence=children['sequence']
    if sequence.get('typeName')!=sequences.TYPE_NAME or sequence.get('readOrder')!=sequences.READ_ORDER:
        raise ValueError(f'{LABEL}.native:sequence-order')
    scalar=children['effectVectors'].get('scalarNative',{})
    if scalar.get('status')!='validated' or scalar.get('selectedReadOrder')!=['blackboardKey','useBlackboardKey','value']:
        raise ValueError(f'{LABEL}.native:scalar-source-order')
    registry=children['target'].get('_registry')
    if registry is None:raise ValueError(f'{LABEL}.native:source-bound-registry-required')
    definitions={}
    for kind,name in contract['childTypes'].items():
        matches=[definition for definition,wrapped in registry.wrapped_names.items() if wrapped==name]
        if len(matches)!=1:raise ValueError(f'{LABEL}.native:unique-child-definition={kind}')
        definitions[kind]=matches[0]
    if definitions['target']!=children['target'].get('targetDefinition'):
        raise ValueError(f'{LABEL}.native:target-definition')
    return definitions


def validate_current_native_contract(*,children:dict[str,Any],gameassembly:Path|None=None,metadata:Path|None=None):
    contract=_contract();pins=contract['nativeInputs']
    gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],
        gameassembly=gameassembly,metadata=metadata)
    if gate.status!='validated':return {'status':gate.status,'detail':gate.detail,'nativeInputs':pins}
    definitions=_definitions(contract,children)
    unity=Path(gate.gameassembly).parent/'UnityPlayer.dll'
    if not unity.is_file() or hashlib.sha256(unity.read_bytes()).hexdigest().upper()!=pins['UnityPlayer.dll']:
        raise ValueError(f'{LABEL}.native:UnityPlayer.dll')
    image=open_native_image(gate.gameassembly,gate.metadata)
    record=contract['records']['teleport'];source_path=CONTRACTS_DIR/record['sourceContract']
    source=json.loads(source_path.read_bytes())
    source_audit=buff_action_read_order(image.pe,image.metadata,image.registration,image.instantiations,
        image.modules,image.owners,source=str(gate.gameassembly),contract_path=source_path)
    def fail(check,expected,actual,**details):
        raise ValueError(f'{LABEL}.native:{check}:expected={str(expected)[:900]},actual={str(actual)[:900]},details={details}')
    proved=named.validate_named_records(image,source,contract['records'],label=LABEL,fail=fail)
    supplement=json.loads((CONTRACTS_DIR/contract['scalarSourceContract']).read_bytes())
    float_member=next(m for m in record['members'] if m['fieldName']=='maxDistance')
    windows=[w for w in supplement['codeWindows'] if w['startRva']==float_member['sourceCall']['targetRva']]
    if windows!=contract['scalarSourceWindows']:raise ValueError(f'{LABEL}.native:float-source-window')
    image.check_windows(windows,label=LABEL+'.floatSource')
    routes,audit=load_action_routes(gameassembly=gate.gameassembly,metadata=gate.metadata)
    route=routes.get(next(iter(supported_tags())))
    if (audit.get('status')!='validated' or route is None or route.status!='resolved'
            or route.wrapper_name!=record['wrapperTypeName']
            or list(route.member_order)!=[m['fieldName'] for m in record['members']]
            or list(route.member_declared_types)!=[m['declaredType'] for m in record['members']]):
        raise ValueError(f'{LABEL}.native:current-dispatcher-and-members')
    after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],
        gameassembly=gate.gameassembly,metadata=gate.metadata)
    if after.status!='validated':return {'status':after.status,'detail':after.detail,'nativeInputs':pins}
    if hashlib.sha256(unity.read_bytes()).hexdigest().upper()!=pins['UnityPlayer.dll']:
        raise ValueError(f'{LABEL}.native:UnityPlayer.dll-after')
    return {'status':'validated','nativeInputs':pins,'recordMembers':proved,
        'actionDispatch':contract['actionDispatch'],'childDefinitions':definitions,
        'sourceAudit':source_audit,'evidenceBoundary':contract['evidenceBoundary']}


def decode_action(data:bytes,*,source:str,digest:str,start:int,end:int,tag:int,
                  native_validation:dict[str,Any],depth:int=0,target_decoder=None):
    contract=_contract();pins=contract['nativeInputs'];children=native_validation.get('children',{})
    packet=children.get('teleport',{})
    if (native_validation.get('status')!='validated' or native_validation.get('nativeInputs')!=pins
            or packet.get('status')!='validated' or packet.get('nativeInputs')!=pins
            or packet.get('recordMembers')!=_members(contract) or packet.get('actionDispatch')!=contract['actionDispatch']
            or type(tag) is not int or str(tag) not in contract['actionDispatch']
            or not isinstance(data,bytes) or not source or not isinstance(digest,str)
            or hashlib.sha256(data).hexdigest().upper()!=digest.upper()
            or type(start) is not int or type(end) is not int or not 0<=start<end<=len(data)):
        raise ValueError(f'{LABEL}.decode:native-source-or-span')
    if type(depth) is not int or not 0<=depth<=SEQUENCE_RECURSION_LIMIT:
        raise ValueError(f'{LABEL}.decode:depth-limit')
    definitions=_definitions(contract,children)
    if definitions!=packet.get('childDefinitions'):raise ValueError(f'{LABEL}.decode:child-definition-drift')
    record=contract['records']['teleport'];reader=Reader(data,source,end);reader.pos=start
    if reader.nested_union_tag((tag,),'teleport-action')!=tag:
        raise ValueError(f'{LABEL}.decode:physical-tag')
    fields=[];null=reader.peek()==255
    if null:reader.take(1,'null-teleport-wrapper')
    else:
        reader.header(len(record['members']))
        for member in record['members']:
            begin=reader.pos;kind=member['kind'];child=None;binding=None
            if kind in WIDTHS:
                tree=stored.fixed_node(reader.take(WIDTHS[kind],member['fieldName']))
            else:
                if kind=='sequence':
                    reader.sequence(depth+1)
                    child=sequences.decode_value(data,source,digest,begin,reader.pos,native_validation,depth+1)
                    if child.get('status')!='exact-null':
                        flags=child['flags']
                        if [flag['name'] for flag in flags]!=sequences.READ_ORDER[1:] or len(flags)!=2:
                            raise ValueError(f'{LABEL}.decode:source-sequence-flags')
                        child={**child,'namedFields':[{'fieldName':sequences.READ_ORDER[0],
                            'start':begin+1,'end':flags[0]['start']},
                            *[{'fieldName':flag['name'],'start':flag['start'],'end':flag['end'],
                                'rawByte':flag['rawByte']} for flag in flags]]}
                elif kind=='scalar-payload':
                    reader.scalar_payload()
                    scalar=scalars.decode_adding_cooldown(data,begin,reader.pos,
                        native_validation=children['effectVectors']['scalarNative'])
                    child={**scalar,'start':scalar['startOffset'],'end':scalar['consumedEnd'],
                        'recursiveStoredSchemaExact':scalar.get('wholeValueExact') is True}
                elif kind=='target':
                    reader.target_profile()
                    if data[begin:reader.pos]==b'\xff':
                        child={'start':begin,'end':reader.pos,'status':'exact-null','recursiveStoredSchemaExact':True}
                    else:
                        if target_decoder is None:
                            from scripts.game_data.memorypack.buff_recursive_actions import recursive_target
                            target_decoder=recursive_target
                        child=target_decoder(data,source,digest,{'start':begin,'end':reader.pos,
                            'fieldName':member['fieldName']},children,depth=depth)
                else:raise ValueError(f'{LABEL}.decode:unsupported-child={kind}')
                if child.get('recursiveStoredSchemaExact') is not True or [child.get('start'),child.get('end')]!=[begin,reader.pos]:
                    raise ValueError(f'{LABEL}.decode:incomplete-child-or-span={member["fieldName"]}')
                tree=stored.decode_stored_plan(data,source=source,digest=digest,start=begin,end=reader.pos,
                    definition=definitions[kind],registry=children['target']['_registry'])['storedTree']
                if kind=='sequence' and child.get('status')!='exact-null':
                    if tree['members'][0]['value'].get('count')!=child['count']:
                        raise ValueError(f'{LABEL}.decode:source-sequence-array-count')
                binding=bind_source_named_tree(child,tree)
            if stored.encode_stored_node(tree)!=data[begin:reader.pos]:
                raise ValueError(f'{LABEL}.decode:field-reencode={member["fieldName"]}')
            fields.append({'fieldName':member['fieldName'],'declaredType':member['declaredType'],'kind':kind,
                'start':begin,'end':reader.pos,'storedValue':tree,'nativeChildReceipt':child,'sourceTreeBinding':binding})
    if reader.pos!=end:raise ValueError(f'{LABEL}.decode:required-action-end:expected={end},actual={reader.pos}')
    receipt={'schema':SCHEMA,'source':source,'logicalSha256':digest.upper(),'tag':tag,
        'typeName':record['runtimeTypeName'],'start':start,'end':end,'null':null,'namedFields':fields,
        'recursiveStoredSchemaExact':True,'runtimeMeaningExact':False}
    if encode_action(receipt)!=data[start:end]:raise ValueError(f'{LABEL}.decode:whole-action-reencode')
    return receipt


def encode_action(receipt):
    contract=_contract();tag=receipt['tag'];fields=receipt['namedFields']
    if type(tag) is not int or str(tag) not in contract['actionDispatch']:
        raise ValueError(f'{LABEL}.encode:current-tag')
    prefix=bytes((tag,)) if tag<250 else b'\xfa'+struct.pack('<H',tag)
    if receipt.get('null') is True:
        if fields:raise ValueError(f'{LABEL}.encode:null-fields')
        return prefix+b'\xff'
    members=contract['records']['teleport']['members']
    if [(field['fieldName'],field['kind']) for field in fields]!=[(m['fieldName'],m['kind']) for m in members]:
        raise ValueError(f'{LABEL}.encode:every-current-field-required')
    return prefix+bytes((len(members),))+b''.join(stored.encode_stored_node(field['storedValue']) for field in fields)
