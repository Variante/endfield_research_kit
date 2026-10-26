"""Named class bits, field iteration, and the complete preparation bridge.

Named on-disk exports anchor physical meanings. Caller/storage coherence,
normal ABI returns and noninterference remain conditions; child effects,
actual class identity, initialized capacity and termination remain open.
"""
from __future__ import annotations
from .integer_byte_shifts import decode_byte_shift_instructions
from .initializer_control import _graph, _frame
from .owned_partition import BranchGrammar, owned_windows, checked_rows, check_byte_partition, window_bytes
from .class_ancestry_control import _load_byte
from .relation_import_control import _memory, _lea, _branch, _import, _exchange, _step

LABEL='classFieldControl'
EXPORTS={'il2cpp_class_get_flags','il2cpp_class_is_blittable',
         'il2cpp_class_has_references','il2cpp_class_get_fields'}


def _test(g, base, offset, mask):
    g.take(f'test byte [{base}+0x{offset:x}], 0x{mask:x}')


def _logic(g, operation, base, offset, mask):
    row=g.row(); fact=row.get('byteMemoryLogicalOperation',{}); address=fact.get('destinationAddress',{})
    if (fact.get('operation'),fact.get('bits'),fact.get('immediateWord'),
        fact.get('memoryReadBytes'),fact.get('memoryWriteBytes'),address.get('base'),
        address.get('index'),address.get('displacement'),address.get('ripRelative')) != (
            operation,8,mask,1,1,base,None,offset,False):
        g.fail('byte-flag-write',(operation,base,offset,mask),row)


def _bit_result(g, bit):
    row=g.row(); f=row.get('byteRegisterShiftOperation',{})
    if type(bit)!=int or not 0<=bit<8 or (
        f.get('destinationRegister'),f.get('bits'),f.get('bitOffset'),
        f.get('effectiveCount'),f.get('logicalZeroFill'),f.get('preservesOtherParentBits')) != (
            'al',8,0,bit,True,True):g.fail('selected-bit-extraction',bit,row)
    row=g.row(); f=row.get('byteLogicalOperation',{})
    if (f.get('operation'),f.get('destinationRegister'),f.get('bits'),f.get('immediateWord')) != ('and','al',8,1):
        g.fail('selected-bit-normalization','AND AL, 1',row)


def _word_zero(g, offset):
    row=g.row(); raw=bytes.fromhex(row['bytes'])
    if raw!=b'\x66\x83\xbf'+offset.to_bytes(4,'little',signed=True)+b'\x00':
        g.fail('word-count-zero','CMP word [RDI+disp32], zero',row)


def _marks(g, f, base):
    def mark(name):
        g.mark(name)
        if g.labels[name]!=base+f['labels'][name]:g.fail('label:'+name,f['labels'][name],g.labels[name]-base)
    return mark


def _has_references(rows, base, c, f):
    fields=c['physicalFields']; g=BranchGrammar(rows,label=LABEL); mark=_marks(g,f,base)
    ready=1<<c['bits']['fieldsReady']; frame=f['frameBytes']
    g.take('push rbx',f'sub rsp, 0x{frame:x}');_test(g,'rcx',fields['fieldState'],ready)
    g.take('mov rbx, rcx');g.branch('je','prepare')
    mark('result');_load_byte(g,'eax','rbx',fields['stateFlags']);_bit_result(g,c['bits']['hasReferences'])
    g.take(f'add rsp, 0x{frame:x}','pop rbx','ret')
    mark('prepare');g.call(base+c['functions']['bridge']['entryRva'])
    _test(g,'rbx',fields['fieldState'],ready);g.branch('jne','result')
    g.call(base+f['failureTargetRva']);g.take('int3');g.finish()


