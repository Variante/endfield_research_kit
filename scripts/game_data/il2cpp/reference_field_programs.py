"""Complete caller and setter flow for a cached reference wrapper profile.

The caller authenticates physical ownership, metadata types and every callee.
These grammars prove original local control flow and return-register transfers;
callee wire framing, closed child contexts and actual execution need independent
proof. Symbols and layout declarations are supplied by a reviewed contract.
"""
from __future__ import annotations
import re
from scripts.game_data.il2cpp.program_grammar import ProgramGrammar
from scripts.game_data.il2cpp.zero_wrapper_programs import (
    Joins, _branch, _exact, _flag, _init, _rip)


def _context(g):
    row=g.pattern(r'mov rdx, \[rip[+-]0x[0-9a-f]+ => 0x[0-9a-f]+\]')
    raw=bytes.fromhex(row['bytes'])
    if len(raw)!=7 or raw[:3]!=b'\x48\x8b\x15':g.fail('context-load-width','64-bit RDX RIP load',row)
    return {**row,'usageCellVA':int(row['va'],16)+7+int.from_bytes(raw[3:],'little',signed=True)}


def prove_reference_field_reader(primary,cold,fields,symbols,*,label='referenceFieldReader'):
    """Full original nine/multi-field caller, including FF and count exits.

The selected ordinary source path uses Win64 RCX reader/RDX byref wrapper.
Each callee's return is forwarded to the declared concrete setter unchanged
apart from the separately proved normalized boolean return.
"""
    if not fields or len(fields)>127:raise ValueError(f'{label}.field-count')
    g=ProgramGrammar(primary,label=label);c=ProgramGrammar(cold,label=label+'.cold');j=Joins(label)
    g.take('mov [rsp+0x18], rbx','push rdi','sub rsp, 0x20')
    flag=_flag(g);g.take('mov rbx, rdx','mov rdi, rcx');j.edge('init',_branch(g,'je'))
    j.mark('common',g);g.take('mov rcx, [rbx]');_exact(g,'mov [rsp+0x38], 0x0','c644243800')
    g.take('test rcx, rcx');j.edge('existing',_branch(g,'jne'))
    j.mark('header',g);g.take('lea rdx, [rsp+0x38]','mov rcx, rdi');header=g.call(symbols['header'])
    g.take('test al, al');j.edge('null',_branch(g,'je'))
    g.take('mov [rsp+0x30], rsi');_exact(g,'cmp [rbx], 0x0','48833b00');j.edge('count',_branch(g,'jne'))
    allocation_type=_rip(g,'mov rcx,');g.call(symbols['allocate']);g.take('mov rsi, rax','test rax, rax')
    j.edge('nullThrow',_branch(g,'je'));g.take('xor edx, edx','mov rcx, rax');g.call(symbols['constructor'])
    g.take('mov rcx, rbx');_exact(g,'mov [rbx], rsi','488933');g.call(symbols['barrier'])
    j.mark('count',g);_exact(g,'movzx esi, [rsp+0x38]','0fb6742438')
    _exact(g,f'cmp sil, 0x{len(fields):x}','4080fe'+bytes((len(fields),)).hex());j.edge('invalidCount',_branch(g,'jne'))
    transfers=[]
    moves={'normalized-byte-return':('movzx edx, al','0fb6d0'),
        'int32-return':('mov edx, eax','8bd0'),'single-return':('movaps xmm1, xmm0','0f28c8'),
        'reference-return':('mov rdx, rax','488bd0')}
    for ordinal,field in enumerate(fields):
        start=int(g.rows[g.cursor]['va'],16);context=_context(g) if field.get('contextBefore') is True else None
        final=ordinal==len(fields)-1
        if context is None:g.take('mov rbx, [rbx]' if final else 'mov rsi, [rbx]','mov rcx, rdi')
        else:g.take('mov rcx, rdi','mov rbx, [rbx]' if final else 'mov rsi, [rbx]')
        source=g.call(field['readerEntry']);g.take('test rbx, rbx' if final else 'test rsi, rsi')
        j.edge('nullThrow',_branch(g,'je'));g.take('xor r8d, r8d')
        move=moves.get(field['mode'])
        if move is None:g.fail('source-return-mode',sorted(moves),field['mode'])
        _exact(g,*move);g.take('mov rcx, rbx' if final else 'mov rcx, rsi');setter=g.call(field['setterEntry'])
        transfers.append({'ordinal':ordinal,'fieldName':field['fieldName'],'mode':field['mode'],
            'startVA':start,'sourceCall':source,'setterCall':setter,'contextLoad':context})
    g.take('mov rsi, [rsp+0x30]');j.mark('return',g)
    g.take('mov rbx, [rsp+0x40]','add rsp, 0x20','pop rdi','ret')
    j.mark('init',g);_init(g,symbols['metadataUsageCount'],flag,symbols);j.edge('common',_branch(g,'jmp'))
    j.mark('nullThrow',g);g.call(symbols['nullThrow']);g.take('int3');g.finish()
    j.mark('existing',c);c.take('xor edx, edx');c.call(symbols['onDeserialized']);c.take('nop');j.edge('header',_branch(c,'jmp'))
    j.mark('invalidCount',c);_rip(c,'mov rcx,');_rip(c,'mov rbx,');c.take('cmp [rcx+0xe0], 0x0')
    j.edge('countTypeReady',_branch(c,'jne'));c.call(symbols['classInit']);j.mark('countTypeReady',c)
    c.take('xor edx, edx','mov rcx, rbx');c.call(symbols['getTypeFromHandle'])
    c.take('xor r9d, r9d','movzx r8d, sil');_exact(c,f'mov dl, 0x{len(fields):x}','b2'+bytes((len(fields),)).hex())
    c.take('mov rcx, rax');c.call(symbols['invalidPropertyCount']);c.take('int3')
    j.mark('null',c);c.take('mov rcx, rbx');_exact(c,'mov [rbx], 0x0','48c70300000000')
    c.call(symbols['barrier']);c.take('nop');j.edge('return',_branch(c,'jmp'));c.finish()
    return {'completeOriginalCallerAndColdEdgesChecked':True,'localJoins':j.finish(),
        'headerCall':header,'allocationTypeLoad':allocation_type,'fieldTransfers':transfers,
        'conditionalAllSourceReturnsForwardedToDeclaredSetters':True,
        'conditionalFFClearsFullWrapperOutputAndReturns':True,
        'invalidPropertyCountsJoinNonreturningExit':True,
        'wireFramingOrTypedChildCompositionProved':False,'runtimeExecutionObserved':False,
        'selection':'Valid disjoint reader/output/frame, normal ABI-preserving initialization/lifecycle/allocation/reader/setter calls, independently proved source return representations and matched concrete setters. Null allocation and trap/throw paths are excluded from normal completion.'}


