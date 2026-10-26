"""Closed shared-list CFG/frame checks and selected reference-cell projections.

This proves local control and instruction widths, not every effect, a concrete
closed collection grammar, callback meaning or live formatter selection.
"""
from __future__ import annotations
from .initializer_control import control_transfer
from .initializer_control import _ALIASES
from .field_setup_control import _frames
from .integer_addressing import _address, decode_lea_address
from .integer_tag_dispatch import decode_dword_sign_extension
from .memory_moves import decode_memory_move
from .owned_partition import checked_rows, check_byte_partition
from .owned_partition import BranchGrammar, rip_load

LABEL = 'referenceListControl'


def _slice(rows, base, window):
    a,b=base+window['startRva'],base+window['endRva']
    part=[r for r in rows if a<=int(r['va'],16)<b]
    if (not part or int(part[0]['va'],16)!=a
            or int(part[-1]['va'],16)+len(bytes.fromhex(part[-1]['bytes']))!=b):
        raise ValueError(LABEL+'.protocol-slice-boundary')
    return part


def _predicate(g,code,label):
    row=g.row();flow=list_transfer(row)
    if flow.get('kind')!='conditional' or flow.get('conditionCode')!=code:
        g.fail('protocol-predicate',code,row)
    g.edges.append((flow['target'],label,row))


def _protocol_origins(rows,base,protocol):
    """Track selected nonvolatile origins across joins and ordinary calls."""
    from collections import deque
    by_at={int(r['va'],16):r for r in rows};start=base+protocol['windows']['header']['startRva']
    prefix=_slice(rows,base,protocol['windows']['header'])
    initial={}
    for text,register,origin in [('xor r12d, r12d','r12','zero'),
                                 ('mov r14, rdx','r14','entryReader'),
                                 ('movsxd rdi, dword [rax]','rdi','sourceCount')]:
        matches=[r for r in prefix if r['text']==text]
        if len(matches)!=1:raise ValueError(LABEL+'.origin-definition')
        initial[int(matches[0]['va'],16)]=(register,origin)
    provider=_slice(rows,base,protocol['windows']['providerAndCount'])
    save=next(r for r in provider if r['text']=='mov r13, rax')
    initial[int(save['va'],16)]=('r13','providerResult')
    names=('r14','r13','rdi','r12');states={start:(None,)*4};pending=deque([start])
    while pending:
        at=pending.popleft();row=by_at[at];values=dict(zip(names,states[at]));flow=list_transfer(row)
        head,_,rest=row['text'].partition(' ');dest=rest.split(',')[0];register=_ALIASES.get(dest)
        if at in initial:
            register,origin=initial[at];values[register]=origin
        elif register in names and head not in ('cmp','test','bt','push'):
            values[register]='zero' if row['text']=='mov r12d, 0x0' else None
        # Selected registers are Win64 nonvolatile; opaque calls must preserve them.
        targets=[];kind=flow['kind']
        if kind in ('jump','conditional'):targets.append(flow['target'])
        if kind in ('next','conditional','call','indirectCall','registerCall'):
            targets.append(at+len(bytes.fromhex(row['bytes'])))
        for target in targets:
            new=tuple(values[n] for n in names);old=states.get(target)
            if old is not None:new=tuple(a if a==b else None for a,b in zip(old,new))
            if new!=old:states[target]=new;pending.append(target)
    callback=next(r for r in _slice(rows,base,protocol['windows']['callback']) if r['text'].startswith('call ['))
    predicate=provider[-1]
    selected=[(int(callback['va'],16),'r14','entryReader'),
              (int(callback['va'],16),'r13','providerResult'),
              (int(predicate['va'],16),'rdi','sourceCount'),
              (base+protocol['nullStoreRva'],'r12','zero')]
    for at,register,expected in selected:
        if dict(zip(names,states[at]))[register]!=expected:
            raise ValueError(LABEL+'.origin-lost:'+register+':'+hex(at-base))
    return {'callbackReaderOrigin':'entryReader','callbackReceiverOrigin':'providerResult',
            'positiveCountPredicateOrigin':'sourceCount','nullableStoreOrigin':'zero',
            'requiresNormalWin64NonvolatilePreservation':True}


