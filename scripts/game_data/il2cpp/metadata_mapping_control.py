"""Complete mapping control and conditional slot/registration return flow.

Every owned instruction, local edge, explicit write and normal frame is
checked. Fresh memory views remain fresh after children. A nonnull view-child
result does not establish a nonnull final return or a mapped-file identity.
"""
from __future__ import annotations
from collections import deque
from scripts.game_data.il2cpp.metadata_loader_control import _partition
from scripts.game_data.il2cpp.owned_partition import BranchGrammar
from scripts.game_data.il2cpp.field_construction_control import _lea
from scripts.game_data.il2cpp.relation_import_control import _memory, _branch, _import, _exchange
from scripts.game_data.il2cpp.generic_creation_control import _overwrites
from scripts.game_data.il2cpp.initializer_control import control_transfer
from scripts.game_data.il2cpp.pe_imports import resolve_named_import_slots

LABEL = 'metadataMappingControl'


def _saved_origins(rows, edges, entry, definitions, edge_definitions):
    registers = ('rbx', 'rsi', 'rdi', 'rbp')
    unknown = frozenset((None,))
    by_at = {int(r['va'], 16): r for r in rows}
    states = {entry: (unknown,) * len(registers)}
    pending = deque((entry,))
    while pending:
        at = pending.popleft()
        row = by_at[at]
        value = list(states[at])
        for n, register in enumerate(registers):
            if control_transfer(row)['kind'] == 'next' and _overwrites(row, register):
                value[n] = unknown
            if (at, register) in definitions:
                value[n] = frozenset((definitions[at, register],))
        for target in edges[at]:
            outgoing = tuple(frozenset((edge_definitions[at, target, r],))
                             if (at, target, r) in edge_definitions else value[n]
                             for n, r in enumerate(registers))
            old = states.get(target)
            new = outgoing if old is None else tuple(a | b for a, b in zip(old, outgoing))
            if new != old:
                states[target] = new
                pending.append(target)
    return {at: dict(zip(registers, value)) for at, value in states.items()}


