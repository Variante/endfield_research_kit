"""Reprove Unity AnimationCurve's current buffered source and pointer loop.

The proof owns the named formatter's complete unwind family and walks each
selected instruction. Callback names identify stored destinations; callback
execution, refill paths and curve evaluation remain outside the claim.
"""
from __future__ import annotations

import json
import struct

from scripts.game_data.buff_frontiers_regenerate import _method_row
from scripts.game_data.il2cpp.initializer_control import control_transfer
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets, runtime_type_name
from scripts.game_data.memorypack import buff_ec_profiles_native as ec
from scripts.game_data.memorypack.pooled_inline_sources import _Path
from scripts.game_data.memorypack.wrapper_members import unmanaged_value_sizes_from_image

SCHEMA = 'endfield.memorypack-animation-curve-native-contract.v2'
OWNER = 'MemoryPack.AnimationCurveFormatter'
FIELDS = (('m_Time','float'),('m_Value','float'),('m_InTangent','float'),
          ('m_OutTangent','float'),('m_WeightedMode','int'),('m_InWeight','float'),('m_OutWeight','float'))
LABEL = 'animationCurveSource'


def need(check, condition, detail=None):
    if not condition:
        raise ValueError(f'{LABEL}.{check}:{str(detail)[:700]}')


def rip_target(row):
    b=ec.raw(row)
    need('rip-instruction',len(b)==7 and b[:3] in (b'\x48\x8b\x05',b'\x48\x8b\x0d',
         b'\x48\x8d\x0d',b'\x48\x89\x05'),row)
    return ec.va(row)+7+struct.unpack_from('<i',b,3)[0]


