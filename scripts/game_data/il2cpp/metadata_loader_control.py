"""Owned loader/path-helper control and selected source/result programs.

Literal bytes and pointer/length descriptors reach the actual shared helper
and candidate-open call. Complete normal control returns zero or the saved
mapping-child result according to observed status/close/error guards. Child
string/open/map effects, live imports, file identity and global stability are
unresolved. Closed mapping/default-allocator transfers infer no ownership.
"""
from __future__ import annotations
from collections import deque
from scripts.game_data.il2cpp.metadata_initialization_instructions import decode_metadata_initialization_instructions
from scripts.game_data.il2cpp.owned_partition import BranchGrammar,owned_windows,checked_rows,check_byte_partition,window_bytes
from scripts.game_data.il2cpp.field_setup_control import _graph,_frames,_projection
from scripts.game_data.il2cpp.field_construction_control import _lea
from scripts.game_data.il2cpp.relation_import_control import _memory,_import
from scripts.game_data.il2cpp.generic_creation_control import _overwrites
from scripts.game_data.il2cpp.initializer_control import control_transfer
from scripts.game_data.il2cpp.pe_imports import resolve_named_import_slots

LABEL='metadataLoaderControl'


def _partition(index,f):
    base=index.pe.image_base;owned,pieces,windows=owned_windows(index,f,LABEL);rows=[]
    for kind,w,start,raw in windows:
        if kind=='paddingWindows':
            if raw!=b'\xcc' or w.get('rawHex')!='cc':raise ValueError(LABEL+'.padding-value')
        else:rows.extend(checked_rows(decode_metadata_initialization_instructions(index.mapper,raw,start),raw,LABEL))
    check_byte_partition(owned,pieces,LABEL);rows.sort(key=lambda r:int(r['va'],16))
    if len(rows)!=f['checkedInstructionCount']:raise ValueError(LABEL+'.instruction-count')
    edges,calls,stores=_graph(rows,base,f);states=_frames(rows,edges,base,f)
    return rows,edges,calls,stores,states


def _origins(rows,edges,entry,definitions):
    # Nonvolatile register origins under normal Win64 callees. Partial writes
    # invalidate a saved value too; no memory/alias preservation is inferred.
    registers=('rbx','rsi','rdi');unknown=frozenset((None,));by_at={int(r['va'],16):r for r in rows}
    states={entry:(unknown,)*3};pending=deque((entry,))
    while pending:
        at=pending.popleft();row=by_at[at];value=list(states[at]);kind=control_transfer(row)['kind']
        for n,register in enumerate(registers):
            if kind=='next' and _overwrites(row,register):value[n]=unknown
            if (at,register) in definitions:value[n]=frozenset((definitions[at,register],))
        for target in edges[at]:
            old=states.get(target);new=tuple(value) if old is None else tuple(a|b for a,b in zip(old,value))
            if new!=old:states[target]=new;pending.append(target)
    return {at:dict(zip(registers,value)) for at,value in states.items()}


def _block(rows,base,f,key):
    w=f[key] if key.endswith('Window') else f[key]['window']
    return BranchGrammar(_projection(rows,base,w),label=LABEL)


def _literals(index,c,rows):
    base=index.pe.image_base;f=c['loader'];results=[]
    for key in ('directory','fileName'):
        literal=c['literals'][key];raw=window_bytes(index,base+literal['rva'],base+literal['rva']+literal['bytes'],literal['sha256'],LABEL)
        if raw!=literal['text'].encode('ascii') or len(raw)!=literal['bytes']:raise ValueError(LABEL+'.literal-bytes')
        g=_block(rows,base,f,key+'Descriptor');_lea(g,'rax',rip=base+literal['rva'])
        _memory(g,'store','rax',8,base='rbp',displacement=-89);g.take(f'mov qword [rbp-0x51], 0x{literal["bytes"]:x}');g.finish()
        results.append({'text':literal['text'],'bytes':literal['bytes'],'actualDescriptorPointerAndLengthWritesChecked':True})
    for key in ('directoryArguments','fileNameArguments'):
        p=f[key];g=_block(rows,base,f,key)
        _lea(g,'r8',base='rbp',displacement=-89);_lea(g,'rdx',base='rbp',displacement=-121)
        _lea(g,'rcx',base='rbp',displacement=p['destinationOffset']);g.call(base+c['pathHelper']['entryRva']);g.finish()
    return results


