"""Complete selected positive instance-adapter ownership below root admission.

The buffered non-FF peek delegates consumption to the same saved Reader. The
nonabstract branch passes the owned wrapper CreateInstance MethodInfo, saves
its returned reference in a local slot, dispatches the wrapper formatter into
that same slot, and converts the result through the original typed interface.
The zero and nonzero child outputs have separate complete original stores.

All runtime type/cache/provider choices and normal callee returns are explicit
conditions. A class-key prefix proves unused incoming R8/RDX pointer bits are
killed before use on that selected path; it does not prove helper purity or
creation effects. This module grants no stored element, positive list or root
admission and never replaces the instance body with its static helper.
"""
from __future__ import annotations

import re
import struct
from typing import Any, Callable

from scripts.game_data.il2cpp.context import method_parameter_owner
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.memorypack.buffered_owned_sources import _move, VOLATILE
from scripts.game_data.memorypack.reference_conversion_sources import (
    validate_program, _target, _canonical, _integer_write, _data_memory, _qword)


def validate_type_key_byref_liveness(image: Any, proof: dict, *, fail: Callable) -> dict:
    """Authenticate a prefix ending at the full RDX kill, not a full return."""
    program=proof['program'];windows=proof['codeWindows'];offset=proof['classCacheDisplacement']
    if type(offset)is not int or not 0<=offset<=0xffff:
        fail('instance-type-key-class-offset','bounded integer class cache displacement',offset)
    expected=['4053','4883EC20','0FBE410A',None,'488BD9','83F80F',None,'83F816',None,
        '0FBE430A','83F812',None,'488BCB','4883C420','5B',None,'4885C9',None,'488B09',
        None,None,'486390'+struct.pack('<I',offset).hex().upper()]
    if (len(program)!=len(expected)
            or not windows or program[0][0]!=windows[0]['startRva']):
        fail('instance-type-key-prefix','bounded class-key prefix ending in full incoming RDX overwrite',proof)
    image.check_windows(windows,label='referenceInstanceTypeKey')
    for n, ((at,raw_hex),wanted) in enumerate(zip(program,expected,strict=True)):
        raw=bytes.fromhex(raw_hex)
        if (not any(w['startRva']<=at<at+len(raw)<=w['endRva']for w in windows)
                or wanted is not None and raw_hex!=wanted):
            fail('instance-type-key-prefix-transfer',{'position':n,'bytes':wanted},[at,raw_hex])
        image.check_instruction_windows([[at,raw_hex]],label='referenceInstanceTypeKey')
        if n==3 and (len(raw)!=7 or raw[:3]!=b'\x4c\x8d\x05'):
            fail('instance-type-key-r8-kill','full RIP-derived R8 before its first read',program[n])
        if n==20 and (len(raw)!=7 or raw[:3]!=b'\x48\x8b\x05'):
            fail('instance-type-key-cache-source','independent RIP-derived class cache',program[n])
    branches={6:(0x7c,False),8:(0x7c,True),11:(0x75,False),17:(0x74,False)}
    for n, ((at,raw_hex),following) in enumerate(zip(program,program[1:])):
        raw=bytes.fromhex(raw_hex);next_at=at+len(raw)
        if n in (15,19):
            if len(raw)!=5 or raw[0]!=0xe9:fail('instance-type-key-tail','complete actual direct tail',program[n])
            next_at=_target(at,raw)
        elif n in branches:
            opcode,take=branches[n]
            if len(raw)!=2 or raw[0]!=opcode:fail('instance-type-key-guard','exact class-kind/non-null guard',program[n])
            if take:next_at=_target(at,raw)
        if following[0]!=next_at:fail('instance-type-key-prefix-edge',next_at,following)
    return {'entryRva':program[0][0],'classKind':0x12,'incomingR8KilledAt':program[3][0],
        'incomingRdxKilledAt':program[-1][0],'prefixInstructionCount':len(program),
        'fullReturnProved':False,'globalEffectsProved':False}


