"""Finite AlphaBlend wrapper programs, separate from Beyond curve16.

AlphaBlend copies a machine payload of 56 bytes while serializing three
members. These byte programs establish neither that nominal layout nor child
wire framing; fresh metadata and independently owned child sources must join
them. In particular, an existing wrapper retains its unserialized state.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

TYPE = 'Beyond.Gameplay.View.Animation.AlphaBlend'
WRAPPER = 'Beyond.MemoryPack.Beyond_Gameplay_View_Animation_AlphaBlendForMemoryPack'
LABEL = 'alphaBlendValue'


def need(key, condition, detail=None):
    if not condition:
        raise ValueError(LABEL + '.' + key + ':' + str(detail)[:650])


def zero_program(regions, entry):
    g = BytesPath(regions, entry)
    g.take('0f57c0', '33c0', '0f114110', '0f114120', '0f114130', '48894140', 'c3')
    return dict(selectedBytes=g.seen, managedBytes=56,
                zeroedSlices=[[0, 16], [16, 16], [32, 16], [48, 8]],
                completePayloadZeroed=True, sameFrameReturned=True,
                physicalExtentProved=False, nominalLayoutAdmitted=False)


def getter_program(regions, entry):
    g = BytesPath(regions, entry)
    g.take('0f104210', '488bc1', '0f104a20', '0f1101', '0f104230',
           '0f114910', 'f20f104a40', '0f114120', 'f20f114930', 'c3')
    return dict(selectedBytes=g.seen, managedBytes=56,
                sourceSlices=[[0, 16], [16, 16], [32, 16], [48, 8]],
                completePayloadBitsCopied=True, returnsSameOutputRax=True,
                sourceWrapperRegister='rdx', outputRegister='rcx',
                normalFrameAndReturn=True, physicalExtentProved=False,
                nominalLayoutAdmitted=False, wireGrammarAdmitted=False)


def reader_program(regions, entry, offsets, symbols, *, new, ff):
    from scripts.game_data.memorypack.generated_inline_constructor_sources import _nonnull

    need('literal-entry-modes', type(new) is bool and type(ff) is bool)
    need('complete-child-symbols', set(symbols) == {'enum', 'single', 'curve', 'allocate', 'barrier'}
         and all(type(v) is int and v > 0 for v in symbols.values()))
    need('owned-reader-counter-offsets', set(offsets) >= {'currentPtr', 'bufferLength', 'advancedCount', 'consumed'}
         and all(type(offsets[k]) is int and 0 <= offsets[k] < 128
                 for k in ('currentPtr', 'bufferLength', 'advancedCount', 'consumed')))
    slot = lambda key: bytes((offsets[key],)).hex()
    g = BytesPath(regions, entry)
    g.take('48895c2408', '48896c2410', '4889742418', '57', '4883ec30')
    initialized_flag = g.relative('803d') + 1
    g.take('00', '488bfa', '488bd9')
    g.branch('0f84', False)
    g.take('837b' + slot('bufferLength') + '01')
    g.branch('0f8c', False)
    g.take('488b43' + slot('currentPtr'), '0fb630', '8b6b' + slot('bufferLength'), '83ed01')
    g.branch('0f88', False)
    g.take('48ff43' + slot('currentPtr'), 'ff43' + slot('advancedCount'),
           'ff43' + slot('consumed'), '896b' + slot('bufferLength'), '4080feff')
    g.branch('0f84', ff)
    allocation = None
    requests = []
    null_exits = []
    if ff:
        g.take('48c70700000000', '488bcf')
        g.jump('eb', 1)
    else:
        g.take('48833f00')
        g.branch('0f84', new)
        if new:
            allocation = dict(instructionVa=g.at, classCell=g.relative('488b0d'))
            g.call(symbols['allocate'])
            g.take('4885c0')
            null_exits.append(_nonnull(g))
            g.take('0f57c0', '33c9', '0f114010', '0f114020', '0f114030', '48894840',
                   '488bcf', '488907')
            g.call(symbols['barrier'])
            g.take('90')
            g.jump('e9')
        g.take('4080fe03')
        g.branch('0f85', False)
        requests.append(dict(role='enum', instructionVa=g.at, cell=g.relative('488b15')))
        g.take('488bcb', '488b37')
        g.call(symbols['enum'])
        g.take('4885f6')
        null_exits.append(_nonnull(g))
        g.take('894614', '488bcb', '488b37')
        g.call(symbols['single'])
        g.take('4885f6')
        null_exits.append(_nonnull(g))
        g.take('f30f114610', '488d4c2420')
        requests.append(dict(role='curve', instructionVa=g.at, cell=g.relative('4c8b05')))
        g.take('488bd3', '488b3f')
        g.call(symbols['curve'])
        g.take('4885ff')
        null_exits.append(_nonnull(g))
        g.take('0f10442420', '488d4f18', '0f114718')
    g.take('488b5c2440', '488b6c2448', '488b742450', '4883c430', '5f')
    need('same-whole-output-or-field-barrier', g.relative('e9') == symbols['barrier'])
    return dict(selectedBytes=g.seen, initializedFlag=initialized_flag, newWrapper=new and not ff,
                nullMarkerSelected=ff, headerBytes=1, memberCount=3,
                allFourHeaderReaderUpdatesProved=True, allocation=allocation,
                actualTypedRequests=requests, ownedNullExits=null_exits,
                freshDefaultPayloadBytes=56 if new and not ff else None,
                existingUnserializedStatePreserved=not new and not ff,
                outputClearedBytes=8 if ff else None,
                serializedManagedSlices=[] if ff else [[4, 4], [0, 4], [8, 16]],
                curveHiddenLocal=dict(displacement=32, bytes=16) if not ff else None,
                referenceBarrierPayloadOffset=8 if not ff else None,
                normalFrameAndNonvolatilesRestored=True,
                childGrammarAdmitted=False, nominalLayoutAdmitted=False,
                condition='Initialized metadata, valid disjoint Reader/output/frame, one buffered header byte and normal ABI-preserving child helpers. The exact Beyond curve16 source/layout/wire is separate. Fresh wrappers zero56; existing wrappers retain all unserialized state. FF clears only the whole wrapper output reference; value56 adapter/default transfer remains separate.')


def layout(image, ctx):
    """Fresh exact ten-field machine56 layout; no source or wire admission."""
    from scripts.game_data.memorypack import scalar_param_native as scalar
    md = image.metadata
    td = ctx.index.types[TYPE]
    need('own-nongeneric-value-definition', ctx.is_value_type(TYPE) and td.generic_container_index < 0)
    expected = [('_blendTime', 'float', 16),
                ('_blendOption', 'Beyond.Gameplay.View.Animation.AlphaBlendOption', 20),
                ('_customCurve', 'Beyond.FAnimationCurve', 24),
                *[(name, 'float', offset) for name, offset in zip(
                    ('m_alphaLerp', 'm_alphaBlend', 'm_blendTimeRemaining', 'm_blendedValue',
                     'm_beginValue', 'm_desiredValue', 'm_cachedDesiredBlendedValue'), range(40, 68, 4))]]
    fields = [f for f in md.fields_for(td) if not ctx.field_attributes(f.type_index) & 16]
    actual = [(md.string(f.name_index), *ctx.field(TYPE + '::' + md.string(f.name_index))[1:]) for f in fields]
    need('own-all-ten-current-fields', actual == expected, actual)
    for field in fields:
        kind = 12 if ctx.type_name(field.type_index) == 'float' else 17
        scalar.ordinary(image, ctx.type_pointer(field.type_index), kind, LABEL + '.storedField')
    need('current-value-size-index', 0 <= td.index < image.registration['typeDefinitionsSizesCount'])
    size = image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'], 16) + td.index * 8)
    need('own-machine56-size', (image.pe.u32_at_va(size), image.pe.u32_at_va(size + 4)) == (72, 56))
    enum_type = 'Beyond.Gameplay.View.Animation.AlphaBlendOption'
    enum = ctx.index.types[enum_type]
    backing, = [f for f in md.fields_for(enum) if not ctx.field_attributes(f.type_index) & 16]
    need('own-option-int32-backing', ctx.is_enum(enum_type) and enum.generic_container_index < 0
         and md.string(backing.name_index) == 'value__' and ctx.type_name(backing.type_index) == 'int')
    scalar.ordinary(image, ctx.type_pointer(backing.type_index), 8, LABEL + '.optionBacking')
    return dict(typeName=TYPE, typeDefinition=td.index, fields=actual, managedBytes=56,
                referenceLaneOffsets=[8], paddingByteRanges=[[52, 56]])


def derive_wrapper(image, pins, *, count_limit=10000):
    """Fresh own MC3/56-byte layout/program joins; canonical adapter stays open."""
    import json
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import generated_action_sources as actions
    from scripts.game_data.memorypack import generated_member_sources as members
    from scripts.game_data.memorypack import generated_primitive_sources as primitives
    from scripts.game_data.memorypack import pointer_param, primitive_param, scalar_param_native as scalar
    from scripts.game_data.memorypack.beyond_curve_value_sources import derive as curve_value
    from scripts.game_data.memorypack.skill_passive_map_sources import _barrier

    _publication_gate(image, pins)
    ctx = NativeReferenceContext(image)
    md = image.metadata
    base = image.pe.image_base
    wrapper, = [w for w in image.memorypack_wrappers.values() if w.wrapped_type == TYPE]
    need('own-value-wrapper', wrapper.name == WRAPPER and wrapper.wrapped_is_value_type
         and not wrapper.abstract and not ctx.is_value_type(wrapper.name))
    need('exact-current-wire-declarations', [(m.name, m.declared_type) for m in wrapper.members] == [
        ('_blendOption', 'Beyond.Gameplay.View.Animation.AlphaBlendOption'),
        ('_blendTime', 'float'), ('_customCurve', 'Beyond.FAnimationCurve')])
    nominal = layout(image, ctx)
    td = ctx.index.types[TYPE]
    actual = nominal['fields']
    enum_type = 'Beyond.Gameplay.View.Animation.AlphaBlendOption'
    holder = ctx.field(wrapper.name + '::__instance')
    need('same-embedded-value-holder', holder == (wrapper.name, TYPE, 16), holder)
    mm = pointer_param.methods(image, wrapper)
    for member, kind in zip(wrapper.members, (17, 12, 17)):
        scalar.owned_method_abi(image, ctx, member.method_index, wrapper.type_definition,
            ('void', 1, False), [(member.declared_type, kind, False)], LABEL + '.memberDeclaration')
    reader = mm['Deserialize']
    primitive_param.reader_abi(image, ctx, reader, wrapper)
    body = members._body(image, image.method_pointer_va(reader))
    rows = body['rows']
    def before(text):
        stop, = [i for i, r in enumerate(rows) if r['text'] == text]
        chosen = next(r for r in reversed(rows[:stop]) if members.control_transfer(r)['kind'] == 'call')
        return members.control_transfer(chosen)['target']
    allocate, = [members.control_transfer(r)['target'] for i, r in enumerate(rows[:-1])
                 if members.control_transfer(r)['kind'] == 'call' and rows[i + 1]['text'] == 'test rax, rax']
    barrier, = [members.control_transfer(r)['target'] for i, r in enumerate(rows)
                if members.control_transfer(r)['kind'] == 'jump' and rows[i - 1]['text'] == 'pop rdi']
    symbols = dict(enum=before('mov [rsi+0x14], eax'), single=before('movss [rsi+0x10], xmm0'),
                   curve=before('movups [rdi+0x18], xmm0'), allocate=allocate, barrier=barrier)
    offsets = scalar.reader_offsets(image, LABEL)
    programs = [reader_program(body['regions'], body['pointer'], offsets, symbols, new=new, ff=ff)
                for new in (False, True) for ff in (False, True)]
    contexts, skipped = actions._contexts(image, rows)
    by_instruction = {base + c['instructionRva']: c for c in contexts}
    enum_request, curve_request = programs[0]['actualTypedRequests']
    enum_context = by_instruction[enum_request['instructionVa']]
    curve_context = by_instruction[curve_request['instructionVa']]
    need('actual-enum-ReadUnmanaged-context', enum_context['fullTypeName'] == enum_type
         and enum_context['methodOwner'] == 'MemoryPack.MemoryPackReader'
         and enum_context['methodName'] == 'ReadUnmanaged')
    need('actual-distinct-Beyond-ReadValue-context', curve_context['fullTypeName'] == 'Beyond.FAnimationCurve'
         and curve_context['methodOwner'] == 'MemoryPack.MemoryPackReader' and curve_context['methodName'] == 'ReadValue')
    usage = derive_typed_usage_context(image, curve_context['instructionRva'], label=LABEL + '.curve')
    child = curve_value(image, pins, typed_request=usage, source_target=symbols['curve'], count_limit=count_limit)
    need('same-fresh-curve-request-source', child['nativeInputs'] == pins and child['actualSourceProved'] is True
         and child['typeName'] == 'Beyond.FAnimationCurve' and child['managedBytes'] == 16
         and child['referenceLaneOffset'] == 0 and child['sourceTargetRva'] == symbols['curve'] - base)
    allocations = []
    for program in programs:
        if program['allocation'] is not None:
            allocation = derive_typed_usage_context(image, program['allocation']['instructionVa'] - base,
                                                     label=LABEL + '.wrapperAllocation')
            need('actual-allocated-own-wrapper', (allocation['tag'], allocation['typeName']) == (1, wrapper.name))
            allocations.append(allocation)
    leaves = []
    for name, builder in (('.ctor', zero_program), ('CreateInstance', zero_program), ('GetValue', getter_program)):
        method = mm[name]
        scalar.owned_method_abi(image, ctx, method.index, wrapper.type_definition,
            (TYPE, 17, False) if name == 'GetValue' else ('void', 1, False), [], LABEL + '.' + name)
        entry = image.method_pointer_va(method)
        proof = builder([(entry, image.pe.bytes_at_va(entry, 128))], entry)
        leaves.append(dict(method=[method.index, wrapper.name, name, entry - base], program=proof))
    _publication_gate(image, pins)
    return json.loads(json.dumps(dict(schema='endfield.alpha-blend-wrapper-source.v1',
        status='proved-conditional-alpha-blend-wrapper-source', nativeInputs=pins,
        typeName=TYPE, wrapperName=WRAPPER, managedBytes=56, serializedMemberCount=3,
        referenceLaneOffsets=[8], paddingByteRanges=[[52, 56]],
        completeStaticWrapperPathsProved=True, canonicalAdapterAdmitted=False,
        parentFieldAdmitted=False, wholeOwnerAdmitted=False,
        proof=dict(layout=dict(typeDefinition=td.index, fields=actual, holder=holder),
            readerMethod=[reader.index, wrapper.name, 'Deserialize', body['pointer'] - base],
            family=body['family'], codeWindows=body['windows'], programs=programs,
            contexts=[enum_context, curve_context], skippedContextCells=skipped,
            enumSource=primitives.derive(image, symbols['enum'], 'int32', offsets),
            singleSource=primitives.derive(image, symbols['single'], 'float32', offsets),
            curveSource=child, wrapperAllocations=allocations,
            barrierSource=_barrier(image, barrier), leaves=leaves),
        condition='Own current MC3/static wrapper programs compose independent primitive and Beyond curve sources. Normal helpers, compatible disjoint storage and disabled barriers remain conditions. Own canonical value56 adapter/default transfer and enclosing selection are not yet admitted.'),
        default=lambda v: v.hex() if isinstance(v, bytes) else sorted(v)))
