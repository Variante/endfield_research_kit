"""Own provider registration/lookup arguments without claiming cache effects."""
from __future__ import annotations
import struct
from typing import Any
from .program_grammar import ProgramGrammar
from .formatter_composition import validate_typed_usage_context
from .reference_layouts import NativeReferenceContext
from .protocol import runtime_type_field_offsets


def _owned(image, proof, *, label, complete=False):
    image.check_windows(proof['codeWindows'], label=label)
    image.check_instruction_windows(proof['program'], label=label)
    rows = []
    for at, raw_hex in proof['program']:
        raw = bytes.fromhex(raw_hex)
        if not any(w['startRva'] <= at < at + len(raw) <= w['endRva'] for w in proof['codeWindows']):
            raise ValueError(f'{label}: instruction outside authenticated body')
        decoded = image.mapper.decode_x64_subset(raw, image.pe.image_base + at, stop_offset=len(raw))
        if len(decoded) != 1 or 'db ' in decoded[0]['text']:
            raise ValueError(f'{label}: complete instruction required')
        rows.append(decoded[0])
    if not rows or proof['program'][0][0] != proof['codeWindows'][0]['startRva']:
        raise ValueError(f'{label}: selected trace must start at owned entry')
    if complete and (len(proof['codeWindows']) != 1
            or proof['program'][-1][0] + len(bytes.fromhex(proof['program'][-1][1])) != proof['codeWindows'][0]['endRva']):
        raise ValueError(f'{label}: complete caller body coverage required')
    return rows


def _rip(grammar, image, prefix, *, cell=None):
    row = grammar.row(); raw = bytes.fromhex(row['bytes']); at = int(row['va'], 16)
    start = bytes.fromhex(prefix)
    if len(raw) != 7 or raw[:len(start)] != start:
        grammar.fail('rip-load', prefix, row)
    if prefix in ('803D','833D') and raw[-1] != 0:
        grammar.fail('initialization-guard-zero', 'compare guard against zero', row)
    target = at + 7 + struct.unpack_from('<i', raw, 3)[0]
    if cell is not None and target != image.pe.image_base + cell:
        grammar.fail('same-usage-cell', cell, target - image.pe.image_base)
    return row