def validate_header_and_loop(rows,base,protocol):
    """Prove selected count/null/callback routing, leaving helpers opaque."""
    labels={k:base+v for k,v in protocol['labels'].items()}
    def grammar(name):
        g=BranchGrammar(_slice(rows,base,protocol['windows'][name]),label=LABEL+'.'+name)
        g.labels=dict(labels);return g
    def here(g,name):
        if int(g.rows[g.cursor]['va'],16)!=labels[name]:g.fail('protocol-label',name,g.rows[g.cursor])
    calls=protocol['calls'];layout=protocol['readerLayout']
    def mem(offset):return f'[r14+0x{layout[offset]:x}]'
    g=grammar('header')
    g.take('mov [rsp+0x20], rbx','push rbp','push rsi','push rdi','push r12','push r14',
           'sub rsp, 0x30','xor r12d, r12d','mov rbp, r9',
           f"cmp dword [rdx+0x{layout['remaining']:x}], 0x4",'mov rsi, r8','mov r14, rdx','mov [rsp+0x20], r12')
    _predicate(g,13,'readCount')
    g.take('xor r8d, r8d','mov edx, 0x4','mov rcx, r14');g.call(base+calls['shortSegmentCandidate'])
    here(g,'readCount');g.take(f"mov rax, {mem('buffer')}",'movsxd rdi, dword [rax]',
        'mov [rsp+0x68], edi',f"mov ebx, {mem('remaining')}",'sub ebx, 0x4')
    _predicate(g,9,'inlineAdvance')
    g.take('mov edx, 0x4','mov rcx, r14');g.call(base+calls['advanceCandidate'])
    g.take('test al, al');_predicate(g,5,'afterAdvance')
    here(g,'inlineAdvance');g.take(f"add {mem('buffer')}, 0x4",f"add {mem('advanced')}, 0x4",
        f"add {mem('consumed')}, 0x4",f"mov {mem('remaining')}, ebx")
    here(g,'afterAdvance');g.take(f"movsxd rax, dword {mem('consumed')}",
        f"mov rcx, {mem('total')}",'sub rcx, rax','cmp rcx, rdi')
    _predicate(g,12,'countError');g.take('cmp edi, -0x1','setne al','test al, al')
    _predicate(g,4,'nullOutput');g.finish()
    g=grammar('providerAndCount')
    rip_load(g,'rcx',base+protocol['globals']['providerInitClass'])
    g.take('cmp dword [rcx+0xe0], r12d');_predicate(g,5,'providerReady')
    g.call(base+calls['providerInitCandidate']);here(g,'providerReady')
    g.take('mov rax, [rbp+0x20]','mov rcx, [rax+0xc0]','mov rcx, [rcx+0x18]')
    g.call(base+calls['providerLookupCandidate'])
    g.take('mov r13, rax','mov r15d, r12d','test edi, edi');_predicate(g,14,'finishLoop');g.finish()
    g=grammar('callback')
    g.take('mov [rsp+0x20], r12','test r13, r13');_predicate(g,4,'nullError')
    g.take('mov rcx, [r13]');g.call(base+calls['callbackPrepCandidate'])
    g.take('mov rax, [r13]','lea r8, [rsp+0x20]','mov rdx, r14','mov rcx, r13','mov r9, [rax+0x198]')
    row=g.row();flow=list_transfer(row)
    if (flow.get('kind'),flow.get('memoryAddress',{}).get('base'),
        flow.get('memoryAddress',{}).get('displacement'))!=('registerCall','rax',0x190):
        g.fail('element-callback-address','[rax+0x190]',row)
    g.finish()
    g=grammar('loopBack')
    g.take('inc r15d','mov r12d, 0x0','cmp r15d, dword [rsp+0x68]')
    _predicate(g,12,'loopStart');g.finish()
    g=grammar('countError')
    g.take('xor edx, edx','mov ecx, edi');g.call(base+calls['countErrorCandidate']);g.take('int3');g.finish()
    null_row=next(r for r in rows if int(r['va'],16)==base+protocol['nullStoreRva'])
    null_entry=next(r for r in rows if int(r['va'],16)==labels['nullOutput'])
    if (not null_entry['text'].startswith('cmp dword [rip')
            or int(null_entry['va'],16)+len(bytes.fromhex(null_entry['bytes']))!=int(null_row['va'],16)):
        raise ValueError(LABEL+'.null-store-not-immediate-after-compare')
    raw=bytes.fromhex(null_row['bytes']);decoded=decode_memory_move(raw,0,int(null_row['va'],16))
    if decoded is None or decoded[1]!=len(raw):raise ValueError(LABEL+'.null-output-store')
    fact=decoded[0]['memoryOperation'];address=fact['address']
    if (fact['direction'],fact['register'],fact['memoryBytes'],address['base'],address['index'],address['displacement'])!=('store','r12',8,'rsi',None,0):
        raise ValueError(LABEL+'.null-output-store')
    # Check both possible outcomes of every local branch from the null entry.
    by_at={int(r['va'],16):r for r in rows};seen=set();pending=[labels['nullOutput']]
    while pending:
        at=pending.pop()
        if at in seen:continue
        seen.add(at);row=by_at[at];flow=list_transfer(row);kind=flow['kind']
        if kind in ('call','indirectCall','registerCall'):raise ValueError(LABEL+'.null-path-has-call')
        if kind in ('jump','conditional'):pending.append(flow['target'])
        if kind in ('next','conditional'):pending.append(at+len(bytes.fromhex(row['bytes'])))
    if base+protocol['nullStoreRva'] not in seen:raise ValueError(LABEL+'.null-path-missing-store')
    origins=_protocol_origins(rows,base,protocol)
    return {'headerAndLoopRoutingProved':True,'signedCountReadBytes':4,
        'inlineAdvanceBytes':4,'countBoundUsesSignedRemainingMinusConsumed':True,
        'countGuard':{'bound':'wrapped QWORD total minus sign-extended consumed DWORD, interpreted signed64',
            'count':'sign-extended source DWORD','failurePredicate':'signed bound < signed count'},
        'cursorArithmeticBits':{'buffer':64,'advanced':32,'consumed':32,'remaining':32},
        'advanceHelperGuardUsesWrappedSubtractSignFlag':True,
        'nonWrappingOrValidByteBoundsProved':False,
        'minusOneBranchSkipsAllProviderAndElementCalls':True,
        'minusOneBranchOutputStoreBytes':8,'minusOneOutputValueZeroConditionalOnNormalWin64Callees':True,
        'nonNullBranchPerformsProviderLookupBeforeTestingPositiveCount':True,
        'nonpositiveCountSkipsElementLoopAfterProviderLookup':True,
        'elementCallArguments':{'rcx':'saved provider candidate result','rdx':'saved entry reader argument',
            'r8':'address of local eight-byte output slot','r9':'fresh companion from fresh candidate class'},
        'selectedOrigins':origins,
        'loopBoundReloadedFromSavedDwordSlot':True,
        'explicitCountBelowMinusOneRejectionProved':False,'negativeCountHelperParityProved':False,
        'numberOfCallbacksGuaranteed':False,'opaqueHelperEffectsProved':False,
        'concreteCollectionGrammarProved':False,'runtimeExecutionKnown':False}


