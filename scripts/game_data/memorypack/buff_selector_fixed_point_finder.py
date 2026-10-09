"""Named FixedPointFinder with explicit inline geometry source programs.

Position and rotation retain twelve and sixteen original bytes. The radius
uses its independent BlackboardDouble reader. No selected point is evaluated.
"""
from __future__ import annotations
import hashlib
import json
import struct
from pathlib import Path
from typing import Any
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.context_audit_memorypack import buff_action_read_order
from scripts.game_data.memorypack import named_native_records as named
from scripts.game_data.memorypack import buff_adding_cooldown as scalar
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError

LABEL='buffSelectorFixedPoint'
CONTRACT_PATH=CONTRACTS_DIR/'buff_selector_fixed_point_finder_native.json'

def _contract() -> dict[str,Any]:
    c,_=read_reviewed_contract(CONTRACT_PATH,schema='endfield.buff-selector-fixed-point-native-contract.v1',status='exact-current-build',label=LABEL)
    if (set(c.get('records',{}))!={'fixedPointFinder'} or c.get('sourceContract')!='buff_119_native.json'
            or type(c.get('dispatcher',{}).get('unionTag')) is not int
            or [m['fieldName'] for m in c['records']['fixedPointFinder']['members']]!=['positionOffset','rotationOffset','sampleRadius','snapToNavmesh']
            or [m['declaredType'] for m in c['records']['fixedPointFinder']['members']]!=['UnityEngine.Vector3','UnityEngine.Quaternion',scalar._contract()['rootContextType'],'bool']
            or c['records']['fixedPointFinder']['members'][2].get('sourceContextInstructionRva') is None):
        raise ValueError(f'{LABEL}.contract:shape')
    return c

def _members(c: dict[str,Any]) -> dict[str,Any]:
    return {k:[{'fieldName':m['fieldName'],'kind':m['kind']} for m in r['members']] for k,r in c['records'].items()}

def _fail(check: str,expected: Any,actual: Any,**details: Any) -> None:
    error=CensusGateError(f'{LABEL}.{check}',source=CONTRACT_PATH.as_posix(),expected=str(expected)[:1024],actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL,nativeInputs=_contract()['nativeInputs'],**details)
    raise error

def validate_current_native_contract(*,selector_native: dict[str,Any],vector_native: dict[str,Any],
        gameassembly: Path|None=None,metadata: Path|None=None) -> dict[str,Any]:
    c=_contract();pins=c['nativeInputs']
    gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
    if gate.status!='validated':return {'status':gate.status,'detail':gate.detail,'nativeInputs':pins}
    for name,child in (('selector',selector_native),('effectVectors',vector_native)):
        if child.get('status')!='validated' or child.get('nativeInputs')!=pins:_fail('shared-child',pins,{'name':name,'status':child.get('status'),'nativeInputs':child.get('nativeInputs')})
    scalar_native=vector_native.get('scalarNative',{})
    if (scalar._contract()['nativeInputs']!=pins or scalar_native.get('status')!='validated'
            or scalar_native.get('sourceStoreValidated') is not True or scalar_native.get('selectedReadOrder')!=scalar._contract()['selectedReadOrder']):
        _fail('scalar-native','selected outer native gate and scalar source/destination read order',scalar_native)
    unity=Path(gate.gameassembly).parent/'UnityPlayer.dll'
    if not unity.is_file() or hashlib.sha256(unity.read_bytes()).hexdigest().upper()!=pins['UnityPlayer.dll']:_fail('UnityPlayer.dll',pins['UnityPlayer.dll'],'missing-or-mismatched')
    image=open_native_image(gate.gameassembly,gate.metadata);source_path=CONTRACTS_DIR/c['sourceContract'];source=json.loads(source_path.read_bytes())
    buff_action_read_order(image.pe,image.metadata,image.registration,image.instantiations,image.modules,image.owners,source=str(gate.gameassembly),contract_path=source_path)
    proved=named.validate_named_records(image,source,c['records'],label=LABEL,fail=_fail)
    dispatch=c['dispatcher'];route=image.validate_dispatcher(dispatch,label=LABEL)
    image.check_instruction_windows([dispatch['typeLoadInstruction']],label=LABEL)
    rva,hex_value=dispatch['typeLoadInstruction'];raw=bytes.fromhex(hex_value)
    if len(raw)!=7 or raw[:3]!=b'\x48\x8b\x15' or image.pe.image_base+rva+7+struct.unpack_from('<i',raw,3)[0]!=route['usageCell']:
        _fail('route-type-load',route['usageCell'],dispatch['typeLoadInstruction'])
    registry=selector_native['_registry'];record=c['records']['fixedPointFinder']
    finder=[m for m in registry.plans[selector_native['selectorDefinition']] if m.name=='finderData' and m.kind=='union']
    if (len(finder)!=1 or registry.union_tag_maps.get(finder[0].ref,{}).get(dispatch['unionTag'])!=record['wrapperTypeDefinition']
            or registry.wrapped_names.get(record['wrapperTypeDefinition'])!=record['runtimeTypeName']):
        _fail('selector-parent-route',record['runtimeTypeName'],record['wrapperTypeDefinition'])
    after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
    if after.status!='validated':return {'status':after.status,'detail':after.detail,'nativeInputs':pins}
    if hashlib.sha256(unity.read_bytes()).hexdigest().upper()!=pins['UnityPlayer.dll']:_fail('UnityPlayer.dll-after',pins['UnityPlayer.dll'],'mismatched')
    return {'status':'validated','nativeInputs':pins,'unionTag':dispatch['unionTag'],'recordMembers':proved,'evidenceBoundary':c['evidenceBoundary']}

