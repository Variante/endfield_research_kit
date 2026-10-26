"""Named field layout and complete generic field-record construction.

This checks stored values and normal ABI flow, including inline allocation.
Actual class identity, valid capacity, unknown aliases and child effects are
conditions or unresolved joins; field count coherence is never inferred.
"""
from __future__ import annotations
from collections import deque
from .integer_byte_shifts import decode_byte_shift_instructions
from .integer_addressing import decode_lea_address
from .initializer_control import _graph,control_transfer
from .owned_partition import BranchGrammar,owned_windows,checked_rows,check_byte_partition,window_bytes,rip_load
from .relation_import_control import _memory

LABEL='fieldConstructionControl'
GETTERS={'il2cpp_field_get_name':('name',8),
         'il2cpp_field_get_type':('type',8),
         'il2cpp_field_get_parent':('parent',8),
         'il2cpp_field_get_offset':('offset',4)}


def _lea(g,register,*,base=None,index=None,scale=1,displacement=0,rip=None):
    r=g.row();raw=bytes.fromhex(r['bytes']);decoded=decode_lea_address(raw,0,int(r['va'],16))
    if decoded is None or decoded[1]!=len(raw):g.fail('lea-encoding','complete address',r)
    f=decoded[0]['addressOperation']
    if (f.get('destination'),f.get('destinationBits'))!=(register,64):g.fail('lea-register',register,r)
    correct=f.get('ripRelative') and f.get('absoluteAddress')==rip if rip is not None else (
        not f.get('ripRelative') and (f.get('base'),f.get('index'),f.get('scale'),f.get('displacement'))==(base,index,scale,displacement))
    if not correct:g.fail('lea-address',(base,index,scale,displacement,rip),r)


def _node_step(g,offset):
    r=g.row();f=r.get('memoryStepOperation',{});a=f.get('destinationAddress',{})
    if (f.get('operation'),f.get('bits'),f.get('locked'),a.get('base'),a.get('index'),a.get('displacement'),a.get('ripRelative'))!=('inc',64,False,'r14',None,offset,False):
        g.fail('node-count-step','unlocked QWORD increment of selected field',r)


def _rsp_frame(rows,edges,base,f):
    """RSP geometry only: RBP is a receiver here, not a frame base."""
    by_at={int(r['va'],16):r for r in rows};states={base+f['entryRva']:0};pending=deque(states)
    while pending:
        at=pending.popleft();r=by_at[at];sp=states[at];head,_,rest=r['text'].partition(' ')
        if head in ('push','pop'):
            if rest=='rsp':raise ValueError(LABEL+'.unreviewed-rsp')
            sp+=-8 if head=='push' else 8
        elif rest.split(',')[0]=='rsp':
            if head not in ('add','sub') or not rest.startswith('rsp, 0x'):raise ValueError(LABEL+'.unreviewed-rsp')
            amount=int(rest.split(', ')[1],16);sp+=amount if head=='add' else -amount
        kind=control_transfer(r)['kind']
        if kind in ('call','indirectCall','registerCall') and ((8+sp)%16 or -sp<32):raise ValueError(LABEL+'.call-frame')
        if kind=='return' and sp!=0:raise ValueError(LABEL+'.return-frame')
        for target in edges[at]:
            if target in states and states[target]!=sp:raise ValueError(LABEL+'.frame-join')
            if target not in states:states[target]=sp;pending.append(target)
    return states


def _word_register(g,raw,text):
    r=g.row()
    if bytes.fromhex(r['bytes'])!=raw:g.fail('word-register-width',text,r)


