"""Complete selected string-source programs, without decoder/provider semantics.

Callers authenticate original body ownership, named methods, field offsets,
typed usage cells and literal values. These grammars check all local edges and
the buffered source/count/result transfers. They do not identify a live cached
encoding, prove its decoding behavior or admit stored strings independently.
"""
from __future__ import annotations
from .program_grammar import ProgramGrammar
from .zero_wrapper_programs import Joins, _branch, _exact


def _rip(g, prefix):
    row = g.row(); raw = bytes.fromhex(row['bytes'])
    if len(raw) != 7 or raw[:3] != bytes.fromhex(prefix): g.fail('rip-operand', prefix, row)
    return int(row['va'],16) + 7 + int.from_bytes(raw[3:],'little',signed=True)


def _offsets(fields, names, label):
    values = [fields[name] for name in names]
    if any(type(n) is not int or not 0 <= n < 128 for n in values) or len(set(values)) != len(values):
        raise ValueError(f'{label}.field-offsets: expected=distinct nonnegative disp8 actual={values}')
    return values


def prove_collection_header(primary, cold, fields, symbols, *, label='collectionHeader'):
    cur, rem, adv, used, total = _offsets(fields,('currentPtr','bufferLength','advancedCount','consumed','totalLength'),label)
    g = ProgramGrammar(primary,label=label); c = ProgramGrammar(cold,label=label+'.cold'); j = Joins(label)
    g.take('mov [rsp+0x8], rbx','mov [rsp+0x10], rsi','push rdi','sub rsp, 0x20')
    _exact(g,f'cmp dword [rcx+0x{rem:x}], 0x4','8379'+bytes((rem,4)).hex())
    g.take('mov rdi, rdx','mov rbx, rcx'); j.edge('refill',_branch(g,'jl')); j.mark('source',g)
    _exact(g,f'mov rax, [rbx+0x{cur:x}]','488b43'+bytes((cur,)).hex())
    _exact(g,'mov ecx, [rax]','8b08'); _exact(g,'mov [rdi], ecx','890f')
    _exact(g,f'mov esi, [rbx+0x{rem:x}]','8b73'+bytes((rem,)).hex()); g.take('add esi, -0x4')
    j.edge('advanceFallback',_branch(g,'js')); j.mark('advance',g)
    for slot,bits,prefix in ((cur,64,'488343'),(adv,32,'8343'),(used,32,'8343')):
        _exact(g,f'add {"qword" if bits==64 else "dword"} [rbx+0x{slot:x}], 0x4',prefix+bytes((slot,4)).hex())
    _exact(g,f'mov [rbx+0x{rem:x}], esi','8973'+bytes((rem,)).hex()); j.mark('remaining',g)
    _exact(g,f'movsxd rax, dword [rbx+0x{used:x}]','486343'+bytes((used,)).hex())
    _exact(g,f'mov rcx, [rbx+0x{total:x}]','488b4b'+bytes((total,)).hex())
    g.take('mov r8d, [rdi]','sub rcx, rax','movsxd rax, r8d','cmp rcx, rax'); j.edge('insufficient',_branch(g,'jl'))
    g.take('mov rbx, [rsp+0x30]'); _exact(g,'cmp r8d, -0x1','4183f8ff')
    g.take('mov rsi, [rsp+0x38]','setne al','add rsp, 0x20','pop rdi','ret'); g.finish()
    j.mark('refill',c); c.take('xor r8d, r8d','mov edx, 0x4'); c.call(symbols['getNextSpan']); c.take('nop'); j.edge('source',_branch(c,'jmp'))
    j.mark('advanceFallback',c); c.take('mov edx, 0x4','mov rcx, rbx'); c.call(symbols['advanceFallback'])
    c.take('test al, al'); j.edge('remaining',_branch(c,'jne')); j.edge('advance',_branch(c,'jmp'))
    j.mark('insufficient',c); c.take('xor edx, edx','mov ecx, r8d'); c.call(symbols['insufficient']); c.take('int3'); c.finish()
    return {'localJoins':j.finish(),'signedLengthBits':32,'nullSentinel':-1,'bufferedCursorDelta':4,
            'remainingBudgetCheckProved':True,'refillOrFallbackEffectsProved':False,
            'condition':'buffered normal path; valid stable disjoint source/output/reader/frame; pointer and signed counters do not overflow; sufficient total budget'}


