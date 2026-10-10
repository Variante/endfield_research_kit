"""Authenticate anonymous relation code/data control and enumerated writes.

Reachability is a static graph over both branch outcomes and normal call
continuations. No live state, recursive termination or class meaning is inferred.
Exact: no graph edge or direct call enters a table guard after its bound
check, so every table transfer is reached through its guard. Memory-update
semantics come from ``integer_effects``.
"""
from __future__ import annotations
from scripts.game_data.il2cpp.integer_effects import decode_effect_instructions
from scripts.game_data.il2cpp.integer_addressing import decode_lea_address
from scripts.game_data.il2cpp.memory_moves import decode_memory_move
from scripts.game_data.il2cpp.owned_partition import (
    BranchGrammar as _Grammar, check_byte_partition, checked_rows, owned_windows, window_bytes)

_LABEL='relationControl'

_PREDICATES = ('OF=1','OF=0','CF=1','CF=0','ZF=1','ZF=0','CF=1 or ZF=1',
    'CF=0 and ZF=0','SF=1','SF=0','PF=1','PF=0','SF!=OF','SF=OF',
    'ZF=1 or SF!=OF','ZF=0 and SF=OF')


def transfer(row):
    raw=bytes.fromhex(row['bytes']);at=int(row['va'],16);end=at+len(raw)
    if raw==b'\xc3':return {'kind':'return'}
    if len(raw)==5 and raw[0] in (0xe8,0xe9) or len(raw)==2 and raw[0]==0xeb:
        return {'kind':'call' if raw[0]==0xe8 else 'jump',
                'target':end+int.from_bytes(raw[1:],'little',signed=True)}
    if len(raw)==2 and 0x70<=raw[0]<=0x7f:
        code=raw[0]&15;relative=raw[1:]
    elif len(raw)==6 and raw[0]==0x0f and 0x80<=raw[1]<=0x8f:
        code=raw[1]&15;relative=raw[2:]
    else:
        if len(raw)==6 and raw[:2]==b'\xff\x15':
            return {'kind':'indirectCall','cell':end+int.from_bytes(raw[2:],'little',signed=True)}
        if raw==b'\xff\xe1':return {'kind':'tableJump'}
        if row['text'].startswith(('j','call','ret')):
            raise ValueError('relationControl.unhandled-transfer:'+row['bytes'])
        return {'kind':'next'}
    return {'kind':'conditional','target':end+int.from_bytes(relative,'little',signed=True),
            'conditionCode':code,'predicate':_PREDICATES[code]}


def explicit_memory_effect(row):
    raw=bytes.fromhex(row['bytes']);at=int(row['va'],16)
    for key in ('lockedMemoryExchangeOperation','memoryStepOperation','immediateMemoryStoreOperation'):
        if key in row:return {'kind':key,'facts':row[key]}
    result=decode_memory_move(raw,0,at)
    if result is not None and result[1]==len(raw) and result[0]['memoryOperation']['direction']=='store':
        return {'kind':'memoryOperation','facts':result[0]['memoryOperation']}
    if row['text'].startswith('mov ['):
        raise ValueError('relationControl.unclassified-memory-store:'+row['bytes'])
    return None


def _partition(index,c):
    base=index.pe.image_base;owned,pieces,windows=owned_windows(index,c,_LABEL);rows=[]
    for category,w,start,raw in windows:
        if category=='paddingWindows':
            if raw!=bytes.fromhex(w['rawHex']):raise ValueError('relationControl.padding-values')
        else:
            rows.extend(checked_rows(decode_effect_instructions(index.mapper,raw,start),raw,_LABEL))
    for table in c['tables']:
        for kind,width in (('target',4),('selector',1)):
            values=table.get(kind+'Values')
            if values is None:
                if kind=='target':raise ValueError('relationControl.missing-targets')
                continue
            if not 0<len(values)<=256 or any(type(v)!=int or not 0<=v<1<<(width*8) for v in values):
                raise ValueError('relationControl.table-values-range')
            start=base+table[kind+'TableRva'];end=start+len(values)*width
            raw=window_bytes(index,start,end,table[kind+'TableSha256'],_LABEL)
            if raw!=b''.join(v.to_bytes(width,'little') for v in values):raise ValueError('relationControl.table-values')
            pieces.append((start,end,table['role']+'.'+kind))
        values=table.get('selectorValues')
        if (values is not None and (len(values)!=table['indexMax']+1 or any(v>=len(table['targetValues']) for v in values))) or (
            values is None and len(table['targetValues'])!=table['indexMax']+1):
            raise ValueError('relationControl.table-index-bounds')
    check_byte_partition(owned,pieces,_LABEL)
    return rows


