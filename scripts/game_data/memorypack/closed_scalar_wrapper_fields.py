"""Closed generic scalar fields established by actual generated setter bodies.

Runtime generic definition offsets are never used for instance destinations.
Owned VAR ordinals and closed carriers establish declared types; each selected
setter and original reader program establishes the concrete cell it writes.
These are conditional normal flows, without provider/allocation/error parity.
"""
from __future__ import annotations

import struct
from typing import Any,Callable
from scripts.game_data.il2cpp.context import type_parameter_owner
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets
from scripts.game_data.memorypack import inherited_reference_sources as ancestry
from scripts.game_data.memorypack import inline_utf8_sources as paths
from scripts.game_data.memorypack import reference_output_sources as references
from scripts.game_data.memorypack import struct_output_sources as structs

LABEL='closedScalarWrapperFields'
MODE='closed-key-boolean-single-fields-from-generated-setters'


def _parent_aliases(image: Any,normal: dict,record: dict,proof: dict,fail: Callable) -> None:
    structs.check_reader_ref_wrapper_abi(image,record,fail=fail)
    rows=proof['parentProgram'];references._program(image,normal,rows,fail)
    final=proof['sourcePrograms']['value']['wrapperLoad']
    if (rows[0][0]!=normal['startRva'] or final not in rows or final[1]!='488B36'
            or rows[-1]!=proof['sourcePrograms']['value']['bridgeProgram'][-1]):
        fail('closed-scalar-parent-extent','entry through last value store and exact final wrapper load',proof)
    aliases={'rsi':'488BF2','rdi':'488BF9'};seen=set()
    for at,h in rows:
        if h=='482BC8':continue  # Explicit SUB RCX,RAX; no incoming-alias write.
        raw=bytes.fromhex(h);decoded=image.mapper.decode_x64_subset(raw,image.pe.image_base+at,stop_offset=len(raw))
        if len(decoded)!=1 or decoded[0]['text'].startswith('db'):
            fail('closed-scalar-parent-instruction','one complete understood instruction',[at,h])
        register=(decoded[0].get('write') or {}).get('register')
        if register in {'rsi','esi','si','sil','rdi','edi','di','dil'}:
            if [at,h]==final and seen==set(aliases):continue
            if register not in aliases or register in seen or h!=aliases[register]:
                fail('closed-scalar-parent-clobber',aliases,[at,h,register])
            seen.add(register)
        if raw[:1]==b'\xe8' and seen!=set(aliases):
            fail('closed-scalar-late-alias',sorted(aliases),sorted(seen))
    if seen!=set(aliases):fail('closed-scalar-missing-alias',sorted(aliases),sorted(seen))


def _guards(normal: dict,rows: list,indices: tuple,fail: Callable) -> list[bytes]:
    result=[]
    for index in indices:
        row=rows[index];raw=bytes.fromhex(row[1])
        if not (len(raw)==6 and raw[:2]==b'\x0f\x84' or len(raw)==2 and raw[:1]==b'\x74'):
            fail('closed-scalar-null-guard','complete JE rel8/rel32',row)
        if normal['startRva']<=paths._target(row)<normal['endRva']:
            fail('closed-scalar-null-target','unproved cold null path outside normal reader window',row)
        result.append(raw)
    return result