def _offset(value,label):
    if type(value) is not int or not 16<=value<=127:raise ValueError(f'{label}.disp8-layout')
    return value


def prove_base_field_setter(rows,*,instance_offset,field_offset,mode,symbols,label='baseFieldSetter'):
    base=_offset(instance_offset,label);field=_offset(field_offset,label)
    g=ProgramGrammar(rows,label=label);j=Joins(label)
    g.take('sub rsp, 0x28');_exact(g,f'mov rax, [rcx+0x{base:x}]','488b41'+bytes((base,)).hex())
    g.take('test rax, rax');j.edge('nullThrow',_branch(g,'je'))
    store={'normalized-byte-return':(f'mov [rax+0x{field:x}], dl','8850'),
        'int32-return':(f'mov [rax+0x{field:x}], edx','8950')}.get(mode)
    if store is None:g.fail('base-setter-mode','byte or int32',mode)
    _exact(g,store[0],store[1]+bytes((field,)).hex());g.take('add rsp, 0x28','ret')
    j.mark('nullThrow',g);g.call(symbols['nullThrow']);g.take('int3');g.finish()
    return {'completeBaseSetterChecked':True,'localJoins':j.finish(),
        'baseInstanceOffset':base,'fieldOffset':field,'mode':mode,'conditionalParameterStoredToOwnedBaseField':True,
        'metadataFieldOwnershipProved':False,'runtimeExecutionObserved':False}