def source_program(rows, entry, offsets, *, literal_at):
    """Prove header, two DWORDs, signed count, one inductive 28-byte loop."""
    by={ec.va(r):r for r in rows};g=_Path(rows);g.at=entry
    b,r,c,s=(offsets[n] for n in ('currentPtr','bufferLength','advancedCount','consumed'))
    g.take('push rbx','push rsi','push rdi','push r14','sub rsp, 0xa8',
        f'cmp dword [rdx+{r:#x}], 0x1','mov r14, r8','mov rbx, rdx')
    g.branch(12,False)
    g.take(f'mov rax, [rbx+{b:#x}]','movzx esi, byte [rax]',f'mov edi, [rbx+{r:#x}]','sub edi, 0x1')
    g.branch(8,False)
    g.take(f'inc qword [rbx+{b:#x}]',f'inc dword [rbx+{c:#x}]',f'inc dword [rbx+{s:#x}]',
        f'mov [rbx+{r:#x}], edi','cmp sil, -0x1')
    null_branch=g.rows[g.at];g.branch(4,False)
    g.take('cmp sil, 0x3');g.branch(5,False)
    g.take('mov [rsp+0xd0], rbp','mov [rsp+0xe0], r12','mov [rsp+0xe8], r13',
        'mov [rsp+0xa0], r15',f'cmp dword [rbx+{r:#x}], 0x8')
    g.branch(12,False)
    raw8_at=g.at
    g.take(f'mov rax, [rbx+{b:#x}]','mov r12d, [rax]','mov r13d, [rax+0x4]',
        'mov [rsp+0x24], r12d','mov [rsp+0x28], r13d',f'mov edi, [rbx+{r:#x}]','add edi, -0x8')
    g.branch(8,False)
    g.take(f'add qword [rbx+{b:#x}], 0x8',f'add dword [rbx+{c:#x}], 0x8',
        f'add dword [rbx+{s:#x}], 0x8',f'mov [rbx+{r:#x}], edi','xor esi, esi',
        f'cmp dword [rbx+{r:#x}], 0x4','mov ebp, esi')
    g.branch(12,False)
    count_at=g.at
    g.take(f'mov rax, [rbx+{b:#x}]','movsxd rdi, dword [rax]',f'mov r15d, [rbx+{r:#x}]','add r15d, -0x4')
    g.branch(8,False)
    g.take(f'add qword [rbx+{b:#x}], 0x4',f'add dword [rbx+{c:#x}], 0x4',
        f'add dword [rbx+{s:#x}], 0x4',f'mov [rbx+{r:#x}], r15d',
        'movaps [rsp+0x90], xmm6','movaps [rsp+0x80], xmm7','movaps [rsp+0x70], xmm8',
        'movaps [rsp+0x60], xmm9','movaps [rsp+0x50], xmm10','movaps [rsp+0x40], xmm11')
    array_at=g.at
    prefix=list(g.seen)
    arrays=[]
    for mode in ('null','empty','positive'):
        a=_Path(rows);a.at=array_at;a.take('cmp edi, -0x1');a.branch(4,mode=='null')
        if mode!='null':
            type_load=a.row();need('array-type-load',ec.raw(type_load)[:3]==b'\x48\x8b\x0d')
            a.take('mov edx, edi');call=a.row();need('array-typed-call',control_transfer(call)['kind']=='call')
            a.take('mov rbp, rax','test edi, edi');a.branch(15,mode=='positive')
        arrays.append(dict(mode=mode,addresses=list(a.seen),join=a.at))
    positive=arrays[2]['join'];join=arrays[0]['join']
    need('array-null-empty-join',arrays[1]['join']==join)
    g=_Path(rows);g.at=positive
    g.take('mov [rsp+0x30], rdi','lea rdi, [rax+0x28]','mov r15, rdi','mov r12d, esi',
        'mov r13, rsi','test rbp, rbp');g.branch(4,False)
    loop_at=g.at
    g.take('cmp r12d, dword [rbp+0x18]');g.branch(3,False)
    g.take(f'cmp dword [rbx+{r:#x}], 0x1c');g.branch(12,False)
    g.take(f'mov rax, [rbx+{b:#x}]')
    loads=[]
    for text in ('mov ecx, [rax+0x10]','movss xmm6, [rax]','movss xmm7, [rax+0x4]',
                 'movss xmm8, [rax+0x8]','movss xmm9, [rax+0xc]',
                 'movss xmm10, [rax+0x14]','movss xmm11, [rax+0x18]'):
        loads.append(g.at);g.take(text)
    g.take('mov [rsp+0xd8], ecx',f'mov eax, [rbx+{r:#x}]','add eax, -0x1c','mov [rsp+0x20], eax')
    g.branch(8,False)
    g.take(f'add qword [rbx+{b:#x}], 0x1c',f'add dword [rbx+{c:#x}], 0x1c',
        f'add dword [rbx+{s:#x}], 0x1c',f'mov [rbx+{r:#x}], eax',
        'mov [r15-0x8], rsi','inc r12d','mov [r15+0x4], rsi','inc r13','mov [r15+0xc], rsi')
    stores=[]
    stores.append(g.at);g.take('movss [r15], xmm8','add r15, 0x1c')
    for text in ('movss [rdi-0x8], xmm6','movss [rdi-0x4], xmm7','movss [rdi+0x4], xmm9',
                 'movss [rdi+0xc], xmm10','movss [rdi+0x10], xmm11','mov [rdi+0x8], ecx'):
        stores.append(g.at);g.take(text)
    g.take('mov rdi, r15','cmp r13, qword [rsp+0x30]')
    loop_branch=g.rows[g.at];g.branch(12,False)
    need('loop-induction-edge',control_transfer(loop_branch)['target']==loop_at)
    g.take('mov r12d, [rsp+0x24]','mov r13d, [rsp+0x28]');g.jump()
    need('loop-output-join',g.at==join)
    loop=list(g.seen)
    g.take('cmp qword [r14], rsi');g.branch(5,True)
    bindings=[]
    for field,arg in (('preWrapMode','mov edx, r12d'),('postWrapMode','mov edx, r13d'),('keys','mov rdx, rbp')):
        g.take('mov rbx, [r14]','test rbx, rbx');g.branch(4,False)
        load=g.row();need('cache-load',ec.raw(load)[:3]==b'\x48\x8b\x05')
        g.take('test rax, rax');branch=g.rows[g.at];g.branch(4,False)
        arg_at=g.at;g.take(arg,'mov rcx, rbx')
        if field!='keys':g.take('call rax')
        fallback=_Path(rows);fallback.at=control_transfer(branch)['target']
        literal=fallback.row();need('callback-literal-instruction',ec.raw(literal)[:3]==b'\x48\x8d\x0d')
        expected=(f'UnityEngine.AnimationCurve::set_{field}(UnityEngine.WrapMode)' if field!='keys'
                  else 'UnityEngine.AnimationCurve::SetKeys(UnityEngine.Keyframe[])')
        need('callback-literal',literal_at(rip_target(literal))==expected,field)
        resolver=fallback.row();need('callback-resolver',control_transfer(resolver)['kind']=='call')
        cache=fallback.row();need('cache-store',ec.raw(cache)[:3]==b'\x48\x89\x05'
             and rip_target(cache)==rip_target(load))
        fallback.jump();need('fallback-argument-join',fallback.at==arg_at)
        bindings.append(dict(fieldName=field,literal=expected,literalVa=rip_target(literal),
            cacheCellVa=rip_target(load),resolverTargetVa=control_transfer(resolver)['target'],
            cacheLoad=ec.va(load),cacheBranch=ec.va(branch),argumentStart=arg_at,
            fallbackAddresses=fallback.seen,transferMode='tail' if field=='keys' else 'call'))
    g.take('movaps xmm10, [rsp+0x50]','movaps xmm9, [rsp+0x60]','movaps xmm8, [rsp+0x70]',
        'movaps xmm7, [rsp+0x80]','movaps xmm6, [rsp+0x90]','movaps xmm11, [rsp+0x40]',
        'mov r13, [rsp+0xe8]','mov r12, [rsp+0xe0]','mov rbp, [rsp+0xd0]','mov r15, [rsp+0xa0]',
        'add rsp, 0xa8','pop r14','pop rdi','pop rsi','pop rbx','jmp rax')
    need('shared-callback-resolver',len({b['resolverTargetVa'] for b in bindings})==1)
    normal=list(g.seen[len(loop):])
    null=_Path(rows);null.at=control_transfer(null_branch)['target']
    null.take('xor esi, esi','mov rcx, r14','mov [r14], rsi','add rsp, 0xa8',
        'pop r14','pop rdi','pop rsi','pop rbx')
    tail=null.row();need('null-barrier-tail',control_transfer(tail)['kind']=='jump')
    return dict(prefix=prefix,arrays=arrays,loop=loop,normalOutput=normal,nullOutput=null.seen,
        arrayTypeLoad=ec.va(type_load),arrayCall=ec.va(call),nullBarrierTargetVa=control_transfer(tail)['target'],
        bindings=bindings,loadAddresses=loads,storeAddresses=stores,
        raw8Start=raw8_at,countStart=count_at,loopStart=loop_at,
        induction='RDI=R15=array+40+28*i, R12d=i, R13=i; each source read/copy advances28; i<count and i<arrayLength')


