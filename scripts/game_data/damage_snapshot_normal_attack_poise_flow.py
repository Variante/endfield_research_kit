"""Selected named Poise Single multiplication, widening and normal return."""
from scripts.game_data.damage_snapshot_cache_flow import _require
from scripts.game_data.il2cpp.context import relative_branch_target
import struct


def check_operand_pe(pe, operand):
    """Authenticate raw backing, section flags and possible base relocations."""
    b = pe.buf
    def u16(o):
        _require(0 <= o <= len(b)-2, 'normal-poise-pe-range', 'two file bytes', o)
        return struct.unpack_from('<H',b,o)[0]
    def u32(o):
        _require(0 <= o <= len(b)-4, 'normal-poise-pe-range', 'four file bytes', o)
        return struct.unpack_from('<I',b,o)[0]
    coff = u32(60)+4; optional = coff+20; size = u16(coff+16)
    _require(u16(optional) == 0x20b and size >= 160, 'normal-poise-pe-header', 'PE32+ relocation directory present', size)
    rva = operand-pe.image_base; matches = []
    for n in range(u16(coff+2)):
        off = optional+size+40*n
        va, raw_size = u32(off+12),u32(off+16)
        if va <= rva and rva+4 <= va+raw_size:
            matches.append((off,u32(off+36)))
    _require(len(matches) == 1, 'normal-poise-operand-section', 'unique four-byte raw-backed section', matches)
    off,flags = matches[0]
    _require(flags & 0x40000000 and not flags & (0x80000000|0x20000000),
             'normal-poise-operand-section-flags', 'PE readable nonwritable nonexecutable', hex(flags))
    rr,rs = u32(optional+152),u32(optional+156)
    overlaps = []
    if rs:
        sections = [s for s in pe.sections if s['virtualAddress'] <= rr and rr+rs <= s['virtualAddress']+s['rawSize']]
        _require(len(sections) == 1, 'normal-poise-relocation-directory', 'complete raw-backed directory', [rr,rs])
        section = sections[0]; cursor = section['rawPointer']+rr-section['virtualAddress']; end = cursor+rs
        while cursor < end:
            page, block = u32(cursor),u32(cursor+4)
            _require(block >= 8 and block%2 == 0 and cursor+block <= end,
                     'normal-poise-relocation-block', 'bounded even complete block', block)
            for at in range(cursor+8,cursor+block,2):
                entry=u16(at); kind=entry>>12; address=page+(entry&4095)
                _require(kind in (0,1,2,3,10),'normal-poise-relocation-kind',
                         'reviewed ABSOLUTE/HIGH/LOW/HIGHLOW/DIR64 only',kind)
                width={0:0,10:8,3:4,1:2,2:2}[kind]
                if kind and address < rva+4 and address+width > rva:
                    overlaps.append([kind,address])
            cursor += block
    _require(not overlaps, 'normal-poise-operand-relocations', 'no possible overlapping base relocation', overlaps)
    return {'sectionCharacteristics':hex(flags),'operandRawBackedBytes':4,
            'baseRelocationOverlapProvedAbsent':True,'liveMemoryProtectionObserved':False}


