"""Complete initializer control, physical writes and conditional saved origins.

All owned bytes are decoded and every local edge is checked. Frame/home
geometry and address provenance are conditional on normal Win64 callees and
stable disjoint storage. Unknown aliases and callee effects remain open.
"""
from __future__ import annotations
from collections import deque
from .integer_addressing import decode_lea_address,_prefix
from .integer_source_operands import is_unknown_instruction
from .initializer_instructions import decode_initializer_instructions
from .memory_moves import _register
from .owned_partition import owned_windows,check_byte_partition,checked_rows
from .relation_control import transfer,explicit_memory_effect

LABEL='initializerControl'
_PARENTS=('rax','rcx','rdx','rbx','rsp','rbp','rsi','rdi')+tuple(f'r{n}' for n in range(8,16))
_ALIASES={}
for n,parent in enumerate(_PARENTS):
    for bits in (8,16,32,64):
        name,_,_=_register(n,bits,True);_ALIASES[name]=parent
for name,parent in zip(('ah','ch','dh','bh'),_PARENTS[:4]):_ALIASES[name]=parent
_VOLATILE=('rax','rcx','rdx','r8','r9','r10','r11')
_READ_ONLY={'cmp','test','nop','push','ret','int3'}
_WRITERS={'mov','movzx','movsx','movsxd','lea','xor','and','or','add','sub','imul','inc','dec','shl','shr','sar','neg','sete','pop','cdqe'}


def control_transfer(row):
    raw = bytes.fromhex(row['bytes'])
    rex = raw[0] if len(raw) == 3 and raw[0] in (0x40, 0x41, 0x48, 0x49) else 0
    opcode = raw[1:] if rex else raw
    if len(opcode) == 2 and opcode[0] == 0xff and 0xd0 <= opcode[1] <= 0xd7:
        register = ('rax','rcx','rdx','rbx','rsp','rbp','rsi','rdi','r8','r9','r10','r11','r12','r13','r14','r15')[(opcode[1]&7) + (8 if rex&1 else 0)]
        if row['text'] != 'call ' + register:
            raise ValueError('registerCall.byte-text-mismatch')
        return {'kind': 'registerCall', 'register': register}
    if raw == b'\xcc':
        return {'kind': 'trap', 'normalContinuation': False}
    return transfer(row)

def memory_effect(row):
    if row.get('memoryOperation',{}).get('direction')=='store':
        return {'kind':'memoryOperation','facts':row['memoryOperation']}
    if 'byteMemoryLogicalOperation' in row:
        return {'kind':'byteMemoryLogicalOperation','facts':row['byteMemoryLogicalOperation']}
    if 'memoryDestinationSubtractOperation' in row:
        return {'kind':'memoryDestinationSubtractOperation','facts':row['memoryDestinationSubtractOperation']}
    effect=explicit_memory_effect(row)
    head,_,rest=row['text'].partition(' ')
    if effect is None and head not in ('cmp','test','lea','nop','call') and '[' in rest.split(',')[0]:
        raise ValueError(LABEL+'.unclassified-memory-write:'+row['bytes'])
    return effect


def _graph(rows,base,f):
    by_at={int(r['va'],16):r for r in rows}
    if len(by_at)!=len(rows):raise ValueError(LABEL+'.duplicate-instruction')
    edges={};branches=[];calls=[];returns=[];traps=[];stores=[]
    owned=[(base+w['startRva'],base+w['endRva']) for w in f['ownedWindows']]
    for at,row in by_at.items():
        t=control_transfer(row);kind=t['kind'];end=at+len(bytes.fromhex(row['bytes']));targets=[]
        if kind in ('jump','conditional'):
            targets.append(t['target']);branches.append({'siteRva':at-base,**t})
        if kind in ('next','conditional','call','indirectCall','registerCall'):targets.append(end)
        if kind in ('call','indirectCall','registerCall'):
            if kind=='call' and t['target']!=base+f['entryRva'] and any(a<=t['target']<b for a,b in owned):
                raise ValueError(LABEL+'.call-into-owned-interior')
            calls.append({'siteRva':at-base,**t})
        elif kind=='return':returns.append(at-base)
        elif kind=='trap':traps.append(at-base)
        elif kind not in ('next','jump','conditional'):raise ValueError(LABEL+'.unreviewed-transfer')
        if any(t not in by_at for t in targets):raise ValueError(LABEL+'.local-boundary')
        edges[at]=set(targets)
        effect=memory_effect(row)
        if effect:stores.append({'siteRva':at-base,**effect})
    for key,value in [('localBranches',branches),('calls',calls),('returnRvas',returns),('trapRvas',traps),('explicitStores',stores)]:
        if f[key]!=value:raise ValueError(LABEL+'.'+key+': expected='+str(f[key])[:180]+' actual='+str(value)[:240])
    reached=set();pending=[base+f['entryRva']]
    while pending:
        at=pending.pop()
        if at in reached:continue
        reached.add(at);pending.extend(edges[at]-reached)
    if reached!=set(by_at):raise ValueError(LABEL+'.uncovered-owned-instructions')
    return edges,calls,stores,returns,traps


