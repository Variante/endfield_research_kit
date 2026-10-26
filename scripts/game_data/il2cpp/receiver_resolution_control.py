"""Closed nullable/pointer-index leaves and complete cache resolver control.

Leaf windows are closed instruction programs, not inferred .pdata ownership.
The owned cache resolver checks a sentinel, two fresh cache views, an actual
metadata constructor call/store and a fresh return view. Static value flow
does not equate those views or prove synchronization and actual class identity.
"""
from __future__ import annotations
from .generic_creation_instructions import decode_generic_creation_instructions
from .generic_creation_control import _partition,_graph,_origins
from .field_setup_control import _frames,_projection
from .owned_partition import BranchGrammar,checked_rows,window_bytes
from .relation_import_control import _memory
from .record_index_geometry import prove_record_index_geometry

LABEL='receiverResolutionControl'


def _leaf_rows(index,w):
    start=index.pe.image_base+w['startRva'];raw=window_bytes(index,start,index.pe.image_base+w['endRva'],w['sha256'],LABEL)
    return checked_rows(decode_generic_creation_instructions(index.mapper,raw,start),raw,LABEL)


def _nullable(index,c):
    base=index.pe.image_base;p=c['nullableLeaf'];rows=_leaf_rows(index,p['window']);g=BranchGrammar(rows,label=LABEL)
    g.take('test rcx, rcx');branch=g.branch('je');_memory(g,'load','rcx',8,base='rcx',displacement=0)
    tail=g.branch('jmp')
    if tail['target']!=base+c['indexLeaf']['window']['startRva']:g.fail('nullable-tail','actual pointer-index leaf',tail)
    returned=g.take('ret');zero=g.take('xor eax, eax');back=g.branch('jmp');g.finish()
    if branch['target']!=int(zero['va'],16) or back['target']!=int(returned['va'],16):g.fail('nullable-closed-edges','null -> zero -> shared RET',(branch,back))
    return rows


def _index_bridge(index,c,records):
    base=index.pe.image_base;p=c['indexLeaf'];rows=_leaf_rows(index,p['window']);g=BranchGrammar(rows,label=LABEL)
    _memory(g,'load','rax',8,absolute=base+c['metadataSource']['headerCellRva'])
    row=g.row();f=row.get('dwordSignExtensionOperation',{});a=f.get('sourceAddress',{})
    if (f.get('destinationRegister'),f.get('destinationBits'),f.get('sourceBits'),f.get('memoryReadBytes'),a.get('base'),a.get('index'),a.get('displacement'),a.get('ripRelative'))!=('rdx',64,32,4,'rax',None,c['recordLayout']['headerTypeDefinitionsOffsetField'],False):g.fail('signed-header-offset','fresh signed DWORD section offset',row)
    encoded=p['multiplier']&((1<<64)-1);g.take(f'mov rax, {hex(encoded)}','sub rcx, rdx')
    row=g.row();f=row.get('memorySourceSubtractOperation',{});a=f.get('sourceAddress',{})
    if (f.get('bits'),f.get('destinationRegister'),f.get('memoryReadBytes'),a.get('ripRelative'),a.get('absoluteAddress'))!=(64,'rcx',8,True,base+c['metadataSource']['baseCellRva']):g.fail('fresh-base-subtraction','QWORD fresh metadata base subtracted modulo 2^64',row)
    row=g.row();f=row.get('implicitSignedMultiplyOperation',{})
    if (f.get('bits'),f.get('sourceRegister'),f.get('accumulatorRegister'),f.get('highResultRegister'),f.get('fullProductBits'),f.get('signedOperands'))!=(64,'rcx','rax','rdx',128,True):g.fail('signed-full-product','RDX:RAX signed multiplier * RCX',row)
    g.take('add rdx, rcx',f'sar rdx, 0x{p["shift"]:x}','mov rcx, rdx','shr rcx, 0x3f','add rcx, rdx');tail=g.branch('jmp');g.finish()
    if tail['target']!=base+c['function']['entryRva']:g.fail('index-resolver-tail','actual cache resolver',tail)
    geometry=prove_record_index_geometry(multiplier=p['multiplier'],shift=p['shift'],record_bytes=c['recordLayout']['recordBytes'],records=records)
    return rows,geometry


def _indexed(g,direction,register,base):
    row=g.row();f=row.get('memoryOperation',{});a=f.get('address',{})
    if (f.get('direction'),f.get('register'),f.get('registerBits'),f.get('memoryBytes'),a.get('base'),a.get('index'),a.get('scale'),a.get('displacement'),a.get('ripRelative'))!=(direction,register,64,8,base,'rdi',8,0,False):g.fail('indexed-cache-memory','original QWORD cache[index] move',row)
    return row


def _cache_zero(g):
    row=g.row();f=row.get('memoryImmediateComparisonOperation',{});a=f.get('sourceAddress',{})
    if (f.get('bits'),f.get('memoryReadBytes'),f.get('immediateWord'),f.get('preservesRegisters'),f.get('writesMemory'),a.get('base'),a.get('index'),a.get('scale'),a.get('displacement'),a.get('ripRelative'))!=(64,8,0,True,False,'rax','rdi',8,0,False):g.fail('indexed-cache-zero','QWORD cache[index] compared with zero',row)


