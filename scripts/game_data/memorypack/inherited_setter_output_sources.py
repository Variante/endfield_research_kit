"""Common inherited setters and derived cached-instance setter transfers.

Reference return widths are not serialized widths. Primitive buffered helpers,
typed source arguments, wrapper ancestry and complete selected setter programs
are checked independently; cold/init/error execution remains outside the proof.
"""
import struct
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext, validate_reference_ancestor_chain
from . import named_native_records as named
from . import setter_output_sources as outputs
from . import reference_output_sources as references

LABEL = 'inheritedSetterOutputSource'


def _primitive_return_type(image, context, fail):
    method = image.metadata.methods[context['methodSpec'][0]]
    section = image.metadata.sections['genericContainers']
    at = section.offset+method.generic_container_index*16
    if method.generic_container_index < 0 or not section.offset <= at <= section.offset+section.size-16:
        fail('inherited-setter-primitive-container', 'bounded method generic container', method.generic_container_index)
    container = struct.unpack_from('<iiii', image.metadata.buf, at)
    pointer = image.pe.u64_at_va(int(image.registration['types'], 16)+method.return_type*8)
    raw = image.pe.bytes_at_va(pointer, 16)
    if (image.type_name(method.declaring_type) != 'MemoryPack.MemoryPackReader'
            or image.metadata.string(method.name_index) != 'ReadUnmanaged'
            or method.flags & 0x10 or method.parameter_count != 0
            or container[:3] != (method.index, 1, 1) or raw[10:12] != b'\x1e\0'
            or int.from_bytes(raw[:8], 'little') != container[3]):
        fail('inherited-setter-primitive-return-type', 'instance ReadUnmanaged<T>() returns its sole MVAR', context)


