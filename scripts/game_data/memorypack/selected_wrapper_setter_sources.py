"""Selected reader/ref-wrapper caller and generated setter transfer profiles.

The profile contains every build-specific declaration. This algorithm checks
all selected ordinary caller/setter instructions; stored reference grammar,
constructor/cold paths and reference-helper effects are separate obligations.
"""
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.memorypack import named_native_records as named
from scripts.game_data.memorypack import reference_output_sources as references
from scripts.game_data.memorypack import setter_output_sources as setters
from scripts.game_data.memorypack import struct_output_sources as structs

MODE = 'reader-rbx-ref-wrapper-rdi-selected-wrapper-rsi-setter-transfers'
LABEL = 'selectedWrapperSetterTransfers'


def _bad(fail, check, expected, actual):
    fail('selected-wrapper-' + check, expected, actual)


def _program(image, window, rows, expected, fail):
    references._program(image, window, rows, fail)
    actual = [bytes.fromhex(row[1]) for row in rows]
    if actual != expected:
        _bad(fail, 'program', [row.hex().upper() for row in expected], rows)


def _branch(row, condition, fail):
    raw = bytes.fromhex(row[1])
    if len(raw) == 2 and raw[0] == 0x70 + condition:
        return raw, row[0] + 2 + int.from_bytes(raw[1:], 'little', signed=True)
    if len(raw) == 6 and raw[:2] == bytes((0x0F, 0x80 + condition)):
        return raw, row[0] + 6 + int.from_bytes(raw[2:], 'little', signed=True)
    _bad(fail, 'branch', 'exact bounded conditional branch', row)


def _operand(prefix, opcode, disp8_modrm, offset, fail):
    if type(offset) is not int or not 0 <= offset <= 0x7FFFFFFF:
        _bad(fail, 'field-offset', 'nonnegative signed DWORD displacement', offset)
    if offset <= 127:
        return prefix + opcode + bytes((disp8_modrm, offset))
    return prefix + opcode + bytes((disp8_modrm + 0x40,)) + offset.to_bytes(4, 'little')


def check_parent_aliases(image, window, record, proof, fail):
    rows = proof['parentProgram']
    references._program(image, window, rows, fail)
    structs.check_reader_ref_wrapper_abi(image, record, fail=fail)
    if not rows or rows[0][0] != record['readerMethod'][3]:
        _bad(fail, 'parent-entry', record['readerMethod'], rows[:1])
    last = record['members'][-1]
    if rows[-1][0] != last['assignment']['rva'] or len(bytes.fromhex(rows[-1][1])) != 5:
        _bad(fail, 'parent-end', 'prefix through final setter call', rows[-1:])
    reader_alias = b'\x48\x8b\xd9'
    ref_alias = b'\x48\x8b\xfa'
    final_load = b'\x48\x8b\x3f'
    aliases = set()
    final_at = proof['finalWrapperLoad'][0]
    first_source = record['members'][0]['sourceCall']['rva']
    seen_final = False
    for at, value in rows:
        raw = bytes.fromhex(value)
        decoded = image.mapper.decode_x64_subset(raw, image.pe.image_base + at, stop_offset=len(raw))
        if len(decoded) != 1 or decoded[0]['text'].startswith('db'):
            _bad(fail, 'parent-instruction', 'one understood complete instruction', [at, value, decoded])
        register = (decoded[0].get('write') or {}).get('register')
        family = ('reader' if register in ('rbx', 'ebx', 'bx', 'bl', 'bh')
                  else 'wrapper-ref' if register in ('rdi', 'edi', 'di', 'dil') else None)
        if family:
            expected = reader_alias if family == 'reader' else ref_alias
            if raw == expected and family not in aliases:
                aliases.add(family)
            elif family == 'wrapper-ref' and at == final_at and raw == final_load and not seen_final and aliases == {'reader', 'wrapper-ref'}:
                seen_final = True
            else:
                _bad(fail, 'parent-alias-clobber', 'sole incoming alias and deliberate final dereference', [at, value, register])
        if register in ('rsi', 'esi', 'si', 'sil') and at >= first_source:
            if raw != b'\x48\x8b\x37' or seen_final:
                _bad(fail, 'parent-selected-wrapper-clobber', 'typed wrapper reloaded from preserved ref before its source', [at, value, register])
        if raw[:1] == b'\xe8' and aliases != {'reader', 'wrapper-ref'}:
            _bad(fail, 'parent-late-alias', 'both incoming aliases before every call', [at, aliases])
        if seen_final and at > final_at and register in ('rdi', 'edi', 'di', 'dil'):
            _bad(fail, 'parent-final-wrapper-clobber', 'final wrapper retained until last setter', [at, value])
    if aliases != {'reader', 'wrapper-ref'} or not seen_final:
        _bad(fail, 'parent-aliases', 'reader/ref aliases and exactly one final wrapper dereference', [aliases, seen_final])


