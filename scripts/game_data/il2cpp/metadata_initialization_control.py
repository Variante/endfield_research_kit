"""Complete owned initialization control and selected metadata/cache stores.

The loader's normal result is published to the actual header/base cells.
A fresh header size supplies a proved conditional cache-allocation quotient;
the indirect call's result is stored in the cache cell used by the resolver.
Global stability, pointer identity, loader/allocator outcomes and child alias
effects remain open. Other initializer stores have only physical inventory.
"""
from __future__ import annotations
from scripts.game_data.il2cpp.metadata_initialization_instructions import decode_metadata_initialization_instructions
from scripts.game_data.il2cpp.metadata_cache_geometry import prove_metadata_cache_geometry
from scripts.game_data.il2cpp.owned_partition import BranchGrammar,owned_windows,checked_rows,check_byte_partition
from scripts.game_data.il2cpp.field_setup_control import _graph,_frames,_projection
from scripts.game_data.il2cpp.class_creation_control import _dominators
from scripts.game_data.il2cpp.relation_import_control import _memory

LABEL='metadataInitializationControl'


def _signed_size(g,destination,source,offset):
    row=g.row();f=row.get('dwordSignExtensionOperation',{});a=f.get('sourceAddress',{})
    if (f.get('destinationRegister'),f.get('destinationBits'),f.get('sourceBits'),f.get('memoryReadBytes'),a.get('base'),a.get('index'),a.get('displacement'),a.get('ripRelative'))!=(destination,64,32,4,source,None,offset,False):
        g.fail('signed-header-size','signed DWORD header read at selected offset',row)
    return row