def _frame(rows,edges,base,f):
    by_at={int(r['va'],16):r for r in rows};start=base+f['entryRva'];states={start:(0,None)};pending=deque([start])
    while pending:
        at=pending.popleft();row=by_at[at];sp,bp=states[at];head,_,rest=row['text'].partition(' ');dest=rest.split(',')[0]
        if head=='push':
            if rest=='rsp':raise ValueError(LABEL+'.push-rsp')
            sp-=8
        elif head=='pop':
            if rest=='rsp':raise ValueError(LABEL+'.pop-rsp')
            if rest=='rbp':bp=None
            sp+=8
        elif dest=='rsp':
            if head not in ('add','sub') or not rest.startswith('rsp, 0x'):raise ValueError(LABEL+'.dynamic-rsp')
            amount=int(rest.split(', ')[1],16);sp+=amount if head=='add' else -amount
        elif _ALIASES.get(dest)=='rbp':
            raw=bytes.fromhex(row['bytes']);d=decode_lea_address(raw,0,at) if head=='lea' else None
            fact=d[0]['addressOperation'] if d and d[1]==len(raw) else {}
            if (fact.get('destination'),fact.get('destinationBits'),fact.get('base'),fact.get('index'),fact.get('ripRelative'))!=('rbp',64,'rsp',None,False):
                raise ValueError(LABEL+'.unreviewed-rbp-write')
            bp=sp+fact['displacement']
        kind=control_transfer(row)['kind']
        if kind in ('call','indirectCall','registerCall') and ((8+sp)%16 or -sp<32):raise ValueError(LABEL+'.call-frame')
        if kind=='return' and sp!=0:raise ValueError(LABEL+'.return-frame')
        for target in edges[at]:
            new=(sp,bp)
            if target in states and states[target]!=new:raise ValueError(LABEL+'.frame-join')
            if target not in states:states[target]=new;pending.append(target)
    return states


def _address_in_frame(address,state):
    if address.get('index') is not None or address.get('ripRelative'):return None
    sp,bp=state;value=sp if address.get('base')=='rsp' else bp if address.get('base')=='rbp' else None
    return None if value is None else value+address['displacement']


def _homes(rows,stores,states,base,f):
    homes=f['entryHomes'];initial=[]
    if len(homes)!=2 or {h['register'] for h in homes}!={'rdx','rcx'}:raise ValueError(LABEL+'.home-set')
    for row,h in zip(rows,homes):
        expected_origin={'rdx':'savedEntryRdxAddress','rcx':'savedEntryRcxReceiver'}[h['register']]
        if h['savedOrigin']!=expected_origin:raise ValueError(LABEL+'.home-origin-role')
        effect=memory_effect(row);fact=effect['facts'] if effect else {};address=fact.get('address',{})
        if (fact.get('direction'),fact.get('register'),fact.get('memoryBytes'),address.get('base'),address.get('index'),address.get('displacement'))!=('store',h['register'],8,'rsp',None,h['offset']):
            raise ValueError(LABEL+'.initial-home-store')
        if type(h['offset'])!=int or not 8<=h['offset']<=32:raise ValueError(LABEL+'.entry-home-range')
        initial.append(int(row['va'],16)-base)
    if abs(homes[0]['offset']-homes[1]['offset'])<8:raise ValueError(LABEL+'.overlapping-homes')
    stack=[]
    for effect in stores:
        fact=effect['facts'];address=fact.get('address',fact.get('destinationAddress',{}));at=base+effect['siteRva']
        begin=_address_in_frame(address,states[at]);width=fact.get('memoryBytes',fact.get('memoryWriteBytes'))
        if address.get('base') in ('rsp','rbp'):
            if begin is None or type(width)!=int or width<=0:raise ValueError(LABEL+'.unclassified-stack-store')
            if effect['siteRva'] not in initial and any(begin<h['offset']+8 and h['offset']<begin+width for h in homes):
                raise ValueError(LABEL+'.direct-stack-store-overwrites-home')
            stack.append({'siteRva':effect['siteRva'],'entrySpOffset':begin,'bytes':width})
    # PUSH and normal CALL return-address stores are distinct implicit writes.
    implicit=[]
    for row in rows:
        at=int(row['va'],16);kind=control_transfer(row)['kind']
        if row['text'].startswith('push ') or kind in ('call','indirectCall','registerCall'):
            begin=states[at][0]-8
            if any(begin<h['offset']+8 and h['offset']<begin+8 for h in homes):raise ValueError(LABEL+'.implicit-stack-store-overwrites-home')
            implicit.append({'siteRva':at-base,'entrySpOffset':begin,'bytes':8,'kind':'push' if row['text'].startswith('push ') else 'normal-call-return-address'})
    return stack,implicit