def check_rows(prefix, footer, pointer, field_offset, providers, literal):
    _require(type(field_offset) is int and 0 <= field_offset < 128,
             'normal-poise-field-offset', 'positive typed disp8', field_offset)
    forms = ['48895c2408', '48896c2410', '4889742418', '57', '4883ec50',
             '488bea', '488bf9', '33d2', 'patch-id', '498bd9', '498bf0',
             'patch-call', '84c0', 'patch-excluded', '488b4f'+bytes([field_offset]).hex(),
             '4533c0', '488bd3', 'scalar-call', 'multiply', 'f30f5ac0',
             '66480f7ec0', 'footer-jump']
    _require(len(prefix) == len(forms), 'normal-poise-prefix-count', len(forms), len(prefix))
    at = pointer; excluded = None; footer_target = None; operand = None; calls = {}
    for row, form in zip(prefix, forms):
        raw = bytes.fromhex(row['bytes'])
        _require(int(row['va'], 16) == at, 'normal-poise-contiguous', hex(at), row['va'])
        if form.endswith('-call'):
            _require(len(raw) == 5 and raw[0] == 0xe8, 'normal-poise-call', 'direct CALL', raw.hex())
            target = relative_branch_target(raw, at, source='normalAttackPoise')
            _require(target == providers[form], 'normal-poise-provider', providers[form], target)
            calls[form] = hex(target)
        elif form == 'patch-id':
            _require(len(raw) == 5 and raw[0] == 0xb9, 'normal-poise-patch-id', 'MOV ECX imm32', raw.hex())
        elif form in ('patch-excluded', 'footer-jump'):
            opcode = 0x75 if form == 'patch-excluded' else 0xeb
            _require(len(raw) == 2 and raw[0] == opcode, 'normal-poise-edge', hex(opcode), raw.hex())
            target = at+2+int.from_bytes(raw[1:], 'little', signed=True)
            if form == 'patch-excluded': excluded = target
            else: footer_target = target
        elif form == 'multiply':
            _require(len(raw) == 8 and raw[:4] == bytes.fromhex('f30f5905'),
                     'normal-poise-mulss', 'MULSS XMM0, RIP m32 complete 8B', raw.hex())
            operand = at+8+int.from_bytes(raw[4:], 'little', signed=True)
        else:
            _require(raw == bytes.fromhex(form), 'normal-poise-instruction', form, raw.hex())
        at += len(raw)
    prefix_end = at
    tail = ['488b5c2460', '488b6c2468', '488b742470', '4883c450', '5f', 'c3']
    _require(len(footer) == len(tail), 'normal-poise-footer-count', len(tail), len(footer))
    at = footer_target
    for row, form in zip(footer, tail):
        raw = bytes.fromhex(row['bytes'])
        _require(int(row['va'],16) == at and raw == bytes.fromhex(form),
                 'normal-poise-footer', [hex(at),form], [row['va'],raw.hex()])
        at += len(raw)
    _require(not pointer <= excluded < prefix_end and not footer_target <= excluded < at,
             'normal-poise-excluded-patch', 'outside both selected spans', excluded)
    _require(len(literal) == 4, 'normal-poise-operand-width', 4, len(literal))
    return {'prefixEnd':prefix_end, 'footerStart':footer_target, 'selectedRetEnd':at,
            'selectedByteCount':prefix_end-pointer+at-footer_target,
            'excludedPatchTarget':hex(excluded), 'actualCalls':calls,
            'operandVA':operand, 'selectedImageOperandBits':literal.hex(),
            'operationOrder':'MULSS ordinary getter XMM0.low32 by actual m32 operand, then CVTSS2SD, then MOVQ XMM0.low64 to RAX',
            'frameDeltaBytes':88, 'normalRetStackDeltaBytes':8,
            'fullOtherPathsProved':False, 'liveOperandOrProviderValuesObserved':False,
            'constantZeroResultProved':False}