def check_bridge(image, window, member, transfer, *, final, contexts, fail):
    context = contexts.get(member.get('sourceContextInstructionRva'))
    args = transfer['argumentProgram']
    wrapper = b'\x48\x8b\x3f' if final else b'\x48\x8b\x37'
    reader = b'\x48\x8b\xcb'
    if context:
        load = bytes.fromhex(context['instructionHex'])
        options = ([load, reader, wrapper], [reader, load, wrapper])
    else:
        options = ([wrapper, reader], [reader, wrapper])
    actual_args = [bytes.fromhex(row[1]) for row in args]
    if actual_args not in options:
        _bad(fail, 'argument-register-transfers', 'exact independent RCX reader, RDX context and selected wrapper loads', args)
    expected_args = actual_args
    _program(image, window, args, expected_args, fail)
    call = member['sourceCall']
    named.check_call(image, call, label=LABEL, fail=fail)
    if args[-1][0] + len(expected_args[-1]) != call['rva']:
        _bad(fail, 'argument-end', 'complete arguments immediately before source', args)
    if context:
        if [context['instructionRva'], context['instructionHex']] not in args:
            _bad(fail, 'argument-context', context['instructionRva'], args)
        named.check_typed_context(image, context, member['declaredType'], label=LABEL, fail=fail)
    rows = transfer['bridgeProgram']
    if len(rows) != 5:
        _bad(fail, 'bridge-count', 5, rows)
    branch, target = _branch(rows[1], 4, fail)
    if rows[0][0] <= target <= member['assignment']['rva']:
        _bad(fail, 'bridge-null-branch', 'failure target outside transfer program', target)
    move = {'reference-return': b'\x48\x8b\xd0', 'normalized-byte-return': b'\x0f\xb6\xd0',
            'int32-return': b'\x8b\xd0', 'single-return': b'\x0f\x28\xc8'}.get(transfer['mode'])
    if move is None:
        _bad(fail, 'return-mode', 'explicit scalar/reference return transfer', transfer['mode'])
    expected = [b'\x48\x85\xff' if final else b'\x48\x85\xf6', branch,
                b'\x45\x33\xc0', move, b'\x48\x8b\xcf' if final else b'\x48\x8b\xce']
    _program(image, window, rows, expected, fail)
    if (rows[0][0] != call['rva'] + 5
            or rows[-1][0] + len(expected[-1]) != member['assignment']['rva']
            or b''.join(expected).hex().upper() != member['sourceToDestinationHex']):
        _bad(fail, 'bridge-order', 'returned bits go directly to exact setter arguments', transfer)
    named.check_call(image, member['assignment'], label=LABEL, fail=fail)


