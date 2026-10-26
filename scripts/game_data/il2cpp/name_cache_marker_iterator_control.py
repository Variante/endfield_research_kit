"""Marker copies, AL equality and conditional finite native iterator filtering.

These programs classify stored sentinel descriptors. They do not identify
metadata records, observe live caches or prove every migration probe terminates.
"""
from __future__ import annotations
from .type_data_initialization_control import _complete
from .method_carrier_control import _Grammar
from .method_carrier_resolution import _memory
from .class_name_lookup_control import _closed_interior
from .name_cache_migration_swap_control import _part
from .class_creation_control import _dominators

LABEL='nameCacheMarkerIteratorControl'

class _SplitGrammar(_Grammar):
    """Keep original coordinates across individually contiguous owned ranges."""
    def __init__(self,rows,*,label):
        parts=[]
        for row in rows:
            if not parts or int(row['va'],16)!=int(parts[-1][-1]['va'],16)+len(bytes.fromhex(parts[-1][-1]['bytes'])):parts.append([])
            parts[-1].append(row)
        super().__init__(parts[0],label=label)
        for part in parts[1:]:_Grammar(part,label=label+'.range')
        # Full CFG/ownership validation precedes this grammar. No gap bytes or
        # local fallthrough across a gap are invented; labels retain actual VAs.
        self.rows=rows

def marker_al(left_header,right_header,left_namespace=None,right_namespace=None,left_name=None,right_name=None):
    """AL-only model of the proved program, with lazy selected CString reads."""
    if any(type(h) is not int or not 0<=h<1<<32 for h in (left_header,right_header)):raise ValueError(LABEL+'.header-domain')
    if left_header!=right_header:return 0
    if left_header:return 1
    def string(v):
        if not isinstance(v,(bytes,bytearray)) or 0 not in v:raise ValueError(LABEL+'.selected-cstring-domain')
        return bytes(v).split(b'\0',1)[0]
    if string(left_namespace)!=string(right_namespace):return 0
    return int(string(left_name)==string(right_name))

def initializer_slot_count(start,end,*,stride=32):
    """Finite nonwrapping range theorem; the native code does not reject others."""
    if any(type(v) is not int for v in (start,end,stride)) or stride<=0 or not 0<=start<=end<1<<64 or (end-start)%stride:
        raise ValueError(LABEL+'.conditional-initializer-range')
    return (end-start)//stride

def select_slot(nodes,start,end,free_descriptor,removed_descriptor=None,*,scan=True):
    """First non-marker or end. An occupied input cursor is not advanced."""
    if any(type(v) is not int for v in (start,end)) or not 0<=start<=end<=len(nodes):raise ValueError(LABEL+'.conditional-slot-range')
    if start==end or not scan:return start
    def match(descriptor,node):
        return marker_al(descriptor[0],node[0],descriptor[1],node[1],descriptor[2],node[2])
    cursor=start
    while cursor<end:
        node=nodes[cursor]
        if not match(free_descriptor,node) and (removed_descriptor is None or not match(removed_descriptor,node)):return cursor
        cursor+=1
    return end

def _byte_loop(g,*,delta,left,right,label,failed):
    g.mark(label)
    g.take(f'movzx {left}, byte [rax]',f'movzx {right}, byte [rax+{delta}*1]',f'sub {left}, {right}')
    g.branch('jne',label+'Done');g.take('inc rax',f'test {right}, {right}');g.branch('jne',label)
    g.mark(label+'Done');g.take(f'test {left}, {left}');g.branch('jne',failed)

def _predicate(rows,l):
    g=_Grammar(rows,label=LABEL+'.predicate');_memory(g,'load','eax',4,'r8',l['nodeHeader']);g.take('mov r9, r8','cmp dword [rdx], eax');g.branch('jne','false')
    g.take('cmp dword [rdx], 0x0');g.branch('jne','true')
    _memory(g,'load','rax',8,'rdx',l['nodeNamespace']);_memory(g,'load','r10',8,'r8',l['nodeNamespace']);g.take('sub r10, rax')
    _byte_loop(g,delta='r10',left='ecx',right='r8d',label='namespace',failed='false')
    _memory(g,'load','rax',8,'rdx',l['nodeName']);_memory(g,'load','r8',8,'r9',l['nodeName']);g.take('sub r8, rax')
    _byte_loop(g,delta='r8',left='ecx',right='edx',label='name',failed='false')
    g.mark('true');g.take('mov al, 0x1','ret');g.mark('false');g.take('xor al, al','ret');g.finish()

