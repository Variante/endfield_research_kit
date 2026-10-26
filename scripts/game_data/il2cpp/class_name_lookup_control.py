"""Owned name-cache control and selected key/index/type-record transfers.

Stable valid tables/strings and ordinary noninterfering helper returns are
conditions. Complete physical control is distinct from all helper effects,
runtime class/cache identity and actual initialization.
"""
from __future__ import annotations

from .backward_copy_instructions import decode_legacy_vector_move
from .class_creation_control import _dominators
from .field_setup_control import _graph, _frames, _projection
from .method_carrier_control import _Grammar
from .method_carrier_resolution import _memory, _global, _address
from .record_index_geometry import prove_record_index_geometry
from .initializer_control import _ALIASES, control_transfer
from .memory_moves import decode_memory_move


def _grammar(rows, base, spec, label):
    return _Grammar(_projection(rows, base, spec['window']), label='classNameLookup.' + label)


def _vector(g, direction, receiver, displacement):
    row = g.row()
    raw = bytes.fromhex(row['bytes'])
    decoded = decode_legacy_vector_move(raw, 0, int(row['va'], 16))
    fact = decoded[0].get('memoryOperation', {}) if decoded else {}
    a = fact.get('address', {})
    if decoded is None or decoded[1] != len(raw) or (fact.get('direction'), fact.get('register'),
            fact.get('memoryBytes'), fact.get('requiredAlignmentBytes'), a.get('base'),
            a.get('index'), a.get('displacement'), a.get('ripRelative')) != (
            direction, 'xmm0', 16, 1, receiver, None, displacement, False):
        g.fail('raw-vector-copy', (direction, receiver, displacement), row)


def _slice_entries(rows, edges, base, spec):
    selected = _projection(rows, base, spec['window'])
    for first, second in zip(selected, selected[1:]):
        current = int(second['va'], 16)
        previous = int(first['va'], 16)
        predecessors = {at for at, targets in edges.items() if current in targets}
        if predecessors != {previous}:
            raise ValueError('classNameLookup.projection-interior-entry:' + second['va'])


def _closed_interior(rows, edges, base, spec):
    """Internal branches are checked by the grammar; exclude outside bypasses."""
    selected = _projection(rows, base, spec['window'])
    owned = {int(r['va'], 16) for r in selected}
    entry = int(selected[0]['va'], 16)
    for at in owned - {entry}:
        outsiders = [n for n, targets in edges.items() if at in targets and n not in owned]
        if outsiders:
            raise ValueError('classNameLookup.projection-interior-entry:' + hex(at))


def _query(rows, edges, base, c):
    p = c['projections']['query']
    l = c['layout']
    g = _grammar(rows, base, p, 'query')
    _memory(g, 'store', 'rbp', 8, 'rsp', p['namespaceSlot'])
    _memory(g, 'store', 'rsi', 8, 'rsp', p['nameSlot'])
    g.take(f'mov dword [rsp+0x{p["keySlot"]:x}], 0x0')
    _vector(g, 'load', 'rsp', p['namespaceSlot'])
    _vector(g, 'store', 'rsp', p['keySlot'] + l['keyNamespace'])
    _address(g, 'r8', 'rsp', p['keySlot'])
    _address(g, 'rdx', 'rsp', p['outputSlot'])
    _memory(g, 'load', 'rcx', 8, 'rbx', l['imageCache'])
    call = g.call(base + c['functions']['cacheLookup']['entryRva'])
    g.finish()
    _slice_entries(rows, edges, base, p)
    return {'actualLookupCallRva': int(call['va'], 16) - base,
            'keyHeaderDword': 0, 'keyNamespaceOffset': l['keyNamespace'], 'keyNameOffset': l['keyName'],
            'namespaceAndNameAreRawAdjacentQwords': True, 'queryFieldsCopiedIntoKeyBeforeCall': True}


