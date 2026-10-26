"""Buffered outputs stored through a cached Data getter, including interleaving.

Reference framing, getter slow paths and barrier effects are separate proofs.
Every selected argument/bridge instruction is authenticated; preservation
across calls is conditional on the ordinary Win64 ABI.
"""
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from . import named_native_records as named
from . import setter_output_sources as outputs
from . import reference_output_sources as references
from . import struct_output_sources as structs
from .inherited_setter_output_sources import _primitive_return_type

LABEL = 'getterDirectActionSource'


def _null_branch(normal, row, fail):
    raw = outputs._branch(bytes.fromhex(row[1]), condition=4, fail=fail)
    target = row[0]+len(raw)+int.from_bytes(raw[2:] if len(raw)==6 else raw[1:], 'little', signed=True)
    if normal['startRva'] <= target < normal['endRva']:
        fail('getter-direct-null-target', 'failure outside selected normal window', row)
    return raw


def _expected_bridge(normal, member, *, final, fail):
    proof = member['getterDirectStore']; rows = proof['bridgeProgram']
    mode = proof['mode']; offset = member['assignment']['fieldOffset']
    if type(offset) is not int or not 0 <= offset < 128:
        fail('getter-direct-offset', 'disp8 field', offset)
    count = 10 if final else 11 if mode == 'single-return' else 10 if mode == 'reference-return' else 9
    if len(rows) != count:
        fail('getter-direct-bridge-count', count, rows)
    save = {'normalized-byte-return': b'\x0f\xb6\xd8' if final else b'\x0f\xb6\xe8',
            'scalar32-return': b'\x8b\xe8', 'single-return': b'\x0f\x28\xf0',
            'reference-return': b'\x48\x8b\xe8'}.get(mode)
    if save is None or final and mode != 'normalized-byte-return':
        fail('getter-direct-mode', 'reference, Boolean, DWORD or Single; final Boolean', mode)
    expected = [save, b'\x48\x85\xff' if final else b'\x48\x85\xf6',
        _null_branch(normal, rows[2], fail), b'\x33\xd2', b'\x48\x8b\xcf' if final else b'\x48\x8b\xce',
        bytes.fromhex(rows[5][1]), b'\x48\x85\xc0', _null_branch(normal, rows[7], fail)]
    if mode == 'reference-return':
        expected += [b'\x48\x8d\x48'+bytes((offset,)), b'\x48\x89\x68'+bytes((offset,))]
    elif mode == 'single-return':
        # The next wrapper/reader arguments are deliberately scheduled before
        # this store; they do not alter RAX or XMM6.
        expected += [b'\x48\x8b\x37', b'\x48\x8b\xcb', b'\xf3\x0f\x11\x70'+bytes((offset,))]
    elif final:
        expected += [b'\x0f\x28\x74\x24\x20', b'\x88\x58'+bytes((offset,))]
    else:
        expected += [(b'\x40\x88\x68' if mode == 'normalized-byte-return' else b'\x89\x68')+bytes((offset,))]
    return expected


