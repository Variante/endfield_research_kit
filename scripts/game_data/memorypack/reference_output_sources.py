"""Selected reference outputs joined to metadata-owned wrapper destinations.

An eight-byte reference transfer is not an eight-byte serialized value.
Independent child readers own the wire grammar. Provider selection and error
execution remain conditional; each reviewed normal program retains its own
reader, ref-wrapper, temporary and runtime-field ownership.
"""
from __future__ import annotations

import struct
from typing import Any, Callable
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets, runtime_type_name
from scripts.game_data.memorypack import named_native_records as named
from scripts.game_data.memorypack import struct_output_sources as structs


def _program(image: Any, window: dict, rows: list, fail: Callable[..., None]) -> None:
    if (not isinstance(rows, list) or not rows or any(not isinstance(r, list) or len(r) != 2
            or type(r[0]) is not int or not isinstance(r[1], str) for r in rows)):
        fail('reference-program-shape', 'bounded instruction program', rows)
    for i, (at, raw_hex) in enumerate(rows):
        raw = bytes.fromhex(raw_hex)
        if (not raw or not window['startRva'] <= at < at + len(raw) <= window['endRva']
                or i and rows[i-1][0] + len(bytes.fromhex(rows[i-1][1])) != at):
            fail('reference-program-boundary', window, rows[i])
    image.check_instruction_windows(rows, label='referenceOutputSource')


def _return_type(image: Any, context: dict, fail: Callable[..., None]) -> None:
    method = image.metadata.methods[context['methodSpec'][0]]
    section = image.metadata.sections['genericContainers']
    at = section.offset + method.generic_container_index * 16
    if method.generic_container_index < 0 or not section.offset <= at <= section.offset + section.size - 16:
        fail('reference-generic-container', 'bounded method container', method.generic_container_index)
    container = struct.unpack_from('<iiii', image.metadata.buf, at)
    pointer = image.pe.u64_at_va(int(image.registration['types'], 16) + method.return_type * 8)
    raw = image.pe.bytes_at_va(pointer, 16)
    if (image.type_name(method.declaring_type) != 'MemoryPack.MemoryPackReader'
            or image.metadata.string(method.name_index) not in ('ReadValue', 'ReadPackable')
            or method.flags & 0x10 or method.parameter_count != 0
            or container[:3] != (method.index, 1, 1)
            or raw[10:12] != b'\x1e\0' or int.from_bytes(raw[:8], 'little') != container[3]):
        fail('reference-source-definition', 'instance ReadValue/ReadPackable<T>() returns its sole MVAR', context)


def _aliases(image: Any, normal: dict, proof: dict, fail: Callable[..., None]) -> None:
    rows = proof['parentProgram']; _program(image, normal, rows, fail)
    if rows[0][0] != normal['startRva']:
        fail('reference-parent-entry', normal['startRva'], rows[0])
    seen = set(); aliases = {'rbx': '488BD9', 'rdi': '488BFA'}
    # Canonical multi-byte NOPs and this GC address calculation do not write
    # the two incoming nonvolatile pointer aliases. The bounded decoder does
    # not understand them; all other unknown instructions refuse the proof.
    no_alias_write = {'0F1F00', '660F1F840000000000', '0F1F840000000000',
                      '660F1F440000', '0F1F440000', '4803D5'}
    for at, raw_hex in rows:
        if raw_hex in no_alias_write:
            continue
        raw = bytes.fromhex(raw_hex)
        decoded = image.mapper.decode_x64_subset(raw, image.pe.image_base + at, stop_offset=len(raw))
        if len(decoded) != 1 or decoded[0]['text'].startswith('db'):
            fail('reference-parent-instruction', 'one understood instruction', [at, raw_hex, decoded])
        register = (decoded[0].get('write') or {}).get('register')
        if register in {'rbx', 'ebx', 'bx', 'bl', 'bh', 'rdi', 'edi', 'di', 'dil'}:
            if register not in aliases or register in seen or raw_hex != aliases[register]:
                fail('reference-parent-pointer-clobber', aliases, [at, raw_hex, register])
            seen.add(register)
        if raw[0] == 0xe8 and seen != set(aliases):
            fail('reference-parent-late-alias', sorted(aliases), sorted(seen))
    if seen != set(aliases):
        fail('reference-parent-aliases', sorted(aliases), sorted(seen))