def preserved_argument(rows, argument):
    """One entry argument saved before control transfers and never overwritten."""
    from .body_claims import _REGISTER_ROOT, _writes_register
    def writes(row, register):
        affected=[]
        multiply=row.get('implicitUnsignedMultiplyOperation',{})
        affected.extend(multiply.get(k) for k in ('lowResultRegister','highResultRegister'))
        exchange=row.get('implicitMemoryExchangeOperation',{})
        affected.append(exchange.get('register'))
        locked=row.get('lockedMemoryExchangeOperation',{})
        affected.append(locked.get('sourceRegister') if locked.get('operation')=='xadd' else locked.get('accumulatorRegister'))
        head,_,operands=row['text'].partition(' ')
        if head not in ('cmp','test','bt','nop','push','call','jmp','prefetch'):
            affected.append(operands.split(',')[0])
        return _writes_register(row,register) or any(_REGISTER_ROOT.get(r,r)==register for r in affected if r)
    saved=[];incoming=True
    for i,row in enumerate(rows):
        if row['text'].startswith('db'):raise ValueError(f'argument-flow:undecoded={row["va"]}')
        match=re.fullmatch(r'mov (rbx|rbp|rsi|rdi|r1[2-5]), '+argument,row['text'])
        if incoming and match:saved.append((match[1],i))
        if writes(row,argument) or row['text'].startswith(('call ','j')):incoming=False
    saved=[register for register,i in saved if not any(writes(row,register) for row in rows[i+1:])]
    if len(saved)!=1:raise ValueError(f'argument-flow:{argument}:preserved-saves={saved}')
    return saved[0]


def _setter_metadata(image,wrappers,member):
    from .protocol import canonical_type_name
    from .reference_layouts import NativeReferenceContext
    label='setterField';md=image.metadata;pe=image.pe
    def need(ok,detail):
        if not ok:raise ValueError(f'{label}:{detail}:member={member.name}')
    context=NativeReferenceContext(image);wrapper=wrappers[member.declaring_wrapper]
    def field(owner,names):
        td=context.index.types[owner]
        found=[f for f in md.fields_for(td) if md.string(f.name_index) in names]
        need(len(found)==1,f'field:{owner}:{names}')
        name=owner+'::'+md.string(found[0].name_index)
        return name,context.field(name)
    target,(_,kind,offset)=field(wrapper.wrapped_type,{member.name,member.name.lstrip('_')})
    need(canonical_type_name(kind)==canonical_type_name(member.declared_type),'typed-ownership')
    method=md.methods[member.method_index]
    need(method.flags&0x10==0 and method.parameter_count==1 and image.type_name(method.declaring_type)==wrapper.name,'setter-abi')
    need(context.type_name(method.return_type)=='void' and canonical_type_name(context.type_name(
        list(md.parameters_for(method))[0].type_index))==canonical_type_name(member.declared_type),'setter-types')
    need(not context.is_value_type(wrapper.name) and all(pe.bytes_at_va(context.type_pointer(i),16)[11]&0x7f==0
        for i in (method.return_type,list(md.parameters_for(method))[0].type_index)),'ordinary-setter-types')
    return context,wrapper,field,target,offset,method


def reader_setup(rows,read):
    i=rows.index(read)
    if i<2:raise ValueError('reader-output-setup:missing')
    reader=preserved_argument(rows[:i],'rcx');output=preserved_argument(rows[:i],'rdx')
    setup={r['text'] for r in rows[i-2:i]}
    receiver=next((m[1] for text in setup if (m:=re.fullmatch(r'mov (rbx|rbp|rsi|rdi|r1[2-5]), \['+output+r'\]',text))),None)
    if receiver is None or len({reader,output,receiver})!=3 or setup!={f'mov {receiver}, [{output}]',f'mov rcx, {reader}'}:
        raise ValueError('reader-output-setup:receiver-or-argument-drift')
    return i,reader,output,receiver


