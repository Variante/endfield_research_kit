"""Complete generic creation code/data control and selected physical flows.

Tables are authenticated DWORD image RVAs reached through checked byte-tag
guards. Normal continuations include both branch outcomes and retain the
recursive/self-call and child-effect gaps. A fresh cache read, not the
pre-exchange register, supplies the selected non-null return path.
"""
from __future__ import annotations
from collections import deque
from .generic_creation_instructions import decode_generic_creation_instructions
from .owned_partition import BranchGrammar,owned_windows,checked_rows,check_byte_partition,window_bytes
from .relation_control import _table_control
from .initializer_control import control_transfer,_ALIASES
from .field_setup_control import _frames,_projection,setup_memory_effect
from .class_creation_control import _word_load,_dominators
from .relation_import_control import _memory

LABEL='genericCreationControl'


def generic_memory_effect(row):
    for key in ('implicitMemoryExchangeOperation','memoryImmediateOrOperation'):
        if key in row:return {'kind':key,'facts':row[key]}
    return setup_memory_effect(row)


def _partition(index,f):
    base=index.pe.image_base;owned,pieces,windows=owned_windows(index,f,LABEL);rows=[]
    if f['paddingWindows']:raise ValueError(LABEL+'.unreviewed-padding')
    for _,_,start,raw in windows:
        rows.extend(checked_rows(decode_generic_creation_instructions(index.mapper,raw,start),raw,LABEL))
    for t in f['tables']:
        values=t['targetValues']
        if t['indexMax']!=15 or t['tagBias']!=15 or len(values)!=16 or any(type(v)!=int or not 0<=v<1<<32 for v in values):
            raise ValueError(LABEL+'.table-domain')
        if 'selectorValues' in t:raise ValueError(LABEL+'.unreviewed-selector')
        start=base+t['targetTableRva'];end=start+4*len(values)
        raw=window_bytes(index,start,end,t['targetTableSha256'],LABEL)
        if raw!=b''.join(v.to_bytes(4,'little') for v in values):raise ValueError(LABEL+'.table-values')
        pieces.append((start,end,t['role']))
    check_byte_partition(owned,pieces,LABEL);rows.sort(key=lambda r:int(r['va'],16))
    if len(rows)!=f['checkedInstructionCount']:raise ValueError(LABEL+'.instruction-count')
    return rows


def _graph(rows,base,f):
    by_at={int(r['va'],16):r for r in rows};tables={base+t['jumpRva']:t for t in f['tables']}
    if len(by_at)!=len(rows) or len(tables)!=len(f['tables']):raise ValueError(LABEL+'.duplicate-sites')
    guards=[_table_control(rows,f,t,base) for t in f['tables']]
    edges={};branches=[];calls=[];stores=[];returns=[];traps=[];seen_tables=set()
    for at,r in by_at.items():
        t=control_transfer(r);kind=t['kind'];end=at+len(bytes.fromhex(r['bytes']));targets=[]
        if kind in ('jump','conditional'):targets.append(t['target']);branches.append({'siteRva':at-base,**t})
        if kind in ('next','conditional','call','indirectCall','registerCall'):targets.append(end)
        if kind in ('call','indirectCall','registerCall'):
            if kind=='call' and t['target']!=base+f['entryRva'] and any(base+w['startRva']<=t['target']<base+w['endRva'] for w in f['ownedWindows']):
                raise ValueError(LABEL+'.call-into-owned-interior')
            calls.append({'siteRva':at-base,**t})
        elif kind=='tableJump':
            if at not in tables:raise ValueError(LABEL+'.unlisted-table-jump')
            seen_tables.add(at);targets.extend(base+v for v in tables[at]['targetValues'])
        elif kind=='return':returns.append(at-base)
        elif kind=='trap':traps.append(at-base)
        elif kind not in ('next','jump','conditional'):raise ValueError(LABEL+'.unreviewed-transfer')
        if any(target not in by_at for target in targets):raise ValueError(LABEL+'.local-boundary')
        edges[at]=set(targets);effect=generic_memory_effect(r)
        if effect:stores.append({'siteRva':at-base,**effect})
    if seen_tables!=set(tables):raise ValueError(LABEL+'.table-jump-coverage')
    for key,value in (('localBranches',branches),('calls',calls),('explicitStores',stores),('returnRvas',returns),('trapRvas',traps)):
        if f[key]!=value:raise ValueError(LABEL+'.'+key+': expected='+str(f[key])[:160]+' actual='+str(value)[:200])
    for guard in guards:
        for before,row in zip(guard,guard[1:]):
            at=int(row['va'],16);previous=int(before['va'],16)
            if {a for a,targets in edges.items() if at in targets}!={previous}:raise ValueError(LABEL+'.table-guard-interior-entry')
            if any(call.get('target')==at for call in calls):raise ValueError(LABEL+'.call-bypasses-table-guard')
    reached=set();pending=[base+f['entryRva']]
    while pending:
        at=pending.pop()
        if at in reached:continue
        reached.add(at);pending.extend(edges[at]-reached)
    if reached!=set(by_at):raise ValueError(LABEL+'.uncovered-owned-instructions')
    return edges,calls,stores


