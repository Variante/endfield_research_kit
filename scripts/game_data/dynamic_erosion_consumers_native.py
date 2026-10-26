"""Authenticate selected non-render Erosion stored-value consumers offline.

The selected non-replacement path proves the supplied grid, group count/index,
axis getters and twelve-byte value argument, plus the unchanged UInt64 return.
Separate complete shapes cover named patch-check calls and inline nullable
replacement dispatch. Neither shape proves live grid selection or insertion.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
import re
import sys
from pathlib import Path

if __name__ == '__main__' and not __package__:
    raise SystemExit('Run with python -m scripts.game_data.dynamic_erosion_consumers_native')

from scripts.common import check_installed_native_inputs, NATIVE_EVIDENCE_VALIDATED
from scripts.game_data import dynamic_group_components_native as groups
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract, NATIVE_MAPPER_PATH, METADATA_HELPER_PATH
from scripts.game_data.il2cpp.protocol import runtime_type_name, runtime_generic_inst_type_pointers
from scripts.game_data.dynamic_scalar_components_native import _relative_call_target, _float32_getter_offset, _validate_carriers
from scripts.game_data.memorypack.corpus_gate import _fingerprint, _parser_source_snapshots
from scripts.game_data.corpus_common import atomic_write_text
from scripts.repo_paths import REPO_ROOT

CONTRACT = CONTRACTS_DIR / 'dynamic_erosion_consumers_native.json'
SCHEMA = 'endfield.dynamic-erosion-consumers-native-contract.v3'
PRIMITIVE_TYPE_CODES = {'System.Void':0x01,'System.Boolean':0x02,'System.Int32':0x08,
                        'System.UInt64':0x0b,'System.Single':0x0c}


def _require(condition, check, expected, actual):
    if not condition:
        raise ValueError(f'erosion_consumers:{check}:expected={str(expected)[:320]} actual={str(actual)[:320]}')


def _type_pointer(image,type_index,label):
    _require(isinstance(type_index,int) and 0<=type_index<image.registration['typesCount'],
        'signature-type-index-'+label,'selected registration type range',type_index)
    table=int(image.registration['types'],16)
    return image.pe.u64_at_va(table+type_index*8)


def _raw_type_abi(image,type_index,label):
    pointer=_type_pointer(image,type_index,label)
    offset,_section,_rva=image.pe.file_offset_for_va(pointer)
    _require(offset is not None and 0<=offset and offset+12<=len(image.pe.buf),
        'primitive-type-bounds-'+label,'complete Il2CppType prefix',offset)
    bits=struct.unpack_from('<I',image.pe.buf,offset+8)[0]
    return bits


def _ordinary_primitive_abi(image,type_index,type_code,label):
    bits=_raw_type_abi(image,type_index,label)
    _require((bits>>16)&0xff==type_code and (bits>>24)&0x7f==0,
        'ordinary-primitive-abi-'+label,f'typeCode={type_code:02X}; flags low seven bits zero',f'rawBits={bits:08X}')
    return bits


def _require_type_shape(image,type_index,type_code,flags,label):
    bits=_raw_type_abi(image,type_index,label)
    _require(bits>>16==(flags<<8)|type_code,'explicit-type-abi-'+label,
        f'typeCode={type_code:02X}; flags={flags:02X}',f'rawBits={bits:08X}')
    return bits


def _list_vector_abi(image,type_index):
    _require_type_shape(image,type_index,0x15,0,'typed-list')
    pointer=_type_pointer(image,type_index,'typed-list')
    data=image.pe.u64_at_va(pointer)
    offset,_section,_rva=image.pe.file_offset_for_va(data)
    _require(offset is not None and 0<=offset and offset+16<=len(image.pe.buf),'generic-list-bounds','complete generic class prefix',offset)
    definition,inst=struct.unpack_from('<QQ',image.pe.buf,offset)
    def raw_pointer_bits(pointer,label):
        at,_section,_rva=image.pe.file_offset_for_va(pointer)
        _require(at is not None and 0<=at and at+12<=len(image.pe.buf),'generic-type-bounds-'+label,'complete type prefix',at)
        return struct.unpack_from('<I',image.pe.buf,at+8)[0]
    _require(raw_pointer_bits(definition,'list-definition')>>16==0x0012,
        'ordinary-list-definition','class kind12, flags00',f'{raw_pointer_bits(definition,"list-definition"):08X}')
    arguments=runtime_generic_inst_type_pointers(image.pe,inst)
    _require(len(arguments)==1,'list-generic-arity',1,len(arguments))
    _require(raw_pointer_bits(arguments[0],'vector-argument')>>16==0x8011,
        'list-vector-value-abi','value kind11, flags80',f'{raw_pointer_bits(arguments[0],"vector-argument"):08X}')
    _require(runtime_type_name(image.pe,image.metadata,arguments[0])=='UnityEngine.Vector3',
        'list-vector-type','UnityEngine.Vector3',runtime_type_name(image.pe,image.metadata,arguments[0]))


def _method_call_abi(image,methods,expected):
    _require(set(methods)==set(expected),'call-abi-role-roster',sorted(methods),sorted(expected))
    for role,kind in expected.items():
        _require(kind in ('static','instance'),'call-abi-declaration-'+role,'static or instance',kind)
        row=methods[role];method=image.metadata.methods[row['index']]
        owner=image.metadata.type_full_name(image.metadata.types[method.declaring_type])
        _require(owner==row['type'],'concrete-owner-'+role,row['type'],owner)
        actual='static' if method.flags&0x10 else 'instance'
        _require(actual==kind,'method-call-abi-'+role,kind,actual)


def _mov_register(raw):
    prefix=raw[0] if raw and 0x40<=raw[0]<=0x4f else 0
    at=1 if prefix else 0
    _require(len(raw)==at+2 and raw[at] in (0x8b,0x89) and raw[at+1]>>6==3,'register-move','MOV register,register',raw.hex())
    mod=raw[at+1];reg=((mod>>3)&7)+(8 if prefix&4 else 0);rm=(mod&7)+(8 if prefix&1 else 0)
    return (64 if prefix&8 else 32,reg,rm) if raw[at]==0x8b else (64 if prefix&8 else 32,rm,reg)


def _float_move(raw):
    _require(len(raw)==3 and raw[:2]==b'\x0f\x28' and raw[2]>>6==3,'float-move','MOVAPS register,register',raw.hex())
    return (raw[2]>>3)&7,raw[2]&7


def _float_store(raw):
    _require(len(raw)>=4 and raw[:3]==b'\xf3\x0f\x11','float-store','MOVSS memory,xmm',raw.hex())
    mod=raw[3];mode=mod>>6;base=mod&7;reg=(mod>>3)&7
    _require(base!=4 and mode in (0,1) and not (mode==0 and base==5),'float-address','simple base/disp8 address',raw.hex())
    length=4 if mode==0 else 5
    _require(len(raw)==length,'float-instruction-length',length,len(raw))
    return base,0 if mode==0 else struct.unpack_from('<b',raw,4)[0],reg


def _lea_stack(raw):
    _require(len(raw)==4 and raw[0]&0xf8==0x48 and raw[1]==0x8d and raw[2]>>6==1 and raw[2]&7==5,
        'stack-address','LEA reg,[RBP+disp8]',raw.hex())
    return ((raw[2]>>3)&7)+(8 if raw[0]&4 else 0),struct.unpack_from('<b',raw,3)[0]


def _instruction_partition(raw,rva,decode):
    """Reject unknown/truncated bytes; every accepted byte owns one instruction."""
    rows=decode(raw,rva,stop_offset=len(raw));cursor=0
    for row in rows:
        encoded=bytes.fromhex(row.get('bytes',''))
        text=str(row.get('text',''))
        _require(row.get('offset')==cursor and encoded and cursor+len(encoded)<=len(raw) and
                 raw[cursor:cursor+len(encoded)]==encoded and text and not text.startswith(('db','ff/','unknown')) and
                 not row.get('truncatedTerminal'),'instruction-partition',f'complete instruction at {cursor}',row)
        cursor+=len(encoded)
    _require(cursor==len(raw),'instruction-partition-end',len(raw),cursor)
    return rows


def _direct_call_targets(raw,rva,decode):
    rows=_instruction_partition(raw,rva,decode)
    return [_relative_call_target(raw,rva,row['offset'],'decoded-direct-call') for row in rows
            if row['text'].startswith('call ') and bytes.fromhex(row['bytes'])[:1]==b'\xe8'
            and len(bytes.fromhex(row['bytes']))==5]


def _direct_call_boundary(rows,at,label):
    instruction=next((row for row in rows if row['offset']==at),None)
    _require(instruction is not None and instruction['text'].startswith('call ') and
             bytes.fromhex(instruction['bytes'])[:1]==b'\xe8' and len(bytes.fromhex(instruction['bytes']))==5,
             'named-call-boundary-'+label,'decoded direct CALL instruction',instruction)
    return instruction


def _disjoint_slots(slots):
    for index,(name,start,width) in enumerate(slots):
        _require(width>0,'frame-slot-width-'+name,'positive byte width',width)
        for other,other_start,other_width in slots[index+1:]:
            _require(start+width<=other_start or other_start+other_width<=start,'frame-slot-alias',
                'disjoint FB carrier, Unity return and list value buffers',(name,start,width,other,other_start,other_width))


def _preserved_interval(rows,start,end,register,allowed_calls,label):
    aliases={'rax':{'rax','eax','ax','al','ah'},'rcx':{'rcx','ecx','cx','cl','ch'},
             'rdx':{'rdx','edx','dx','dl','dh'},'rdi':{'rdi','edi','di','dil'},
             'rbx':{'rbx','ebx','bx','bl','bh'},'rsi':{'rsi','esi','si','sil'}}
    watched=aliases.get(register,{register})
    extended=re.fullmatch(r'r(8|9|1[0-5])(?:d|w|b)?',register)
    if extended:
        base='r'+extended.group(1);watched={base,base+'d',base+'w',base+'b'}
    for row in rows:
        if not start<=row['offset']<end:continue
        write=row.get('write') or {}
        _require(write.get('register') not in watched,'interval-clobber-'+label,register,row)
        if row['text'].startswith('call '):
            _require(row['offset'] in allowed_calls and bytes.fromhex(row['bytes'])[:1]==b'\xe8',
                'interval-call-'+label,'explicit allowed direct call under Win64 nonvolatile ABI',row)


def _check_decoder_and_helpers(contract,bodies,probes,partitions,methods,dependency_bodies,carriers,vector_layout,decode):
    """Shape-independent decoder, Unity constructor, list forwarder and vector-clone checks."""
    decoder=bodies['decoder']
    axis_calls=sorted((row['offset'],row['target']) for row in contract['calls'] if row['window']=='decoder')
    _require([role for _,role in axis_calls]==['x','y','z'],'decoder-getter-order',['x','y','z'],axis_calls)
    for at,role in axis_calls:
        _require(decoder[at-5:at]==bytes.fromhex('488BCB33D2') or decoder[at-8:at-3]==bytes.fromhex('33D2488BCB'),
            'decoder-getter-source-'+role,'saved FB source RBX; zero generated accessor context',decoder[max(0,at-8):at].hex())
    _require(_mov_register(probes['decoderSaveSource'])==(64,3,2),'decoder-source',(64,3,2),_mov_register(probes['decoderSaveSource']))
    _require(_mov_register(probes['decoderSaveOutput'])==(64,7,1),'decoder-output',(64,7,1),_mov_register(probes['decoderSaveOutput']))
    _require(_mov_register(probes['decoderReturn'])==(64,0,7),'decoder-return-pointer',(64,0,7),_mov_register(probes['decoderReturn']))
    values=[]
    for axis,constructor_reg in (('X',1),('Y',2),('Z',3)):
        base,offset,reg=_float_store(probes['decoder'+axis+'Store'])
        ctor_base,ctor_offset,ctor_value=_float_store(probes['constructor'+axis+'Store'])
        if axis!='Z':
            saved,source=_float_move(probes['decoder'+axis+'Save'])
            _require(source==0 and reg==saved,'axis-return-'+axis,'getter XMM0 retained to same store register',(source,reg,saved))
        else:_require(reg==0,'axis-return-Z','getter XMM0',reg)
        _require(base==7 and ctor_base==1 and offset==ctor_offset and ctor_value==constructor_reg,
            'unity-constructor-axis-'+axis,(7,1,offset,constructor_reg),(base,ctor_base,ctor_offset,ctor_value))
        values.append({'getter':'get_'+axis,'constructorParameter':axis.lower(),'returnByteOffset':offset})
    _require(bodies['constructor']==b''.join(probes['constructor'+axis+'Store'] for axis in ('X','Y','Z'))+b'\xc3',
        'constructor-leaf','three exact float stores; RET',bodies['constructor'].hex())
    forward=bodies['valueForwarder']
    _require(forward[:26]==bytes.fromhex('4883EC38F20F10028B4208488D542420F20F1144242089442428') and forward[26]==0xe8
             and forward[31:]==bytes.fromhex('4883C438C3'),'opaque-forwarding','twelve-byte copy with RCX/R8 unchanged; one call; RET',forward.hex())
    _require(probes['cloneSlot'][:1]==b'\xba' and struct.unpack_from('<I',probes['cloneSlot'],1)[0]==vector_layout['vtableSlot'],
        'clone-vector-slot',vector_layout['vtableSlot'],probes['cloneSlot'].hex())
    _require(probes['cloneIndex']==bytes.fromhex('418BF0') and probes['cloneStride']==bytes.fromhex('8D0C76')
             and probes['clonePosition']==bytes.fromhex('8D1488') and vector_layout['elementWidth']==3*4,
        'clone-index-stride','supplied R8D index retained in ESI; index*3*4',probes['cloneStride'].hex())
    clone_calls=_direct_call_targets(bodies['vectorClone'],contract['windows']['vectorClone']['rva'],decode)
    original_calls=_direct_call_targets(dependency_bodies['vectorOriginal'],methods['vectorOriginal']['rva'],decode)
    _require(len(clone_calls)==len(original_calls)==3 and clone_calls[:2]==original_calls[:2],
        'clone-generated-shared-helpers',original_calls,clone_calls)
    _require(clone_calls[2]==carriers['initialize']['rva'] and original_calls[2]==carriers['forward']['rva'],
        'clone-generated-carriers',(carriers['initialize']['rva'],carriers['forward']['rva']),
        (clone_calls[2],original_calls[2]))
    decoder_rows=partitions['decoder']
    def at(name):return contract['probes'][name]['offset']
    def after(name):return at(name)+len(probes[name])
    axis_calls={row['target']:row['offset'] for row in contract['calls'] if row['window']=='decoder'}
    for axis in ('X','Y'):
        _preserved_interval(decoder_rows,axis_calls[axis.lower()]+5,at('decoder'+axis+'Save'),'xmm0',set(),'getter-'+axis+'-to-save')
    _preserved_interval(decoder_rows,after('decoderXSave'),at('decoderXStore'),'xmm7',
        {axis_calls['y'],axis_calls['z']},'saved-X')
    _preserved_interval(decoder_rows,after('decoderYSave'),at('decoderYStore'),'xmm6',
        {axis_calls['z']},'saved-Y')
    _preserved_interval(decoder_rows,axis_calls['z']+5,at('decoderZStore'),'xmm0',set(),'getter-Z-to-store')
    _preserved_interval(decoder_rows,after('decoderSaveOutput'),after('decoderZStore'),'rdi',set(axis_calls.values()),'unity-output-pointer')
    _preserved_interval(decoder_rows,after('decoderReturn'),len(bodies['decoder']),'rax',set(),'unity-return-pointer')
    return values


def _check_flow(contract,bodies,methods,dependency_bodies,carriers,vector_layout,decode):
    partitions={role:_instruction_partition(raw,contract['windows'][role]['rva'],decode) for role,raw in bodies.items()}
    probes={}
    for name,probe in contract['probes'].items():
        raw=bodies[probe['window']];at=probe['offset'];expected=bytes.fromhex(probe['bytes'])
        _require(0<=at and expected and at+len(expected)<=len(raw) and raw[at:at+len(expected)]==expected,
            'witness-'+name,expected.hex(),raw[at:at+len(expected)].hex())
        probes[name]=expected
    targets={name:row['rva'] for name,row in methods.items()}
    targets.update({name:row['rva'] for name,row in contract['windows'].items()})
    for call in contract['calls']:
        window=call['window'];at=call['offset'];rva=contract['windows'][window]['rva']
        _direct_call_boundary(partitions[window],at,call['target'])
        actual=_relative_call_target(bodies[window],rva,at,call['target'])
        _require(actual==targets[call['target']],'call-'+call['target'],targets[call['target']],actual)
    if probes['patchBranch'][:3]==bytes.fromhex('488B05'):
        return _check_inline_flow(contract,bodies,probes,partitions,methods,dependency_bodies,
                                  carriers,vector_layout,decode)
    patch=probes['patchBranch'];at=contract['probes']['patchBranch']['offset']
    _require(patch[:4]==bytes.fromhex('84C00F85'),'patch-result-test','TEST AL,AL; JNE alternate route',patch.hex())
    alternate=at+8+struct.unpack_from('<i',patch,4)[0]
    loop_end=contract['probes']['loopControl']['offset']+len(probes['loopControl'])
    _require(loop_end<=alternate<contract['probes']['returnFrame']['offset'] and at+8<contract['probes']['rootGetterArgs']['offset'],
        'patch-route-separation','nonzero result skips selected source/getter loop',(alternate,loop_end))
    check_call=next(row for row in contract['calls'] if row['target']=='patchCheck')
    _require(check_call['window']=='collector' and check_call['offset']+5==at,
        'patch-check-result','named check return AL immediately tested',check_call)
    _require(_mov_register(probes['saveList'])==(64,7,8),'original-list-receiver',(64,7,8),_mov_register(probes['saveList']))
    _require(_mov_register(probes['saveComp'])==(64,6,2),'original-comp-id',(64,6,2),_mov_register(probes['saveComp']))
    _require(_mov_register(probes['saveThis'])==(64,14,1),'original-system',(64,14,1),_mov_register(probes['saveThis']))
    _require(_mov_register(probes['numCapture'])==(32,6,0),'num-return-capture',(32,6,0),_mov_register(probes['numCapture']))
    _require(_mov_register(probes['indexCapture'])==(32,14,0),'index-return-capture',(32,14,0),_mov_register(probes['indexCapture']))
    _require(probes['initialCounter']==bytes.fromhex('33DB'),'counter-initialization','XOR EBX,EBX',probes['initialCounter'].hex())
    guard=probes['numGuard'];at=contract['probes']['numGuard']['offset']
    _require(guard[:4]==bytes.fromhex('85F60F8E'),'nonpositive-num-branch','TEST ESI,ESI; JLE',guard.hex())
    target=at+8+struct.unpack_from('<i',guard,4)[0]
    _require(target==contract['probes']['returnFrame']['offset'],'nonpositive-num-exit',contract['probes']['returnFrame']['offset'],target)
    loop=probes['loopControl'];at=contract['probes']['loopControl']['offset']
    _require(loop[:5]==bytes.fromhex('FFC33BDE7C'),'loop-counter','INC EBX; CMP EBX,ESI; JL',loop.hex())
    _require(at+6+struct.unpack_from('<b',loop,5)[0]==contract['probes']['loopIndex']['offset'],'loop-target',contract['probes']['loopIndex']['offset'],at+6+struct.unpack_from('<b',loop,5)[0])
    _require(probes['loopIndex'][:4]==bytes.fromhex('468D0433'),'index-plus-counter','LEA R8D,[RBX+R14]',probes['loopIndex'].hex())
    _require(_lea_stack(probes['rootGetterArgs'][4:8])==_lea_stack(probes['loopIndex'][4:8]),'same-grid-carrier',probes['rootGetterArgs'][4:8].hex(),probes['loopIndex'][4:8].hex())
    root_args=probes['rootGetterArgs'];group_args=probes['groupGetterArgs']
    num_args=probes['groupNumArgs'];index_args=probes['indexArgs']
    group_index=probes['groupIndexArgs'];decode_args=probes['decodeArgs']
    lookup=probes['selectGridAndRoot'];grid_out=_lea_stack(lookup[7:11]);index_out=_lea_stack(lookup[:4])
    _require(_mov_register(lookup[4:7])==(64,2,6) and _mov_register(lookup[11:])==(64,1,14),
        'lookup-original-inputs','saved original component ID and system receiver',lookup.hex())
    _require(grid_out[0]==8 and _lea_stack(root_args[4:8])==(2,grid_out[1]) and index_out==(9,-57),
        'lookup-grid-and-root-index','lookup output grid and explicit root index feed root getter',(grid_out,index_out))
    _require(root_args[:4]==bytes.fromhex('448B45C7'),'root-index-input','R8D from authored root lookup stack output',root_args.hex())
    parent_out=_lea_stack(root_args[8:12])
    child_out=_lea_stack(probes['loopIndex'][8:12])
    _require(parent_out==child_out==_lea_stack(group_args[7:11])==_lea_stack(group_index[7:11]),
        'proxy-output-slots','same explicit RBP temporary slot',(parent_out,child_out))
    proxy_input=_lea_stack(group_args[3:7])
    _require(proxy_input==_lea_stack(group_index[3:7])==_lea_stack(decode_args[:4]),
        'proxy-input-slots','same RDX carrier slot',proxy_input)
    _require(_lea_stack(num_args[2:6])==_lea_stack(index_args[2:6])==(1,proxy_input[1]),
        'scalar-proxy-input','RCX points to returned carrier temporary',num_args.hex())
    carrier_copy=bytes.fromhex('0F10000F1048100F1145CF0F114DDF')
    _require(group_args[11:]==num_args[6:]==index_args[6:]==carrier_copy,
        'returned-carrier-copy','returned RAX carrier copied to same 32-byte temporary',group_args.hex())
    clone_call=next(row for row in contract['calls'] if row['target']=='vectorClone')
    decoder_call=next(row for row in contract['calls'] if row['target']=='decoder' and row['window']=='collector')
    between=bodies['collector'][clone_call['offset']+5:contract['probes']['decodeArgs']['offset']]
    _require(len(between)==27 and between[:3]==bytes.fromhex('488B0D') and between[7:22]==carrier_copy and between[22]==0xe8,
        'cloned-source-carrier','returned vector proxy copied to decoder source slot; intervening call receives static RIP-relative RCX',between.hex())
    _require(decoder_call['offset']==contract['probes']['decodeArgs']['offset']+len(decode_args),
        'decoder-argument-adjacency','explicit source/output arguments immediately precede decoder',decoder_call)
    _require(group_args[:3]==group_index[:3]==bytes.fromhex('4533C0') and num_args[:2]==index_args[:2]==bytes.fromhex('33D2'),
        'generated-scalar-zero-index','zero offset arguments for group and index accessors',group_index.hex())
    _require(_lea_stack(decode_args[4:])==(1,71),'decoder-output-slot','RCX points to independent Unity result slot',decode_args.hex())
    _disjoint_slots([('fb-carrier',proxy_input[1],32),('unity-return',_lea_stack(decode_args[4:])[1],12),
                     ('list-value',_lea_stack(probes['listArgs'][:4])[1],12)])
    _require(probes['listArgs']==bytes.fromhex('488D55F7488BCFF20F10008B4008F20F1145F78945FF'),
        'vector-call-arguments','same list receiver plus returned first eight and next four bytes',probes['listArgs'].hex())
    values=_check_decoder_and_helpers(contract,bodies,probes,partitions,methods,dependency_bodies,carriers,vector_layout,decode)
    collector_rows=partitions['collector']
    def at(name):return contract['probes'][name]['offset']
    def after(name):return at(name)+len(probes[name])
    argument_start=at('listArgs');argument_end=argument_start+len(probes['listArgs'])
    collector_calls={row['offset'] for row in collector_rows if row['text'].startswith('call ') and
                     bytes.fromhex(row['bytes'])[:1]==b'\xe8' and row['offset']<argument_start}
    _preserved_interval(collector_rows,after('saveList'),argument_start+4,'rdi',collector_calls,'saved-list-receiver')
    _preserved_interval(collector_rows,decoder_call['offset']+5,argument_start+11,'rax',set(),'vector-pointer-to-loads')
    _preserved_interval(collector_rows,argument_start+11,argument_start+14,'xmm0',set(),'copied-XY')
    _preserved_interval(collector_rows,argument_start+14,argument_start+19,'rax',set(),'copied-Z')
    _preserved_interval(collector_rows,argument_start+4,argument_end,'rdx',set(),'vector-argument-address')
    _preserved_interval(collector_rows,argument_start+7,argument_end,'rcx',set(),'restored-list-receiver')
    return values


def _inline_guard(raw,at,source_at,return_at,*,collector):
    """Both null branches enter the source path; a replacement skips it entirely."""
    guard=raw[at:source_at]
    # The leading RIP displacement and two wrapper slots are build declarations;
    # their widths, receiver chain and relation are instruction-level facts.
    prefix=bytes.fromhex('488B48704885C974') if collector else bytes.fromhex('4C8BD1488B48704885C974')
    start=7+len(prefix)
    _require(guard[:3]==bytes.fromhex('488B05') and guard[7:7+len(prefix)]==prefix,
        'inline-guard-owner','RIP owner; nullable dispatch table; source on null',guard.hex())
    first=start
    _require(at+first+1+struct.unpack_from('<b',guard,first)[0]==source_at,
        'inline-guard-null-table',source_at,guard[first])
    load=first+1
    _require(guard[load:load+3]==bytes.fromhex('488B81') and
             guard[load+7:load+11]==bytes.fromhex('4885C074'),
        'inline-guard-entry','nullable function pointer read',guard[load:].hex())
    slot=struct.unpack_from('<i',guard,load+3)[0]
    second=load+11
    _require(at+second+1+struct.unpack_from('<b',guard,second)[0]==source_at,
        'inline-guard-null-entry',source_at,guard[second])
    context=second+1
    _require(guard[context:context+3]==bytes.fromhex('488B89') and
             struct.unpack_from('<i',guard,context+3)[0]==slot+8,
        'inline-guard-context','adjacent wrapper context',guard[context:].hex())
    args=bytes.fromhex('4C8BCF4C8BC64C897C2420498BD6FFD0') if collector else bytes.fromhex('4D8BC84C8BC2498BD2FFD0')
    tail=context+7
    _require(guard[tail:tail+len(args)]==args,'inline-guard-arguments','original inputs forwarded to replacement',guard[tail:].hex())
    jump=tail+len(args)
    if collector:
        _require(guard[jump:jump+1]==b'\xe9' and jump+5==len(guard),
            'inline-guard-jump','closed near jump to return frame',guard[jump:].hex())
        target=at+jump+5+struct.unpack_from('<i',guard,jump+1)[0]
    else:
        _require(guard[jump:jump+1]==b'\xeb' and jump+2==len(guard),
            'inline-guard-jump','closed short jump to return frame',guard[jump:].hex())
        target=at+jump+2+struct.unpack_from('<b',guard,jump+1)[0]
    _require(target==return_at,'inline-guard-replacement-exit',return_at,target)


def _check_inline_flow(contract,bodies,probes,partitions,methods,dependency_bodies,carriers,vector_layout,decode):
    """Complete split-stack collector shape; all selected stores/calls are bounded."""
    raw=bodies['collector'];rows=partitions['collector']
    def at(name):return contract['probes'][name]['offset']
    def after(name):return at(name)+len(probes[name])
    calls={row['target']:row['offset'] for row in contract['calls'] if row['window']=='collector'}
    expected_roles={'gridErosion','posList','num','groupIndex','index','vectorClone','decoder','valueForwarder'}
    _require(set(calls)==expected_roles,'inline-call-roster',sorted(expected_roles),sorted(calls))
    expected={
        'frame':'488D68C84881EC20010000',
        'initialCounter':'33DB','saveList':'498BF8','saveComp':'488BF2','saveThis':'4C8BF1',
        'selectGridAndRoot':'4C8D4C2430488BD64C8D45B0498BCE',
        'rootGetterArgs':'448B442430488D55B0488D4DF0',
        'groupGetterArgs':'4533C0488D542470488D4DF00F10000F114424700F1048100F114D80',
        'groupNumArgs':'33D2488D4C24500F10000F114424500F1048100F114C2460',
        'groupIndexArgs':'4533C0488D542450488D4DF0',
        'indexArgs':'33D2488D4D900F10000F1145900F1048100F114DA0',
        'numCapture':'8BF0','indexCapture':'448BF0','numGuard':'85F67E64',
        'loopIndex':'468D0433488D55B0488D4DF0',
        'decodeArgs':'488D55D0488D4D10',
        'listArgs':'488D542440488BCFF20F10008B4008F20F1144244089442448',
        'loopControl':'FFC33BDE7C9C',
        'returnFrame':'4C8D9C2420010000498B5B20498B7328498B7B30498BE3415F415E5DC3',
    }
    for name,value in expected.items():
        _require(probes[name]==bytes.fromhex(value),'inline-'+name,value,probes[name].hex())
    _require(at('frame')==20 and at('initialCounter')==after('frame') and at('saveList')==42 and
             at('saveComp')==after('saveList') and at('saveThis')==after('saveComp'),
        'inline-entry-shape','frame then original input saves',[(k,at(k)) for k in ('frame','initialCounter','saveList','saveComp','saveThis')])
    _require(raw[:at('frame')]==bytes.fromhex('488BC44889580848897010488978185541564157'),
        'inline-frame-origin','RAX is entry RSP; three pushes before fixed-frame allocation',raw[:at('frame')].hex())
    guard_at=at('patchBranch');source_at=after('patchBranch');return_at=at('returnFrame')
    _require(guard_at==96,'inline-guard-position',96,guard_at)
    _inline_guard(raw,guard_at,source_at,return_at,collector=True)
    # Initialize only the local slots, then clear the supplied list before lookup.
    initialize=bytes.fromhex('895C24300F57C00F57C90F1145B00F1145C00F114C24500F114C24600F114424700F1145800F114D900F114DA00F1145D00F1145E0')
    _require(raw[source_at:at('clearList')]==initialize,'inline-local-initialization','zeroed lookup outputs and carrier slots',raw[source_at:at('clearList')].hex())
    clear=probes['clearList']
    _require(clear[:5]==bytes.fromhex('4885FF7506') and clear[5]==0xe8 and
             clear[10:]==bytes.fromhex('CCFF471C895F18') and after('clearList')==at('selectGridAndRoot'),
        'inline-list-clear','null exception; version increment; zero count on original list',clear.hex())
    for name,target in (('rootGetterArgs','gridErosion'),('groupGetterArgs','posList'),
                        ('groupNumArgs','num'),('indexArgs','index'),('loopIndex','vectorClone'),
                        ('decodeArgs','decoder'),('listArgs','valueForwarder')):
        _require(after(name)==calls[target],'inline-adjacent-'+name,calls[target],after(name))
    lookup=after('selectGridAndRoot')
    _direct_call_boundary(rows,lookup,'supplied-grid-and-index-lookup')
    _require(lookup+5==at('rootGetterArgs') and calls['gridErosion']+5==at('groupGetterArgs') and
        calls['posList']+5==at('groupNumArgs') and calls['num']+5==at('groupIndexArgs') and
        after('groupIndexArgs')==at('numCapture') and after('numCapture')==calls['groupIndex'] and
        calls['groupIndex']+5==at('indexArgs') and calls['index']+5==at('indexCapture') and
        after('indexCapture')==at('numGuard') and after('numGuard')==at('loopIndex'),
        'inline-carrier-chain','no intervening source or count/index writes',calls)
    # The selected grid occupies RBP-80, RSP+112 == RBP-144, and scalar carriers
    # occupy RSP+80 == RBP-176. RBP == RSP+256 follows from the proved prologue.
    _disjoint_slots([('grid',-80,32),('proxy-output',-16,32),('root-source',-144,32),
                     ('group-source',-176,32),('index-source',-112,32),
                     ('vector-source',-48,32),('unity-output',16,12),('list-value',-192,12),('root-index',-208,4)])
    cloned=raw[calls['vectorClone']+5:at('decodeArgs')]
    _require(len(cloned)==27 and cloned[:3]==bytes.fromhex('488B0D') and
        cloned[7:22]==bytes.fromhex('0F10000F1145D00F1048100F114DE0') and cloned[22]==0xe8,
        'inline-cloned-carrier','complete returned proxy copied before static initialization call',cloned.hex())
    context=probes['listContext']
    _require(context[:3]==bytes.fromhex('4C8B05') and len(context)==7 and
             calls['decoder']+5==at('listContext') and after('listContext')==at('listArgs') and
             calls['valueForwarder']+5==at('loopControl') and after('loopControl')==return_at,
        'inline-list-context','one RIP context load then exact value argument/call/loop/return',context.hex())
    _require(after('numGuard')+struct.unpack_from('<b',probes['numGuard'],3)[0]==return_at and
             after('loopControl')+struct.unpack_from('<b',probes['loopControl'],5)[0]==at('loopIndex') and
             after('returnFrame')==len(raw),'inline-loop-edges','count exit and index+counter back edge; closed return',len(raw))
    allowed={r['offset'] for r in rows if r['text'].startswith('call ') and bytes.fromhex(r['bytes'])[:1]==b'\xe8'}
    for register,name,end in (('rdi','saveList',at('listArgs')+8),('rsi','saveComp',at('selectGridAndRoot')+8),
                              ('r14','saveThis',after('selectGridAndRoot'))):
        _preserved_interval(rows,after(name),guard_at,register,allowed,'inline-original-prefix-'+register)
        _preserved_interval(rows,source_at,end,register,allowed,'inline-original-'+register)
    _preserved_interval(rows,after('initialCounter'),guard_at,'rbx',allowed,'inline-counter-prefix')
    _preserved_interval(rows,source_at,at('loopControl'),'rbx',allowed,'inline-counter')
    _preserved_interval(rows,after('numCapture'),at('loopControl'),'rsi',allowed,'inline-count')
    _preserved_interval(rows,after('indexCapture'),at('loopControl'),'r14',allowed,'inline-index')
    _preserved_interval(rows,calls['decoder']+5,at('listArgs')+12,'rax',set(),'inline-vector-pointer')
    return _check_decoder_and_helpers(contract,bodies,probes,partitions,methods,dependency_bodies,carriers,vector_layout,decode)


def _lea_rsp(raw):
    _require(len(raw) in (5,8) and raw[0]&0xf8==0x48 and raw[1]==0x8d and raw[2]&7==4 and raw[3]==0x24,
             'rsp-address','LEA register,[RSP+signed displacement]',raw.hex())
    mode=raw[2]>>6
    _require((mode,len(raw)) in ((1,5),(2,8)), 'rsp-address-width','disp8 or disp32',raw.hex())
    dest=((raw[2]>>3)&7)+(8 if raw[0]&4 else 0)
    return dest,struct.unpack_from('<b' if mode==1 else '<i',raw,4)[0]


def check_core_id_flow(raw,method_rva,probes,calls,methods,decode):
    rows=_instruction_partition(raw,method_rva,decode)
    values={}
    for name,probe in probes.items():
        at=probe['offset'];value=bytes.fromhex(probe['bytes'])
        _require(raw[at:at+len(value)]==value,'core-id-witness-'+name,value.hex(),raw[at:at+len(value)].hex())
        values[name]=value
    if values['patchBranch'][:3]==bytes.fromhex('488B05'):
        return _check_inline_core_flow(raw,method_rva,probes,values,calls,methods,rows)
    for role in ('patchCheck','gridErosion','coreId'):
        call=calls[role]
        _direct_call_boundary(rows,call,'core-'+role)
        _require(_relative_call_target(raw,method_rva,call,role)==methods[role]['rva'],
                 'core-id-call-'+role,methods[role]['rva'],_relative_call_target(raw,method_rva,call,role))
    _require(_mov_register(values['saveComp'])==(64,3,2) and _mov_register(values['saveThis'])==(64,7,1),
             'core-id-original-inputs','RDX comp saved in RBX; RCX system saved in RDI',values['saveComp'].hex())
    lookup=values['lookupArgs'];root=values['rootArgs'];core=values['coreArgs']
    grid=_lea_rsp(lookup[11:16]);index_out=_lea_rsp(lookup[:8])
    _require(_mov_register(lookup[8:11])==(64,2,3) and _mov_register(lookup[16:])==(64,1,7),
             'core-id-lookup-inputs','original comp and system receivers',lookup.hex())
    _require(grid[0]==8 and _lea_rsp(root[8:13])==(2,grid[1]),
             'core-id-same-grid','root getter consumes supplied lookup grid',root.hex())
    _require(root[:4]==bytes.fromhex('448B8424') and struct.unpack_from('<i',root,4)[0]==index_out[1],
             'core-id-lookup-index','R8D uses explicit lookup index output',root.hex())
    output=_lea_rsp(root[13:]);input_slot=_lea_rsp(core[2:7])
    _require(output[0]==1 and input_slot==(1,grid[1]) and core[:2]==bytes.fromhex('33D2'),
             'core-id-scalar-input','RCX copied root carrier, RDX zero',core.hex())
    _require(core[7:]==bytes.fromhex('0F10000F1048100F114424300F114C2440') and grid[1]==48,
             'core-id-returned-carrier','RAX root proxy copied to getter source temporary',core.hex())
    patch=values['patchBranch'];at=probes['patchBranch']['offset']
    _require(patch[:3]==bytes.fromhex('84C075') and calls['patchCheck']+5==at,
             'core-id-patch-result','named check AL immediately tested',patch.hex())
    alternate=at+4+struct.unpack_from('<b',patch,3)[0]
    branch=values['getterReturnBranch'];jump_at=probes['getterReturnBranch']['offset']
    ret_at=probes['returnFrame']['offset']
    _require(branch[:1]==b'\xeb' and calls['coreId']+5==jump_at and jump_at+2+struct.unpack_from('<b',branch,1)[0]==ret_at
             and jump_at+2==alternate,'core-id-return-path','getter RAX skips replacement path directly to return frame',branch.hex())
    _require(values['returnFrame']==bytes.fromhex('488B9C24800000004883C4705FC3') and ret_at+len(values['returnFrame'])==len(raw),
             'core-id-no-return-transform','closed return frame does not write RAX',values['returnFrame'].hex())
    def at(name):return probes[name]['offset']
    def after(name):return at(name)+len(values[name])
    _preserved_interval(rows,after('saveComp'),at('lookupArgs')+8,'rbx',{calls['patchCheck']},'core-original-UInt64-to-lookup')
    _preserved_interval(rows,after('saveThis'),at('lookupArgs')+16,'rdi',{calls['patchCheck']},'core-original-system-to-lookup')
    _preserved_interval(rows,calls['gridErosion']+5,at('coreArgs')+14,'rax',set(),'core-returned-proxy-to-loads')
    _preserved_interval(rows,at('coreArgs')+10,at('coreArgs')+14,'xmm0',set(),'core-proxy-first-half')
    _preserved_interval(rows,at('coreArgs')+14,at('coreArgs')+19,'xmm1',set(),'core-proxy-second-half')
    _preserved_interval(rows,at('coreArgs')+7,calls['coreId'],'rcx',set(),'core-source-address')
    _preserved_interval(rows,at('coreArgs')+2,calls['coreId'],'rdx',set(),'core-zero-context')
    _disjoint_slots([('root-return',output[1],32),('core-source',input_slot[1],32)])
    return {'storedField':'ErosionRootComp.ErosionCoreId','returnType':'System.UInt64',
            'selectedGetterReturnUnchanged':True,'runtimeObserved':False,'coreIdTargetResolved':False}


def _check_inline_core_flow(raw,method_rva,probes,values,calls,methods,rows):
    """The source branch keeps original RDX and returns its named getter directly."""
    def at(name):return probes[name]['offset']
    def after(name):return at(name)+len(values[name])
    expected={'frame':'4055488D6C24A94881EC90000000','saveThis':'4C8BD1',
        'lookupArgs':'4C8D4D7F4C8D4517498BCA',
        'lookupInit':'0F1145170F1145270F114DF70F114D07',
        'rootArgs':'448B457F488D5517488D4D37',
        'coreArgs':'33D2488D4DF70F10000F1145F70F1048100F114D07',
        'returnFrame':'4881C4900000005DC3'}
    for name,value in expected.items():
        _require(values[name]==bytes.fromhex(value),'inline-core-'+name,value,values[name].hex())
    _require(set(calls)=={'gridErosion','coreId'},'inline-core-call-roster',['gridErosion','coreId'],sorted(calls))
    for role,call in calls.items():
        _direct_call_boundary(rows,call,'inline-core-'+role)
        actual=_relative_call_target(raw,method_rva,call,role)
        _require(actual==methods[role]['rva'],'core-id-call-'+role,methods[role]['rva'],actual)
    source_at=after('patchBranch')
    _require(at('frame')==0 and after('frame')==at('patchBranch') and
             raw[source_at:at('lookupArgs')]==bytes.fromhex('0F57C0C7457F000000000F57C9'),
        'inline-core-entry','proved RBP frame and zeroed lookup index',source_at)
    _inline_guard(raw,at('patchBranch'),source_at,at('returnFrame'),collector=False)
    _require(after('lookupArgs')==at('lookupInit') and after('lookupInit')+5==at('rootArgs') and
             after('rootArgs')==calls['gridErosion'] and calls['gridErosion']+5==at('coreArgs') and
             after('coreArgs')==calls['coreId'] and calls['coreId']+5==at('returnFrame') and
             after('returnFrame')==len(raw),
        'inline-core-chain','adjacent original lookup, root getter, copied carrier, UInt64 getter and return',calls)
    _direct_call_boundary(rows,after('lookupInit'),'inline-core-supplied-grid-lookup')
    _preserved_interval(rows,source_at,after('lookupInit'),'rdx',set(),'inline-core-original-component')
    _preserved_interval(rows,source_at,after('lookupArgs'),'r10',set(),'inline-core-original-system')
    _disjoint_slots([('grid',23,32),('root-return',55,32),('core-source',-9,32),('root-index',127,4)])
    return {'storedField':'ErosionRootComp.ErosionCoreId','returnType':'System.UInt64',
            'selectedGetterReturnUnchanged':True,'runtimeObserved':False,'coreIdTargetResolved':False}



def _check_method(image,row):
    image.validate_method_row([row['index'],row['type'],row['method'],row['rva']],label='erosion_consumers')
    method=image.metadata.methods[row['index']];params=image.metadata.parameters_for(method)
    actual=[image.metadata.metadata_type_name(p.type_index) for p in params]
    _require(actual==row['parameters'],'method-parameters-'+row['method'],row['parameters'],actual)
    _require(image.metadata.metadata_type_name(method.return_type)==row['returnType'],'method-return-'+row['method'],row['returnType'],image.metadata.metadata_type_name(method.return_type))
    if row['returnType'] in PRIMITIVE_TYPE_CODES:
        _ordinary_primitive_abi(image,method.return_type,PRIMITIVE_TYPE_CODES[row['returnType']],row['method']+'-return')
    for ordinal,(param,expected) in enumerate(zip(params,row['parameters'])):
        if expected in PRIMITIVE_TYPE_CODES:
            _ordinary_primitive_abi(image,param.type_index,PRIMITIVE_TYPE_CODES[expected],row['method']+f'-parameter{ordinal}')
    if 'parameterNames' in row:
        actual=[image.metadata.string(p.name_index) for p in params]
        _require(actual==row['parameterNames'],'parameter-names-'+row['method'],row['parameterNames'],actual)
    raw=image.pe.bytes_at_va(image.pe.image_base+row['rva'],row['bodyExtent'])
    _require(hashlib.sha256(raw).hexdigest().upper()==row['bodySha256'].upper(),'method-bytes-'+row['method'],row['bodySha256'],hashlib.sha256(raw).hexdigest().upper())
    return raw


def validate(gameassembly,metadata):
    contract,_=read_reviewed_contract(CONTRACT,schema=SCHEMA,status='validated',label='erosion_consumers')
    inputs=contract['nativeInputs']
    gate=check_installed_native_inputs(inputs['gameAssemblySha256'],inputs['metadataSha256'],gameassembly=gameassembly,metadata=metadata)
    _require(gate.status==NATIVE_EVIDENCE_VALIDATED,'native-inputs','validated',f'{gate.status}:{gate.detail}')
    unity=_fingerprint(Path(gameassembly).parent/'UnityPlayer.dll')
    _require(unity['sha256'].upper()==inputs['unityPlayerSha256'].upper(),'unity-input',inputs['unityPlayerSha256'],unity['sha256'])
    image=open_native_image(gameassembly,metadata);methods=dict(contract['methods']);native_bodies={};catalogs={}
    for dependency in contract['dependencies']:
        filename=dependency['path']
        catalog,_=read_reviewed_contract(CONTRACTS_DIR/filename,schema=dependency['schema'],status='validated',label='erosion_consumers_dependency')
        _require(catalog['nativeInputs']==inputs,'dependency-build-'+filename,inputs,catalog['nativeInputs'])
        catalogs[filename]=catalog
        for role,selector in dependency['methodRoles'].items():
            rows=[row for row in catalog['methods'] if (row['type'],row['method'])==(selector['type'],selector['method'])]
            _require(len(rows)==1,'dependency-method-'+role,'one selected method',len(rows))
            methods[role]=rows[0]
    for role,row in methods.items():native_bodies[role]=_check_method(image,row)
    _method_call_abi(image,methods,contract['methodCallAbi'])
    for role in ('gridErosion','vectorOriginal','posList','groupIndex'):
        method=image.metadata.methods[methods[role]['index']]
        bits=_raw_type_abi(image,method.return_type,role+'-proxy-return')
        _require((bits>>16)&0xff==0x11 and (bits>>24)&0x7f==0,
            'ordinary-value-return-'+role,'value kind11; low seven flags zero',f'rawBits={bits:08X}')
    bodies={}
    extents=image.mapper.pdata_function_extents(image.pe)
    for role,window in contract['windows'].items():
        raw=image.pe.bytes_at_va(image.pe.image_base+window['rva'],window['bodyExtent'])
        _require(hashlib.sha256(raw).hexdigest().upper()==window['bodySha256'].upper(),'window-'+role,window['bodySha256'],hashlib.sha256(raw).hexdigest().upper())
        if role!='constructor':
            _require(extents.get(image.pe.image_base+window['rva'])==image.pe.image_base+window['rva']+window['bodyExtent'],
                'primary-body-'+role,window['bodyExtent'],extents.get(image.pe.image_base+window['rva']))
        bodies[role]=raw
    for axis,offset in (('x',0),('y',4),('z',8)):
        _require(_float32_getter_offset(native_bodies[axis],axis)==offset,'stored-axis-'+axis,offset,_float32_getter_offset(native_bodies[axis],axis))
    collector=image.metadata.methods[methods['collector']['index']]
    params=image.metadata.parameters_for(collector)
    resolved=[runtime_type_name(image.pe,image.metadata,image.pe.u64_at_va(int(image.registration['types'],16)+p.type_index*8)) for p in params]
    _require(resolved==['ulong','System.Collections.Generic.List`1<UnityEngine.Vector3>'],'collector-native-types',
        ['ulong','System.Collections.Generic.List`1<UnityEngine.Vector3>'],resolved)
    _list_vector_abi(image,params[1].type_index)
    decoder=image.metadata.methods[methods['decoder']['index']]
    decoder_params=image.metadata.parameters_for(decoder)
    _require_type_shape(image,decoder.return_type,0x11,0x80,'unity-vector-return')
    _require_type_shape(image,decoder_params[0].type_index,0x11,0x20,'fb-vector-source-parameter')
    source_pointer=_type_pointer(image,decoder_params[0].type_index,'fb-vector-source')
    _require(runtime_type_name(image.pe,image.metadata,source_pointer)=='Beyond.Gameplay.Core.DynamicScene.FBDynamicSceneVector3',
        'decoder-source-type','Beyond.Gameplay.Core.DynamicScene.FBDynamicSceneVector3',runtime_type_name(image.pe,image.metadata,source_pointer))
    _require(methods['constructor']['parameterNames']==['x','y','z'] and methods['constructor']['parameters']==['System.Single']*3,
        'constructor-axes','three named x/y/z Single parameters',methods['constructor']['parameterNames'])
    scalar=catalogs['dynamic_scalar_components_native.json']
    carriers=_validate_carriers(scalar['layout'],image)
    vector_layout=next(row for row in catalogs['dynamic_main_vector_native.json']['layout']['vectors'] if row['name']=='Vector3')
    original=methods['vectorOriginal'];primary_end=extents.get(image.pe.image_base+original['rva'])
    _require(primary_end is not None and 0<primary_end-(image.pe.image_base+original['rva'])<=len(native_bodies['vectorOriginal']),
        'owned-vector-primary-body','complete selected primary body inside pinned source window',primary_end)
    native_bodies['vectorOriginal']=native_bodies['vectorOriginal'][:primary_end-(image.pe.image_base+original['rva'])]
    axes=_check_flow(contract,bodies,methods,native_bodies,carriers,vector_layout,image.mapper.decode_x64_subset)
    core_proof=contract['coreIdFlow']
    core_calls={row['target']:row['offset'] for row in core_proof['calls']}
    core_rows=_instruction_partition(bodies['coreReturn'],methods['coreReturn']['rva'],image.mapper.decode_x64_subset)
    for role,at in core_calls.items():
        _direct_call_boundary(core_rows,at,'core-'+role)
    core_result=check_core_id_flow(bodies['coreReturn'],methods['coreReturn']['rva'],
        core_proof['probes'],core_calls,methods,image.mapper.decode_x64_subset)
    return {'format':'endfield.dynamic-erosion-consumers-native-audit.v1','status':'validated','nativeInputs':inputs,
        'flows':{'positions':{'collector':methods['collector']['type']+'.'+methods['collector']['method'],
            'collectorParameterTypes':resolved,'sourceField':'ErosionRootComp.PosList',
            'sourceIndex':'DataGroup.index.Index','sourceCount':'DataGroup.Num',
            'axes':axes,'valueArgumentWidth':12,'listInsertionProved':False,'runtimeObserved':False},
            'coreIdReturn':core_result},'evidenceBoundary':contract['evidenceBoundary']}



def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gameassembly',type=Path,required=True);parser.add_argument('--metadata',type=Path,required=True)
    parser.add_argument('--output-json',type=Path,default=REPO_ROOT/'reports/animestudio/dynamic_erosion_consumers_native_latest.json')
    args=parser.parse_args(argv)
    try:
        sources=_parser_source_snapshots(Path(__file__))
        contract=json.loads(CONTRACT.read_text())
        sources.extend(_fingerprint(path) for path in [CONTRACT,NATIVE_MAPPER_PATH,METADATA_HELPER_PATH,
            *(CONTRACTS_DIR/dependency['path'] for dependency in contract['dependencies'])])
        inputs=[_fingerprint(path) for path in (args.gameassembly,args.metadata,args.gameassembly.parent/'UnityPlayer.dll')]
        protected=[Path(row['path']) for row in sources+inputs]
        groups._guard_publication(args.output_json,protected)
        result=validate(args.gameassembly,args.metadata)
        result['proofSources']=sources;result['proofInputs']=inputs
        encoded=json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
        groups._require_unchanged(sources+inputs);groups._guard_publication(args.output_json,protected)
        atomic_write_text(args.output_json,encoded)
    except (OSError,ValueError,KeyError,IndexError,RuntimeError,struct.error) as exc:
        print(f'dynamic-erosion-consumers-native:{str(exc)[:1400]}',file=sys.stderr);return 1
    print('Erosion native consumers passed: PosList axes -> Unity Vector3 argument; CoreId getter -> UInt64 return; runtime unresolved')
    return 0


if __name__=='__main__':raise SystemExit(main())
