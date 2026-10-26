"""Authenticate selected string-key lookup, counter and GetStrKey value sources.

The historical named-IsPatched grammars remain exact. Nullable inline shapes
authenticate complete unwind families, separate instruction partitions and
owned sparse edges, including the direct original entry and null-pointer
resume. They prove the concrete dictionary request and referenced output,
the counter's signed reset/modulo-32-bit increment, and GetStrKey's selected
minus-one, lookup-hit and counter-candidate return sources. Native field,
ordinary ABI, generic-owner and registered call-pointer checks stay separate
from the instruction-shape proof.

Claims require valid original arguments, selected original paths, normal
returning Win64 callees and preserved caller locals; GetStrKey's value-source
claim additionally selects an original false Boolean. Replacement behavior,
ReadOnlySpan instance-field meaning, hash algorithms, dictionary execution or
mutation, allocation, key stability/uniqueness and runtime invocation remain
unresolved. Declared unwind ownership does not prove unwind-code semantics.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path

if __name__ == '__main__' and not __package__:
    raise SystemExit('Run with python -m scripts.game_data.dynamic_mission_string_providers_native')

from scripts.common import check_installed_native_inputs, NATIVE_EVIDENCE_VALIDATED
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract, NATIVE_MAPPER_PATH, METADATA_HELPER_PATH
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext, closed_generic_reference_extent
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets
from scripts.game_data.il2cpp.context import method_spec_usage_index, generic_method_candidates, type_parameter_owner
from scripts.game_data.dynamic_erosion_consumers_native import _ordinary_primitive_abi, _instruction_partition, _preserved_interval
from scripts.game_data.dynamic_mission_condition_consumers_native import (
    _composed_decoder, _program_from_fragments, _expect_at, _branch_at,
    _rip_load_cell, _call_at, _call_target)
from scripts.game_data.memorypack.corpus_gate import _fingerprint, _parser_source_snapshots
from scripts.game_data.corpus_common import atomic_write_text
from scripts.game_data import dynamic_group_components_native as groups
from scripts.repo_paths import REPO_ROOT

CONTRACT = CONTRACTS_DIR/'dynamic_mission_string_providers_native_claims.json'
SCHEMA = 'endfield.dynamic-mission-string-providers-native-claims.v2'


def require(ok, label, actual):
    if not ok: raise ValueError('mission_string_providers:'+label+':'+str(actual)[:500])


def _va(row): return int(row['va'], 16)


def _raw(row): return bytes.fromhex(row['bytes'])


def branch_target(row):
    raw=_raw(row);va=_va(row)
    if len(raw)==2 and (0x70<=raw[0]<=0x7f or raw[0]==0xeb):
        return va+2+struct.unpack('<b',raw[1:])[0]
    if len(raw)==6 and raw[0]==0x0f and 0x80<=raw[1]<=0x8f:
        return va+6+struct.unpack('<i',raw[2:])[0]
    if len(raw)==5 and raw[0] in (0xe8,0xe9):
        return va+5+struct.unpack('<i',raw[1:])[0]
    raise ValueError('mission_string_providers:unsupported-direct-branch:'+str(row)[:400])


def _grammar(rows, expected):
    require(len(rows)==len(expected), 'complete-grammar-count', (len(expected),len(rows)))
    for row, token in zip(rows, expected):
        text=row['text']
        require(text.startswith(token[:-1]) if token.endswith('*') else text==token,
                'complete-grammar-slot', (row['offset'],token,text))


def _call(rows, at, pointer, label):
    row=rows[at]
    require(len(_raw(row))==5 and _raw(row)[0]==0xe8 and branch_target(row)==pointer,
            label, row)


def _edge(rows, at, opcode, target):
    row=rows[at]
    require(_raw(row).startswith(bytes.fromhex(opcode)) and branch_target(row)==_va(rows[target]),
            'owned-branch-boundary', (at,target,row))


def check_counter(rows, patch, grammar):
    _grammar(rows,grammar)
    _call(rows,5,patch,'counter-actual-patch')
    require(_raw(rows[7])[:2]==b'\x0f\x85' and not _va(rows[0])<=branch_target(rows[7])<=_va(rows[-1]),
            'counter-false-patch-fallthrough',rows[7])
    _edge(rows,9,'7c',16);_edge(rows,17,'eb',10)
    for at,raw in ((8,'837B2000'),(10,'8B4320'),(12,'894320'),(16,'C7432000000000')):
        require(_raw(rows[at])==bytes.fromhex(raw),'counter-Int32-memory-width',rows[at])
    require(rows[11].get('operandWidth')==32 and rows[11].get('upperRegisterEffect')=='zero upper 32 bits',
            'counter-INC32',rows[11])
    _preserved_interval(rows,rows[10]['offset'],rows[12]['offset'],'rbx',set(),'counter-this')
    return {'negativeInput':1,'nonnegativeInput':'(stored UInt32 bits + 1) modulo 2^32',
            'writesSameField':True,'globalUniquenessProved':False,'runtimeObserved':False}


def check_lookup(rows, patch, hash_pointer, dictionary_pointer, grammar):
    _grammar(rows,grammar)
    _call(rows,11,patch,'lookup-actual-patch');_call(rows,21,hash_pointer,'lookup-actual-hash-request')
    _call(rows,28,dictionary_pointer,'lookup-actual-contextual-dictionary')
    require(_raw(rows[16])==bytes.fromhex('837B1000'),'string-length-Int32-read',rows[16])
    _edge(rows,8,'74',41);_edge(rows,15,'74',34);_edge(rows,17,'76',34)
    _edge(rows,23,'74',45);_edge(rows,44,'e9',9)
    require(_raw(rows[13])[:2]==b'\x0f\x85' and not _va(rows[0])<=branch_target(rows[13])<=_va(rows[-1]),
            'lookup-false-patch-fallthrough',rows[13])
    require(rows[45]['text'].startswith('call ') and rows[46]['text']=='int3',
            'lookup-null-exception',rows[45:])
    # Raw program closes both return frames, including untouched AL/EAX after the dictionary call.
    _preserved_interval(rows,rows[22]['offset'],rows[28]['offset'],'rax',set(),'hash-return-key')
    _preserved_interval(rows,rows[29]['offset'],rows[33]['offset'],'rax',set(),'dictionary-bool-return')
    _preserved_interval(rows,rows[19]['offset'],rows[28]['offset'],'rdi',{rows[21]['offset']},'lookup-saved-map')
    _preserved_interval(rows,rows[8]['offset'],rows[28]['offset'],'rsi',{rows[11]['offset'],rows[21]['offset']},'lookup-saved-output')
    require(_raw(rows[36])==bytes.fromhex('C706FFFFFFFF'),'empty-output-minus-one',rows[36])
    def rip_cell(row,displacement):return _va(row)+len(_raw(row))+struct.unpack_from('<i',_raw(row),displacement)[0]
    require(_raw(rows[4])[:2]==bytes.fromhex('803D') and _raw(rows[4])[-1:]==b'\0' and
            _raw(rows[43])[:2]==bytes.fromhex('C605') and _raw(rows[43])[-1:]==b'\1' and
            rip_cell(rows[4],2)==rip_cell(rows[43],2),'same-initialization-flag',(rows[4],rows[43]))
    require(_raw(rows[41])[:3]==bytes.fromhex('488D0D') and rip_cell(rows[41],3)==rip_cell(rows[24],3) and
            len(_raw(rows[42]))==5 and _raw(rows[42])[0]==0xe8,'same-context-initialization',(rows[41],rows[42]))
    return {'nonemptyRequest':'selected UInt64 hash return to Dictionary<UInt64,Int32>.TryGetValue',
            'normalReturn':'same dictionary Boolean return and original referenced Int32 output',
            'nullOrEmpty':'false; referenced Int32 written -1',
            'hashAlgorithmProved':False,'keyStabilityProved':False,'runtimeObserved':False}


def _type_record(image,index):
    selected=NativeReferenceContext(image)
    return image.pe.bytes_at_va(selected.type_pointer(index),16)


def _abi(image,index,token,label):
    codes={'Void':1,'Boolean':2,'Int32':8,'UInt64':11}
    if token in codes:
        _ordinary_primitive_abi(image,index,codes[token],label);return
    raw=_type_record(image,index)
    if token=='SpanByte':
        require(raw[10]==0x15 and raw[11]&0x7f==0,'ordinary-span-value',raw.hex())
        generic=struct.unpack_from('<Q',raw)[0];pe=image.pe;md=image.metadata
        definition_pointer,inst=struct.unpack('<QQ',pe.bytes_at_va(generic,16))
        definition_raw=pe.bytes_at_va(definition_pointer,16)
        require(definition_raw[10]==0x11 and definition_raw[11]&0x7f==0,'span-value-definition',definition_raw.hex())
        definition=struct.unpack_from('<Q',definition_raw)[0]
        require(0<=definition<len(md.types) and md.type_full_name(md.types[definition])=='System.ReadOnlySpan`1',
                'span-concrete-definition',definition)
        td=md.types[definition];section=md.sections['genericContainers'];at=section.offset+td.generic_container_index*16
        require(td.generic_container_index>=0 and section.offset<=at<=section.offset+section.size-16,'span-generic-owner-range',at)
        owner,count,is_method,parameter=struct.unpack_from('<iiii',md.buf,at)
        argc,argv=struct.unpack('<QQ',pe.bytes_at_va(inst,16))
        require(owner==definition and count==argc==1 and is_method==0 and parameter>=0,'span-generic-arity',(owner,count,argc))
        argument=pe.bytes_at_va(pe.u64_at_va(argv),16)
        require(argument[10]==5 and argument[11]&0x7f==0,'span-ordinary-Byte-argument',argument.hex())
        return
    require((raw[10],raw[11])==({'String':(0x0e,0),'ref Int32':(8,0x20)}[token]),label,raw.hex())


def select_ordinary_overload(image,candidates,spec):
    matching=[];rejected=[];md=image.metadata
    for candidate in candidates:
        params=md.parameters_for(candidate)
        if len(params)!=len(spec['parameters']) or bool(candidate.flags&0x10)!=(spec['callAbi']=='static'):
            rejected.append({'index':candidate.index,'reason':'parameter count or static/instance role'});continue
        try:
            _abi(image,candidate.return_type,spec['returnType'],'overload-return')
            for param,token in zip(params,spec['parameters']):_abi(image,param.type_index,token,'overload-parameter')
        except (ValueError,KeyError,IndexError,RuntimeError,struct.error) as exc:
            rejected.append({'index':candidate.index,'reason':str(exc)[:240]});continue
        matching.append(candidate)
    require(len(matching)==1,'unique-full-ordinary-ABI-overload',
            {'matching':[m.index for m in matching],'rejected':rejected[:8]})
    return matching[0]


def _methods(image,contract):
    md=image.metadata;methods={};bodies={};extents=image.mapper.pdata_function_extents(image.pe)
    for role,spec in contract['methods'].items():
        owners=[td for td in md.types if md.type_full_name(td)==spec['type'] and
                md.string(md.images[image.owners[td.index]].name_index)==spec['image']]
        require(len(owners)==1,'qualified-owner-'+role,len(owners))
        candidates=[m for m in md.methods_for(owners[0]) if md.string(m.name_index)==spec['method']]
        if role=='getKey':
            candidates=[select_ordinary_overload(image,candidates,spec)]
        require(len(candidates)==1,'qualified-method-'+role,len(candidates));m=candidates[0]
        params=md.parameters_for(m)
        require(len(params)==len(spec['parameters']) and bool(m.flags&0x10)==(spec['callAbi']=='static'),
                'method-role-'+role,(m.flags,len(params)))
        _abi(image,m.return_type,spec['returnType'],role+'-return')
        for p,token in zip(params,spec['parameters']):_abi(image,p.type_index,token,role+'-parameter')
        pointer=image.method_pointer_va(m);require(pointer is not None,'method-pointer-'+role,pointer)
        methods[role]=(m,pointer)
        if role in ('counter','lookup'):
            end=extents.get(pointer);require(end is not None and 0<end-pointer<=4096,'bounded-primary-'+role,end)
            raw=image.pe.bytes_at_va(pointer,end-pointer)
            bodies[role]={'rows':_instruction_partition(raw,pointer,_composed_decoder(image.mapper)),
                          'rva':pointer-image.pe.image_base,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest().upper()}
    require(methods['counter'][0].declaring_type==methods['lookup'][0].declaring_type==methods['getKey'][0].declaring_type,
            'same-concrete-provider-owner',[m.declaring_type for m,_ in methods.values()])
    return methods,bodies


def _register_preserved(rows,registers,allowed):
    """Closed-program checks cover all aliases, including flags held in BPL."""
    aliases={'rbp':{'rbp','ebp','bp','bpl'},'rbx':{'rbx','ebx','bx','bl','bh'},
             'rdi':{'rdi','edi','di','dil'},'rsi':{'rsi','esi','si','sil'},
             'r14':{'r14','r14d','r14w','r14b'},'rax':{'rax','eax','ax','al','ah'}}
    watched=set().union(*(aliases[r] for r in registers))
    for row in rows:
        require((row.get('write') or {}).get('register') not in watched,'get-key-saved-register-alias',row)
        if row['text'].startswith('call '):
            require(_va(row) in allowed and len(_raw(row))==5 and _raw(row)[0]==0xe8,'get-key-normal-call',row)


def check_get_key_program(parts,methods,programs):
    require(len(parts)==5,'get-key-family-shape',len(parts))
    by_va={_va(r):r for rows in parts.values() for r in rows}
    require(len(by_va)==sum(map(len,parts.values())),'get-key-disjoint-partitions',len(by_va))
    for role,rows in parts.items():_grammar(rows,programs[role])
    prefix=parts['prefix'];main=parts['main'];init=parts['init'];exception=parts['exception'];cold=parts['cold']
    p={r['offset']:r for r in prefix};m={r['offset']:r for r in main};i={r['offset']:r for r in init};c={r['offset']:r for r in cold}
    def edge(row,opcode,target):
        require(_raw(row).startswith(bytes.fromhex(opcode)) and branch_target(row)==_va(target),'get-key-owned-edge',(row,target))
    edge(p[37],'0F84',i[0]);edge(i[67],'E9',p[43])
    require(_va(p[43])+len(_raw(p[43]))==_va(m[0]),'get-key-owned-fallthrough',(p[43],m[0]))
    def rip(row,at):return _va(row)+len(_raw(row))+struct.unpack_from('<i',_raw(row),at)[0]
    require(_raw(p[20])[:2]==bytes.fromhex('803D') and _raw(p[20])[-1:]==b'\0' and
            _raw(i[60])[:2]==bytes.fromhex('C605') and _raw(i[60])[-1:]==b'\1' and
            rip(p[20],2)==rip(i[60],2),'get-key-same-entry-init-flag',(p[20],i[60]))
    require(_raw(i[12])[:3]==bytes.fromhex('488D0D') and _raw(i[24])[:3]==bytes.fromhex('488D0D') and
            rip(i[12],3)==rip(m[74],3) and rip(i[24],3)==rip(m[196],3),
            'get-key-same-initialized-request-contexts',(i[12],i[24]))
    _call(main,4,methods['patch'][1],'get-key-actual-patch')
    edge(m[23],'0F85',c[89]);edge(m[32],'0F84',c[79])
    edge(m[68],'0F84',exception[0]);edge(m[190],'0F84',exception[0])
    edge(m[96],'74',m[170]);edge(m[105],'74',m[142]);edge(m[217],'75',m[224])
    edge(m[222],'EB',m[144]);edge(c[84],'E9',m[144])
    require(_raw(p[27])==bytes.fromhex('410FB6E8'),'original-Boolean-to-EBP',p[27])
    require(_raw(m[29])==bytes.fromhex('397308') and _raw(p[43])==bytes.fromhex('33F6'),
            'anonymous-carrier-Int32-at8',(m[29],p[43]))
    require(_raw(m[38])==bytes.fromhex('0F1003') and _raw(m[48])==bytes.fromhex('0F29442440'),
            'mechanical-16-byte-carrier-copy',(m[38],m[48]))
    for at,encoded in ((0,'4C89742460'),(7,'89742430'),(43,'488D4C2440'),(58,'488B4F10'),
                       (81,'4C8D442430'),(86,'488BD0'),(170,'33D2'),(172,'488BCF'),(180,'488B4F10')):
        require(_raw(m[at])==bytes.fromhex(encoded),'get-key-concrete-argument-or-local',m[at])
    require(_raw(m[98])==bytes.fromhex('8B742430') and _raw(m[142])==bytes.fromhex('8BC6'),
            'lookup-output-to-return',(m[98],m[142]))
    for at,hex_value in ((184,'448BF0'),(203,'448BC0'),(206,'488BD6'),(219,'418BC6')):
        require(_raw(m[at])==bytes.fromhex(hex_value),'counter-candidate-lane',m[at])
    require(_raw(c[79])==bytes.fromhex('B8FFFFFFFF'),'zero-anonymous-lane-minus-one',c[79])
    require(_raw(m[102])==_raw(m[214])==bytes.fromhex('4084ED'),'false-original-Boolean-tests',(m[102],m[214]))
    require([m[at]['text'] for at in (144,149,154,159,164,168,169)]==
            ['mov r14, [rsp+0x60]','mov rbx, [rsp+0x68]','mov rbp, [rsp+0x70]',
             'mov rsi, [rsp+0x78]','add rsp, 0x50','pop rdi','ret'],'get-key-balanced-frame',m[144])
    # Evaluate the full owned instruction graph only under declared selection conditions.
    choices={_va(m[at]):take for at,take in ((23,False),(68,False),(105,True),(190,False),(217,False))}
    paths=[]
    def walk(va,path):
        require(len(path)<512 and len(paths)<32,'get-key-CFG-traversal-bound',(len(path),len(paths)))
        require(va in by_va and va not in path,'get-key-CFG-owned-acyclic-edge',va)
        row=by_va[va];raw=_raw(row);path=path+[va]
        if row['text']=='ret':paths.append(path);return
        require(row['text']!='int3','get-key-selected-exception',row)
        next_va=va+len(raw)
        conditional=(len(raw)==2 and 0x70<=raw[0]<=0x7f) or (len(raw)==6 and raw[0]==0x0f and 0x80<=raw[1]<=0x8f)
        if conditional:
            selected=choices.get(va)
            successors=[branch_target(row)] if selected is True else [next_va] if selected is False else [next_va,branch_target(row)]
        elif row['text'].startswith('jmp '):successors=[branch_target(row)]
        else:successors=[next_va]
        for target in successors:walk(target,path)
    walk(_va(p[0]),[])
    require(len(paths)==6 and all(path[-1]==_va(m[169]) for path in paths),'get-key-six-normal-paths',len(paths))
    normal_calls={_va(r) for path in paths for va in path for r in (by_va[va],) if r['text'].startswith('call ')}
    for path in paths:
        selected=[by_va[va] for va in path]
        flag_start=path.index(_va(p[27]))+1;flag_end=path.index(_va(m[154]))
        _register_preserved(selected[flag_start:flag_end],('rbp',),normal_calls)
        before_return=path.index(_va(m[144]))
        _register_preserved(selected[path.index(_va(p[34]))+1:before_return],('rdi',),normal_calls)
        if _va(m[175]) in path:
            _register_preserved(selected[path.index(_va(m[184]))+1:before_return],('r14',),normal_calls)
            _register_preserved(selected[path.index(_va(m[62]))+1:path.index(_va(m[209]))],('rsi',),normal_calls)
        if _va(m[89]) in path and _va(m[98]) in path:
            for va in path[path.index(_va(m[89]))+1:path.index(_va(m[98]))]:
                row=by_va[va]
                require(not row['text'].startswith(('mov [','movups [','movaps [','push ','pop ','add rsp','sub rsp','call ')),
                        'get-key-output-local-preserved',row)
        if _va(m[38]) in path:
            interval=selected[path.index(_va(m[38]))+1:path.index(_va(m[48]))]
            require(all((r.get('write') or {}).get('register')!='xmm0' and not r['text'].startswith('call ') for r in interval),
                    'get-key-mechanical-copy-preserved',interval)
    _preserved_interval(main,187,203,'rax',set(),'counter-return-to-setter-value')
    # Typed request identities are independent from the raw branch predicates.
    for at,role in ((53,'spanHash'),(175,'counter')):
        row=m[at];require(len(_raw(row))==5 and _raw(row)[0]==0xe8 and branch_target(row)==methods[role][1],
                         'get-key-actual-'+role,row)
    return {'flagSelection':'original Boolean false','zeroAnonymousInt32LaneAt8':'Int32 -1',
            'nonzeroLaneLookupHit':'successful referenced Int32 lookup output returned',
            'nonzeroLaneLookupMiss':'typed counter return sent to same UInt64/Int32 dictionary setter and returned',
            'instanceSpanFieldLayoutProved':False,'hashAlgorithmProved':False,'dictionaryMutationProved':False,
            'globalUniquenessProved':False,'runtimeObserved':False,'normalPaths':len(paths),
            'conditions':['valid original value carrier and receiver, false actual IFix, original Boolean false, nonnull dictionary',
                          'normal returning Win64 callees preserve nonvolatile registers and caller locals']}


def get_key_value_source(image,methods,contract,map_field):
    pe=image.pe;pointer=methods['getKey'][1]
    family=image.unwind_index.family(pointer-pe.image_base)
    if len(family['ranges'])==7:
        program=_selected_program(image,pointer,7,'get-key-current')
        proof=_current_get_key(program,methods)
        by=program['by']
        _,proof['lookupContext']=dictionary_context(image,by[125],by[140],map_field,method_name='TryGetValue',argument_kinds=(11,8))
        _,proof['setterContext']=dictionary_context(image,by[243],by[256],map_field,method_name='set_Item',argument_kinds=(11,8))
        proof['getKeyMethod']={'index':methods['getKey'][0].index,'rva':pointer-pe.image_base}
        return proof
    require(len(family['ranges'])==5 and sum(p['codeBytes'] for p in family['ranges'])<=4096,'get-key-bounded-owned-family',family['ranges'])
    partitions={}
    for part in family['ranges']:
        begin,end,_=part['runtimeTriple'];body=pe.bytes_at_va(pe.image_base+begin,end-begin)
        partitions[pe.image_base+begin]=(_instruction_partition(body,pe.image_base+begin,_composed_decoder(image.mapper)),part,hashlib.sha256(body).hexdigest().upper())
    require(pointer in partitions,'get-key-primary-owned-start',pointer)
    prefix=partitions[pointer][0];p={r['offset']:r for r in prefix}
    require(37 in p and 43 in p,'get-key-prefix-stage',list(p))
    main_start=_va(p[43])+len(_raw(p[43]));init_start=branch_target(p[37])
    require(main_start in partitions and init_start in partitions,'get-key-explicit-main-init-starts',(main_start,init_start))
    main=partitions[main_start][0];m={r['offset']:r for r in main}
    require(23 in m and 32 in m and 68 in m,'get-key-main-stage',list(m))
    cold_start=branch_target(m[32])-79;exception_start=branch_target(m[68])
    require(cold_start in partitions and exception_start in partitions,'get-key-explicit-cold-exception-starts',(cold_start,exception_start))
    starts={'prefix':pointer,'main':main_start,'init':init_start,'cold':cold_start,'exception':exception_start}
    require(len(set(starts.values()))==5,'get-key-distinct-owned-parts',starts)
    parts={role:partitions[start][0] for role,start in starts.items()}
    proof=check_get_key_program(parts,methods,contract['getKeyPrograms'])
    lookup_pointer,lookup_context=dictionary_context(image,m[74],m[89],map_field,method_name='TryGetValue',argument_kinds=(11,8))
    setter_pointer,setter_context=dictionary_context(image,m[196],m[209],map_field,method_name='set_Item',argument_kinds=(11,8))
    proof['lookupContext']=lookup_context;proof['setterContext']=setter_context
    proof['bodyParts']={role:{'runtimeTriple':partitions[start][1]['runtimeTriple'],'sha256':partitions[start][2]} for role,start in starts.items()}
    proof['getKeyMethod']={'index':methods['getKey'][0].index,'rva':pointer-pe.image_base}
    proof['unwindOwnership']=family;proof['unwindInstructionSemanticsProved']=False
    return proof


def dictionary_context(image,row,call_row,field,*,method_name,argument_kinds):
    md=image.metadata;pe=image.pe;reg=image.registration
    raw=_raw(row)
    signatures={'TryGetValue':('Boolean',(0,0x20)), 'set_Item':('Void',(0,0))}
    require(method_name in signatures and len(argument_kinds)==2,'supported-dictionary-request',method_name)
    return_type,parameter_flags=signatures[method_name]
    require(raw[:3]==bytes.fromhex('4C8B0D') and len(raw)==7,'dictionary-context-load',row)
    cell=_va(row)+7+struct.unpack_from('<i',raw,3)[0]
    spec=method_spec_usage_index(pe.bytes_at_va(cell,8),reg['methodSpecsCount'],source=str(image.gameassembly),offset=cell)
    definition,class_inst,method_inst=struct.unpack('<iii',pe.bytes_at_va(int(reg['methodSpecs'],16)+spec*12,12))
    require(0<=definition<len(md.methods) and 0<=class_inst<reg['genericInstsCount'] and method_inst==-1,
            'dictionary-context-roster',(definition,class_inst,method_inst))
    method=md.methods[definition];selected=NativeReferenceContext(image)
    extent=closed_generic_reference_extent(selected,field.type_index)
    require(method.declaring_type==extent['definitionTypeIndex'] and
            md.type_full_name(md.types[method.declaring_type])=='System.Collections.Generic.Dictionary`2' and
            md.string(method.name_index)==method_name and not method.flags&0x10,
            'dictionary-concrete-owner',definition)
    _abi(image,method.return_type,return_type,'dictionary-return')
    params=md.parameters_for(method);require(len(params)==2,'dictionary-arity',len(params))
    for ordinal,param in enumerate(params):
        record=_type_record(image,param.type_index)
        require(record[10]==0x13 and record[11]==parameter_flags[ordinal],'dictionary-generic-parameter',record.hex())
        owner=type_parameter_owner(md.buf,struct.unpack_from('<Q',record)[0],
                                   [td.generic_container_index for td in md.types],source=str(image.metadata_path))
        require(owner['typeIndex']==method.declaring_type and owner['ordinal']==ordinal,'dictionary-parameter-owner',owner)
    arguments=image.instantiations.resolve(class_inst).arguments
    require(len(arguments)==2,'dictionary-arguments',len(arguments))
    generic=struct.unpack_from('<Q',bytes.fromhex(extent['declaredTypeRecordHex']))[0]
    argc,argv=struct.unpack('<QQ',pe.bytes_at_va(pe.u64_at_va(generic+8),16))
    require(argc==2,'field-argument-count',argc)
    for ordinal,(arg,kind) in enumerate(zip(arguments,argument_kinds)):
        raw=bytes.fromhex(arg.raw_type_record_hex)
        require(raw[10]==kind and raw[11]&0x7f==0 and raw==pe.bytes_at_va(pe.u64_at_va(argv+ordinal*8),16),
                'same-field-context-primitive',raw.hex())
    code=image.mapper.code_registration_summary(pe,image.code_registration);table=int(reg['genericMethodTable'],16)
    candidates=generic_method_candidates(pe.bytes_at_va(table,reg['genericMethodTableCount']*16),reg['genericMethodTableCount'],
        reg['methodSpecsCount'],{spec},code['genericMethodPointersCount'],code['invokerPointersCount'],source=str(image.gameassembly),offset=table)
    require(len(candidates)==1,'dictionary-pointer-candidates',len(candidates))
    pointer=pe.u64_at_va(int(code['genericMethodPointers'],16)+candidates[0]['indices'][0]*8)
    require(pointer==branch_target(call_row),'dictionary-actual-pointer',(pointer,call_row))
    return pointer,{'methodSpecIndex':spec,'definition':definition,'classInstantiation':class_inst,
                    'fieldType':extent['type'],'argumentRawHex':[a.raw_type_record_hex for a in arguments]}


def _selected_program(image,pointer,range_count,label):
    """Every selected unwind range is decoded; sparse gaps remain unowned."""
    family=image.unwind_index.family(pointer-image.pe.image_base)
    require(len(family['ranges'])==range_count and sum(p['codeBytes'] for p in family['ranges'])<=4096,
            label+'-bounded-complete-family',family['ranges'])
    fragments=[];parts=[]
    for record in family['ranges']:
        start,end,_=record['runtimeTriple'];raw=image.pe.bytes_at_va(image.pe.image_base+start,end-start)
        fragments.append({'startRva':image.pe.image_base+start,'rawHex':raw.hex()})
        parts.append({'runtimeTriple':record['runtimeTriple'],'sha256':hashlib.sha256(raw).hexdigest().upper()})
    program=_program_from_fragments(pointer,fragments,_composed_decoder(image.mapper))
    program['unwindOwnership']=family;program['bodyParts']=parts
    return program


def _inline_original_selection(p,branch,resume,epilogue,kind):
    """Prove the direct original path and its null-pointer resume, not replacement behavior."""
    row=p['by'][branch];entry=branch_target(row)-p['base']
    _branch_at(p,branch,'0F85',entry,kind+'-manager-selection')
    source='498B81' if kind=='counter' else '488B81'
    raw=_raw(p['by'][entry]);require(len(raw)==7 and raw[:3]==bytes.fromhex(source),kind+'-function-load',p['by'][entry])
    slot=struct.unpack_from('<I',raw,3)[0]
    _expect_at(p,entry+7,'4885C0',kind+'-function-null-test')
    _branch_at(p,entry+10,'0F84',resume,kind+'-original-null-resume')
    if kind=='counter':
        _expect_at(p,entry+16,'4C8BC2488BD1',kind+'-replacement-carried-arguments')
        context_at=entry+22;prefix='498B89';call=entry+29
    elif kind=='lookup':
        context_at=entry+16;prefix='488B89'
        _expect_at(p,entry+23,'4C8BCE4C8BC348896C2420488BD7',kind+'-replacement-carried-arguments')
        call=entry+37
    else:
        require(kind=='getKey','inline-selection-kind',kind)
        _expect_at(p,entry+16,'0F1003','get-key-replacement-source-copy')
        context_at=entry+19;prefix='488B89'
        _expect_at(p,entry+26,'4C8D442440440FB6CD4889742420488BD70F29442440',
                   'get-key-replacement-carried-arguments')
        call=entry+48
    context=_raw(p['by'][context_at])
    require(len(context)==7 and context[:3]==bytes.fromhex(prefix) and struct.unpack_from('<I',context,3)[0]==slot+8,
            kind+'-same-replacement-context-slot',p['by'][context_at])
    _expect_at(p,call,'FFD090',kind+'-replacement-invocation-boundary')
    _branch_at(p,call+3,'E9',epilogue,kind+'-replacement-epilogue')
    return entry


def _current_counter(p):
    _expect_at(p,0,'4883EC28','counter-current-frame')
    root=_rip_load_cell(p,4,'488B05','counter-current-root')
    _expect_at(p,11,'4C8B48704D85C9','counter-current-manager')
    _inline_original_selection(p,18,24,38,'counter')
    _expect_at(p,24,'83792000','counter-current-signed-field-test')
    _branch_at(p,28,'7C',43,'counter-current-negative-reset')
    _expect_at(p,30,'8B4120FFC08941204883C428C3C7412000000000','counter-current-load-increment-store-reset')
    _branch_at(p,50,'EB',30,'counter-current-reset-join')
    require(p['by'][33].get('operandWidth')==32 and p['by'][33].get('upperRegisterEffect')=='zero upper 32 bits',
            'counter-current-INC32',p['by'][33])
    return root,{'negativeInput':1,'nonnegativeInput':'(stored UInt32 bits + 1) modulo 2^32',
        'writesSameField':True,'globalUniquenessProved':False,'runtimeObserved':False,
        'originalPathSelection':'direct original path or null replacement-pointer resume',
        'unwindOwnership':p['unwindOwnership'],'bodyParts':p['bodyParts']}


def _same_flag(p,test_at,write_at,label):
    tested=_raw(p['by'][test_at]);written=_raw(p['by'][write_at])
    require(len(tested)==len(written)==7 and tested[:2]==b'\x80\x3d' and tested[-1]==0 and
        written[:2]==b'\xc6\x05' and written[-1]==1 and
        test_at+7+struct.unpack_from('<i',tested,2)[0]==write_at+7+struct.unpack_from('<i',written,2)[0],
        label+'-same-initialization-flag',(p['by'][test_at],p['by'][write_at]))


def _current_lookup(p,hash_pointer,dictionary_pointer):
    _expect_at(p,0,'48895C240848896C24104889742418574883EC30','lookup-current-frame')
    _expect_at(p,27,'498BE9498BF0488BDA488BF9','lookup-current-original-inputs')
    _branch_at(p,39,'74',143,'lookup-current-context-init')
    root=_rip_load_cell(p,41,'488B05','lookup-current-root')
    _expect_at(p,48,'488B48704885C9','lookup-current-manager')
    _inline_original_selection(p,55,61,112,'lookup')
    _expect_at(p,61,'4885DB','lookup-current-null-string')
    _branch_at(p,64,'74',133,'lookup-current-null-result')
    _expect_at(p,66,'837B1000','lookup-current-string-length')
    _branch_at(p,70,'76',133,'lookup-current-empty-result')
    _expect_at(p,72,'488B7F1033D2488BCB','lookup-current-map-and-string-hash-argument')
    _call_at(p,81,hash_pointer,'lookup-current-typed-hash')
    _expect_at(p,86,'4885FF','lookup-current-null-map')
    _branch_at(p,89,'74',164,'lookup-current-map-exception')
    context=_rip_load_cell(p,91,'4C8B0D','lookup-current-dictionary-context')
    _expect_at(p,98,'4C8BC6488BD0488BCF','lookup-current-output-hash-and-map')
    _call_at(p,107,dictionary_pointer,'lookup-current-dictionary-request')
    _expect_at(p,112,'488B5C2440488B6C2448488B7424504883C4305FC3C706FFFFFFFF32C0',
               'lookup-current-return-and-null-output')
    _branch_at(p,141,'EB',112,'lookup-current-null-return')
    require(_rip_load_cell(p,143,'488D0D','lookup-current-init-context')==context,
            'lookup-current-same-initialized-context',context)
    _call_target(p,150,'lookup-current-context-initializer')
    _same_flag(p,20,155,'lookup-current')
    _branch_at(p,162,'EB',41,'lookup-current-initialized-entry')
    _call_target(p,164,'lookup-current-exception-helper');_expect_at(p,169,'CC','lookup-current-exception-terminal')
    for start,end,register,allowed,label in ((86,107,'rax',set(),'hash-result'),(112,133,'rax',set(),'dictionary-Boolean'),
        (76,107,'rdi',{81},'saved-map'),(33,107,'rsi',{81},'original-output')):
        _preserved_interval(p['rows'],start,end,register,allowed,'current-lookup-'+label)
    return root,{'nonemptyRequest':'selected UInt64 hash return to Dictionary<UInt64,Int32>.TryGetValue',
        'normalReturn':'same dictionary Boolean return and original referenced Int32 output',
        'nullOrEmpty':'false; referenced Int32 written -1','hashAlgorithmProved':False,'keyStabilityProved':False,
        'runtimeObserved':False,'originalPathSelection':'direct original path or null replacement-pointer resume',
        'unwindOwnership':p['unwindOwnership'],'bodyParts':p['bodyParts']}


def _current_get_key(p,methods):
    """Complete seven-range shape; evaluate only original/false-Boolean paths."""
    _expect_at(p,0,'48895C241048896C24184889742420574883EC50','get-key-current-frame')
    _expect_at(p,27,'498BF1410FB6E8488BDA488BF9','get-key-current-original-inputs')
    _branch_at(p,40,'0F84',345,'get-key-current-entry-init')
    root=_rip_load_cell(p,46,'488B05','get-key-current-root')
    _expect_at(p,53,'488B48704885C9','get-key-current-manager')
    replacement=_inline_original_selection(p,60,66,200,'getKey')
    _expect_at(p,66,'837B0800C744243000000000','get-key-current-zero-lane-and-output-local')
    _branch_at(p,78,'0F84',417,'get-key-current-zero-lane')
    _expect_at(p,84,'4C897424600F100333D2488D4C24400F29442440','get-key-current-span-copy')
    _call_at(p,104,methods['spanHash'][1],'get-key-current-typed-span-hash')
    _expect_at(p,109,'488B4F10488BF04885C9','get-key-current-map-and-saved-hash')
    _branch_at(p,119,'0F84',339,'get-key-current-lookup-null-map')
    lookup_cell=_rip_load_cell(p,125,'4C8B0D','get-key-current-lookup-context')
    _expect_at(p,132,'4C8D442430488BD0','get-key-current-output-local-and-hash-key')
    _call_target(p,140,'get-key-current-dictionary-lookup')
    _expect_at(p,145,'84C0','get-key-current-lookup-result')
    _branch_at(p,147,'74',221,'get-key-current-miss-to-counter')
    _expect_at(p,149,'8B7424304084ED','get-key-current-hit-output-and-original-Boolean')
    _branch_at(p,156,'74',193,'get-key-current-false-Boolean-hit-return')
    _expect_at(p,158,'488B4F184885C9','get-key-current-unselected-hit-receiver')
    _branch_at(p,165,'0F84',339,'get-key-current-unselected-hit-null')
    _rip_load_cell(p,171,'4C8B05','get-key-current-unselected-hit-context')
    _expect_at(p,178,'8BD6','get-key-current-unselected-hit-argument')
    _call_target(p,180,'get-key-current-unselected-hit-request')
    _expect_at(p,185,'84C0','get-key-current-unselected-hit-test')
    keep=branch_target(p['by'][187])-p['base']
    _branch_at(p,187,'0F84',keep,'get-key-current-unselected-hit-cold')
    _expect_at(p,193,'8BC64C8B742460488B5C2468488B6C2470488B7424784883C4505FC3',
               'get-key-current-hit-return-and-frame')
    _expect_at(p,221,'33D2488BCF','get-key-current-counter-arguments')
    _call_at(p,226,methods['counter'][1],'get-key-current-typed-counter')
    _expect_at(p,231,'488B4F10448BF04885C9','get-key-current-saved-counter-and-same-map')
    _branch_at(p,241,'74',339,'get-key-current-setter-null-map')
    setter_cell=_rip_load_cell(p,243,'4C8B0D','get-key-current-setter-context')
    _expect_at(p,250,'448BC0488BD6','get-key-current-counter-value-and-retained-hash')
    _call_target(p,256,'get-key-current-dictionary-setter')
    _expect_at(p,261,'4084ED','get-key-current-original-Boolean-miss-test')
    _branch_at(p,264,'75',271,'get-key-current-unselected-true-Boolean')
    _expect_at(p,266,'418BC6','get-key-current-counter-return-value')
    _branch_at(p,269,'EB',195,'get-key-current-counter-return-frame')
    _expect_at(p,271,'488B7F1833C9','get-key-current-unselected-miss-receiver')
    request=_call_target(p,277,'get-key-current-unselected-carrier-request')
    _expect_at(p,282,'4885C0','get-key-current-unselected-carrier-test')
    _branch_at(p,285,'74',339,'get-key-current-unselected-carrier-null')
    copy='0F10034533C0488D542440488BC80F29442440'
    _expect_at(p,287,copy,'get-key-current-unselected-carrier-copy')
    conversion=_call_target(p,306,'get-key-current-unselected-conversion')
    _expect_at(p,311,'4885FF','get-key-current-unselected-map-test')
    _branch_at(p,314,'74',339,'get-key-current-unselected-map-null')
    keep_cell=_rip_load_cell(p,316,'4C8B0D','get-key-current-unselected-map-context')
    _expect_at(p,323,'4C8BC0418BD6488BCF','get-key-current-unselected-map-arguments')
    store=_call_target(p,332,'get-key-current-unselected-map-request')
    _branch_at(p,337,'EB',266,'get-key-current-unselected-miss-return')
    _call_target(p,339,'get-key-current-exception-helper');_expect_at(p,344,'CC','get-key-current-exception-terminal')
    initialized={}
    for at in (345,357,369,381,393):
        initialized[at]=_rip_load_cell(p,at,'488D0D','get-key-current-entry-context')
    initializer=_call_target(p,352,'get-key-current-entry-initializer')
    for at in (364,376,388,400):_call_at(p,at,initializer,'get-key-current-same-entry-initializer')
    require(initialized[345]==_rip_load_cell(p,171,'4C8B05','get-key-current-hit-init-join') and
        initialized[357]==lookup_cell and initialized[369]==setter_cell and initialized[381]==keep_cell,
        'get-key-current-same-request-initialization',initialized)
    _same_flag(p,20,405,'get-key-current')
    _branch_at(p,412,'E9',46,'get-key-current-initialized-entry')
    _expect_at(p,417,'B8FFFFFFFF','get-key-current-zero-lane-minus-one')
    _branch_at(p,422,'E9',200,'get-key-current-zero-lane-return-frame')
    # The second distant fragment is owned and partitioned even though its
    # keep-true path is outside the original-false-Boolean claim.
    _expect_at(p,keep,'488B7F1833C9','get-key-current-cold-unselected-receiver')
    _call_at(p,keep+6,request,'get-key-current-same-cold-carrier-request')
    _expect_at(p,keep+11,'4885C0','get-key-current-cold-carrier-test')
    _branch_at(p,keep+14,'0F84',339,'get-key-current-cold-carrier-null')
    _expect_at(p,keep+20,copy,'get-key-current-cold-carrier-copy')
    _call_at(p,keep+39,conversion,'get-key-current-same-cold-conversion')
    _expect_at(p,keep+44,'4885FF','get-key-current-cold-map-test')
    _branch_at(p,keep+47,'0F84',339,'get-key-current-cold-map-null')
    require(_rip_load_cell(p,keep+53,'4C8B0D','get-key-current-cold-map-context')==keep_cell,
            'get-key-current-same-cold-map-context',keep_cell)
    _expect_at(p,keep+60,'4C8BC08BD6488BCF','get-key-current-cold-map-arguments')
    _call_at(p,keep+68,store,'get-key-current-same-cold-map-request')
    _expect_at(p,keep+73,'90','get-key-current-cold-nop')
    _branch_at(p,keep+74,'E9',193,'get-key-current-cold-hit-return')
    paths=_current_get_key_paths(p,replacement)
    return {'flagSelection':'original Boolean false','zeroAnonymousInt32LaneAt8':'Int32 -1',
        'nonzeroLaneLookupHit':'successful referenced Int32 lookup output returned',
        'nonzeroLaneLookupMiss':'typed counter return sent to same UInt64/Int32 dictionary setter and returned',
        'instanceSpanFieldLayoutProved':False,'hashAlgorithmProved':False,'dictionaryMutationProved':False,
        'globalUniquenessProved':False,'runtimeObserved':False,'normalPaths':len(paths),
        'conditions':['valid original value carrier and receiver, selected original path, original Boolean false, nonnull dictionary',
                      'normal returning Win64 callees preserve nonvolatile registers and caller locals'],
        'originalPathSelection':'direct original path or null replacement-pointer resume',
        'replacementRootCellVa':root,'bodyParts':p['bodyParts'],'unwindOwnership':p['unwindOwnership'],
        'unwindInstructionSemanticsProved':False}


def _current_get_key_paths(p,replacement):
    """Visit both original entries and all three value exits, with full path preservation."""
    by={_va(row):row for row in p['rows']};base=p['base'];paths=[]
    choices={base+replacement+10:True,base+119:False,base+156:True,base+241:False,base+264:False}
    def walk(va,path):
        require(len(path)<512 and len(paths)<32,'get-key-current-CFG-bound',(len(path),len(paths)))
        require(va in by and va not in path,'get-key-current-CFG-owned-acyclic-edge',va)
        row=by[va];raw=_raw(row);path=path+[va]
        if row['text']=='ret':paths.append(path);return
        require(row['text']!='int3','get-key-current-selected-exception',row)
        fallthrough=va+len(raw)
        conditional=(len(raw)==2 and 0x70<=raw[0]<=0x7f) or (len(raw)==6 and raw[0]==15 and 0x80<=raw[1]<=0x8f)
        if conditional:
            choice=choices.get(va)
            successors=[branch_target(row)] if choice is True else [fallthrough] if choice is False else [fallthrough,branch_target(row)]
        else:successors=[branch_target(row)] if row['text'].startswith('jmp ') else [fallthrough]
        for successor in successors:walk(successor,path)
    walk(base,[])
    require(len(paths)==12 and all(path[-1]==base+220 for path in paths),'get-key-current-twelve-normal-paths',len(paths))
    calls={va for path in paths for va in path if by[va]['text'].startswith('call ')}
    for path in paths:
        selected=[by[va] for va in path]
        def interval(start,end):return selected[path.index(base+start)+1:path.index(base+end)]
        _register_preserved(interval(30,205),('rbp',),calls)
        _register_preserved(interval(34,200),('rbx',),calls)
        _register_preserved(interval(37,200),('rdi',),calls)
        if base+226 in path:
            _register_preserved(interval(235,266),('r14',),calls)
            _register_preserved(interval(113,256),('rsi',),calls)
            _register_preserved(selected[path.index(base+231):path.index(base+250)],('rax',),calls)
        values=[offset for offset in (193,266,417) if base+offset in path]
        require(len(values)==1,'get-key-current-one-value-source',values)
        _register_preserved(selected[path.index(base+values[0])+1:],('rax',),set())
        if base+149 in path:
            for row in interval(140,149):
                require(not row['text'].startswith(('mov [','movups [','movaps [','push ','pop ','add rsp','sub rsp','call ')),
                        'get-key-current-output-local-preserved',row)
        if base+89 in path:
            for row in interval(89,99):
                require((row.get('write') or {}).get('register')!='xmm0' and not row['text'].startswith('call '),
                        'get-key-current-mechanical-copy-preserved',row)
    return paths


def validate(image,contract):
    methods,bodies=_methods(image,contract);md=image.metadata;pe=image.pe
    string_spec=contract['stringLength']
    string_owners=[td for td in md.types if md.type_full_name(td)==string_spec['owner']]
    require(len(string_owners)==1,'concrete-string-owner',len(string_owners))
    string_fields=[f for f in md.fields_for(string_owners[0]) if md.string(f.name_index)==string_spec['name']]
    require(len(string_fields)==1,'string-length-field',len(string_fields))
    field=string_fields[0]
    _abi(image,field.type_index,'Int32','string-length-Int32')
    require(not int.from_bytes(_type_record(image,field.type_index)[8:10],'little')&0x10 and
            runtime_type_field_offsets(md,pe,image.registration,string_owners[0].index)[string_spec['name']]==string_spec['offset'],
            'string-length-layout',string_spec)
    owner=md.types[methods['lookup'][0].declaring_type]
    offsets=runtime_type_field_offsets(md,pe,image.registration,owner.index)
    fields={}
    for role,spec in contract['fields'].items():
        candidates=[f for f in md.fields_for(owner) if md.string(f.name_index)==spec['name']]
        require(len(candidates)==1,'provider-field-'+role,len(candidates));field=candidates[0]
        require(not int.from_bytes(_type_record(image,field.type_index)[8:10],'little')&0x10 and
                offsets[spec['name']]==spec['offset'],'provider-field-role-'+role,offsets)
        fields[role]=field
    _abi(image,fields['counter'].type_index,'Int32','counter-field-ABI')
    roots=[];lookup_rows=bodies['lookup']['rows'];counter_rows=bodies['counter']['rows']
    current_lookup=bodies['lookup']['bytes']==170 and _raw(lookup_rows[1])==bytes.fromhex('48896C2410')
    current_counter=bodies['counter']['bytes']==52 and _raw(counter_rows[0])==bytes.fromhex('4883EC28')
    if current_lookup:
        lookup_program=_selected_program(image,methods['lookup'][1],2,'lookup-current')
        context_row=lookup_program['by'][91];call_row=lookup_program['by'][107]
    else:context_row,call_row=lookup_rows[24],lookup_rows[28]
    pointer,context=dictionary_context(image,context_row,call_row,fields['map'],method_name='TryGetValue',argument_kinds=(11,8))
    if current_counter:
        root,counter=_current_counter(_selected_program(image,methods['counter'][1],2,'counter-current'));roots.append(root)
    else:counter=check_counter(counter_rows,methods['patch'][1],contract['programs']['counter'])
    if current_lookup:
        root,lookup=_current_lookup(lookup_program,methods['hash'][1],pointer);roots.append(root)
    else:lookup=check_lookup(lookup_rows,methods['patch'][1],methods['hash'][1],pointer,contract['programs']['lookup'])
    key_source=get_key_value_source(image,methods,contract,fields['map'])
    if 'replacementRootCellVa' in key_source:roots.append(key_source['replacementRootCellVa'])
    require(not roots or len(set(roots))==1,'same-provider-original-selection-root',roots)
    field_proof={role:{'name':contract['fields'][role]['name'],'offset':offsets[contract['fields'][role]['name']],
                      'ownerDefinition':owner.index,'rawTypeHex':_type_record(image,f.type_index).hex().upper()}
                 for role,f in fields.items()}
    field_proof['stringLength']={'name':string_spec['name'],'offset':string_spec['offset'],'ownerDefinition':string_owners[0].index,
                                'rawTypeHex':_type_record(image,string_fields[0].type_index).hex().upper()}
    return {'counter':counter,'lookup':lookup,'getKeyValueSource':key_source,'context':context,'fields':field_proof,
            'bodies':{role:{k:v for k,v in body.items() if k!='rows'} for role,body in bodies.items()},
            'methods':{role:{'index':m.index,'rva':p-pe.image_base,'definition':m.declaring_type} for role,(m,p) in methods.items()}}


def validate_native_claims(gameassembly,metadata,inputs):
    contract,_=read_reviewed_contract(CONTRACT,schema=SCHEMA,status='reviewed',label='mission_string_providers')
    by_name={Path(row['path']).name:row for row in inputs}
    gate=check_installed_native_inputs(by_name['GameAssembly.dll']['sha256'],by_name['global-metadata.dat']['sha256'],gameassembly=gameassembly,metadata=metadata)
    require(gate.status==NATIVE_EVIDENCE_VALIDATED,'native-inputs',f'{gate.status}:{gate.detail}')
    proof=validate(open_native_image(gameassembly,metadata),contract)
    return {'format':'endfield.dynamic-mission-string-providers-native-audit.v2','status':'validated','proof':proof,
            'nativeInputs':{name:row['sha256'] for name,row in by_name.items()},'evidenceBoundary':contract['evidenceBoundary']}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gameassembly',type=Path,required=True);parser.add_argument('--metadata',type=Path,required=True)
    parser.add_argument('--output-json',type=Path,default=REPO_ROOT/'reports/animestudio/dynamic_mission_string_providers_native_latest.json')
    args=parser.parse_args(argv)
    try:
        sources=_parser_source_snapshots(Path(__file__))+[_fingerprint(p) for p in (CONTRACT,NATIVE_MAPPER_PATH,METADATA_HELPER_PATH)]
        inputs=[_fingerprint(p) for p in (args.gameassembly,args.metadata,args.gameassembly.parent/'UnityPlayer.dll')]
        protected=[Path(row['path']) for row in sources+inputs];groups._guard_publication(args.output_json,protected)
        result=validate_native_claims(args.gameassembly,args.metadata,inputs)
        result['proofSources']=sources;result['proofInputs']=inputs
        encoded=json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n'
        groups._require_unchanged(sources+inputs);groups._guard_publication(args.output_json,protected)
        atomic_write_text(args.output_json,encoded)
    except (OSError,ValueError,KeyError,IndexError,RuntimeError,struct.error) as exc:
        print('mission-string-providers:'+str(exc)[:1400],file=sys.stderr);return 1
    print('Mission string providers passed: typed lookup, counter and normal GetStrKey value sources; hash/live keys unresolved')
    return 0


if __name__=='__main__':raise SystemExit(main())
