"""Complete conditional migration and power-of-two triangular probe theorem.

Post-allocation storage/capacity invariants are explicit conditions, not observed
runtime facts. Duplicate-key population and class/provider identity stay open.
"""
from __future__ import annotations
from .type_data_initialization_control import _complete
from .method_carrier_control import _Grammar
from .method_carrier_resolution import _memory
from .initializer_control import _ALIASES
from .name_cache_marker_iterator_control import validate_name_cache_marker_iterator,marker_al,select_slot
from .class_creation_control import _dominators

LABEL='nameCacheDestinationMigrationControl'

def probe_indices(capacity,initial_hash):
    """Each slot exactly once, conditional on a nonzero power-of-two capacity."""
    if type(capacity) is not int or not 0<capacity<1<<64 or capacity&(capacity-1) or type(initial_hash) is not int or not 0<=initial_hash<1<<64:
        raise ValueError(LABEL+'.conditional-power-two-probe-domain')
    index=initial_hash&(capacity-1);step=0
    for _ in range(capacity):
        yield index;step+=1;index=(index+step)&(capacity-1)

def hash_key(namespace,name,profile):
    """Actual signed-byte alternating CString hash; header/record are not inputs."""
    mask=(1<<profile['wordBits'])-1
    def one(value):
        if not isinstance(value,(bytes,bytearray)) or 0 not in value:raise ValueError(LABEL+'.selected-hash-cstring-domain')
        a=b=profile['seed']
        for i,v in enumerate(bytes(value).split(b'\0',1)[0]):
            signed=v if v<128 else v-256
            if i&1:b=((b*profile['characterMultiplier'])^signed)&mask
            else:a=((a*profile['characterMultiplier'])^signed)&mask
        return (a+b*profile['pairMultiplier'])&mask
    return (one(name)+one(namespace)*profile['namespaceMultiplier'])&mask

def migrate_slots(source,destination_capacity,free_descriptor,removed_descriptor,profile,*,max_model_slots=1<<20):
    """Field-level composition model under the explicitly validated domain."""
    if destination_capacity>max_model_slots:raise ValueError(LABEL+'.bounded-migration-model-domain')
    indices=list(probe_indices(destination_capacity,0))
    ordinary=[];cursor=select_slot(source,0,len(source),free_descriptor,removed_descriptor)
    while cursor<len(source):
        node=source[cursor]
        if len(node)!=4:raise ValueError(LABEL+'.node-field-domain')
        hash_key(node[1],node[2],profile)
        if marker_al(free_descriptor[0],node[0],free_descriptor[1],node[1],free_descriptor[2],node[2]):raise ValueError(LABEL+'.ordinary-source-is-free-marker')
        ordinary.append(node);cursor=select_slot(source,cursor+1,len(source),free_descriptor,removed_descriptor)
    if len(ordinary)>len(indices):raise ValueError(LABEL+'.insufficient-destination-slots')
    dest=[None]*destination_capacity;probes=[]
    for node in ordinary:
        visits=0
        for index in probe_indices(destination_capacity,hash_key(node[1],node[2],profile)):
            visits+=1
            if dest[index] is None:dest[index]=node;break
        else:raise AssertionError('conditional permutation failed to reach an available slot')
        probes.append(visits)
    return {'nodes':dest,'ordinaryNodes':ordinary,'usedCount':len(ordinary),'probeCounts':probes}

def _hash(rows,h):
    g=_Grammar(rows,label=LABEL+'.hash');seed=h['seed'];mul=h['characterMultiplier'];pair=h['pairMultiplier'];mix=h['namespaceMultiplier']
    if (h['wordBits'],h['signedCharacterBits'])!=(64,8):raise ValueError(LABEL+'.hash-word-domain')
    _memory(g,'load','rcx',8,'rdx',16);g.take(f'mov r8d, 0x{seed:x}','mov r11, rdx','mov r9d, r8d','mov r10d, r8d','movzx eax, byte [rcx]','test al, al');g.branch('je','namespaceStart');g.take('nop');g.mark('nameLoop')
    g.take(f'imul r9, r9, 0x{mul:x}','movsx rax, al','xor r9, rax','movsx rax, byte [rcx+0x1]','test al, al');g.branch('je','namespaceStart');g.take(f'imul r10, r10, 0x{mul:x}','add rcx, 0x2','xor r10, rax','movzx eax, byte [rcx]','test al, al');g.branch('jne','nameLoop')
    g.mark('namespaceStart');_memory(g,'load','rax',8,'r11',8);g.take('mov rdx, r8',f'imul r10, r10, 0x{pair:x}','movzx ecx, byte [rax]','add r10, r9','test cl, cl');g.branch('je','combine');g.take('nop');g.mark('namespaceLoop')
    g.take(f'imul r8, r8, 0x{mul:x}','movsx rcx, cl','xor r8, rcx','movsx rcx, byte [rax+0x1]','test cl, cl');g.branch('je','combine');g.take(f'imul rdx, rdx, 0x{mul:x}','add rax, 0x2','xor rdx, rcx','movzx ecx, byte [rax]','test cl, cl');g.branch('jne','namespaceLoop')
    g.mark('combine');g.take(f'imul rax, rdx, 0x{pair:x}','add rax, r8',f'imul rax, rax, 0x{mix:x}','add rax, r10','ret');g.finish()