def _field_iterator(rows, base, c, f):
    fields=c['physicalFields']; frame=f['frameBytes']; home=f['savedRegisterOffset']
    g=BranchGrammar(rows,label=LABEL);mark=_marks(g,f,base)
    _memory(g,'store','rbx',8,base='rsp',displacement=home)
    g.take('push rdi',f'sub rsp, 0x{frame:x}','mov rbx, rdx','mov rdi, rcx','test rdx, rdx')
    g.branch('je','empty');g.take('cmp qword [rdx], 0x0');g.branch('je','prepare')
    g.take(f'movzx ecx, word [rcx+0x{fields["fieldCount"]:x}]')
    _memory(g,'load','rax',8,base='rdx');g.take(f'shl rcx, 0x{f["strideShift"]:x}',f'add rax, 0x{f["strideBytes"]:x}')
    row=g.row();raw=bytes.fromhex(row['bytes'])
    expected=b'\x48\x03\x8f'+fields['fields'].to_bytes(4,'little',signed=True)
    # This selected ADD uses a disp32. A disp8 representation is also accepted
    # below after decoding its original exact instruction length.
    short=b'\x48\x03\x4f'+fields['fields'].to_bytes(1,'little') if 0<=fields['fields']<128 else None
    if raw not in (expected,short):g.fail('field-array-end','ADD RCX, QWORD [RDI+fields]',row)
    g.take('cmp rax, rcx');g.branch('jae','empty');_memory(g,'store','rax',8,base='rdx')
    mark('restore');_memory(g,'load','rbx',8,base='rsp',displacement=home+frame+8)
    g.take(f'add rsp, 0x{frame:x}','pop rdi','ret')
    mark('prepare');call=g.call(base+c['functions']['bridge']['entryRva']);_word_zero(g,fields['fieldCount'])
    g.branch('jne','first')
    mark('empty');g.take('xor eax, eax');g.branch('jmp','restore')
    mark('first');_memory(g,'load','rax',8,base='rdi',displacement=fields['fields'])
    _memory(g,'store','rax',8,base='rbx')
    # The second receiver-field load is fresh after the iterator write.
    _memory(g,'load','rax',8,base='rdi',displacement=fields['fields'])
    _memory(g,'load','rbx',8,base='rsp',displacement=home+frame+8)
    g.take(f'add rsp, 0x{frame:x}','pop rdi','ret');g.finish()
    if type(f['strideShift'])!=int or not 0<=f['strideShift']<=31 or f['strideBytes']!=1<<f['strideShift']:
        raise ValueError(LABEL+'.field-stride')
    return {'preparationCallRva':int(call['va'],16)-base,
            'iteratorWritesPointedSlotDirectly':True,'initialReturnReloadsFieldsAfterIteratorWrite':True,
            'initialStoredPointerEqualsReloadedReturnWithoutNoninterferenceProved':False,
            'fieldCountBits':16,'fieldStrideBytes':f['strideBytes'],
            'iterationEndGuard':'unsigned next pointer >= fresh field base + unsigned field count * stride',
            'iterationGuardAssumesNonwrappingValidArrayForCapacityInterpretation':True}


def _bridge(rows, base, c, f):
    fields=c['physicalFields'];p=c['protocol'];offsets=p['offsets'];frame=f['frameBytes'];home=f['contextStackOffset']
    g=BranchGrammar(rows,label=LABEL);mark=_marks(g,f,base);ready=1<<c['bits']['fieldsReady']
    g.take('push rbx',f'sub rsp, 0x{frame:x}','mov rbx, rcx');_test(g,'rcx',fields['fieldState'],ready)
    g.branch('jne','restore');_lea(g,'rcx',absolute=base+p['globalContextRva'])
    _memory(g,'store','rcx',8,base='rsp',displacement=home);g.call(base+f['acquireTargetRva']);g.take('nop')
    _lea(g,'rdx',displacement=home);g.take('mov rcx, rbx');call=g.call(base+c['functions']['setup']['entryRva']);g.take('nop')
    _memory(g,'load','r8',8,base='rsp',displacement=home)
    g.take(f'cmp dword [r8+0x{offsets["reentry"]:x}], 0x0');_branch(g,'jle',base+f['labels']['restore'])
    g.take(f'cmp dword [r8+0x{offsets["reentry"]:x}], 0x1');g.branch('jne','decrement')
    g.take('xor eax, eax');_memory(g,'store','rax',8,base='r8',displacement=offsets['owner'])
    _memory(g,'store','eax',4,base='r8',displacement=offsets['reentry']);g.take('mov r9d, 0x1')
    _memory(g,'load','ecx',4,base='r8',displacement=offsets['count']);g.take('nop')
    mark('retry');g.take(f'cmp ecx, dword [r8+0x{offsets["limit"]:x}]');g.branch('je','restore')
    g.take('lea eax, [rcx+r9*1]',f'cmp eax, dword [r8+0x{offsets["limit"]:x}]');_branch(g,'jle',base+f['labels']['candidate'])
    _memory(g,'load','r9d',4,base='r8',displacement=offsets['limit']);g.take('sub r9d, ecx')
    mark('candidate');g.take('lea edx, [rcx+r9*1]','mov eax, ecx');_exchange(g,'cmpxchg','edx',displacement=offsets['count'])
    g.branch('je','exchanged');g.take('mov ecx, eax');g.branch('jmp','retry')
    mark('exchanged');g.take('test ecx, ecx');_branch(g,'jns',base+f['labels']['restore'])
    g.take('neg ecx','cmp r9d, ecx','cmovge r9d, ecx','mov edx, r9d')
    _memory(g,'load','rcx',8,base='r8',displacement=offsets['handle']);_import(g,base+f['releaseSlotRva']);g.branch('jmp','restore')
    mark('decrement');_step(g,'dec',displacement=offsets['reentry'])
    mark('restore');g.take(f'add rsp, 0x{frame:x}','pop rbx','ret');g.finish()
    if not frame<=home<=frame+32:raise ValueError(LABEL+'.bridge-home')
    return {'setupCallRva':int(call['va'],16)-base,'setupReceivesOriginalClassReceiver':True,
            'setupReceivesAddressOfBridgeStackSlot':True,'postSetupReleaseContextPointerTreatedAsFresh':True,
            'bridgeSetupArgumentIsComputedStackSlotAddress':True,
            'bridgeSlotAndOriginalIteratorAddressDisjointProved':False}