def inlined_base_setter(image,bodies,wrappers,member,reader_rows,read,store):
    """Prove scalar substitution or a direct reference store before its barrier."""
    from scripts.game_data.memorypack.wrapper_members import INSTANCE_FIELD_NAMES
    label='inlinedBaseSetter';md=image.metadata;pe=image.pe;base=pe.image_base
    def need(ok,detail):
        if not ok:raise ValueError(f'{label}:{detail}:member={member.name}')
    context,wrapper,field,target,offset,method=_setter_metadata(image,wrappers,member)
    instance,(_,held,slot)=field(wrapper.name,INSTANCE_FIELD_NAMES)
    need(held==wrapper.wrapped_type,'typed-instance')
    reference=member.kind=='string'
    need(reference or member.kind=='bool' or member.kind in ('scalar32','enum') and member.width==4,'field-kind')
    pointer=image.method_pointer_va(method);end=bodies.extents[pointer]
    if not reference:
        need(not bodies.chained_fragments.get(pointer),'setter-fragments')
        rows=image.mapper.decode_x64_subset(pe.bytes_at_va(pointer,end-pointer),pointer,stop_offset=end-pointer)
        need(len(rows)==9 and rows[4]['text'].startswith('call ') and rows[5]['text']=='int3','setter-null-path')
        null=int(rows[4]['text'].split()[1],16)
        g=ProgramGrammar(rows,label=label)
        g.take('sub rsp, 0x28');_exact(g,f'mov rax, [rcx+0x{slot:x}]','488b41'+bytes((_offset(slot,label),)).hex())
        g.take('test rax, rax');g.branch('jne','store');g.call(null);g.take('int3');g.mark('store')
        _exact(g,f'mov [rax+0x{offset:x}], '+('dl' if member.kind=='bool' else 'edx'),
            ('8850' if member.kind=='bool' else '8950')+bytes((_offset(offset,label),)).hex())
        g.take('add rsp, 0x28','ret');g.finish()
    i,reader,output,receiver=reader_setup(reader_rows,read);j=reader_rows.index(store)
    g=ProgramGrammar(reader_rows[i+1:j+1],label=label+'.substitution')
    g.take(f'test {receiver}, {receiver}');first=g.branch('je')['target']
    destination='r8' if reference else 'rcx'
    g.take(f'mov {destination}, [{receiver}+0x{slot:x}]',f'test {destination}, {destination}');second=g.branch('je')['target']
    if reference:
        flag=g.row();raw=bytes.fromhex(flag['bytes'])
        need(raw[:2]==b'\x83\x3d' and len(raw)==7 and raw[-1]==0,'reference-barrier-flag-read')
    g.take(f'mov [{destination}+0x{offset:x}], '+('rax' if reference else 'al' if member.kind=='bool' else 'eax'));g.finish()
    trap=[r for r in reader_rows if int(r['va'],16)>=first][:2]
    need(first==second and len(trap)==2 and trap[0]['text'].startswith('call '),'caller-null-trap')
    g=ProgramGrammar(trap,label=label+'.null');g.call(int(trap[0]['text'].split()[1],16));g.take('int3');g.finish()
    import hashlib
    result={'memberIndex':None,'methodIndex':member.method_index,'declaringWrapper':wrapper.name,
        'setterName':md.string(method.name_index),'transfer':'directOwnedReferenceStore' if reference else 'inlinedBaseStore','normalPathOnly':True,
        'instanceField':instance,'targetField':target,'instanceOffset':slot,'fieldOffset':offset,
        'storeRva':int(store['va'],16)-base,'storeHex':store['bytes'].replace(' ','').upper()}
    if reference:result.update(evidenceBoundary='direct',setterMetadataOnly=True,writeBarrierEquivalenceProved=False)
    else:result['setterWindow']={'startRva':pointer-base,'endRva':end-base,'sha256':hashlib.sha256(pe.bytes_at_va(pointer,end-pointer)).hexdigest().upper()}
    return result