def _overwrites(row,register):
    head,_,rest=row['text'].partition(' ')
    if head not in ('cmp','test','bt','nop','push') and _ALIASES.get(rest.split(',')[0])==register:return True
    fact=row.get('implicitMemoryExchangeOperation',{})
    if _ALIASES.get(fact.get('register'))==register:return True
    fact=row.get('lockedMemoryExchangeOperation',{})
    return fact.get('operation')=='xadd' and _ALIASES.get(fact.get('sourceRegister'))==register


def _origins(rows,edges,entry,definitions):
    registers=('r12','r14','rdi','rbx');unknown=frozenset((None,));by_at={int(r['va'],16):r for r in rows}
    states={entry:(unknown,)*len(registers)};pending=deque((entry,))
    while pending:
        at=pending.popleft();row=by_at[at];value=list(states[at]);kind=control_transfer(row)['kind']
        for n,register in enumerate(registers):
            if kind=='next' and _overwrites(row,register):value[n]=unknown
            if (at,register) in definitions:value[n]=frozenset((definitions[at,register],))
        for target in edges[at]:
            old=states.get(target);new=tuple(value) if old is None else tuple(a|b for a,b in zip(old,value))
            if new!=old:states[target]=new;pending.append(target)
    return {at:dict(zip(registers,value)) for at,value in states.items()}