def list_transfer(row):
    """Decode local/direct transfers and FF /2 memory-call addresses."""
    raw = bytes.fromhex(row['bytes']); at = int(row['va'], 16)
    if len(raw) >= 2 and raw[0] == 0xff and (raw[1] >> 3) & 7 == 2:
        modrm = raw[1]
        if modrm >> 6 == 3:
            raise ValueError(LABEL + '.unreviewed-register-call')
        address, end = _address(raw, 2, modrm, 0, 0, LABEL)
        if end != len(raw):
            raise ValueError(LABEL + '.memory-call-trailing-bytes')
        return {'kind': 'registerCall', 'memoryAddress': address}
    return control_transfer(row)


def _selected(rows, base, selected):
    by_at = {int(r['va'], 16): r for r in rows}
    kinds = {'countSignedLoad': ('dwordSignExtensionOperation', decode_dword_sign_extension),
             'elementOutputAddress': ('addressOperation', decode_lea_address)}
    result = {}
    for role, selection in selected.items():
        row = by_at.get(base + selection['rva'])
        if row is None:
            raise ValueError(LABEL + '.selected-site:' + role)
        raw = bytes.fromhex(row['bytes']); at = int(row['va'], 16)
        if role == 'elementCallback':
            fact = list_transfer(row)
        else:
            key, decoder = kinds.get(role, ('memoryOperation', decode_memory_move))
            decoded = decoder(raw, 0, at)
            if decoded is None or decoded[1] != len(raw):
                raise ValueError(LABEL + '.selected-instruction:' + role)
            fact = decoded[0][key]
        if fact != selection['facts']:
            raise ValueError(LABEL + '.selected-facts:' + role)
        result[role] = fact
    if set(result) != {'countBufferLoad', 'countSignedLoad', 'countStackSave',
                       'elementSlotReset', 'elementOutputAddress', 'elementCallback',
                       'elementSlotLoad', 'inlineArrayStore'}:
        raise ValueError(LABEL + '.selected-role-set')
    count = result['countSignedLoad']; save = result['countStackSave']
    load = result['elementSlotLoad']; store = result['inlineArrayStore']
    reset = result['elementSlotReset']; output = result['elementOutputAddress']
    if (count['sourceBits'], count['memoryReadBytes'], count['destinationBits']) != (32, 4, 64):
        raise ValueError(LABEL + '.count-width')
    if save['direction'] != 'store' or save['memoryBytes'] != 4:
        raise ValueError(LABEL + '.saved-count-width')
    source = result['countBufferLoad']
    pointer_row = by_at[base + selected['countBufferLoad']['rva']]
    count_row = by_at[base + selected['countSignedLoad']['rva']]
    if (source['direction'] != 'load' or source['memoryBytes'] != 8
            or source['register'] != count['sourceAddress']['base']
            or count['sourceAddress']['index'] is not None
            or count['sourceAddress']['displacement'] != 0
            or count['destinationRegister'] != save['backingRegister']
            or selected['countBufferLoad']['rva'] + len(bytes.fromhex(pointer_row['bytes']))
               != selected['countSignedLoad']['rva']
            or selected['countSignedLoad']['rva'] + len(bytes.fromhex(count_row['bytes']))
               != selected['countStackSave']['rva']):
        raise ValueError(LABEL + '.count-source-save-join')
    if (load['direction'], load['memoryBytes'], store['direction'], store['memoryBytes'],
        store['address']['scale']) != ('load', 8, 'store', 8, 8):
        raise ValueError(LABEL + '.reference-cell-width')
    if (reset['direction'], reset['memoryBytes']) != ('store', 8):
        raise ValueError(LABEL + '.reference-reset-width')
    for address in (reset['address'], load['address'], output):
        if address.get('base') != 'rsp' or address.get('index') is not None or address.get('ripRelative'):
            raise ValueError(LABEL + '.output-slot-address')
    if len({reset['address']['displacement'], load['address']['displacement'],
            output['displacement']}) != 1:
        raise ValueError(LABEL + '.distinct-output-slots')
    if load['register'] != store['register']:
        raise ValueError(LABEL + '.distinct-reference-registers')
    return result