def check_setter(image, record, member, transfer, getter, selected, fail):
    method_row = transfer['setterMethod']
    image.validate_method_row(method_row, label=LABEL)
    method = image.metadata.methods[member['setterMethodIndex']]
    parameters = list(image.metadata.parameters_for(method))
    if (method_row[0] != method.index or method_row[3] != member['assignment']['targetRva']
            or method.declaring_type != record['wrapperTypeDefinition'] or method.flags & 0x10
            or len(parameters) != 1 or selected.type_name(parameters[0].type_index) != member['declaredType']
            or selected.type_name(method.return_type) != 'void'):
        _bad(fail, 'setter-signature', 'selected instance void setter with exact declared argument', method_row)
    owner, actual_type, offset = selected.field(record['runtimeTypeName'] + '::' + member['fieldName'])
    if owner != record['runtimeTypeName'] or actual_type != member['declaredType'] or offset != transfer['fieldOffset']:
        _bad(fail, 'setter-field', [record['runtimeTypeName'], member['declaredType'], transfer['fieldOffset']], [owner, actual_type, offset])
    mode = transfer['mode']
    parameter = image.pe.bytes_at_va(selected.type_pointer(parameters[0].type_index), 16)
    if (mode == 'reference-return' and (parameter[10] not in (0x12, 0x0E) or parameter[11])
            or mode == 'normalized-byte-return' and actual_type != 'bool'
            or mode == 'single-return' and actual_type != 'float'
            or mode == 'int32-return' and actual_type != 'int' and not selected.is_enum(actual_type) and member.get('unmanagedSource') is None):
        _bad(fail, 'setter-representation', 'reference, bool, raw Single or independently proved DWORD', [mode, actual_type, parameter.hex()])
    rows = transfer['setterProgram']
    window = transfer['setterWindow']
    image.check_windows([window], label=LABEL)
    count = 12 if mode == 'reference-return' else 11
    if len(rows) != count:
        _bad(fail, 'setter-count', count, rows)
    call = transfer['getterCall']
    named.check_call(image, call, label=LABEL, fail=fail)
    if call['targetRva'] != getter[3] or rows[4][0] != call['rva']:
        _bad(fail, 'setter-getter', 'exact common typed getter at selected program position', call)
    branch, target = _branch(rows[6], 4, fail)
    if rows[0][0] <= target < rows[-1][0] + len(bytes.fromhex(rows[-1][1])):
        _bad(fail, 'setter-null-branch', 'null/error target outside normal setter return', target)
    source_call_raw = image.pe.bytes_at_va(image.pe.image_base + call['rva'], 5)
    if mode == 'single-return':
        expected = [b'\x48\x83\xec\x38', b'\x0f\x29\x74\x24\x20', b'\x33\xd2', b'\x0f\x28\xf1',
            source_call_raw, b'\x48\x85\xc0', branch,
            _operand(b'\xf3', b'\x0f\x11', 0x70, offset, fail), b'\x0f\x28\x74\x24\x20', b'\x48\x83\xc4\x38', b'\xc3']
    else:
        capture = {'reference-return': b'\x48\x8b\xda', 'normalized-byte-return': b'\x0f\xb6\xda', 'int32-return': b'\x8b\xda'}[mode]
        expected = [b'\x40\x53', b'\x48\x83\xec\x20', capture, b'\x33\xd2', source_call_raw, b'\x48\x85\xc0', branch]
        if mode == 'reference-return':
            tail = bytes.fromhex(rows[-1][1])
            if len(tail) != 5 or tail[0] != 0xE9:
                _bad(fail, 'reference-tail', 'complete post-store tail after restoring frame/RBX', rows[-1])
            target_tail = rows[-1][0] + 5 + int.from_bytes(tail[1:], 'little', signed=True)
            if target_tail != transfer['postStoreTailTargetRva']:
                _bad(fail, 'reference-tail-target', transfer['postStoreTailTargetRva'], target_tail)
            expected += [_operand(b'\x48', b'\x8d', 0x48, offset, fail), _operand(b'\x48', b'\x89', 0x58, offset, fail), b'\x48\x83\xc4\x20', b'\x5b', tail]
        else:
            expected += [_operand(b'', b'\x88' if mode == 'normalized-byte-return' else b'\x89', 0x58, offset, fail), b'\x48\x83\xc4\x20', b'\x5b', b'\xc3']
    _program(image, window, rows, expected, fail)
    if rows[0][0] != method_row[3]:
        _bad(fail, 'setter-entry', method_row[3], rows[0])


def _selected_getter_branches(rows, fail):
    end = rows[-1][0] + len(bytes.fromhex(rows[-1][1]))
    targets = [_branch(rows[i], condition, fail)[1] for i, condition in ((4, 4), (6, 4), (9, 5))]
    if any(rows[0][0] <= target < end for target in targets) or targets[1] != targets[2]:
        _bad(fail, 'getter-selected-branches', 'init/null/unequal branches leave the complete normal return, with one shared cold target', targets)