def validate_inherited_setter_outputs(image, source, record, *, fail):
    proof = record['inheritedSetterOutputSource']
    if proof['mode'] != 'reader-rdi-ref-wrapper-rbx-common-base-and-derived-setters':
        fail('inherited-setter-parent-mode', 'explicit common/derived setter profile', proof['mode'])
    normal = next(w for w in source['codeWindows'] if w['startRva'] == record['readerMethod'][3])
    selected = NativeReferenceContext(image)
    outputs._parent(image, normal, record, proof, fail)
    outputs._getter(image, record, proof, source, selected, fail)
    validate_reference_ancestor_chain(selected, record['runtimeTypeName'], [proof['baseDataName']], proof['baseDataName'])
    validate_reference_ancestor_chain(selected, record['wrapperTypeName'], [proof['wrapperBaseName']], proof['wrapperBaseName'])
    reloads = proof['wrapperReloads']
    actual_reloads = [r for m in record['members'] for r in m['setterTransfer']['argumentProgram'] if r[1] == '488B33']
    if reloads != actual_reloads or len(reloads) != len(record['members'])-1:
        fail('inherited-setter-wrapper-load', 'one checked RBX -> RSI reload for every non-final source', reloads)
    image.check_instruction_windows(reloads, label=LABEL)
    first_reload = reloads[0][0]
    for at, raw_hex in proof['parentProgram']:
        if at <= first_reload: continue
        raw = bytes.fromhex(raw_hex)
        rows = image.mapper.decode_x64_subset(raw, image.pe.image_base+at, stop_offset=len(raw))
        destination = (rows[0].get('write') or {}).get('register')
        if destination in ('rsi', 'esi', 'si', 'sil') and [at, raw_hex] not in reloads:
            fail('inherited-setter-wrapper-clobber', 'stable RSI wrapper after its load', [at, raw_hex])
    primitive_count = 0
    for ordinal, member in enumerate(record['members']):
        transfer = member['setterTransfer']; mode = transfer['mode']
        context = next((c for c in source['nestedContexts'] if c['instructionRva'] == member.get('sourceContextInstructionRva')), None)
        if context is not None:
            named.check_typed_context(image, context, member['declaredType'], label=LABEL, fail=fail)
            (_primitive_return_type if mode in ('normalized-byte-return', 'int32-return') else references._return_type)(image, context, fail)
        if mode in ('normalized-byte-return', 'int32-return'):
            outputs.validate_primitive_source(image, source, member, fail=fail); primitive_count += 1
        final = ordinal == len(record['members'])-1
        args = transfer['argumentProgram']; wanted_args = []
        if context is not None: wanted_args.append(bytes.fromhex(context['instructionHex']))
        wrapper = b'\x48\x8b\x1b' if final else b'\x48\x8b\x33'
        wanted_args.extend([b'\x48\x8b\xcf', wrapper] if context is not None else [wrapper, b'\x48\x8b\xcf'])
        outputs._program(image, normal, args, wanted_args, fail)
        if args[-1][0]+len(wanted_args[-1]) != member['sourceCall']['rva']:
            fail('inherited-setter-source-arguments', 'immediately before actual source call', args)
        named.check_call(image, member['sourceCall'], label=LABEL, fail=fail)
        rows = transfer['transferProgram']; actual = [bytes.fromhex(r[1]) for r in rows]
        move = {'normalized-byte-return': b'\x0f\xb6\xd0', 'int32-return': b'\x8b\xd0', 'reference-return': b'\x48\x8b\xd0'}[mode]
        if len(actual) != 5: fail('inherited-setter-bridge-count', 5, rows)
        expected = [b'\x48\x85\xdb' if final else b'\x48\x85\xf6',
            outputs._branch(actual[1], condition=4, fail=fail), b'\x45\x33\xc0', move,
            b'\x48\x8b\xcb' if final else b'\x48\x8b\xce']
        outputs._program(image, normal, rows, expected, fail)
        if (rows[0][0] != member['sourceCall']['rva']+5
                or rows[-1][0]+len(expected[-1]) != member['assignment']['rva']
                or b''.join(actual).hex().upper() != member['sourceToDestinationHex']):
            fail('inherited-setter-complete-bridge', member['assignment'], rows)
        setter = transfer['setterProgram']; method = image.metadata.methods[member['setterMethodIndex']]
        parameters = list(image.metadata.parameters_for(method))
        if method.flags & 0x10 or len(parameters) != 1 or selected.type_name(parameters[0].type_index) != member['declaredType'] or selected.type_name(method.return_type) != 'void':
            fail('inherited-setter-signature', 'instance void setter and exact parameter', member['fieldName'])
        owner_name = proof['baseDataName'] if ordinal < record['inheritedMemberCount'] else record['runtimeTypeName']
        owner, type_name, offset = selected.field(owner_name+'::'+member['fieldName'])
        if owner != owner_name or type_name != member['declaredType'] or not 0 <= offset < 128:
            fail('inherited-setter-field', [owner_name, member['declaredType'], 'disp8'], [owner, type_name, offset])
        window = next(w for w in source['codeWindows'] if w['startRva'] == member['assignment']['targetRva'])
        if ordinal < record['inheritedMemberCount']:
            if image.type_name(method.declaring_type) != proof['wrapperBaseName'] or len(setter) != 7:
                fail('inherited-setter-common-owner', proof['wrapperBaseName'], image.type_name(method.declaring_type))
            _owner, field_type, instance_offset = selected.field(proof['wrapperBaseName']+'::'+proof['baseInstanceField'])
            if field_type != proof['baseDataName'] or not 0 <= instance_offset < 128:
                fail('inherited-setter-common-instance', proof['baseDataName'], field_type)
            wanted = [b'\x48\x83\xec\x28', b'\x48\x8b\x41'+bytes((instance_offset,)), b'\x48\x85\xc0',
                outputs._branch(bytes.fromhex(setter[3][1]), condition=4, fail=fail),
                (b'\x88\x50' if mode == 'normalized-byte-return' else b'\x89\x50')+bytes((offset,)),
                b'\x48\x83\xc4\x28', b'\xc3']
            outputs._program(image, window, setter, wanted, fail)
        elif mode == 'int32-return':
            if method.declaring_type != record['wrapperTypeDefinition'] or len(setter) != 11:
                fail('inherited-setter-derived-int32', 'derived eleven-instruction setter', setter)
            call = transfer['getterCall']; named.check_call(image, call, label=LABEL, fail=fail)
            if call['targetRva'] != proof['getterMethod'][3] or setter[4][0] != call['rva']:
                fail('inherited-setter-int32-getter', proof['getterMethod'], call)
            wanted = [b'\x40\x53', b'\x48\x83\xec\x20', b'\x8b\xda', b'\x33\xd2', bytes.fromhex(setter[4][1]),
                b'\x48\x85\xc0', outputs._branch(bytes.fromhex(setter[6][1]), condition=4, fail=fail),
                b'\x89\x58'+bytes((offset,)), b'\x48\x83\xc4\x20', b'\x5b', b'\xc3']
            outputs._program(image, window, setter, wanted, fail)
        else:
            outputs._setter(image, record, member, source, proof['getterMethod'], selected, fail)
        if setter[0][0] != window['startRva']:
            fail('inherited-setter-entry', window['startRva'], setter[0])
    return {'fieldsForwardedToOwnedData': len(record['members']), 'primitiveSourceReadsProved': primitive_count,
        'inheritedFieldsChecked': record['inheritedMemberCount'], 'evidenceBoundary': 'conditional',
        'condition': 'selected buffered/getter normal paths, valid coherent references and ordinary preserving Win64 calls',
        'sourceReferenceWireWidthsProved': False, 'runtimeExecutionKnown': False}
