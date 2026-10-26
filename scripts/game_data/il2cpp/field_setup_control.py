"""Complete field-setup CFGs with selected home/count/reference projections.

All owned bytes and stores are checked. Only the selected typed projections
have value-flow meaning; the other body effects remain structural or open.
"""
from __future__ import annotations
from collections import deque
from .field_setup_instructions import decode_field_setup_instructions
from .integer_addressing import decode_lea_address
from .initializer_control import control_transfer,memory_effect,_register_copy,_ALIASES
from .owned_partition import BranchGrammar,owned_windows,checked_rows,check_byte_partition
from .field_construction_control import _lea
from .relation_import_control import _memory
from .class_ancestry_control import _load_byte

LABEL='fieldSetupControl'


def setup_memory_effect(row):
    if 'lockedMemoryAddOperation' in row:return {'kind':'lockedMemoryAddOperation','facts':row['lockedMemoryAddOperation']}
    return memory_effect(row)


def _graph(rows,base,f):
    by_at={int(r['va'],16):r for r in rows};edges={};branches=[];calls=[];stores=[];returns=[];traps=[]
    if len(by_at)!=len(rows):raise ValueError(LABEL+'.duplicate-instruction')
    for at,r in by_at.items():
        t=control_transfer(r);kind=t['kind'];next_at=at+len(bytes.fromhex(r['bytes']));targets=[]
        if kind in ('jump','conditional'):targets.append(t['target']);branches.append({'siteRva':at-base,**t})
        if kind in ('next','conditional','call','indirectCall','registerCall'):targets.append(next_at)
        if kind in ('call','indirectCall','registerCall'):
            if kind=='call' and t['target']!=base+f['entryRva'] and any(base+w['startRva']<=t['target']<base+w['endRva'] for w in f['ownedWindows']):raise ValueError(LABEL+'.call-into-owned-interior')
            calls.append({'siteRva':at-base,**t})
        elif kind=='return':returns.append(at-base)
        elif kind=='trap':traps.append(at-base)
        elif kind not in ('next','jump','conditional'):raise ValueError(LABEL+'.unreviewed-transfer')
        if any(t not in by_at for t in targets):raise ValueError(LABEL+'.local-boundary')
        edges[at]=set(targets);effect=setup_memory_effect(r)
        if effect:stores.append({'siteRva':at-base,**effect})
    for key,value in [('localBranches',branches),('calls',calls),('explicitStores',stores),('returnRvas',returns),('trapRvas',traps)]:
        if f[key]!=value:raise ValueError(LABEL+'.'+key+': expected='+str(f[key])[:180]+' actual='+str(value)[:240])
    reached=set();pending=[base+f['entryRva']]
    while pending:
        at=pending.pop()
        if at in reached:continue
        reached.add(at);pending.extend(edges[at]-reached)
    if reached!=set(by_at):raise ValueError(LABEL+'.uncovered-owned-instructions')
    return edges,calls,stores