def prove_string_reader(rows, symbols, empty_cell, *, label='stringReader'):
    g = ProgramGrammar(rows,label=label); j = Joins(label)
    g.take('push rbx','sub rsp, 0x20'); flag = g.row(); raw = bytes.fromhex(flag['bytes'])
    if len(raw)!=7 or raw[:2]!=b'\x80\x3d' or raw[-1]!=0: g.fail('byte-init-flag','CMP byte RIP zero',flag)
    flag_cell = int(flag['va'],16)+7+int.from_bytes(raw[2:6],'little',signed=True)
    g.take('mov rbx, rcx'); j.edge('header',_branch(g,'jne'))
    if _rip(g,'488d0d')!=empty_cell: g.fail('empty-literal-init',empty_cell,'other usage cell')
    g.call(symbols['metadataInit']); store = g.row(); raw = bytes.fromhex(store['bytes'])
    if (len(raw)!=7 or raw[:2]!=b'\xc6\x05' or raw[-1]!=1
            or int(store['va'],16)+7+int.from_bytes(raw[2:6],'little',signed=True)!=flag_cell):
        g.fail('same-byte-init-store',flag_cell,store)
    j.mark('header',g); g.take('lea rdx, [rsp+0x40]'); _exact(g,'mov dword [rsp+0x40], 0x0','c744244000000000')
    g.take('mov rcx, rbx'); g.call(symbols['header']); g.take('test al, al'); j.edge('null',_branch(g,'je'))
    g.take('mov edx, [rsp+0x40]','test edx, edx'); j.edge('empty',_branch(g,'je'))
    g.take('xor r8d, r8d','mov rcx, rbx','add rsp, 0x20','pop rbx'); tail = _branch(g,'jmp')
    if tail['target']!=symbols['readUtf8']: g.fail('utf8-tail-target',symbols['readUtf8'],tail)
    j.mark('empty',g)
    if _rip(g,'488b05')!=empty_cell: g.fail('same-empty-literal',empty_cell,'other usage cell')
    j.edge('return',_branch(g,'jmp')); j.mark('null',g); g.take('xor eax, eax'); j.mark('return',g)
    g.take('add rsp, 0x20','pop rbx','ret'); g.finish()
    return {'localJoins':j.finish(),'sameReaderAndSignedCountForwarded':True,'nullEmptyDistinct':True,
            'condition':'authenticated collection header; initialized empty literal; normal ABI-preserving initialization calls'}