def check_normal_attack_poise(index, consumer_proof, spec):
    from scripts.game_data.damage_snapshot_abi import require_ordinary_type, require_ordinary_value_type, require_ordinary_double_array, require_ordinary_field
    from scripts.game_data.damage_snapshot_append_flow import _check_named_provider
    from scripts.game_data.damage_snapshot_forward_flow import _parameter
    from scripts.game_data.damage_snapshot_multiply_formula_flow import check_result_records
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    _require(consumer_proof.get('claim') == 'snapshotCacheIndexToReturn',
             'normal-poise-result-witness', 'fresh concrete CalcResult consumer', consumer_proof.get('claim'))
    selected = NativeReferenceContext(index.image, index=index)
    body = index.body(spec['type'], spec['method'])
    _require(not selected.is_value_type(spec['type']) and selected.parent(spec['type']) == spec['baseType'],
             'normal-poise-owner', spec['baseType'], selected.parent(spec['type']))
    def methods(symbol, pointer):
        return [index.metadata.methods[r['methodIndex']] for r in index.names_by_pointer.get(pointer, ())
                if f"{r.get('type')}.{r.get('method')}" == symbol]
    reference_owner, reference_method = consumer_proof['symbol'].rsplit('.', 1)
    reference = index.body(reference_owner, reference_method)
    records = [index.pe.bytes_at_va(selected.type_pointer(m.return_type),16)
               for m in methods(reference.symbol,reference.pointer)]
    named = methods(body.symbol,body.pointer)
    _require(bool(named), 'normal-poise-named-definition', 'actual named Evaluate definitions', body.symbol)
    for method in named:
        _require(not method.flags & 0x10 and len(index.metadata.parameters_for(method)) == 7,
                 'normal-poise-instance-signature', 'instance seven ordinary arguments', method.flags)
        require_ordinary_value_type(selected,method.return_type,spec['returnType'],'normalPoise.result')
        check_result_records(index.pe.bytes_at_va(selected.type_pointer(method.return_type),16),records)
        for name, typ in spec['referenceParameters'].items():
            require_ordinary_type(selected,_parameter(selected,method,name).type_index,typ,'normalPoise.'+name,reference_kind=0x12)
        for name in ('attackerOverrideAttributes','defenderOverrideAttributes'):
            require_ordinary_double_array(selected,_parameter(selected,method,name).type_index,'normalPoise.'+name)
    for name, register in (('this','rcx'),('attacker','rdx'),('defender','r8'),('blackboard','r9')):
        _require(index.parameter_location(body.pointer,body.symbol,name) == ('register',register),
                 'normal-poise-input-register', [name,register], index.parameter_location(body.pointer,body.symbol,name))
    owner, typ, offset = selected.field(spec['scaleField'])
    _require((owner,typ) == (spec['type'],spec['scalarParameterType']), 'normal-poise-field-owner',
             [spec['type'],spec['scalarParameterType']], [owner,typ])
    require_ordinary_field(selected,spec['scaleField'],typ,'normalPoise.atkScale')
    rows = body.rows
    _require(len(rows) >= 28, 'normal-poise-body-rows', 'selected prefix and footer available', len(rows))
    prefix = rows[:22]
    providers = {name:relative_branch_target(bytes.fromhex(prefix[n]['bytes']),int(prefix[n]['va'],16),source='normalAttackPoise')
                 for name,n in (('patch-call',11),('scalar-call',17))}
    _check_named_provider(index,providers['patch-call'],spec['patchMethod'],['int'],'bool',is_static=True)
    _check_named_provider(index,providers['scalar-call'],spec['scalarGetter'],[typ,spec['referenceParameters']['blackboard']],'float',is_static=True)
    jump = bytes.fromhex(prefix[-1]['bytes']); jump_va = int(prefix[-1]['va'],16)
    _require(len(jump) == 2 and jump[0] == 0xeb, 'normal-poise-footer-edge', 'short direct JMP', jump.hex())
    footer_va = jump_va+2+int.from_bytes(jump[1:],'little',signed=True)
    footer = [r for r in rows if footer_va <= int(r['va'],16) < footer_va+21]
    multiply = bytes.fromhex(prefix[18]['bytes']); multiply_va = int(prefix[18]['va'],16)
    _require(len(multiply) == 8 and multiply[:4] == bytes.fromhex('f30f5905'),
             'normal-poise-operand-encoding', 'complete 8B RIP MULSS', multiply.hex())
    operand = multiply_va+8+int.from_bytes(multiply[4:],'little',signed=True)
    literal = index.pe.bytes_at_va(operand,4)
    operand_pe = check_operand_pe(index.pe,operand)
    proof = check_rows(prefix,footer,body.pointer,offset,providers,literal)
    _require(literal.hex() == spec['reviewedOperandBits'], 'normal-poise-selected-operand', spec['reviewedOperandBits'],literal.hex())
    _require(body.pointer in index.extents and proof['selectedRetEnd'] == index.extents[body.pointer],
             'normal-poise-physical-extent', 'complete selected RET ends actual pdata range', proof['selectedRetEnd'])
    for part in (prefix,footer):
        start = int(part[0]['va'],16); raw = b''.join(bytes.fromhex(r['bytes']) for r in part)
        _require(index.pe.bytes_at_va(start,len(raw)) == raw, 'normal-poise-raw-coverage', 'complete selected raw partition', hex(start))
    return {**proof, 'operandImageStorage':operand_pe, 'symbol':body.symbol, 'claim':'normalAttackPoiseSingleOperandMultiplyThenDoubleResult',
            'typedScaleField':spec['scaleField'], 'ordinaryReturnConcreteOwnerJoined':True,
            'boundary':'The complete selected false-patch path requests the named ordinary Single getter with this.atkScale and incoming blackboard; MULSS uses the actual selected-image four-byte operand, then CVTSS2SD and MOVQ return the low64 through the full restoring RET. Selected disk operand bits require original body/operand unchanged in the running image; no live memory protection, value, floating environment or provider internals are observed. Valid initialized receiver/field/frame storage, normal Win64 callees preserving saved registers/frame and SSE normal completion under actual MXCSR rounding/DAZ/FTZ/exception state remain conditions. The Single multiply is not a Double multiply and is not simplified to a constant zero for NaN, infinity or signed zero. Other patch paths, final live Poise and runtime subtype selection remain open.'}