def _selected(rows,base,c,f,edges,stores):
    p=f['prefix'];g=BranchGrammar(_projection(rows,base,p['window']),label=LABEL)
    _memory(g,'store','rbx',8,base='rsp',displacement=8)
    g.take('push rbp','push rsi','push rdi','push r12','push r13','push r14','push r15',f'sub rsp, 0x{f["frameBytes"]:x}',
           'movzx ebx, dl')
    input_saved=g.take('mov r12, rcx')
    if int(input_saved['va'],16)!=base+p['inputSavedRva']:g.fail('input-save-site',p['inputSavedRva'],input_saved)
    source=g.call(base+c['genericReceiver']['entryRva']);saved=g.take('mov r14, rax');g.take('test rax, rax')
    branch=g.branch('jne')
    if branch['target']!=base+p['nonNullRva']:g.fail('source-non-null',p['nonNullRva'],branch)
    g.take('test bl, bl');branch=g.branch('jne')
    if branch['target']!=base+p['throwRva']:g.fail('null-source-throw',p['throwRva'],branch)
    branch=g.branch('jmp')
    if branch['target']!=base+p['restoreRva']:g.fail('null-source-restore',p['restoreRva'],branch)
    g.finish()
    p=f['cacheGuard'];g=BranchGrammar(_projection(rows,base,p['window']),label=LABEL)
    g.take(f'cmp qword [r12+0x{f["exchangeAndReload"]["cacheOffset"]:x}], 0x0')
    branch=g.branch('jne')
    if branch['target']!=base+p['reloadRva']:g.fail('existing-cache-skip',p['reloadRva'],branch)
    cache_branch_at=int(branch['va'],16)
    g.finish()
    a=f['allocation'];g=BranchGrammar(_projection(rows,base,a['window']),label=LABEL)
    _word_load(g,'r8d','r14',a['sourceWordOffset'])
    g.take(f'add r8, 0x{a["bias"]:x}',f'shl r8, 0x{a["shift"]:x}','mov rdx, rbx')
    _memory(g,'load','rcx',8,absolute=base+a['contextCellRva'])
    allocation=g.call(base+c['allocatorEntryJoin']['entryRva']);result=g.take('mov rdi, rax');g.finish()
    g=BranchGrammar(_projection(rows,base,f['initialCopies']['window']),label=LABEL)
    _memory(g,'store','rax',8,base='rax',displacement=f['initialCopies']['selfOffset'])
    for offset,width in f['initialCopies']['sourceCopies']:
        register='rcx' if width==8 else 'ecx'
        _memory(g,'load',register,width,base='r14',displacement=offset);_memory(g,'store',register,width,base='rax',displacement=offset)
    link=_memory(g,'store','r12',8,base='rax',displacement=c['classGenericLink']);g.finish()
    p=f['countCopy'];g=BranchGrammar(_projection(rows,base,p['window']),label=LABEL)
    load=_word_load(g,'eax','r14',c['classFieldCount']);store=_memory(g,'store','ax',2,base='rdi',displacement=c['classFieldCount']);g.finish()
    x=f['exchangeAndReload'];g=BranchGrammar(_projection(rows,base,x['window']),label=LABEL)
    exchange=g.row();fact=exchange.get('implicitMemoryExchangeOperation',{});addr=fact.get('address',{})
    if (fact.get('register'),fact.get('bits'),fact.get('memoryReadBytes'),fact.get('memoryWriteBytes'),fact.get('implicitlyLocked'),fact.get('registerPreserved'),
        addr.get('base'),addr.get('index'),addr.get('displacement'),addr.get('ripRelative'))!=('rdi',64,8,8,True,False,'r12',None,x['cacheOffset'],False):
        g.fail('exchange-operands','implicitly locked incoming-receiver cache / RDI exchange',exchange)
    _memory(g,'load','eax',4,absolute=base+x['followingStateCellRva'])
    reload=_memory(g,'load','rdi',8,base='r12',displacement=x['cacheOffset']);g.finish()
    g=BranchGrammar(_projection(rows,base,f['returnWindow']),label=LABEL)
    returned=g.take('mov rax, rdi');_memory(g,'load','rbx',8,base='rsp',displacement=f['frameBytes']+56+8)
    g.take(f'add rsp, 0x{f["frameBytes"]:x}','pop r15','pop r14','pop r13','pop r12','pop rdi','pop rsi','pop rbp','ret');g.finish()
    source_at=int(source['va'],16);saved_at=int(saved['va'],16);allocation_at=int(allocation['va'],16);result_at=int(result['va'],16)
    load_at=int(load['va'],16);store_at=int(store['va'],16);exchange_at=int(exchange['va'],16);reload_at=int(reload['va'],16);returned_at=int(returned['va'],16)
    if reload_at!=base+f['cacheGuard']['reloadRva']:raise ValueError(LABEL+'.cache-guard-reload-join')
    dom=_dominators(edges,base+f['entryRva'])
    for name in ('prefix','cacheGuard','allocation','initialCopies','countCopy','exchangeAndReload'):
        block=_projection(rows,base,f[name]['window'])
        for previous,row in zip(block,block[1:]):
            at=int(row['va'],16)
            expected={int(previous['va'],16)}
            if name=='exchangeAndReload' and at==reload_at:expected.add(cache_branch_at)
            actual={a for a,targets in edges.items() if at in targets}
            if actual!=expected:raise ValueError(LABEL+'.selected-projection-interior-entry: role='+name+' site='+hex(at-base)+' expected='+str(sorted(a-base for a in expected))+' actual='+str(sorted(a-base for a in actual))[:160])
    first=base+f['initialCopies']['window']['startRva']
    if {a for a,targets in edges.items() if first in targets}!={result_at}:raise ValueError(LABEL+'.initial-copy-result-continuation')
    for target,required in ((load_at,(source_at,saved_at,allocation_at,result_at)),(store_at,(load_at,)),
            (int(link['va'],16),(allocation_at,result_at)),(exchange_at,(store_at,allocation_at,result_at)),(returned_at,(reload_at,))):
        if any(site not in dom[target] for site in required):raise ValueError(LABEL+'.selected-dominance')
    count_site=base+a['oneCountRva'];by_at={int(r['va'],16):r for r in rows}
    if count_site not in dom[allocation_at] or by_at[count_site]['text']!='mov ebx, 0x1':raise ValueError(LABEL+'.allocation-count-one-origin')
    definitions={(int(input_saved['va'],16),'r12'):'incomingReceiver',(saved_at,'r14'):'sourceGetterResult',
        (result_at,'rdi'):'allocationResult',(exchange_at,'rdi'):'previousCacheValue',
        (reload_at,'rdi'):'freshCacheRead',(count_site,'rbx'):'one'}
    origins=_origins(rows,edges,base+f['entryRva'],definitions)
    for at,register,expected in ((allocation_at,'rbx','one'),(base+a['window']['startRva'],'r14','sourceGetterResult'),(load_at,'r14','sourceGetterResult'),
            (store_at,'rdi','allocationResult'),(exchange_at,'rdi','allocationResult'),
            (int(link['va'],16),'r12','incomingReceiver'),(exchange_at,'r12','incomingReceiver'),
            (reload_at,'r12','incomingReceiver'),(returned_at,'rdi','freshCacheRead')):
        if origins[at][register]!=frozenset((expected,)):raise ValueError(LABEL+'.saved-origin-overwritten: site='+hex(at-base)+' register='+register+' expected='+expected+' actual='+str(sorted(map(str,origins[at][register]))))
    return {'sourceGetterCallRva':source_at-base,'allocationCallRva':allocation_at-base,'countCopyStoreRva':store_at-base,
        'cacheExchangeRva':exchange_at-base,'freshCacheReloadRva':reload_at-base,
        'sharedReceiverGetterAndSourceSaveProved':True,'countWordSourceIsFreshSavedGetterReceiverProved':True,
        'allocationCountArgumentOneConditionallyProved':True,
        'allocationStrideFormula':'(unsignedSourceWord + bias) << shift',
        'allocationStrideRange':[(a['bias'])<<a['shift'],(65535+a['bias'])<<a['shift']],
        'countCopyAndPublicationUseSavedAllocationResultConditionallyProved':True,
        'allocationGenericLinkStoresOriginalIncomingReceiverProved':True,
        'cacheExchangeOverwritesRdiWithPreviousCacheValueProved':True,
        'nonZeroExistingCacheBranchSkipsAllocationAndCountCopyProved':True,
        'selectedRegisterOriginsCheckedAcrossCompletePossibleControlGraph':True,
        'nonNullReturnProjectionUsesFreshCacheReloadProved':True,
        'allocationAndCountCopyDominateEveryNormalLocalReturnProved':False,
        'cacheReloadEqualsPublishedOrAllocatedPointerProved':False,
        'actualAllocatedClassCacheAndPreparationReceiverIdentityProved':False,
        'creationCountEqualsLaterPreparationCountProved':False,'countUnchangedByChildOrAliasEffectsProved':False}