def _generic(rows,base,c):
    f=c['function'];fields=c['classFields'];record=c['recordFields'];a=f['allocation']
    frame=f['frameBytes'];homes=f['savedRegisterOffsets'];stride=f['strideBytes'];shift=f['strideShift']
    g=BranchGrammar(rows,label=LABEL)
    def mark(name):
        g.mark(name)
        if g.labels[name]!=base+f['labels'][name]:g.fail('label:'+name,f['labels'][name],g.labels[name]-base)
    for register in ('rbx','rbp','rsi'):_memory(g,'store',register,8,base='rsp',displacement=homes[register])
    g.take('push rdi','push r12','push r13','push r14','push r15',f'sub rsp, 0x{frame:x}','mov rbp, rcx')
    _memory(g,'load','rcx',8,base='rcx',displacement=fields['genericLink']);g.call(base+c['genericReceiver']['entryRva'])
    g.take('mov r13, rax',f'movzx r12d, word [rax+0x{fields["fieldCount"]:x}]','xor esi, esi')
    _word_register(g,b'\x66\x45\x85\xe4','TEST R12W, R12W');g.branch('jne','nonempty')
    _memory(g,'store','rsi',8,base='rbp',displacement=fields['fields']);g.branch('jmp','restore')
    mark('nonempty');g.take('mov rbx, r12');rip_load(g,'r14',base+a['contextCellRva'])
    g.take('mov r15, r12',f'shl r15, 0x{shift:x}')
    _memory(g,'load','rax',8,base='r14');_memory(g,'load','rcx',8,base='rax',displacement=a['listNext'])
    _memory(g,'load','rdi',8,base='rcx',displacement=a['nodeValue'])
    g.take(f'cmp qword [rdi+0x{a["remaining"]:x}], r15');g.branch('jae','reserve')
    r=g.row();raw=bytes.fromhex(r['bytes']);at=int(r['va'],16)
    wanted=b'\x40\x38\x35'+(base+a['modeCellRva']-at-7).to_bytes(4,'little',signed=True)
    if raw!=wanted:g.fail('byte-mode-comparison','CMP byte [selected RIP cell], SIL',r)
    g.branch('je','newblock');g.take('mov rcx, r14');g.call(base+a['refillTargetRva'])
    g.take('mov rdi, rax','test rax, rax');g.branch('jne','reserve')
    mark('newblock');rip_load(g,'rax',base+a['allocatorCellRva']);g.take(f'mov ecx, 0x{a["metadataBytes"]:x}','call rax','mov rdi, rax')
    _lea(g,'rax',base='r15',displacement=a['roundMask'])
    g.take(f'and rax, -0x{a["roundMask"]+1:x}',f'mov ebx, 0x{a["minimumBlockBytes"]:x}','cmp rax, rbx','cmova rbx, rax')
    rip_load(g,'rax',base+a['allocatorCellRva']);g.take('mov rcx, rbx','call rax')
    for offset in (a['cursor'],a['buffer']):_memory(g,'store','rax',8,base='rdi',displacement=offset)
    for offset in (a['remaining'],a['total']):_memory(g,'store','rbx',8,base='rdi',displacement=offset)
    _memory(g,'store','rsi',8,base='rdi',displacement=a['headWord']);_memory(g,'load','rbx',8,base='r14')
    g.take(f'mov rax, 0x{a["maximumNodes"]:x}',f'cmp qword [r14+0x{a["nodeCount"]:x}], rax');g.branch('je','failure')
    _memory(g,'store','r14',8,base='rsp',displacement=f['temporaryContextOffset'])
    _memory(g,'store','rsi',8,base='rsp',displacement=f['temporaryZeroOffset'])
    g.take(f'mov ecx, 0x{a["nodeBytes"]:x}');g.call(base+a['nodeAllocationTargetRva'])
    _memory(g,'store','rdi',8,base='rax',displacement=a['nodeValue']);_node_step(g,a['nodeCount'])
    _memory(g,'load','rcx',8,base='rbx',displacement=a['listNext'])
    _memory(g,'store','rbx',8,base='rax');_memory(g,'store','rcx',8,base='rax',displacement=a['listNext'])
    _memory(g,'store','rax',8,base='rbx',displacement=a['listNext']);_memory(g,'store','rax',8,base='rcx')
    g.take('mov rbx, r12')
    mark('reserve');_memory(g,'load','rcx',8,base='rdi',displacement=a['cursor'])
    _lea(g,'rdx',base='r15',index='rcx',scale=1);_memory(g,'store','rdx',8,base='rdi',displacement=a['cursor'])
    g.take(f'sub qword [rdi+0x{a["remaining"]:x}], r15',f'shl rbx, 0x{shift:x}','mov r8, rbx','xor edx, edx')
    clear=g.call(base+f['clearTargetRva']);g.take('mov r15, rax')
    _word_register(g,b'\x66\x41\x3b\xf4','CMP SI, R12W');g.branch('jae','publish')
    _lea(g,'rdi',base='rax',displacement=record['parent']);g.take('mov r14, r12','nop')
    mark('loop');_memory(g,'load','rdx',8,base='rbp',displacement=fields['genericLink'])
    g.take(f'add rdx, 0x{f["genericContextOffset"]:x}')
    _memory(g,'load','rbx',8,base='r13',displacement=fields['fields']);g.take('add rbx, rsi','xor r8d, r8d')
    _memory(g,'load','rcx',8,base='rbx',displacement=record['type']);inflate=g.call(base+f['inflateTargetRva'])
    _memory(g,'store','rax',8,base='rdi',displacement=record['type']-record['parent'])
    _memory(g,'load','rax',8,base='rbx',displacement=record['name'])
    _memory(g,'store','rax',8,base='rdi',displacement=record['name']-record['parent'])
    _memory(g,'store','rbp',8,base='rdi')
    for name in ('offset','trailingWord'):
        _memory(g,'load','eax',4,base='rbx',displacement=record[name])
        _memory(g,'store','eax',4,base='rdi',displacement=record[name]-record['parent'])
    _lea(g,'rdi',base='rdi',displacement=stride);g.take(f'add rsi, 0x{stride:x}','sub r14, 0x1');g.branch('jne','loop')
    mark('publish');_memory(g,'store','r15',8,base='rbp',displacement=fields['fields'])
    mark('restore')
    for register in ('rbx','rbp','rsi'):_memory(g,'load',register,8,base='rsp',displacement=homes[register]+frame+5*8)
    g.take(f'add rsp, 0x{frame:x}','pop r15','pop r14','pop r13','pop r12','pop rdi','ret')
    mark('failure');_lea(g,'rcx',rip=base+a['failureMessageRva']);g.call(base+a['failureTargetRva']);g.take('int3');g.finish()
    spans=sorted((record[name],record[name]+width) for name,width in [('name',8),('type',8),('parent',8),('offset',4),('trailingWord',4)])
    if f['countBits']!=16 or stride!=1<<shift or spans[0][0]!=0 or spans[-1][1]!=stride or any(x[1]!=y[0] for x,y in zip(spans,spans[1:])):
        raise ValueError(LABEL+'.record-partition-and-domain')
    limit=(1<<f['countBits'])-1;maximum=limit*stride;mask=a['roundMask']
    if mask<=0 or (mask+1)&mask or a['minimumBlockBytes']<=0:raise ValueError(LABEL+'.reservation-domain')
    return {'savedCountBits':16,'fieldStrideBytes':stride,'maximumRecordCount':limit,'maximumRecordBytes':maximum,
            'maximumRoundedRequestBytes':(maximum+mask)&~mask,
            'zeroCountStoresNullFieldsAndSkipsInlineAllocation':True,
            'nonzeroLoopIterationsConditionallyEqualSavedCount':True,
            'sourceFieldBaseReloadedForEachRecord':True,'sourceNameOffsetAndTrailingWordReloadedAfterInflate':True,
            'explicitRecordWritesCoverEveryByteExactlyOncePerIteration':True,
            'inflateCallRva':int(inflate['va'],16)-base,'clearCallRva':int(clear['va'],16)-base,
            'inflateArguments':{'type':'fresh source record type','genericContext':'fresh receiver generic link + reviewed context offset','thirdWord':0},
            'constructedRecordParentIsOriginalReceiverConditionallyProved':True,
            'publishedFieldsPointerIsClearReturnConditionallyProved':True,
            'clearArgumentsAreOldCursorZeroAndSavedCountTimesStrideProved':True,
            'receiverFieldCountAssignedByThisProgram':False,
            'receiverCountEqualsSavedSourceCountProved':False,
            'childMayModifyAliasesOrIncomingPointedSlot':True,
            'allocationSuccessCapacityAndRuntimeExecutionProved':False}