def validate_reference_join(image: Any, source: dict, proof: dict, *, fail: Callable[..., None]) -> None:
    """Prove a typed reference result reaches one exact owned Data field."""
    image.validate_method_row(proof['readerMethod'], label='referenceOutputSource')
    normal = next(w for w in source['codeWindows'] if w['startRva'] == proof['readerMethod'][3])
    structs.check_reader_ref_wrapper_abi(image, proof, fail=fail)
    _aliases(image, normal, proof, fail)
    owner = proof['runtimeTypeDefinition']; wrapper = proof['wrapperTypeDefinition']
    if image.type_name(owner) != proof['runtimeTypeName'] or image.type_name(wrapper) != proof['wrapperTypeName']:
        fail('reference-owner-type', proof['runtimeTypeName'], image.type_name(owner))
    fields = [f for f in image.metadata.fields_for(image.metadata.types[wrapper])
              if image.metadata.string(f.name_index) == proof['instanceFieldName']]
    if len(fields) != 1:
        fail('reference-wrapper-instance', 'one exact typed instance field', len(fields))
    table = int(image.registration['types'], 16)
    raw = image.pe.bytes_at_va(image.pe.u64_at_va(table + fields[0].type_index * 8), 16)
    slot = runtime_type_field_offsets(image.metadata, image.pe, image.registration, wrapper)[proof['instanceFieldName']]
    if raw[10:12] != b'\x12\0' or int.from_bytes(raw[:8], 'little') != owner or slot != 16:
        fail('reference-wrapper-instance-type', 'exact reference Data at wrapper offset sixteen', raw.hex())
    wanted = [f for f in image.metadata.fields_for(image.metadata.types[owner])
              if image.metadata.string(f.name_index) == proof['fieldName']]
    if len(wanted) != 1:
        fail('reference-runtime-field', proof['fieldName'], len(wanted))
    pointer = image.pe.u64_at_va(table + wanted[0].type_index * 8)
    declared = runtime_type_name(image.pe, image.metadata, pointer)
    context = next(c for c in source['nestedContexts'] if c['instructionRva'] == proof['sourceContextInstructionRva'])
    if declared != proof['declaredType']:
        fail('reference-field-declaration', proof['declaredType'], declared)
    options = ({'load_prefixes': (b'\x48\x8b\x35',)}
               if proof['mode'] == 'provider-stack-reference-r8' else {})
    named.check_typed_context(image, context, declared, label='referenceOutputSource', fail=fail, **options)
    _return_type(image, context, fail)
    offset = runtime_type_field_offsets(image.metadata, image.pe, image.registration, owner)[proof['fieldName']]
    if not 0 <= offset < 128:
        fail('reference-field-offset', 'bounded disp8 field', offset)
    rows = proof['transferProgram']; _program(image, normal, rows, fail)
    mode = proof['mode']; store = b'\x49\x89\x40' + bytes([offset])
    actual = [bytes.fromhex(r[1]) for r in rows]
    if mode == 'rax-reference-r8':
        if len(actual)!=7:fail('reference-return-transfer','seven complete transfer instructions',rows)
        call = proof['sourceCall']; named.check_call(image, call, label='referenceOutputSource', fail=fail)
        if (actual[:4] != [b'\x48\x85\xf6', actual[1], b'\x4c\x8b\x46\x10', b'\x4d\x85\xc0']
                or len(actual) != 7 or len(actual[1]) != 6 or actual[1][:2] != b'\x0f\x84'
                or len(actual[4]) != 6 or actual[4][:2] != b'\x0f\x84'
                or len(actual[5]) != 7 or actual[5][:2] != b'\x83\x3d' or actual[6] != store
                or call['rva'] + 5 != rows[0][0]):
            fail('reference-return-transfer', 'complete RAX -> exact Data field via RSI wrapper', rows)
        arguments = proof['argumentProgram']; _program(image, normal, arguments, fail)
        # Both optimized call layouts retain RCX=reader and RDX=closed context.
        arg_raw = [bytes.fromhex(r[1]) for r in arguments]
        expected = ([b'\x48\x8b\xcb', bytes.fromhex(context['instructionHex']), b'\x48\x8b\x37']
                    if proof.get('argumentOrder') == 'reader-context-wrapper'
                    else [bytes.fromhex(context['instructionHex']), b'\x48\x8b\xcb', b'\x48\x8b\x37'])
        if (arg_raw != expected or arguments[-1][0] + len(arg_raw[-1]) != call['rva']):
            fail('reference-source-arguments', [v.hex().upper() for v in expected], arguments)
    elif mode == 'provider-stack-reference-r8':
        if len(actual)!=10:fail('reference-provider-transfer','ten complete transfer instructions',rows)
        expected = [b'\x48\x85\xed', actual[1], b'\x4c\x8b\x45\x10', b'\x4d\x85\xc0', actual[4],
                    actual[5], b'\x48\x8b\x44\x24\x40', b'\x4c\x89\x7c\x24\x50', actual[8], store]
        if (len(actual) != 10 or actual != expected or any(len(actual[i]) != 6 or actual[i][:2] != b'\x0f\x84' for i in (1,4))
                or len(actual[5]) != 7 or actual[5][:2] != b'\x83\x3d'
                or len(actual[8]) != 7 or actual[8][:3] != b'\x4c\x8d\x3d'):
            fail('reference-provider-transfer', 'complete stack reference -> exact Data field via RBP wrapper', rows)
        args = proof['argumentProgram']; _program(image, normal, args, fail)
        packet = proof['sourceCall']; named.check_call(image, packet, label='referenceOutputSource', fail=fail)
        patterns = [b'\xb9\x05\0\0\0', b'\x4c\x8d\x4c\x24\x40', b'\x4c\x8b\xc3', b'\x48\x8b\xd0']
        if [bytes.fromhex(r[1]) for r in args] != patterns or args[-1][0]+3 != packet['rva'] or packet['rva']+5 != rows[0][0]:
            fail('reference-provider-arguments', 'reader and independently initialized output reference slot', args)
        init = proof['outputInit']; image.check_instruction_windows([init], label='referenceOutputSource')
        if init[1] != '48C744244000000000' or not context['instructionRva'] < init[0] < args[0][0]:
            fail('reference-provider-output-init', 'separate null reference slot before conditional formatter invocation', init)
        cache = proof['contextProgram']; _program(image, normal, cache, fail)
        if (cache[0][0] != context['instructionRva'] or cache[0][1] != context['instructionHex']
                or [bytes.fromhex(r[1]) for r in cache][-2:] != [b'\x48\x8b\x46\x38', b'\x48\x8b\x08']
                or cache[-1][0]+3 != proof['providerResolverCall']['rva']):
            fail('reference-provider-context', 'selected typed MethodInfo -> its cached formatter resolver', cache)
        named.check_call(image, proof['providerResolverCall'], label='referenceOutputSource', fail=fail)
        gate = proof['providerBranch']; _program(image, normal, gate, fail)
        raw_gate = [bytes.fromhex(r[1]) for r in gate]
        if (raw_gate[:1] != [b'\x48\x85\xc0'] or len(raw_gate) != 2 or len(raw_gate[1]) != 2 or raw_gate[1][0] != 0x74
                or gate[0][0] != proof['providerResolverCall']['rva']+5
                or gate[1][0]+2+struct.unpack('b',raw_gate[1][1:])[0] != rows[0][0]):
            fail('reference-provider-null-branch', 'null formatter retains initialized null slot', gate)
    else:
        fail('reference-mode', 'explicit reviewed reference transfer profile', mode)
    # Both normal transfers keep the reference result until the final store.
    end = rows[-1][0] + len(bytes.fromhex(rows[-1][1]))
    if proof['parentProgram'][-1][0] + len(bytes.fromhex(proof['parentProgram'][-1][1])) != end:
        fail('reference-parent-program-end', end, proof['parentProgram'][-1])