def validate_reference_list_control(rows, base, function, selected):
    """Check all local byte boundaries/edges, frames and selected cell widths."""
    by_at = {int(r['va'], 16): r for r in rows}
    if len(by_at) != len(rows):
        raise ValueError(LABEL + '.duplicate-instruction')
    owned = [(base + w['startRva'], base + w['endRva']) for w in function['ownedWindows']]
    for w in function['ownedWindows']:
        a, b = base + w['startRva'], base + w['endRva']
        part = [r for r in rows if a <= int(r['va'], 16) < b]
        checked_rows(part, bytes.fromhex(w['rawHex']), LABEL)
        cursor = a
        for row in part:
            if int(row['va'], 16) != cursor:
                raise ValueError(LABEL + '.instruction-boundary')
            cursor += len(bytes.fromhex(row['bytes']))
        if cursor != b:
            raise ValueError(LABEL + '.instruction-tail')
    pieces = [(a, b, 'code') for a, b in owned]
    check_byte_partition(owned, pieces, LABEL)
    if set(by_at) != {int(r['va'], 16) for r in rows
                     if any(a <= int(r['va'], 16) < b for a, b in owned)}:
        raise ValueError(LABEL + '.instruction-outside-owned')
    edges = {}; calls = []; branches = []; returns = []; traps = []
    for at, row in by_at.items():
        flow = list_transfer(row); kind = flow['kind']; targets = []
        end = at + len(bytes.fromhex(row['bytes']))
        if kind in ('jump', 'conditional'):
            targets.append(flow['target']); branches.append({'siteRva': at-base, **flow})
        if kind in ('next', 'conditional', 'call', 'indirectCall', 'registerCall'):
            targets.append(end)
        if kind in ('call', 'indirectCall', 'registerCall'):
            if kind == 'call' and any(a <= flow['target'] < b for a, b in owned):
                raise ValueError(LABEL + '.call-into-owned-code')
            calls.append({'siteRva': at-base, **flow})
        elif kind == 'return': returns.append(at-base)
        elif kind == 'trap': traps.append(at-base)
        elif kind not in ('next', 'jump', 'conditional'):
            raise ValueError(LABEL + '.unreviewed-transfer')
        if any(t not in by_at for t in targets):
            raise ValueError(LABEL + '.local-boundary')
        edges[at] = set(targets)
    for key, actual in (('calls', calls), ('localBranches', branches),
                        ('returnRvas', returns), ('trapRvas', traps)):
        if function[key] != actual:
            raise ValueError(LABEL + '.declaration:' + key)
    reached = set(); pending = [base + function['entryRva']]
    while pending:
        at = pending.pop()
        if at in reached: continue
        reached.add(at); pending.extend(edges[at] - reached)
    if reached != set(by_at):
        raise ValueError(LABEL + '.uncovered-owned-instructions')
    _frames(rows, edges, base, function, transfer_decoder=list_transfer)
    facts = _selected(rows, base, selected)
    return {'instructionsChecked': len(rows), 'ownedRangesChecked': len(owned),
            'localBranchesChecked': len(branches), 'callsChecked': len(calls),
            'returnRvas': returns, 'trapRvas': traps,
            'completeLocalControlGraphProved': True, 'normalRspFramesProved': True,
            'selectedRepresentation': facts, 'allMemoryEffectsProved': False,
            'loopTerminationProved': False, 'concreteCollectionGrammarProved': False,
            'runtimeExecutionKnown': False}