def validate_registration_state_transfers(image: Any, c: dict) -> dict:
    """Complete RegisterWrap/public caller plus selected named lookup-hit return.

    The storage expression is equal only for stable initialized cell contents.
    Class/static-storage semantics, dictionary mutation/retrieval and runtime
    receiver identity are deliberately not inferred from this expression.
    """
    label = 'formatterRegistrationState'; base = image.pe.image_base
    owner = c['providerType']; offsets = c['classCarrierOffsets']; calls = c['calls']
    selected = NativeReferenceContext(image)
    td = selected.index.types[owner]
    field_spec = c['dictionaryField']
    fields = [f for f in image.metadata.fields_for(td) if image.metadata.string(f.name_index) == field_spec['name']]
    if len(fields) != 1 or not selected.field_attributes(fields[0].type_index) & 0x10:
        raise ValueError(f'{label}: unique declared static formatter dictionary required')
    field = fields[0]
    actual_offset = runtime_type_field_offsets(image.metadata, image.pe, image.registration, td.index)[field_spec['name']]
    if selected.type_name(field.type_index) != field_spec['typeName'] or actual_offset != field_spec['selectedOffsetWord']:
        raise ValueError(f'{label}: selected static field representation differs')
    for key in ('providerClass', 'setter', 'lookup'):
        usage = c['usages'][key]
        validate_typed_usage_context(image, usage, label=label)
        if key == 'providerClass':
            if usage['tag'] != 1 or usage['typeName'] != owner:
                raise ValueError(f'{label}: exact provider class usage required')
        elif (usage['tag'] != 6 or usage['typeName'] != c['dictionaryDefinition']
                or usage['methodName'] != ('set_Item' if key == 'setter' else 'TryGetValue')
                or usage['classArguments'] != c['dictionaryArguments'] or usage['methodArguments'] != []):
            raise ValueError(f'{label}: exact closed dictionary method usage required')
    if (c['usages']['setter']['methodSpec'][1] != c['usages']['lookup']['methodSpec'][1]
            or field_spec['typeName'] != c['dictionaryDefinition'] + '<' + ','.join(c['dictionaryArguments']) + '>'):
        raise ValueError(f'{label}: same closed dictionary instantiation required')
    for role, row in c['methods'].items():
        image.validate_method_row(row, label=label)
        method = image.metadata.methods[row[0]]
        names = [selected.type_name(p.type_index) for p in image.metadata.parameters_for(method)]
        expected = ['MemoryPack.IMemoryPackFormatter', 'System.Type'] if role == 'registerWrap' else ['System.Type']
        result = 'void' if role == 'registerWrap' else 'MemoryPack.IMemoryPackFormatter'
        if (row[1] != owner or row[2] != {'registerWrap':'RegisterWrap', 'publicLookup':'GetFormatter', 'namedLookup':'GetFormatter_'}[role]
                or not method.flags & 0x10 or method.generic_container_index != -1
                or names != expected or selected.type_name(method.return_type) != result):
            raise ValueError(f'{label}: nongeneric static provider declaration differs')
    cell = c['usages']['providerClass']['usageCellRva']
    setter_cell = c['usages']['setter']['usageCellRva']; lookup_cell = c['usages']['lookup']['usageCellRva']
    storage = offsets['staticStorage']; initialized = offsets['initialized']; slot = actual_offset

    rows = _owned(image, c['registerProgram'], label=label, complete=True)
    g = ProgramGrammar(rows, label=label + '.register')
    g.take('mov [rsp+0x8], rbx', 'push rdi', 'sub rsp, 0x20')
    _rip(g, image, '803D'); g.take('mov rbx, rdx', 'mov rdi, rcx'); g.branch('je', 'usageInit')
    g.mark('warm'); _rip(g, image, '488B05', cell=cell)
    g.take(f'cmp [rax+0x{initialized:x}], 0x0'); g.branch('je', 'classInit')
    g.mark('loadStorage'); g.take(f'mov rcx, [rax+0x{storage:x}]', f'mov rcx, [rcx+0x{slot:x}]', 'test rcx, rcx')
    g.branch('je', 'nullDictionary'); _rip(g, image, '4C8B0D', cell=setter_cell)
    g.take('mov r8, rdi', 'mov rdx, rbx', 'mov rbx, [rsp+0x30]', 'add rsp, 0x20', 'pop rdi')
    tail = g.branch('jmp')
    if tail['target'] != base + calls['dictionarySetter']:
        g.fail('setter-tail', calls['dictionarySetter'], tail['target'] - base)
    g.mark('usageInit')
    _rip(g, image, '488D0D', cell=setter_cell); g.call(base + calls['usageInit'])
    _rip(g, image, '488D0D', cell=cell); g.call(base + calls['usageInit'])
    flag = g.row(); raw = bytes.fromhex(flag['bytes'])
    if len(raw) != 7 or raw[:2] != b'\xc6\x05' or raw[-1] != 1:
        g.fail('usage-initialized-store', 'one-byte RIP flag set to one', flag)
    guard = bytes.fromhex(rows[3]['bytes'])
    guard_cell = int(rows[3]['va'],16) + 7 + struct.unpack_from('<i',guard,2)[0]
    flag_cell = int(flag['va'],16) + 7 + struct.unpack_from('<i',raw,2)[0]
    if flag_cell != guard_cell: g.fail('same-initialized-flag', guard_cell, flag_cell)
    g.branch('jmp', 'warm'); g.mark('classInit'); g.take('mov rcx, rax')
    g.call(base + calls['classInit']); _rip(g, image, '488B05', cell=cell); g.branch('jmp', 'loadStorage')
    g.mark('nullDictionary'); g.call(base + calls['nullDictionary']); g.take('int3'); g.finish()
    if c['registerProgram']['program'][0][0] != c['methods']['registerWrap'][3]:
        raise ValueError(f'{label}: RegisterWrap entry differs')

    rows = _owned(image, c['publicLookupProgram'], label=label, complete=True)
    g = ProgramGrammar(rows, label=label + '.publicLookup')
    g.take('push rbx', 'sub rsp, 0x20'); _rip(g,image,'803D')
    g.take('mov rbx, rcx'); g.branch('jne', 'warm')
    _rip(g,image,'488D0D',cell=cell); g.call(base + calls['usageInit'])
    flag = g.row(); raw = bytes.fromhex(flag['bytes']); guard = bytes.fromhex(rows[2]['bytes'])
    if (len(raw) != 7 or raw[:2] != b'\xc6\x05' or raw[-1] != 1
            or int(flag['va'],16) + 7 + struct.unpack_from('<i',raw,2)[0]
            != int(rows[2]['va'],16) + 7 + struct.unpack_from('<i',guard,2)[0]):
        g.fail('same-usage-initialized-flag', 'exact guard flag set to one', flag)
    g.mark('warm'); _rip(g,image,'488B0D',cell=cell)
    g.take(f'cmp [rcx+0x{initialized:x}], 0x0'); g.branch('jne', 'forward')
    g.call(base + calls['classInit']); g.mark('forward')
    g.take('mov rcx, rbx', 'add rsp, 0x20', 'pop rbx'); tail = g.branch('jmp')
    if tail['target'] != base + calls['formatterResult']:
        g.fail('same-physical-result-tail', calls['formatterResult'], tail['target'] - base)
    g.finish()
    if c['publicLookupProgram']['program'][0][0] != c['methods']['publicLookup'][3]:
        raise ValueError(f'{label}: public lookup entry differs')

    # Reuse the existing selected-edge validator for the actual RET path.
    from scripts.game_data.memorypack.read_value_reference_sources import _profile
    def fail(check, expected, actual):
        raise ValueError(f'{label}.{check}: expected={str(expected)[:512]} actual={str(actual)[:512]}')
    expected = ['48895C2410','57','4883EC20',None,'488BD9',None,None,'488364243000',None,None,
        '488B88' + storage.to_bytes(4,'little').hex().upper(), '488B49' + slot.to_bytes(1,'little').hex().upper(),
        '4885C9',None,None,'4C8D442430','488BD3',None,'84C0',None,'488B442430','488B5C2438','4883C420','5F','C3']
    proof = c['lookupHitProgram']
    _profile(image, proof, expected, {5:('75',True),13:('0F84',False),19:('0F85',True)},
        {8:'lookupClassInit',17:'dictionaryLookup'}, {3:'803D',6:'488B0D',9:'488B05',14:'4C8B0D'}, (), (), calls, fail=fail)
    for at in (6,9):
        raw=bytes.fromhex(proof['program'][at][1]); rva=proof['program'][at][0]
        if rva+7+struct.unpack_from('<i',raw,3)[0]!=cell: fail('lookup-same-class-cell',cell,rva)
    at=14;raw=bytes.fromhex(proof['program'][at][1]);rva=proof['program'][at][0]
    if rva+7+struct.unpack_from('<i',raw,3)[0]!=lookup_cell: fail('lookup-closed-context-cell',lookup_cell,rva)
    if proof['program'][0][0] != c['methods']['namedLookup'][3]: fail('lookup-entry',c['methods']['namedLookup'][3],proof['program'][0])
    return {'completeRegisterWrapCallerProved':True,'registerKeyAndFormatterForwardedTogether':True,
        'completePublicLookupCallerProved':True,'samePhysicalFormatterResultEntryProved':True,
        'sameProviderUsageAndDictionaryAddressExpressionProved':True,
        'sameClosedDictionarySetterLookupInstantiationProved':True,'selectedNamedLookupHitOutputReturned':True,
        'dictionaryOutputAndReturnBits':64,'lookupPredicateBits':'AL',
        'staticFieldRepresentationBoundary':'structuralOnly','runtimeStaticStorageObserved':False,
        'dictionaryMutationAndRetrievalProved':False,'actualArrayCallbackTargetProved':False,
        'callbackCursorEqualityProved':False,'positiveListAdmitted':False,'wholeRootAdmitted':False}