def validate_instance_context(image: Any, adapter: dict, method_contexts: list,
                              entries: Any, helper_definition: int, *, fail: Callable) -> dict:
    """Additional owned wrapper key/CreateInstance and method-MVAR joins.

    The caller first authenticates these complete ranges and the adapter's
    conversion context. Runtime substitution is still a condition.
    """
    selected=NativeReferenceContext(image);td=image.metadata.types[adapter['definition']]
    section=image.metadata.sections['genericContainers']
    start=struct.unpack_from('<iiii',image.metadata.buf,section.offset+td.generic_container_index*16)[3]
    slots={r['relativeSlot']:r for r in adapter['entries']}
    def payload(row,kind):
        raw=bytes.fromhex(row['rawHex'])
        if (len(raw)!=16 or row['kind']!=kind or int.from_bytes(raw[:4],'little')!=kind
                or image.pe.u32_at_va(int.from_bytes(raw[8:],'little'))!=row['index']):
            fail('instance-context-payload',kind,row)
    for slot,kind in ((3,3),(7,2),(10,1),(11,3)):payload(slots[slot],kind)
    for slot in (7,10):
        raw=image.pe.bytes_at_va(selected.type_pointer(slots[slot]['index']),16)
        if raw[10:12]!=b'\x13\x00' or int.from_bytes(raw[:8],'little')!=start+1:
            fail('instance-wrapper-key-var','same owned adapter wrapper VAR',raw.hex())
    if slots[7]['index']!=slots[10]['index']:
        fail('instance-wrapper-key-join','identical wrapper type/key descriptor',slots)
    helper_spec=entries.specs[slots[3]['index']]
    if (list(helper_spec)!=slots[3]['methodSpec'] or helper_spec[0]!=helper_definition
            or helper_spec[2]!=-1):
        fail('instance-helper-companion-spec','same two-argument adapter class helper',helper_spec)
    arguments=image.instantiations.resolve(helper_spec[1]).arguments
    if len(arguments)!=2:fail('instance-helper-context-arity',2,len(arguments))
    for n,arg in enumerate(arguments):
        raw=image.pe.bytes_at_va(arg.type_pointer_va,16)
        if raw[10:12]!=b'\x13\x00' or int.from_bytes(raw[:8],'little')!=start+n:
            fail('instance-helper-owned-var',[start,n],raw.hex())
    provider=entries.specs[slots[4]['index']];activator=entries.specs[slots[11]['index']]
    if (list(activator)!=slots[11]['methodSpec'] or activator[1]!=-1
            or activator[2]!=provider[2]):
        fail('instance-activator-wrapper-instance','same exact wrapper method instantiation as provider',activator)
    expected={provider[0]:('MemoryPack.MemoryPackFormatterProvider','GetFormatter'),
              activator[0]:('System.Activator','CreateInstance')}
    by_definition={r['definition']:r for r in method_contexts}
    if len(by_definition)!=2 or set(by_definition)!=set(expected):
        fail('instance-method-context-bijection','owned provider and activator contexts',method_contexts)
    result=[]
    containers=[m.generic_container_index for m in image.metadata.methods]
    for definition,(type_name,method_name) in expected.items():
        row=by_definition[definition];m=image.metadata.methods[definition]
        at=section.offset+m.generic_container_index*16
        if (not row['isMethod'] or m.generic_container_index<0
                or not section.offset<=at<=section.offset+section.size-16
                or image.type_name(m.declaring_type)!=type_name
                or image.metadata.string(m.name_index)!=method_name or not m.flags&0x10
                or image.metadata.parameters_for(m)):
            fail('instance-static-method-context-owner',[type_name,method_name],row)
        owner,count,is_method,mvar=struct.unpack_from('<iiii',image.metadata.buf,at)
        identity=method_parameter_owner(image.metadata.buf,mvar,containers,source='referenceInstance')
        if (owner,count,is_method)!=(definition,1,1) or identity['methodIndex']!=definition or identity['ordinal']!=0:
            fail('instance-owned-method-mvar','one reciprocal method parameter',identity)
        method_slots={r['relativeSlot']:r for r in row['entries']}
        if len(method_slots)!=2 or set(method_slots)!={0,1}:fail('instance-method-context-slots','two exact method slots',row)
        payload(method_slots[0],1);payload(method_slots[1],2)
        key=image.pe.bytes_at_va(selected.type_pointer(method_slots[0]['index']),16)
        if key[10:12]!=b'\x1e\x00' or int.from_bytes(key[:8],'little')!=mvar:
            fail('instance-method-key-mvar','same owned method parameter',key.hex())
        target=image.pe.bytes_at_va(selected.type_pointer(method_slots[1]['index']),16)
        if method_name=='CreateInstance':
            if target!=key:fail('instance-activator-result-type','same MVAR key and result class',target.hex())
        else:
            if target[10:12]!=b'\x15\x00':fail('instance-provider-result-type','formatter over owned MVAR',target.hex())
            definition_ptr,inst_ptr=struct.unpack('<QQ',image.pe.bytes_at_va(int.from_bytes(target[:8],'little'),16))
            root=image.pe.bytes_at_va(definition_ptr,16)
            args=image.instantiations.resolve_pointer(inst_ptr).arguments
            if (root[10:12]!=b'\x12\x00' or image.type_name(int.from_bytes(root[:8],'little'))!='MemoryPack.MemoryPackFormatter`1'
                    or len(args)!=1 or image.pe.bytes_at_va(args[0].type_pointer_va,16)!=key):
                fail('instance-provider-owned-result','formatter of the same owned MVAR',target.hex())
        signature=image.pe.bytes_at_va(selected.type_pointer(m.return_type),16)
        if signature!=target:fail('instance-method-result-signature','context result identical to declared return type',signature.hex())
        result.append({'methodDefinition':definition,'methodParameterOrdinal':0,'runtimeInflationObserved':False})
    return {'adapterOriginalOrdinal':0,'adapterWrapperOrdinal':1,'additionalAdapterSlots':[3,7,10,11],
        'ownedMethodContexts':result,'activatorAndProviderShareWrapperInstantiation':True}