def _matched_record(rows, edges, base, c, records):
    p = c['projections']['matchedRecord']
    l = c['layout']
    g = _grammar(rows, base, p, 'matchedRecord')
    _memory(g, 'load', 'rax', 8, 'rbx', l['imageCache'])
    _memory(g, 'load', 'rcx', 8, 'rax', l['cacheCapacity'])
    g.take(f'shl rcx, 0x{l["nodeShift"]:x}')
    g.take(f'add rcx, qword [rax+0x{l["cacheNodes"]:x}]')
    _memory(g, 'load', 'r8', 8, 'rsp', p['outputSlot'] + l['outputNode'])
    g.take('cmp r8, rcx')
    g.branch('je', 'notFound')
    _global(g, 'rax', 8, base + c['globals']['metadataHeader'])
    g.take(f'movsxd rcx, dword [rax+0x{l["typeDefinitionsHeader"]:x}]')
    _memory(g, 'load', 'r8', 8, 'r8', l['nodeRecord'])
    g.take('sub r8, rcx', f'sub r8, qword [rip => {hex(base+c["globals"]["metadataBase"])}]',
           f'mov rax, {hex(p["multiplier"] & ((1<<64)-1))}', 'imul r8', 'add rdx, r8',
           f'sar rdx, 0x{p["shift"]:x}', 'mov rcx, rdx', 'shr rcx, 0x3f', 'add rcx, rdx')
    call = g.call(base + c['functions']['classResolver']['entryRva'])
    g.branch('jmp', 'restore')
    g.mark('notFound')
    g.take('xor eax, eax')
    g.mark('restore')
    g.finish()
    if g.labels['restore'] != base + p['window']['endRva']:
        g.fail('return-join', p['window']['endRva'], g.labels['restore'] - base)
    geometry = prove_record_index_geometry(multiplier=p['multiplier'], shift=p['shift'],
                                          record_bytes=l['typeRecordBytes'], records=records)
    _closed_interior(rows, edges, base, p)
    return {**geometry, 'actualClassResolverCallRva': int(call['va'], 16) - base,
            'resultNodeComparedWithFreshEndPointer': True,
            'nonEndNodeRecordOffset': l['nodeRecord'], 'selectedEndResultReturnsZero': True,
            'cacheViewsEqualOrRecordBoundsObserved': False}


def _key_compare(rows, edges, base, p, layout):
    g = _grammar(rows, base, p, 'cstringCompare')
    sources = {'defaultNamespace': ('rdi', layout['cacheDefaultNamespace'], layout['keyNamespace']),
               'defaultName': ('rdi', layout['cacheDefaultName'], layout['keyName']),
               'queryNamespace': ('r15', layout['keyNamespace'], layout['keyNamespace']),
               'queryName': ('r15', layout['keyName'], layout['keyName'])}
    if p['role'] not in sources:
        raise ValueError('classNameLookup.comparison-role')
    receiver, offset, node_offset = sources[p['role']]
    _memory(g, 'load', 'rax', 8, receiver, offset)
    row = g.row()
    raw = bytes.fromhex(row['bytes'])
    decoded = decode_memory_move(raw, 0, int(row['va'], 16))
    fact = decoded[0].get('memoryOperation', {}) if decoded else {}
    address = fact.get('address', {})
    if decoded is None or decoded[1] != len(raw) or (fact.get('direction'), fact.get('register'),
        fact.get('memoryBytes'), address.get('base'), address.get('index'), address.get('scale'),
        address.get('displacement'), address.get('ripRelative')) != (
            'load', 'r9', 8, 'r8', 'rsi', 1, node_offset, False):
        g.fail('node-key-source', (p['role'], node_offset), row)
    g.take('sub r9, rax')
    if p['padding']:
        g.take(p['padding'])
    g.mark('loop')
    g.take('movzx edx, byte [rax]', 'movzx ecx, byte [rax+r9*1]', 'sub edx, ecx')
    g.branch('jne', 'difference')
    g.take('inc rax', 'test ecx, ecx')
    g.branch('jne', 'loop')
    g.mark('difference')
    g.take('test edx, edx')
    mismatch = g.branch(p['finalPredicate'])
    g.finish()
    if mismatch['target'] != base + p['finalTargetRva']:
        g.fail('comparison-result-edge', p['finalTargetRva'], mismatch['target'] - base)
    # The grammar checks the two backedges and their predicates. Every other
    # incoming edge into the interior must originate in this same profile.
    selected = _projection(rows, base, p['window'])
    initial = int(selected[0]['va'], 16)
    loop = g.labels['loop']
    _closed_interior(rows, edges, base, p)
    return {'initialRva': initial - base, 'loopRva': loop - base,
            'readBytesPerSide': 1, 'zeroExtensionBits': 32,
            'zeroDifferenceRequiresEqualBytes': True,
            'matchingZeroByteEndsComparison': True, 'mismatchOrTerminatorControlsFinalBranch': True,
            'sourceRole': p['role'], 'terminationOrActualStringEqualityObserved': False}