def validate_closed_scalar_fields(image: Any,source: dict,record: dict,proof: dict,*,
                                  key_result_join: int,barrier_flag: int,fail: Callable) -> dict:
    if proof.get('mode')!=MODE or set(proof.get('setters',{}))!={'blackboardKey','useBlackboardKey','value'}:
        fail('closed-scalar-scope','three owned key/Boolean/Single setters',proof)
    runtime=ancestry._ancestry(image,proof['runtimeTypeDefinition'])
    wrappers=ancestry._ancestry(image,record['wrapperTypeDefinition'])
    ancestry._ancestry_matches(runtime,proof['runtimeAncestry'],fail)
    ancestry._ancestry_matches(wrappers,proof['wrapperAncestry'],fail)
    closed=[r['parent'] for r in runtime if r['parent'] and r['parent']['kind']==0x15]
    instances=[(r,f) for r in wrappers for f in r['fields'] if f['type']['kind']==0x15]
    if len(closed)!=1 or len(instances)!=1:fail('closed-scalar-carriers',[1,1],[len(closed),len(instances)])
    closed=closed[0];wrapper_owner,instance=instances[0];wrapped=instance['type']
    if (bytes.fromhex(closed['rawHex'])[:8]!=bytes.fromhex(wrapped['rawHex'])[:8]
            or any(closed[k]!=wrapped[k] for k in ('definition','instanceIndex','arguments'))):
        fail('closed-scalar-same-instantiation',closed,wrapped)
    slot=wrapper_owner['offsets'][instance['name']]
    if not 16<=slot<128:fail('closed-scalar-wrapper-slot','owned wrapper reference disp8',slot)
    owner=image.metadata.types[closed['definition']];section=image.metadata.sections['genericContainers']
    at=section.offset+owner.generic_container_index*16
    if owner.generic_container_index<0 or not section.offset<=at<=section.offset+section.size-16:
        fail('closed-scalar-container','bounded type generic container',owner.generic_container_index)
    container=list(struct.unpack_from('<iiii',image.metadata.buf,at))
    if container!=proof['genericContainer'] or container[:3]!=[owner.index,2,0]:
        fail('closed-scalar-container-owner',proof['genericContainer'],container)
    if [a['name'] for a in closed['arguments']]!=['float','double']:
        fail('closed-scalar-arguments',['float','double'],closed['arguments'])
    declared_fields=[(r,f) for r in runtime for f in r['fields']]
    fields={f['name']:(r,f) for r,f in declared_fields}
    if set(fields)!={'blackboardKey','useBlackboardKey','value'} or len(declared_fields)!=3:
        fail('closed-scalar-declared-fields','exact three scalar instance members',sorted(fields))
    value_owner,value=fields['value']
    if value_owner['definition']!=owner.index or value['type']['kind']!=0x13:
        fail('closed-scalar-value-var','generic owner value VAR',value)
    parameter=int.from_bytes(bytes.fromhex(value['type']['rawHex'])[:8],'little')
    identity=type_parameter_owner(image.metadata.buf,parameter,
        [t.generic_container_index for t in image.metadata.types],source=LABEL)
    if identity!=proof['valueParameterOwner'] or identity['typeIndex']!=owner.index or identity['ordinal']!=0:
        fail('closed-scalar-value-var-owner',proof['valueParameterOwner'],identity)
    offsets={}
    for name,block in proof['setters'].items():
        method=block['method'];image.validate_method_row(method,label=LABEL)
        definition=image.metadata.methods[method[0]];parameters=list(image.metadata.parameters_for(definition))
        if (definition.flags&0x10 or len(parameters)!=1 or method[1]!=wrapper_owner['name']
                or method[2]!='set___'+name+'__' or ancestry._type_row(image,definition.return_type)['name']!='void'):
            fail('closed-scalar-setter-abi','current owned instance void setter',method)
        actual=ancestry._type_row(image,parameters[0].type_index)
        field=fields[name][1]['type']
        if name=='value':
            if actual['pointerRva']!=closed['arguments'][identity['ordinal']]['pointerRva']:
                fail('closed-scalar-var-substitution',closed['arguments'][0],actual)
        elif field['kind']!=actual['kind'] or field['name']!=actual['name']:
            fail('closed-scalar-field-parameter',field,actual)
        offset=block['destinationOffset']
        if type(offset) is not int or not 16<=offset<128:
            fail('closed-scalar-setter-cell','bounded actual destination disp8',offset)
        rows=block['program'];normal=block['window'];image.check_windows([normal],label=LABEL)
        raw=[bytes.fromhex(row[1]) for row in rows]
        if name=='blackboardKey':
            if len(raw)!=13:fail('closed-scalar-key-setter-size',13,rows)
            flag=raw[6]
            if (len(flag)!=7 or flag[:2]!=b'\x83\x3d' or flag[-1]!=0
                    or rows[6][0]+7+int.from_bytes(flag[2:6],'little',signed=True)!=barrier_flag):
                fail('closed-scalar-key-barrier-flag','same independently proved disabled-barrier flag',rows[6])
            expected=[b'\x48\x89\x5c\x24\x10',b'\x57',b'\x48\x83\xec\x20',b'\x48\x8b\x59'+bytes((slot,)),
                b'\x48\x85\xdb',raw[5],flag,b'\x48\x89\x53'+bytes((offset,)),raw[8],
                b'\x48\x8b\x5c\x24\x38',b'\x48\x83\xc4\x20',b'\x5f',b'\xc3']
            branches={5:('74',False),8:('74',True)}
        else:
            if len(raw)!=7:fail('closed-scalar-primitive-setter-size',7,rows)
            store=(b'\x88\x50' if name=='useBlackboardKey' else b'\xf3\x0f\x11\x48')+bytes((offset,))
            expected=[b'\x48\x83\xec\x28',b'\x48\x8b\x41'+bytes((slot,)),b'\x48\x85\xc0',raw[3],store,
                      b'\x48\x83\xc4\x28',b'\xc3'];branches={3:('74',False)}
        if rows[0][0]!=method[3]:fail('closed-scalar-setter-entry',method[3],rows[0])
        paths._selected(image,normal,rows,expected,branches,rows[-1][0]+1,fail)
        offsets[name]=offset
    ranges=[(offsets[name],offsets[name]+width) for name,width in [('blackboardKey',8),('useBlackboardKey',1),('value',4)]]
    if any(a<b2 and b<a2 for i,(a,a2) in enumerate(ranges) for b,b2 in ranges[i+1:]):
        fail('closed-scalar-cell-overlap','distinct actual emitted cells',ranges)
    normal=next(w for w in source['codeWindows'] if w['startRva']==record['readerMethod'][3])
    _parent_aliases(image,normal,record,proof,fail)
    fields=proof['readerFieldOffsets'];reader=proof['readerTypeDefinition']
    actual=runtime_type_field_offsets(image.metadata,image.pe,image.registration,reader)
    if image.type_name(reader)!='MemoryPack.MemoryPackReader' or actual!=fields:
        fail('closed-scalar-reader-layout',fields,actual)
    pointer,remaining,advanced,consumed=[fields[n]-16 for n in ('currentPtr','bufferLength','advancedCount','consumed')]
    if any(not 0<=v<128 for v in (pointer,remaining,advanced,consumed)):
        fail('closed-scalar-reader-disp8','four unboxed reader fields',fields)
    key=proof['sourcePrograms']['blackboardKey'];load=key['wrapperLoad']
    if load not in proof['parentProgram'] or load[1]!='4C8B36' or load[0]>=key_result_join:
        fail('closed-scalar-key-wrapper','exact prior R14 load from ref-wrapper alias',load)
    for at,h in proof['parentProgram']:
        if load[0]<at<key_result_join:
            raw=bytes.fromhex(h)
            if h=='482BC8':continue
            decoded=image.mapper.decode_x64_subset(raw,image.pe.image_base+at,stop_offset=len(raw))
            register=(decoded[0].get('write') or {}).get('register')
            if register in {'r14','r14d','r14w','r14b'}:
                fail('closed-scalar-key-wrapper-clobber','R14 preserved from wrapper load to key result join',[at,h,register])
    rows=key['bridgeProgram'];guards=_guards(normal,rows,(1,4),fail)
    flag=bytes.fromhex(rows[5][1])
    if len(flag)!=7 or flag[:2]!=b'\x83\x3d' or flag[-1]!=0 or rows[5][0]+7+int.from_bytes(flag[2:6],'little',signed=True)!=barrier_flag:
        fail('closed-scalar-source-barrier-flag','same independently proved barrier flag',rows[5])
    expected=[b'\x4d\x85\xf6',guards[0],b'\x4d\x8b\x46'+bytes((slot,)),b'\x4d\x85\xc0',guards[1],flag,
              b'\x49\x89\x58'+bytes((offsets['blackboardKey'],))]
    structs._program(image,normal,rows,expected,label=LABEL,fail=fail)
    if rows[0][0]!=key_result_join:fail('closed-scalar-key-result-join',key_result_join,rows[0])
    skip=key['afterStoreBranch'];image.check_instruction_windows([skip],label=LABEL)
    bool_start=proof['sourcePrograms']['useBlackboardKey']['readProgram'][0][0]
    if (skip[0]!=rows[-1][0]+len(bytes.fromhex(rows[-1][1])) or bytes.fromhex(skip[1])[:1]!=b'\x74'
            or len(bytes.fromhex(skip[1]))!=2 or paths._target(skip)!=bool_start):
        fail('closed-scalar-key-to-boolean','same barrier-disabled branch reaches the following Boolean source',skip)
    for name,width in [('useBlackboardKey',1),('value',4)]:
        block=proof['sourcePrograms'][name];rows=block['readProgram'];raw=[bytes.fromhex(row[1]) for row in rows]
        is_bool=name=='useBlackboardKey'
        if len(raw)!=12:fail('closed-scalar-source-read-size',12,rows)
        load=b'\x48\x8b\x2e' if is_bool else b'\x48\x8b\x36'
        expected=[b'\x83\x7f'+bytes((remaining,width)),load,raw[2],b'\x48\x8b\x47'+bytes((pointer,)),
            b'\x44\x0f\xb6\x30' if is_bool else b'\xf3\x0f\x10\x30',b'\x8b\x5f'+bytes((remaining,)),
            b'\x83\xeb'+bytes((width,)),raw[7]]
        expected+=([b'\x48\xff\x47'+bytes((pointer,)),b'\xff\x47'+bytes((advanced,)),b'\xff\x47'+bytes((consumed,))] if is_bool else
                   [b'\x48\x83\x47'+bytes((pointer,width)),b'\x83\x47'+bytes((advanced,width)),b'\x83\x47'+bytes((consumed,width))])
        expected+=[b'\x89\x5f'+bytes((remaining,))]
        bridge=block['bridgeProgram']
        paths._selected(image,normal,rows,expected,{2:('7D',True),7:('79',True)},bridge[0][0],fail)
        guards=_guards(normal,bridge,(2,5) if is_bool else (1,4),fail)
        if is_bool:
            expected_bridge=[b'\x0f\x29\x74\x24\x20',b'\x48\x85\xed',guards[0],b'\x48\x8b\x4d'+bytes((slot,)),
                b'\x48\x85\xc9',guards[1],b'\x45\x84\xf6',b'\x0f\x95\xc0',b'\x88\x41'+bytes((offsets[name],))]
        else:
            expected_bridge=[b'\x48\x85\xf6',guards[0],b'\x48\x8b\x46'+bytes((slot,)),b'\x48\x85\xc0',guards[1],
                b'\x4c\x8b\x74\x24\x58',b'\xf3\x0f\x11\x70'+bytes((offsets[name],))]
        structs._program(image,normal,bridge,expected_bridge,label=LABEL,fail=fail)
        if block['wrapperLoad']!=rows[1]:fail('closed-scalar-source-wrapper-load',rows[1],block['wrapperLoad'])
        if is_bool and bridge[-1][0]+len(bytes.fromhex(bridge[-1][1]))!=proof['sourcePrograms']['value']['readProgram'][0][0]:
            fail('closed-scalar-boolean-to-value','value source immediately follows normalized Boolean store',bridge[-1])
    return {'fields':[{'fieldName':name,'destinationOffset':offsets[name],
                      'representation':'reference' if name=='blackboardKey' else 'normalized-bool' if name=='useBlackboardKey' else 'raw-float32'}
                     for name in ('blackboardKey','useBlackboardKey','value')],
        'closedArguments':['float','double'],'runtimeGenericTemplateOffsetsUsed':False,
        'sourceMatchesActualNamedSetterCells':True,'normalBooleanNormalizationProved':True,
        'rawFloat32CopyProved':True,'evidenceBoundary':'conditional',
        'condition':'coherent declared wrapper/base-Data reference, buffered sources, ordinary Win64 returning calls; selected key setter barrier-disabled path',
        'runtimeConsumerReadsProved':False,'providerSelectionProved':False,'allocationOrFailureParityKnown':False,
        'wholeActionAdmitted':False,'wholeRootAdmitted':False}
