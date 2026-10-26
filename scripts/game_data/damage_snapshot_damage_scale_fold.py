"""Independent ordered Double fold grammar and selected normal-return paths.

The installed entry is the inline patch-table guard (``il2cpp.patch_table_guard``);
both paths follow its ordinary fall-through, a conditional selection.
"""
from scripts.game_data.damage_snapshot_cache_flow import _require

GUARD_ALIASES = {'r14': 'rcx'}


def check_fold_rows(rows, guard):
    """Installed 67-row grammar; ``guard(rows, 2)`` proves the patch-table entry."""
    _require(len(rows) == 67, 'fold-row-count', 67, len(rows))
    raw = [bytes.fromhex(x['bytes']) for x in rows]
    p = int(rows[0]['va'], 16)
    at = p
    for row, b in zip(rows, raw):
        _require(int(row['va'], 16) == at, 'fold-contiguous-row', hex(at), row['va'])
        at += len(b)
    _require(at - p == 284, 'fold-body-bytes', 284, at-p)
    exact = {0: '4156', 1: '4883ec30', 8: '0f29742420', 10: '83b8e000000000', 12: '488b80b8000000', 13: '48895c2440', 14: '48896c2448', 15: '48897c2458', 16: '488b88a0000000', 17: '4885c9', 19: '488bb950050000', 20: '4885ff', 22: '488b7f18', 24: '488bcf', 26: '8be8', 27: '85c0', 29: '0f1f00', 30: '33db', 31: '4885ff', 33: '4889742450', 35: '8bd3', 36: '488bcf', 39: '488bf0', 40: '83b9e000000000', 42: '4533c0', 43: '488bd6', 44: '498bce', 46: 'ffc3', 47: 'f20f59f0', 48: '3bdd', 50: '488b742450', 51: '488b7c2458', 52: '0f28c6', 53: '0f28742420', 54: '488b6c2448', 55: '488b5c2440', 56: '4883c430', 57: '415e', 58: 'c3', 60: 'cc', 61: '488bc8'}
    for n, b in exact.items():
        _require(raw[n].hex() == b, 'fold-instruction', (n,b), (n,raw[n].hex()))
    for n, pre, size in ((7, '488b05', 7), (9, 'f20f1035', 8), (23, '488b15', 7), (34, '4c8b05', 7), (38, '488b0d', 7), (63, '488b05', 7)):
        _require(len(raw[n]) == size and raw[n].hex().startswith(pre), 'fold-rip-operand', (n, pre), raw[n].hex())
    for n in (25, 37, 45, 59, 62, 65):
        _require(len(raw[n]) == 5 and raw[n][0] == 232, 'fold-call', n, raw[n].hex())
    patch = guard(rows, 2)
    _require(patch['aliases'] == GUARD_ALIASES and patch['nextPosition'] == 7, 'fold-guard', (GUARD_ALIASES, 7), (patch['aliases'], patch['nextPosition']))

    def edge(n, op, dest):
        b = raw[n]
        _require(b[:len(op)] == op and len(b) == len(op) + (4 if len(op) == 2 or op == bytes([0xe9]) else 1), 'fold-edge', (n, op.hex()), b.hex())
        v = int(rows[n]['va'], 16) + len(b) + int.from_bytes(b[len(op):], 'little', signed=True)
        _require(v == int(rows[dest]['va'], 16), 'fold-branch-target', (n,rows[dest]['va']), hex(v))
    for n, op, dest in ((11, bytes.fromhex('0f84'), 61), (18, bytes.fromhex('0f84'), 59), (21, bytes.fromhex('0f84'), 59), (28, bytes.fromhex('7e'), 51), (32, bytes.fromhex('74'), 59), (41, bytes.fromhex('74'), 65), (49, bytes.fromhex('7c'), 34), (64, bytes.fromhex('e9'), 12), (66, bytes.fromhex('eb'), 42)):
        edge(n, op, dest)
    return {'emptyNormalReturnIndices': list(range(29)) + list(range(51, 59)), 'positiveEntryIndices': list(range(34)), 'positiveIterationIndices': list(range(34, 50)), 'positiveFooterIndices': list(range(50, 59)), 'normalRetPopBytes': 8, 'patchTableGuard': patch, 'iterationOrder': 'item request(index EBX32) -> named Double scale request(raw RAX Zone-compatible carrier) -> INC EBX32 -> MULSD ordered accumulator -> CMP32/JL -> same request or full footer', 'typedListZoneProved': False, 'counterAndItemManagedPrototypeProved': False}