def _type_record_copy(rows, edges, base, c):
    p = c['projections']['typeCopy']
    l = c['layout']
    g = _grammar(rows, base, p, 'typeRecordCopy')
    g.take(f'movsxd rax, dword [rdi+0x{l["recordByvalIndex"]:x}]', 'cmp eax, -0x1')
    g.branch('jne', 'registeredType')
    g.take('mov rax, rbp')
    g.branch('jmp', 'copy')
    g.mark('registeredType')
    g.take('mov rdx, rax')
    _global(g, 'rax', 8, base + c['globals']['metadataRegistration'])
    _memory(g, 'load', 'rcx', 8, 'rax', l['registrationTypes'])
    g.take('mov rax, [rcx+rdx*8]')
    g.mark('copy')
    _vector(g, 'load', 'rax', 0)
    _memory(g, 'store', 'rdi', 8, 'rbx', l['classRecord'])
    _vector(g, 'store', 'rbx', l['classReferenceType'])
    _memory(g, 'load', 'eax', 4, 'rbx', l['classReferenceType'] + 8)
    g.take(f'and eax, {hex(p["referenceMask"])}', f'bts eax, 0x{p["referenceBit"]:x}')
    _memory(g, 'store', 'eax', 4, 'rbx', l['classReferenceType'] + 8)
    _vector(g, 'store', 'rbx', l['classValueType'])
    g.finish()
    _closed_interior(rows, edges, base, p)
    # No call or SIMD register update occurs between the one load and the two
    # stores. The reference flag update writes the other copy, not XMM0.
    return {'sourceTypeRecordBytes': 16, 'classValueTypeOffset': l['classValueType'],
            'classReferenceTypeOffset': l['classReferenceType'],
            'originalVectorReusedForValueTypeCopy': True,
            'onlyReferenceCopyFlagDwordChanged': True, 'minusOneByvalUsesOpaqueRbpSource': True,
            'selectedRegistrationTypeIndexBoundsProved': False,
            'copySurvivesLaterCalleesOrAliasesProved': False}


def _zero_key_success(rows, edges, base, c):
    """Under a stable zero key header, both byte comparisons precede a hit."""
    p = c['projections']['zeroKeySuccess']
    l = c['layout']
    comparisons = {item['role']: item for item in c['projections']['comparisons']}
    if set(comparisons) != {'defaultNamespace', 'defaultName', 'queryNamespace', 'queryName'} or len(c['projections']['comparisons']) != 4:
        raise ValueError('classNameLookup.comparison-role-set')
    namespace, name = comparisons['queryNamespace'], comparisons['queryName']
    if (namespace['finalPredicate'], namespace['finalTargetRva'], namespace['window']['endRva'],
        name['finalPredicate'], name['finalTargetRva'], name['window']['endRva']) != (
            'jne', p['probeRva'], name['window']['startRva'], 'je', p['hit']['window']['startRva'], p['probeRva']):
        raise ValueError('classNameLookup.zero-key-comparison-chain')
    g = _grammar(rows, base, p['guard'], 'zeroKeyGuard')
    g.take('cmp dword [r15], 0x0')
    edge = g.branch('je')
    g.finish()
    if edge['target'] != base + namespace['window']['startRva'] or base + p['guard']['window']['endRva'] != base + p['hit']['window']['startRva']:
        raise ValueError('classNameLookup.zero-key-guard-target')
    _closed_interior(rows, edges, base, p['guard'])
    g = _grammar(rows, base, p['hit'], 'hitOutput')
    _memory(g, 'load', 'rcx', 8, 'rdi', l['cacheCapacity'])
    g.take('mov rax, rsi', 'cmp r11, -0x1')
    sentinel = g.branch('je')
    g.take(f'shl rcx, 0x{l["nodeShift"]:x}', 'add rcx, rax',
           f'shl r11, 0x{l["nodeShift"]:x}', 'add r11, rax')
    _memory(g, 'store', 'r11', 8, 'r14', l['outputNode'])
    write = g.rows[g.cursor - 1]
    joined = g.branch('jmp')
    g.finish()
    if sentinel['target'] != base + p['sentinelRva'] or joined['target'] != base + p['commonOutputRva']:
        raise ValueError('classNameLookup.hit-output-joins')
    _closed_interior(rows, edges, base, p['hit'])
    # Remove precisely the mode-nonzero edge. No other path is assumed absent.
    selected_edges = {at: set(targets) for at, targets in edges.items()}
    selected_edges[int(edge['va'], 16)] = {edge['target']}
    entry = base + c['functions']['cacheLookup']['entryRva']
    reached, pending = set(), [entry]
    while pending:
        at = pending.pop()
        if at not in reached:
            reached.add(at)
            pending.extend(selected_edges[at] - reached)
    selected_edges = {at: targets for at, targets in selected_edges.items() if at in reached}
    dom = _dominators(selected_edges, entry)
    write_at = int(write['va'], 16)
    required = {base + item['window']['startRva'] for item in (namespace, name)}
    if write_at not in dom or not required <= dom[write_at]:
        raise ValueError('classNameLookup.zero-key-success-dominance')
    return {'selectedMode': 0, 'nonSentinelNodeWriteRva': write_at - base,
            'bothQueryComparisonsDominateHitUnderStableZeroHeader': True,
            'queryHeaderStabilityObserved': False, 'emptyCacheHelperOutputProved': False,
            'terminationOrRuntimeHitObserved': False}