def validate_metadata_mapping_control(index, contract):
    base = index.pe.image_base
    f = contract['mapping']
    rows, edges, calls, stores, frames = _partition(index, f)
    g = BranchGrammar(rows, label=LABEL)
    children = {k: base + v for k, v in contract['childEntries'].items()}
    cells = {k: base + v for k, v in contract['globalCells'].items()}
    labels = {k: base + v for k, v in f['labels'].items()}
    definitions = {}
    requirements = []

    def define(row, register, origin):
        definitions[int(row['va'], 16), register] = origin

    def require(row, register, origin):
        requirements.append((int(row['va'], 16), register, frozenset((origin,))))

    for register, offset in (('rbx', 8), ('r8', 24), ('rdx', 16)):
        _memory(g, 'store', register, 8, base='rsp', displacement=offset)
    g.take('push rbp', 'push rsi', 'push rdi', 'sub rsp, 0x60')
    define(g.take('mov edi, r9d'), 'rdi', 'incomingModeDwordZeroExtended')
    define(g.take('mov rbx, rcx'), 'rbx', 'incomingHandle')
    _lea(g, 'rcx', rip=cells['handle'])
    _memory(g, 'store', 'rcx', 8, base='rsp', displacement=88)
    acquired = g.call(children['acquire'])
    g.take('nop')
    define(g.take('xor ebp, ebp'), 'rbp', 'zero')
    _memory(g, 'store', 'rbp', 8, base='rsp', displacement=72)
    _memory(g, 'store', 'ebp', 4, base='rsp', displacement=144)
    _lea(g, 'rax', base='rsp', displacement=144)
    _memory(g, 'store', 'rax', 8, base='rsp', displacement=48)
    _memory(g, 'store', 'ebp', 4, base='rsp', displacement=40)
    _memory(g, 'store', 'edi', 4, base='rsp', displacement=32)
    _lea(g, 'r9', base='rsp', displacement=72)
    g.take('xor r8d, r8d', 'xor edx, edx', 'mov rcx, rbx')
    created = g.call(children['create'])
    require(created, 'rbx', 'incomingHandle')
    require(created, 'rdi', 'incomingModeDwordZeroExtended')
    require(created, 'rbp', 'zero')
    define(g.take('mov rsi, rax'), 'rsi', 'firstChildNormalResult')
    g.take('cmp dword [rsp+0x90], ebp')
    _branch(g, 'je', labels['view'])
    define(g.take('mov ebx, ebp'), 'rbx', 'zero')
    _branch(g, 'jmp', labels['release'])
    g.mark('view')
    _memory(g, 'store', 'rbp', 8, base='rsp', displacement=72)
    _lea(g, 'rax', base='rsp', displacement=144)
    _memory(g, 'store', 'rax', 8, base='rsp', displacement=40)
    _lea(g, 'rax', base='rsp', displacement=72)
    _memory(g, 'store', 'rax', 8, base='rsp', displacement=32)
    g.take('mov r9d, edi', 'xor r8d, r8d')
    _lea(g, 'rdx', base='rsp', displacement=136)
    g.take('mov rcx, rsi')
    viewed = g.call(children['view'])
    require(viewed, 'rsi', 'firstChildNormalResult')
    require(viewed, 'rdi', 'incomingModeDwordZeroExtended')
    require(viewed, 'rbp', 'zero')
    define(g.take('mov rbx, rax'), 'rbx', 'viewChildNormalResult')
    _memory(g, 'store', 'rax', 8, base='rsp', displacement=64)
    g.take('test rax, rax')
    zero_view = _branch(g, 'je', labels['release'])
    g.call(children['registryA'])
    define(g.take('mov rbx, rax'), 'rbx', 'registryAReceiver')
    g.call(children['registryB'])
    define(g.take('mov rdi, rax'), 'rdi', 'registryBReceiver')
    _memory(g, 'load', 'rcx', 8, base='rsp', displacement=72)
    subtraction = g.row()
    fact = subtraction.get('memoryDestinationSubtractOperation', {})
    address = fact.get('destinationAddress', {})
    if (fact.get('bits'), fact.get('sourceRegister'), fact.get('memoryReadBytes'),
        fact.get('memoryWriteBytes'), address.get('base'), address.get('index'),
        address.get('displacement'), address.get('ripRelative')) != (64, 'rcx', 8, 8, 'rsp', None, 64, False):
        g.fail('return-slot-subtraction', 'QWORD slot64 -= fresh slot72 modulo 64 bits', fact)
    _lea(g, 'r8', base='rsp', displacement=64)
    _lea(g, 'rdx', base='rsp', displacement=72)
    g.take('mov rcx, rbx')
    insert_a = g.call(children['insertA'])
    require(insert_a, 'rbx', 'registryAReceiver')
    _memory(g, 'load', 'rcx', 8, base='rax', displacement=0)
    store_a = _memory(g, 'store', 'rsi', 8, base='rcx', displacement=40)
    require(store_a, 'rsi', 'firstChildNormalResult')
    _lea(g, 'r8', base='rsp', displacement=64)
    _lea(g, 'rdx', base='rsp', displacement=72)
    g.take('mov rcx, rdi')
    insert_b = g.call(children['insertB'])
    require(insert_b, 'rdi', 'registryBReceiver')
    _memory(g, 'load', 'rcx', 8, base='rax', displacement=0)
    offset_load = _memory(g, 'load', 'rax', 8, base='rsp', displacement=136)
    store_b = _memory(g, 'store', 'rax', 8, base='rcx', displacement=40)
    fresh_return = g.take('mov rbx, [rsp+0x40]')
    define(fresh_return, 'rbx', 'freshPostRegistrationReturnSlot')
    g.mark('release')
    _memory(g, 'load', 'eax', 4, absolute=cells['reentry'])
    g.take('test eax, eax')
    _branch(g, 'jle', labels['return'])
    g.take('cmp eax, 0x1')
    _branch(g, 'jne', labels['decrement'])
    owner_clear = _memory(g, 'store', 'rbp', 8, absolute=cells['owner'])
    require(owner_clear, 'rbp', 'zero')
    _memory(g, 'store', 'ebp', 4, absolute=cells['reentry'])
    g.take('mov r8d, eax')
    _memory(g, 'load', 'ecx', 4, absolute=cells['count'])
    g.mark('retry')
    _memory(g, 'load', 'edx', 4, absolute=cells['limit'])
    g.take('cmp ecx, edx')
    _branch(g, 'je', labels['return'])
    g.take('lea eax, [rcx+r8*1]', 'cmp eax, edx')
    _branch(g, 'jle', labels['exchange'])
    g.take('mov r8d, edx', 'sub r8d, ecx')
    g.mark('exchange')
    g.take('lea edx, [rcx+r8*1]', 'mov eax, ecx')
    exchange = _exchange(g, 'cmpxchg', 'edx', absolute=cells['count'])
    _branch(g, 'je', labels['exchangeSuccess'])
    g.take('mov ecx, eax')
    _branch(g, 'jmp', labels['retry'])
    g.mark('exchangeSuccess')
    g.take('test ecx, ecx')
    _branch(g, 'jns', labels['return'])
    g.take('neg ecx', 'cmp r8d, ecx', 'cmovge r8d, ecx', 'mov edx, r8d')
    _memory(g, 'load', 'rcx', 8, absolute=cells['handle'])
    released = _import(g, base + contract['releaseImport']['slotRva'])
    _branch(g, 'jmp', labels['return'])
    g.mark('decrement')
    g.take('dec eax')
    _memory(g, 'store', 'eax', 4, absolute=cells['reentry'])
    g.mark('return')
    returned = g.take('mov rax, rbx')
    _memory(g, 'load', 'rbx', 8, base='rsp', displacement=128)
    g.take('add rsp, 0x60', 'pop rdi', 'pop rsi', 'pop rbp', 'ret')
    g.finish()
    if g.labels != labels:
        g.fail('physical-labels', labels, g.labels)
    edge_definitions = {(int(zero_view['va'], 16), labels['release'], 'rbx'): 'zero'}
    origins = _saved_origins(rows, edges, base + f['entryRva'], definitions, edge_definitions)
    for at, register, expected in requirements:
        if origins[at][register] != expected:
            raise ValueError(f'{LABEL}.saved-origin: site={at-base} register={register} expected={expected} actual={origins[at][register]}')
    if origins[int(returned['va'], 16)]['rbx'] != frozenset(('zero', 'freshPostRegistrationReturnSlot')):
        raise ValueError(LABEL + '.normal-return-origin')
    # The saved incoming RDX cell and reused low DWORD of the R8 home are
    # physical caller-owned cells, not proved immutable input values.
    if any(frames[int(r['va'], 16)][0] != -120 for r in (created, viewed, subtraction, insert_a, offset_load, fresh_return, released, returned)):
        raise ValueError(LABEL + '.physical-frame-slot-geometry')
    binding = resolve_named_import_slots(index.pe, [contract['releaseImport']['slotRva']])['selectedImports']
    if binding != [contract['releaseImport']]:
        raise ValueError(LABEL + '.selected-release-import-declaration')
    return {'checkedInstructions': len(rows), 'ownedBytes': sum(w['endRva']-w['startRva'] for w in f['ownedWindows']),
        'explicitStores': len(stores), 'callSites': calls, 'localBranches': f['localBranches'],
        'normalReturnOrigins': ['zero', 'freshPostRegistrationReturnSlot'],
        'entryHomeOffsets': {'incomingRdx': 16, 'incomingR8': 24},
        'viewChildReceivesAddressOfIncomingRdxHome': True, 'statusOverwritesLowDwordOfIncomingR8Home': True,
        'fullOwnedMappingControlWritesAndNormalFramesChecked': True,
        'firstChildResultAndIncomingModeArgumentsConditionallyPreserved': True,
        'statusFailureAndZeroViewEdgesReturnZero': True,
        'nonnullViewPathSubtractsFreshSlotBeforeTwoRegistrationCalls': True,
        'registrationChildrenReceiveSamePhysicalMutableSlotAddresses': True,
        'firstRegistrationStoresSavedFirstChildResult': True,
        'secondRegistrationStoresFreshIncomingRdxHomeView': True,
        'returnReloadsSlotAfterBothRegistrationCalls': True,
        'releaseUsesFreshGlobalsLockedDwordCompareExchangeRetryAndSignedClamp': True,
        'selectedReleaseImportDeclarationChecked': True,
        'normalReturnEqualsOriginalViewResultProved': False, 'finalReturnNonnullOrValidProved': False,
        'childAliasesOrSlotNoninterferenceProved': False, 'actualMappedFileIdentityProved': False,
        'liveIatCalleeOrSynchronizationOutcomeProved': False, 'retryTerminationProved': False,
        'positiveListAdmitted': False, 'wholeRootAdmitted': False}