def prove_utf8_reader(rows, fields, symbols, context_cell, *, label='utf8Reader'):
    cur, rem = _offsets(fields,('currentPtr','bufferLength'),label)
    g = ProgramGrammar(rows,label=label); j = Joins(label)
    g.take('mov [rsp+0x8], rbx','mov [rsp+0x10], rsi','push rdi','sub rsp, 0x30','mov edi, edx','mov rsi, rcx')
    _exact(g,f'cmp edx, dword [rcx+0x{rem:x}]','3b51'+bytes((rem,)).hex())
    row = g.row(); raw = bytes.fromhex(row['bytes']); at = int(row['va'],16)
    if len(raw)!=2 or raw[0]!=0x7e: g.fail('buffered-signed-le','JLE rel8',row)
    target = at+2+int.from_bytes(raw[1:],'little',signed=True)
    if row['text']!=f'jle 0x{target:x}': g.fail('jle-decoding',hex(target),row)
    j.edge('buffered',{**row,'target':target,'predicate':'jle'})
    g.take('xor r8d, r8d'); g.call(symbols['getNextSpan']); j.mark('buffered',g)
    if _rip(g,'4c8b0d')!=context_cell: g.fail('span-context',context_cell,'other usage cell')
    g.take('lea rcx, [rsp+0x20]'); _exact(g,f'mov rdx, [rsi+0x{cur:x}]','488b56'+bytes((cur,)).hex())
    g.take('mov r8d, edi'); g.call(symbols['createSpan']); g.take('xor ecx, ecx'); g.call(symbols['getUtf8'])
    g.take('test rax, rax'); j.edge('encoding',_branch(g,'jne')); g.call(symbols['nullThrow']); g.take('int3'); j.mark('encoding',g)
    g.take('movaps xmm0, [rsp+0x20]','lea rdx, [rsp+0x20]','xor r8d, r8d','movdqa [rsp+0x20], xmm0','mov rcx, rax')
    g.call(symbols['getString']); g.take('mov edx, edi','mov rcx, rsi','mov rbx, rax'); g.call(symbols['advance'])
    g.take('mov rsi, [rsp+0x48]','mov rax, rbx','mov rbx, [rsp+0x40]','add rsp, 0x30','pop rdi','ret'); g.finish()
    return {'localJoins':j.finish(),'samePointerCountSpanAndAdvance':True,'decodingResultPreserved':True,
            'encodingSemanticsProved':False,
            'condition':'nonnegative buffered byte count; authenticated typed span/context; normal ABI-preserving disjoint callees; selected encoding and decoder semantics proved independently'}


def prove_span_creation(rows, symbols, *, label='spanCreation'):
    g = ProgramGrammar(rows,label=label); j = Joins(label)
    g.take('mov [rsp+0x8], rbx','mov [rsp+0x10], rsi','push rdi','sub rsp, 0x20')
    _exact(g,'cmp qword [r9+0x38], 0x0','4983793800')
    g.take('mov edi, r8d','mov rsi, rdx','mov rbx, rcx'); j.edge('store',_branch(g,'jne'))
    g.take('mov rcx, r9'); g.call(symbols['classInit']); j.mark('store',g)
    _exact(g,'mov dword [rbx+0xc], 0x0','c7430c00000000'); g.take('mov rax, rbx')
    _exact(g,'mov [rbx], rsi','488933'); g.take('mov rsi, [rsp+0x38]'); _exact(g,'mov [rbx+0x8], edi','897b08')
    g.take('mov rbx, [rsp+0x30]','add rsp, 0x20','pop rdi','ret'); g.finish()
    return {'localJoins':j.finish(),'pointerOffset':0,'countOffset':8,'clearedPaddingOffset':12,
            'condition':'typed ReadOnlySpan<byte> context proved independently; valid disjoint 16-byte output; normal ABI-preserving class initialization'}


def prove_reader_advance(primary, cold, fields, symbols, *, label='readerAdvance'):
    cur, rem, adv, used = _offsets(fields,('currentPtr','bufferLength','advancedCount','consumed'),label)
    g = ProgramGrammar(primary,label=label); c = ProgramGrammar(cold,label=label+'.cold'); j = Joins(label)
    g.take('test edx, edx'); j.edge('return',_branch(g,'je'))
    g.take('mov [rsp+0x10], rbx','push rdi','sub rsp, 0x20','movsxd rdi, edx','mov rbx, rcx','mov [rsp+0x30], rsi')
    _exact(g,f'mov esi, [rcx+0x{rem:x}]','8b71'+bytes((rem,)).hex()); g.take('sub esi, edi')
    j.edge('fallback',_branch(g,'js')); j.mark('advance',g)
    for slot,bits,reg,prefix in ((cur,64,'rdi','48017b'),(adv,32,'edi','017b'),(used,32,'edi','017b')):
        _exact(g,f'add {"qword" if bits==64 else "dword"} [rbx+0x{slot:x}], {reg}',prefix+bytes((slot,)).hex())
    _exact(g,f'mov [rbx+0x{rem:x}], esi','8973'+bytes((rem,)).hex()); j.mark('epilogue',g)
    g.take('mov rsi, [rsp+0x30]','mov rbx, [rsp+0x38]','add rsp, 0x20','pop rdi'); j.mark('return',g); g.take('ret'); g.finish()
    j.mark('fallback',c); c.take('mov edx, edi'); c.call(symbols['advanceFallback']); c.take('test al, al')
    j.edge('epilogue',_branch(c,'jne')); j.edge('advance',_branch(c,'jmp')); c.finish()
    return {'localJoins':j.finish(),'zeroCountPreservesReader':True,'bufferedDeltaEqualsSignedCount':True,
            'refillFallbackEffectsProved':False,
            'condition':'nonnegative buffered count; valid reader/frame; pointer and signed counter arithmetic do not overflow'}