def prove_cached_field_setter(rows,*,field_offset,mode,symbols,label='cachedFieldSetter'):
    field=field_offset
    if type(field) is not int or not 16<=field<0x80000000:raise ValueError(f'{label}.field-layout')
    def encoded(prefix):
        raw=bytearray.fromhex(prefix);raw[-1]=(raw[-1]&0x3f)|(0x40 if field<128 else 0x80)
        return (raw+field.to_bytes(1 if field<128 else 4,'little',signed=True)).hex()
    g=ProgramGrammar(rows,label=label);j=Joins(label)
    if mode=='single-return':
        g.take('sub rsp, 0x38','movaps [rsp+0x20], xmm6','xor edx, edx','movaps xmm6, xmm1')
    else:
        g.take('push rbx','sub rsp, 0x20')
        if mode=='reference-return':g.take('mov rbx, rdx')
        elif mode=='int32-return':g.take('mov ebx, edx')
        elif mode=='normalized-byte-return':_exact(g,'movzx ebx, dl','0fb6da')
        else:g.fail('cached-setter-mode','reference, Int32, normalized byte or single',mode)
        g.take('xor edx, edx')
    getter=g.call(symbols['getter']);g.take('test rax, rax')
    inline_null=g.rows[g.cursor]['text'].startswith('jne ')
    if inline_null:
        j.edge('store',_branch(g,'jne'));g.call(symbols['nullThrow']);g.take('int3');j.mark('store',g)
    else:j.edge('nullThrow',_branch(g,'je'))
    if mode=='single-return':
        _exact(g,f'movss [rax+0x{field:x}], xmm6',encoded('f30f1170'))
        g.take('movaps xmm6, [rsp+0x20]','add rsp, 0x38','ret')
    elif mode=='normalized-byte-return':
        _exact(g,f'mov [rax+0x{field:x}], bl',encoded('8858'));g.take('add rsp, 0x20','pop rbx','ret')
    elif mode=='int32-return':
        _exact(g,f'mov [rax+0x{field:x}], ebx',encoded('8958'));g.take('add rsp, 0x20','pop rbx','ret')
    else:
        _exact(g,f'lea rcx, [rax+0x{field:x}]',encoded('488d48'))
        _exact(g,f'mov [rax+0x{field:x}], rbx',encoded('488958'))
        g.take('add rsp, 0x20','pop rbx');tail=_branch(g,'jmp')
        if tail['target']!=symbols['barrier']:g.fail('reference-store-barrier',symbols['barrier'],tail)
    if not inline_null:j.mark('nullThrow',g);g.call(symbols['nullThrow']);g.take('int3')
    g.finish()
    return {'completeCachedSetterChecked':True,'localJoins':j.finish(),'getterCall':getter,
        'fieldOffset':field,'mode':mode,'conditionalParameterStoredToGetterReturnedData':True,
        'metadataFieldOwnershipOrGetterResultProved':False,'runtimeExecutionObserved':False}


def instance_getter(image,wrappers,member):
    wrapper=wrappers[member.declaring_wrapper];md=image.metadata
    matches=[m for m in md.methods_for(md.types[wrapper.type_definition]) if md.string(m.name_index)=='get___instance']
    if len(matches)!=1:raise ValueError(f'instance-getter:method-count={len(matches)}:{wrapper.name}')
    return matches[0],image.method_pointer_va(matches[0])


