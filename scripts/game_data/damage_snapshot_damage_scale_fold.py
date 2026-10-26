"""Independent ordered Double fold grammar and selected normal-return paths."""
from scripts.game_data.damage_snapshot_cache_flow import _require

def check_fold_rows(rows):
    _require(len(rows) == 68, 'fold-row-count', 68, len(rows))
    raw = [bytes.fromhex(x['bytes']) for x in rows]
    p = int(rows[0]['va'], 16)
    at = p
    for row, b in zip(rows, raw):
        _require(int(row['va'], 16) == at, 'fold-contiguous-row', hex(at), row['va'])
        at += len(b)
    _require(at - p == 284, 'fold-body-bytes', 284, at-p)
    exact = {0: '48895c2410', 1: '48896c2418', 2: '48897c2420', 3: '4156', 4: '4883ec30', 5: '4c8bf1', 6: '0f29742420', 8: '33d2', 10: '84c0', 14: '83b8e000000000', 16: '488b80b8000000', 17: '488b88a0000000', 18: '4885c9', 20: '488bb910050000', 21: '4885ff', 23: '488b7f18', 25: '488bcf', 27: '8be8', 28: '85c0', 30: '0f1f00', 31: '33db', 32: '4885ff', 34: '4889742440', 36: '8bd3', 37: '488bcf', 40: '488bf0', 41: '83b9e000000000', 43: '4533c0', 44: '488bd6', 45: '498bce', 47: 'ffc3', 48: 'f20f59f0', 49: '3bdd', 51: '488b742440', 52: '0f28c6', 53: '488b5c2448', 54: '488b6c2450', 55: '488b7c2458', 56: '0f28742420', 57: '4883c430', 58: '415e', 59: 'c3', 60: '488bc8', 67: 'cc'}
    for n, b in exact.items():
        _require(raw[n].hex() == b, 'fold-instruction', (n,b), (n,raw[n].hex()))
    for n, pre, size in ((12, '488b05', 7), (13, 'f20f1035', 8), (24, '488b15', 7), (35, '4c8b05', 7), (39, '488b0d', 7), (62, '488b05', 7)):
        _require(len(raw[n]) == size and raw[n].hex().startswith(pre), 'damage-scale-fold-raw', 'reviewed complete grammar/control', 'mismatch')
    _require(len(raw[7]) == 5 and raw[7][0] == 185, 'damage-scale-fold-raw', 'reviewed complete grammar/control', 'mismatch')
    for n in (9, 26, 38, 46, 61, 64, 66):
        _require(len(raw[n]) == 5 and raw[n][0] == 232, 'damage-scale-fold-raw', 'reviewed complete grammar/control', 'mismatch')

    def edge(n, op, dest):
        b = raw[n]
        _require(b[:len(op)] == op, 'damage-scale-fold-raw', 'reviewed complete grammar/control', 'mismatch')
        _require(len(b) == len(op) + (4 if len(op) == 2 or op == b'\xe9' else 1), 'damage-scale-fold-raw', 'reviewed complete grammar/control', 'mismatch')
        v = int(rows[n]['va'], 16) + len(b) + int.from_bytes(b[len(op):], 'little', signed=True)
        if dest is None:
            _require(not p <= v < at, 'damage-scale-fold-raw', 'reviewed complete grammar/control', 'mismatch')
        else:
            _require(v == int(rows[dest]['va'], 16), 'fold-branch-target', (n,rows[dest]['va']), hex(v))
    for n, op, dest in ((11, b'\x0f\x85', None), (15, b'\x0f\x84', 60), (19, b'\x0f\x84', 66), (22, b'\x0f\x84', 66), (29, b'~', 52), (33, b't', 66), (42, b't', 64), (50, b'|', 35), (63, b'\xe9', 16), (65, b'\xeb', 43)):
        edge(n, op, dest)
    return {'emptyNormalReturnIndices': list(range(30)) + list(range(52, 60)), 'positiveEntryIndices': list(range(35)), 'positiveIterationIndices': list(range(35, 51)), 'positiveFooterIndices': list(range(51, 60)), 'normalRetPopBytes': 8, 'iterationOrder': 'item request(index EBX32) -> named Double scale request(raw RAX Zone-compatible carrier) -> INC EBX32 -> MULSD ordered accumulator -> CMP32/JL -> same request or full footer', 'typedListZoneProved': False, 'counterAndItemManagedPrototypeProved': False}

