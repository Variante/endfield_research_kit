"""Complete selected WORD record scan and indirect normal tail transfer.

Record/class/interface/method names require separate source joins. This lane
proves physical arguments, bounded local scanning, modular address arithmetic
and normal frame restoration, while child effects/live target identity stay open.
"""
from collections import deque
import hashlib
from scripts.game_data.il2cpp.memory_moves import decode_memory_move
from scripts.game_data.il2cpp.owned_partition import BranchGrammar
from scripts.game_data.il2cpp.relation_control import transfer

LABEL='contextFallbackControl'
TAIL_BYTES=b'\x49\xff\xe0'

def _take(g,text,raw):
    row=g.take(text)
    if bytes.fromhex(row['bytes'])!=raw:g.fail('instruction-encoding',raw.hex(),row)
    return row

def _move(g,direction,register,bits,receiver,*,offset=None,index=None,scale=1):
    row=g.row();raw=bytes.fromhex(row['bytes']);decoded=decode_memory_move(raw,0,int(row['va'],16))
    if decoded is None or decoded[1]!=len(raw):g.fail('complete-memory-move',(direction,register,bits),row)
    fact=decoded[0]['memoryOperation'];address=fact['address']
    expected=(direction,register,bits,bits//8,receiver,index,scale,False,64)
    actual=(fact['direction'],fact['register'],fact['registerBits'],fact['memoryBytes'],
            address['base'],address['index'],address['scale'],address['ripRelative'],address['addressBits'])
    if actual!=expected or row['text']!=decoded[0]['text']:g.fail('physical-memory-move',expected,row)
    if offset is not None and address['displacement']!=offset:g.fail('memory-displacement',offset,address)
    return address['displacement'],int(row['va'],16)

def _global(g):
    row=g.row();raw=bytes.fromhex(row['bytes']);decoded=decode_memory_move(raw,0,int(row['va'],16))
    if decoded is None or decoded[1]!=len(raw):g.fail('complete-global-load','QWORD RIP load',row)
    fact=decoded[0]['memoryOperation'];address=fact['address']
    if (fact['direction'],fact['register'],fact['registerBits'],fact['memoryBytes'],address['ripRelative'])!=('load','rsi',64,8,True) or row['text']!=decoded[0]['text']:
        g.fail('captured-comparison-pointer','RIP-relative QWORD to RSI',row)
    return address['absoluteAddress'],int(row['va'],16)

def _word_limit(g):
    row=g.row();raw=bytes.fromhex(row['bytes'])
    if len(raw)!=8 or raw[:4]!=b'\x44\x0f\xb7\x83':g.fail('unsigned-word-limit','MOVZX R8D, word [RBX+disp32]',row)
    offset=int.from_bytes(raw[4:],'little',signed=True)
    text=f'movzx r8d, word [rbx{("+" if offset>=0 else "-")+hex(abs(offset))}]'
    if row['text']!=text:g.fail('unsigned-word-limit-decoding',text,row)
    return offset,int(row['va'],16)

def _call(g,start,end):
    row=g.rows[g.cursor];fact=transfer(row)
    if fact['kind']!='call' or start<=fact['target']<end:g.fail('external-direct-call','E8 target outside owned body',row)
    g.call(fact['target']);return int(row['va'],16),fact['target']

def _transfer(row):
    return {'kind':'indirectTail'} if bytes.fromhex(row['bytes'])==TAIL_BYTES else transfer(row)

def _cfg_and_frames(rows,entry):
    by_at={int(row['va'],16):row for row in rows};edges={}
    if len(by_at)!=len(rows):raise ValueError(LABEL+'.duplicate-instruction')
    for at,row in by_at.items():
        fact=_transfer(row);kind=fact['kind'];targets=[]
        if kind in ('jump','conditional'):targets.append(fact['target'])
        if kind in ('next','conditional','call'):targets.append(at+len(bytes.fromhex(row['bytes'])))
        if kind not in ('next','conditional','jump','call','indirectTail') or any(target not in by_at for target in targets):
            raise ValueError(LABEL+'.unreviewed-transfer-or-local-boundary: '+str(row)[:384])
        edges[at]=set(targets)
    incoming={entry:0};pending=deque([entry]);tails=[]
    while pending:
        at=pending.popleft();row=by_at[at];delta=incoming[at];head,_,rest=row['text'].partition(' ')
        if head in ('push','pop'):delta += -8 if head=='push' else 8
        elif rest.startswith('rsp, '):
            if head not in ('add','sub') or not rest.startswith('rsp, 0x'):raise ValueError(LABEL+'.dynamic-stack')
            amount=int(rest.split(', ')[1],16);delta+=amount if head=='add' else -amount
        kind=_transfer(row)['kind']
        if kind=='call' and ((8+delta)%16 or -delta<32):raise ValueError(LABEL+'.call-frame')
        if kind=='indirectTail':
            if delta!=0:raise ValueError(LABEL+'.tail-frame-not-restored')
            tails.append(at)
        for target in edges[at]:
            if target in incoming and incoming[target]!=delta:raise ValueError(LABEL+'.normal-frame-join')
            if target not in incoming:incoming[target]=delta;pending.append(target)
    if set(incoming)!=set(by_at) or len(tails)!=1:raise ValueError(LABEL+'.owned-reachability-or-tail-count')
    return edges,tails[0]

def prove_context_fallback_control(rows,windows,base,entry_rva):
    if len(windows)!=1 or windows[0]['startRva']!=entry_rva:raise ValueError(LABEL+'.single-complete-owned-window')
    window=windows[0];raw=bytes.fromhex(window['rawHex']);start=base+entry_rva;end=base+window['endRva']
    if end-start!=len(raw) or hashlib.sha256(raw).hexdigest().upper()!=window['sha256'].upper():
        raise ValueError(LABEL+'.owned-window-bytes-or-hash')
    if not rows or int(rows[0]['va'],16)!=start or b''.join(bytes.fromhex(row['bytes']) for row in rows)!=raw:
        raise ValueError(LABEL+'.owned-instruction-partition')
    g=BranchGrammar(rows,label=LABEL)
    home_rbx,_=_move(g,'store','rbx',64,'rsp');home_rsi,_=_move(g,'store','rsi',64,'rsp')
    if min(home_rbx,home_rsi)<8 or max(home_rbx,home_rsi)>32 or abs(home_rbx-home_rsi)<8:
        g.fail('saved-homes','separate caller shadow-space QWORD homes', (home_rbx,home_rsi))
    _take(g,'push rdi',b'\x57');row=g.row();packet=bytes.fromhex(row['bytes'])
    if len(packet)!=4 or packet[:3]!=b'\x48\x83\xec' or not 32<=packet[3]<0x80:
        g.fail('frame-allocation','SUB RSP positive imm8',row)
    frame=packet[3]
    if frame%16 or row['text']!=f'sub rsp, 0x{frame:x}':g.fail('frame-alignment','push plus aligned shadow frame',row)
    _,receiver_load=_move(g,'load','rbx',64,'r8',offset=0)
    _take(g,'mov rdi, r8',b'\x49\x8b\xf8')
    comparison_cell,comparison_load=_global(g)
    _take(g,'mov rcx, rbx',b'\x48\x8b\xcb');prepare_call,prepare_target=_call(g,start,end)
    count_offset,count_load=_word_limit(g)
    _take(g,'xor ecx, ecx',b'\x33\xc9');_take(g,'cmp cx, r8w',b'\x66\x41\x3b\xc8');g.branch('jae','miss')
    array_offset,array_load=_move(g,'load','rdx',64,'rbx')
    g.mark('scan');_take(g,'movzx eax, cx',b'\x0f\xb7\xc1');_take(g,'add rax, rax',b'\x48\x03\xc0')
    match=_take(g,'cmp qword [rdx+rax*8], rsi',b'\x48\x39\x34\xc2');g.branch('je','hit')
    _take(g,'inc cx',b'\x66\xff\xc1');_take(g,'cmp cx, r8w',b'\x66\x41\x3b\xc8');g.branch('jb','scan')
    g.mark('miss');row=g.row();packet=bytes.fromhex(row['bytes'])
    if len(packet)!=6 or packet[:2]!=b'\x41\xb8':g.fail('resolver-slot','MOV R8D imm32',row)
    slot=int.from_bytes(packet[2:],'little')
    if slot>=0x80 or row['text']!=f'mov r8d, 0x{slot:x}':g.fail('shared-slot-declaration','matching positive imm8-compatible DWORD slot',row)
    _take(g,'mov rdx, rsi',b'\x48\x8b\xd6');_take(g,'mov rcx, rdi',b'\x48\x8b\xcf')
    resolver_call,resolver_target=_call(g,start,end)
    g.mark('dispatch');_,method_load=_move(g,'load','r8',64,'rax',offset=0)
    _take(g,'mov rcx, rdi',b'\x48\x8b\xcf');_,metadata_load=_move(g,'load','rdx',64,'rax',offset=8)
    _move(g,'load','rbx',64,'rsp',offset=frame+8+home_rbx)
    _move(g,'load','rsi',64,'rsp',offset=frame+8+home_rsi)
    _take(g,f'add rsp, 0x{frame:x}',b'\x48\x83\xc4'+bytes((frame,)))
    _take(g,'pop rdi',b'\x5f');tail=_take(g,'jmp r8',TAIL_BYTES)
    g.mark('hit');_take(g,'movzx ecx, cx',b'\x0f\xb7\xc9');_take(g,'add rcx, rcx',b'\x48\x03\xc9')
    _,offset_load=_move(g,'load','eax',32,'rdx',offset=8,index='rcx',scale=8)
    _take(g,f'add eax, 0x{slot:x}',b'\x83\xc0'+bytes((slot,)));_take(g,'cdqe',b'\x48\x98')
    row=g.row();packet=bytes.fromhex(row['bytes'])
    if len(packet)!=4 or packet[:3]!=b'\x48\x83\xc0' or packet[3]>=0x80:g.fail('pair-base-bias','positive ADD RAX imm8',row)
    bias=packet[3]
    if row['text']!=f'add rax, 0x{bias:x}':g.fail('pair-base-bias-decoding',bias,row)
    row=g.row();packet=bytes.fromhex(row['bytes'])
    if len(packet)!=4 or packet[:3]!=b'\x48\xc1\xe0' or packet[3]>=64:g.fail('pair-stride-shift','SHL RAX imm8 below 64',row)
    shift=packet[3]
    if row['text']!=f'shl rax, 0x{shift:x}':g.fail('pair-stride-shift-decoding',shift,row)
    _take(g,'add rax, rbx',b'\x48\x03\xc3');g.branch('jmp','dispatch');g.finish()
    _,tail_site=_cfg_and_frames(rows,start)
    if tail_site!=int(tail['va'],16):raise ValueError(LABEL+'.tail-site-mismatch')
    return {'completeOwnedControlProved':True,'checkedInstructions':len(rows),'ownedBytes':len(raw),
            'localBranches':sum(_transfer(row)['kind'] in ('jump','conditional') for row in rows),
            'originalIncomingObjectRegister':'r8','originalObjectSavedInRdi':True,
            'receiverFirstQwordLoadRva':receiver_load-base,'capturedComparisonCellRva':comparison_cell-base,
            'comparisonCellLoadRva':comparison_load-base,'comparisonValueCapturedBeforePreparationCall':True,
            'preparationCall':{'siteRva':prepare_call-base,'targetRva':prepare_target-base,'rcx':'fresh first QWORD of original incoming R8'},
            'freshWordCountLoad':{'siteRva':count_load-base,'receiverByteOffset':count_offset,'bits':16,'zeroExtended':True},
            'freshArrayPointerLoad':{'siteRva':array_load-base,'receiverByteOffset':array_offset,'memoryBytes':8,'zeroCountBypassesLoad':True},
            'scan':{'indexBits':16,'limitBits':16,'unsignedGuardBeforeEveryRecordLoad':True,
                'recordStrideBytes':16,'comparisonMemoryBytes':8,'matchComparisonRva':int(match['va'],16)-base,
                'wordIndexNeverWrapsOnAReachedContinuingIteration':True,'maximumRecordComparisons':65535,
                'normalFiniteLocalLoopConditionalOnReadableStorage':True,'firstMatchingRecordSelected':True},
            'resolverCall':{'siteRva':resolver_call-base,'targetRva':resolver_target-base,
                'rcx':'original incoming R8 object','rdx':'captured comparison QWORD','r8d':slot,
                'normalPairSource':'fresh child RAX, not a preserved pre-call pair'},
            'matchedPairAddress':{'offsetLoadRva':offset_load-base,'offsetMemoryBytes':4,'offsetRecordByteOffset':8,
                'slot':slot,'bias':bias,'shift':shift,'methodPairStrideBytes':1<<shift,
                'formula':'saved receiver QWORD + ((sign_extend_64((fresh offset DWORD + slot) modulo 2^32) + bias) << shift), with QWORD operations modulo 2^64',
                'signedExtensionOccursAfterDwordAddition':True,'nonnegativeOrInBoundsSlotProved':False},
            'tailTransfer':{'siteRva':tail_site-base,'targetLoadRva':method_load-base,'metadataLoadRva':metadata_load-base,
                'target':'fresh QWORD at selected pair + 0','rcx':'original incoming R8 object',
                'rdx':'fresh QWORD at selected pair + 8','rspRestoredToEntry':True,
                'savedNonvolatileRbxRsiRdiRestored':True,'normalCompatibleTailResultReturnsToOriginalCaller':True},
            'explicitStores':{'callerShadowQwordHomes':2,'payloadStoreInstructions':0},
            'callStackWritesAndUnknownChildEffectsRemain':True,'liveInterfaceOrMethodIdentityProved':False,
            'preparationOrResolverEffectsAndTerminationProved':False,'runtimeContextIdentityProved':False,
            'wholeConditionExecutionProved':False,'wholeRootAdmitted':False,
            'conditions':['Readable stable object, receiver/count/array/selected pair storage and valid actual tail target.',
                'Ordinary returning Win64 preparation/resolver callees preserve nonvolatile state and disjoint caller homes.',
                'Compatible normal tail target preserves the original return address and calling convention.',
                'Current selected native bytes and complete ownership are independently gated.']}
