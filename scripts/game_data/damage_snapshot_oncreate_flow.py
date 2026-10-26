"""Prove the exact false-IFix OnCreate this-to-snapshot tail transfer."""
from scripts.game_data.damage_snapshot_cache_flow import _address, _require
from scripts.game_data.damage_snapshot_abi import require_ordinary_signature
from scripts.game_data.il2cpp.context import relative_branch_target
from scripts.game_data.il2cpp.stack_argument_flow import _edge


def check_oncreate_program(rows, *, pointer, end, patch_pointer, snapshot_pointer):
    expected = [b'\x40\x53', b'\x48\x83\xec\x20', b'\x48\x8b\xd9', b'\x33\xd2',
                'guard-index', ('call', patch_pointer), b'\x33\xd2', b'\x84\xc0', 'patch-edge',
                b'\x48\x8b\xcb', b'\x48\x83\xc4\x20', b'\x5b', ('jump', snapshot_pointer)]
    _require(len(rows) >= len(expected), 'oncreate-program-length', len(expected), len(rows))
    at = pointer; edge = None
    for row, encoding in zip(rows, expected):
        raw = bytes.fromhex(row['bytes'])
        _require(_address(row) == at and at+len(raw) <= end, 'oncreate-contiguity', hex(at), row['va'])
        if encoding == 'guard-index':
            _require(len(raw) == 5 and raw[:1] == b'\xb9', 'oncreate-guard-index', 'MOV ECX imm32', raw.hex())
        elif encoding == 'patch-edge':
            branch = _edge(row)
            _require(len(raw) == 6 and raw[:2] == b'\x0f\x85' and branch is not None,
                     'oncreate-patch-edge', 'JNE patch branch', raw.hex())
            edge = branch[0]
        elif isinstance(encoding, tuple):
            actual = relative_branch_target(raw, at, source='damageOnCreate')
            _require(raw[:1] == (b'\xe8' if encoding[0]=='call' else b'\xe9') and actual==encoding[1],
                     'oncreate-physical-target', hex(encoding[1]), hex(actual))
        else:
            _require(raw == encoding, 'oncreate-instruction', encoding.hex(), raw.hex())
        at += len(raw)
    _require(edge is not None and not pointer <= edge < at, 'oncreate-excluded-patch', 'outside selected tail path', edge)
    return {'entry':hex(pointer), 'snapshotTarget':hex(snapshot_pointer), 'tailInstruction':rows[12]['va'],
            'selectedInstructionCount':len(expected), 'excludedPatchTarget':hex(edge),
            'receiverSource':'incoming this RCX copied to nonvolatile RBX, restored into RCX before popping RBX',
            'stackAtTail':'same entry RSP after ADD 0x20 and POP RBX', 'runtimeOnCreateObserved':False}


def check_oncreate(index, clear_proof, spec):
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    _require(clear_proof.get('claim') == 'snapshotIncomingThisCacheReset',
             'oncreate-clear-dependency', 'fresh snapshot entry proof', clear_proof.get('claim'))
    caller = index.body(spec['type'], spec['method'])
    target = index.body(spec['type'], spec['targetMethod'])
    _require(target.pointer == int(clear_proof['entry'],16), 'oncreate-snapshot-entry', clear_proof['entry'], hex(target.pointer))
    selected = NativeReferenceContext(index.image,index=index)
    _require(not selected.is_value_type(spec['type']), 'oncreate-receiver-class', 'ordinary action class', spec['type'])
    for body in (caller,target):
        _require(index.parameter_location(body.pointer,body.symbol,'this') == ('register','rcx'),
                 'oncreate-this-abi', ['register','rcx'], index.parameter_location(body.pointer,body.symbol,'this'))
        methods = [index.metadata.methods[row['methodIndex']] for row in index.names_by_pointer.get(body.pointer,())
                   if f"{row.get('type')}.{row.get('method')}" == body.symbol]
        _require(bool(methods) and all(not m.flags&0x10 and selected.type_name(m.return_type)=='void'
                 and not index.metadata.parameters_for(m) for m in methods),
                 'oncreate-method-abi', 'instance void no-argument concrete action methods', body.symbol)
        for m in methods:
            require_ordinary_signature(selected,m,[],'void',body.symbol)
    _require(caller.pointer in index.extents,'oncreate-pdata-entry','exact owned entry',hex(caller.pointer))
    end=index.extents[caller.pointer]
    _require(0<end-caller.pointer<=512,'oncreate-owned-range','bounded exact owned extent',[caller.pointer,end])
    raw=index.pe.bytes_at_va(caller.pointer,end-caller.pointer);rows=index._decode(caller.pointer,end-caller.pointer)
    _require(b''.join(bytes.fromhex(row['bytes']) for row in rows)==raw,'oncreate-byte-coverage','complete owned partition',len(raw))
    calls=[row for row in rows if bytes.fromhex(row['bytes'])[:1]==b'\xe8']
    _require(bool(calls),'oncreate-patch-call','first direct patch call',len(calls))
    patch=relative_branch_target(bytes.fromhex(calls[0]['bytes']),_address(calls[0]),source='damageOnCreate')
    names=index.names_of(patch);_require(spec['patchMethod'] in names,'oncreate-patch-name',spec['patchMethod'],names)
    patch_methods=[index.metadata.methods[row['methodIndex']] for row in index.names_by_pointer[patch]
                   if f"{row.get('type')}.{row.get('method')}"==spec['patchMethod']]
    _require(bool(patch_methods) and all(m.flags&0x10 and selected.type_name(m.return_type)=='bool'
             and [selected.type_name(p.type_index) for p in index.metadata.parameters_for(m)]==['int']
             for m in patch_methods),'oncreate-patch-abi','static bool IsPatched(int)',len(patch_methods))
    for m in patch_methods:
        require_ordinary_signature(selected,m,['int'],'bool','oncreate.IFix')
    proof=check_oncreate_program(rows,pointer=caller.pointer,end=end,patch_pointer=patch,snapshot_pointer=target.pointer)
    return {**proof,'symbol':caller.symbol,'claim':'snapshotOnCreateIncomingThisTail',
            'boundary':'On the checked false IFix guard, OnCreate preserves its incoming action this through the normally returning guard, restores it into snapshot RCX, fully restores its own frame and tail-jumps to the exact previously proved snapshot entry. Actual OnCreate invocation, live object/class validity and default patch selection remain unobserved conditions; no lifecycle execution, ownership selection or final effect follows.'}
