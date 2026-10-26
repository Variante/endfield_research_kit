"""Finite Alpha56 caller fragments, separate from whole caller admission.

These programs own the actual hidden-output setup and every local/source bit
through the named setter or four direct destination stores. The full caller
entry, other members, lifecycle and frame bounds must still be composed.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.alpha_blend_value_sources import TYPE


def need(key, condition):
    if not condition:
        raise ValueError('generatedAlphaBlendTransfer.' + key)


def _stack(opcode, number, displacement):
    need('finite-local-displacement-and-vector', number in (0, 1) and type(displacement) is int
         and 32 <= displacement < 256)
    short = displacement < 128
    return opcode + bytes(((0x44 if short else 0x84) | (number << 3), 0x24)).hex() + displacement.to_bytes(1 if short else 4, 'little').hex()


def _local_address(register, displacement):
    need('finite-hidden-or-argument-local', register in ('rcx', 'rdx') and type(displacement) is int
         and 32 <= displacement < 256)
    short = displacement < 128
    return ('488d' + ('4c' if register == 'rcx' else '54') + '24' + bytes((displacement,)).hex()) if short else (
        '488d' + ('8c' if register == 'rcx' else '94') + '24' + displacement.to_bytes(4, 'little').hex())


def program(regions, entry, *, reader, output, context_cell, source, field, barrier,
            hidden_local, setter=None, argument_local=None, path_factory=None):
    from scripts.game_data.memorypack.generated_inline_constructor_sources import _nonnull
    from scripts.game_data.memorypack.generated_member_sources import _displacement
    need('finite-observed-caller-roles', (reader, output) in (('rdi', 'rbx'), ('rbx', 'rdi')))
    need('actual-source-context-and-destination', all(type(n) is int and n > 0 for n in (context_cell, source, barrier))
         and type(field) is int and field >= 16 and (setter is None or type(setter) is int and setter > 0))
    need('finite-whole56-hidden-local', type(hidden_local) is int and hidden_local in (32, 48))
    need('literal-copy-profile', setter is None and argument_local is None
         or setter is not None and (reader, output) == ('rdi', 'rbx') and hidden_local == 32 and argument_local == 96)
    need('callable-only-path-factory', path_factory is None or callable(path_factory))
    g = (BytesPath if path_factory is None else path_factory)(regions, entry)
    if reader == 'rbx':
        g.take('488bd3')
    context_site = g.at
    need('same-actual-R8-context-cell', g.relative('4c8b05') == context_cell)
    g.take(_local_address('rcx', hidden_local), '488b33' if output == 'rbx' else '488b37')
    if reader == 'rdi':
        g.take('488bd7')
    source_call = g.at
    g.call(source)
    g.take('4885f6')
    exits = [_nonnull(g)]
    stores = []
    copies = []
    if setter is None:
        g.take('488b4e10', '4885c9')
        exits.append(_nonnull(g))
        g.take(_stack('0f10', 0, hidden_local), _stack('0f10', 1, hidden_local+16))
        stores.append(dict(instructionVa=g.at, sourceOffset=0, bytes=16))
        g.take(_displacement('0f1141', field), _stack('0f10', 0, hidden_local+32))
        stores.append(dict(instructionVa=g.at, sourceOffset=16, bytes=16))
        g.take(_displacement('0f1149', field+16), _stack('f20f10', 1, hidden_local+48))
        stores.append(dict(instructionVa=g.at, sourceOffset=32, bytes=16))
        g.take(_displacement('0f1141', field+32))
        stores.append(dict(instructionVa=g.at, sourceOffset=48, bytes=8))
        g.take(_displacement('f20f1149', field+48),
               ('4883c1'+bytes((field+8,)).hex()) if field+8 < 128 else
               ('4881c1'+(field+8).to_bytes(4, 'little').hex()))
        transfer_call = g.at
        g.call(barrier)
    else:
        g.take(_stack('0f10', 0, hidden_local), '4533c0', _local_address('rdx', argument_local),
               _stack('0f10', 1, hidden_local+16), '488bce')
        for offset, width, number, load in ((0,16,0,True),(16,16,1,True),(32,16,0,False),(48,8,1,False)):
            copies.append(dict(instructionVa=g.at, displacement=argument_local+offset, bytes=width,
                               sourceOffset=offset, sourceRegister='xmm'+str(number)))
            g.take(_stack('0f29' if width == 16 else 'f20f11', number, argument_local+offset))
            if load:
                next_offset = 32 if offset == 0 else 48
                g.take(_stack('0f10' if next_offset == 32 else 'f20f10', 0 if next_offset == 32 else 1, hidden_local+next_offset))
        transfer_call = g.at
        g.call(setter)
    return dict(selectedBytes=g.seen, nextInstructionVa=g.at, typeName=TYPE, managedBytes=56,
        readerRegister=reader, outputRegister=output, wrapperRegister='rsi', contextInstructionVa=context_site,
        contextCell=context_cell, sourceCallVa=source_call, sourceTarget=source,
        hiddenOutputLocal=dict(displacement=hidden_local, bytes=56),
        sourceLocalCopies=copies, directFieldStores=stores, fieldOffset=field,
        transferCallVa=transfer_call, transferTarget=barrier if setter is None else setter,
        namedSetterSelected=setter is not None, barrierReferenceLaneOffset=8,
        destinationFieldOffsetAdmitted=setter is None, ownSetterFieldAndBarrierJoinRequired=setter is not None,
        completeSourceBitsTransferredUnchanged=True, ownedNullExits=[dict(edge,
            bytes=bytes(g.bytes[edge['nullTargetVa']+i] for i in range(6)).hex().upper()) for edge in exits],
        parentFrameAdmitted=False, fullCallerAdmitted=False, childGrammarAdmitted=False, wholeOwnerAdmitted=False)


def derive(image, pins, *, wrapper_name):
    import json
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import generated_action_sources as actions, pointer_param as pointer
    from scripts.game_data.memorypack.generated_alpha_blend_field_sources import derive_setter, read_source
    _publication_gate(image, pins)
    profiles = {
        'Beyond.MemoryPack.Beyond_Gameplay_Core_CharInteractPerform_CharAnimActionDataForMemoryPack': ('rdi', 'rbx', 32, 96),
        'Beyond.MemoryPack.Beyond_Montage_ClipMontageDataForMemoryPack': ('rbx', 'rdi', 48, None),
        'Beyond.MemoryPack.Beyond_Montage_SequenceMontageDataForMemoryPack': ('rdi', 'rbx', 32, None),
    }
    need('selected-actual-Alpha-parent', wrapper_name in profiles)
    reader, output, local, argument = profiles[wrapper_name]
    base = image.pe.image_base
    wrappers = {w.name: w for w in image.memorypack_wrappers.values()}
    wrapper = wrappers[wrapper_name]
    member, = [m for m in wrapper.members if m.declared_type == TYPE]
    method = pointer.methods(image, wrapper)['Deserialize']
    body = pointer.owned(image, image.method_pointer_va(method))
    contexts, skipped = actions._contexts(image, body['rows'])
    context, = [c for c in contexts if c.get('fullTypeName') == TYPE
                and c.get('methodOwner') == 'MemoryPack.MemoryPackReader' and c.get('methodName') == 'ReadValue']
    position, = [i for i, row in enumerate(body['rows']) if int(row['va'], 16) == base+context['instructionRva']]
    calls = [r for r in body['rows'][position+1:position+8] if pointer.control_transfer(r)['kind'] == 'call']
    need('actual-direct-E8-source-after-context', bool(calls) and bytes.fromhex(calls[0]['bytes'])[:1] == b'\xe8')
    target = pointer.control_transfer(calls[0])['target']
    usage = derive_typed_usage_context(image, context['instructionRva'], label='alphaFieldFragment.context')
    targets, barrier, disabled = actions._prepare(image, pins)
    setter = derive_setter(image, pins, member, wrappers, barrier, {})
    source = read_source(image, pins, context=context, source_target=target)
    own = source['proof']['childSource']['proof']['layout']
    nominal = setter['managedValueLayout']
    need('same-current-source-and-destination-nominal56', own['typeDefinition'] == nominal['typeDefinition']
         and json.loads(json.dumps(own['fields'])) == json.loads(json.dumps(nominal['fields']))
         and source['referenceLaneOffsets'] == nominal['referenceLaneOffsets'] == [8]
         and source['paddingByteRanges'] == nominal['paddingByteRanges'] == [[52, 56]])
    direct = argument is None
    need('same-actual-setter-kind', direct is (setter['getter'] is None))
    ctx = NativeReferenceContext(image)
    ancestry = []
    current = wrapper.wrapped_type
    while current not in ('', 'object', 'System.Object'):
        need('complete-finite-parent-ancestry', current not in ancestry and len(ancestry) < 32)
        ancestry.append(current)
        current = ctx.parent(current)
    declaring = wrappers[member.declaring_wrapper]
    need('current-parent-derived-from-actual-setter-owner', declaring.wrapped_type in ancestry)
    holder = None
    if direct:
        holder = setter['directHolder']
        need('actual-declared-base-holder16', isinstance(holder, dict)
             and holder['field'] == [declaring.name, declaring.wrapped_type, 16]
             and holder['inheritedFieldAliasUsed'] is False and holder['openGenericOffsetUsed'] is False)
        wrapper_chain = []
        current = wrapper.name
        while current != declaring.name:
            need('finite-ordinary-caller-wrapper-ancestry', current not in wrapper_chain and len(wrapper_chain) < 16
                 and current in ctx.index.types and ctx.index.types[current].generic_container_index < 0
                 and not ctx.is_value_type(current))
            wrapper_chain.append(current)
            ctx.require_ordinary_kind(ctx.index.types[current].parent_index, 18)
            current = ctx.parent(current)
        holder = dict(holder, callerWrapperAncestry=wrapper_chain+[declaring.name])
    start = base+context['instructionRva']-(3 if reader == 'rbx' else 0)
    fragment = program(body['regions'], start, reader=reader, output=output,
        context_cell=base+usage['usageCellRva'], source=target, field=setter['fieldOffset'],
        barrier=base+barrier, hidden_local=local, setter=None if direct else base+setter['method'][3],
        argument_local=argument)
    need('same-source-call-and-owned-request', fragment['sourceCallVa'] == int(calls[0]['va'], 16)
         and fragment['contextInstructionVa'] == base+usage['instructionRva'])
    if direct:
        need('independent-destination-all56-bits-and-same-reference-lane',
             [(s['sourceOffset'], s['bytes']) for s in fragment['directFieldStores']] == [(0,16),(16,16),(32,16),(48,8)]
             and setter['program']['sourceSlices'] == [[0,16],[16,16],[32,16],[48,8]]
             and setter['program']['barrierReferenceLaneOffset'] == fragment['barrierReferenceLaneOffset'] == 8)
    else:
        need('same-whole-named-setter-field-and-barrier', fragment['transferTarget'] == base+setter['method'][3]
             and fragment['fieldOffset'] == setter['fieldOffset']
             and setter['program']['fieldOffset'] == setter['fieldOffset']
             and setter['program']['barrierReferenceLaneOffset'] == fragment['barrierReferenceLaneOffset'] == 8)
    _publication_gate(image, pins)
    return json.loads(json.dumps(dict(schema='endfield.alpha-blend-parent-field-fragment.v1',
        status='proved-conditional-alpha56-parent-field-fragment', nativeInputs=pins,
        typeName=TYPE, wrapperName=wrapper.name, member=member.row(), managedBytes=56,
        sourceTargetRva=target-base, readerMethodDefinition=source['readerMethodDefinition'],
        resultAbi='hidden-local-to-owned-field', selectedFieldTransferProved=True,
        proof=dict(source=source, setter=setter, sourceProgram=fragment, typedContext=context,
            typedRequest=usage, callerMethod=[method.index, wrapper.name, 'Deserialize', body['pointer']-base],
            callerWindows=body['windows'], callerRegions=[[a-base, h.hex() if isinstance(h, bytes) else h] for a,h in body['regions']],
            callerOriginalAncestry=ancestry, callerDirectHolder=holder, skippedContextCells=skipped),
        parentFieldAdmitted=False, parentFrameAdmitted=False, wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Fresh actual Alpha ReadValue/context and own full managed56/canonical transfer join the exact hidden-local setup, every3x16+8 copied source slice, current named setter or direct field stores, and lane8 disabled barrier.',
            conditional=__doc__+' Compatible disjoint buffered caller frame/output/locals, coherent initialized contexts/getter and normal helpers remain conditions.',
            unresolved=['complete caller entry and all other fields', 'complete enclosing caller frame/lifecycle', 'live provider and callback selection', 'whole enclosing owner/EOF']))))