def validate_field_construction_control(index,c,exports):
    base=index.pe.image_base;selected={r['symbolName']:r for r in exports['selectedExports']}
    if set(selected)!=set(GETTERS) or any(r['isForwarder'] for r in selected.values()):raise ValueError(LABEL+'.selected-export-set')
    closed=[]
    if {r['symbolName'] for r in c['getters']}!=set(GETTERS) or len(c['getters'])!=len(GETTERS):raise ValueError(LABEL+'.getter-set')
    for f in c['getters']:
        role,width=GETTERS[f['symbolName']];w=f['window'];entry=base+f['entryRva']
        if f['role']!=role or selected[f['symbolName']]['targetRva']!=f['entryRva'] or w['startRva']!=f['entryRva'] or not 2<=w['endRva']-w['startRva']<=16:raise ValueError(LABEL+'.getter-entry')
        raw=window_bytes(index,entry,base+w['endRva'],w['sha256'],LABEL);rows=checked_rows(decode_byte_shift_instructions(index.mapper,raw,entry),raw,LABEL)
        g=BranchGrammar(rows,label=LABEL)
        if role=='offset':
            r=g.row();fact=r.get('dwordSignExtensionOperation',{});address=fact.get('sourceAddress',{})
            if (fact.get('destinationRegister'),fact.get('destinationBits'),fact.get('sourceBits'),fact.get('memoryReadBytes'),address.get('base'),address.get('index'),address.get('displacement'),address.get('ripRelative'))!=('rax',64,32,4,'rcx',None,c['recordFields'][role],False):
                g.fail('named-offset-sign-extension','signed DWORD field extended to RAX',r)
        else:_memory(g,'load','rax',width,base='rcx',displacement=c['recordFields'][role])
        g.take('ret');g.finish()
        closed.append({'role':role,'bytes':len(raw),'instructions':len(rows),'physicalExtentProved':False})
    wrapper=c['genericReceiver'];w=wrapper['window'];entry=base+wrapper['entryRva']
    if w['startRva']!=wrapper['entryRva'] or not 2<=w['endRva']-w['startRva']<=16:raise ValueError(LABEL+'.receiver-wrapper-window')
    raw=window_bytes(index,entry,base+w['endRva'],w['sha256'],LABEL);rows=checked_rows(decode_byte_shift_instructions(index.mapper,raw,entry),raw,LABEL)
    g=BranchGrammar(rows,label=LABEL);_memory(g,'load','rcx',8,base='rcx');jump=g.branch('jmp');g.finish()
    if jump['target']!=base+wrapper['tailTargetRva']:g.fail('receiver-wrapper-tail',wrapper['tailTargetRva'],jump)
    closed.append({'role':'genericReceiver','bytes':len(raw),'instructions':len(rows),'physicalExtentProved':False})
    f=c['function'];owned,pieces,windows=owned_windows(index,f,LABEL)
    if f['paddingWindows']:raise ValueError(LABEL+'.unreviewed-padding')
    rows=[]
    for _,_,start,raw in windows:rows.extend(checked_rows(decode_byte_shift_instructions(index.mapper,raw,start),raw,LABEL))
    rows.sort(key=lambda r:int(r['va'],16));check_byte_partition(owned,pieces,LABEL)
    if len(rows)!=f['checkedInstructionCount']:raise ValueError(LABEL+'.instruction-count')
    edges,calls,stores,returns,traps=_graph(rows,base,f);_rsp_frame(rows,edges,base,f)
    summary=_generic(rows,base,c)
    return {**summary,'checkedInstructions':len(rows)+sum(r['instructions'] for r in closed),'ownedBytes':sum(b-a for a,b in owned),
            'closedEntryBytes':sum(r['bytes'] for r in closed),'explicitStores':len(stores),'closedEntries':closed,
            'callSites':calls,'returnSites':returns,'trapSites':traps,'recordFields':c['recordFields'],
            'namedFieldNameTypeParentOffsetConsumersProved':True,'namedOffsetIsSignedDwordExtendedTo64Proved':True,'trailingWordSemanticNameProved':False,
            'liveClassOrFormatterIdentityProved':False,'incomingSlotContentsUnchangedProved':False,
            'positiveListAdmitted':False,'wholeRootAdmitted':False}