def validate_type_flags_dispatch(image: Any, proof: dict, actual_getter: int, *, fail: Callable) -> dict:
    """Full slot-66 optimized RuntimeType dispatch reads a class Int32 slot."""
    validate_program(image,proof,fail=fail,extra_opcodes={'490306':'add rax, [r14]'})
    expected=['48895C2408','55','56','57','4154','4155','4156','4157','4883EC50','4C8BF2',
        '0FB7D9','488B0A',None,'488D4314','48C1E004','490306','4C8B00','488B5008',None,
        '4C3BC0',None,None,'4C3BC0',None,'B201','498B4E10',None,'488BD8','488BC8',None,
        '8B8314010000',None,'488B9C2490000000','4883C450','415F','415E','415D','415C','5F','5E','5D','C3']
    rows=proof['program']
    if len(rows)!=len(expected):fail('instance-flags-profile-size',len(expected),len(rows))
    for n,(row,wanted) in enumerate(zip(rows,expected,strict=True)):
        if wanted is not None and row[1]!=wanted:fail('instance-flags-owned-transfer',[n,wanted],row)
    for lea,branch,opcode,taken,equal in ((18,20,b'\x0f\x85',True,False),(21,23,b'\x75',False,True)):
        at,h=rows[lea];raw=bytes.fromhex(h);ba,bh=rows[branch];br=bytes.fromhex(bh)
        if len(raw)!=7 or raw[:3]!=b'\x48\x8d\x05' or br[:len(opcode)]!=opcode:
            fail('instance-flags-pointer-guard','actual optimized pointer comparison',rows[lea:branch+1])
        pointer=at+7+int.from_bytes(raw[3:],'little',signed=True)
        if (pointer==actual_getter)!=equal or rows[branch+1][0]!=(_target(ba,br)if taken else ba+len(br)):
            fail('instance-flags-concrete-selection','actual RuntimeType getter pointer and selected equality edge',pointer)
    calls={}
    for n,key in ((12,'classPrepare'),(26,'typeKey'),(29,'classInitialize')):
        at,h=rows[n];raw=bytes.fromhex(h)
        if len(raw)!=5 or raw[0]!=0xe8:fail('instance-flags-relative-call','actual full direct call',rows[n])
        calls[key]=_target(at,raw)
    return {'slot':66,'receiverTypeFieldOffset':16,'classInt32ResultOffset':276,
        'resultBits':32,'calls':calls,'runtimeReceiverSelectionObserved':False,
        'classFlagsMatchMetadata':'conditional'}