def check_fold(index, spec):
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.context import relative_branch_target
    from scripts.game_data.damage_snapshot_atk_scale_flow import check_physical_coverage
    from scripts.game_data.damage_snapshot_abi import require_ordinary_value_type, require_ordinary_type
    from scripts.game_data.damage_snapshot_max_poise_flow import check_reference_definition
    from scripts.game_data.il2cpp.patch_table_guard import check_entry_guard
    from scripts.game_data.damage_snapshot_normal_attack_poise_flow import check_operand_pe
    selected=NativeReferenceContext(index.image,index=index)
    body=index.body(spec['type'],spec['method']); owner=index.types[spec['type']]
    receiver=require_ordinary_value_type(selected,owner.byval_type_index,spec['type'],'fold.receiver')
    raw=index.pe.bytes_at_va(selected.type_pointer(owner.byval_type_index),16)
    _require(int.from_bytes(raw[:8],'little')==owner.index,'fold-concrete-value-owner',owner.index,raw.hex())
    defs=[index.metadata.methods[n['methodIndex']] for n in index.names_by_pointer.get(body.pointer,()) if f"{n.get('type')}.{n.get('method')}"==body.symbol]
    _require(bool(defs),'fold-entry-definition',body.symbol,defs)
    for m in defs:
        _require(m.declaring_type==owner.index and not m.flags&0x10 and not index.metadata.parameters_for(m),'fold-entry-prototype','same concrete instance zero-argument owner',m.declaring_type)
        require_ordinary_type(selected,m.return_type,'double','fold.return')
    _require(body.size==spec['entryExtentBytes'],'fold-entry-extent',spec['entryExtentBytes'],body.size)
    rows=index._decode(body.pointer,body.size)
    _require([len(bytes.fromhex(r['bytes'])) for r in rows]==spec['entryInstructionLengths'],'fold-instruction-lengths',len(spec['entryInstructionLengths']),len(rows))
    grammar=check_fold_rows(rows,lambda r,n:check_entry_guard(r,n,pe=index.pe,decode=index._decode))
    calls={str(n):relative_branch_target(bytes.fromhex(rows[n]['bytes']),int(rows[n]['va'],16),source='damageScaleFold') for n in (25,37,45,59,62,65)}
    provider=[index.metadata.methods[n['methodIndex']] for n in index.names_by_pointer.get(calls['45'],()) if f"{n.get('type')}.{n.get('method')}"==spec['providerMethod']]
    _require(bool(provider),'fold-provider-identity',spec['providerMethod'],hex(calls['45']))
    zone=index.types[spec['zoneType']]
    for m in provider:
        args=list(index.metadata.parameters_for(m))
        _require(m.declaring_type==owner.index and not m.flags&0x10 and len(args)==1,'fold-provider-prototype','same concrete instance owner and one Zone argument',m.declaring_type)
        check_reference_definition(selected,args[0].type_index,spec['zoneType'],zone.index,'fold.Zone')
        require_ordinary_type(selected,m.return_type,'double','fold.provider.return')
        name=index.metadata.string(args[0].name_index)
        _require(index.parameter_location(calls['45'],spec['providerMethod'],name)==('register','rdx'),'fold-zone-slot','rdx',name)
    b=bytes.fromhex(rows[9]['bytes']); operand=int(rows[9]['va'],16)+len(b)+int.from_bytes(b[4:],'little',signed=True)
    bits=index.pe.bytes_at_va(operand,8)
    _require(bits.hex()==spec['seedBits'],'fold-seed-original-bits',spec['seedBits'],bits.hex())
    sections=[s for s in index.pe.sections if s['virtualAddress']<=operand-index.pe.image_base and operand-index.pe.image_base+8<=s['virtualAddress']+s['rawSize']]
    _require(len(sections)==1,'fold-seed-complete-section','unique full eight-byte raw-backed section',sections)
    pe=[check_operand_pe(index.pe,operand+n) for n in (0,4)]
    common={**grammar,'symbol':body.symbol,'receiverABI':receiver,'providerConcreteDefinitionIndex':owner.index,'zoneConcreteDefinitionIndex':zone.index,
        'selectedPhysicalPdataRanges':check_physical_coverage(index.extents,[rows]),'actualCalls':{n:hex(p) for n,p in calls.items()},
        'originalSeedOperand':hex(operand),'originalSeedBits':bits.hex(),'seedPeChunks':pe,
        'boundary':spec['evidenceBoundary']}
    return [{**common,'claim':'damageScaleEmptySignedBoundSeedNormalReturn','selectedInstructionIndices':grammar['emptyNormalReturnIndices'],'selection':'unpatched inline patch-table guard (null table or null slot, anonymous runtime state), anonymous static readiness nonzero and carriers nonnull; opaque count normal post-call EAX interpreted signed Int32 c<=0','formula':'original Double seed XMM6.low64 -> XMM0.low64 -> full normal RET'},
        {**common,'claim':'damageScalePositiveOrderedDoubleFoldNormalReturn','selection':'same unpatched ready/non-null guards, opaque count normal EAX c in [1,INT32_MAX], each iteration readiness nonzero','formula':'i0=0; request item EDX=i; ordinary named scale returns r_i in XMM0.low64; INC32 i then p_(i+1)=MULSD(p_i,r_i); signed CMP/JL repeats while i<c; full saved-state/frame RET returns p_c'}]