def _register_copy(raw):
    at,rex=_prefix(raw,0);opcode=raw[at:at+1]
    if opcode not in (b'\x89',b'\x8b') or len(raw)!=at+2:return None
    modrm=raw[at+1]
    if modrm>>6!=3 or not rex&8:return None
    reg=_register(((modrm>>3)&7)|((rex&4)<<1),64,True)[0];rm=_register((modrm&7)|((rex&1)<<3),64,True)[0]
    return (reg,rm) if opcode==b'\x8b' else (rm,reg)


def _origins(rows,edges,states,base,f):
    by_at={int(r['va'],16):r for r in rows};unknown=frozenset({'unknown'})
    entry=[unknown]*16;entry[_PARENTS.index('rdx')]=frozenset({'entryRdxAddress'});entry[_PARENTS.index('rcx')]=frozenset({'entryRcxReceiver'})
    incoming={base+f['entryRva']:tuple(entry)};pending=deque(incoming)
    while pending:
        at=pending.popleft();row=by_at[at];values=list(incoming[at]);kind=control_transfer(row)['kind'];head,_,rest=row['text'].partition(' ')
        raw=bytes.fromhex(row['bytes']);dest=rest.split(',')[0];parent=_ALIASES.get(dest)
        if kind in ('call','indirectCall','registerCall'):
            for register in _VOLATILE:values[_PARENTS.index(register)]=unknown
        elif kind in ('conditional','jump','return','trap') or head in _READ_ONLY:pass
        elif 'memoryOperation' in row:
            fact=row['memoryOperation']
            if fact['direction']=='load' and fact['backingRegister'] in _PARENTS:
                value=unknown;home=_address_in_frame(fact['address'],states[at])
                if fact['registerBits']==64 and fact['memoryBytes']==8:
                    match=next((h for h in f['entryHomes'] if home==h['offset']),None)
                    if match:value=frozenset({match['savedOrigin']})
                values[_PARENTS.index(fact['backingRegister'])]=value
        elif head=='lock':
            fact=row.get('lockedMemoryExchangeOperation')
            if fact:
                register='rax' if fact['operation']=='cmpxchg' else _ALIASES.get(fact['sourceRegister'])
                if register in _PARENTS:values[_PARENTS.index(register)]=unknown
            elif 'memoryStepOperation' not in row:raise ValueError(LABEL+'.unreviewed-locked-effect')
        elif 'implicitSignedMultiplyOperation' in row:
            for register in ('rax','rdx'):values[_PARENTS.index(register)]=unknown
        elif head in _WRITERS or head.startswith('cmov'):
            if head=='cdqe':parent='rax'
            copy=_register_copy(raw) if head=='mov' else None
            if copy:
                destination,source=copy;values[_PARENTS.index(destination)]=values[_PARENTS.index(source)]
            elif parent is not None:values[_PARENTS.index(parent)]=unknown
        elif head in ('movups','movaps','movdqa','movdqu','xorps'):pass
        else:raise ValueError(LABEL+'.unreviewed-register-effect:'+row['text'])
        output=tuple(values)
        for target in edges[at]:
            old=incoming.get(target);new=output if old is None else tuple(a|b for a,b in zip(old,output))
            if new!=old:incoming[target]=new;pending.append(target)
    return incoming