def prove_span_get_string(rows, symbols, *, label='spanGetString'):
    g = ProgramGrammar(rows,label=label); j = Joins(label)
    g.take('mov [rsp+0x8], rbx','push rdi','sub rsp, 0x30','movups xmm0, [rdx]','mov rdi, rcx','mov rbx, rdx')
    context = _rip(g,'488b0d'); g.take('movaps [rsp+0x20], xmm0')
    _exact(g,'cmp qword [rcx+0x38], 0x0','4883793800'); j.edge('init',_branch(g,'je')); j.mark('common',g)
    g.take('psrldq xmm0, 0x8','movq rax, xmm0','test eax, eax'); j.edge('empty',_branch(g,'je'))
    g.take('movups xmm0, [rbx]','movups [rsp+0x20], xmm0','mov rdx, [rsp+0x20]'); j.mark('count',g)
    g.take('mov r8d, [rbx+0x8]','xor r9d, r9d','mov rcx, rdi','mov rbx, [rsp+0x40]','add rsp, 0x30','pop rdi')
    tail = _branch(g,'jmp')
    if tail['target']!=symbols['pointerGetString']: g.fail('pointer-overload-tail',symbols['pointerGetString'],tail)
    j.mark('empty',g); g.take('mov edx, 0x1'); j.edge('count',_branch(g,'jmp'))
    j.mark('init',g); g.call(symbols['classInit']); g.take('movaps xmm0, [rsp+0x20]'); j.edge('common',_branch(g,'jmp')); g.finish()
    return {'localJoins':j.finish(),'initializationContextCell':context,'positivePointerAndCountForwarded':True,
            'sameEncodingReceiverForwarded':True,'condition':'positive stable span; normal ABI-preserving class initialization; pointer overload decoding semantics proved independently'}


def _encoding_fields(fields, label):
    readonly, page, emit, throws = _offsets(fields,('readOnly','codePage','emitIdentifier','throwInvalid'),label)
    if throws!=emit+1: raise ValueError(f'{label}.adjacent-boolean-fields: expected={emit+1} actual={throws}')
    if len({readonly,*range(page,page+4),emit,throws})!=7: raise ValueError(f'{label}.overlapping-instance-fields')
    return readonly,page,emit,throws


