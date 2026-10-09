"""DamageUnit-owned nullable processor lists with independent leaf receipts.

The typed owner/source join is direct. The shared reference-list formatter's
wire program is conditional on formatter selection; original owner spans and
complete following fields are required by callers before root admission.
No modifier root is fabricated, and stored operands do not prove mutations.
"""
from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path, PurePosixPath
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack import named_native_records as named
from scripts.game_data.memorypack import buff_damage_modifier_receipt as modifier
from scripts.game_data.memorypack import buff_damage_scalar_processor_child_receipt as scalar
from scripts.game_data.memorypack import buff_damage_scale_processor_child_receipt as scale
from scripts.game_data.memorypack import buff_damage_text_processor_child_receipt as text
from scripts.game_data.memorypack import buff_damage_instant_modify_attribute_processor_receipt as instant
from scripts.game_data.memorypack import buff_damage_modify_calc_result_processor_child_receipt as modify_calc

LABEL='buffDamageProcessorCollection'
CONTRACT_PATH=CONTRACTS_DIR/'buff_damage_processor_collection_native.json'
LEAVES={'scalar':scalar,'scale':scale,'text':text,'instant':instant,'modifyCalc':modify_calc}


def _contract() -> dict[str, Any]:
    value,_=read_reviewed_contract(CONTRACT_PATH,
        schema='endfield.buff-damage-processor-collection-native-contract.v1',
        status='exact-current-build',label=LABEL)
    if (value.get('owner')!={'record':'unit','sourceMemberIndex':8,'fieldName':'damageProcessors',
            'declaredType':'System.Collections.Generic.List`1<Beyond.Gameplay.Core.DamageProcessorBase>',
            'runtimeTypeName':'Beyond.Gameplay.Core.DamageAction+DamageUnit'}
        or value.get('wire')!={'count':'signed-i32-null-minus-one','minimumFollowingUnitBytes':42,
            'supportedUnionTags':[0,2,3,4,5,6,9,10],'nullUnionElements':'unresolved-refuse'}
        or any(value.get('dependencies',{}).get(key)!=module.CONTRACT_PATH.name
               for key,module in LEAVES.items())):
        raise ValueError(f'{LABEL}.contract:shape')
    return value


def _source_call(image: Any, row: dict[str, Any]) -> int:
    rva=row['rva']; raw=image.pe.bytes_at_va(image.pe.image_base+rva,5)
    if (len(raw)!=5 or raw[0]!=0xe8 or ('rawHex' in row and raw.hex().upper()!=row['rawHex'])
        or rva+5+struct.unpack_from('<i',raw,1)[0]!=row['targetRva']):
        raise ValueError(f'{LABEL}.native:source-call')
    return row['targetRva']