def _later_type_pointer(rows, edges, base, c):
    p = c['projections']['laterTypePointer']
    g = _grammar(rows, base, p, 'laterTypePointer')
    _address(g, 'rcx', 'rbx', c['layout']['classValueType'])
    while g.cursor < len(g.rows) - 1:
        row = g.row()
        head, _, rest = row['text'].partition(' ')
        if control_transfer(row)['kind'] != 'next' or _ALIASES.get(rest.split(',')[0]) == 'rcx':
            g.fail('type-address-preservation', 'ordinary instruction without RCX overwrite', row)
    call = g.call(base + p['calleeRva'])
    g.finish()
    _closed_interior(rows, edges, base, p)
    return {'actualCallRva': int(call['va'], 16) - base,
            'classValueTypeAddressPassedToLaterCallee': True,
            'calleeCannotMutateTypeCopyProved': False}


def validate_class_name_lookup(programs, *, image_base, contract, metadata_records):
    functions = contract['functions']
    if set(programs) != set(functions):
        raise ValueError('classNameLookup.function-set')
    controls = {}
    graphs = {}
    for key, rows in programs.items():
        f = functions[key]
        actual = [[int(r['va'], 16) - image_base, bytes.fromhex(r['bytes']).hex().upper()] for r in rows]
        if len(rows) != f['checkedInstructionCount'] or actual != f['program']:
            raise ValueError('classNameLookup.complete-code-inventory:' + key)
        edges, calls, stores = _graph(rows, image_base, f)
        _frames(rows, edges, image_base, f)
        graphs[key] = edges
        controls[key] = {'instructions': len(rows), 'actualCalls': calls,
                         'explicitStores': len(stores), 'completeLocalControlAndNormalFramesChecked': True}
    query = _query(programs['lookup'], graphs['lookup'], image_base, contract)
    record = _matched_record(programs['lookup'], graphs['lookup'], image_base, contract, metadata_records)
    comparisons = [_key_compare(programs['cacheLookup'], graphs['cacheLookup'], image_base, p, contract['layout'])
                   for p in contract['projections']['comparisons']]
    copied = _type_record_copy(programs['constructor'], graphs['constructor'], image_base, contract)
    success = _zero_key_success(programs['cacheLookup'], graphs['cacheLookup'], image_base, contract)
    later = _later_type_pointer(programs['constructor'], graphs['constructor'], image_base, contract)
    return {'completeControls': controls, 'distinctOwnedInstructions': sum(len(r) for r in programs.values()),
            'query': query, 'matchedRecord': record, 'keyByteComparisons': comparisons, 'typeRecordCopy': copied,
            'zeroKeySuccess': success, 'laterTypePointer': later,
            'classLookupReturnedNamedClassProved': False, 'metadataOrCacheLiveIdentityProved': False,
            'runtimeInitializationExecuted': False, 'concreteDamageTypeSharingSelected': False,
            'wholeRootAdmitted': False, 'runtimeExecutionKnown': False}
