"""Authenticate the selected stored MissionCondition comparison offline.

Complete declared unwind families and sparse instruction/branch joins bind the
query, vector carrier, State/IsSame getters, equality selector and changed flag.
Replacement null-resume and zero-vector carrier paths have explicit checks.
The proof is conditional on normal returns and the selected stored-reader
paths; provider/cache ownership, live values and runtime truth remain unresolved.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
import re
import sys
from pathlib import Path

if __name__=='__main__' and not __package__:
    raise SystemExit('Run with python -m scripts.game_data.dynamic_mission_condition_consumers_native')

from scripts.common import check_installed_native_inputs, NATIVE_EVIDENCE_VALIDATED
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract, NATIVE_MAPPER_PATH, METADATA_HELPER_PATH
from scripts.game_data.il2cpp.integer_registers import decode_integer_register_instructions
from scripts.game_data.il2cpp.integer_byte_operations import decode_byte_register_logic
from scripts.game_data.il2cpp.integer_widths import _byte
from scripts.game_data.il2cpp.context import method_spec_usage_index, generic_method_candidates, type_parameter_owner
from scripts.game_data.dynamic_erosion_consumers_native import (_check_method, _ordinary_primitive_abi, _raw_type_abi, _mov_register,
    _lea_stack, _method_call_abi, _instruction_partition, _direct_call_boundary, _preserved_interval)
from scripts.game_data.dynamic_scalar_components_native import _getter_offset, _relative_call_target, _validate_carriers
from scripts.game_data.memorypack.corpus_gate import _fingerprint, _parser_source_snapshots
from scripts.game_data import dynamic_group_components_native as groups
from scripts.game_data.corpus_common import atomic_write_text
from scripts.repo_paths import REPO_ROOT

CONTRACT=CONTRACTS_DIR / 'dynamic_mission_condition_consumers_native.json'
SCHEMA='endfield.dynamic-mission-condition-consumers-native-contract.v4'


def _require(condition,check,expected,actual):
    if not condition:
        raise ValueError(f'mission_condition_consumers:{check}:expected={str(expected)[:320]} actual={str(actual)[:320]}')


def compare_condition_state(value:int,state:int,is_same:int)->bool:
    """Selected comparison only; caller supplies the unresolved native value."""
    for name,number in (('value',value),('state',state),('is_same',is_same)):
        _require(type(number) is int and -(1<<31)<=number<(1<<31),'comparison-input-'+name,'stored/native Int32',number)
    return value==state if is_same==1 else value!=state


def _vector_return_abi(image,method):
    bits=_raw_type_abi(image,method.return_type,'mission-vector-proxy-return')
    _require((bits>>16)&0xff==0x11 and (bits>>24)&0x7f==0,
             'ordinary-vector-value-return','value kind11; low seven flags zero',f'rawBits={bits:08X}')


def _query_context(image,raw,query,pins):
    pe=image.pe;reg=image.registration;at=pins['contextLoadOffset']
    _require(raw[at:at+3]==bytes.fromhex('4C8B0D') and raw[at:at+7].hex().upper()==pins['contextLoadRawHex'],
             'query-context-load',pins['contextLoadRawHex'],raw[at:at+7].hex())
    cell_rva=query['rva']+at+7+struct.unpack_from('<i',raw,at+3)[0]
    _require(cell_rva==pins['usageCellRva'],'query-context-cell',pins['usageCellRva'],cell_rva)
    cell=pe.image_base+cell_rva;usage=pe.bytes_at_va(cell,8)
    _require(usage.hex().upper()==pins['usageRawHex'],'query-usage-bytes',pins['usageRawHex'],usage.hex())
    spec=method_spec_usage_index(usage,reg['methodSpecsCount'],source=str(image.gameassembly),offset=cell)
    _require(spec==pins['methodSpecIndex'],'query-selected-spec',pins['methodSpecIndex'],spec)
    spec_va=int(reg['methodSpecs'],16)+spec*12;spec_raw=pe.bytes_at_va(spec_va,12)
    _require(spec_raw.hex().upper()==pins['methodSpecRawHex'],'query-spec-bytes',pins['methodSpecRawHex'],spec_raw.hex())
    definition,class_inst,method_inst=struct.unpack('<iii',spec_raw)
    _require(definition==pins['definition'] and 0<=definition<len(image.metadata.methods) and
             class_inst==pins['classInstantiationIndex'] and 0<=class_inst<reg['genericInstsCount'] and method_inst==-1,
             'query-spec-roster','selected concrete class-only MethodSpec',(definition,class_inst,method_inst))
    method=image.metadata.methods[definition]
    _require(image.metadata.type_full_name(image.metadata.types[method.declaring_type])==pins['type'] and
             image.metadata.string(method.name_index)==pins['method'] and not method.flags&0x10,
             'query-generic-method','selected instance Dictionary.TryGetValue',definition)
    _ordinary_primitive_abi(image,method.return_type,0x02,'query-dictionary-return')
    parameters=image.metadata.parameters_for(method)
    _require(len(parameters)==2,'query-generic-parameters',2,len(parameters))
    for ordinal,param in enumerate(parameters):
        bits=_raw_type_abi(image,param.type_index,'query-dictionary-parameter')
        _require((bits>>16)&0xff==0x13 and bits>>24==(0 if ordinal==0 else 0x20),
                 'query-generic-parameter-abi-'+str(ordinal),'VAR flags key00/value20',f'{bits:08X}')
        pointer=pe.u64_at_va(int(reg['types'],16)+param.type_index*8);record=pe.bytes_at_va(pointer,16)
        expected=pins['signature']['parameters'][ordinal]
        _require(record.hex().upper()==expected['rawTypeRecordHex'],'query-parameter-record',expected['rawTypeRecordHex'],record.hex())
        owner=type_parameter_owner(image.metadata.buf,struct.unpack_from('<Q',record)[0],
            [row.generic_container_index for row in image.metadata.types],source=str(image.metadata_path))
        _require(owner['typeIndex']==method.declaring_type and owner['ordinal']==ordinal,
                 'query-generic-owner','same concrete Dictionary owner and ordinal',(owner['typeIndex'],owner['ordinal']))
    inst=image.instantiations.resolve(class_inst)
    _require(len(inst.arguments)==2,'query-concrete-arguments',2,len(inst.arguments))
    for arg in inst.arguments:
        record=bytes.fromhex(arg.raw_type_record_hex)
        _require(record[10]==0x08 and record[11]&0x7f==0,'query-concrete-Int32','ordinary Int32',record.hex())
    code=image.mapper.code_registration_summary(pe,image.code_registration);table=int(reg['genericMethodTable'],16)
    candidates=generic_method_candidates(pe.bytes_at_va(table,reg['genericMethodTableCount']*16),
        reg['genericMethodTableCount'],reg['methodSpecsCount'],{spec},code['genericMethodPointersCount'],
        code['invokerPointersCount'],source=str(image.gameassembly),offset=table)
    _require(len(candidates)==1,'query-pointer-candidates','one explicitly selected MethodSpec candidate',len(candidates))
    slot=candidates[0]['indices'][0]
    _require(slot==pins['methodPointerIndex'],'query-pointer-slot',pins['methodPointerIndex'],slot)
    pointer=pe.u64_at_va(int(code['genericMethodPointers'],16)+slot*8)
    target=_relative_call_target(raw,query['rva'],pins['callOffset'],'query-TryGetValue-call')
    _require(target==pins['callTargetRva'] and pointer==pe.image_base+target,
             'query-context-call','selected MethodSpec pointer equals direct call',(target,pointer))
    return {'methodSpecIndex':spec,'classArguments':['System.Int32','System.Int32'],'method':pins['type']+'.'+pins['method']}


def _composed_decoder(mapper):
    class ByteSubset:
        def decode_one_x64(self,raw,offset,start_va):
            at=offset;rex=0
            if raw[offset:offset+1]==b'\x34':
                _require(offset+2<=len(raw),'byte-xor-truncated','XOR AL,imm8',raw[offset:].hex())
                immediate=raw[offset+1];stop=offset+2
                return {'offset':offset,'va':hex(start_va+offset),'bytes':raw[offset:stop].hex(' '),
                    'text':f'xor al, 0x{immediate:x}',
                    'byteLogicalOperation':{'operation':'xor','destinationRegister':'al','parentRegister':'rax',
                        'bits':8,'bitOffset':0,'preservesOtherParentBits':True,'zeroExtendsTo64':False,
                        'sourceRegister':None,'immediateWord':immediate,'memoryReadBytes':0,'memoryWriteBytes':0,
                        'clearsFlags':['CF','OF'],'undefinedFlags':['AF'],'writesResultFlags':['SF','ZF','PF']},
                    'write':{'register':'al','value':'modified low byte; other parent bits preserved'}},stop
            if 0<=at<len(raw) and 0x40<=raw[at]<=0x4f:rex=raw[at];at+=1
            if not rex&0x0a and raw[at:at+1]==b'\x22':
                _require(at+2<=len(raw),'byte-and-truncated','complete register ModRM',raw[offset:].hex())
                modrm=raw[at+1]
                if modrm>>6==3:
                    destination=_byte(((modrm>>3)&7)|((rex&4)<<1),rex)
                    source=_byte((modrm&7)|((rex&1)<<3),rex);stop=at+2
                    return {'offset':offset,'va':hex(start_va+offset),'bytes':raw[offset:stop].hex(' '),
                        'text':f'and {destination}, {source}',
                        'write':{'register':destination,'value':'modified low/high byte; other parent bits preserved'}},stop
            result=decode_byte_register_logic(raw,offset,start_va)
            if result is not None:
                row,stop=result
                row['write']={'register':row['byteLogicalOperation']['destinationRegister'],'value':'modified byte; other parent bits preserved'}
                return row,stop
            return mapper.decode_one_x64(raw,offset,start_va)
    def decode(raw,start_va,*,stop_offset):
        _require(stop_offset==len(raw),'decoder-bound','complete bounded primary body',stop_offset)
        return decode_integer_register_instructions(ByteSubset(),raw,start_va)
    return decode


def _cfg_preserved(rows,base,start,stops,register,allowed_calls,selected_fallthrough,visit_check=None):
    """Explore all admitted paths; explicit false-patch edges alone are pruned."""
    by_offset={row['offset']:row for row in rows};states={};reached=set()
    def visit(at):
        if at in stops:reached.add(at);return
        _require(states.get(at)!=1,'cfg-cycle-'+register,'acyclic getter-to-predicate region',at)
        if states.get(at)==2:return
        states[at]=1
        _require(at in by_offset,'cfg-escape-'+register,'owned instruction or admitted stop',at)
        row=by_offset[at];size=len(bytes.fromhex(row['bytes']));next_at=at+size
        if visit_check is not None:visit_check(row)
        _preserved_interval([row],at,next_at,register,allowed_calls,'cfg-'+register)
        text=row['text'];mnemonic=text.split()[0]
        _require(mnemonic not in ('ret','int3'),'cfg-terminal-'+register,'reach predicate before return/exception',row)
        if mnemonic.startswith('j'):
            match=re.fullmatch(r'j[a-z]+ 0x([0-9a-f]+)',text)
            _require(match is not None,'cfg-branch-'+register,'direct decoded branch',row)
            target=int(match.group(1),16)-base
            if at in selected_fallthrough:
                _require(mnemonic!='jmp','cfg-selection-'+register,'conditional non-replacement fallthrough',row)
                successors=[next_at]
            elif mnemonic=='jmp':successors=[target]
            else:successors=[next_at,target]
        else:successors=[next_at]
        for successor in successors:visit(successor)
        states[at]=2
    visit(start)
    _require(reached==set(stops),'cfg-predicate-roster-'+register,sorted(stops),sorted(reached))


def _provider_local_store_check(row):
    """Direct fixed-frame stores only; indirect/callee isolation is conditional."""
    write=row.get('write') or {}
    _require(write.get('register') not in {'rbp','ebp','bp','bpl','rsp','esp','sp','spl'},
             'provider-frame-base','stable RBP/RSP',row)
    mnemonic,_,operands=row['text'].partition(' ')
    destination=operands.split(',',1)[0]
    if not destination.startswith('[') or mnemonic in ('cmp','test'):
        return
    if not destination.startswith('[rbp'):
        _require(not destination.startswith('[rsp'),'provider-rsp-store','no unbound RSP-relative store',row)
        return
    match=re.fullmatch(r'\[rbp(?:([+-])0x([0-9a-f]+))?\]',destination)
    _require(match is not None,'provider-frame-address','simple fixed RBP-relative destination',row)
    offset=int(match.group(2),16)*(1 if match.group(1)=='+' else -1) if match.group(2) else 0
    widths={'movups':16,'movaps':16,'movsd':8,'movss':4}
    width=widths.get(mnemonic)
    if mnemonic=='mov':
        source=operands.split(',',1)[1].strip()
        if re.fullmatch(r'(?:e[a-z]{2}|r(?:[89]|1[0-5])d)',source):width=4
        elif re.fullmatch(r'(?:r[a-z]{2}|r(?:[89]|1[0-5]))',source):width=8
        elif re.fullmatch(r'(?:[abcd][lh]|[sd]il|bpl|spl|r(?:[89]|1[0-5])b)',source):width=1
    _require(width is not None,'provider-frame-store-width','proved fixed-width store',row)
    _require(offset+width<=127 or offset>=131,'provider-local-overlap','store disjoint from RBP+127..130',row)


def _program_from_fragments(base,fragments,decode):
    """Decode each owned range separately; never fill sparse gaps with bytes."""
    _require(bool(fragments),'family-empty','nonempty complete family',fragments)
    rows=[];chunks={};contiguous=bytearray();cursor=base;previous_end=None
    for fragment in fragments:
        start=fragment['startRva'];raw=bytes.fromhex(fragment['rawHex'])
        _require(start not in chunks and raw,'family-range','unique nonempty fragment',start)
        _require(previous_end is None or previous_end<=start,'family-range-overlap','sorted disjoint byte ranges',(previous_end,start))
        previous_end=start+len(raw)
        chunks[start]=raw
        for instruction in _instruction_partition(raw,start,decode):
            row=dict(instruction);row['offset']+=start-base;rows.append(row)
        if start==cursor:contiguous.extend(raw);cursor+=len(raw)
    rows.sort(key=lambda row:row['offset']);by={row['offset']:row for row in rows}
    _require(len(by)==len(rows),'family-overlap','one owner per instruction',base)
    for row in rows:
        at=row['offset'];raw=bytes.fromhex(row['bytes']);mnemonic=row['text'].split()[0]
        if mnemonic.startswith('j'):
            target=_branch_target(row,base)
            _require(target in by,'family-branch-escape','owned instruction start',(at,target))
        if mnemonic not in ('jmp','ret','int3'):
            _require(at+len(raw) in by,'family-fallthrough-escape','owned instruction start',row)
    return {'base':base,'raw':bytes(contiguous),'rows':rows,'by':by,'fragments':fragments}


def _branch_target(row,base):
    match=re.fullmatch(r'j[a-z]+ 0x([0-9a-f]+)',row['text'])
    _require(match is not None,'direct-branch','decoded direct jump',row)
    return int(match.group(1),16)-base


def _family_program(image,method,pins,decode):
    family=json.loads(json.dumps(image.unwind_index.family(method['rva'])))
    def same(expected,actual,path):
        if isinstance(expected,dict) and isinstance(actual,dict):
            _require(set(expected)==set(actual),path+'-keys',sorted(expected),sorted(actual))
            for key in sorted(expected):same(expected[key],actual[key],path+'.'+key)
        elif isinstance(expected,list) and isinstance(actual,list):
            _require(len(expected)==len(actual),path+'-length',len(expected),len(actual))
            for index,(left,right) in enumerate(zip(expected,actual)):same(left,right,path+'.'+str(index))
        else:_require(type(expected) is type(actual) and expected==actual,path,expected,actual)
    same(pins['unwindFamily'],family,'complete-unwind-family-'+method['method'])
    declared=pins['codeRanges'];ranges=family['ranges']
    _require(len(declared)==len(ranges),'family-range-roster',len(ranges),len(declared))
    fragments=[]
    for claim,record in zip(declared,ranges):
        start,end,_=record['runtimeTriple']
        _require((claim['startRva'],claim['endRva'])==(start,end),'family-code-range',(start,end),claim)
        raw=image.pe.bytes_at_va(image.pe.image_base+start,end-start)
        digest=hashlib.sha256(raw).hexdigest().upper()
        _require(digest==claim['sha256'],'family-code-bytes',claim['sha256'],digest)
        fragments.append({'startRva':start,'rawHex':raw.hex()})
    return _program_from_fragments(method['rva'],fragments,decode)


def _expect_at(program,at,hex_bytes,label):
    raw=bytes.fromhex(hex_bytes);by=program['by'];cursor=at
    while cursor<at+len(raw):
        _require(cursor in by,'semantic-instruction-start-'+label,'owned complete instruction',cursor)
        cursor+=len(bytes.fromhex(by[cursor]['bytes']))
    _require(cursor==at+len(raw),'semantic-instruction-end-'+label,cursor,at+len(raw))
    actual=b''.join(bytes.fromhex(row['bytes']) for row in program['rows'] if at<=row['offset']<cursor)
    _require(actual==raw,'semantic-'+label,raw.hex(),actual.hex())


def _branch_at(program,at,opcode,target,label):
    row=program['by'].get(at);prefix=bytes.fromhex(opcode)
    _require(row is not None and bytes.fromhex(row['bytes']).startswith(prefix) and
        _branch_target(row,program['base'])==target,'semantic-branch-'+label,(opcode,target),row)


def _call_at(program,at,target,label):
    row=_direct_call_boundary(program['rows'],at,label)
    raw=bytes.fromhex(row['bytes']);actual=program['base']+at+5+struct.unpack_from('<i',raw,1)[0]
    _require(actual==target,'semantic-call-'+label,target,actual)


def _call_target(program,at,label):
    row=_direct_call_boundary(program['rows'],at,label);raw=bytes.fromhex(row['bytes'])
    return program['base']+at+5+struct.unpack_from('<i',raw,1)[0]


def _rip_load_cell(program,at,prefix,label):
    row=program['by'].get(at);raw=bytes.fromhex(row['bytes']) if row else b''
    _require(len(raw)==7 and raw[:3]==bytes.fromhex(prefix),'rip-load-'+label,prefix,row)
    return program['base']+at+7+struct.unpack_from('<i',raw,3)[0]


def _replacement(program,branch,resume,epilogue,kind):
    """Authenticate the nullable replacement route, excluding invocation semantics."""
    entry=_branch_target(program['by'][branch],program['base'])
    _branch_at(program,branch,'0F85',entry,kind+'-replacement-selection')
    source='498B81' if kind in ('state','same') else '488B81'
    row=program['by'].get(entry);raw=bytes.fromhex(row['bytes']) if row else b''
    _require(len(raw)==7 and raw[:3]==bytes.fromhex(source),'replacement-function-load-'+kind,source,row)
    slot=struct.unpack_from('<I',raw,3)[0]
    _expect_at(program,entry+7,'4885C0',kind+'-replacement-null-test')
    _branch_at(program,entry+10,'0F84',resume,kind+'-replacement-null-resume')
    if kind in ('state','same'):
        _expect_at(program,entry+16,'4C8BC2488BD1',kind+'-replacement-arguments')
        load=program['by'][entry+22];raw=bytes.fromhex(load['bytes'])
        _require(raw[:3]==bytes.fromhex('498B89') and len(raw)==7 and struct.unpack_from('<I',raw,3)[0]==slot+8,
                 'replacement-context-'+kind,'same replacement slot plus8',load)
        call=entry+29
    else:
        load=program['by'][entry+16];raw=bytes.fromhex(load['bytes'])
        _require(raw[:3]==bytes.fromhex('488B89') and len(raw)==7 and struct.unpack_from('<I',raw,3)[0]==slot+8,
                 'replacement-context-'+kind,'same replacement slot plus8',load)
        args='4D8BC84C8BC2498BD6' if kind=='update' else '448BCF440FB7C648896C2420488BD3'
        _expect_at(program,entry+23,args,kind+'-replacement-arguments');call=entry+23+len(bytes.fromhex(args))
    _expect_at(program,call,'FFD090',kind+'-replacement-call')
    _branch_at(program,call+3,'E9',epilogue,kind+'-replacement-return')
    return entry


def _check_current_getter(program,field,kind):
    _expect_at(program,0,'4883EC48',kind+'-frame')
    root=_rip_load_cell(program,4,'488B05',kind+'-replacement-root')
    _expect_at(program,11,'4C8B48704D85C9',kind+'-replacement-receiver')
    _replacement(program,18,24,85,kind)
    _expect_at(program,24,'0F10410848895C2440F20F1049188B19',kind+'-source-carrier')
    _rip_load_cell(program,40,'488B0D',kind+'-reader-class')
    _expect_at(program,47,'0F11442420F20F114C243083B9E000000000',kind+'-source-buffer')
    _branch_at(program,65,'74',90,kind+'-class-initialization')
    _expect_at(program,67,'8D53'+bytes([field['offset']]).hex()+'488D4C2420',kind+'-field-address')
    reader=_call_target(program,75,kind+'-stored-read')
    _expect_at(program,80,'488B5C24404883C448C3',kind+'-return')
    auxiliary=_call_target(program,90,kind+'-class-initializer')
    _branch_at(program,95,'EB',67,kind+'-initialized-reader')
    return root,reader,auxiliary


def _check_current_query(program,pins):
    _expect_at(program,0,'48895C240848896C24104889742418574883EC40', 'query-frame')
    _expect_at(program,27,'498BE9418BF80FB7F2488BD9','query-preserved-inputs')
    _branch_at(program,39,'74',160,'query-context-initialization')
    root=_rip_load_cell(program,41,'488B05','query-replacement-root')
    _expect_at(program,48,'488B48704885C9','query-replacement-receiver')
    _replacement(program,55,61,133,'query')
    _expect_at(program,61,'488B4B28C7442430000000004885C9','query-lookup-receiver')
    _branch_at(program,76,'74',154,'query-null-lookup')
    _rip_load_cell(program,78,'4C8B0D','query-lookup-context')
    _expect_at(program,85,'448BC70FB7D6','query-same-lookup-arguments')
    _call_target(program,91,'query-lookup')
    _expect_at(program,96,'488B4B384885C9','query-dictionary-receiver')
    _branch_at(program,103,'74',154,'query-null-dictionary')
    _require(pins['contextLoadOffset']==105 and pins['callOffset']==120,'current-query-context-slots',(105,120),pins)
    _expect_at(program,112,'4C8D4424308B5008','query-key-and-output')
    _expect_at(program,125,'84C0','query-success-test')
    _branch_at(program,127,'74',196,'query-miss')
    _expect_at(program,129,'8B442430','query-success-output')
    _expect_at(program,133,'488B5C2450488B6C2458488B7424604883C4405FC3','query-return-frame')
    _call_target(program,154,'query-null-exception')
    _expect_at(program,159,'CC','query-exception-terminal')
    for at in (160,172):
        _rip_load_cell(program,at,'488D0D','query-initialization-context')
    _require(_call_target(program,167,'query-init-dictionary')==_call_target(program,179,'query-init-lookup'),
             'query-shared-context-initializer','same initializer',pins)
    flag=bytes.fromhex(program['by'][20]['bytes']);written=bytes.fromhex(program['by'][184]['bytes'])
    _require(len(flag)==7 and flag[:2]==bytes.fromhex('803D') and flag[-1]==0 and
             len(written)==7 and written[:2]==bytes.fromhex('C605') and written[-1]==1 and
             20+7+struct.unpack_from('<i',flag,2)[0]==184+7+struct.unpack_from('<i',written,2)[0],
             'query-context-ready-flag','same RIP-relative byte tested zero and assigned one',(flag.hex(),written.hex()))
    _branch_at(program,191,'E9',41,'query-initialization-resume')
    _expect_at(program,196,'33C0','query-miss-zero')
    _branch_at(program,198,'EB',133,'query-miss-return')
    for register in ('rbx','rdi','rsi'):
        _cfg_preserved(program['rows'],program['base'],61,{129,196},register,{91,120},{76,103})
    for start,end,register,label in ((65,91,'rcx','lookup-receiver'),(100,120,'rcx','dictionary-receiver'),
        (117,120,'r8','dictionary-output-pointer')):
        _preserved_interval(program['rows'],start,end,register,set(),'current-query-'+label)
    _preserved_interval(program['rows'],133,154,'rax',set(),'query-output-return')
    _preserved_interval(program['rows'],96,117,'rax',set(),'query-key-carrier')
    return root,{'dictionary':'System.Collections.Generic.Dictionary<System.Int32,System.Int32>',
        'key':'opaque lookup object Int32 at offset8','successReturn':'Int32 output at RSP+48',
        'missReturn':0,'nullReceiver':'exception helper then int3','runtimeObserved':False,'keyOwnershipResolved':False}


def _check_current_comparison(programs,methods,vector,fields,carriers):
    p=programs['update'];rows=p['rows'];base=p['base'];raw=p['raw']
    _expect_at(p,0,'40554156488D6C24B14881ECC8000000','update-frame')
    root=_rip_load_cell(p,16,'488B05','update-replacement-root')
    _expect_at(p,23,'4C8BF1488B48704885C9','update-original-system')
    _replacement(p,33,39,444,'update')
    _expect_at(p,39,'498B4E200F57C00F57C948899C24E00000004889B424E8000000488BF248C1EE20',
               'update-hot-slot-and-lookup')
    _expect_at(p,72,'0F1145D70F1145E70F114D170F114D270F1145F70F1145074885C9','update-initial-carriers')
    _branch_at(p,99,'0F84',492,'update-null-cache-pool')
    _rip_load_cell(p,105,'4C8B05','update-cache-context')
    _call_target(p,112,'update-cache-lookup')
    _expect_at(p,117,'498B4E10488BD84885C9','update-cache-receiver')
    _branch_at(p,127,'0F84',492,'update-null-grid-pool')
    _expect_at(p,133,'4889BC24F00000004C8D4DD74C89A424C00000004C8D45170FB7D64C89AC24B8000000',
               'update-grid-lookup-arguments')
    _call_target(p,168,'update-grid-lookup')
    _expect_at(p,173,'448B6B0C4533E40FB67B044585ED','update-count-counter-and-aggregate')
    _branch_at(p,187,'0F8E',390,'update-empty-count')
    _expect_at(p,193,'4C89BC24B0000000448B7B084533C94503FC0FB7D6458BC7498BCE','update-record-index-and-query-arguments')
    _call_at(p,220,methods['query']['rva'],'update-selected-query')
    _expect_at(p,225,'BA'+struct.pack('<I',vector['vtableSlot']).hex()+'89457F488D4DD7','update-provider-local-and-table')
    source=programs['vector']
    _expect_at(source,24,'488BCFBA'+struct.pack('<I',vector['vtableSlot']).hex()+'418BF0',
               'source-owned-vector-slot-and-index')
    _call_at(p,237,_call_target(source,35,'owned-vector-table'),'update-source-owned-table')
    _expect_at(p,242,'85C0','update-vector-present')
    zero=_branch_target(p['by'][244],base);_branch_at(p,244,'0F84',zero,'update-null-vector')
    _expect_at(p,zero,'0F57DB0F57E4','update-null-vector-zero-carrier')
    _branch_at(p,zero+6,'E9',319,'update-null-vector-join')
    _expect_at(p,250,'0F57C0488D4DD70F1145178BD00F1145270F1045DF0F2945B7F20F1045EFF20F1145C7',
               'update-source-buffer-and-carrier')
    _call_at(p,285,_call_target(source,62,'owned-vector-offset'),'update-source-owned-vector')
    _require(vector['elementWidth']==16,'update-record-width',16,vector['elementWidth'])
    _expect_at(p,290,'41C1E7044C8D45B7488D4D17418D1407','update-record-stride-and-position')
    _call_at(p,306,carriers['initialize']['rva'],'update-record-carrier-initializer')
    _call_at(source,109,carriers['forward']['rva'],'source-owned-vector-forwarder')
    _expect_at(p,311,'0F105D270F10651733D2488D4DF70F1165F70F115D07','update-shared-record-carriers')
    _call_at(p,333,methods['state']['rva'],'update-source-owned-state')
    _expect_at(p,338,'33D2488D4DF7448BF8','update-shared-record-same-and-saved-state')
    _call_at(p,347,methods['same']['rva'],'update-source-owned-is-same')
    getters=[_check_current_getter(programs[role],fields[role],role) for role in ('state','same')]
    _require(all(row[0]==root for row in getters) and getters[0][1:]==getters[1][1:],
             'shared-getter-replacement-root-and-stored-read','same root and source-owned reader/initializer',getters)
    _expect_at(p,352,'83F801','update-only-literal-one')
    _branch_at(p,355,'75',468,'update-inequality-selector')
    _expect_at(p,357,'443B7D7F0F94C1','update-equality-predicate')
    _expect_at(p,468,'443B7D7F0F95C1','update-inequality-predicate')
    _branch_at(p,475,'EB',364,'update-predicate-join')
    _expect_at(p,364,'807B04000FB6C1','update-aggregation-selector')
    _branch_at(p,371,'74',477,'update-or-aggregation')
    _expect_at(p,373,'34014022F984C0','update-and-aggregation')
    _branch_at(p,380,'74',455,'update-and-loop')
    _expect_at(p,382,'4C8BBC24B00000000FB643064C8BAC24B8000000403AC74C8BA424C0000000488BB424E80000000F95C040887B06488BBC24F0000000488B9C24E0000000',
               'update-cache-changed-flag')
    _expect_at(p,444,'4881C4C8000000415E5DC3','update-return-frame')
    _expect_at(p,455,'41FFC4453BE5','update-loop-counter')
    _branch_at(p,461,'7D',382,'update-loop-done')
    _branch_at(p,463,'E9',201,'update-loop-next')
    _expect_at(p,477,'400ACF','update-or-predicate')
    _branch_at(p,480,'75',487,'update-or-one')
    _expect_at(p,482,'4032FF','update-or-zero')
    _branch_at(p,485,'EB',378,'update-or-zero-join')
    _expect_at(p,487,'40B701','update-or-true')
    _branch_at(p,490,'EB',378,'update-or-true-join')
    _call_target(p,492,'update-null-exception');_expect_at(p,497,'CC','update-exception-terminal')
    # Both vector routes reach both predicates without overwriting the provider
    # local. R15 is nonvolatile across the selected typed getter calls.
    _cfg_preserved(rows,base,233,{357,468},'rbp',{237,285,306,333,347},set(),_provider_local_store_check)
    _cfg_preserved(rows,base,347,{357,468},'r15d',{347},set())
    _preserved_interval(rows,352,357,'rax',set(),'current-IsSame-to-selector')
    _preserved_interval(rows,424,455,'rax',set(),'current-changed-flag-return')
    return root,{'record':'MissionCondition','storedStateField':'State','selectorField':'IsSame','selectorLiteral':1,
        'selectedRelation':'equal','fallbackRelation':'not_equal','provider':methods['query']['type']+'.'+methods['query']['method'],
        'providerParameterNames':methods['query']['parameterNames'],'updateReturnsChangedFlag':True,
        'completeUnwindFamiliesAuthenticated':True,'zeroVectorCarrierPathAuthenticated':True,
        'runtimeObserved':False,'authoredGroupToLiveCacheResolved':False,'providerValueOriginResolved':False}


def validate(gameassembly,metadata):
    contract,_=read_reviewed_contract(CONTRACT,schema=SCHEMA,status='validated',label='mission_condition_consumers')
    inputs=contract['nativeInputs']
    gate=check_installed_native_inputs(inputs['gameAssemblySha256'],inputs['metadataSha256'],gameassembly=gameassembly,metadata=metadata)
    _require(gate.status==NATIVE_EVIDENCE_VALIDATED,'native-inputs','validated',f'{gate.status}:{gate.detail}')
    unity=_fingerprint(Path(gameassembly).parent/'UnityPlayer.dll')
    _require(unity['sha256'].upper()==inputs['unityPlayerSha256'].upper(),'unity-input',inputs['unityPlayerSha256'],unity['sha256'])
    image=open_native_image(gameassembly,metadata);methods=dict(contract['methods']);catalogs={}
    for dependency in contract['dependencies']:
        filename=dependency['path']
        catalog,_=read_reviewed_contract(CONTRACTS_DIR/filename,schema=dependency['schema'],status='validated',label='mission_condition_dependency')
        _require(catalog['nativeInputs']==inputs,'dependency-build-'+filename,inputs,catalog['nativeInputs'])
        catalogs[filename]=catalog
        rows=catalog['methods'].values() if isinstance(catalog['methods'],dict) else catalog['methods']
        rows=list(rows)
        for role,selector in dependency['methodRoles'].items():
            selected=[row for row in rows if (row['type'],row['method'])==(selector['type'],selector['method'])]
            _require(len(selected)==1,'selected-method-'+role,'exactly one source-owned method',len(selected))
            methods[role]=selected[0]
    bodies={role:_check_method(image,row) for role,row in methods.items()}
    _method_call_abi(image,methods,contract['methodCallAbi'])
    _vector_return_abi(image,image.metadata.methods[methods['vector']['index']])
    extents=image.mapper.pdata_function_extents(image.pe)
    for role in ('update','query'):
        row=methods[role]
        _require(extents.get(image.pe.image_base+row['rva'])==image.pe.image_base+row['rva']+row['bodyExtent'],
            'primary-body-'+role,row['bodyExtent'],extents.get(image.pe.image_base+row['rva']))
    for role in ('vector',):
        row=methods[role];end=extents.get(image.pe.image_base+row['rva'])
        _require(end is not None and 0<end-(image.pe.image_base+row['rva'])<=len(bodies[role]),
            'owned-primary-body-'+role,'primary body inside source-owned pinned window',end)
        bodies[role]=bodies[role][:end-(image.pe.image_base+row['rva'])]
    query=image.metadata.methods[methods['query']['index']];params=image.metadata.parameters_for(query)
    _require(methods['query']['parameters']==['System.UInt16','System.Int32'] and methods['query']['parameterNames']==['hotSlot','conditionIndex'],
        'query-signature','named UInt16 hotSlot and Int32 conditionIndex',methods['query']['parameters'])
    _ordinary_primitive_abi(image,params[0].type_index,0x07,'condition-query-hotSlot')
    scalar=catalogs['dynamic_scalar_components_native.json'];main=catalogs['dynamic_main_vector_native.json']
    decode=_composed_decoder(image.mapper)
    _require(set(contract['families'])=={'update','query','state','same','vector'},
             'complete-family-role-roster',['update','query','state','same','vector'],sorted(contract['families']))
    programs={role:_family_program(image,methods[role],pins,decode) for role,pins in contract['families'].items()}
    record=next(row for row in scalar['layout']['records'] if row['name']=='MissionCondition')
    fields={role:next(field for field in record['fields'] if field['getterMethodIndex']==methods[role]['index']) for role in ('state','same')}
    for role,field in fields.items():
        starts=frozenset(row['offset'] for row in programs[role]['rows'])
        offset=_getter_offset(programs[role]['raw'],role,starts)
        _require(field['type']=='System.Int32' and offset==field['offset'],
            'source-owned-field-'+role,field['offset'],offset)
    vector=next(row for row in main['layout']['vectors'] if row['name']=='MissionCondition')
    _require(vector['elementWidth']==record['width'],'owned-record-width',record['width'],vector['elementWidth'])
    carriers=_validate_carriers(scalar['layout'],image)
    root,flow=_check_current_comparison(programs,methods,vector,fields,carriers)
    query_root,query_flow=_check_current_query(programs['query'],contract['queryContext'])
    _require(query_root==root,'query-same-replacement-root',root,query_root)
    query_context=_query_context(image,bodies['query'],methods['query'],contract['queryContext'])
    return {'format':'endfield.dynamic-mission-condition-consumers-native-audit.v3','status':'validated',
        'nativeInputs':inputs,'flow':flow,'providerQuery':query_flow,'queryContext':query_context,
        'evidenceBoundary':contract['evidenceBoundary']}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gameassembly',type=Path,required=True);parser.add_argument('--metadata',type=Path,required=True)
    parser.add_argument('--output-json',type=Path,default=REPO_ROOT/'reports/animestudio/dynamic_mission_condition_consumers_native_latest.json')
    args=parser.parse_args(argv)
    try:
        sources=_parser_source_snapshots(Path(__file__))
        contract=json.loads(CONTRACT.read_text())
        sources.extend(_fingerprint(path) for path in [CONTRACT,NATIVE_MAPPER_PATH,METADATA_HELPER_PATH,
            *(CONTRACTS_DIR/dependency['path'] for dependency in contract['dependencies'])])
        inputs=[_fingerprint(path) for path in (args.gameassembly,args.metadata,args.gameassembly.parent/'UnityPlayer.dll')]
        protected=[Path(row['path']) for row in sources+inputs]
        groups._guard_publication(args.output_json,protected)
        result=validate(args.gameassembly,args.metadata);result['proofSources']=sources;result['proofInputs']=inputs
        encoded=json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
        groups._require_unchanged(sources+inputs);groups._guard_publication(args.output_json,protected)
        atomic_write_text(args.output_json,encoded)
    except (OSError,ValueError,KeyError,IndexError,RuntimeError,struct.error) as exc:
        print(f'dynamic-mission-condition-consumers-native:{str(exc)[:1400]}',file=sys.stderr);return 1
    print('MissionCondition native comparison passed: IsSame==1 selects State equality; update returns change flag; runtime unresolved')
    return 0


if __name__=='__main__':raise SystemExit(main())