def _frames(rows,edges,base,f,*,transfer_decoder=None):
    """Track RSP plus optional RBP/R11 stack aliases through normal calls."""
    transfer_decoder=control_transfer if transfer_decoder is None else transfer_decoder
    registers=('rsp','rbp','r11');by_at={int(r['va'],16):r for r in rows}
    states={base+f['entryRva']:(0,None,None)};pending=deque(states)
    while pending:
        at=pending.popleft();r=by_at[at];state=dict(zip(registers,states[at]));head,_,rest=r['text'].partition(' ')
        destination=rest.split(',')[0];parent=_ALIASES.get(destination);kind=transfer_decoder(r)['kind'];raw=bytes.fromhex(r['bytes'])
        if head in ('push','pop'):
            if rest=='rsp':raise ValueError(LABEL+'.unreviewed-rsp')
            state['rsp']+=-8 if head=='push' else 8
            if head=='pop' and parent in registers:state[parent]=None
        elif kind in ('call','indirectCall','registerCall'):state['r11']=None
        elif parent in registers and head not in ('cmp','test','bt'):
            if parent=='rsp' and head in ('add','sub') and rest.startswith('rsp, 0x'):
                amount=int(rest.split(', ')[1],16);state[parent]+=amount if head=='add' else -amount
            else:
                copy=_register_copy(raw) if head=='mov' else None
                decoded=decode_lea_address(raw,0,at) if head=='lea' else None
                fact=decoded[0]['addressOperation'] if decoded and decoded[1]==len(raw) else {}
                if copy and copy[0] in registers:state[parent]=state.get(copy[1])
                elif fact.get('destinationBits')==64 and fact.get('base') in registers and fact.get('index') is None and not fact.get('ripRelative'):
                    origin=state[fact['base']];state[parent]=None if origin is None else origin+fact['displacement']
                else:state[parent]=None
        if state['rsp'] is None:raise ValueError(LABEL+'.unproved-rsp')
        if kind in ('call','indirectCall','registerCall') and ((8+state['rsp'])%16 or -state['rsp']<32):raise ValueError(LABEL+'.call-frame')
        if kind=='return' and state['rsp']!=0:raise ValueError(LABEL+'.return-frame')
        for target in edges[at]:
            value=tuple(state[n] for n in registers);old=states.get(target)
            if old is not None:
                if old[0]!=value[0]:raise ValueError(LABEL+'.rsp-join')
                value=tuple(a if a==b else None for a,b in zip(old,value))
            if old!=value:states[target]=value;pending.append(target)
    return states


def _projection(rows,base,w):
    selected=[r for r in rows if base+w['startRva']<=int(r['va'],16)<base+w['endRva']]
    if not selected or int(selected[0]['va'],16)!=base+w['startRva'] or int(selected[-1]['va'],16)+len(bytes.fromhex(selected[-1]['bytes']))!=base+w['endRva']:
        raise ValueError(LABEL+'.projection-boundary')
    return selected


def _ordinary(rows,base,c,f,states,stores):
    p=f['allocationPrefix'];fields=c['classFields'];g=BranchGrammar(_projection(rows,base,p['window']),label=LABEL)
    g.labels.update({name:base+value for name,value in p['labels'].items() if name!='nonempty'})
    _memory(g,'store','rdx',8,base='rsp',displacement=f['entryHomes']['rdx']);_memory(g,'store','rcx',8,base='rsp',displacement=f['entryHomes']['rcx'])
    for register in ('rbx','rbp','rsi','rdi','r12','r13','r14','r15'):g.take('push '+register)
    g.take(f'sub rsp, 0x{f["frameBytes"]:x}',f'movaps [rsp+0x{f["vectorHomeOffset"]:x}], xmm6','mov rbx, rcx')
    r=g.row()
    if bytes.fromhex(r['bytes'])!=b'\x66\x83\xb9'+fields['fieldCount'].to_bytes(4,'little',signed=True)+b'\x00':g.fail('word-count-zero','CMP WORD receiver count, zero',r)
    g.branch('jne','nonempty');g.take(f'mov qword [rcx+0x{fields["fields"]:x}], 0x0');g.branch('jmp','restore')
    g.mark('nonempty')
    if g.labels['nonempty']!=base+p['labels']['nonempty']:g.fail('nonempty-entry',p['labels']['nonempty'],g.labels['nonempty']-base)
    g.take(f'movzx edx, word [rcx+0x{fields["fieldCount"]:x}]',f'mov r8d, 0x{c["strideBytes"]:x}')
    _memory(g,'load','rcx',8,absolute=base+p['allocatorContextCellRva']);call=g.call(base+p['allocatorTargetRva'])
    _memory(g,'store','rax',8,base='rsp',displacement=p['resultSlotOffset']);g.take('mov r15, rax',f'movzx ecx, word [rbx+0x{fields["fieldCount"]:x}]','xor esi, esi','mov edx, esi')
    _memory(g,'store','edx',4,base='rsp',displacement=p['counterSlotOffset']);g.take('cmp si, cx');g.branch('jae','publish')
    g.finish();home=f['entryHomes']['rdx'];home_writes=[];rcx_other=[]
    for s in stores:
        fact=s['facts'];address=fact.get('address',fact.get('destinationAddress',{}));width=fact.get('memoryBytes',fact.get('memoryWriteBytes'))
        if address.get('base')!='rsp' or address.get('index') is not None or address.get('ripRelative'):continue
        offset=states[base+s['siteRva']][0]+address['displacement']
        if s['siteRva']==f['entryRva']:continue
        if offset<home+8 and home<offset+width:home_writes.append({'siteRva':s['siteRva'],'entrySpOffset':offset,'bytes':width})
        saved=f['entryHomes']['rcx']
        if s['siteRva']!=f['receiverSaveRva'] and offset<saved+8 and saved<offset+width:rcx_other.append(s['siteRva'])
    if home_writes!=f['rdxHomeCounterWrites'] or not home_writes or rcx_other:raise ValueError(LABEL+'.home-reuse-inventory')
    return {'allocatorCallRva':int(call['va'],16)-base,'allocatorUnsignedCountBits':16,'allocatorStrideBytes':c['strideBytes'],
            'allocationCountAndPostAllocationLoopCountAreSeparateLoadsProved':True,
            'allocationCountEqualsFreshLoopCountProved':False,'savedRdxHomeRepurposedAsDwordCounterProved':True,
            'rdxHomeCounterWrites':home_writes,'savedRcxHomeAvoidedByOtherDirectStackWrites':True,
            'homeReuseDoesNotProveIncomingPointedSlotPreservation':True}


