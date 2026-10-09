"""Complete caller and setter flow for a cached reference wrapper profile.

The caller authenticates physical ownership, metadata types and every callee.
These grammars prove original local control flow and return-register transfers;
callee wire framing, closed child contexts and actual execution need independent
proof. Symbols and layout declarations are supplied by a reviewed contract.
"""
from __future__ import annotations
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


def prove_cached_field_setter(rows,*,field_offset,mode,symbols,label='cachedFieldSetter'):
    field=_offset(field_offset,label);g=ProgramGrammar(rows,label=label);j=Joins(label)
    if mode=='single-return':
        g.take('sub rsp, 0x38','movaps [rsp+0x20], xmm6','xor edx, edx','movaps xmm6, xmm1')
    else:
        g.take('push rbx','sub rsp, 0x20')
        if mode=='reference-return':g.take('mov rbx, rdx')
        elif mode=='normalized-byte-return':_exact(g,'movzx ebx, dl','0fb6da')
        else:g.fail('cached-setter-mode','reference, normalized byte or single',mode)
        g.take('xor edx, edx')
    getter=g.call(symbols['getter']);g.take('test rax, rax');j.edge('nullThrow',_branch(g,'je'))
    if mode=='single-return':
        _exact(g,f'movss [rax+0x{field:x}], xmm6','f30f1170'+bytes((field,)).hex())
        g.take('movaps xmm6, [rsp+0x20]','add rsp, 0x38','ret')
    elif mode=='normalized-byte-return':
        _exact(g,f'mov [rax+0x{field:x}], bl','8858'+bytes((field,)).hex());g.take('add rsp, 0x20','pop rbx','ret')
    else:
        _exact(g,f'lea rcx, [rax+0x{field:x}]','488d48'+bytes((field,)).hex())
        _exact(g,f'mov [rax+0x{field:x}], rbx','488958'+bytes((field,)).hex())
        g.take('add rsp, 0x20','pop rbx');tail=_branch(g,'jmp')
        if tail['target']!=symbols['barrier']:g.fail('reference-store-barrier',symbols['barrier'],tail)
    j.mark('nullThrow',g);g.call(symbols['nullThrow']);g.take('int3');g.finish()
    return {'completeCachedSetterChecked':True,'localJoins':j.finish(),'getterCall':getter,
        'fieldOffset':field,'mode':mode,'conditionalParameterStoredToGetterReturnedData':True,
        'metadataFieldOwnershipOrGetterResultProved':False,'runtimeExecutionObserved':False}


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
