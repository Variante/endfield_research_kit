"""Complete metadata-record construction control with selected count origins.

Physical source/allocation/count/return projections are conditional. Unknown
aliases, child effects, runtime metadata/class/cache identity remain open.
"""
from __future__ import annotations
from .class_creation_instructions import decode_class_creation_instructions
from .field_setup_control import _graph,_frames,_projection,setup_memory_effect
from .initializer_control import _ALIASES,control_transfer
from .owned_partition import BranchGrammar,owned_windows,checked_rows,check_byte_partition
from .relation_import_control import _memory

LABEL='classCreationControl'


def _word_load(g,destination,register,offset):
    r=g.row();f=r.get('wordZeroExtensionOperation',{});a=f.get('sourceAddress',{})
    if (f.get('destinationRegister'),f.get('destinationBits'),f.get('sourceBits'),f.get('memoryReadBytes'),a.get('base'),a.get('index'),a.get('displacement'),a.get('ripRelative'))!=(destination,32,16,2,register,None,offset,False):
        g.fail('word-source','unsigned word memory to DWORD register',r)
    return r


def _dominators(edges,entry):
    nodes=set(edges);predecessors={n:set() for n in nodes}
    for n,targets in edges.items():
        for t in targets:predecessors[t].add(n)
    dom={n:({entry} if n==entry else set(nodes)) for n in nodes};changed=True
    while changed:
        changed=False
        for n in sorted(nodes-{entry}):
            if not predecessors[n]:raise ValueError(LABEL+'.unreachable-predecessor')
            value={n}|set.intersection(*(dom[p] for p in predecessors[n]))
            if value!=dom[n]:dom[n]=value;changed=True
    return dom


def _prefix(rows,base,c,f):
    p=f['sourceAllocationPrefix'];layout=c['recordLayout'];g=BranchGrammar(_projection(rows,base,p['window']),label=LABEL)
    for register in ('rbx','rbp','rsi','rdi'):_memory(g,'store',register,8,base='rsp',displacement=f['entrySavedHomes'][register])
    g.take('push r14',f'sub rsp, 0x{f["frameBytes"]:x}')
    _memory(g,'load','rax',8,absolute=base+p['headerPointerCellRva']);g.take('movsxd rsi, ecx')
    _memory(g,'load','rcx',8,absolute=base+p['allocatorContextCellRva'])
    g.take(f'imul rdi, rsi, 0x{layout["recordBytes"]:x}')
    r=g.row();fact=r.get('dwordSignExtensionOperation',{});address=fact.get('sourceAddress',{})
    if (fact.get('destinationRegister'),fact.get('destinationBits'),fact.get('sourceBits'),fact.get('memoryReadBytes'),address.get('base'),address.get('index'),address.get('displacement'),address.get('ripRelative'))!=('rdx',64,32,4,'rax',None,layout['headerTypeDefinitionsOffsetField'],False):g.fail('header-offset','signed DWORD table offset from fresh header pointer',r)
    r=g.row();fact=r.get('sourceArithmeticOperation',{});address=fact.get('sourceAddress',{})
    if (fact.get('operation'),fact.get('destinationRegister'),fact.get('bits'),fact.get('memoryReadBytes'),address.get('ripRelative'),address.get('absoluteAddress'))!=('add','rdx',64,8,True,base+p['metadataBaseCellRva']):g.fail('metadata-base','fresh global QWORD base added to table offset',r)
    _memory(g,'load','rax',8,absolute=base+p['registrationCellRva']);g.take('add rdi, rdx')
    _memory(g,'load','rdx',8,base='rax',displacement=p['registrationArrayOffset'])
    _word_load(g,'r8d','rdi',layout['vtableCountWordOffset'])
    g.take(f'add r8, 0x{p["allocationBias"]:x}',f'shl r8, 0x{p["allocationShift"]:x}',f'mov r14, [rdx+rsi*{p["registrationIndexScale"]}]','mov edx, 0x1')
    call=g.call(base+c['allocatorEntryJoin']['entryRva'])
    _memory(g,'load','r9d',4,absolute=base+p['followingCountCellRva']);g.take('xor ebp, ebp','mov rbx, rax');g.finish()
    return int(call['va'],16)