def derive(image,inputs):
    from scripts.game_data.memorypack import animation_curve as consumer
    base=image.pe.image_base
    method=_method_row(image,[0,OWNER,'Deserialize',1])
    family,windows,rows=ec.family(image,method[3])
    offsets=ec.source_offsets(image)
    proof=source_program(rows,base+method[3],offsets,literal_at=image.pe.c_string_at_va)
    owned=consumer.formatter_curve_type(image,source_method=method)
    key=image.named_types['UnityEngine.Keyframe']
    sizes=unmanaged_value_sizes_from_image(image)
    need('keyframe-width',sizes.get('UnityEngine.Keyframe')==28)
    fields=image.metadata.fields_for(key)
    layout=runtime_type_field_offsets(image.metadata,image.pe,image.registration,key.index)
    declared=[]
    for f in fields:
        pointer=image.pe.u64_at_va(int(image.registration['types'],16)+f.type_index*8)
        declared.append((image.metadata.string(f.name_index),runtime_type_name(image.pe,image.metadata,pointer)))
    need('keyframe-fields',declared==list(FIELDS),declared)
    need('keyframe-offsets',layout=={name:16+4*i for i,(name,_) in enumerate(FIELDS)},layout)
    by={ec.va(r):r for r in rows}
    type_load=by[proof['arrayTypeLoad']];cell=rip_target(type_load);word=image.pe.u64_at_va(cell)
    index=(word>>1)&0xfffffff
    need('array-type-usage',word>>29==1 and word&1 and index<image.registration['typesCount'])
    pointer=image.pe.u64_at_va(int(image.registration['types'],16)+index*8)
    need('array-type-name',runtime_type_name(image.pe,image.metadata,pointer)=='UnityEngine.Keyframe[]')
    # The loop starts its pointers eight bytes into the array payload; match
    # every source word to its actual store before recording named wire slots.
    load_order=(1,2,3,4,0,5,6);store_order=(1,2,0,3,6,4,5)
    mapped=[]
    for i,(name,kind) in enumerate(FIELDS):
        mapped.append(dict(fieldName=name,declaredType=kind,wireOffset=4*i,bytes=4,
            runtimeFieldOffset=layout[name],sourceInstruction=ec.site(by[proof['loadAddresses'][load_order[i]]],base),
            destinationInstruction=ec.site(by[proof['storeAddresses'][store_order[i]]],base)))
    def sites(addresses):return [ec.site(by[a],base) for a in addresses]
    bindings=[]
    for binding in proof['bindings']:
        bindings.append({**{k:v for k,v in binding.items() if k not in ('fallbackAddresses',)},
            'fallbackInstructions':sites(binding['fallbackAddresses'])})
    out=dict(schema=SCHEMA,status='exact-current-build',nativeInputs=dict(inputs),sourceMethod=method,
        sourceFamily=family,codeWindows=windows,storedMemberCount=3,keyframeBytes=28,
        keyframeTypeDefinition=key.index,keyframeTypeName='UnityEngine.Keyframe',keyframeFields=mapped,
        readerOffsets=offsets,arrayPayloadOffset=32,formatterCurveType=owned,
        arrayAllocation=dict(typeLoad=ec.site(type_load,base),cellRva=cell-base,typeName='UnityEngine.Keyframe[]',
            call=ec.site(by[proof['arrayCall']],base)),icallBindings=bindings,
        sourcePrograms=dict(prefix=sites(proof['prefix']),arrays=[dict(mode=a['mode'],instructions=sites(a['addresses'])) for a in proof['arrays']],
            keyLoop=sites(proof['loop']),normalOutput=sites(proof['normalOutput']),nullOutput=sites(proof['nullOutput'])),
        loopInduction=proof['induction'],nullBarrierTargetRva=proof['nullBarrierTargetVa']-base,
        evidenceBoundary=dict(exact='Selected one-byte FF/member3 header, two wire DWORDs, signed nullable count, source and destination widths, seven typed Keyframe words and complete current formatter unwind family.',
            direct='Closed Keyframe[] type argument and bounded pointer-induction stores; wrap words and array argument reach separately named callback-resolution caches.',
            conditional='Buffered source, count -1 or nonnegative, compatible output storage, existing nonnull curve for the nonnull output program, resolved caches and ordinary native ABI. The FF clear path is proved separately.',
            unresolved='Live formatter or callback selection, new curve construction, callback execution, invalid/refill parity, interpolation, evaluation or gameplay effects.'))
    return json.loads(json.dumps(out))


def validate_on_image(image,inputs,*,contract=None):
    from scripts.game_data.memorypack import animation_curve as consumer
    contract=contract if contract is not None else consumer._contract()
    need('schema',contract.get('schema')==SCHEMA and contract.get('status')=='exact-current-build')
    need('native-inputs',contract['nativeInputs']==inputs)
    actual=derive(image,inputs)
    need('reviewed-source-proof',actual==contract,ec.first_difference(contract,actual))
    return dict(status='validated',nativeInputs=inputs,keyframeBytes=28,storedMemberCount=3,
                keyframeFields=actual['keyframeFields'],evidenceBoundary=actual['evidenceBoundary'])