def _path_helper(rows,base,c):
    f=c['pathHelper'];g=BranchGrammar(rows,label=LABEL)
    _memory(g,'store','rbx',8,base='rsp',displacement=16);_memory(g,'store','rsi',8,base='rsp',displacement=24)
    _memory(g,'store','rcx',8,base='rsp',displacement=8)
    g.take('push rdi','sub rsp, 0x30','mov rdi, r8','mov rbx, rdx','mov rsi, rcx','xor eax, eax')
    _memory(g,'store','eax',4,base='rsp',displacement=32)
    g.take('xorps xmm0, xmm0','movups [rcx], xmm0');_memory(g,'store','rax',8,base='rcx',displacement=16)
    g.take('mov qword [rcx+0x18], 0xf','mov [rcx], al','mov dword [rsp+0x20], 0x1')
    _memory(g,'load','rcx',8,base='rdx',displacement=8);_memory(g,'load','rdx',8,base='r8',displacement=8)
    g.take('inc rcx','add rdx, rcx','mov rcx, rsi');g.call(base+f['reserveEntryRva'])
    _memory(g,'load','r8',8,base='rbx',displacement=8);_memory(g,'load','rdx',8,base='rbx',displacement=0)
    g.take('mov rcx, rsi');g.call(base+f['appendEntryRva'])
    g.take('mov r8b, 0x5c','mov edx, 0x1','mov rcx, rsi');g.call(base+f['separatorEntryRva'])
    _memory(g,'load','r8',8,base='rdi',displacement=8);_memory(g,'load','rdx',8,base='rdi',displacement=0)
    g.take('mov rcx, rsi');g.call(base+f['appendEntryRva']);g.take('mov rax, rsi')
    _memory(g,'load','rbx',8,base='rsp',displacement=72);_memory(g,'load','rsi',8,base='rsp',displacement=80)
    g.take('add rsp, 0x30','pop rdi','ret');g.finish()


def _loader(rows,edges,base,c):
    f=c['loader'];g=_block(rows,base,f,'prefix')
    for r,o in (('rbx',16),('rsi',24),('rdi',32),('rcx',8)):_memory(g,'store',r,8,base='rsp',displacement=o)
    g.take('push rbp');_lea(g,'rbp',base='rsp',displacement=-87);g.take('sub rsp, 0x100');zero=g.take('xor ebx, ebx');g.finish()
    g=_block(rows,base,f,'openAndMap')
    _memory(g,'store','ebx',4,base='rbp',displacement=103);_lea(g,'rax',base='rbp',displacement=103)
    _memory(g,'store','rax',8,base='rsp',displacement=40);_memory(g,'store','ebx',4,base='rsp',displacement=32)
    g.take('mov edx, 0x3','mov r9d, 0x1','mov r8d, r9d');_lea(g,'rcx',base='rbp',displacement=-41)
    opened=g.call(base+f['openEntryRva']);saved_file=g.take('mov rsi, rax');g.take('cmp dword [rbp+0x67], 0x0');failed=g.branch('jne')
    if failed['target']!=base+f['openFailureRva']:g.fail('open-status-failure-edge',f['openFailureRva'],failed)
    g.take('mov rcx, rax');mapped=g.call(base+c['mappingThunk']['window']['startRva']);saved_map=g.take('mov rdi, rax');g.finish()
    g=_block(rows,base,f,'closeAndSelect');g.take('mov rcx, rsi');_import(g,base+c['imports']['CloseHandle']);g.take('test eax, eax');failed=g.branch('je')
    if failed['target']!=base+f['closeError']['window']['startRva']:g.fail('close-zero-edge',f['closeError'],failed)
    publish=g.take('mov rbx, rdi');g.finish()
    g=_block(rows,base,f,'closeError');_import(g,base+c['imports']['GetLastError']);g.take('test eax, eax');no_error=g.branch('je')
    if no_error['target']!=int(publish['va'],16):g.fail('close-error-zero-edge','saved map result selected',no_error)
    g.take('xor edx, edx','mov rcx, rdi');discard=g.call(base+f['discardEntryRva']);g.take('nop');back=g.branch('jmp');g.finish()
    if back['target']!=base+f['returnWindow']['startRva']:g.fail('discard-return-edge','cleanup with zero selection',back)
    g=_block(rows,base,f,'returnWindow');_lea(g,'rcx',base='rbp',displacement=-41);g.call(base+f['cleanupEntryRva']);g.take('nop')
    _lea(g,'rcx',base='rbp',displacement=-9);g.call(base+f['cleanupEntryRva']);returned=g.take('mov rax, rbx')
    _lea(g,'r11',base='rsp',displacement=256)
    for r,o in (('rbx',24),('rsi',32),('rdi',40)):_memory(g,'load',r,8,base='r11',displacement=o)
    g.take('mov rsp, r11','pop rbp','ret');g.finish()
    for key in ('prefix','directoryDescriptor','fileNameDescriptor','directoryArguments','fileNameArguments','openAndMap','closeAndSelect','closeError','returnWindow'):
        block=_block(rows,base,f,key).rows
        for before,row in zip(block,block[1:]):
            at=int(row['va'],16);expected={int(before['va'],16)}
            if at==int(publish['va'],16):expected.add(int(no_error['va'],16))
            if {a for a,targets in edges.items() if at in targets}!=expected:raise ValueError(LABEL+'.projection-interior-entry:'+key)
    definitions={(int(zero['va'],16),'rbx'):'zero',(int(saved_file['va'],16),'rsi'):'openResult',
        (int(saved_map['va'],16),'rdi'):'mapResult',(int(publish['va'],16),'rbx'):'mapResult'}
    origins=_origins(rows,edges,base+f['entryRva'],definitions)
    if origins[int(publish['va'],16)]['rdi']!=frozenset(('mapResult',)) or origins[int(discard['va'],16)]['rdi']!=frozenset(('mapResult',)):
        raise ValueError(LABEL+'.saved-map-result-origin')
    close_at=base+f['closeAndSelect']['window']['startRva']
    if origins[close_at]['rsi']!=frozenset(('openResult',)):raise ValueError(LABEL+'.saved-open-result-origin')
    if origins[int(returned['va'],16)]['rbx']!=frozenset(('zero','mapResult')):raise ValueError(LABEL+'.normal-return-origin')
    # The zero EBX status/stack stores precede any result publication.
    if origins[base+f['openAndMap']['window']['startRva']]['rbx']!=frozenset(('zero',)):raise ValueError(LABEL+'.open-zero-arguments-origin')
    return {'actualOpenCandidateCallRva':int(opened['va'],16)-base,'actualMappingThunkCallRva':int(mapped['va'],16)-base,
        'normalReturnOrigins':['zero','savedNormalMappingChildResult'],'savedFileAndMappingResultRegistersConditionallyPreserved':True,
        'statusCloseAndErrorResultSelectionGuardsChecked':True,'mappingResultNonnullOrValidProved':False}