def validate_positive_instance_transfer(image: Any, proof: dict, calls: dict, offsets: dict,
                                        *, null_wrapper: bool, fail: Callable,
                                        creation: str = 'concrete') -> dict:
    """Own the concrete-created or abstract-zero local through full child/output return."""
    if creation not in ('concrete', 'abstract'):
        fail('instance-creation-mode', 'concrete or abstract selected branch', creation)
    abstract = creation == 'abstract'
    rows=validate_program(image,proof,fail=fail,extra_opcodes={'A980000000':'test eax, 0x80'})
    prefix=['48895C2408','4C894C2420','4C89442418','4889542410','55','56','57','4154','4155','4156','4157',
        '4881EC90000000','498BD9','498BF0','488BFA',None,None,
        f'837F{offsets["bufferLength"]:02X}01',None,f'488B47{offsets["currentPtr"]:02X}','8038FF',None]
    if len(proof['program'])<len(prefix)+10:fail('instance-prefix-size','complete buffered positive path',proof)
    for n,wanted in enumerate(prefix):
        if wanted is not None and proof['program'][n][1]!=wanted:fail('instance-buffered-prefix',[n,wanted],proof['program'][n])
    for n,op in ((16,0x75),(18,0x7d),(21,0x75)):
        at,h=proof['program'][n];raw=bytes.fromhex(h)
        if len(raw)!=2 or raw[0]!=op or proof['program'][n+1][0]!=_target(at,raw):
            fail('instance-positive-peek-edge','initialized/buffered/non-FF taken guards',proof['program'][n])
    registers={'rdx':'reader','r8':'originalOut','r9':'parentCompanion'};slots={};sp=0
    dispatch=[];conversion=[];stores=[];reader_reloads=[];created=[];flags_guard=None;wrapper_guard=None
    candidate_loads=[];key_calls=[];helper_save=False;zero_local=[]
    def borrowed(value):
        return value in ('reader','originalOut','readerPointer') or isinstance(value,tuple) and value[0]=='partialByref'
    ctx_slots={0x18:'helperCompanion',0x20:'providerCompanion',0x40:'originalInterface',0x50:'wrapperTypeKey',0x58:'activatorCompanion'}
    for n, ((at,h),row) in enumerate(zip(proof['program'],rows,strict=True)):
        raw=bytes.fromhex(h);text=row['text']
        save=re.fullmatch(r'mov \[rsp\+0x([0-9a-f]+)\], ([a-z0-9]+)',text)
        reload=re.fullmatch(r'mov ([a-z0-9]+), \[rsp\+0x([0-9a-f]+)\]',text)
        address=re.fullmatch(r'lea ([a-z0-9]+), \[rsp\+0x([0-9a-f]+)\]',text)
        if text.startswith('push '):sp-=8;slots[sp]=registers.get(text[5:]);continue
        if text.startswith('pop '):registers[text[4:]]=slots.get(sp);sp+=8;continue
        if text.startswith(('sub rsp, 0x','add rsp, 0x')):
            sp+=(1 if text.startswith('add')else -1)*int(text.split('0x')[1],16);continue
        if save:
            slot=sp+int(save[1],16);value=registers.get(_canonical(save[2]))if _qword(raw) else None
            if slot in (16,24) and slot in slots:fail('instance-owned-stack-overwrite','saved Reader/output remain intact',[at,h])
            if slot==32 and slot in slots and not helper_save:fail('instance-parent-context-overwrite','helper context consumed before parent save reused',[at,h])
            if slot==-128:
                if value!='helperCompanion':fail('instance-helper-context-save','owned helper MethodInfo',value)
                helper_save=True
            if slot==-168 and created and value!='createdWrap':fail('instance-created-wrap-preservation','same Activator return in local output slot',[at,h,value])
            if slot==-168 and abstract and flags_guard is not None:
                if value!=0:
                    fail('instance-abstract-zero-local', 'full zero reference from the abstract attribute branch', [at,h,value])
                zero_local.append(at)
            slots[slot]=value;continue
        if reload:
            dest=reload[1];slot=sp+int(reload[2],16);value=slots.get(slot)if _qword(raw) else None
            registers[_canonical(dest)]=value
            if value=='reader':reader_reloads.append(at)
            continue
        if address:registers[address[1]]=('stack',sp+int(address[2],16));continue
        move=_move(raw)
        if move:registers[move[0]]=registers.get(move[1]);continue
        if (len(raw)==7 and _qword(raw) and raw[1]in(0x8b,0x8d)
                and raw[2]&0xc7==0x05):
            # A full RIP-relative definition does not depend on the previous
            # register's borrowed pointer bits. Its loaded value stays unknown.
            register=_canonical((row.get('write')or{}).get('register',''))
            registers[register]=None;continue
        load=_data_memory(raw,b'\x8b')
        if load:
            source=registers.get(load['base']);offset=load['offset'];value=None
            if (isinstance(source,tuple)and source[0]=='partialByref' or source=='originalOut'
                    or source=='reader'and offset!=offsets['currentPtr']):
                fail('instance-unowned-byref-read','only the owned positive Reader pointer peek',[at,h,source])
            if _qword(raw):
                if source in ('parentCompanion','helperCompanion') and offset==0x20:value='adapterClass'
                elif (source,offset)==('adapterClass',0xc0):value='adapterContext'
                elif source=='adapterContext':value=ctx_slots.get(offset)
                elif (source,offset)==('providerCompanion',0x38):value='providerMethodContext'
                elif source=='providerMethodContext':value={0:'wrapperTypeKey',8:'expectedWrapperFormatterClass'}.get(offset)
                elif (source,offset)==('selectedFormatter',0):value='actualFormatterClass'
                elif (source,offset)==('reader',offsets['currentPtr']):value='readerPointer'
            registers[load['register']]=value;continue
        if raw==bytes.fromhex('4C8B2CC8'):
            if registers.get('rax')in('reader','originalOut')or registers.get('rcx')in('reader','originalOut'):
                fail('instance-cache-read-alias','cache candidate read cannot use an owned byref',[at,h])
            registers['r13']='cacheCandidate';candidate_loads.append(at);continue
        store=_data_memory(raw,b'\x89')
        if store:
            destination=registers.get(store['base']);value=registers.get(store['register'])
            if destination!='originalOut' or store['offset']!=0 or not _qword(raw) or value!=(0 if null_wrapper else 'originalGetterValue'):
                fail('instance-original-output-store','one full owned original reference store',[at,h,destination,value])
            stores.append(at);continue
        if text.startswith(('mov [','inc [','dec [','add [','sub [','and [','or [','xor [')):
            fail('instance-unowned-memory-write','only owned stack/original output writes', [at,h,text])
        immediate=re.fullmatch(r'mov ([a-z0-9]+), 0x([0-9a-f]+)',text)
        zero=re.fullmatch(r'xor ([a-z0-9]+), \1',text)
        if immediate or zero:
            dest=_canonical(immediate[1]if immediate else zero[1]);prior=registers.get(dest)
            value=_integer_write(raw,immediate=bool(immediate))
            registers[dest]=('partialByref',prior)if value is None and borrowed(prior)else value
            continue
        if h=='A980000000':
            if registers.get('rax')!='typeAttributes':fail('instance-attribute-flag-source','actual slot-66 query result',registers)
            ba,bh=proof['program'][n+1];br=bytes.fromhex(bh)
            if (len(br)!=2 or br[:1]!=b'\x76'
                    or proof['program'][n+2][0]!=(ba+len(br) if abstract else _target(ba,br))
                    or abstract and proof['program'][n+2][1]!='33C0'):
                fail('instance-abstract-creation-branch' if abstract else 'instance-concrete-creation-branch',
                     'bit 0x80 set reaches full zero; clear reaches Activator',proof['program'][n:n+3])
            flags_guard=at
        if re.fullmatch(r'test ([a-z0-9]+), \1',text)and registers.get(text.split()[1][:-1])=='wrapperOutput':
            ba,bh=proof['program'][n+1];br=bytes.fromhex(bh)
            if not _qword(raw) or br[:1]!=b'\x75'or proof['program'][n+2][0]!= (ba+len(br)if null_wrapper else _target(ba,br)):
                fail('instance-child-wrapper-branch','full wrapper zero/nonzero branch',proof['program'][n:n+3])
            wrapper_guard=at
        if raw[0]==0xe8 or text.startswith('call '):
            target=_target(at,raw)if len(raw)==5 and raw[0]==0xe8 else None;returned=None
            if target==calls['typeKey']:
                if registers.get('rcx')!='wrapperTypeKey':fail('instance-wrapper-type-key','owned wrapper key reaches class helper',registers)
                key_calls.append(at)
            elif target==calls['typeFlags']:
                if registers.get('rcx')!=66 or registers.get('rdx')!='cacheCandidate':fail('instance-attributes-arguments','slot 66 and selected cache object',registers)
                returned='typeAttributes'
            elif target==calls['activator']:
                if abstract:fail('instance-abstract-activator-call','selected abstract path makes no direct creation call',[at,h])
                if registers.get('rcx')!='activatorCompanion'or flags_guard is None:fail('instance-wrapper-activator-context','owned wrapper MethodInfo on concrete branch',registers)
                created.append(at);returned='createdWrap'
            elif target==calls['formatterResult']:
                if registers.get('rcx')!='cacheCandidate':fail('instance-provider-candidate','actual cache object reaches provider result helper',registers)
                returned='selectedFormatter'
            elif target==calls['formatterClassPredicate']:
                if registers.get('rcx')!='actualFormatterClass'or registers.get('rdx')!='expectedWrapperFormatterClass':
                    fail('instance-formatter-type-arguments','provider-owned expected result class and actual candidate class',registers)
            elif target==calls['formatterDispatch']:
                if (registers.get('rcx')!=5 or registers.get('rdx')!='selectedFormatter'
                        or registers.get('r8')!='reader' or registers.get('r9')!=('stack',-168)
                        or slots.get(-168)!=(0 if abstract else 'createdWrap') or slots.get(16)!='reader'or slots.get(24)!='originalOut'):
                    fail('instance-formatter-owned-arguments','slot five, same Reader and preserved created-wrapper local',registers)
                slots[-168]='wrapperOutput';dispatch.append(at)
            elif target==calls['interfaceConversion']:
                if (registers.get('rcx')!=0 or registers.get('rdx')!='originalInterface'
                        or registers.get('r8')!='wrapperOutput'or wrapper_guard is None):
                    fail('instance-original-interface-arguments','original typed interface and same child wrapper',registers)
                returned='originalGetterValue';conversion.append(at)
            for register in ('rcx','rdx','r8','r9'):
                value=registers.get(register)
                if borrowed(value)and not (
                        target==calls['typeKey']and register in('rdx','r8')
                        or target==calls['formatterDispatch']and register=='r8'):
                    fail('instance-owned-byref-escape','owned byrefs reach only the proved child/type-key argument paths',[at,register,value])
                if isinstance(value,tuple)and value[0]=='stack' and not(target==calls['formatterDispatch']and register=='r9'and value==('stack',-168)):
                    fail('instance-owned-slot-escape','local output slot reaches only child dispatch',[at,register,value])
            for register in VOLATILE:registers.pop(register,None)
            registers['rax']=returned;continue
        written=(row.get('write')or{}).get('register')
        if written:
            register=_canonical(written);prior=registers.get(register)
            # Unmodelled arithmetic cannot silently erase borrowed-bit provenance.
            registers[register]=('partialByref',prior)if borrowed(prior)else None
    if (sp!=0 or len(created)!=(0 if abstract else 1) or len(zero_local)!=(1 if abstract else 0)
            or len(dispatch)!=1 or len(stores)!=1 or len(conversion)!=(0 if null_wrapper else 1)
            or len(candidate_loads)!=2 or len(key_calls)!=2 or not reader_reloads or flags_guard is None or wrapper_guard is None):
        fail('instance-complete-owned-path','one complete creation/child/output and required context/reload paths',
            {'stack':sp,'creation':created,'dispatch':dispatch,'stores':stores,'conversion':conversion,'readerReloads':reader_reloads})
    return {'readerReloads':reader_reloads,'readerDirectCounterStores':0,'positivePeekWireBytesConsumed':0,
        'wrapperCreationCall':created[0] if created else None,
        'wrapperLocalEntryValue':'zero' if abstract else 'typed Activator return',
        'abstractZeroLocalStore':zero_local[0] if zero_local else None,
        'wrapperOutputEntryOffset':-168,'formatterDispatch':dispatch[0],
        'originalOutputStore':stores[0],'originalInterfaceConversion':conversion[0]if conversion else None,
        'nullWrapperOutput':null_wrapper,'runtimeSelectionObserved':False,'creationEffectsProved':False}