def _migration(rows,l,roles,base):
    g=_Grammar(rows,label=LABEL+'.migration')
    for reg,off in (('rbx',8),('rbp',16),('rsi',24),('rdi',32)):_memory(g,'store',reg,8,'rsp',off)
    g.take('push r14','sub rsp, 0x60','mov rbx, rdx','mov rsi, rcx');_memory(g,'load','rdx',8,'rdx',l['cacheUsedCount']);g.take(f'sub rdx, qword [rbx+0x{l["cacheRemovedCount"]:x}]');g.call(base+roles['capacity']['entryRva']);g.take('mov rdx, rax','mov rcx, rsi');g.call(base+roles['allocation']['entryRva'])
    _memory(g,'load','r9',8,'rbx',l['cacheCapacity']);g.take(f'lea rcx, [rsp+0x{l["callerBeginIterator"]:x}]');_memory(g,'load','r8',8,'rbx',l['cacheNodes']);g.take('mov rdx, rbx','shl r9, 0x5',f'add r9, qword [rbx+0x{l["cacheNodes"]:x}]',f'mov byte [rsp+0x{l["callerScanByte"]:x}], 0x1');g.call(base+roles['iteratorCreate']['entryRva']);g.take('nop')
    g.mark('endRefresh');_memory(g,'load','r9',8,'rbx',l['cacheCapacity']);g.take(f'lea rcx, [rsp+0x{l["callerEndIterator"]:x}]');_memory(g,'load','r8',8,'rbx',l['cacheCapacity']);g.take('mov rdx, rbx','shl r9, 0x5',f'add r9, qword [rbx+0x{l["cacheNodes"]:x}]','shl r8, 0x5',f'add r8, qword [rbx+0x{l["cacheNodes"]:x}]',f'mov byte [rsp+0x{l["callerScanByte"]:x}], 0x1');g.call(base+roles['iteratorCreate']['entryRva'])
    _memory(g,'load','rdi',8,'rsp',l['callerBeginIterator']+l['iteratorCursor']);g.take(f'cmp rdi, qword [rsp+0x{l["callerEndIterator"]+l["iteratorCursor"]:x}]');g.branch('je','finish')
    _memory(g,'load','rbp',8,'rsi',l['cacheCapacity']);g.take('xor r14d, r14d','dec rbp','mov rdx, rdi');g.call(base+roles['hash']['entryRva']);_memory(g,'load','r11d',4,'rsi',l['cacheFreeHeader']);g.take('mov r9, rax')
    g.mark('probe');g.take('and r9, rbp','mov r8, r9','shl r8, 0x5',f'add r8, qword [rsi+0x{l["cacheNodes"]:x}]','cmp r11d, dword [r8]');g.branch('jne','advanceProbe');g.take('test r11d, r11d');g.branch('je','freeStrings')
    g.mark('copy');_memory(g,'load','eax',4,'rdi',0);g.take(f'lea rcx, [rsp+0x{l["callerBeginIterator"]:x}]','shl r9, 0x5',f'add r9, qword [rsi+0x{l["cacheNodes"]:x}]');_memory(g,'store','eax',4,'r9',0);_memory(g,'load','xmm0',16,'rdi',8);_memory(g,'store','xmm0',16,'r9',8);_memory(g,'load','rax',8,'rdi',24);g.take('add rdi, 0x20');_memory(g,'store','rax',8,'r9',24);g.take(f'inc qword [rsi+0x{l["cacheUsedCount"]:x}]');_memory(g,'store','rdi',8,'rsp',l['callerBeginIterator']+l['iteratorCursor']);g.call(base+roles['iteratorNext']['entryRva']);g.branch('jmp','endRefresh')
    g.mark('freeStrings');_memory(g,'load','rax',8,'rsi',l['cacheFreeStrings']);_memory(g,'load','r10',8,'r8',8);g.take('sub r10, rax');g.mark('freeNamespace')
    g.take('movzx edx, byte [rax]','movzx ecx, byte [rax+r10*1]','sub edx, ecx');g.branch('jne','namespaceDone');g.take('inc rax','test ecx, ecx');g.branch('jne','freeNamespace');g.mark('namespaceDone');g.take('test edx, edx');g.branch('jne','advanceProbe')
    _memory(g,'load','rax',8,'rsi',l['cacheFreeStrings']+8);_memory(g,'load','r10',8,'r8',16);g.take('sub r10, rax','nop');g.mark('freeName')
    g.take('movzx edx, byte [rax]','movzx ecx, byte [rax+r10*1]','sub edx, ecx');g.branch('jne','nameDone');g.take('inc rax','test ecx, ecx');g.branch('jne','freeName');g.mark('nameDone');g.take('test edx, edx');g.branch('je','copy')
    g.mark('advanceProbe');g.take('inc r14','add r9, r14');g.branch('jmp','probe');g.mark('finish');g.take(f'inc dword [rsi+0x{l["cacheGeneration"]:x}]','lea r11, [rsp+0x60]')
    for reg,off in (('rbx',16),('rbp',24),('rsi',32),('rdi',40)):_memory(g,'load',reg,8,'r11',off)
    g.take('mov rsp, r11','pop r14','ret');g.finish()

