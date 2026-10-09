"""Own anonymous word/predicate dispatch and ordinary argument/return paths."""
from __future__ import annotations
import hashlib
from typing import Any
from scripts.game_data.il2cpp.integer_widths import decode_width_aware_integer_instructions
from scripts.game_data.il2cpp.program_grammar import ProgramGrammar


def _owned(index, spec):
    pe=index.pe;base=pe.image_base;entry=base+spec['entryRva']
    actual=sorted(set([(entry,index.extents[entry])]+[(a,a+n) for a,n in index.chained_fragments.get(entry,[])]))
    expected=[(base+w['startRva'],base+w['endRva']) for w in spec['codeWindows']]
    if actual!=expected: raise ValueError(f'comparerDispatch.owned-fragments: expected={expected} actual={actual}')
    fragments=[]
    for w in spec['codeWindows']:
        start=base+w['startRva'];raw=pe.bytes_at_va(start,w['endRva']-w['startRva'])
        if hashlib.sha256(raw).hexdigest().upper()!=w['sha256'].upper(): raise ValueError('comparerDispatch.code-window')
        rows=decode_width_aware_integer_instructions(index.mapper,raw,start)
        if any('db ' in r['text'] for r in rows): raise ValueError('comparerDispatch.unknown-instruction')
        fragments.append(rows)
    return fragments


def _unsigned_branch(g, condition, label):
    row=g.row();raw=bytes.fromhex(row['bytes']);at=int(row['va'],16)
    opcode={'jae':0x73,'jb':0x72}[condition]
    if len(raw)!=2 or raw[0]!=opcode: g.fail('unsigned-predicate',condition,row)
    target=at+2+int.from_bytes(raw[1:],'little',signed=True)
    if row['text'] not in (f'{condition} 0x{target:x}',f'jcc 0x{target:x}'):
        g.fail('unsigned-branch-decoding',hex(target),row)
    g.edges.append((target,label,row))


def _scan(g,base,c,*,class_reg,receiver,context,selector,selector_word,word):
    layout=c['layout'];calls=c['calls']
    g.take(f'movzx r9d, word [{class_reg}+0x{layout["recordCount"]:x}]')
    if word: g.take('xor ebx, ebx','movzx eax, bx')
    else: g.take('xor eax, eax')
    row=g.take(f'cmp {"bx" if word else "ax"}, r9w')
    if row['wordComparisonOperation']['bits']!=16: g.fail('initial-count-width','word compare',row)
    _unsigned_branch(g,'jae','fallback')
    g.take(f'mov rdx, [{class_reg}+0x{layout["recordStorage"]:x}]');g.mark('scanLoop')
    g.take('movzx ecx, ax','add rcx, rcx',f'cmp [rdx+rcx*{layout["pointerBytes"]}], {context}')
    g.branch('je','foundRecord')
    row=g.take('inc ax')
    if not row['wordIncrementOperation']['preservesBitsAboveDestination']: g.fail('counter-upper-bits','preserved',row)
    g.take('cmp ax, r9w');_unsigned_branch(g,'jb','scanLoop')
    g.mark('fallback');g.take(f'movzx r8d, {selector_word}',f'mov rdx, {context}',f'mov rcx, {receiver}')
    g.call(base+calls['resolveSlot']);g.branch('jmp','selectedPair')
    g.mark('foundRecord');g.take('movzx edx, ax',f'mov rax, [{class_reg}+0x{layout["recordStorage"]:x}]',
        'add rdx, rdx',f'mov eax, [rax+0x{layout["recordOffsetWord"]:x}+rdx*{layout["pointerBytes"]}]',
        f'add eax, {selector}','cdqe',f'add rax, 0x{layout["pairArrayBiasUnits"]:x}',
        f'shl rax, 0x{layout["pairScaleShift"]:x}',f'add rax, {class_reg}')
    if (layout['pointerBytes'],layout['pairScaleShift'])!=(8,4):
        g.fail('pair-and-record-scale','two qwords per 16-byte record/pair',layout)
    g.mark('selectedPair')


def _special_address(g,base,target):
    row=g.row();op=row.get('addressOperation',{})
    if not op.get('ripRelative') or op.get('destination')!='rax' or op.get('absoluteAddress')!=base+target:
        g.fail('actual-specialization-address',target,row)