def validate_current_native_contract() -> dict[str, Any]:
    """Check this collection's owner, conditional count source and every leaf."""
    contract=_contract(); pins=contract['nativeInputs']
    gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'])
    if gate.status!='validated':
        return {'status':gate.status,'detail':gate.detail,'nativeInputs':pins}
    unity=Path(gate.gameassembly).parent/'UnityPlayer.dll'
    if not unity.is_file() or hashlib.sha256(unity.read_bytes()).hexdigest().upper()!=pins['UnityPlayer.dll']:
        return {'status':'mismatched' if unity.is_file() else 'missing',
            'detail':'UnityPlayer.dll missing or mismatched','nativeInputs':pins}
    dependencies={key:json.loads((CONTRACTS_DIR/name).read_bytes())
                  for key,name in contract['dependencies'].items()}
    owner=contract['owner']; damage=dependencies['owner']; unit=damage['records'][owner['record']]
    member=unit['members'][owner['sourceMemberIndex']]
    if (damage.get('nativeInputs')!=pins or dependencies['modifier'].get('nativeInputs')!=pins
        or unit['runtimeTypeName']!=owner['runtimeTypeName']
        or any(member[key]!=owner[key] for key in ('fieldName','declaredType'))
        or member['kind']!='empty-list' or member['sourceCall']!=contract['sourceCall']
        or member['sourceContextInstructionRva']!=contract['sourceContext']['instructionRva']
        or damage['dependencies'].get('damageProcessorsList')!=CONTRACT_PATH.name
        or damage['sourceContract']!=contract['dependencies']['ownerSource']):
        raise ValueError(f'{LABEL}.contract:owner-binding')
    image=open_native_image(gate.gameassembly,gate.metadata)
    source=dependencies['ownerSource']; context=contract['sourceContext']
    if context not in source['nestedContexts']:
        raise ValueError(f'{LABEL}.contract:source-context')
    image.check_windows(source['codeWindows']+[dependencies['modifier']['childWindow']],label=LABEL)
    def fail(check,expected,actual):
        raise ValueError(f'{LABEL}.{check}: expected={expected!r}; actual={actual!r}')
    named.check_typed_context(image,context,owner['declaredType'],label=LABEL,fail=fail)
    target=_source_call(image,contract['sourceCall'])
    rows=dependencies['modifier']['childSourceInstructions']
    at,raw,_=next(r for r in rows if r[2]=='damageProcessors source context')
    # Same closed MethodSpec, including its actual generic argument, beyond
    # a matching field name. The source checker authenticates usage bytes.
    alternate={**context,'instructionRva':at,'instructionHex':raw}
    instruction=image.pe.bytes_at_va(image.pe.image_base+at,7)
    alternate['cellVa']=image.pe.image_base+at+7+struct.unpack_from('<i',instruction,3)[0]
    named.check_typed_context(image,alternate,owner['declaredType'],label=LABEL,fail=fail)
    at,raw,_=next(r for r in rows if r[2]=='damageProcessors source read')
    if _source_call(image,{'rva':at,'rawHex':raw,'targetRva':target})!=target:
        raise ValueError(f'{LABEL}.native:modifier-source-target')
    count=dependencies['countSource']; count_ref=contract['conditionalCountSource']
    windows=[count['codeWindows'][i] for i in count_ref['codeWindowIndexes']]
    data_windows=[count['dataWindows'][i] for i in count_ref['dataWindowIndexes']]
    if len(windows)!=1 or 'shared List<Object>' not in windows[0]['boundary'] or len(data_windows)!=3:
        raise ValueError(f'{LABEL}.contract:conditional-count-source')
    image.check_windows(windows+data_windows,label=LABEL)
    # The referenced source records both the closed Object-list MethodSpec
    # and its registered pointer. This is explicitly a conditional reference.
    spec=struct.unpack('<iii',image.pe.bytes_at_va(image.pe.image_base+data_windows[0]['startRva'],12))
    method=image.metadata.methods[spec[0]]
    args=image.instantiations.resolve(spec[1]).arguments
    from scripts.game_data.il2cpp.protocol import runtime_type_name
    actual={'formatterType':image.type_name(method.declaring_type),
        'method':image.metadata.string(method.name_index),
        'arguments':[runtime_type_name(image.pe,image.metadata,a.type_pointer_va) for a in args],
        'pointer':image.pe.u64_at_va(image.pe.image_base+data_windows[2]['startRva'])}
    wanted={'formatterType':count_ref['formatterType'],'method':count_ref['method'],
        'arguments':[count_ref['referenceElementType']],'pointer':image.pe.image_base+windows[0]['startRva']}
    if actual!=wanted:
        raise ValueError(f'{LABEL}.native:conditional-count-registration: expected={wanted!r}; actual={actual!r}')
    parent=modifier.validate_current_native_contract(gameassembly=gate.gameassembly,metadata=gate.metadata)
    if parent.get('status')!='validated':
        return {'status':parent.get('status','failed'),'detail':'independent processor source parent','nativeInputs':pins}
    children={key:module.validate_current_native_contract(modifier_native=parent) for key,module in LEAVES.items()}
    if any(child.get('status')!='validated' or child.get('nativeInputs')!=pins for child in children.values()):
        raise ValueError(f'{LABEL}.native:leaf-gates')
    after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],
        gameassembly=gate.gameassembly,metadata=gate.metadata)
    if after.status!='validated' or hashlib.sha256(unity.read_bytes()).hexdigest().upper()!=pins['UnityPlayer.dll']:
        raise ValueError(f'{LABEL}.native:inputs-changed')
    return {'status':'validated','nativeInputs':pins,'owner':owner,
        'conditionalCountSource':count_ref,'leaves':children,'evidenceBoundary':contract['evidenceBoundary']}