def _initializer(rows,l):
    g=_Grammar(rows,label=LABEL+'.initializer');g.take('cmp rdx, r8');g.branch('je','return');g.mark('copy')
    _memory(g,'load','eax',4,'rcx',l['cacheFreeHeader']);_memory(g,'store','eax',4,'rdx',l['nodeHeader'])
    _memory(g,'load','xmm0',16,'rcx',l['cacheFreeStrings']);_memory(g,'store','xmm0',16,'rdx',l['nodeNamespace'])
    _memory(g,'load','rax',8,'rcx',l['cacheFreeRecord']);_memory(g,'store','rax',8,'rdx',l['nodeRecord'])
    g.take(f'add rdx, 0x{l["nodeBytes"]:x}','cmp rdx, r8');g.branch('jne','copy');g.mark('return');g.take('ret');g.finish()

def _iterator(rows,l,*,create,predicate_entry):
    g=_SplitGrammar(rows,label=LABEL+'.'+('create' if create else 'next'))
    if create:
        _memory(g,'store','rbx',8,'rsp',8);g.take('push rdi','sub rsp, 0x20');_memory(g,'store','rdx',8,'rcx',l['iteratorCache']);g.take('mov rdi, r9');_memory(g,'store','r8',8,'rcx',l['iteratorCursor']);g.take('mov rbx, rdx');_memory(g,'store','r9',8,'rcx',l['iteratorEnd']);g.take('mov r11, rcx','cmp r8, r9');g.branch('je','restore')
        g.take(f'cmp byte [rsp+0x{l["calleeScanByte"]:x}], 0x0');g.branch('je','restore')
    else:
        g.take('sub rsp, 0x28');_memory(g,'load','rax',8,'rcx',l['iteratorEnd']);g.take('mov r11, rcx',f'cmp qword [rcx+0x{l["iteratorCursor"]:x}], rax');g.branch('je','finish')
        _memory(g,'store','rbx',8,'rsp',48);_memory(g,'load','rbx',8,'rcx',l['iteratorCache']);_memory(g,'store','rdi',8,'rsp',32);g.take('mov rdi, rax')
    g.mark('scan');_memory(g,'load','r9',8,'r11',l['iteratorCursor']);_memory(g,'load','eax',4,'r9',l['nodeHeader']);g.take(f'cmp dword [rbx+0x{l["cacheFreeHeader"]:x}], eax');g.branch('jne','notFree')
    g.take(f'cmp dword [rbx+0x{l["cacheFreeHeader"]:x}], 0x0');g.branch('je','freeStrings')
    g.mark('advance');g.take(f'add [r11+0x{l["iteratorCursor"]:x}], 0x{l["nodeBytes"]:x}',f'cmp qword [r11+0x{l["iteratorCursor"]:x}], rdi');g.branch('jne','scan');g.branch('jmp','restore')
    g.mark('notFree');g.take(f'cmp qword [rbx+0x{l["cacheRemovedCount"]:x}], 0x0');g.branch('ja','removed')
    g.mark('restore');_memory(g,'load','rbx',8,'rsp',48)
    if create:g.take('mov rax, r11','add rsp, 0x20','pop rdi','ret')
    else:_memory(g,'load','rdi',8,'rsp',32);g.mark('finish');g.take('add rsp, 0x28','ret')
    g.mark('freeStrings');_memory(g,'load','rax',8,'rbx',l['cacheFreeStrings']);_memory(g,'load','r8',8,'r9',l['nodeNamespace']);g.take('sub r8, rax','nop')
    _byte_loop(g,delta='r8',left='edx',right='ecx',label='freeNamespace',failed='notFree')
    _memory(g,'load','rax',8,'rbx',l['cacheFreeStrings']+8);_memory(g,'load','r8',8,'r9',l['nodeName']);g.take('sub r8, rax')
    g.mark('freeName');g.take('movzx edx, byte [rax]','movzx ecx, byte [rax+r8*1]','sub edx, ecx');g.branch('jne','freeNameDone');g.take('inc rax','test ecx, ecx');g.branch('jne','freeName');g.mark('freeNameDone');g.take('test edx, edx');g.branch('je','advance');g.branch('jmp','notFree')
    g.mark('removed');g.take(f'lea rdx, [rbx+0x{l["cacheRemovedDescriptor"]:x}]','mov r8, r9');g.call(predicate_entry);g.take('test al, al');g.branch('je','restore');g.branch('jmp','advance');g.finish()