def prove_utf8_constructor(rows, fields, symbols, *, label='utf8Constructor'):
    readonly,page,emit,throws = _encoding_fields(fields,label)
    g = ProgramGrammar(rows,label=label); j = Joins(label)
    g.take('mov [rsp+0x8], rbx','mov [rsp+0x10], rsi','push rdi','sub rsp, 0x20','movzx esi, r8b')
    _exact(g,f'mov byte [rcx+0x{readonly:x}], 0x1','c641'+bytes((readonly,1)).hex())
    g.take('movzx edi, dl','mov rbx, rcx')
    _exact(g,f'mov dword [rcx+0x{page:x}], 0xfde9','c741'+bytes((page,)).hex()+'e9fd0000')
    g.take('mov rdx, rbx','mov ecx, 0x5'); g.call(symbols['initializeEncoding'])
    _exact(g,f'mov [rbx+0x{emit:x}], dil','40887b'+bytes((emit,)).hex())
    _exact(g,f'mov [rbx+0x{throws:x}], sil','408873'+bytes((throws,)).hex())
    g.take('test sil, sil'); j.edge('throwingFallback',_branch(g,'jne')); j.mark('return',g)
    g.take('mov rbx, [rsp+0x30]','mov rsi, [rsp+0x38]','add rsp, 0x20','pop rdi','ret')
    j.mark('throwingFallback',g); g.take('mov ecx, 0x5','mov rdx, rbx'); g.call(symbols['initializeEncoding'])
    j.edge('return',_branch(g,'jmp')); g.finish()
    return {'localJoins':j.finish(),'codePage':65001,'readOnly':True,
            'emitIdentifierFromSecondArgumentByte':True,'throwInvalidFromThirdArgumentByte':True,
            'falseThrowArgumentSkipsSecondInitialization':True,
            'condition':'ordinary named UTF8Encoding(bool,bool) ABI and typed fields authenticated; normal initializer preserves saved arguments, object and disjoint frame; constructor called on valid zero-initialized allocation',
            'initializerEffectsProved':False}


def prove_utf8_cache(rows, fields, symbols, encoding_cell, allocation_cell, *, label='utf8Cache'):
    readonly,page,emit,throws = _encoding_fields(fields,label)
    slot, = _offsets(fields,('utf8Cache',),label)
    g = ProgramGrammar(rows,label=label); j = Joins(label)
    def cache_area():
        if _rip(g,'488b05')!=encoding_cell: g.fail('same-encoding-type-cell',encoding_cell,'different cell')
        _exact(g,'mov rcx, [rax+0xb8]','488b88b8000000')
    def read_cache(): _exact(g,f'mov rax, [rcx+0x{slot:x}]','488b41'+bytes((slot,)).hex())
    def fence(): _exact(g,'lock or dword [rsp], 0x0','f0830c2400')
    g.take('push rbx','sub rsp, 0x20'); cache_area(); read_cache(); fence()
    g.take('test rax, rax'); j.edge('allocate',_branch(g,'je')); j.mark('cachedReturn',g)
    cache_area(); read_cache(); fence(); g.take('add rsp, 0x20','pop rbx','ret'); j.mark('allocate',g)
    if _rip(g,'488b0d')!=allocation_cell: g.fail('typed-utf8-allocation-cell',allocation_cell,'different cell')
    g.call(symbols['allocate']); g.take('mov rbx, rax','test rax, rax'); j.edge('initialize',_branch(g,'jne'))
    g.call(symbols['nullThrow']); g.take('int3'); j.mark('initialize',g)
    _exact(g,f'mov byte [rax+0x{readonly:x}], 0x1','c640'+bytes((readonly,1)).hex()); g.take('mov ecx, 0x5')
    _exact(g,f'mov dword [rax+0x{page:x}], 0xfde9','c740'+bytes((page,)).hex()+'e9fd0000')
    g.take('mov rdx, rbx'); g.call(symbols['initializeEncoding'])
    _exact(g,f'mov word [rbx+0x{emit:x}], 0x1','66c743'+bytes((emit,)).hex()+'0100'); fence(); cache_area()
    _exact(g,f'mov [rcx+0x{slot:x}], rbx','488959'+bytes((slot,)).hex()); cache_area()
    _exact(g,f'add rcx, 0x{slot:x}','4883c1'+bytes((slot,)).hex()); g.call(symbols['barrier'])
    j.edge('cachedReturn',_branch(g,'jmp')); g.finish()
    return {'localJoins':j.finish(),'codePage':65001,'readOnly':True,'emitIdentifier':True,'throwInvalid':False,
            'sameTypedCacheSlotLoadedStoredAndReturned':True,'constructorArgumentEquivalent':[True,False],
            'condition':'authenticated Encoding static cache and UTF8Encoding allocation cells; cache is initially null or holds the corresponding initialized UTF8 encoding; valid zeroed allocation; normal ABI-preserving disjoint allocator/initializer/barrier; no interfering cache or object mutation',
            'liveCacheIdentityOrAllocatorInitializerBarrierEffectsProved':False,'unicodeDecodingAlgorithmProved':False}