def _low_byte_returns(rows,edges,base,f):
    by_at={int(r['va'],16):r for r in rows};incoming={base+f['entryRva']:frozenset({None})};pending=deque(incoming)
    while pending:
        at=pending.popleft();r=by_at[at];value=incoming[at];raw=bytes.fromhex(r['bytes']);head,_,rest=r['text'].partition(' ');dest=rest.split(',')[0]
        kind=control_transfer(r)['kind'];parent=_ALIASES.get(dest)
        if raw==b'\x32\xc0':value=frozenset({0})
        elif len(raw)==2 and raw[0]==0xb0:value=frozenset({raw[1]})
        elif kind in ('call','indirectCall','registerCall'):value=frozenset({None})
        elif (head not in _READ_ONLY and parent=='rax' or head=='cdqe' or
              'implicitSignedMultiplyOperation' in r or
              head=='lock' and (
                  r.get('lockedMemoryExchangeOperation',{}).get('operation')=='cmpxchg' or
                  _ALIASES.get(r.get('lockedMemoryExchangeOperation',{}).get('sourceRegister'))=='rax')):value=frozenset({None})
        for target in edges[at]:
            old=incoming.get(target);new=value if old is None else old|value
            if new!=old:incoming[target]=new;pending.append(target)
    result=set().union(*(incoming[int(r['va'],16)] for r in rows if control_transfer(r)['kind']=='return'))
    if result!={0,1}:raise ValueError(LABEL+'.normal-return-low-byte:'+str(result))
    return [0,1]


def validate_initializer_control(index,c):
    f=c['function'];base=index.pe.image_base;owned,pieces,windows=owned_windows(index,f,LABEL)
    if f['paddingWindows']:raise ValueError(LABEL+'.unreviewed-padding')
    rows=[]
    for category,_,at,raw in windows:
        if category!='codeWindows':raise ValueError(LABEL+'.unreviewed-window')
        rows.extend(checked_rows(decode_initializer_instructions(index.mapper,raw,at),raw,LABEL))
    check_byte_partition(owned,pieces,LABEL);rows.sort(key=lambda r:int(r['va'],16))
    if len(rows)!=f['checkedInstructionCount']:raise ValueError(LABEL+'.instruction-count')
    edges,calls,stores,returns,traps=_graph(rows,base,f);states=_frame(rows,edges,base,f)
    stack,implicit=_homes(rows,stores,states,base,f);origins=_origins(rows,edges,states,base,f)
    handoffs=[]
    actual_handoffs=[r['siteRva'] for r in calls if origins[base+r['siteRva']][_PARENTS.index('rdx')] <= {'entryRdxAddress','savedEntryRdxAddress'}]
    if not actual_handoffs or actual_handoffs!=f['incomingAddressCallRvas']:raise ValueError(LABEL+'.complete-incoming-address-call-inventory')
    for site in actual_handoffs:
        value=origins[base+site][_PARENTS.index('rdx')]
        if not value or not value<={'entryRdxAddress','savedEntryRdxAddress'}:raise ValueError(LABEL+'.incoming-address-handoff:'+str((site,sorted(value))))
        handoffs.append({'siteRva':site,'rdxOrigins':sorted(value),'calleeParameterOwnershipOrReadProved':False})
    classified=[]
    for effect in stores:
        fact=effect['facts'];address=fact.get('address',fact.get('destinationAddress',{}));state=origins[base+effect['siteRva']]
        origin=sorted(state[_PARENTS.index(address['base'])]) if address.get('base') in _PARENTS else ['constantOrAbsentBase']
        classified.append({'siteRva':effect['siteRva'],'base':address.get('base'),'baseOrigins':origin})
    return {'completeOwnedInitializerControlAndExplicitWritesChecked':True,'checkedInstructions':len(rows),
            'ownedBytes':sum(b-a for a,b in owned),'checkedLocalBranches':len(f['localBranches']),
            'callSites':calls,'explicitStoreSites':len(stores),'returnSites':returns,'trapSites':traps,
            'directStackStores':stack,'implicitStackWrites':implicit,'allDirectAndImplicitStackStoresAvoidSavedHomesConditionallyProved':True,
            'selectedIncomingAddressHandoffs':handoffs,'explicitStoreBaseOrigins':classified,
            'normalReturnLowByteValues':_low_byte_returns(rows,edges,base,f),
            'normalCallsPreserveNonvolatileAndInvalidateVolatileOrigins':True,
            'unknownAliasAndCalleeWritesCanAffectPointedSlot':True,'incomingSlotContentsUnchangedProved':False,
            'completeTypedClassFieldMeaningProved':False,'liveClassOrFormatterIdentityProved':False,
            'allocationCapacityAndInitializationOutcomeProved':False,'recursiveTerminationProved':False,
            'callbackCursorEqualityProved':False,'positiveListAdmitted':False,'wholeRootAdmitted':False}