def finder_tags() -> frozenset[int]:
    return frozenset((_contract()['dispatcher']['unionTag'],))

def decode_finder(data: bytes,*,source: str,digest: str,start: int,end: int,context: dict[str,Any]) -> dict[str,Any]:
    c=_contract();native=context.get('fixedPointFinder',{});tag=c['dispatcher']['unionTag'];vector=context.get('effectVectors',{})
    scalar_native=vector.get('scalarNative',{})
    if (native.get('status')!='validated' or native.get('nativeInputs')!=c['nativeInputs'] or native.get('unionTag')!=tag or native.get('recordMembers')!=_members(c)
            or vector.get('status')!='validated' or vector.get('nativeInputs')!=c['nativeInputs']
            or scalar._contract()['nativeInputs']!=c['nativeInputs'] or scalar_native.get('status')!='validated'
            or scalar_native.get('sourceStoreValidated') is not True or scalar_native.get('selectedReadOrder')!=scalar._contract()['selectedReadOrder']
            or not isinstance(data,bytes) or not source or not isinstance(digest,str) or hashlib.sha256(data).hexdigest().upper()!=digest.upper()
            or type(start) is not int or type(end) is not int or not 0<=start<end<=len(data)):
        raise ValueError(f'{LABEL}.decode:native-source-or-span')
    reader=Reader(data,source,end);reader.pos=start;selected=reader.nested_union_tag((tag,),'fixed-point-finder');fields=[]
    if selected is None:status='exact-null-union'
    elif reader.peek()==255:reader.take(1,'null-finder-wrapper');status='exact-null-wrapper'
    else:
        record=c['records']['fixedPointFinder'];reader.header(len(record['members']));status='named-finder-exact-span'
        for m in record['members']:
            begin=reader.pos;kind=m['kind'];value={}
            if kind in ('byte','raw12','raw16'):value['rawHex']=reader.take({'byte':1,'raw12':12,'raw16':16}[kind],m['fieldName']).hex().upper()
            elif kind=='scalarPayload':
                reader.scalar_payload();child=scalar.decode_adding_cooldown(data,begin,reader.pos,native_validation=scalar_native)
                if child.get('wholeValueExact') is not True or [child.get('startOffset'),child.get('consumedEnd')]!=[begin,reader.pos]:
                    raise ValueError(f'{LABEL}.decode:scalar-span at={begin}')
                value['child']={**child,'start':begin,'end':reader.pos,'recursiveStoredSchemaExact':True}
            else:raise ValueError(f'{LABEL}.decode:unsupported-kind={kind}')
            fields.append({'fieldName':m['fieldName'],'declaredType':m['declaredType'],'kind':kind,'start':begin,'end':reader.pos,**value})
    if reader.pos!=end:raise ValueError(f'{LABEL}.decode:finder-end={reader.pos}; expected={end}')
    return {'source':source,'logicalSha256':digest.upper(),'start':start,'end':end,'tag':selected,'status':status,
        'typeName':c['records']['fixedPointFinder']['runtimeTypeName'],'namedFields':fields,'recursiveStoredSchemaExact':True,'runtimeMeaningExact':False}