def validate_name_cache_marker_iterator(programs,*,image_base,contract):
    c=contract;base=image_base;roles=c['functions'];required={'nodeInitializer','iteratorPredicate','allocation','iteratorCreate','iteratorNext','migration'}
    if set(programs)!=required or set(roles)!=required:raise ValueError(LABEL+'.function-membership')
    l=c['layout'];p=c['projections'];graphs={role:_complete(rr,base+roles[role]['entryRva']) for role,rr in programs.items()}
    if (l['nodeBytes'],l['nodeHeader'],l['nodeNamespace'],l['nodeName'],l['nodeRecord'])!=(32,0,8,16,24):raise ValueError(LABEL+'.node-layout')
    for role in ('nodeInitializer','iteratorPredicate'):
        if graphs[role]['calls'] or graphs[role]['traps']:raise ValueError(LABEL+'.closed-child-call-or-trap')
    _initializer(programs['nodeInitializer'],l);_predicate(programs['iteratorPredicate'],l)
    predicate_entry=base+roles['iteratorPredicate']['entryRva']
    for role,create in (('iteratorCreate',True),('iteratorNext',False)):
        _iterator(programs[role],l,create=create,predicate_entry=predicate_entry)
        if len(graphs[role]['calls'])!=1 or graphs[role]['calls'][0]['target']!=predicate_entry:raise ValueError(LABEL+'.iterator-only-readonly-child')
    # Strict whole-child grammars contain no R11 or nonvolatile register writes;
    # predicate has no memory stores. This proves the caller's volatile iterator
    # pointer survives its actual child, rather than assuming normal ABI does it.
    if graphs['iteratorPredicate']['stores']:raise ValueError(LABEL+'.predicate-unexpected-store')
    block=_part(programs['allocation'],base,p['allocationOrigins']);g=_Grammar(block,label=LABEL+'.allocationOrigins');g.take('mov rdi, rdx','mov rbx, rcx');g.finish()
    origin_sites={int(r['va'],16) for r in block};target=base+p['allocationInitAndReset']['startRva'];dom=_dominators(graphs['allocation']['edges'],base+roles['allocation']['entryRva'])
    if not origin_sites<=dom[target]:raise ValueError(LABEL+'.allocation-origin-dominance')
    ancestors={target};pending=[target];edges=graphs['allocation']['edges']
    while pending:
        at=pending.pop()
        for predecessor,destinations in edges.items():
            if at in destinations and predecessor not in ancestors:ancestors.add(predecessor);pending.append(predecessor)
    for row in programs['allocation']:
        at=int(row['va'],16);head,_,rest=row['text'].partition(' ')
        if at in ancestors and at not in origin_sites and head in ('mov','and','xor','add','sub','pop') and rest.split(',')[0] in ('rbx','ebx','rdi','edi'):
            raise ValueError(LABEL+'.allocation-origin-clobber')
    block=_part(programs['allocation'],base,p['allocationInitAndReset']);g=_Grammar(block,label=LABEL+'.allocationInit')
    _memory(g,'load','rdx',8,'rbx',l['cacheNodes']);g.take('mov r8, rdi','shl r8, 0x5','mov rcx, rbx',f'add r8, qword [rbx+0x{l["cacheNodes"]:x}]');g.call(base+roles['nodeInitializer']['entryRva']);g.take('xor ecx, ecx');_memory(g,'store','rdi',8,'rbx',l['cacheCapacity']);_memory(g,'store','rcx',8,'rbx',l['cacheUsedCount']);g.take('xorps xmm0, xmm0');_memory(g,'store','rcx',8,'rbx',l['cacheRemovedCount']);g.finish()
    _closed_interior(programs['allocation'],graphs['allocation']['edges'],base,{'window':p['allocationInitAndReset']})
    if l['calleeScanByte']-l['createEntryToBodyStackDelta']-8!=l['callerScanByte'] or l['createEntryToBodyStackDelta']!=40:raise ValueError(LABEL+'.scan-byte-call-frame-geometry')
    for key,iterator_offset,end in (('migrationBegin',l['callerBeginIterator'],False),('migrationEnd',l['callerEndIterator'],True)):
        block=_part(programs['migration'],base,p[key]);g=_Grammar(block,label=LABEL+'.'+key);_memory(g,'load','r9',8,'rbx',l['cacheCapacity']);g.take(f'lea rcx, [rsp+0x{iterator_offset:x}]')
        _memory(g,'load','r8',8,'rbx',l['cacheCapacity'] if end else l['cacheNodes']);g.take('mov rdx, rbx','shl r9, 0x5',f'add r9, qword [rbx+0x{l["cacheNodes"]:x}]')
        if end:g.take('shl r8, 0x5',f'add r8, qword [rbx+0x{l["cacheNodes"]:x}]')
        g.take(f'mov byte [rsp+0x{l["callerScanByte"]:x}], 0x1');g.call(base+roles['iteratorCreate']['entryRva'])
        if not end:g.take('nop')
        g.finish();_closed_interior(programs['migration'],graphs['migration']['edges'],base,{'window':p[key]})
    block=_part(programs['migration'],base,p['migrationAdvance']);g=_Grammar(block,label=LABEL+'.migrationAdvance');g.take(f'add rdi, 0x{l["nodeBytes"]:x}');_memory(g,'store','rax',8,'r9',l['nodeRecord']);g.take(f'inc qword [rsi+0x{l["cacheUsedCount"]:x}]');_memory(g,'store','rdi',8,'rsp',l['callerBeginIterator']+l['iteratorCursor']);g.call(base+roles['iteratorNext']['entryRva']);jump=g.branch('jmp');g.finish()
    if jump['target']!=base+p['migrationEnd']['startRva']:raise ValueError(LABEL+'.migration-end-refresh-backedge')
    return {'status':'marker-initialization-al-comparison-and-finite-iterator-selection-proved','codeInstructions':sum(len(rr) for rr in programs.values()),'controls':{role:{k:g[k] for k in ('instructions','calls','stores','returns','traps','normalFramesProved')} for role,g in graphs.items()},
        'initializerCopiesFreeHeaderStringsAndAuxiliaryPerSlotProved':True,'initializerLeavesFourNodeGapBytesUnwrittenProved':True,'initializerFiniteForValidNonwrappingAlignedRangeProved':True,
        'predicateAlIsHeaderAndConditionalCStringEqualityProved':True,'predicateRecordAndNodeGapBytesIgnoredProved':True,'predicatePreservesR11RbxRdiAndMemoryProved':True,'predicateWholeRaxBooleanProved':False,
        'allocationInitializerArgumentsAndCountResetJoined':True,'iteratorCompleteMarkerFiltersAndReadonlyChildJoined':True,'iteratorSelectsFirstNonMarkerOrEndUnderStableFiniteInputsProved':True,'occupiedInputCursorIsNotAdvancedByNextProved':True,
        'migrationBeginEndAndScanByteGeometryJoined':True,'migrationAdvancesBeforeNextAndRefreshesEndJoined':True,
        'allocatorSuccessObserved':False,'invalidInitializerRangeRejectedByNativeProved':False,'allOccupiedNodesMigratedProved':False,'duplicateRecordHistoryProved':False,'hashCapacityOrProbeTerminationProved':False,
        'lookupReturnedSystemInt32ClassProved':False,'primitiveClassCellNonNullProved':False,'concreteDamageTypeSharingSelected':False,'wholeRootAdmitted':False,'runtimeExecutionKnown':False}