def validate_getter_direct_outputs(image, source, record, *, source_string_helpers, fail):
    proof = record['getterDirectOutputSource']
    if proof.get('mode') != 'reader-rbx-ref-wrapper-rdi-common-direct-derived-getter-final-byte':
        fail('getter-direct-parent-mode', 'explicit common/derived direct-store profile', proof.get('mode'))
    normal = next(w for w in source['codeWindows'] if w['startRva'] == record['readerMethod'][3])
    selected = NativeReferenceContext(image)
    parent = proof['parentProgram']; final_member = record['members'][-1]
    final_args = final_member['getterDirectStore']['argumentProgram']
    dereference = next((r for r in final_args if r[1]=='488B3F'), None)
    if (dereference is None or parent[0][0] != normal['startRva']
            or parent[-1] != [final_member['assignment']['rva'], final_member['assignment']['rawHex']]):
        fail('getter-direct-parent-extent', 'entry through final direct store', parent)
    structs.check_reader_ref_wrapper_abi(image, record, fail=fail)
    structs._check_pointer_aliases(image, normal, [r for r in parent if r[0]<dereference[0]], label=LABEL, fail=fail)
    references._program(image, normal, parent, fail)
    final_call = final_member['sourceCall']['rva']
    for at, raw_hex in parent:
        if at < dereference[0]: continue
        raw = bytes.fromhex(raw_hex)
        decoded = image.mapper.decode_x64_subset(raw, image.pe.image_base+at, stop_offset=len(raw))
        if len(decoded)!=1 or decoded[0]['text'].startswith('db'):
            fail('getter-direct-parent-instruction', 'one decoded instruction', [at, raw_hex])
        dest = (decoded[0].get('write') or {}).get('register')
        if dest in ('rbx','ebx','bx','bl','bh','rdi','edi','di','dil'):
            allowed = [at,raw_hex]==dereference or at==final_call+5 and raw_hex=='0FB6D8'
            if not allowed: fail('getter-direct-final-alias', 'only final wrapper dereference and Boolean save', [at,raw_hex])
    outputs._getter(image, record, proof, source, selected, fail)
    checked = []
    previous = record['members'][3]['assignment']['rva']+len(bytes.fromhex(record['members'][3]['assignment']['rawHex']))
    for ordinal, member in enumerate(record['members'][4:], start=4):
        transfer = member['getterDirectStore']; final = ordinal==len(record['members'])-1
        mode = transfer['mode']; args=transfer['argumentProgram']; call=member['sourceCall']; assignment=member['assignment']
        context = next((c for c in source['nestedContexts'] if c['instructionRva']==member.get('sourceContextInstructionRva')), None)
        arg_mode = transfer['argumentMode']
        values = {'reader': b'\x48\x8b\xcb', 'wrapper': b'\x48\x8b\x3f' if final else b'\x48\x8b\x37'}
        if context is not None:
            named.check_typed_context(image, context, member['declaredType'], label=LABEL, fail=fail)
            (_primitive_return_type if mode=='scalar32-return' else references._return_type)(image, context, fail)
            values['context']=bytes.fromhex(context['instructionHex'])
        try: expected_args=[values[k] for k in arg_mode]
        except KeyError: fail('getter-direct-argument-mode', 'reader/wrapper and actual optional context', arg_mode)
        if sorted(arg_mode)!=sorted(values): fail('getter-direct-argument-set', sorted(values), arg_mode)
        scheduled=transfer.get('scheduledPreviousStore')
        if scheduled is not None:
            if scheduled != [record['members'][ordinal-1]['assignment']['rva'], record['members'][ordinal-1]['assignment']['rawHex']]:
                fail('getter-direct-interleaved-store', 'immediately previous member store', scheduled)
            expected_args.insert(2, bytes.fromhex(scheduled[1]))
        outputs._program(image, normal, args, expected_args, fail)
        if args[-1][0]+len(expected_args[-1])!=call['rva'] or args[0][0]<previous and scheduled is None:
            fail('getter-direct-argument-order', 'source immediately after checked arguments', args)
        named.check_call(image, call, label=LABEL, fail=fail)
        if mode in ('normalized-byte-return','scalar32-return','single-return'):
            outputs.validate_primitive_source(image,source,member,fail=fail)
        elif member['declaredType']=='string':
            if context is not None or call['targetRva'] not in source_string_helpers:
                fail('getter-direct-string-source', 'independently proved physical UTF8 helper', call)
        elif context is None: fail('getter-direct-reference-context', 'typed reference source', member['fieldName'])
        owner,declared,offset=selected.field(record['runtimeTypeName']+'::'+member['fieldName'])
        if (owner!=record['runtimeTypeName'] or declared!=member['declaredType']
                or mode=='normalized-byte-return' and declared!='bool'
                or mode=='single-return' and declared!='float'
                or mode=='scalar32-return' and declared!='int' and not selected.is_enum(declared)
                or assignment.get('kind')!='direct-store' or assignment.get('baseRegister')!=0
                or assignment.get('fieldOwnerTypeDefinition')!=record['runtimeTypeDefinition'] or offset!=assignment['fieldOffset']):
            fail('getter-direct-field', 'exact owned Data field and representation', assignment)
        rows=transfer['bridgeProgram']; wanted=_expected_bridge(normal,member,final=final,fail=fail)
        outputs._program(image,normal,rows,wanted,fail)
        getter=transfer['getterCall'];named.check_call(image,getter,label=LABEL,fail=fail)
        if getter['targetRva']!=proof['getterMethod'][3] or rows[5][0]!=getter['rva']:
            fail('getter-direct-getter-call', proof['getterMethod'], getter)
        if rows[0][0]!=call['rva']+5 or rows[-1]!=[assignment['rva'],assignment['rawHex']] or member['sourceToDestinationHex']!=''.join(r[1] for r in rows[:-1]):
            fail('getter-direct-complete-transfer', 'uninterrupted source through owned store', rows)
        previous=assignment['rva']+len(bytes.fromhex(assignment['rawHex']))
        if mode=='reference-return':
            barrier=transfer['barrierCall'];named.check_call(image,barrier,label=LABEL,fail=fail)
            if barrier['rva']!=previous or barrier!=member['observedBarrierCall']:
                fail('getter-direct-barrier-call', 'actual call immediately after owned reference store', barrier)
            previous+=5
        checked.append(member['fieldName'])
    return {'derivedFieldsForwardedToOwnedData':checked,'evidenceBoundary':'conditional',
        'condition':'buffered source, coherent getter normal path and preserving Win64 calls',
        'referenceFramingProved':False,'barrierEffectsKnown':False,'runtimeExecutionKnown':False}