def check_fold(index, spec):
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.context import relative_branch_target
    from scripts.game_data.damage_snapshot_primary_attr_flow import partition
    from scripts.game_data.damage_snapshot_atk_scale_flow import check_physical_coverage
    from scripts.game_data.damage_snapshot_abi import require_ordinary_value_type, require_ordinary_type
    from scripts.game_data.damage_snapshot_max_poise_flow import check_reference_definition
    from scripts.game_data.damage_snapshot_append_flow import _check_named_provider
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
    rows=partition(index.pe.bytes_at_va(body.pointer,body.size),body.pointer,spec['entryInstructionLengths'])
    grammar=check_fold_rows(rows)
    calls={str(n):relative_branch_target(bytes.fromhex(rows[n]['bytes']),int(rows[n]['va'],16),source='damageScaleFold') for n in (9,26,38,46,61,64,66)}
    _check_named_provider(index,calls['9'],spec['patchMethod'],['int'],'bool',is_static=True)
    provider=[index.metadata.methods[n['methodIndex']] for n in index.names_by_pointer.get(calls['46'],()) if f"{n.get('type')}.{n.get('method')}"==spec['providerMethod']]
    _require(bool(provider),'fold-provider-identity',spec['providerMethod'],hex(calls['46']))
    zone=index.types[spec['zoneType']]
    for m in provider:
        args=list(index.metadata.parameters_for(m))
        _require(m.declaring_type==owner.index and not m.flags&0x10 and len(args)==1,'fold-provider-prototype','same concrete instance owner and one Zone argument',m.declaring_type)
        check_reference_definition(selected,args[0].type_index,spec['zoneType'],zone.index,'fold.Zone')
        require_ordinary_type(selected,m.return_type,'double','fold.provider.return')
        name=index.metadata.string(args[0].name_index)
        _require(index.parameter_location(calls['46'],spec['providerMethod'],name)==('register','rdx'),'fold-zone-slot','rdx',name)
    b=bytes.fromhex(rows[13]['bytes']); operand=int(rows[13]['va'],16)+len(b)+int.from_bytes(b[4:],'little',signed=True)
    bits=index.pe.bytes_at_va(operand,8)
    _require(bits.hex()==spec['seedBits'],'fold-seed-original-bits',spec['seedBits'],bits.hex())
    sections=[s for s in index.pe.sections if s['virtualAddress']<=operand-index.pe.image_base and operand-index.pe.image_base+8<=s['virtualAddress']+s['rawSize']]
    _require(len(sections)==1,'fold-seed-complete-section','unique full eight-byte raw-backed section',sections)
    pe=[check_operand_pe(index.pe,operand+n) for n in (0,4)]
    common={**grammar,'symbol':body.symbol,'receiverABI':receiver,'providerConcreteDefinitionIndex':owner.index,'zoneConcreteDefinitionIndex':zone.index,
        'selectedPhysicalPdataRanges':check_physical_coverage(index.extents,[rows]),'actualCalls':{n:hex(p) for n,p in calls.items()},
        'originalSeedOperand':hex(operand),'originalSeedBits':bits.hex(),'seedPeChunks':pe,
        'boundary':spec['evidenceBoundary']}
    return [{**common,'claim':'damageScaleEmptySignedBoundSeedNormalReturn','selectedInstructionIndices':grammar['emptyNormalReturnIndices'],'selection':'ordinary patch return AL=0, anonymous static readiness nonzero and carriers nonnull; opaque count normal post-call EAX interpreted signed Int32 c<=0','formula':'original Double seed XMM6.low64 -> XMM0.low64 -> full normal RET'},
        {**common,'claim':'damageScalePositiveOrderedDoubleFoldNormalReturn','selection':'same unpatched ready/non-null guards, opaque count normal EAX c in [1,INT32_MAX], each iteration readiness nonzero','formula':'i0=0; request item EDX=i; ordinary named scale returns r_i in XMM0.low64; INC32 i then p_(i+1)=MULSD(p_i,r_i); signed CMP/JL repeats while i<c; full saved-state/frame RET returns p_c'}]