def _setup(rows, base, c, f):
    fields=c['physicalFields'];frame=f['frameBytes'];home=f['savedRegisterOffset'];ready=1<<c['bits']['fieldsReady'];preparing=1<<c['bits']['fieldsPreparing']
    g=BranchGrammar(rows,label=LABEL);mark=_marks(g,f,base)
    _memory(g,'store','rbx',8,base='rsp',displacement=home);g.take('push rdi',f'sub rsp, 0x{frame:x}')
    _test(g,'rcx',fields['fieldState'],ready);g.take('mov rdi, rdx','mov rbx, rcx');g.branch('jne','restore')
    _logic(g,'or','rcx',fields['stateFlags'],preparing)
    g.take(f'cmp qword [rcx+0x{fields["parent"]:x}], 0x0');g.branch('je','generic')
    _memory(g,'load','rax',8,base='rcx',displacement=fields['parent']);_test(g,'rax',fields['fieldState'],ready);g.branch('je','parent')
    mark('generic');g.take(f'cmp qword [rbx+0x{fields["genericLink"]:x}], 0x0');g.branch('je','ordinary')
    _memory(g,'load','rcx',8,base='rbx',displacement=fields['genericLink']);g.call(base+f['genericReceiverTargetRva'])
    g.take('mov rcx, rax','mov rdx, rdi');g.call(base+f['entryRva'])
    g.take('mov rcx, rbx');g.call(base+f['genericFieldsTargetRva'])
    mark('auxiliary');_test(g,'rbx',fields['stateFlags'],f['skipAuxiliaryMask']);g.branch('jne','finish')
    g.take('mov rcx, rbx');g.call(base+f['auxiliaryTargetRva'])
    mark('finish');_logic(g,'and','rbx',fields['stateFlags'],255^preparing)
    _logic(g,'or','rbx',fields['fieldState'],ready)
    mark('restore');_memory(g,'load','rbx',8,base='rsp',displacement=home+frame+8)
    g.take(f'add rsp, 0x{frame:x}','pop rdi','ret')
    mark('ordinary');g.take('mov rcx, rbx');g.call(base+f['ordinaryFieldsTargetRva']);g.branch('jmp','auxiliary')
    mark('parent');g.take('mov rcx, rax');g.call(base+f['entryRva']);g.branch('jmp','generic');g.finish()
    return {'completeFieldPreparationFlagAndRecursiveControlChecked':True,
            'directParentAndGenericRecursiveCalls':2,'recursiveCallsReuseIncomingAddressConditionally':True,
            'noAdditionalPreparingBitGuardBeforeParentRecursion':True,
            'preparationFinishClearsPreparingBitAndSetsFieldsReadyBit':True,
            'childFieldStorageConstructionOrPointedSlotEffectsProved':False}