def decode_collection(data: bytes, *, source: str, digest: str, start: int, end: int,
                      native_validation: dict[str, Any]) -> dict[str, Any]:
    """Name ordered independent processor spans without a modifier root."""
    contract=_contract(); packet=native_validation; children=packet.get('leaves',{})
    if (packet.get('status')!='validated' or packet.get('nativeInputs')!=contract['nativeInputs']
        or packet.get('owner')!=contract['owner']
        or packet.get('conditionalCountSource')!=contract['conditionalCountSource']
        or set(children)!=set(LEAVES)
        or any(p.get('status')!='validated' or p.get('nativeInputs')!=contract['nativeInputs'] for p in children.values())):
        raise ValueError(f'{LABEL}.decode:native-unvalidated')
    virtual=PurePosixPath(source)
    if (not isinstance(data,bytes) or not isinstance(digest,str)
        or hashlib.sha256(data).hexdigest().upper()!=digest.upper()
        or virtual.is_absolute() or virtual.parts[:3]!=('Data','Json','BuffData')
        or len(virtual.parts)!=4 or '..' in virtual.parts or not source.endswith('.json')
        or type(start) is not int or type(end) is not int or not 0<=start<end<=len(data)):
        raise ValueError(f'{LABEL}.decode:source-or-span')
    reader=Reader(data,source,end); reader.pos=start
    count=reader.count(1,nullable=True); elements=[]
    for index in range(max(0,count)):
        begin=reader.pos; reader.damage_processor_profile(); finish=reader.pos
        route=next(r for r in reversed(reader.records) if r['kind']=='anonymous-damage-processor-profile' and r['start']==begin)
        tag=route['variant']
        if tag is None:
            raise ValueError(f'{LABEL}.decode:null-union-element-unproved')
        key='scalar' if tag in (0,2,3,4) else {5:'scale',6:'text',9:'instant',10:'modifyCalc'}[tag]
        decoder={'scalar':scalar.decode_scalar_processor_span,'scale':scale.decode_damage_scale_processor_span,
            'text':text.decode_damage_text_processor_span,'instant':instant.decode_instant_modify_attribute_processor_span,
            'modifyCalc':modify_calc.decode_modify_calc_result_processor_span}[key]
        child=decoder(data,source=source,logical_sha256=digest,start=begin,end=finish,native_validation=children[key])
        if (child.get('start')!=begin or child.get('end')!=finish or child.get('unionTag')!=tag
            or child.get('wholeStoredSpanExact') is not True or child.get('recursiveNamedSchemaExact') is not True):
            raise ValueError(f'{LABEL}.decode:leaf-boundary')
        elements.append({'index':index,'start':begin,'end':finish,'unionTag':tag,'child':child})
    if reader.pos!=end:
        raise ValueError(f'{LABEL}.decode:list-end={reader.pos}; expected={end}')
    return {'source':source,'logicalSha256':digest.upper(),'start':start,'end':end,'count':count,
        'owner':contract['owner'],'elements':elements,'recursiveStoredSchemaExact':True,'runtimeMeaningExact':False,
        'evidenceBoundary':contract['evidenceBoundary']}


__all__=['validate_current_native_contract','decode_collection']