def inlined_getter_setter(image,bodies,wrappers,member,rows,read,store):
    """Typed store behind the exact instance getter; outcomes stay conditional."""
    import hashlib
    from .body_claims import _REGISTER_ROOT
    context,wrapper,field,target,offset,method=_setter_metadata(image,wrappers,member)
    def need(ok,detail):
        if not ok:raise ValueError(f'getter-setter-substitution:{detail}:member={member.name}')
    reference=member.kind=='string' or member.declared_type.startswith(('Beyond.Gameplay.Actions.Param`1<','Beyond.Gameplay.Actions.ParamOutput`1<'))
    boolean=member.kind=='bool'
    need(reference or boolean or member.kind in ('scalar32','enum') and member.width==4,'field-kind')
    md=image.metadata;pe=image.pe;base=pe.image_base
    getter,entry=instance_getter(image,wrappers,member)
    need(getter.flags&0x10==0 and getter.parameter_count==0 and context.type_name(getter.return_type)==wrapper.wrapped_type
         and not pe.bytes_at_va(context.type_pointer(getter.return_type),16)[11]&0x7f,'ordinary-getter-abi')
    pointer=image.method_pointer_va(method);end=bodies.extents[pointer]
    if not reference:
        need(not bodies.chained_fragments.get(pointer),'setter-fragments')
        setter_rows=pe.bytes_at_va(pointer,end-pointer)
        program=image.mapper.decode_x64_subset(setter_rows,pointer,stop_offset=end-pointer)
        calls=[row for row in program if row['text'].startswith('call ')]
        need(len(program)==13 and len(calls)==2,'complete-setter-shape')
        prove_cached_field_setter(program,field_offset=offset,mode='normalized-byte-return' if boolean else 'int32-return',
            symbols={'getter':entry,'nullThrow':int(calls[1]['text'].split()[1],16)})
    i,reader,output,receiver=reader_setup(rows,read);j=rows.index(store)
    g=ProgramGrammar(rows[i+1:j+1],label='getterSetterCaller')
    pattern=r'mov (?:rbx|rbp|rsi|rdi|r1[2-5]), rax' if reference else r'movzx (?:ebx|ebp|esi|edi|r1[2-5]d), al' if boolean else r'mov (?:ebx|ebp|esi|edi|r1[2-5]d), eax'
    saved=g.pattern(pattern)['text'].split()[1].rstrip(',')
    need(_REGISTER_ROOT.get(saved,saved) not in (reader,output,receiver),'preserved-return-register')
    g.take(f'test {receiver}, {receiver}');first=g.branch('je')['target']
    g.take('xor edx, edx',f'mov rcx, {receiver}');g.call(entry)
    g.take('test rax, rax');second=g.branch('je')['target']
    if reference and bytes.fromhex(g.rows[g.cursor]['bytes'])[:2]==b'\x83\x3d':
        flag=g.row();raw=bytes.fromhex(flag['bytes']);need(len(raw)==7 and raw[-1]==0,'reference-barrier-flag-read')
    value=({'ebx':'bl','ebp':'bpl','esi':'sil','edi':'dil'}.get(saved,saved[:-1]+'b')) if boolean else saved
    g.take(f'mov [rax+0x{offset:x}], {value}');g.finish()
    trap=[r for r in rows if int(r['va'],16)>=first][:2]
    need(first==second and len(trap)==2 and trap[0]['text'].startswith('call '),'caller-null-trap')
    g=ProgramGrammar(trap,label='getterSetterNull');g.call(int(trap[0]['text'].split()[1],16));g.take('int3');g.finish()
    def window(start,end):
        return {'startRva':start-base,'endRva':end-base,'sha256':hashlib.sha256(pe.bytes_at_va(start,end-start)).hexdigest().upper()}
    result={'memberIndex':None,'methodIndex':member.method_index,'declaringWrapper':wrapper.name,
        'setterName':md.string(method.name_index),'transfer':'getterBackedStore','evidenceBoundary':'conditional','normalPathOnly':True,
        'targetField':target,'fieldOffset':offset,'storeRva':int(store['va'],16)-base,'storeHex':store['bytes'].replace(' ','').upper(),
        'getterMethod':[getter.index,wrapper.name,'get___instance',entry-base],
        'getterWindows':[window(entry,bodies.extents[entry]),*(window(at,at+size) for at,size in bodies.chained_fragments.get(entry,()))],
        'getterResultOwnershipProved':False,'exceptionPathEquivalenceProved':False}
    if reference:result.update(setterMetadataOnly=True,writeBarrierEquivalenceProved=False)
    else:result['setterWindow']=window(pointer,end)
    return result