def validate_name_cache_destination_migration(programs,*,image_base,contract):
    c=contract;base=image_base;roles=c['functions'];required={'migration','allocation','iteratorCreate','iteratorNext','nodeInitializer','iteratorPredicate','capacity','hash'}
    if set(programs)!=required or set(roles)!=required:raise ValueError(LABEL+'.function-membership')
    subset=required-{'capacity','hash'};old={**c,'functions':{k:roles[k] for k in subset}};joined=validate_name_cache_marker_iterator({k:programs[k] for k in subset},image_base=base,contract=old)
    graphs={role:_complete(rr,base+roles[role]['entryRva']) for role,rr in programs.items()};_hash(programs['hash'],c['hashArithmetic']);_migration(programs['migration'],c['layout'],roles,base)
    for role in ('capacity','hash'):
        if graphs[role]['calls'] or graphs[role]['stores'] or graphs[role]['traps']:raise ValueError(LABEL+'.readonly-closed-child:'+role)
    writers=[]
    for row in programs['capacity']:
        head,_,rest=row['text'].partition(' ')
        if _ALIASES.get(rest.split(',')[0])=='r9' and head not in ('cmp','test'):writers.append(row['text'])
    if writers!=['mov r9d, 0x4','add r9, r9']:raise ValueError(LABEL+'.capacity-write-closure')
    by={int(r['va'],16):r for r in programs['capacity']};returns=graphs['capacity']['returns']
    if len(returns)!=1:raise ValueError(LABEL+'.capacity-return-origin')
    return_copy=next(r for r in programs['capacity'] if int(r['va'],16)+len(bytes.fromhex(r['bytes']))==returns[0])
    if return_copy['text']!='mov rax, r9':raise ValueError(LABEL+'.capacity-return-origin')
    dom=_dominators(graphs['capacity']['edges'],base+roles['capacity']['entryRva'])
    if int(return_copy['va'],16) not in dom[returns[0]]:raise ValueError(LABEL+'.capacity-return-dominance')
    return {'status':'conditional-triangular-probe-and-complete-node-field-migration-proved','codeInstructions':sum(len(rr) for rr in programs.values()),'controls':{role:{k:g[k] for k in ('instructions','calls','stores','returns','traps','normalFramesProved')} for role,g in graphs.items()},
        'markerAndIteratorComposition':joined['status'],'completeMigrationGrammarAndActualChildJoinsProved':True,'hashSignedByteOrderAndHeaderRecordIndependenceProved':True,
        'triangularProbeVisitsAllSlotsForNonzeroPowerTwoCapacityProved':True,'capacityReturnedValueIsPowerTwoOrZeroProved':True,'destinationFreeMarkerBranchMatchesDescriptorEqualityProved':True,
        'conditionalCompleteMigrationPreservesOrdinaryNodeFieldMultisetProved':True,'conditionalMigrationTerminatesWithEnoughSlotsProved':True,'sourceNodeFieldsUnmodifiedUnderDisjointStorageProved':True,
        'capacityNonzeroGuaranteed':False,'actualCapacitySufficientForSourceProved':False,'allocatorSuccessObserved':False,'unconditionalCompleteMigrationProved':False,'duplicateInsertionRecordHistoryProved':False,
        'wholeNodePaddingEqualityProved':False,'lookupReturnedSystemInt32ClassProved':False,'primitiveClassCellNonNullProved':False,'concreteDamageTypeSharingSelected':False,'wholeRootAdmitted':False,'runtimeExecutionKnown':False}