def validate_generic_creation_control(index,c):
    base=index.pe.image_base;f=c['function'];rows=_partition(index,f);edges,calls,stores=_graph(rows,base,f)
    # The shared frame reader handles explicit register destinations. Refuse
    # implicit exchange/XADD writes to its stack aliases rather than leaving
    # their previous origins in place. The selected current exchange uses RDI.
    for row in rows:
        implicit=row.get('implicitMemoryExchangeOperation',{}).get('register')
        locked=row.get('lockedMemoryExchangeOperation',{})
        source=locked.get('sourceRegister') if locked.get('operation')=='xadd' else None
        if any(_ALIASES.get(register) in ('rsp','rbp','r11') for register in (implicit,source)):
            raise ValueError(LABEL+'.unreviewed-implicit-stack-alias-write:'+row['bytes'])
    _frames(rows,edges,base,f);summary=_selected(rows,base,c,f,edges,stores)
    return {**summary,'checkedInstructions':len(rows),'ownedBytes':sum(w['endRva']-w['startRva'] for w in f['ownedWindows']),
        'codeBytes':sum(w['endRva']-w['startRva'] for w in f['codeWindows']),'tableBytes':sum(len(t['targetValues'])*4 for t in f['tables']),
        'guardedTablesChecked':len(f['tables']),'explicitStores':len(stores),'callSites':calls,
        'completeOwnedCodeDataPartitionChecked':True,'completeOwnedControlAndNormalFrameChecked':True,
        'tableGuardsCannotBeEnteredAfterBoundCheck':True,'acceptedSignedByteTags':[15,30],
        'tableTargetRvasZeroExtendBeforeImageBaseAdditionProved':True,
        'completeTypedCreationEffectsProved':False,'actualSynchronizationAndCacheOutcomeProved':False,
        'recursiveTerminationProved':False,'allocationCapacityAndInitializationOutcomeProved':False,
        'actualArrayCallbackTargetProved':False,'callbackCursorEqualityProved':False,'positiveListAdmitted':False,'wholeRootAdmitted':False}
