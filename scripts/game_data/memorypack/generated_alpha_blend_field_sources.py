"""AlphaBlend's named managed56 field transfer, distinct from its MC3 wire."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.alpha_blend_value_sources import TYPE

SLICES = [[0, 16], [16, 16], [32, 16], [48, 8]]


def need(key, condition):
    if not condition:
        raise ValueError('generatedAlphaBlendField.' + key)


def setter_program(regions, entry, *, getter, field, barrier, path_factory=None):
    from scripts.game_data.memorypack.generated_inline_constructor_sources import _nonnull
    from scripts.game_data.memorypack.generated_member_sources import _displacement
    need('actual-named-targets-and-owned-field', (getter is None or type(getter) is int and getter > 0)
         and type(barrier) is int and barrier > 0
         and type(field) is int and 16 <= field < 2**31-64)
    need('callable-only-path-factory', path_factory is None or callable(path_factory))
    g = (BytesPath if path_factory is None else path_factory)(regions, entry)
    if getter is None:
        g.take('4883ec28', '488b4910', '4885c9')
    else:
        g.take('4053', '4883ec20', '488bda', '33d2')
        g.call(getter)
        g.take('4885c0')
    null = _nonnull(g)
    null = dict(null, bytes=bytes(g.bytes[null['nullTargetVa']+i] for i in range(6)).hex().upper())
    if getter is None:
        g.take('0f1002', '0f104a10', _displacement('0f1141', field), '0f104220',
               _displacement('0f1149', field+16), 'f20f104a30', _displacement('0f1141', field+32),
               _displacement('f20f1149', field+48),
               ('4883c1'+bytes((field+8,)).hex()) if field+8 < 128 else
               ('4881c1'+(field+8).to_bytes(4, 'little').hex()), '4883c428')
    else:
        g.take('0f1003', _displacement('488d48', field+8), '0f104b10',
               _displacement('0f1140', field), '0f104320', _displacement('0f1148', field+16),
               'f20f104b30', _displacement('0f1140', field+32), _displacement('f20f1148', field+48),
               '4883c420', '5b')
    need('same-owned-disabled-barrier', g.relative('e9') == barrier)
    return dict(selectedBytes=g.seen, managedBytes=56, storedBytes=56, fieldOffset=field,
        sourceSlices=SLICES, referenceLaneOffsets=[8], barrierReferenceLaneOffset=8,
        holderOffset=16 if getter is None else None,
        incomingValueSource='rdx' if getter is None else 'rdx preserved in rbx',
        getterReceiver=None if getter is None else 'incoming rcx with zero edx',
        wholeInputBitsStoredUnchanged=True, completeSourceBitsStoredUnchanged=True,
        entryRspRestored=True, normalFrameAndReturn=True, nonvolatileRegistersRestored=[] if getter is None else ['rbx'],
        normalReturnViaBarrier=True, ownedNullExit=null, disabledCollectorRequired=True,
        childGrammarAdmitted=False)



def direct_holder(image, ctx, wrapper):
    """Bind the literal declared holder spelling, with no inherited alias."""
    from scripts.game_data.memorypack import scalar_param_native as scalar
    td = ctx.index.types[wrapper.name]
    need('nongeneric-named-direct-holder-owner', td.generic_container_index < 0
         and td.index == wrapper.type_definition and not ctx.is_value_type(wrapper.wrapped_type))
    fields = [field for field in image.metadata.fields_for(td)
              if image.metadata.string(field.name_index) in ('__instance', '___instance')]
    need('one-literal-declared-instance-holder', len(fields) == 1)
    field, = fields
    name = image.metadata.string(field.name_index)
    actual = ctx.field(wrapper.name+'::'+name)
    need('actual-direct-holder16', actual == (wrapper.name, wrapper.wrapped_type, 16))
    pointer = ctx.type_pointer(field.type_index)
    scalar.ordinary(image, pointer, 18, 'generatedAlphaBlendField.holder', reference=True)
    return dict(fieldName=name, field=list(actual), ownerTypeDefinition=td.index,
        fieldTypeRecordHex=image.pe.bytes_at_va(pointer, 16).hex().upper(),
        inheritedFieldAliasUsed=False, openGenericOffsetUsed=False)


def derive_setter(image, pins, member, wrappers, barrier, getter_cache):
    from scripts.game_data.il2cpp.reference_field_programs import _setter_metadata
    from scripts.game_data.memorypack import generated_member_sources as members, pointer_param as pointer, scalar_param_native as scalar
    from scripts.game_data.memorypack.alpha_blend_value_sources import layout
    ctx, wrapper, field, target, offset, method = _setter_metadata(image, wrappers, member)
    need('exact-nominal-reference-parent', member.declared_type == TYPE and not ctx.is_value_type(wrapper.wrapped_type))
    nominal = layout(image, ctx)
    need('own-padded-single-reference-layout', nominal['managedBytes'] == 56
         and nominal['referenceLaneOffsets'] == [8] and nominal['paddingByteRanges'] == [[52, 56]])
    scalar.owned_method_abi(image, ctx, method.index, wrapper.type_definition,
        ('void', 1, False), [(TYPE, 17, False)], 'generatedAlphaBlendField.setter')
    need('nongeneric-owned-setter', method.generic_container_index < 0)
    parameter, = image.metadata.parameters_for(method)
    raw = image.pe.bytes_at_va(ctx.type_pointer(parameter.type_index), 16)
    body = members._body(image, image.method_pointer_va(method))
    getter_proof = None
    getter_target = None
    holder_proof = None
    if image.pe.bytes_at_va(body['pointer'], 4) == bytes.fromhex('4883ec28'):
        holder_proof = direct_holder(image, ctx, wrapper)
        profile = 'direct-base-holder-setter'
    else:
        getter = pointer.methods(image, wrapper)['get___instance']
        getter_target = image.method_pointer_va(getter)
        getter_proof = members._coherent_getter(image, ctx, wrapper, getter, getter_cache,
            barrier=image.pe.image_base+barrier)
        profile = 'cached-getter-setter'
    program = setter_program(body['regions'], body['pointer'], getter=getter_target,
                             field=offset, barrier=image.pe.image_base+barrier)
    return dict(method=[method.index, wrapper.name, image.metadata.string(method.name_index), body['pointer']-image.pe.image_base],
        member=member.row(), targetField=target, fieldOffset=offset, parameterTypeRecordHex=raw.hex().upper(), storedBytes=56,
        managedValueLayout=nominal, sourceFamily=body['family'], codeWindows=body['windows'], profile=profile,
        program=program, getter=getter_proof, directHolder=holder_proof, ordinarySourceRows=body['rows'],
        ordinarySourceRegions=[[a-image.pe.image_base, h.hex() if isinstance(h, bytes) else h] for a,h in body['regions']],
        incomingValueStoredUnchanged=True, childGrammarAdmitted=False, factoryAdmitted=False)


def validate_event(event, setter):
    layout = setter.get('managedValueLayout', {})
    program = setter.get('program', {})
    raw = bytes.fromhex(setter.get('parameterTypeRecordHex', ''))
    need('exact-own-hidden56-event-and-nominal-setter', event.get('kind') == 'managed:'+TYPE
         and event.get('declaredType') == layout.get('typeName') == TYPE
         and event.get('mode') == 'typed-managed-value' and event.get('actualSourceProved') is True
         and event.get('resultAbi') == 'hidden-local' and 'wireBytes' not in event
         and event.get('managedBytes') == layout.get('managedBytes') == setter.get('storedBytes') == 56
         and event.get('referenceLaneOffsets') == layout.get('referenceLaneOffsets') == [8]
         and layout.get('paddingByteRanges') == [[52, 56]] and type(layout.get('typeDefinition')) is int
         and len(raw) == 16 and raw[10:12] == bytes((17, 128))
         and int.from_bytes(raw[:8], 'little') == layout['typeDefinition']
         and program.get('sourceSlices') == SLICES and program.get('barrierReferenceLaneOffset') == 8
         and all(program.get(k) is True for k in ('wholeInputBitsStoredUnchanged',
             'completeSourceBitsStoredUnchanged', 'entryRspRestored', 'normalFrameAndReturn')))
    context = event.get('context')
    if event.get('sourceContextMode')=='owned-closed-forwarder':
        from scripts.game_data.memorypack.alpha_blend_closed_value_sources import verify
        actual=event.get('alphaBlendClosedForwarderSource',{})
        verify(actual,actual.get('nativeInputs'))
        need('same-own-closed-Alpha56-source',context is None and actual.get('sourceTargetRva')==event.get('sourceTargetRva')
            and actual['proof']['childSource']['proof']['layout']['typeDefinition']==layout['typeDefinition'])
        return True
    need('own-ordinary-hidden-ReadValue-parent-context', isinstance(context, dict)
         and context.get('fullTypeName') == TYPE and context.get('methodOwner') == 'MemoryPack.MemoryPackReader'
         and context.get('methodName') == 'ReadValue' and context.get('register') == 'r8'
         and context.get('typeKind') == 17 and event.get('sourceContextMode') is None)
    return True


def read_source(image, pins, *, context, source_target):
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack.alpha_blend_value_transfer import derive
    need('actual-own-hidden56-context', isinstance(context, dict) and context.get('fullTypeName') == TYPE
         and context.get('methodOwner') == 'MemoryPack.MemoryPackReader' and context.get('methodName') == 'ReadValue'
         and context.get('register') == 'r8' and context.get('typeKind') == 17)
    usage = derive_typed_usage_context(image, context['instructionRva'], label='generatedAlphaBlendField.ReadValue')
    need('same-actual-context-bytes', usage['methodSpec'] == context['methodSpec']
         and usage['instructionHex'] == context['instructionHex'])
    proof = derive(image, pins, typed_request=usage, source_target=source_target, count_limit=10000)
    need('independently-proved-nominal-value56-source', proof['nativeInputs'] == pins and proof['typeName'] == TYPE
         and proof['managedBytes'] == 56 and proof['resultAbi'] == 'hidden-local'
         and proof['actualSourceProved'] is True and proof['sourceTargetRva'] == source_target-image.pe.image_base
         and proof['readerMethodDefinition'] == context['methodSpec'][0]
         and proof['referenceLaneOffsets'] == [8] and proof['paddingByteRanges'] == [[52, 56]]
         and proof['wireGrammarAdmitted'] is False)
    return proof