def _closed(index,p):
    w=p['window'];base=index.pe.image_base;raw=window_bytes(index,base+w['startRva'],base+w['endRva'],w['sha256'],LABEL)
    return checked_rows(decode_metadata_initialization_instructions(index.mapper,raw,base+w['startRva']),raw,LABEL)


def validate_metadata_loader_control(index,c):
    base=index.pe.image_base;rows,edges,calls,stores,states=_partition(index,c['loader']);path,_,path_calls,path_stores,_=_partition(index,c['pathHelper'])
    literals=_literals(index,c,rows);_path_helper(path,base,c);summary=_loader(rows,edges,base,c)
    mapper_rows=_closed(index,c['mappingThunk']);g=BranchGrammar(mapper_rows,label=LABEL);g.take('xor edx, edx','mov r9d, 0x1');tail=g.branch('jmp');g.finish()
    if tail['target']!=base+c['mappingThunk']['targetEntryRva']:g.fail('mapping-tail-target',c['mappingThunk']['targetEntryRva'],tail)
    default=c['allocatorDefault'];word=index.pe.bytes_at_va(base+default['cellRva'],8)
    if int.from_bytes(word,'little')!=base+default['window']['startRva']:raise ValueError(LABEL+'.on-disk-allocator-pointer')
    allocator_rows=_closed(index,default);g=BranchGrammar(allocator_rows,label=LABEL);tail=g.branch('jmp');g.finish()
    if tail['target']!=base+default['targetEntryRva']:g.fail('default-allocator-tail-target',default['targetEntryRva'],tail)
    bindings=resolve_named_import_slots(index.pe,c['imports'].values())
    actual={r['symbolName']:r['slotRva'] for r in bindings['selectedImports']}
    if actual!=c['imports'] or any(r['libraryName'].lower()!='kernel32.dll' for r in bindings['selectedImports']):raise ValueError(LABEL+'.selected-import-declarations')
    return {**summary,'checkedInstructions':len(rows)+len(path)+len(mapper_rows)+len(allocator_rows),
        'loaderInstructions':len(rows),'pathHelperInstructions':len(path),'closedTransferInstructions':len(mapper_rows)+len(allocator_rows),
        'ownedBytes':sum(w['endRva']-w['startRva'] for f in (c['loader'],c['pathHelper']) for w in f['ownedWindows']),
        'authenticatedPaddingBytes':2,'closedTransferBytes':sum(c[k]['window']['endRva']-c[k]['window']['startRva'] for k in ('mappingThunk','allocatorDefault')),
        'explicitStores':len(stores)+len(path_stores),'loaderCallSites':calls,'pathHelperCallSites':path_calls,'literalPrograms':literals,
        'completeOwnedLoaderAndPathHelperControlStoresAndNormalFramesChecked':True,'literalPointerAndLengthDescriptorArgumentsJoined':True,
        'samePathHelperReceivesDirectoryAndFileNameDescriptorsProved':True,'pathHelperFreshPointerLengthCallsAndSeparatorByteChecked':True,
        'pathHelperNormalReturnIsIncomingDestinationPointerProved':True,'pathHelperLengthArithmeticWrapsModulo64WithoutExtraGuard':True,
        'actualMappingThunkAndOnDiskAllocatorClosedTransfersChecked':True,'closedTransferUnwindOwnershipInferred':False,
        'selectedCloseAndErrorImportDeclarationsChecked':True,'liveIatValueOrCalleeSelected':False,
        'actualConstructedPathContentsProved':False,'actualOpenedOrMappedMetadataFileIdentityProved':False,
        'actualAllocatorLiveSelectionOutcomeOrCapacityProved':False,'childAliasesAndLaterGlobalStabilityProved':False,
        'positiveListAdmitted':False,'wholeRootAdmitted':False}