def _image_base(g,register,base):
    row=g.row();raw=bytes.fromhex(row['bytes']);result=decode_lea_address(raw,0,int(row['va'],16))
    if result is None or result[1]!=len(raw):g.fail('table-image-base','complete LEA',row)
    f=result[0]['addressOperation']
    if (f['destination'],f['destinationBits'],f['ripRelative'],f.get('absoluteAddress'))!=(register,64,True,base):
        g.fail('table-image-base',(register,base),f)


def _target_load(g,t):
    row=g.row();raw=bytes.fromhex(row['bytes']);result=decode_memory_move(raw,0,int(row['va'],16))
    if result is None or result[1]!=len(raw):g.fail('target-load','complete DWORD memory move',row)
    f=result[0]['memoryOperation'];a=f['address']
    if (f['direction'],f['register'],f['registerBits'],f['memoryBytes'],f['upperRegisterEffect'],
        a['base'],a['index'],a['scale'],a['displacement'])!=('load','ecx',32,4,'zero upper 32 bits',
        t['baseRegister'],'rax',4,t['targetTableRva']):
        g.fail('target-load','checked zero-extending DWORD target at scale four',f)


def _table_control(rows,c,t,base):
    selected=[r for r in rows if base+t['guardStartRva']<=int(r['va'],16)<=base+t['jumpRva']]
    g=_Grammar(selected,label='relationControl.'+t['role']);tag=t['tagRegister'];bias=t['tagBias']
    g.take(f'movsx {tag}, byte [{t["tagBaseRegister"]}+0x{t["tagOffset"]:x}]',
           f'add {tag}, {hex(-bias)}',f'cmp {tag}, 0x{t["indexMax"]:x}')
    row=g.branch('ja')
    if row['target']!=base+t['skipRva']:g.fail('table-guard-skip',t['skipRva'],row['target']-base)
    g.take('cdqe' if tag=='eax' else 'movsxd rax, ecx');_image_base(g,t['baseRegister'],base)
    if 'selectorValues' in t:
        row=g.row();f=row.get('byteMemoryZeroExtensionOperation');a=f['sourceAddress'] if f else {}
        if not f or (f['destinationRegister'],f['destinationBits'],f['memoryReadBytes'],f['zeroExtendsTo64'],
            a['base'],a['index'],a['scale'],a['displacement'])!=('eax',32,1,True,t['baseRegister'],'rax',1,t['selectorTableRva']):
            g.fail('selector-load','checked zero-extending byte selector',row)
    _target_load(g,t);g.take(f'add rcx, {t["baseRegister"]}');row=g.take('jmp rcx')
    if bytes.fromhex(row['bytes'])!=b'\xff\xe1' or int(row['va'],16)!=base+t['jumpRva']:
        g.fail('table-indirect-transfer','original full RCX jump',row)
    g.finish()
    return selected


def _returns(rows,c,base):
    positions={int(r['va'],16):n for n,r in enumerate(rows)}
    entry=positions[base+c['entryRva']]
    prefix=rows[entry:entry+15];g=_Grammar(prefix,label='relationControl.identity')
    g.take('mov [rsp+0x10], rdx','mov [rsp+0x8], rcx','push rbx','push rbp','push rsi','push rdi',
        'push r12','push r13','push r14','push r15','sub rsp, 0x38','mov r13, rdx','mov rsi, rcx','cmp rcx, rdx')
    row=g.branch('je')
    if row['target']!=base+c['returnTrueRva']:g.fail('identity-return',c['returnTrueRva'],row['target']-base)
    g.finish()
    start=positions[base+c['returnTrueRva']];g=_Grammar(rows[start:start+11],label='relationControl.restore')
    g.take('mov al, 0x1','add rsp, 0x38','pop r15','pop r14','pop r13','pop r12','pop rdi','pop rsi','pop rbp','pop rbx','ret');g.finish()
    if int(rows[start+1]['va'],16)!=base+c['restoreRva']:raise ValueError('relationControl.common-restore-entry')
    for rva in c['returnFalseRvas']:
        n=positions[base+rva];g=_Grammar(rows[n:n+2],label='relationControl.false')
        g.take('xor al, al');row=g.branch('jmp')
        if row['target']!=base+c['restoreRva']:g.fail('false-restoration',c['restoreRva'],row['target']-base)
        g.finish()