def validate_comparer_dispatch_control(index: Any, c: dict) -> dict:
    base=index.pe.image_base;layout=c['layout'];calls=c['calls'];special=c['specializations']
    word=_owned(index,c['programs']['keyWordProducer']);predicate=_owned(index,c['programs']['candidatePredicate'])
    if len(word)!=2 or len(predicate)!=1: raise ValueError('comparerDispatch.fragment-shape')
    g=ProgramGrammar(word[0],label='comparerDispatch.word')
    g.take('mov [rsp+0x8], rbx','mov [rsp+0x10], rbp','mov [rsp+0x18], rsi','push rdi',
           'push r14','push r15','sub rsp, 0x20','mov rbp, [r8]','mov rsi, r9','movzx r15d, cx',
           'mov r14, r8','mov rcx, rbp','mov rdi, rdx');g.call(base+calls['prepareClass'])
    _scan(g,base,c,class_reg='rbp',receiver='r14',context='rdi',selector='r15d',selector_word='r15w',word=True)
    g.take('mov r9, [rax]',f'mov r8, [rax+0x{layout["pointerBytes"]:x}]')
    _special_address(g,base,special['word'][0]);g.take('cmp r9, rax');g.branch('jne','secondWordSpecial')
    g.mark('nullableWord');g.take('test rsi, rsi');g.branch('je','wordEpilogue')
    g.mark('invokeObjectWord');g.take('mov ecx, 0x2','mov rdx, rsi');g.call(base+calls['objectWordInvoke'])
    g.mark('saveWord');g.take('mov ebx, eax');g.mark('wordEpilogue')
    g.take('mov rbp, [rsp+0x48]','mov eax, ebx','mov rbx, [rsp+0x40]','mov rsi, [rsp+0x50]',
           'add rsp, 0x20','pop r15','pop r14','pop rdi','ret')
    g.mark('secondWordSpecial');_special_address(g,base,special['word'][1]);g.take('cmp r9, rax')
    g.branch('jne','thirdWordSpecial');g.take('test rsi, rsi');g.branch('jne','invokeObjectWord')
    g.labels['nullWordError']=int(word[1][0]['va'],16);g.branch('jmp','nullWordError')
    g.mark('thirdWordSpecial');_special_address(g,base,special['word'][2]);g.take('cmp r9, rax')
    g.branch('je','nullableWord');g.take('mov rdx, rsi','mov rcx, r14','call r9')
    if bytes.fromhex(word[0][g.cursor-1]['bytes'])!=bytes.fromhex('41ffd1'):
        g.fail('word-indirect-call','complete CALL R9',word[0][g.cursor-1])
    g.branch('jmp','saveWord');g.finish()
    cold=ProgramGrammar(word[1],label='comparerDispatch.wordNullError')
    cold.take('xor edx, edx','xor ecx, ecx');cold.call(base+calls['throwNullWord']);cold.take('int3');cold.finish()

    g=ProgramGrammar(predicate[0],label='comparerDispatch.predicate')
    g.take('mov [rsp+0x8], rbx','mov [rsp+0x10], rbp','mov [rsp+0x18], rsi','mov [rsp+0x20], rdi',
           'push r14','sub rsp, 0x20','mov rsi, [r8]','mov rdi, r9','movzx ebp, cx',
           'mov r14, r8','mov rcx, rsi','mov rbx, rdx');g.call(base+calls['prepareClass'])
    _scan(g,base,c,class_reg='rsi',receiver='r14',context='rbx',selector='ebp',selector_word='bp',word=False)
    g.take('mov r10, [rax]',f'mov r9, [rax+0x{layout["pointerBytes"]:x}]')
    _special_address(g,base,special['predicate'][0]);g.take('cmp r10, rax');g.branch('jne','secondPredicateSpecial')
    g.take('test rdi, rdi');g.branch('je','nullLeft')
    g.take('mov r8, [rsp+0x50]','test r8, r8');g.branch('je','falseResult')
    g.take('xor ecx, ecx','mov rdx, rdi');g.call(base+calls['objectPredicateInvoke']);g.mark('predicateEpilogue')
    g.take('mov rbx, [rsp+0x30]','mov rbp, [rsp+0x38]','mov rsi, [rsp+0x40]','mov rdi, [rsp+0x48]',
           'add rsp, 0x20','pop r14','ret')
    g.mark('secondPredicateSpecial');_special_address(g,base,special['predicate'][1]);g.take('cmp r10, rax')
    g.branch('jne','thirdPredicateSpecial');g.take('mov rdx, [rsp+0x50]','cmp rdi, rdx')
    g.branch('je','trueResult');g.take('test rdi, rdi');g.branch('je','falseResult')
    g.take('test rdx, rdx');g.branch('je','falseResult')
    g.take(f'mov eax, [rdi+0x{layout["payloadLength"]:x}]',f'cmp eax, [rdx+0x{layout["payloadLength"]:x}]')
    g.branch('je','equalLengthPayload');g.mark('falseResult')
    row=g.take('xor al, al')
    if row['byteXorOperation']['zeroExtendsTo64']: g.fail('false-result-width','AL only',row)
    g.branch('jmp','predicateEpilogue');g.mark('thirdPredicateSpecial')
    _special_address(g,base,special['predicate'][2]);g.take('cmp r10, rax');g.branch('jne','virtualPredicate')
    g.take('cmp rdi, [rsp+0x50]');g.mark('pointerIdentityDecision');g.branch('jne','falseResult')
    g.mark('trueResult');g.take('mov al, 0x1');g.branch('jmp','predicateEpilogue')
    g.mark('equalLengthPayload')
    g.take(f'movsxd r8, [rdi+0x{layout["payloadLength"]:x}]',f'lea rcx, [rdi+0x{layout["payloadStart"]:x}]',
           'add r8, r8',f'add rdx, 0x{layout["payloadStart"]:x}','xor r9d, r9d')
    g.call(base+calls['payloadPredicate']);g.branch('jmp','predicateEpilogue')
    g.mark('virtualPredicate');g.take('mov r8, [rsp+0x50]','mov rdx, rdi','mov rcx, r14','call r10')
    if bytes.fromhex(predicate[0][g.cursor-1]['bytes'])!=bytes.fromhex('41ffd2'):
        g.fail('predicate-indirect-call','complete CALL R10',predicate[0][g.cursor-1])
    g.branch('jmp','predicateEpilogue');g.mark('nullLeft');g.take('cmp [rsp+0x50], 0x0')
    g.branch('jmp','pointerIdentityDecision');g.finish()
    return {'completeOwnedInstructionGrammarChecked':True,
        'checkedInstructions':sum(map(len,word))+sum(map(len,predicate)),
        'selectorTruncatedToUInt16Proved':True,'unsignedWordCountAndCounterProved':True,
        'recordScanAndActualPairAddressTransferProved':True,'functionAndMethodContextPairLoadedTogether':True,
        'fallbackReceiverContextAndSelectorForwarded':True,'ordinaryIndirectArgumentsAndReturnProved':True,
        'predicatePointerIdentitySpecializationReturnsALOnly':True,'nullAndPayloadSpecializationControlProved':True,
        'fullFramesAndNonvolatileRestorationProved':True,
        'matchingRecordPairAddressEquation':'class + (((int64)(int32)(recordOffsetWord + (uint16)selector) + pairArrayBiasUnits) << pairScaleShift), modulo 2^64',
        'recordCounterTermination':'zero to unsigned16 count; increment occurs only below count, so no low-word wrap precedes normal exhaustion',
        'conditions':['nonnull receiver and valid stable compatible class/context/record/pair/stack storage',
            'class preparation and fallback return normally with ABI-compatible preserved registers and pair result',
            'selected indirect and specialization helper calls have compatible normal-return ABI',
            'selected payload branch requires compatible lengths/buffers; opaque child behavior remains open'],
        'namedRuntimeInterfaceAndSlotMeaningProved':False,'wordHashAndPredicateEqualityMeaningProved':False,
        'actualRuntimeTargetSelected':False,'liveCacheContentsProved':False,
        'actualArrayCallbackTargetProved':False,'callbackCursorEqualityProved':False,
        'positiveListAdmitted':False,'wholeRootAdmitted':False}