def validate_class_field_control(index,c,exports):
    base=index.pe.image_base;selected={e['symbolName']:e for e in exports['selectedExports']}
    if set(selected)!=EXPORTS or any(e['isForwarder'] for e in selected.values()):raise ValueError(LABEL+'.selected-export-set')
    fields=c['physicalFields'];bits=c['bits'];closed=[]
    for role,name in [('typeFlags','il2cpp_class_get_flags'),('blittable','il2cpp_class_is_blittable'),('hasReferencesTail','il2cpp_class_has_references')]:
        f=c['closedEntries'][role];w=f['window'];entry=base+f['entryRva']
        if selected[name]['targetRva']!=f['entryRva'] or w['startRva']!=f['entryRva']:raise ValueError(LABEL+'.closed-export-entry')
        if not 1<=w['endRva']-w['startRva']<=32:raise ValueError(LABEL+'.closed-entry-range')
        raw=window_bytes(index,entry,base+w['endRva'],w['sha256'],LABEL)
        rows=checked_rows(decode_byte_shift_instructions(index.mapper,raw,entry),raw,LABEL);g=BranchGrammar(rows,label=LABEL)
        if role=='typeFlags':_memory(g,'load','eax',4,base='rcx',displacement=fields['typeFlags']);g.take('ret')
        elif role=='blittable':_load_byte(g,'eax','rcx',fields['fieldState']);_bit_result(g,bits['blittable']);g.take('ret')
        else:
            r=g.branch('jmp')
            if r['target']!=base+c['functions']['hasReferences']['entryRva']:g.fail('has-references-tail',c['functions']['hasReferences']['entryRva'],r)
        g.finish();closed.append({'role':role,'bytes':len(raw),'instructions':len(rows),'physicalExtentProved':False})
    results={};count=sum(r['instructions'] for r in closed);size=0;stores=0
    programs={'hasReferences':_has_references,'fieldIterator':_field_iterator,'bridge':_bridge,'setup':_setup}
    if set(c['functions'])!=set(programs):raise ValueError(LABEL+'.function-role-set')
    if selected['il2cpp_class_get_fields']['targetRva']!=c['functions']['fieldIterator']['entryRva']:raise ValueError(LABEL+'.iterator-export-entry')
    for role,program in programs.items():
        f=c['functions'][role];owned,pieces,windows=owned_windows(index,f,LABEL)
        if f['paddingWindows']:raise ValueError(LABEL+'.unreviewed-padding')
        rows=[]
        for _,_,start,raw in windows:rows.extend(checked_rows(decode_byte_shift_instructions(index.mapper,raw,start),raw,LABEL))
        rows.sort(key=lambda r:int(r['va'],16));check_byte_partition(owned,pieces,LABEL)
        if len(rows)!=f['checkedInstructionCount']:raise ValueError(LABEL+'.instruction-count')
        edges,calls,writes,returns,traps=_graph(rows,base,f);_frame(rows,edges,base,f)
        result=program(rows,base,c,f) or {}
        results[role]={'checkedInstructions':len(rows),'ownedBytes':sum(b-a for a,b in owned),'explicitStores':len(writes),
                       'callSites':calls,'returnSites':returns,'trapSites':traps,**result}
        count+=len(rows);size+=sum(b-a for a,b in owned);stores+=len(writes)
    projection=c['callerBlittableInheritance'];w=projection['window']
    raw=window_bytes(index,base+w['startRva'],base+w['endRva'],w['sha256'],LABEL)
    rows=checked_rows(decode_byte_shift_instructions(index.mapper,raw,base+w['startRva']),raw,LABEL)
    g=BranchGrammar(rows,label=LABEL)
    _memory(g,'load','rcx',8,base='rcx',displacement=fields['genericLink']);_memory(g,'load','rcx',8,base='rcx')
    g.call(base+projection['genericDefinitionTargetRva']);g.take('mov rbx, rax','mov rdx, rdi','mov rcx, rax')
    g.call(base+c['incomingCallerJoin']['entryRva']);_load_byte(g,'eax','r13',fields['fieldState']);g.take('movzx ecx, al')
    row=g.row();expected=b'\x32\x8b'+fields['fieldState'].to_bytes(4,'little',signed=True)
    if bytes.fromhex(row['bytes'])!=expected:g.fail('other-receiver-byte-xor','XOR CL, byte [RBX+fieldState]',row)
    row=g.row();f=row.get('byteLogicalOperation',{})
    if (f.get('operation'),f.get('destinationRegister'),f.get('immediateWord'))!=('and','cl',1<<bits['blittable']):
        g.fail('blittable-transfer-mask',1<<bits['blittable'],row)
    g.take('xor cl, al');_memory(g,'store','cl',1,base='r13',displacement=fields['fieldState']);g.finish()
    count+=len(rows)
    return {'checkedInstructions':count,'ownedBytes':size,'closedEntryBytes':sum(r['bytes'] for r in closed),
            'callerProjectionBytes':len(raw),
            'closedEntries':closed,'explicitStoreSites':stores,'programs':results,
            'namedBlittableBitConsumerProved':True,'namedHasReferencesBitConsumerProved':True,
            'namedFieldIteratorAndCompletePreparationBridgeProved':True,'physicalFields':fields,'bits':bits,
            'actualCallerBlittableBitTransferProved':True,
            'callerBlittableBitTransfer':'old receiver byte with its selected bit replaced by the freshly read other receiver bit',
            'genericDefinitionResultIsLiveClassProved':False,
            'liveClassOrFormatterIdentityProved':False,'incomingSlotContentsUnchangedProved':False,
            'initializationCapacityOrSynchronizationOutcomeProved':False,'recursiveTerminationProved':False,
            'callbackCursorEqualityProved':False,'positiveListAdmitted':False,'wholeRootAdmitted':False}