def validate_reader_stores(image,bodies,wrappers,wrapper,route,*,label):
    """Recheck paired reads and declared call/inline transfers, returning their sites."""
    import struct
    from .type_data_initialization_instructions import decode_type_data_initialization_instructions
    base=image.pe.image_base;start=base+route['methods'][0][3];end=bodies.extents[start]
    for at,size in bodies.chained_fragments.get(start,()):
        if at!=end:break
        end+=size
    rows=decode_type_data_initialization_instructions(image.mapper,image.pe.bytes_at_va(start,end-start),start)
    by_rva={int(row['va'],16)-base:row for row in rows};names={w.name:w for w in wrappers.values()}
    def call(site,raw):
        actual=image.pe.bytes_at_va(base+site,5)
        if actual[0]!=0xe8 or actual.hex().upper()!=raw.upper():raise ValueError(f'{label}.native:call={site:#x}')
        return site+5+struct.unpack_from('<i',actual,1)[0]
    def inside(site,size):
        return any(w['startRva']<=site and site+size<=w['endRva'] for w in route['codeWindows'][:-1])
    sites=[];previous=route['memberCountInstruction']['rva']
    for read,member in zip(route['orderedReads'],wrapper.members,strict=True):
        i=read['memberIndex'];site=read['readCallRva'];proof=read.get('setterInlineProof')
        stop=proof['storeRva'] if proof else read['setterCallRva']
        if not previous<site<stop or not inside(site,5) or call(site,read['readCallHex'])!=read['readTargetRva']:
            raise ValueError(f'{label}.native:ordered-read={i}')
        if i in route['inlineSetterMembers']+route['getterSetterMembers']:
            prove=inlined_base_setter if i in route['inlineSetterMembers'] else inlined_getter_setter
            checked=prove(image,bodies,names,member,rows,by_rva[site],by_rva[stop]);checked['memberIndex']=i
            if checked!=proof or not inside(stop,len(bytes.fromhex(proof['storeHex']))):
                raise ValueError(f'{label}.native:inline-setter={i}')
        else:
            method=image.metadata.methods[member.method_index]
            if (proof or not inside(stop,5) or member.method_index!=read['setterMethodIndex']
                or member.declaring_wrapper!=read.get('declaringWrapper',member.declaring_wrapper)
                or image.metadata.string(method.name_index)!=f'set___{member.name}__'
                or call(stop,read['setterCallHex'])!=read['setterTargetRva']
                or image.method_pointer_va(method)!=base+read['setterTargetRva']):
                raise ValueError(f'{label}.native:setter={i}')
        sites.append(stop);previous=stop
    return sites


def prove_cached_instance_getter(primary,cold,*,instance_offset,cache_offset,symbols,label='cachedInstanceGetter'):
    base=_offset(instance_offset,label);cache=_offset(cache_offset,label)
    if base==cache:raise ValueError(f'{label}.distinct-instance-and-cache-slots')
    g=ProgramGrammar(primary,label=label);c=ProgramGrammar(cold,label=label+'.cold');j=Joins(label)
    g.take('push rbx','sub rsp, 0x20');flag=_flag(g);g.take('mov rbx, rcx');j.edge('init',_branch(g,'je'))
    j.mark('common',g);_exact(g,f'cmp [rbx+0x{cache:x}], 0x0','48837b'+bytes((cache,0)).hex())
    j.edge('refresh',_branch(g,'je'));_exact(g,f'mov rax, [rbx+0x{base:x}]','488b43'+bytes((base,)).hex())
    _exact(g,f'cmp [rbx+0x{cache:x}], rax','483943'+bytes((cache,)).hex());j.edge('refresh',_branch(g,'jne'))
    j.mark('return',g);_exact(g,f'mov rax, [rbx+0x{cache:x}]','488b43'+bytes((cache,)).hex())
    g.take('add rsp, 0x20','pop rbx','ret');j.mark('init',g);_init(g,1,flag,symbols)
    j.edge('common',_branch(g,'jmp'));g.finish()
    j.mark('refresh',c);first_context=_context(c);c.take('mov [rsp+0x30], rdi')
    _exact(c,f'mov rdi, [rbx+0x{base:x}]','488b7b'+bytes((base,)).hex());c.take('mov rcx, rdi');c.call(symbols['cast'])
    _exact(c,f'mov [rbx+0x{cache:x}], rax','488943'+bytes((cache,)).hex());c.take('mov rcx, rdi');second_context=_context(c)
    if first_context['usageCellVA']!=second_context['usageCellVA']:c.fail('same-cast-context-cell',first_context,second_context)
    c.call(symbols['cast']);_exact(c,f'lea rcx, [rbx+0x{cache:x}]','488d4b'+bytes((cache,)).hex())
    c.call(symbols['barrier']);c.take('mov rdi, [rsp+0x30]');j.edge('return',_branch(c,'jmp'));c.finish()
    return {'completeOriginalGetterAndRefreshEdgesChecked':True,'localJoins':j.finish(),
        'baseInstanceOffset':base,'cacheOffset':cache,'castContextLoad':first_context,
        'conditionalCoherentCacheReturnedToSetter':True,
        'castAndMetadataOwnershipProved':False,'runtimeExecutionObserved':False,
        'selection':'Normally returning noninterfering initialization/barrier and cast, stable compatible wrapper/base/cache, disjoint matched frame and Win64 nonvolatile preservation. Selected cache already equals base, or the independently proved typed cast result establishes it.'}