def _resolver(rows,base,c,edges):
    f=c['function'];p=f['prefix'];g=BranchGrammar(_projection(rows,base,p['window']),label=LABEL)
    _memory(g,'store','rbx',8,base='rsp',displacement=8);_memory(g,'store','rsi',8,base='rsp',displacement=24)
    g.take('push rdi',f'sub rsp, 0x{f["frameBytes"]:x}');saved=g.take('movsxd rdi, ecx');g.take('cmp edi, -0x1');branch=g.branch('jne');g.finish()
    if branch['target']!=base+f['fastCheck']['window']['startRva']:g.fail('non-sentinel-check','first cache view',branch)
    g=BranchGrammar(_projection(rows,base,f['nullReturnWindow']),label=LABEL);g.take('xor eax, eax')
    _memory(g,'load','rbx',8,base='rsp',displacement=48);_memory(g,'load','rsi',8,base='rsp',displacement=64)
    g.take('add rsp, 0x20','pop rdi','ret');g.finish()
    check_rows=[]
    for name in ('fastCheck','slowCheck'):
        p=f[name];g=BranchGrammar(_projection(rows,base,p['window']),label=LABEL)
        _memory(g,'load','rax',8,absolute=base+c['cacheCellRva']);_cache_zero(g);branch=g.branch('jne');g.finish()
        if branch['target']!=base+p['nonZeroRva']:g.fail('cache-check-continuation',p['nonZeroRva'],branch)
        check_rows.append(base+p['window']['startRva'])
    p=f['creationStore'];g=BranchGrammar(_projection(rows,base,p['window']),label=LABEL)
    copied=g.take('mov ecx, edi');call=g.call(base+c['constructorEntryRva'])
    _memory(g,'load','rcx',8,absolute=base+c['cacheCellRva']);store=_indexed(g,'store','rax','rcx');g.finish()
    g=BranchGrammar(_projection(rows,base,f['cacheReturnWindow']),label=LABEL)
    fresh=_memory(g,'load','rax',8,absolute=base+c['cacheCellRva']);load=_indexed(g,'load','rax','rax')
    _memory(g,'load','rbx',8,base='rsp',displacement=48);_memory(g,'load','rsi',8,base='rsp',displacement=64)
    g.take('add rsp, 0x20','pop rdi','ret');g.finish()
    for name in ('prefix','nullReturnWindow','fastCheck','slowCheck','creationStore','cacheReturnWindow'):
        w=f[name] if name.endswith('Window') else f[name]['window'];block=_projection(rows,base,w)
        for before,row in zip(block,block[1:]):
            at=int(row['va'],16);expected={int(before['va'],16)};actual={a for a,targets in edges.items() if at in targets}
            if actual!=expected:raise ValueError(LABEL+'.projection-interior-entry:'+name+' site='+hex(at-base))
    saved_at=int(saved['va'],16);origins=_origins(rows,edges,base+f['entryRva'],{(saved_at,'rdi'):'signedIncomingDwordIndex'})
    sites=check_rows+[int(copied['va'],16),int(store['va'],16),int(load['va'],16)]
    if any(origins[at]['rdi']!=frozenset(('signedIncomingDwordIndex',)) for at in sites):raise ValueError(LABEL+'.cache-index-origin')
    return {'actualMetadataConstructorCallRva':int(call['va'],16)-base,'constructorResultCacheStoreRva':int(store['va'],16)-base,
        'cacheReturnFreshPointerLoadRva':int(fresh['va'],16)-base,'cacheReturnFreshElementLoadRva':int(load['va'],16)-base,
        'signedIncomingIndexPreservedAcrossCompletePossibleGraphProved':True,'minusOneSentinelReturnsNullProved':True,
        'twoDistinctFreshCacheNullChecksProved':True,'sameSignedIndexPassedToMetadataConstructorAndCacheStoreProved':True,
        'normalConstructorResultStoredIntoFreshCacheArrayProved':True,'normalNonSentinelReturnUsesFreshCacheArrayAndElementProved':True,
        'cacheCheckPublicationAndReturnViewsEqualProved':False,'constructorRunsOnEveryNormalReturnProved':False,
        'actualCacheIndexBoundsAndStorageProved':False,'actualSynchronizationOutcomeProved':False}


def validate_receiver_resolution_control(index,c,*,record_count):
    nullable=_nullable(index,c);bridge,geometry=_index_bridge(index,c,record_count)
    base=index.pe.image_base;f=c['function'];rows=_partition(index,f);edges,calls,stores=_graph(rows,base,f);_frames(rows,edges,base,f)
    summary=_resolver(rows,base,c,edges)
    return {**geometry,**summary,'checkedInstructions':len(nullable)+len(bridge)+len(rows),'closedLeafInstructions':len(nullable)+len(bridge),
        'ownedResolverInstructions':len(rows),'closedLeafBytes':sum(c[k]['window']['endRva']-c[k]['window']['startRva'] for k in ('nullableLeaf','indexLeaf')),
        'ownedResolverBytes':sum(w['endRva']-w['startRva'] for w in f['ownedWindows']),'explicitResolverStores':len(stores),'resolverCallSites':calls,
        'closedNullableAndPointerIndexInstructionProgramsChecked':True,'leafPdataOwnershipInferred':False,
        'completeOwnedResolverControlStoresAndNormalFramesChecked':True,'actualCurrentMetadataConstructorEntryJoined':True,
        'sameMetadataHeaderBaseCellsAndRecordStrideConditionallyRoundTripProved':True,
        'originalIncomingReceiverNullHandlingProved':False,'actualReturnedClassCountEqualsSelectedMetadataWordProved':False,
        'liveSourceClassCachePreparationIdentityProved':False,'childAliasEffectsAndLaterCountCoherenceProved':False,
        'completeTypedResolverEffectsProved':False,'actualArrayCallbackTargetProved':False,'callbackCursorEqualityProved':False,
        'positiveListAdmitted':False,'wholeRootAdmitted':False}