def validate_metadata_initialization_control(index,c,*,section_bytes,record_count):
    base=index.pe.image_base;f=c['function'];owned,pieces,windows=owned_windows(index,f,LABEL);rows=[]
    if f['paddingWindows']:raise ValueError(LABEL+'.unreviewed-padding')
    for _,_,start,raw in windows:rows.extend(checked_rows(decode_metadata_initialization_instructions(index.mapper,raw,start),raw,LABEL))
    check_byte_partition(owned,pieces,LABEL);rows.sort(key=lambda r:int(r['va'],16))
    if len(rows)!=f['checkedInstructionCount']:raise ValueError(LABEL+'.instruction-count')
    edges,calls,stores=_graph(rows,base,f);_frames(rows,edges,base,f)
    p=f['prefix'];g=BranchGrammar(_projection(rows,base,p['window']),label=LABEL)
    g.take(f'sub rsp, 0x{f["frameBytes"]:x}');loader=g.call(base+c['loaderEntryRva'])
    base_store=_memory(g,'store','rax',8,absolute=base+c['metadataSource']['baseCellRva'])
    g.take('mov rcx, rax','test rax, rax');null=g.branch('je')
    if null['target']!=base+f['nullJumpWindow']['startRva']:g.fail('null-loader-edge','shared restore without further calls',null)
    _signed_size(g,'rdx','rax',p['preHeaderReadOffset'])
    header_store=_memory(g,'store','rax',8,absolute=base+c['metadataSource']['headerCellRva']);g.finish()
    p=f['cacheAllocation'];g=BranchGrammar(_projection(rows,base,p['window']),label=LABEL)
    fresh=_memory(g,'load','rax',8,absolute=base+c['metadataSource']['headerCellRva'])
    size=_signed_size(g,'rcx','rax',c['recordLayout']['headerTypeDefinitionsOffsetField']+4)
    g.take(f'mov rax, {hex(p["multiplier"])}');row=g.row();m=row.get('implicitUnsignedMultiplyOperation',{})
    if (m.get('bits'),m.get('sourceRegister'),m.get('accumulatorRegister'),m.get('lowResultRegister'),m.get('highResultRegister'),m.get('fullProductBits'),m.get('unsignedOperands'),m.get('writesMemory'))!=(64,'rcx','rax','rax','rdx',128,True,False):
        g.fail('unsigned-full-product','RDX:RAX = unsigned RAX * RCX',row)
    allocator=_memory(g,'load','rax',8,absolute=base+c['allocatorCellRva'])
    g.take('sub rcx, rdx','shr rcx, 0x1','add rcx, rdx','mov edx, 0x8',f'shr rcx, 0x{p["shift"]:x}')
    call=g.take('call rax');cache_store=_memory(g,'store','rax',8,absolute=base+c['cacheCellRva']);g.finish()
    g=BranchGrammar(_projection(rows,base,f['successWindow']),label=LABEL)
    g.call(base+c['postInitializeEntryRva']);g.take('mov al, 0x1');g.finish()
    g=BranchGrammar(_projection(rows,base,f['restoreWindow']),label=LABEL)
    g.take(f'add rsp, 0x{f["frameBytes"]:x}','ret');g.finish()
    g=BranchGrammar(_projection(rows,base,f['nullJumpWindow']),label=LABEL);jump=g.branch('jmp');g.finish()
    if jump['target']!=base+f['restoreWindow']['startRva']:g.fail('null-restore-edge','shared normal restore',jump)
    for name in ('prefix','cacheAllocation','successWindow','restoreWindow','nullJumpWindow'):
        w=f[name] if name.endswith('Window') else f[name]['window'];block=_projection(rows,base,w)
        for before,row in zip(block,block[1:]):
            at=int(row['va'],16)
            if {a for a,targets in edges.items() if at in targets}!={int(before['va'],16)}:
                raise ValueError(LABEL+'.projection-interior-entry:'+name)
    dom=_dominators(edges,base+f['entryRva']);fresh_at=int(fresh['va'],16);store_at=int(cache_store['va'],16)
    if int(header_store['va'],16) not in dom[fresh_at] or store_at not in dom[base+f['successWindow']['startRva']]:
        raise ValueError(LABEL+'.selected-publication-dominance')
    selected={base+c['metadataSource']['baseCellRva']:int(base_store['va'],16)-base,
        base+c['metadataSource']['headerCellRva']:int(header_store['va'],16)-base,base+c['cacheCellRva']:store_at-base}
    actual={cell:[] for cell in selected}
    for store in stores:
        a=store['facts'].get('address',store['facts'].get('destinationAddress',{}));cell=a.get('absoluteAddress')
        if a.get('ripRelative') and cell in actual:actual[cell].append(store['siteRva'])
    if any(actual[cell]!=[site] for cell,site in selected.items()):raise ValueError(LABEL+'.selected-cell-store-inventory')
    geometry=prove_metadata_cache_geometry(multiplier=p['multiplier'],shift=p['shift'],record_bytes=c['recordLayout']['recordBytes'],section_bytes=section_bytes,record_count=record_count)
    return {**geometry,'checkedInstructions':len(rows),'ownedBytes':sum(b-a for a,b in owned),'explicitStores':len(stores),'callSites':calls,
        'loaderCallRva':int(loader['va'],16)-base,'metadataBaseStoreRva':int(base_store['va'],16)-base,
        'metadataHeaderStoreRva':int(header_store['va'],16)-base,'freshHeaderReadRva':fresh_at-base,
        'freshTypeDefinitionSizeReadRva':int(size['va'],16)-base,'allocatorPointerReadRva':int(allocator['va'],16)-base,
        'cacheAllocatorCallRva':int(call['va'],16)-base,'cacheResultStoreRva':store_at-base,
        'completeOwnedInitializationControlStoresAndNormalFramesChecked':True,
        'normalLoaderResultPublishedToSameMetadataBaseAndHeaderCellsProved':True,
        'nullLoaderResultPublishesZeroBaseAndReturnsZeroWithoutCacheSetupProved':True,
        'freshHeaderSignedSizeSuppliesCacheAllocationCountConditionallyProved':True,
        'freshAllocatorPointerReceivesSelectedCountAndEightByteStrideProved':True,
        'normalIndirectAllocatorResultPublishedToResolverCacheCellProved':True,
        'normalSuccessReturnSetsOnlyAlToOneProved':True,'allGlobalWritersDiscovered':False,
        'actualLoadedMetadataSourceIdentityProved':False,'liveHeaderAndCacheGlobalStabilityProved':False,
        'actualAllocatorTargetAndAllocationOutcomeProved':False,'allChildAliasEffectsProved':False,
        'actualReturnedClassCountEqualsSelectedMetadataWordProved':False,'positiveListAdmitted':False,'wholeRootAdmitted':False}