def validate_relation_control(index,c):
    base=index.pe.image_base;rows=_partition(index,c);starts={int(r['va'],16) for r in rows}
    if len(starts)!=len(rows):raise ValueError('relationControl.duplicate-instruction-start')
    _returns(rows,c,base)
    table_jumps={base+t['jumpRva']:t for t in c['tables']}
    if len(table_jumps)!=len(c['tables']):raise ValueError('relationControl.duplicate-table-jump')
    guards=[_table_control(rows,c,t,base) for t in c['tables']]
    calls=[];indirect=[];effects=[];edges={};branches=[];returns=[]
    for row in rows:
        at=int(row['va'],16);raw=bytes.fromhex(row['bytes']);end=at+len(raw);f=transfer(row);kind=f['kind'];targets=[]
        if kind in ('jump','conditional'):
            targets.append(f['target']);branches.append({'siteRva':at-base,**{k:(v-base if k=='target' else v) for k,v in f.items()}})
        if kind in ('next','conditional','call','indirectCall'):targets.append(end)
        if kind=='call':
            target=f['target'];calls.append({'siteRva':at-base,'targetRva':target-base})
            if any(base+w['startRva']<=target<base+w['endRva'] for w in c['ownedWindows']) and target not in starts:
                raise ValueError('relationControl.call-into-owned-data-or-instruction-middle')
        if kind=='indirectCall':indirect.append({'siteRva':at-base,'cellRva':f['cell']-base})
        if kind=='tableJump':
            t=table_jumps.get(at)
            if t is None:raise ValueError('relationControl.unlisted-table-jump')
            targets.extend(base+rva for rva in t['targetValues'])
        if kind=='return':returns.append(at-base)
        if not all(target in starts for target in targets):raise ValueError('relationControl.target-or-fallthrough-boundary')
        edges[at]=set(targets)
        effect=explicit_memory_effect(row)
        if effect is not None:effects.append({'siteRva':at-base,**effect})
    if calls!=c['directCalls'] or indirect!=c['indirectCalls']:raise ValueError('relationControl.actual-calls')
    if effects!=c['explicitMemoryEffects']:raise ValueError('relationControl.explicit-memory-effects')
    if len(rows)!=c['checkedInstructionCount']:raise ValueError('relationControl.instruction-count')
    if set(table_jumps)!={int(r['va'],16) for r in rows if transfer(r)['kind']=='tableJump'}:
        raise ValueError('relationControl.table-jump-coverage')
    # No branch, table target or fallthrough can bypass a table's own signed tag and unsigned bound checks.
    for guard in guards:
        for before,row in zip(guard,guard[1:]):
            at=int(row['va'],16);expected=int(before['va'],16)
            predecessors={source for source,targets in edges.items() if at in targets}
            if predecessors!={expected}:raise ValueError('relationControl.table-guard-interior-entry')
            if any(call['targetRva']==at-base for call in calls):raise ValueError('relationControl.call-bypasses-table-guard')
    reached=set();pending=[base+c['entryRva']]
    while pending:
        at=pending.pop()
        if at in reached:continue
        reached.add(at);pending.extend(edges[at]-reached)
    updates=[e for e in effects if base+e['siteRva'] in reached]
    locked=[e for e in updates if e['kind']=='lockedMemoryExchangeOperation']
    global_updates={}
    for effect in updates:
        f=effect['facts'];a=f.get('destinationAddress',f.get('address'))
        if not a['ripRelative']:continue
        cell=a['absoluteAddress']-base
        global_updates.setdefault(cell,[]).append({'siteRva':effect['siteRva'],'kind':effect['kind'],
            'writeBytes':f.get('memoryWriteBytes',f.get('memoryBytes'))})
    return {'completeOwnedCodeDataPartitionChecked':True,'checkedInstructions':len(rows),
        'ownedBytes':sum(w['endRva']-w['startRva'] for w in c['ownedWindows']),
        'codeBytes':sum(w['endRva']-w['startRva'] for w in c['codeWindows']),
        'tableBytes':sum(len(t['targetValues'])*4+len(t.get('selectorValues',[])) for t in c['tables']),
        'paddingBytes':sum(w['endRva']-w['startRva'] for w in c['paddingWindows']),
        'completeBranchAndNormalContinuationBoundariesChecked':True,'branchSites':len(branches),
        'directCallSites':calls,'indirectCallStorageSites':indirect,'returnSites':returns,
        'guardedTableJumpsChecked':len(guards),'tableGuardsCannotBeEnteredAfterBoundCheck':True,
        'staticPossibleReachableInstructions':len(reached),'explicitMemoryUpdateSites':effects,
        'staticPossibleReachableLockedUpdateSites':locked,
        'checkedGlobalUpdateStorageGroups':[{'globalCellRva':cell,'sites':sites} for cell,sites in sorted(global_updates.items())],
        'equalInputPointersReturnLowByteOneBeforeHelperCallsProved':True,
        'selectedTrueFalseAndCommonFrameRestoreProved':True,
        'relationIsNotGenerallyFreeOfExplicitMemoryUpdates':bool(updates),
        'conditions':['valid compatible stable selected storage and disjoint stack storage',
            'normal compatible child returns; branch graph includes both outcomes and proves no live path selection'],
        'completeFieldFlowOrNamedTypeRelationMeaningProved':False,'childEffectsOrSynchronizationMeaningProved':False,
        'recursiveTerminationProved':False,'actualRuntimeTargetSelected':False,
        'actualArrayCallbackTargetProved':False,'callbackCursorEqualityProved':False,
        'positiveListAdmitted':False,'wholeRootAdmitted':False}