def validate_class_creation_control(index,c):
    base=index.pe.image_base;f=c['function'];owned,pieces,windows=owned_windows(index,f,LABEL);rows=[]
    if f['paddingWindows']:raise ValueError(LABEL+'.unreviewed-padding')
    for _,_,start,raw in windows:rows.extend(checked_rows(decode_class_creation_instructions(index.mapper,raw,start),raw,LABEL))
    rows.sort(key=lambda r:int(r['va'],16));check_byte_partition(owned,pieces,LABEL)
    if len(rows)!=f['checkedInstructionCount']:raise ValueError(LABEL+'.instruction-count')
    edges,calls,stores=_graph(rows,base,f);_frames(rows,edges,base,f)
    allocation=_prefix(rows,base,c,f);p=f['countCopy'];g=BranchGrammar(_projection(rows,base,p['window']),label=LABEL)
    load=_word_load(g,'eax','rdi',c['recordLayout']['fieldCountWordOffset']);store=_memory(g,'store','ax',2,base='rbx',displacement=c['classFieldCount']);g.finish()
    source=int(load['va'],16);count_store=int(store['va'],16);bound=base+f['sourceAllocationPrefix']['window']['endRva']
    g=BranchGrammar(_projection(rows,base,f['returnWindow']),label=LABEL)
    frame=f['frameBytes']+8
    _memory(g,'load','rbp',8,base='rsp',displacement=frame+f['entrySavedHomes']['rbp']);r=g.row()
    if r['text']!='mov rax, rbx':g.fail('allocated-result-return','MOV RAX, saved allocation result RBX',r)
    return_result=int(r['va'],16)
    for register in ('rbx','rsi','rdi'):_memory(g,'load',register,8,base='rsp',displacement=frame+f['entrySavedHomes'][register])
    g.take(f'add rsp, 0x{f["frameBytes"]:x}','pop r14','ret');g.finish()
    for r in rows:
        at=int(r['va'],16)
        if at<bound or control_transfer(r)['kind']!='next':continue
        head,_,rest=r['text'].partition(' ');parent=_ALIASES.get(rest.split(',')[0])
        if head not in ('cmp','test','bt','nop') and ((parent=='rdi' and at<source) or (parent=='rbx' and at<return_result)):
            raise ValueError(LABEL+'.saved-source-or-result-overwritten:'+r['bytes'])
    dom=_dominators(edges,base+f['entryRva'])
    if not f['returnRvas'] or any(allocation not in dom[base+r] or count_store not in dom[base+r] for r in f['returnRvas']):raise ValueError(LABEL+'.allocation-and-count-dominance')
    writes=[]
    for s in stores:
        facts=s['facts'];a=facts.get('address',facts.get('destinationAddress',{}));size=facts.get('memoryBytes',facts.get('memoryWriteBytes'))
        if a.get('base')=='rbx' and a.get('index') is None and not a.get('ripRelative') and a['displacement']<c['classFieldCount']+2 and c['classFieldCount']<a['displacement']+size:writes.append(s['siteRva'])
    if writes!=[count_store-base]:raise ValueError(LABEL+'.direct-count-store-inventory')
    return {'checkedInstructions':len(rows),'ownedBytes':sum(b-a for a,b in owned),'explicitStores':len(stores),'callSites':calls,
        'completeOwnedCfgAndNormalFrameGeometryProved':True,'selectedSignedIndexHeaderAndMetadataBaseAddressFormulaProved':True,
        'sourceRecordAddressFormula':'signedIncomingDwordIndex * recordBytes + signedHeaderTableOffset + freshGlobalMetadataBase modulo 2^64',
        'savedSourceAndAllocationResultRegistersPreservedUntilCountReadProved':True,'freshSourceWordCopiedIntoNamedCountOffsetProved':True,
        'allocationAndCountCopyDominateEveryNormalLocalReturnProved':True,'allocationResultReturnOriginConditionallyProved':True,
        'allDirectUnindexedRbxStoresOverlappingCountAreSelectedCopyProved':True,
        'sourceIndexInMetadataBoundsProved':False,'actualGlobalMetadataHeaderAndTablePointersProved':False,
        'actualAllocatedClassCacheAndPreparationReceiverIdentityProved':False,'completeTypedCreationEffectsProved':False,
        'countUnchangedByChildOrAliasEffectsProved':False,'creationCountEqualsLaterPreparationCountProved':False,
        'allocationCapacityAndInitializationOutcomeProved':False,'positiveListAdmitted':False,'wholeRootAdmitted':False}