def _auxiliary(rows,base,c,f,edges):
    if not f['laterLayoutCalls']:raise ValueError(LABEL+'.empty-later-layout-calls')
    fields=c['classFields'];p=f['parentReferencePrefix'];g=BranchGrammar(_projection(rows,base,p['window']),label=LABEL)
    g.labels.update({name:base+value for name,value in p['labels'].items()})
    for register in ('rbx','rsi','rdi'):_memory(g,'store',register,8,base='rsp',displacement=f['savedRegisterOffsets'][register])
    for register in ('rbp','r12','r13','r14','r15'):g.take('push '+register)
    _lea(g,'rbp',base='rsp',displacement=f['framePointerDisplacement']);g.take(f'sub rsp, 0x{f["frameBytes"]:x}','mov rbx, rcx')
    g.take(f'test byte [rcx+0x{fields["stateFlags"]:x}], 0x{f["skipMask"]:x}');g.branch('jne','restore')
    g.take(f'cmp qword [rcx+0x{fields["parent"]:x}], 0x0');g.branch('je','noParent')
    _memory(g,'load','rax',8,base='rcx',displacement=fields['parent']);_load_byte(g,'edx','rax',fields['stateFlags'])
    r=g.row();fact=r.get('byteMemoryOrOperation',{});address=fact.get('sourceAddress',{})
    if (fact.get('destinationRegister'),fact.get('bits'),fact.get('memoryReadBytes'),fact.get('memoryWriteBytes'),address.get('base'),address.get('index'),address.get('displacement'),address.get('ripRelative'))!=('dl',8,1,0,'rcx',None,fields['stateFlags'],False):g.fail('parent-reference-byte-or','DL OR fresh receiver byte',r)
    _load_byte(g,'eax','rcx',fields['stateFlags']);g.take('xor dl, al');r=g.row();fact=r.get('byteLogicalOperation',{})
    if (fact.get('operation'),fact.get('destinationRegister'),fact.get('immediateWord'))!=('and','dl',1<<c['hasReferencesBit']):g.fail('named-reference-mask',c['hasReferencesBit'],r)
    g.take('xor dl, al');_memory(g,'store','dl',1,base='rcx',displacement=fields['stateFlags']);g.finish()
    gate=f['referenceCallGate'];g=BranchGrammar(_projection(rows,base,gate['window']),label=LABEL)
    g.labels['skip']=base+gate['skipRva'];g.call(base+c['hasReferencesTargetRva']);g.take('test al, al');g.branch('je','skip')
    r=g.row();fact=r.get('byteMemoryLogicalOperation',{});address=fact.get('destinationAddress',{})
    if (fact.get('operation'),fact.get('bits'),fact.get('immediateWord'),fact.get('memoryReadBytes'),fact.get('memoryWriteBytes'),address.get('base'),address.get('index'),address.get('displacement'),address.get('ripRelative'))!=('or',8,1<<c['hasReferencesBit'],1,1,'rbx',None,fields['stateFlags'],False):g.fail('named-reference-set','OR receiver reference bit',r)
    g.finish();ready=base+f['earlyReadyWriteRva'];r=next(r for r in rows if int(r['va'],16)==ready)
    fact=r.get('byteMemoryLogicalOperation',{});address=fact.get('destinationAddress',{})
    if (fact.get('operation'),fact.get('bits'),fact.get('immediateWord'),fact.get('memoryReadBytes'),fact.get('memoryWriteBytes'),address.get('base'),address.get('index'),address.get('displacement'),address.get('ripRelative'))!=('or',8,1<<c['fieldsReadyBit'],1,1,'rbx',None,fields['fieldState'],False):raise ValueError(LABEL+'.early-ready-write')
    nodes=set(edges);entry=base+f['entryRva'];dom={n:({entry} if n==entry else set(nodes)) for n in nodes};changed=True
    predecessors={n:set() for n in nodes}
    for a,targets in edges.items():
        for b in targets:predecessors[b].add(a)
    while changed:
        changed=False
        for n in sorted(nodes-{entry}):
            value={n}|set.intersection(*(dom[p] for p in predecessors[n]))
            if value!=dom[n]:dom[n]=value;changed=True
    sites={int(r['va'],16):r for r in rows}
    for call in f['laterLayoutCalls']:
        at=base+call['siteRva'];transfer=control_transfer(sites[at])
        if transfer!=call['transfer'] or ready not in dom[at]:raise ValueError(LABEL+'.early-ready-before-layout-call')
    return {'namedHasReferencesBitInheritedConditionallyProved':True,
            'parentReferenceStoreFormula':'freshReceiver2 XOR (((parentByte OR freshReceiver1) XOR freshReceiver2) AND namedMask)',
            'unselectedReceiverBitsEqualFreshReceiver2Proved':True,'twoReceiverByteLoadsNotAssumedEqual':True,
            'actualNamedHasReferencesCallAndSelectedBitStoreProved':True,
            'fieldsReadyWriteDominatesSelectedLaterLayoutCallsOnNormalLocalPaths':True,
            'fieldsReadyWriteDoesNotProveAllLayoutChildrenCompleted':True}