def prove_pointer_get_string(primary, cold, layout, symbols, empty_cell, *, label='pointerGetString'):
    """Full pointer overload: count, allocate, fill and unchanged String return.

    Virtual slot/type resolution and each decoder's character semantics remain
    independent. Error paths are checked through their original terminal traps.
    """
    g=ProgramGrammar(primary,label=label); c=ProgramGrammar(cold,label=label+'.cold'); j=Joins(label)
    def invoke(slot,context_slot):
        _exact(g,f'mov r10, [rax+0x{slot:x}]','4c8b90'+slot.to_bytes(4,'little').hex())
        _exact(g,f'mov rax, [rax+0x{context_slot:x}]','488b80'+context_slot.to_bytes(4,'little').hex())
    for slot in ('countFunction','fillFunction'):
        if type(layout[slot]) is not int or not 0<=layout[slot]<1<<31:raise ValueError(f'{label}.virtual-slot-range')
    first,=_offsets(layout,('firstChar',),label)
    g.take('mov [rsp+0x8], rbx','mov [rsp+0x10], rbp','mov [rsp+0x18], rsi','mov [rsp+0x20], rdi',
           'push r14','sub rsp, 0x40','mov esi, r8d','mov rbp, rdx','mov rbx, rcx','test rdx, rdx')
    j.edge('nullPointer',_branch(g,'je')); g.take('test r8d, r8d'); j.edge('negativeCount',_branch(g,'js'))
    g.take('test rcx, rcx'); j.edge('nullThrow',_branch(g,'je')); g.take('mov rcx, [rcx]'); g.call(symbols['prepareClass'])
    g.take('mov rax, [rbx]','xor r9d, r9d','mov r8d, esi','mov rdx, rbp','mov rcx, rbx')
    invoke(layout['countFunction'],layout['countFunction']+8)
    g.take('mov [rsp+0x20], rax'); _exact(g,'call r10','41ffd2')
    g.take('mov r14d, eax','test eax, eax'); j.edge('empty',_branch(g,'je'))
    g.take('mov ecx, eax'); g.call(symbols['allocateString']); g.take('mov rdi, rax','test rax, rax')
    j.edge('nullThrow',_branch(g,'je')); g.take('mov rcx, [rbx]'); g.call(symbols['prepareClass']); g.take('mov rax, [rbx]')
    _exact(g,f'lea r9, [rdi+0x{first:x}]','4c8d4f'+bytes((first,)).hex())
    g.take('mov r8d, esi','mov rdx, rbp','mov rcx, rbx'); invoke(layout['fillFunction'],layout['fillFunction']+8)
    g.take('mov [rsp+0x30], rax'); _exact(g,'mov qword [rsp+0x28], 0x0','48c744242800000000')
    g.take('mov [rsp+0x20], r14d'); _exact(g,'call r10','41ffd2'); j.mark('return',g)
    g.take('mov rbx, [rsp+0x50]','mov rax, rdi','mov rdi, [rsp+0x68]','mov rbp, [rsp+0x58]',
           'mov rsi, [rsp+0x60]','add rsp, 0x40','pop r14','ret'); j.mark('empty',g)
    if _rip(g,'488b05')!=empty_cell:g.fail('empty-string-type-cell',empty_cell,'different cell')
    _exact(g,'mov rcx, [rax+0xb8]','488b88b8000000'); _exact(g,'mov rdi, [rcx]','488b39'); j.edge('return',_branch(g,'jmp'))
    j.mark('nullThrow',g); g.call(symbols['nullThrow']); g.take('int3'); g.finish()
    for role,constructor in (('negativeCount','rangeConstructor'),('nullPointer','nullConstructor')):
        j.mark(role,c); _rip(c,'488d0d'); c.call(symbols['metadataInit']); _rip(c,'488d0d')
        c.take('mov rdi, rax'); c.call(symbols['metadataInit']); c.take('mov rcx, rax'); c.call(symbols['allocateException'])
        c.take('mov rbx, rax','test rax, rax'); j.edge('nullThrow',_branch(c,'je'))
        _rip(c,'488d0d'); c.call(symbols['metadataInit']); c.take('xor r9d, r9d','mov r8, rdi','mov rdx, rax','mov rcx, rbx')
        c.call(symbols[constructor]); _rip(c,'488d0d'); c.call(symbols['metadataInit'])
        c.take('mov rdx, rax','mov rcx, rbx'); c.call(symbols['throwException']); c.take('int3')
    c.finish()
    return {'localJoins':j.finish(),'sameBytePointerCountAndEncodingToBothVirtualCalls':True,
            'bothDecoderStateArgumentsNull':True,'countReturnBecomesAllocationAndCharacterCapacity':True,
            'allocatedStringPreservedAcrossFillAndReturned':True,'fillReturnDoesNotReplaceString':True,
            'virtualCalleeResolutionProved':False,'decoderCharacterSemanticsProved':False,
            'condition':'valid stable nonnull encoding/byte source and nonnegative count; normal prepare/allocator/decoder callees preserve ABI and disjoint frames; allocation yields a valid String of the requested character capacity; virtual methods and decoder character semantics proved independently'}