def validate(image, source, record, profile, *, fail):
    if profile.get('mode') != MODE:
        _bad(fail, 'mode', MODE, profile.get('mode'))
    indices = [i for i, m in enumerate(record['members']) if m['assignment']['kind'] == 'setter']
    if profile['memberIndices'] != indices or len(profile['transfers']) != len(indices):
        _bad(fail, 'member-selection', 'every and only generated setter member', profile['memberIndices'])
    window = next(w for w in source['codeWindows'] if w['startRva'] == record['readerMethod'][3])
    image.check_windows(source['codeWindows'], label=LABEL)
    check_parent_aliases(image, window, record, profile, fail)
    selected = NativeReferenceContext(image)
    getter_proof = {key: profile[key] for key in ('getterMethod', 'getterProgram', 'baseInstanceField', 'cachedInstanceField')}
    setters._getter(image, record, getter_proof, source, selected, fail)
    _selected_getter_branches(profile['getterProgram'], fail)
    contexts = {row['instructionRva']: row for row in source['nestedContexts']}
    unmanaged_sizes = None
    generic_entries = None
    results = []
    for index, transfer in zip(indices, profile['transfers'], strict=True):
        member = record['members'][index]
        if transfer['fieldName'] != member['fieldName']:
            _bad(fail, 'field-order', member['fieldName'], transfer['fieldName'])
        check_bridge(image, window, member, transfer, final=index == len(record['members']) - 1, contexts=contexts, fail=fail)
        if member.get('unmanagedSource') is not None:
            if transfer['mode'] != 'int32-return' or member['kind'] != 'scalar32' or 'primitiveSource' in transfer:
                _bad(fail, 'unmanaged-source-mode', 'independent DWORD cursor source, without a primitive substitute', transfer)
            if unmanaged_sizes is None:
                unmanaged_sizes = named.unmanaged_value_sizes_from_image(image)
                generic_entries = named.GenericEntries(image)
            named.check_unmanaged_source(image, source, member, unmanaged_sizes, generic_entries,
                record=record['runtimeTypeName'], width=4, label=LABEL,
                fail=lambda check, expected, actual, **scope: fail(check, expected, {'scope': scope, 'actual': actual}))
        elif transfer['mode'] != 'reference-return':
            primitive_member = {**member, 'primitiveSource': transfer['primitiveSource']}
            setters.validate_primitive_source(image, source, primitive_member, fail=fail)
            primitive_rows = transfer['primitiveSource']['program']
            primitive_end = primitive_rows[-1][0] + len(bytes.fromhex(primitive_rows[-1][1]))
            for branch_index, condition in ((6, 12), (11, 8)):
                target = _branch(primitive_rows[branch_index], condition, fail)[1]
                if primitive_rows[0][0] <= target < primitive_end:
                    _bad(fail, 'primitive-cold-branch', 'refill/overflow branches leave selected buffered normal source', target)
        check_setter(image, record, member, transfer, profile['getterMethod'], selected, fail)
        results.append({'fieldName': member['fieldName'], 'mode': transfer['mode'], 'fieldOffset': transfer['fieldOffset'],
                        'normalPrimitiveSetterReturns': transfer['mode'] != 'reference-return', 'referenceStoredBeforeTail': transfer['mode'] == 'reference-return'})
    return {'fields': results, 'conditionalOwnedSetterTransfersProved': len(results),
        'incomingAliasesAndFinalWrapperReloadProved': True, 'sameBaseAndDerivedReferentOnSelectedGetterConditionProved': True,
        'condition': 'coherent compatible reader/ref-wrapper and cached/base Data references at every reached getter; initialized getter branch; ordinary Win64 calls preserve nonvolatile state. Reference helper effects and actual returned types remain unsupplied.',
        'bufferedPrimitiveSourcesProved': sum(transfer['mode'] != 'reference-return' and member.get('unmanagedSource') is None
            for member, transfer in zip((record['members'][i] for i in indices), profile['transfers'], strict=True)),
        'unmanagedCursorSourcesProved': sum(record['members'][i].get('unmanagedSource') is not None for i in indices),
        'referenceHelperEffectsProved': False,
        'physicalGenericSourceIdentityProved': False, 'constructorAndColdPathEffectsProved': False,
        'childSchemaAdmitted': False, 'wholeActionAdmitted': False, 'wholeRootAdmitted': False, 'runtimeExecutionKnown': False}