def validate_field_setup_control(index,c):
    base=index.pe.image_base;results={};count=size=stores=0
    if {f['role'] for f in c['functions']}!={'ordinaryFields','auxiliary'} or len(c['functions'])!=2:raise ValueError(LABEL+'.role-set')
    for f in c['functions']:
        owned,pieces,windows=owned_windows(index,f,LABEL);rows=[]
        if f['paddingWindows']:raise ValueError(LABEL+'.unreviewed-padding')
        for _,_,start,raw in windows:rows.extend(checked_rows(decode_field_setup_instructions(index.mapper,raw,start),raw,LABEL))
        rows.sort(key=lambda r:int(r['va'],16));check_byte_partition(owned,pieces,LABEL)
        if len(rows)!=f['checkedInstructionCount']:raise ValueError(LABEL+'.instruction-count')
        edges,calls,writes=_graph(rows,base,f);states=_frames(rows,edges,base,f)
        typed=_ordinary(rows,base,c,f,states,writes) if f['role']=='ordinaryFields' else _auxiliary(rows,base,c,f,edges)
        results[f['role']]={'checkedInstructions':len(rows),'ownedBytes':sum(b-a for a,b in owned),'explicitStores':len(writes),
            'callSites':calls,'completeOwnedCfgAndFrameGeometryProved':True,'completeTypedEffectsProved':False,**typed}
        count+=len(rows);size+=sum(b-a for a,b in owned);stores+=len(writes)
    return {'checkedInstructions':count,'ownedBytes':size,'explicitStores':stores,'programs':results,
            'completeTypedOrdinaryAuxiliaryEffectsProved':False,'liveClassOrFormatterIdentityProved':False,
            'incomingSlotContentsUnchangedProved':False,'initializationCapacityOrSynchronizationOutcomeProved':False,
            'callbackCursorEqualityProved':False,'positiveListAdmitted':False,'wholeRootAdmitted':False}