def prove_virtual_slot_prefix(rows, symbols, *, label='encodingVirtualSlotPrefix'):
    """Selected generic dispatch prefix; optimized targets are excluded explicitly."""
    g=ProgramGrammar(rows,label=label)
    g.take('mov [rsp+0x8], rbx','mov [rsp+0x10], rsi','push rdi','sub rsp, 0x40',
           'movzx ebx, cx','mov rdi, rdx','mov rcx, [rdx]','movaps [rsp+0x30], xmm6')
    g.call(symbols['prepareClass']); g.take('mov rax, [rdi]')
    row=g.row();raw=bytes.fromhex(row['bytes'])
    if len(raw)!=4 or raw[:3]!=b'\x48\x8d\x4b' or raw[3]>=128:g.fail('slot-address-base','positive disp8 LEA RCX from RBX',row)
    base=raw[3]
    if row['text']!=f'lea rcx, [rbx+0x{base:x}]':g.fail('slot-address-decoding',base,row)
    _exact(g,'add rcx, rcx','4803c9'); _exact(g,'mov r8, [rax+rcx*8]','4c8b04c8')
    _exact(g,'mov rdx, [rax+rcx*8+0x8]','488b54c808'); excluded=[]
    for _ in range(3):
        target=_rip(g,'488d05'); g.take('cmp r8, rax'); edge=_branch(g,'je')
        if target==symbols['selectedMethod']:g.fail('generic-path-selection','selected method differs from each optimized target',target)
        excluded.append({'functionVA':target,'branchVA':edge['target']})
    g.take('mov rcx, rdi'); _exact(g,'call r8','41ffd0'); continuation=_branch(g,'jmp'); g.finish()
    return {'vtableOffset':base*16,'entryBytes':16,'methodInfoOffset':8,'slotInputBits':16,
            'genericCallReceivesSameReceiver':True,'excludedOptimizedTargets':excluded,'continuationVA':continuation['target'],
            'condition':'actual receiver class function at the requested slot equals the authenticated selected method, hence none of the optimized targets; normal class preparation and call ABI; complete helper effects and other paths unproved'}
